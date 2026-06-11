"""
Typing Indicator Module

Handles showing Discord typing indicators ("Bot is typing...")
using the discord.py 2.x async typing() context manager.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TypingIndicator:
    """Manages Discord typing indicators for the bot."""

    @staticmethod
    async def show(channel: Any) -> None:
        """Show typing indicator in a Discord channel.

        Uses the async typing() context manager (discord.py 2.x API).
        The typing indicator shows for ~10 seconds by default.

        Args:
            channel: The Discord channel object to show typing in
        """
        try:
            async with channel.typing():
                # The typing indicator is shown while inside this context manager
                # It lasts ~10 seconds. We just need to enter the context to trigger it.
                pass
            logger.info(f"Typing indicator shown for channel {channel.id}")
        except Exception as e:
            logger.warning(f"Could not send typing indicator: {e}")