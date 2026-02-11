"""Twilio webhook handlers for incoming SMS and WhatsApp messages."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Form, Response

from chief_of_staff.agent.core import get_agent
from chief_of_staff.communication.sms import send_sms
from chief_of_staff.knowledge.database import get_recent_conversations, log_conversation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/twilio", tags=["twilio"])


def _strip_whatsapp_prefix(phone: str) -> str:
    """Strip whatsapp: prefix for clean storage, keep raw E.164 number."""
    return phone.replace("whatsapp:", "")


@router.post("/sms")
async def incoming_sms(
    From: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(""),
) -> Response:
    """Handle incoming SMS or WhatsApp message from Twilio.

    This is the primary founder interface — message the Chief of Staff,
    get an AI-powered response with full company context.
    """
    # Normalize phone number (strip whatsapp: prefix for DB lookups)
    raw_from = From
    clean_phone = _strip_whatsapp_prefix(From)
    is_whatsapp = raw_from.startswith("whatsapp:")

    logger.info(f"Incoming {'WhatsApp' if is_whatsapp else 'SMS'} from {clean_phone}: {Body[:100]}...")

    # Log the inbound message
    conv_id = str(uuid.uuid4())
    log_conversation(
        conv_id=conv_id,
        founder_phone=clean_phone,
        direction="inbound",
        message=Body,
    )

    # Build conversation history from recent messages
    recent = get_recent_conversations(clean_phone, limit=10)
    history = []
    for msg in reversed(recent):
        history.append({"role": "user", "content": msg["message"]})
        if msg.get("response"):
            history.append({"role": "assistant", "content": msg["response"]})

    # Get agent response
    agent = get_agent()
    response_text = await agent.respond(
        user_message=Body,
        conversation_history=history[:-1],  # exclude current message (added by agent)
        founder_phone=clean_phone,
    )

    # Log the response
    log_conversation(
        conv_id=str(uuid.uuid4()),
        founder_phone=clean_phone,
        direction="outbound",
        message=response_text,
    )

    # Send response back via the same channel (WhatsApp or SMS)
    await send_sms(to=clean_phone, body=response_text)

    # Return empty TwiML (we're sending the response ourselves)
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="text/xml",
    )
