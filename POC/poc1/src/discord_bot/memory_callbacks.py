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
        """Handle session start: inject wake-up memory into system prompt.

        Args:
            channel_id: Discord channel ID
            user_id: Discord user ID
            author_name: Discord username
            bot_instance: Reference to the DiscordBot instance
        """
        if not self._memory_manager:
            return

        try:
            # Build a short "wake-up" prompt from recent/relevant memories
            wake_up = self._memory_manager.get_wake_up_prompt(
                user_id=user_id,
                channel_id=str(channel_id),
            )
            if wake_up:
                # Append wake-up context to the bot's system prompt
                bot_instance.system_prompt = f"{bot_instance.system_prompt}\n\n{wake_up}"
                # Rebuild the conversation history with updated system prompt
                # (first message is the system prompt)
                history = bot_instance._conversation_history.get(channel_id, [])
                if history and history[0].get("role") == "system":
                    history[0]["content"] = bot_instance.system_prompt
                logger.info(f"Injected wake-up memory for channel {channel_id}")
            else:
                logger.info(f"No wake-up memory for channel {channel_id}")
        except Exception as e:
            logger.warning(f"Failed to inject wake-up memory for channel {channel_id}: {e}")

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