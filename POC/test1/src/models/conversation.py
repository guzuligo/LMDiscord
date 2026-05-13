"""
Conversation State Model Module

This module defines the data model for managing conversation state with LM Studio.
Each conversation is tied to a specific Discord channel and maintains message history.

Key Responsibilities:
- Store conversation history (list of messages)
- Track conversation metadata (channel, user, creation time)
- Provide methods for adding messages and retrieving context
- Limit history size to manage memory

Key Features:
- Per-channel conversation history
- Configurable max history length
- Message ordering
- Context extraction for LM Studio API
"""

# TODO: Implement Conversation class
# - Properties: channel_id, messages (list), created_at, last_activity
# - add_message(role: str, content: str) -> None
# - get_context() -> list[dict]: Return messages in OpenAI format
# - clear() -> None: Clear message history
# - truncate(max_messages: int) -> None: Limit history size