"""Gmail ingestion — pull emails from the Chief of Staff inbox into the knowledge base."""

from __future__ import annotations

import base64
import logging
from datetime import datetime
from typing import Any

from chief_of_staff.communication._google_auth import get_gmail_service
from chief_of_staff.knowledge.store import ingest

logger = logging.getLogger(__name__)


def fetch_and_ingest_emails(max_results: int = 500, query: str = "", newer_than: str = "") -> int:
    """Fetch recent emails and ingest them into the knowledge base.

    Paginates through all results up to max_results. Captures full email
    context including To, From, CC, BCC, Reply-To, and thread IDs.

    Args:
        max_results: Maximum number of emails to fetch (paginates automatically).
        query: Gmail search query (e.g., 'from:client@example.com').
        newer_than: Gmail newer_than filter (e.g., '1d' for last day, '2h' for last 2 hours).

    Returns:
        Number of emails ingested.
    """
    service = get_gmail_service()

    full_query = query
    if newer_than:
        full_query = f"newer_than:{newer_than} {query}".strip()

    logger.info(f"Fetching emails with query: '{full_query}', max_results={max_results}")

    # Paginate through all results
    all_messages = []
    page_token = None
    while len(all_messages) < max_results:
        batch_size = min(100, max_results - len(all_messages))
        results = service.users().messages().list(
            userId="me",
            maxResults=batch_size,
            q=full_query,
            pageToken=page_token,
        ).execute()

        batch = results.get("messages", [])
        if not batch:
            break
        all_messages.extend(batch)

        page_token = results.get("nextPageToken")
        if not page_token:
            break

    logger.info(f"Found {len(all_messages)} emails matching query")
    count = 0

    for msg_ref in all_messages:
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
            cc_addr = headers.get("cc", "")
            bcc_addr = headers.get("bcc", "")
            reply_to = headers.get("reply-to", "")
            date = headers.get("date", "")
            message_id = headers.get("message-id", "")
            in_reply_to = headers.get("in-reply-to", "")
            thread_id = msg.get("threadId", "")
            labels = msg.get("labelIds", [])

            body = _extract_body(msg["payload"])

            # Build full email context with all participants
            content_parts = [
                f"From: {from_addr}",
                f"To: {to_addr}",
            ]
            if cc_addr:
                content_parts.append(f"CC: {cc_addr}")
            if bcc_addr:
                content_parts.append(f"BCC: {bcc_addr}")
            if reply_to:
                content_parts.append(f"Reply-To: {reply_to}")
            content_parts.extend([
                f"Date: {date}",
                f"Subject: {subject}",
                "",
                body,
            ])
            content = "\n".join(content_parts)

            metadata = {
                "from": from_addr,
                "to": to_addr,
                "cc": cc_addr,
                "bcc": bcc_addr,
                "reply_to": reply_to,
                "date": date,
                "subject": subject,
                "gmail_id": msg_ref["id"],
                "thread_id": thread_id,
                "in_reply_to": in_reply_to,
                "labels": ",".join(labels),
            }

            ingest(
                source="gmail",
                source_id=msg_ref["id"],
                title=f"Email: {subject}",
                content=content,
                metadata=metadata,
            )
            count += 1

        except Exception as e:
            logger.error(f"Failed to ingest email {msg_ref['id']}: {e}")

    logger.info(f"Ingested {count}/{len(all_messages)} emails")
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
