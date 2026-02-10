"""ElevenLabs transcript ingestion — pull call transcripts into the knowledge base."""

from __future__ import annotations

import logging

import httpx

from chief_of_staff.config import settings
from chief_of_staff.knowledge.store import ingest

logger = logging.getLogger(__name__)

BASE_URL = "https://api.elevenlabs.io/v1"


async def fetch_and_ingest_transcripts(limit: int = 50) -> int:
    """Fetch conversation transcripts from ElevenLabs and ingest them.

    Uses the ElevenLabs Conversational AI API to list conversations
    and pull transcripts.

    Returns:
        Number of transcripts ingested.
    """
    headers = {"xi-api-key": settings.elevenlabs_api_key}
    count = 0

    async with httpx.AsyncClient() as client:
        # List recent conversations
        resp = await client.get(
            f"{BASE_URL}/convai/conversations",
            headers=headers,
            params={"page_size": limit},
        )
        resp.raise_for_status()
        conversations = resp.json().get("conversations", [])

        for conv in conversations:
            conv_id = conv.get("conversation_id", "")
            if not conv_id:
                continue

            try:
                # Get full conversation details including transcript
                detail_resp = await client.get(
                    f"{BASE_URL}/convai/conversations/{conv_id}",
                    headers=headers,
                )
                detail_resp.raise_for_status()
                detail = detail_resp.json()

                transcript = _format_transcript(detail)
                agent_name = detail.get("agent_id", "unknown_agent")
                status = detail.get("status", "unknown")
                start_time = detail.get("metadata", {}).get("start_time", "")

                ingest(
                    source="elevenlabs",
                    source_id=conv_id,
                    title=f"Call transcript ({agent_name}) — {start_time}",
                    content=transcript,
                    metadata={
                        "conversation_id": conv_id,
                        "agent_id": agent_name,
                        "status": status,
                        "start_time": start_time,
                        "call_duration": detail.get("metadata", {}).get("call_duration_secs"),
                    },
                )
                count += 1

            except Exception as e:
                logger.error(f"Failed to ingest transcript {conv_id}: {e}")

    logger.info(f"Ingested {count}/{len(conversations)} ElevenLabs transcripts")
    return count


def _format_transcript(detail: dict) -> str:
    """Format a conversation detail into a readable transcript."""
    transcript_parts: list[str] = []
    transcript_data = detail.get("transcript", [])

    for entry in transcript_data:
        role = entry.get("role", "unknown")
        message = entry.get("message", "")
        timestamp = entry.get("time_in_call_secs", "")
        ts_str = f" [{timestamp}s]" if timestamp else ""
        speaker = "Agent" if role == "agent" else "Caller"
        transcript_parts.append(f"{speaker}{ts_str}: {message}")

    if not transcript_parts:
        return "(no transcript available)"

    return "\n".join(transcript_parts)
