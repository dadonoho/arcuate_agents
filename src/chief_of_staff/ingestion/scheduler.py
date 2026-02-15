"""Background scheduler — periodically re-ingests data from all sources."""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

_task: asyncio.Task | None = None

SYNC_INTERVAL_SECONDS = 300  # 5 minutes


async def _sync_loop():
    """Runs forever, syncing all sources on an interval."""
    # Wait before first sync to let the server start up
    await asyncio.sleep(60)
    await run_sync()

    while True:
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)
        logger.info("=== Scheduled sync starting ===")
        await run_sync()


async def run_sync():
    """Run a single sync of all configured sources. Uses threads to avoid blocking."""
    loop = asyncio.get_event_loop()

    # Emails (sync function — run in thread)
    try:
        from chief_of_staff.ingestion.gmail import fetch_and_ingest_emails
        count = await loop.run_in_executor(
            None, lambda: fetch_and_ingest_emails(max_results=500, newer_than="3d")
        )
        logger.info(f"Synced {count} emails")
    except Exception as e:
        logger.error(f"Email sync failed: {e}")

    # Google Docs (sync function — run in thread)
    try:
        from chief_of_staff.ingestion.gdocs import fetch_and_ingest_docs
        count = await loop.run_in_executor(None, lambda: fetch_and_ingest_docs(max_results=50))
        logger.info(f"Synced {count} docs")
    except Exception as e:
        logger.error(f"Docs sync failed: {e}")

    # ElevenLabs (already async)
    try:
        from chief_of_staff.ingestion.elevenlabs import fetch_and_ingest_transcripts
        count = await fetch_and_ingest_transcripts(limit=50)
        logger.info(f"Synced {count} ElevenLabs transcripts")
    except Exception as e:
        logger.error(f"ElevenLabs sync failed: {e}")

    logger.info("=== Scheduled sync complete ===")


def start_scheduler():
    """Start the background sync loop."""
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_sync_loop())
        logger.info(f"Background scheduler started (interval: {SYNC_INTERVAL_SECONDS}s)")
