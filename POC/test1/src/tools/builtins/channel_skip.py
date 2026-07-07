"""
Skip Ahead Tool (channel_skip)

This module implements a tool for fast-forwarding through Discord channel history
without fetching full message content. It returns only message metadata (ID, timestamp,
author) to help the LM "scan through time" efficiently.

Key Responsibilities:
- Accept channel_id, limit, and optional target_date parameters
- Fetch oldest N messages from a channel with minimal data
- Return structured metadata for timeline navigation
- Include media/attachment type indicators (images, links, etc.)

Tool Definition:
- name: "channel_skip"
- description: "Fast-forward through channel history to find a specific time period"
- parameters: { channel, count, target_date }

Integration:
- The bot layer fetches messages via Discord.py async API
- This tool formats the pre-fetched data into structured metadata
- Message data is passed via kwargs from the tool executor
"""

import logging
from typing import Any, Dict, List, Optional

from ..base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ChannelSkipTool(BaseTool):
    """Tool for fast-forwarding through channel history to find a time period.
    
    This tool fetches the N oldest messages from a channel but returns ONLY
    metadata (message ID, timestamp, author, media indicators) — NOT the full
    message content. This allows the LM to "scan through time" without
    consuming tokens on message text.
    
    The actual Discord API calls (channel.history()) are handled by the
    bot layer in bot_core.py, since they are async operations.
    """

    DEFAULT_COUNT = 50
    MAX_COUNT = 100

    @property
    def name(self) -> str:
        return "channel_skip"

    @property
    def description(self) -> str:
        return (
            "Fast-forward through Discord channel history to find a specific time period. "
            "Returns only metadata (message ID, timestamp, author, media indicators) without "
            "full message content. Use this to quickly scan through time without wasting tokens "
            "on message text. Channel specification: use '#123456789' for channel ID, "
            "'@channelname' for channel name, 'this' for the current active channel, or leave "
            "empty to skip in the current active channel. Optional parameters: count (default 50, "
            "max 100), target_date (YYYY-MM-DD format hint to know when to stop)."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel to skip in. Use '#123456789' for channel ID, '@channelname' for channel name, 'this' for current active channel, or leave empty for current active channel"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of oldest messages to fetch (default: 50, max: 100)",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 100
                },
                "target_date": {
                    "type": "string",
                    "description": "Optional date hint in YYYY-MM-DD format. The tool will return the oldest messages in the batch so you can check if you've reached the target date range"
                },
                "tell_user_you_are_working": {
                    "type": "string",
                    "description": "A short, friendly message to show the user while you work. E.g. 'Scanning through recent messages...' or 'Looking back in time...'. This replaces the generic status message."
                }
            },
            "required": []
        }

    async def execute(self, messages: list = None, **kwargs) -> ToolResult:
        """Format pre-fetched skip-ahead message metadata into a structured result.
        
        The bot layer fetches messages via Discord.py async API and passes
        them as the 'messages' kwarg. This method formats them into metadata-only
        results for timeline navigation.
        
        Args:
            messages: List of message dicts from bot layer, each containing:
                - message_id (int): Discord message ID
                - channel_id (int): Discord channel ID
                - guild_id (int|None): Discord guild/server ID
                - author (str): username
                - display_name (str): display name
                - timestamp (str): ISO format timestamp
                - has_image (bool): whether message has image attachment
                - has_link (bool): whether message has embedded links
                - has_embed (bool): whether message has embeds
                - attachment_count (int): number of non-image attachments
            **kwargs: Additional arguments including:
                - bot (callable): Optional callable that returns the DiscordBot instance
                
        Returns:
            ToolResult with content as formatted metadata summary.
            Includes the oldest message's ID and timestamp so the LM can
            decide whether to continue skipping or start searching.
        """
        try:
            if not messages:
                return ToolResult(
                    success=False,
                    content="No messages found in this channel.",
                    error="No messages provided"
                )

            count = kwargs.get("count", self.DEFAULT_COUNT)
            
            # Build metadata entries (no content!)
            metadata_entries = []
            stats = {
                "total": len(messages),
                "with_images": 0,
                "with_links": 0,
                "with_embeds": 0,
                "with_attachments": 0,
                "replies": 0
            }

            for msg in messages:
                author = msg.get("author", "Unknown")
                display_name = msg.get("display_name", author)
                timestamp = msg.get("timestamp", "")
                message_id = msg.get("message_id", 0)
                has_image = msg.get("has_image", False)
                has_link = msg.get("has_link", False)
                has_embed = msg.get("has_embed", False)
                attachment_count = msg.get("attachment_count", 0)
                is_reply = msg.get("is_reply", False)

                # Update stats
                if has_image:
                    stats["with_images"] += 1
                if has_link:
                    stats["with_links"] += 1
                if has_embed:
                    stats["with_embeds"] += 1
                if attachment_count > 0:
                    stats["with_attachments"] += attachment_count
                if is_reply:
                    stats["replies"] += 1

                # Build metadata entry with media indicators
                indicators = []
                if has_image:
                    indicators.append("📷")
                if has_link:
                    indicators.append("🔗")
                if has_embed:
                    indicators.append("📎")
                if attachment_count > 0:
                    indicators.append(f"📁{attachment_count}")
                
                indicator_str = " ".join(indicators) if indicators else ""
                entry = f"  {display_name} ({author}) — {timestamp} (ID: {message_id}) {indicator_str}"
                metadata_entries.append(entry)

            # Get oldest message info (last in chronological order)
            oldest_msg = messages[-1] if messages else None
            oldest_id = oldest_msg.get("message_id", "N/A") if oldest_msg else "N/A"
            oldest_timestamp = oldest_msg.get("timestamp", "N/A") if oldest_msg else "N/A"
            oldest_author = oldest_msg.get("author", "Unknown") if oldest_msg else "N/A"

            # Build result text
            result_lines = [
                f"⏭️ Skip Results ({len(messages)} messages scanned):",
                "",
                "--- Timeline Overview ---",
                f"  Newest: {messages[0].get('timestamp', 'N/A') if messages else 'N/A'}",
                f"  Oldest: {oldest_timestamp} (ID: {oldest_id}) by {oldest_author}",
                "",
                "--- Message Types ---",
                f"  Total messages: {stats['total']}",
                f"  With images: {stats['with_images']}",
                f"  With links: {stats['with_links']}",
                f"  With embeds: {stats['with_embeds']}",
                f"  With attachments: {stats['with_attachments']}",
                f"  Replies: {stats['replies']}",
                "",
                "--- Oldest Messages (use ID to go deeper) ---",
            ]
            
            # Show only the last 10 entries to keep it compact
            for entry in metadata_entries[-10:]:
                result_lines.append(entry)
            
            if len(metadata_entries) > 10:
                result_lines.append(f"  ... and {len(metadata_entries) - 10} more messages above")
            
            result_lines.extend([
                "",
                f"📌 Oldest message ID: {oldest_id}",
                f"📌 Oldest timestamp: {oldest_timestamp}",
                "",
                "💡 Tip: Use this ID with channel_search(before_message_id=...) to search older messages"
            ])

            result_text = "\n".join(result_lines)

            return ToolResult(
                success=True,
                content=result_text
            )

        except Exception as exc:
            return ToolResult(
                success=False,
                content="",
                error=f"Failed to format skip results: {str(exc)}"
            )