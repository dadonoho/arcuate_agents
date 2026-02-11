"""Meeting recorder/transcript ingestion — Zoom and other meeting platforms.

This module provides manual ingestion for meeting transcripts.
For automated ingestion, see:
- zoom.py: Zoom cloud recording transcript puller
- zoom_client.py: Zoom API client (OAuth, recordings, users)
- recall_bot.py: Recall.ai meeting bot (auto-join, record, transcribe)
"""

from __future__ import annotations

import logging
from datetime import datetime

from chief_of_staff.knowledge.store import ingest

logger = logging.getLogger(__name__)


def ingest_meeting_transcript(
    title: str,
    transcript: str,
    meeting_date: str | None = None,
    attendees: list[str] | None = None,
    platform: str = "zoom",
) -> str:
    """Manually ingest a meeting transcript.

    Args:
        title: Meeting title/subject.
        transcript: Full transcript text.
        meeting_date: Date of the meeting (ISO format).
        attendees: List of attendee names.
        platform: Meeting platform ('zoom', 'google_meet', 'other').

    Returns:
        The document ID.
    """
    date = meeting_date or datetime.utcnow().isoformat()
    source_id = f"meeting_{date}_{title[:30]}"

    content = f"Meeting: {title}\nDate: {date}\nPlatform: {platform}\n"
    if attendees:
        content += f"Attendees: {', '.join(attendees)}\n"
    content += f"\n--- Transcript ---\n{transcript}"

    doc_id = ingest(
        source="meeting",
        source_id=source_id,
        title=f"Meeting: {title} ({date})",
        content=content,
        metadata={
            "meeting_date": date,
            "attendees": attendees or [],
            "platform": platform,
        },
    )

    logger.info(f"Ingested meeting transcript: {title} -> {doc_id}")
    return doc_id
