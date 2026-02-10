"""Gmail API — send emails on behalf of the Chief of Staff."""

from __future__ import annotations

import base64
import logging
from email.mime.text import MIMEText

from chief_of_staff.communication._google_auth import get_gmail_service

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, body: str) -> str:
    """Send an email via the Gmail API.

    Returns the message ID on success.
    """
    service = get_gmail_service()

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    result = service.users().messages().send(
        userId="me",
        body={"raw": raw},
    ).execute()

    msg_id = result.get("id", "unknown")
    logger.info(f"Email sent to {to}, subject='{subject}', id={msg_id}")
    return msg_id
