"""Gmail ingestion — pull emails from the Chief of Staff inbox into the knowledge base."""

from __future__ import annotations

import base64
import logging
from datetime import datetime
from typing import Any

from chief_of_staff.communication._google_auth import get_gmail_service
from chief_of_staff.knowledge.store import ingest

logger = logging.getLogger(__name__)


def fetch_and_ingest_emails(max_results: int = 100, query: str = "") -> int:
    """Fetch recent emails and ingest them into the knowledge base.

    Args:
        max_results: Maximum number of emails to fetch.
        query: Gmail search query (e.g., 'from:client@example.com').

    Returns:
        Number of emails ingested.
    """
    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        maxResults=max_results,
        q=query,
    ).execute()

    messages = results.get("messages", [])
    count = 0

    for msg_ref in messages:
        try:
            msg = service.users().messages().get(
                userId="me",
                id=msg_ref["id"],
                format="full",
            ).execute()

            headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
            subject = headers.get("subject", "(no subject)")
            from_addr = headers.get("from", "unknown")
            to_addr = headers.get("to", "unknown")
            date = headers.get("date", "")

            body = _extract_body(msg["payload"])

            content = f"From: {from_addr}\nTo: {to_addr}\nDate: {date}\nSubject: {subject}\n\n{body}"

            ingest(
                source="gmail",
                source_id=msg_ref["id"],
                title=f"Email: {subject}",
                content=content,
                metadata={
                    "from": from_addr,
                    "to": to_addr,
                    "date": date,
                    "subject": subject,
                    "gmail_id": msg_ref["id"],
                },
            )
            count += 1

        except Exception as e:
            logger.error(f"Failed to ingest email {msg_ref['id']}: {e}")

    logger.info(f"Ingested {count}/{len(messages)} emails")
    return count


def _extract_body(payload: dict[str, Any]) -> str:
    """Extract plain text body from a Gmail message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    # Multipart — recurse into parts
    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")

    # Fallback: try first part with data
    for part in parts:
        body = _extract_body(part)
        if body:
            return body

    return "(no text body)"
