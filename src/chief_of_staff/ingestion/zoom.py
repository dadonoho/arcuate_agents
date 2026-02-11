"""Zoom cloud recording ingestion — pull meeting transcripts into the knowledge base.

Fetches cloud recordings from Zoom, extracts transcripts (VTT or audio transcript),
and ingests them into the knowledge store for semantic search.

Supports:
1. Auto-generated Zoom transcripts (from cloud recordings)
2. Audio transcripts (VTT files attached to recordings)
3. Chat logs from meetings
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any

from chief_of_staff.ingestion.zoom_client import (
    get_recording_transcript,
    list_recordings,
    list_users,
)
from chief_of_staff.knowledge.store import ingest

logger = logging.getLogger(__name__)


async def fetch_and_ingest_recordings(
    days_back: int = 30,
    user_emails: list[str] | None = None,
) -> int:
    """Fetch Zoom cloud recordings and ingest transcripts.

    Args:
        days_back: How many days back to look for recordings.
        user_emails: Specific user emails to fetch for. If None, fetches for all users.

    Returns:
        Number of recordings ingested.
    """
    from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    to_date = datetime.utcnow().strftime("%Y-%m-%d")

    # Determine which users to fetch for
    if user_emails:
        user_ids = user_emails
    else:
        users = await list_users()
        user_ids = [u["id"] for u in users]
        logger.info(f"Found {len(user_ids)} Zoom users")

    total_ingested = 0

    for user_id in user_ids:
        try:
            recordings = await list_recordings(
                user_id=user_id,
                from_date=from_date,
                to_date=to_date,
            )
            logger.info(f"Found {len(recordings)} recordings for user {user_id}")

            for meeting in recordings:
                count = await _ingest_meeting_recording(meeting)
                total_ingested += count

        except Exception as e:
            logger.error(f"Failed to fetch recordings for user {user_id}: {e}")

    logger.info(f"Total Zoom recordings ingested: {total_ingested}")
    return total_ingested


async def _ingest_meeting_recording(meeting: dict[str, Any]) -> int:
    """Ingest a single meeting's recordings and transcripts.

    Returns number of items ingested (transcripts + chat logs).
    """
    meeting_id = meeting.get("id", meeting.get("uuid", "unknown"))
    topic = meeting.get("topic", "Untitled Meeting")
    start_time = meeting.get("start_time", "")
    duration = meeting.get("duration", 0)
    host_email = meeting.get("host_email", "unknown")
    participants = meeting.get("total_size", 0)

    recording_files = meeting.get("recording_files", [])
    count = 0

    for rec_file in recording_files:
        file_type = rec_file.get("file_type", "")
        recording_type = rec_file.get("recording_type", "")
        download_url = rec_file.get("download_url", "")
        status = rec_file.get("status", "")

        if status != "completed" or not download_url:
            continue

        # We want transcript files (TRANSCRIPT or TIMELINE) and chat files
        if recording_type in ("audio_transcript", "chat_file") or file_type == "TRANSCRIPT":
            try:
                raw_content = await get_recording_transcript(download_url)

                if file_type == "TRANSCRIPT" or recording_type == "audio_transcript":
                    transcript = parse_vtt_transcript(raw_content)
                    source_id = f"zoom_transcript_{meeting_id}"
                    title = f"Zoom Meeting: {topic}"
                    content = _format_meeting_content(
                        topic=topic,
                        start_time=start_time,
                        duration=duration,
                        host_email=host_email,
                        transcript=transcript,
                    )
                elif recording_type == "chat_file":
                    source_id = f"zoom_chat_{meeting_id}"
                    title = f"Zoom Chat: {topic}"
                    content = _format_chat_content(
                        topic=topic,
                        start_time=start_time,
                        chat_log=raw_content,
                    )
                else:
                    continue

                ingest(
                    source="meeting",
                    source_id=source_id,
                    title=title,
                    content=content,
                    metadata={
                        "platform": "zoom",
                        "meeting_id": str(meeting_id),
                        "topic": topic,
                        "start_time": start_time,
                        "duration_minutes": duration,
                        "host_email": host_email,
                        "recording_type": recording_type,
                    },
                )
                count += 1
                logger.info(f"Ingested Zoom {recording_type}: {topic} ({start_time})")

            except Exception as e:
                logger.error(f"Failed to ingest recording {recording_type} for meeting {meeting_id}: {e}")

    return count


def parse_vtt_transcript(vtt_content: str) -> str:
    """Parse a WebVTT transcript into clean readable text.

    VTT format:
        WEBVTT

        00:00:01.000 --> 00:00:05.000
        Speaker Name: Hello everyone, welcome to the meeting.

    Returns:
        Clean transcript with timestamps and speaker names.
    """
    lines = vtt_content.strip().split("\n")
    transcript_parts: list[str] = []
    current_speaker = ""

    # Skip the WEBVTT header
    i = 0
    while i < len(lines) and not re.match(r"\d{2}:\d{2}:\d{2}", lines[i]):
        i += 1

    while i < len(lines):
        line = lines[i].strip()

        # Timestamp line: 00:00:01.000 --> 00:00:05.000
        ts_match = re.match(r"(\d{2}:\d{2}:\d{2})\.\d+ --> ", line)
        if ts_match:
            timestamp = ts_match.group(1)
            # Next line(s) are the speech content
            i += 1
            speech_lines = []
            while i < len(lines) and lines[i].strip():
                speech_lines.append(lines[i].strip())
                i += 1

            speech = " ".join(speech_lines)

            # Extract speaker name if present (format: "Speaker Name: text")
            speaker_match = re.match(r"^(.+?):\s*(.+)$", speech)
            if speaker_match:
                speaker = speaker_match.group(1)
                text = speaker_match.group(2)
                if speaker != current_speaker:
                    current_speaker = speaker
                    transcript_parts.append(f"\n{speaker} [{timestamp}]:")
                transcript_parts.append(f"  {text}")
            elif speech:
                transcript_parts.append(f"  [{timestamp}] {speech}")

        i += 1

    return "\n".join(transcript_parts).strip() if transcript_parts else vtt_content


def _format_meeting_content(
    topic: str,
    start_time: str,
    duration: int,
    host_email: str,
    transcript: str,
) -> str:
    """Format a meeting transcript for ingestion."""
    return (
        f"Meeting: {topic}\n"
        f"Date: {start_time}\n"
        f"Duration: {duration} minutes\n"
        f"Host: {host_email}\n"
        f"Platform: Zoom\n"
        f"\n--- Transcript ---\n"
        f"{transcript}"
    )


def _format_chat_content(
    topic: str,
    start_time: str,
    chat_log: str,
) -> str:
    """Format a meeting chat log for ingestion."""
    return (
        f"Meeting Chat: {topic}\n"
        f"Date: {start_time}\n"
        f"Platform: Zoom\n"
        f"\n--- Chat Log ---\n"
        f"{chat_log}"
    )
