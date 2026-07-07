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
import logging

from ..base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ChannelSearchTool(BaseTool):
    """Tool for searching recent Discord channel messages.
    
    This tool accepts pre-fetched message data (from the Discord bot layer)
    and formats it into a structured result for LM Studio consumption.
    
    The actual Discord API calls (channel.history()) are handled by the
    bot layer in bot_core.py, since they are async operations.
    
    Pagination Support:
    - Use `before_message_id` to search messages older than a specific ID
    - Use `max_pages` to scan multiple pages of 50 messages each
    - Use `search_depth` to track total messages scanned across pages
    """

    MAX_MESSAGES = 50
    TRUNCATE_LENGTH = 200
    MAX_PAGES = 20  # Safety limit to prevent rate limit exhaustion

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
            "Pagination: use before_message_id (oldest ID from previous result) to search older messages. "
            "Use max_pages to scan multiple batches (default 1, max 20). Each page fetches up to 'limit' messages. "
            "Filters: limit (default 15, max 50), search_query (text filter), "
            "username (author filter), compress_long (truncate long messages). "
            "Result includes total_messages_scanned and oldest_message_id for pagination tracking."
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
                "message_id": {
                    "type": "string",
                    "description": "Optional Discord message ID. If provided, fetches that specific message to get its image attachments. Use this when the user referenced a specific message with an image."
                },
                "tell_user_you_are_working": {
                    "type": "string",
                    "description": "A short, friendly message to show the user while you work. E.g. 'Let me check what we were talking about...' or 'Looking through recent messages...'. This replaces the generic status message."
                },
                "before_message_id": {
                    "type": "string",
                    "description": "Discord message ID to anchor the search BEFORE this point. Use the oldest_message_id from a previous search result to go deeper into history. The bot will fetch messages older than this ID."
                },
                "max_pages": {
                    "type": "integer",
                    "description": "Maximum number of 50-message pages to scan (default: 1, max: 20). Each page fetches up to 'limit' messages. Use this to search deeper into history. Total messages scanned = max_pages * limit.",
                    "default": 1,
                    "minimum": 1,
                    "maximum": 20
                },
                "pages_scanned_so_far": {
                    "type": "integer",
                    "description": "Number of pages already scanned in this search session. Used for tracking total search depth across multiple tool calls.",
                    "default": 0
                }
            },
            "required": []
        }

    async def execute(self, messages: list = None, **kwargs) -> ToolResult:
        """Format pre-fetched channel messages into a structured result.
        
        The bot layer fetches messages via Discord.py async API and passes
        them as the 'messages' kwarg. This method formats them into the
        structured result format.
        
        Each message dict includes Discord jump link data (message_id,
        channel_id, guild_id) so the LM can reference specific messages
        with clickable links in its responses.
        
        If a message_id is provided in kwargs, the tool will attempt to
        fetch that specific message to get its image attachments.
        
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
            **kwargs: Additional arguments including:
                - message_id (str): Optional Discord message ID to fetch
                - search_query (str): Optional text filter
                - username (str): Optional author filter
                - compress_long (bool): Whether to truncate long messages
                - bot (callable): Optional callable that returns the DiscordBot instance
            
        Returns:
            ToolResult with content as formatted text summary of messages.
            Each message includes a REF field with a Discord jump link
            (https://discord.com/channels/{guild}/{channel}/{message}).
        """
        try:
            # Extract message_id for fetching specific message attachments
            message_id = kwargs.get("message_id")
            bot_instance = kwargs.get("bot")
            
            # If message_id provided and bot available, fetch specific message for image URLs
            if message_id and bot_instance:
                try:
                    # Extract channel_id from messages or use first message's channel
                    target_channel_id = None
                    if messages and len(messages) > 0:
                        target_channel_id = messages[0].get("channel_id")
                    
                    if target_channel_id:
                        msg_data = await bot_instance.get_message_by_id(
                            int(target_channel_id), int(message_id)
                        )
                        if msg_data and msg_data.get("message"):
                            fetched_msg = msg_data["message"]
                            logger.info(
                                f"[channel_search] Fetched message {message_id}: "
                                f"has_image={fetched_msg.get('has_image', False)}, "
                                f"image_urls={fetched_msg.get('image_urls', [])}"
                            )
                            # Add the fetched message to the beginning of results
                            messages.insert(0, fetched_msg)
                except Exception as e:
                    logger.warning(f"Failed to fetch message {message_id} for image URLs: {e}")
            
            if not messages:
                return ToolResult(
                    success=False,
                    content="No messages found in this channel.",
                    error="No messages provided"
                )

            # Apply filters from kwargs
            raw_search_query = kwargs.get("search_query", "").strip()
            search_query = raw_search_query.lower() if raw_search_query else ""
            username_filter = kwargs.get("username", "").strip()
            compress_long = kwargs.get("compress_long", True)

            # Recommendation 3: Reject queries shorter than 2 characters
            if raw_search_query and len(raw_search_query) < 2:
                return ToolResult(
                    success=False,
                    content="Error: search_query must be at least 2 characters long. Provide a more specific search term.",
                    error="Query too short"
                )

            # Recommendation 5: When no filters are specified, reduce limit to avoid wasting tokens
            # Return only the 5 most recent messages instead of fetching the full limit
            if not search_query and not username_filter:
                # Apply a reduced limit for unfiltered queries
                effective_limit = min(5, len(messages) if messages else 5)
                messages = messages[:effective_limit]

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

                # Image indicator — include actual URLs for LM to use
                if has_image and msg.get("image_urls"):
                    for url in msg["image_urls"]:
                        entry_parts.append(f"  [📷 Image: {url}]")

                formatted_messages.append("\n".join(entry_parts))

            # Extract pagination metadata from kwargs
            before_message_id = kwargs.get("before_message_id")
            max_pages = kwargs.get("max_pages", 1)
            pages_scanned_so_far = kwargs.get("pages_scanned_so_far", 0)
            limit = kwargs.get("limit", 15)
            
            # Get oldest message ID for further pagination
            oldest_msg = messages[-1] if messages else None
            oldest_message_id = str(oldest_msg.get("message_id", "")) if oldest_msg else ""
            oldest_timestamp = oldest_msg.get("timestamp", "") if oldest_msg else ""
            
            # Calculate search depth
            total_scanned = (pages_scanned_so_far + max_pages) * limit
            has_more_pages = (pages_scanned_so_far + max_pages) < self.MAX_PAGES
            
            # Build pagination info section
            pagination_info = [
                "",
                "--- Pagination Info ---",
                f"  Messages matched: {len(messages)}",
                f"  Pages scanned: {pages_scanned_so_far + 1}/{max_pages}",
                f"  Total messages scanned (all pages): ~{total_scanned}",
            ]
            
            if oldest_message_id:
                pagination_info.append(f"  Oldest message ID: {oldest_message_id}")
                pagination_info.append(f"  Oldest timestamp: {oldest_timestamp}")
                
                if has_more_pages:
                    pagination_info.append(
                        f"  💡 To go deeper: use before_message_id={oldest_message_id}, "
                        f"max_pages={max_pages + 1}"
                    )
                else:
                    pagination_info.append(
                        "  ⚠️ Reached max pages. Increase max_pages to search deeper "
                        "(max 20 pages total)."
                    )
            else:
                pagination_info.append("  ⚠️ No more messages — reached the oldest messages in this channel")
            
            # Build summary
            summary_lines = [
                f"📋 Channel Search Results ({len(messages)} messages):",
                "",
                *formatted_messages,
            ]
            
            # Add pagination info after message list
            summary_lines.extend(pagination_info)
            
            # Add LM instructions to help it use the results
            summary_lines.extend([
                "",
                "--- Instructions ---",
                "Read the messages above. If the search query was 'X', identify which messages "
                "contain this term and provide a direct answer to the user's original question.",
                "If no results found, use the pagination info to search older messages."
            ])

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