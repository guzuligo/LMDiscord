"""
Delay Processor Module

Handles delayed message processing for Discord bot.
Provides configurable delays before processing messages
to allow for follow-up message batching.
"""

import asyncio
import logging
import sys
from typing import Dict, List, Any, Callable, Optional

logger = logging.getLogger(__name__)


class DelayProcessor:
    """Processes messages after a configurable delay."""

    def __init__(self, default_delay: int = 5):
        """Initialize delay processor.

        Args:
            default_delay: Default delay in seconds before processing (default: 5)
        """
        self._default_delay = default_delay

    @property
    def default_delay(self) -> int:
        """Get the default delay."""
        return self._default_delay

    @default_delay.setter
    def default_delay(self, value: int) -> None:
        """Set the default delay.

        Args:
            value: Delay in seconds
        """
        self._default_delay = value

    async def process_with_delay(
        self,
        delay: Optional[int],
        channel_id: int,
        author_display: str,
        content: str,
        handler_callback: Any,
        *args
    ) -> None:
        """Wait for a delay, then call the handler callback.

        Args:
            delay: Delay in seconds (uses default if None)
            channel_id: Discord channel ID
            author_display: Author's display name
            content: Message content (truncated for logging)
            handler_callback: Async callable to invoke after delay
            *args: Arguments to pass to the handler callback
        """
        try:
            actual_delay = delay if delay is not None else self._default_delay
            logger.info(f"Waiting {actual_delay} seconds before processing: {content[:50]}...")

            await asyncio.sleep(actual_delay)

            # Check if something is already processing
            bot_instance = None
            for obj in sys.modules.get('__main__', {}).globals().values():
                if hasattr(obj, '_processing_lock'):
                    bot_instance = obj
                    break

            if bot_instance and bot_instance._processing_lock.get(channel_id, False):
                logger.info("Skipping delayed processing, another message is being processed")
                return

            await handler_callback(*args)

        except Exception as e:
            logger.error(f"Error in delayed processing: {e}", exc_info=True)

    async def process_active_session_with_delay(
        self,
        message: Any,
        content: str,
        channel_id: int,
        author_name: str,
        author_display: str,
        processing_lock: Dict[int, bool],
        pending_messages: Dict[int, List[Dict[str, str]]],
        handler_callback: Any,
        delay: Optional[int] = None,
        image_attachments: Optional[List[Dict]] = None
    ) -> None:
        """Process an active session message after a delay.

        Sets the lock BEFORE the delay so that subsequent messages arriving
        during the delay are properly queued and processed as a batch.

        Args:
            message: The discord.Message object
            content: The message content
            channel_id: Discord channel ID
            author_name: Author's username
            author_display: Author's display name
            processing_lock: Dict of channel_id -> processing lock status
            pending_messages: Dict of channel_id -> list of pending message dicts
            handler_callback: Async callable for batch processing
            delay: Delay in seconds (uses default if None)
            image_attachments: List of image attachment dicts
        """
        try:
            actual_delay = delay if delay is not None else self._default_delay
            logger.info(f"Waiting {actual_delay} seconds before processing active session: {content[:50]}...")

            # Set lock BEFORE delay so subsequent messages get queued
            processing_lock[channel_id] = True

            await asyncio.sleep(actual_delay)

            logger.info("Delay complete, processing active session message now")

            # Collect pending messages that arrived while waiting
            pending = pending_messages.pop(channel_id, [])

            if pending:
                logger.info(f"Processing {len(pending)} queued message(s) for channel {channel_id}")

            # Merge attachment info from pending messages
            merged_attachments = list(image_attachments) if image_attachments else []
            for p in pending:
                if isinstance(p, dict) and "image_attachments" in p:
                    merged_attachments.extend(p["image_attachments"])
            
            await handler_callback(
                message, content, channel_id, author_name, author_display,
                None, pending_messages=pending,
                image_attachments=merged_attachments if merged_attachments else None
            )

        except Exception as e:
            logger.error(f"Error in delayed active session processing: {e}", exc_info=True)
            processing_lock[channel_id] = False
