"""Voice communication via Twilio + ElevenLabs (placeholder for future implementation)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def initiate_call(to: str, script: str | None = None) -> str:
    """Initiate an outbound voice call.

    This will use Twilio for telephony and ElevenLabs for voice synthesis.
    Full implementation pending — requires TwiML webhook setup.
    """
    # TODO: Implement with Twilio Voice + ElevenLabs TTS
    # 1. Generate TwiML that streams to ElevenLabs
    # 2. Use Twilio REST API to initiate the call
    # 3. Handle call status callbacks
    logger.warning("Voice calls not yet implemented")
    return "voice_not_implemented"
