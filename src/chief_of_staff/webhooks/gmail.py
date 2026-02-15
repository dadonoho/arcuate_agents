"""Gmail push notification webhook — triggers email ingestion on new messages."""

from __future__ import annotations

import base64
import json
import logging

from fastapi import APIRouter, Request

from chief_of_staff.ingestion.gmail import fetch_and_ingest_emails

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/gmail", tags=["gmail"])


@router.post("/push")
async def gmail_push_notification(request: Request) -> dict:
    """Handle Gmail push notifications via Google Cloud Pub/Sub.

    When a new email arrives in the Chief of Staff inbox, Google sends
    a push notification. We trigger an incremental email sync.

    Setup requires:
    1. Google Cloud Pub/Sub topic
    2. Push subscription pointing to this endpoint
    3. Gmail watch on the inbox
    """
    body = await request.json()

    # Decode the Pub/Sub message
    message = body.get("message", {})
    if message.get("data"):
        data = json.loads(base64.b64decode(message["data"]).decode())
        email_address = data.get("emailAddress", "unknown")
        history_id = data.get("historyId", "unknown")
        logger.info(f"Gmail push: new mail for {email_address}, historyId={history_id}")

    # Track webhook
    from chief_of_staff.agent.activity import log_activity, WEBHOOK_RECEIVED, EMAIL_INGESTED
    log_activity(
        agent_name="chief_of_staff",
        action_type=WEBHOOK_RECEIVED,
        action_detail="Gmail push notification",
        channel="gmail",
    )

    # Trigger incremental sync (fetch recent unread emails)
    count = fetch_and_ingest_emails(max_results=10, query="is:unread")
    logger.info(f"Ingested {count} new emails from push notification")

    if count > 0:
        log_activity(
            agent_name="chief_of_staff",
            action_type=EMAIL_INGESTED,
            action_detail=f"Push: ingested {count} new emails",
            channel="gmail",
            metadata={"count": count, "trigger": "push_notification"},
        )

    return {"status": "ok", "emails_ingested": count}
