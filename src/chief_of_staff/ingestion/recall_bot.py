"""Recall.ai meeting bot integration — auto-join Zoom/Meet/Teams to record and transcribe.

Recall.ai provides a meeting bot API that:
1. Joins any meeting via URL (Zoom, Google Meet, Microsoft Teams)
2. Records audio/video
3. Generates real-time transcripts
4. Sends webhook when transcript is ready

This is the most reliable way to get the Chief of Staff "in the room"
for every internal meeting without requiring hosts to enable cloud recording.

Setup:
1. Sign up at https://www.recall.ai/
2. Get your API key from the dashboard
3. Set RECALL_API_KEY in .env
4. Configure webhook URL for transcript delivery
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from chief_of_staff.config import settings
from chief_of_staff.knowledge.store import ingest

logger = logging.getLogger(__name__)

RECALL_API_BASE = "https://api.recall.ai/api/v1"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Token {settings.recall_api_key}",
        "Content-Type": "application/json",
    }


async def dispatch_bot(
    meeting_url: str,
    meeting_title: str = "",
    bot_name: str = "Arcuate Chief of Staff",
    join_at: str | None = None,
) -> dict[str, Any]:
    """Send a Recall.ai bot to join a meeting.

    Args:
        meeting_url: The meeting join URL (Zoom, Meet, Teams).
        meeting_title: Optional title for tracking.
        bot_name: Name shown in the meeting participant list.
        join_at: ISO timestamp to schedule join. If None, joins immediately.

    Returns:
        Bot creation response from Recall.ai API.
    """
    payload: dict[str, Any] = {
        "meeting_url": meeting_url,
        "bot_name": bot_name,
        "transcription_options": {
            "provider": "default",
        },
        "real_time_transcription": {
            "destination_url": f"{settings.webhook_base_url}/webhooks/recall/transcript",
        },
    }

    if join_at:
        payload["join_at"] = join_at

    if meeting_title:
        payload["metadata"] = {"title": meeting_title}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{RECALL_API_BASE}/bot/",
            headers=_headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

    bot_id = data.get("id", "unknown")
    logger.info(f"Recall bot dispatched: {bot_id} → {meeting_url} (title: {meeting_title})")
    return data


async def get_bot_status(bot_id: str) -> dict[str, Any]:
    """Check the status of a deployed bot."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{RECALL_API_BASE}/bot/{bot_id}/",
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()


async def get_bot_transcript(bot_id: str) -> list[dict[str, Any]]:
    """Get the full transcript from a completed bot session."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{RECALL_API_BASE}/bot/{bot_id}/transcript/",
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


async def list_bots(
    meeting_url: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List recent bots, optionally filtered by meeting URL."""
    params: dict[str, Any] = {"limit": limit}
    if meeting_url:
        params["meeting_url"] = meeting_url

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{RECALL_API_BASE}/bot/",
            headers=_headers(),
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    return data.get("results", [])


async def remove_bot(bot_id: str) -> None:
    """Remove a bot from a meeting."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{RECALL_API_BASE}/bot/{bot_id}/leave_call/",
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
    logger.info(f"Recall bot removed: {bot_id}")


async def ingest_bot_transcript(
    bot_id: str,
    meeting_title: str = "",
    meeting_url: str = "",
) -> str:
    """Fetch and ingest a completed bot's transcript.

    Returns the document ID.
    """
    transcript_data = await get_bot_transcript(bot_id)
    bot_info = await get_bot_status(bot_id)

    # Format transcript
    lines: list[str] = []
    for entry in transcript_data:
        speaker = entry.get("speaker", "Unknown")
        words = entry.get("words", [])
        text = " ".join(w.get("text", "") for w in words)
        timestamp = entry.get("start_time", "")
        if text.strip():
            lines.append(f"{speaker} [{timestamp}]: {text}")

    transcript = "\n".join(lines) if lines else "(no transcript)"

    # Get metadata from bot info
    created_at = bot_info.get("created_at", "")
    metadata_from_bot = bot_info.get("metadata", {})
    title = meeting_title or metadata_from_bot.get("title", f"Meeting {bot_id[:8]}")

    content = (
        f"Meeting: {title}\n"
        f"Date: {created_at}\n"
        f"Platform: {bot_info.get('meeting_platform', 'unknown')}\n"
        f"Meeting URL: {meeting_url}\n"
        f"\n--- Transcript ---\n"
        f"{transcript}"
    )

    doc_id = ingest(
        source="meeting",
        source_id=f"recall_{bot_id}",
        title=f"Meeting: {title}",
        content=content,
        metadata={
            "platform": bot_info.get("meeting_platform", "unknown"),
            "bot_id": bot_id,
            "meeting_url": meeting_url,
            "created_at": created_at,
            "ingested_via": "recall_bot",
        },
    )

    logger.info(f"Ingested Recall bot transcript: {title} -> {doc_id}")
    return doc_id
