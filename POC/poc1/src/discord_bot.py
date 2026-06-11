"""
Discord Bot Module - Backward Compatibility Wrapper

This module is now a thin wrapper that imports DiscordBot from the
modular src/discord_bot/ package for backward compatibility.

All implementation logic has been moved to:
- src/discord_bot/bot_core.py        - Main DiscordBot class
- src/discord_bot/message_handler.py  - Message processing
- src/discord_bot/session_manager.py  - Session management
- src/discord_bot/token_tracker.py    - Token usage tracking
- src/discord_bot/typing_indicator.py - Typing indicators
- src/discord_bot/delay_processor.py  - Delayed processing
"""

# Re-export DiscordBot for backward compatibility
from src.discord_bot.bot_core import DiscordBot

__all__ = ["DiscordBot"]
