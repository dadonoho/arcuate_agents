"""Twilio messaging — send SMS or WhatsApp messages."""

from __future__ import annotations

import logging

from twilio.rest import Client

from chief_of_staff.config import settings

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_twilio_client() -> Client:
    global _client
    if _client is None:
        _client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    return _client


def _wrap_number(phone: str) -> str:
    """Wrap a phone number with the whatsapp: prefix if using WhatsApp channel."""
    if settings.messaging_channel == "whatsapp":
        if not phone.startswith("whatsapp:"):
            return f"whatsapp:{phone}"
    return phone


async def send_sms(to: str, body: str) -> str:
    """Send a message via Twilio (SMS or WhatsApp based on config).

    Returns the message SID on success.
    """
    client = get_twilio_client()

    from_number = _wrap_number(settings.twilio_phone_number)
    to_number = _wrap_number(to)

    # WhatsApp supports longer messages than SMS, but still split at 4096 chars
    max_len = 4096 if settings.messaging_channel == "whatsapp" else 1500
    if len(body) > max_len:
        segments = [body[i : i + max_len] for i in range(0, len(body), max_len)]
    else:
        segments = [body]

    sids = []
    for segment in segments:
        message = client.messages.create(
            body=segment,
            from_=from_number,
            to=to_number,
        )
        sids.append(message.sid)
        logger.info(f"Message sent to {to} via {settings.messaging_channel}: SID={message.sid}")

    # Track outbound SMS/WhatsApp
    try:
        from chief_of_staff.agent.activity import log_activity, SMS_SENT
        log_activity(
            agent_name="chief_of_staff",
            action_type=SMS_SENT,
            action_detail=f"To {to}: {body[:200]}",
            channel=settings.messaging_channel,
            user_id=to,
            metadata={"sids": sids, "segments": len(segments)},
        )
    except Exception:
        pass  # Don't let tracking failures break messaging

    return sids[0] if len(sids) == 1 else f"Sent {len(sids)} segments"
