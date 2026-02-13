"""Discord bot interface — founders message the Chief of Staff via Discord."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import discord

from chief_of_staff.config import settings

logger = logging.getLogger(__name__)




class ChiefOfStaffBot(discord.Client):
    """Discord bot that connects to the Claude-powered Chief of Staff agent."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self._agent = None

    def _get_agent(self):
        if self._agent is None:
            from chief_of_staff.agent.core import get_agent
            self._agent = get_agent()
        return self._agent

    async def on_ready(self):
        logger.info(f"Discord bot connected as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} server(s)")

    async def on_message(self, message: discord.Message):
        # Don't respond to ourselves
        if message.author == self.user:
            return

        # Don't respond to other bots
        if message.author.bot:
            return

        # Respond to DMs or messages that mention the bot or are in a designated channel
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = self.user in message.mentions
        channel_name = getattr(message.channel, "name", "")
        is_agent_channel = channel_name in settings.discord_channels

        if not (is_dm or is_mentioned or is_agent_channel):
            return

        # Strip the bot mention from the message if present
        content = message.content
        if is_mentioned:
            content = content.replace(f"<@{self.user.id}>", "").strip()

        if not content:
            return

        logger.info(f"Discord message from {message.author}: {content[:100]}...")

        # Show typing indicator while processing
        async with message.channel.typing():
            try:
                agent = self._get_agent()
                # Build conversation history from recent channel messages
                history = await self._build_history(message.channel)

                response = await agent.respond(
                    user_message=content,
                    conversation_history=history,
                    founder_phone=f"discord:{message.author.id}",
                )

                # Discord has a 2000 char limit per message
                if len(response) <= 2000:
                    await message.reply(response)
                else:
                    # Split into chunks at newlines
                    chunks = _split_message(response)
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            await message.reply(chunk)
                        else:
                            await message.channel.send(chunk)

            except Exception as e:
                logger.error(f"Error processing Discord message: {e}", exc_info=True)
                await message.reply("Something went wrong processing your message. Please try again.")

    async def _build_history(self, channel, limit: int = 10) -> list[dict[str, Any]]:
        """Build conversation history from recent messages in the channel."""
        history = []
        messages = []

        async for msg in channel.history(limit=limit + 1):  # +1 to skip current
            messages.append(msg)

        # Reverse to chronological order, skip the current message
        for msg in reversed(messages[1:]):
            if msg.author == self.user:
                history.append({"role": "assistant", "content": msg.content})
            elif not msg.author.bot:
                content = msg.content.replace(f"<@{self.user.id}>", "").strip()
                if content:
                    history.append({"role": "user", "content": content})

        return history


def _split_message(text: str, max_len: int = 2000) -> list[str]:
    """Split a long message into chunks respecting Discord's limit."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break

        # Try to split at a newline
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len

        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    return chunks


_bot: ChiefOfStaffBot | None = None


def get_discord_bot() -> ChiefOfStaffBot:
    """Get the singleton Discord bot instance."""
    global _bot
    if _bot is None:
        _bot = ChiefOfStaffBot()
    return _bot


async def start_discord_bot():
    """Start the Discord bot (runs forever)."""
    token = settings.discord_bot_token
    if not token:
        logger.warning("DISCORD_BOT_TOKEN not set — Discord bot disabled")
        return

    bot = get_discord_bot()
    logger.info("Starting Discord bot...")
    await bot.start(token)
