"""
Memory Callbacks Module

Handles memory-related callbacks for session lifecycle events:
- _on_session_started: Inject wake-up memory into system prompt
- _on_session_ended: Save conversation to memory
- _on_session_cleanup: Prune low-importance memories
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MemoryCallbackHandler:
    """Handles memory callbacks for session lifecycle events."""

    def __init__(
        self,
        memory_manager: Optional[Any] = None,
        memory_tool: Optional[Any] = None,
        session_manager: Optional[Any] = None
    ):
        """Initialize memory callback handler.

        Args:
            memory_manager: MemoryManager instance for saving/recalling memories
            memory_tool: MemoryTool instance for memory operations
            session_manager: SessionManager instance for session info
        """
        self._memory_manager = memory_manager
        self._memory_tool = memory_tool
        self._session_manager = session_manager

    def set_memory_manager(self, memory_manager: Any) -> None:
        """Set the memory manager instance."""
        self._memory_manager = memory_manager

    def set_memory_tool(self, memory_tool: Any) -> None:
        """Set the memory tool instance."""
        self._memory_tool = memory_tool

    def set_session_manager(self, session_manager: Any) -> None:
        """Set the session manager instance."""
        self._session_manager = session_manager

    async def on_session_started(
        self,
        channel_id: int,
        user_id: str,
        author_name: str,
        bot_instance: Any
    ) -> None:
        """Handle session start: inject wake-up memory and recent channel context.

        This implements the session start context initialization for FEAT-008:
        1. Inject wake-up memory into system prompt
        2. Fetch recent channel messages and generate a context summary
        3. Add the summary to the system prompt for better context awareness

        Args:
            channel_id: Discord channel ID
            user_id: Discord user ID
            author_name: Discord username
            bot_instance: Reference to the DiscordBot instance
        """
        if not self._memory_manager:
            return

        try:
            # Step 1: Build a short "wake-up" prompt from recent/relevant memories
            wake_up = self._memory_manager.get_wake_up_prompt(
                user_id=user_id,
                channel_id=str(channel_id),
            )

            # Step 2: Fetch recent channel messages for context (FEAT-008)
            channel_context = None
            try:
                channel_context = await self._fetch_recent_channel_context(
                    bot_instance, channel_id
                )
            except Exception as ctx_err:
                logger.warning(f"Failed to fetch recent channel context for channel {channel_id}: {ctx_err}")

            # Step 3: Combine wake-up memory + channel context into system prompt
            combined_context = wake_up or ""
            if channel_context:
                combined_context = f"{combined_context}\n\n{channel_context}" if combined_context else channel_context

            if combined_context:
                # Append context to the bot's system prompt
                bot_instance.system_prompt = f"{bot_instance.system_prompt}\n\n{combined_context}"
                # Rebuild the conversation history with updated system prompt
                # (first message is the system prompt)
                history = bot_instance._conversation_history.get(channel_id, [])
                if history and history[0].get("role") == "system":
                    history[0]["content"] = bot_instance.system_prompt
                logger.info(f"Injected session context for channel {channel_id}")
            else:
                logger.info(f"No session context for channel {channel_id}")
        except Exception as e:
            logger.warning(f"Failed to inject session context for channel {channel_id}: {e}")

    async def _fetch_recent_channel_context(
        self,
        bot_instance: Any,
        channel_id: int,
        recent_count: int = 10
    ) -> Optional[str]:
        """Fetch recent channel messages and generate a context summary.

        This implements the session start context initialization for FEAT-008:
        When a new session starts, we fetch the last N messages from the
        channel and generate a concise summary to provide the bot with
        recent conversation context.

        Args:
            bot_instance: Reference to the DiscordBot instance
            channel_id: Discord channel ID
            recent_count: Number of recent messages to fetch (default 10)

        Returns:
            Formatted context string, or None if no context available
        """
        import discord
        from datetime import datetime, timedelta, timezone

        # Find the channel
        target_channel = None
        if bot_instance.client and bot_instance.client.is_ready():
            target_channel = bot_instance.client.get_channel(channel_id)
            if target_channel is None:
                # Try to get channel from guild
                for guild in bot_instance.client.guilds:
                    if guild is None:
                        continue
                    target_channel = guild.get_channel(channel_id) or guild.get_text_channel(channel_id)
                    if target_channel:
                        break

        if target_channel is None:
            logger.debug(f"Channel {channel_id} not accessible for context fetch")
            return None

        if not hasattr(target_channel, 'history'):
            logger.debug(f"Channel {channel_id} does not support history fetch")
            return None

        # Fetch recent messages
        recent_messages = []
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)  # Last 24 hours only

        try:
            async for msg in target_channel.history(limit=recent_count * 2):
                # Skip bot's own messages and messages older than 24 hours
                if msg.author == bot_instance.client.user:
                    continue
                if msg.created_at < cutoff_time:
                    continue

                # Format message
                author = msg.author.display_name or msg.author.name
                content = (msg.content or "").strip()
                if not content and not msg.attachments:
                    continue

                # Truncate very long messages
                if len(content) > 300:
                    content = content[:297] + "..."

                recent_messages.append({
                    "author": author,
                    "content": content,
                    "timestamp": msg.created_at.isoformat(),
                    "has_attachments": len(list(msg.attachments)) > 0
                })

                if len(recent_messages) >= recent_count:
                    break

        except Exception as e:
            logger.warning(f"Failed to fetch recent messages from channel {channel_id}: {e}")
            return None

        if not recent_messages:
            return None

        # Format context block
        context_lines = []
        context_lines.append(f"📋 [RECENT CHANNEL CONTEXT: Last {len(recent_messages)} messages]")

        for i, msg in enumerate(recent_messages, 1):
            has_media = " [media]" if msg["has_attachments"] else ""
            context_lines.append(
                f"  [{i}] {msg['author']}: {msg['content']}{has_media}"
            )

        context_text = "\n".join(context_lines)
        logger.info(f"Fetched {len(recent_messages)} recent messages for channel {channel_id} context")
        return context_text

    async def on_session_ended(
        self,
        channel_id: int,
        user_id: str,
        author_name: str,
        bot_instance: Any
    ) -> None:
        """Handle session end: save conversation to memory.

        Args:
            channel_id: Discord channel ID
            user_id: Discord user ID
            author_name: Discord username
            bot_instance: Reference to the DiscordBot instance
        """
        if not self._memory_manager:
            return

        try:
            history = bot_instance._conversation_history.get(channel_id, [])
            if history:
                # Save the conversation to memory
                self._memory_manager.save_conversation(
                    conversation=history,
                    user_id=user_id,
                    channel_id=str(channel_id),
                    author_name=author_name,
                )
                logger.info(f"Saved conversation to memory for channel {channel_id}")
            else:
                logger.info(f"No conversation history to save for channel {channel_id}")
        except Exception as e:
            logger.warning(f"Failed to save conversation for channel {channel_id}: {e}")

    async def on_session_cleanup(
        self,
        channel_id: int,
        user_id: Optional[str] = None,
        author_name: Optional[str] = None,
    ) -> None:
        """Handle session cleanup: prune low-importance memories.

        Args:
            channel_id: Discord channel ID
            user_id: Discord user ID
            author_name: Discord username
        """
        if not self._memory_manager:
            return

        try:
            self._memory_manager.prune_low_importance_memories(
                channel_id=str(channel_id),
                user_id=user_id,
            )
            logger.info(f"Pruned low-importance memories for channel {channel_id}")
        except Exception as e:
            logger.warning(f"Failed to prune memories for channel {channel_id}: {e}")