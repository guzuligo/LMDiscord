"""
Discord bot package - Modular implementation.

This package contains the Discord bot components:
- bot_core: Core bot class, initialization, connection management
- message_handler: Message processing and LM Studio interaction
- session_manager: Session lifecycle and state management
- typing_indicator: Discord typing indicator logic
- delay_processor: Delayed message processing
- token_tracker: Token usage tracking for web UI sync
"""

from src.discord_bot.bot_core import DiscordBot

__all__ = ["DiscordBot"]
