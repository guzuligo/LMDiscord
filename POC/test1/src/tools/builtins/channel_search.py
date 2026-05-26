"""
Channel Search Tool

This module implements a tool for searching recent Discord channel messages.
It enables LM Studio to fetch channel history for context building,
search/filtering, and conversation compression.

Key Responsibilities:
- Accept channel_id, limit, search_query, username, compress_long parameters
- Format message data into structured result for LM Studio consumption
- Handle parameter validation and error cases

Tool Definition:
- name: "channel_search"
- description: "Search recent messages in a Discord channel to gather context"
- parameters: { channel_id, limit, search_query, username, compress_long }

Integration:
- The bot layer fetches messages via Discord.py async API
- This tool formats the pre-fetched data into the structured result
- Message data is passed via kwargs from the tool executor
"""

import json

from ..base import BaseTool, ToolResult


class ChannelSearchTool(BaseTool):
    """Tool for searching recent Discord channel messages.
    
    This tool accepts pre-fetched message data (from the Discord bot layer)
    and formats it into a structured result for LM Studio consumption.
    
    The actual Discord API calls (channel.history()) are handled by the
    bot layer in bot_core.py, since they are async operations.
    """

    MAX_MESSAGES = 50
    TRUNCATE_LENGTH = 200

    @property
    def name(self) -> str:
        return "channel_search"

    @property
    def description(self) -> str:
        return (
            "Search recent messages in Discord channels to gather context for conversation. "
            "Returns a list of recent messages with author, content, timestamp, and reply info. "
            "Use this when you need to read channel history to understand ongoing conversations, "
            "find specific messages, or gather context before responding. "
            "Channel specification: use '#123456789' for channel ID, '@channelname' for channel name, "
            "'this' for the current active channel, or leave empty to search all channels. "
            "Optional filters: limit (default 15, max 50), search_query (text filter), "
            "username (author filter), compress_long (truncate long messages)."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel to search. Use '#123456789' for channel ID, '@channelname' for channel name, 'this' for current active channel, or leave empty to search all channels"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of recent messages to fetch per channel (default: 15, max: 50)",
                    "default": 15,
                    "minimum": 1,
                    "maximum": 50
                },
                "search_query": {
                    "type": "string",
                    "description": "Optional text filter — only messages containing this text are returned"
                },
                "username": {
                    "type": "string",
                    "description": "Optional username filter — only messages from this specific user"
                },
                "compress_long": {
                    "type": "boolean",
                    "description": "If true, truncate messages longer than 200 characters with '...'",
                    "default": True
                },
                "user_feedback": {
                    "type": "string",
                    "description": "Optional contextual feedback from the LM about what the user is looking for. Helps prioritize and frame results. Include the user's original question or intent here."
                },
                "tell_user_you_are_working": {
                    "type": "string",
                    "description": "A short, friendly message to show the user while you work. E.g. 'Let me check what we were talking about...' or 'Looking through recent messages...'. This replaces the generic status message."
                }
            },
            "required": []
        }

    def execute(self, messages: list = None, **kwargs) -> ToolResult:
        """Format pre-fetched channel messages into a structured result.
        
        The bot layer fetches messages via Discord.py async API and passes
        them as the 'messages' kwarg. This method formats them into the
        structured result format.
        
        Each message dict includes Discord jump link data (message_id,
        channel_id, guild_id) so the LM can reference specific messages
        with clickable links in its responses.
        
        Args:
            messages: List of message dicts from bot layer, each containing:
                - message_id (int): Discord message ID (for jump links)
                - channel_id (int): Discord channel ID
                - guild_id (int|None): Discord guild/server ID
                - author (str): username
                - display_name (str): display name
                - content (str): message text
                - timestamp (str): ISO format timestamp
                - is_reply (bool): whether this is a reply
                - replied_to_author (str|None): author being replied to
                - replied_to_content (str|None): content being replied to
                - has_image (bool): whether message has image attachment
            **kwargs: Additional arguments (ignored)
            
        Returns:
            ToolResult with content as formatted text summary of messages.
            Each message includes a REF field with a Discord jump link
            (https://discord.com/channels/{guild}/{channel}/{message}).
        """
        try:
            if not messages:
                return ToolResult(
                    success=False,
                    content="No messages found in this channel.",
                    error="No messages provided"
                )

            # Apply filters from kwargs
            search_query = kwargs.get("search_query", "").strip().lower()
            username_filter = kwargs.get("username", "").strip()
            compress_long = kwargs.get("compress_long", True)

            # Apply search_query filter
            if search_query:
                messages = [
                    m for m in messages
                    if search_query in m.get("content", "").lower()
                ]

            # Apply username filter
            if username_filter:
                messages = [
                    m for m in messages
                    if m.get("author", "").lower() == username_filter.lower()
                    or m.get("display_name", "").lower() == username_filter.lower()
                ]

            if not messages:
                return ToolResult(
                    success=True,
                    content="No messages match the specified filters.",
                    error=""
                )

            # Format messages into readable summary
            formatted_messages = []
            for msg in messages:
                author = msg.get("author", "Unknown")
                display_name = msg.get("display_name", author)
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                is_reply = msg.get("is_reply", False)
                replied_to_author = msg.get("replied_to_author")
                replied_to_content = msg.get("replied_to_content")
                has_image = msg.get("has_image", False)

                # Truncate long messages if compress_long is True
                if compress_long and len(content) > self.TRUNCATE_LENGTH:
                    content = content[:self.TRUNCATE_LENGTH] + "..."

                # Build formatted entry
                entry_parts = []

                # Reply indicator
                if is_reply and replied_to_author:
                    entry_parts.append(
                        f"[Reply to {replied_to_author}: \"{replied_to_content[:50]}{'...' if replied_to_content and len(replied_to_content) > 50 else ''}\"] "
                    )

                # Author and content
                entry_parts.append(f"**{display_name}** ({author}) — {timestamp}:")
                entry_parts.append(f"  {content}")

                # Image indicator
                if has_image:
                    entry_parts.append("  [📷 Image attached]")

                formatted_messages.append("\n".join(entry_parts))

            # Build summary
            summary_lines = [
                f"📋 Channel Search Results ({len(messages)} messages):",
                "",
                *formatted_messages,
                "",
                f"Total messages returned: {len(messages)}"
            ]

            result_text = "\n".join(summary_lines)

            return ToolResult(
                success=True,
                content=result_text
            )

        except Exception as exc:
            return ToolResult(
                success=False,
                content="",
                error=f"Failed to format channel search results: {str(exc)}"
            )