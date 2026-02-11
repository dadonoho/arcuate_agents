#!/usr/bin/env python3
"""One-time initial ingestion — pull all historical data into the knowledge base.

Run this after setting up credentials to backfill:
- All emails from the Chief of Staff inbox
- All Google Docs from the shared drive
- All ElevenLabs call transcripts
- All Zoom cloud recording transcripts

Usage:
    python scripts/ingest_initial.py
    python scripts/ingest_initial.py --emails-only
    python scripts/ingest_initial.py --docs-only
    python scripts/ingest_initial.py --transcripts-only
    python scripts/ingest_initial.py --zoom-only
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chief_of_staff.knowledge.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Initial data ingestion")
    parser.add_argument("--emails-only", action="store_true")
    parser.add_argument("--docs-only", action="store_true")
    parser.add_argument("--transcripts-only", action="store_true")
    parser.add_argument("--zoom-only", action="store_true")
    parser.add_argument("--max-emails", type=int, default=500)
    parser.add_argument("--max-docs", type=int, default=100)
    parser.add_argument("--max-transcripts", type=int, default=200)
    parser.add_argument("--zoom-days-back", type=int, default=90)
    parser.add_argument("--docs-folder-id", type=str, default=None)
    args = parser.parse_args()

    # Initialize database
    init_db()

    do_all = not (args.emails_only or args.docs_only or args.transcripts_only or args.zoom_only)

    if do_all or args.emails_only:
        logger.info("=== Ingesting emails ===")
        from chief_of_staff.ingestion.gmail import fetch_and_ingest_emails

        count = fetch_and_ingest_emails(max_results=args.max_emails)
        logger.info(f"Emails ingested: {count}")

    if do_all or args.docs_only:
        logger.info("=== Ingesting Google Docs ===")
        from chief_of_staff.ingestion.gdocs import fetch_and_ingest_docs

        count = fetch_and_ingest_docs(
            folder_id=args.docs_folder_id,
            max_results=args.max_docs,
        )
        logger.info(f"Docs ingested: {count}")

    if do_all or args.transcripts_only:
        logger.info("=== Ingesting ElevenLabs transcripts ===")
        from chief_of_staff.ingestion.elevenlabs import fetch_and_ingest_transcripts

        count = await fetch_and_ingest_transcripts(limit=args.max_transcripts)
        logger.info(f"Transcripts ingested: {count}")

    if do_all or args.zoom_only:
        logger.info("=== Ingesting Zoom cloud recordings ===")
        from chief_of_staff.ingestion.zoom import fetch_and_ingest_recordings

        count = await fetch_and_ingest_recordings(days_back=args.zoom_days_back)
        logger.info(f"Zoom recordings ingested: {count}")

    logger.info("=== Initial ingestion complete ===")


if __name__ == "__main__":
    asyncio.run(main())
