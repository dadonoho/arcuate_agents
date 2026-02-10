"""Twilio SMS — send and receive text messages."""

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


async def send_sms(to: str, body: str) -> str:
    """Send an SMS message via Twilio.

    Returns the message SID on success.
    """
    client = get_twilio_client()

    # Twilio has a 1600 char limit per SMS segment; split if needed
    if len(body) > 1500:
        segments = [body[i : i + 1500] for i in range(0, len(body), 1500)]
    else:
        segments = [body]

    sids = []
    for segment in segments:
        message = client.messages.create(
            body=segment,
            from_=settings.twilio_phone_number,
            to=to,
        )
        sids.append(message.sid)
        logger.info(f"SMS sent to {to}: SID={message.sid}")

    return sids[0] if len(sids) == 1 else f"Sent {len(sids)} segments"
