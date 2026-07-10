"""
Channel Search Tool

This module implements a tool for searching recent Discord channel messages.
It enables LM Studio to fetch channel history for context building,
search/filtering, and conversation compression.

Key Responsibilities:
- Accept pre-filtered message data and apply additional filtering via explicit parameters
- Format message data into structured result for LM Studio consumption
- Handle parameter validation and error cases

Tool Definition:
- name: "channel_search"
- description: "Search recent messages in a Discord channel to gather context"
- parameters: { channel, limit, search_query, username, has_image, has_link, has_file, has_video, has_audio, after_date, before_date, compress_long, ... }

Integration:
- The bot layer fetches messages via Discord.py async API and passes them as 'messages' kwarg
- This tool formats the pre-fetched data into the structured result
- Message data is passed via kwargs from the tool executor

DEPRECATED: The old operator-based query syntax (e.g., "has: image from: BotGuzu") is deprecated.
Use explicit boolean parameters instead: has_image=true, username="BotGuzu", etc.
The operator syntax is no longer supported and will be removed in a future version.
"""

import json
import logging
import re
import time
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from ..base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ChannelSearchTool(BaseTool):
    """Tool for searching recent Discord channel messages.
    
    This tool accepts pre-fetched message data (from the Discord bot layer)
    and formats it into a structured result for LM Studio consumption.
    
    The actual Discord API calls (channel.history()) are handled by the
    bot layer in bot_core.py, since they are async operations.
    
    PHASE 4: Request-level caching to avoid redundant Discord API calls
    when the same search parameters are used within a short time window.
    """

    MAX_MESSAGES = 50
    TRUNCATE_LENGTH = 200
    
    # PHASE 4: Cache configuration
    _request_cache: Dict[str, tuple] = {}  # cache_key -> (timestamp, result)
    _cache_ttl: float = 60.0  # 60 seconds TTL for request cache

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
            "Filtering (use explicit parameters, NOT operator syntax in search_query): "
            "Use has_image=true / has_link=true / has_file=true / has_video=true / has_audio=true "
            "to filter by content type (any of these can be set to true — they act as OR). "
            "Use username='BotGuzu' to filter by author, after_date='YYYY-MM-DD' / before_date='YYYY-MM-DD' "
            "for date range, and search_query='keyword' for text matching "
            "(all act as AND — if specified, all must match). "
            "For single-word search_query: matches only in message content (not file names). "
            "For multi-word search_query: ALL words must appear somewhere in the message. "
            "Optional: limit (default 50, max 50), compress_long (truncate long messages). "
            "For accessing older messages: use offset to skip recent messages, and windows to fetch "
            "multiple non-contiguous message windows (max 5 windows). Each window fetches 'limit' messages. "
            "For searching deeper into message history (older than the last 50 messages): use "
            "deep_search=true. This scans up to 500 messages backward from newest to oldest, "
            "stopping when a match is found."
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
                    "description": "Number of recent messages to fetch per channel (default: 50, max: 50). Always fetches the maximum to ensure the search sees all recent messages.",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 50
                },
                "has_image": {
                    "type": "boolean",
                    "description": "If true, filter to only messages with image attachments"
                },
                "has_link": {
                    "type": "boolean",
                    "description": "If true, filter to only messages with link embeds (URL previews)"
                },
                "has_file": {
                    "type": "boolean",
                    "description": "If true, filter to only messages with file attachments (non-image files)"
                },
                "has_video": {
                    "type": "boolean",
                    "description": "If true, filter to only messages with video attachments"
                },
                "has_audio": {
                    "type": "boolean",
                    "description": "If true, filter to only messages with audio attachments"
                },
                "search_query": {
                    "type": "string",
                    "description": "Optional text search filter. Single word: matches in message content only. Multiple words: ALL words must appear somewhere in the message (AND logic). Does not search file/attachment names."
                },
                "username": {
                    "type": "string",
                    "description": "Optional username filter — only messages from this specific user (e.g., 'BotGuzu' or 'BotGuzu#3756')"
                },
                "after_date": {
                    "type": "string",
                    "description": "Optional date filter — only messages after this date (YYYY-MM-DD format)"
                },
                "before_date": {
                    "type": "string",
                    "description": "Optional date filter — only messages before this date (YYYY-MM-DD format)"
                },
                "compress_long": {
                    "type": "boolean",
                    "description": "If true, truncate messages longer than 200 characters with '...'",
                    "default": True
                },
                "context_before": {
                    "type": "integer",
                    "description": "Number of messages before each match to include in context (default: 4). Helps show what led up to a match.",
                    "default": 4,
                    "minimum": 0,
                    "maximum": 20
                },
                "context_after": {
                    "type": "integer",
                    "description": "Number of messages after each match to include in context (default: 2). Helps show follow-up context.",
                    "default": 2,
                    "minimum": 0,
                    "maximum": 20
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
                "offset": {
                    "type": "integer",
                    "description": "Number of most recent messages to skip before fetching the first window. Use this to access older message history. Default is 0 (most recent messages).",
                    "default": 0,
                    "minimum": 0
                },
                "windows": {
                    "type": "integer",
                    "description": "Number of non-contiguous message windows to fetch. Each window fetches 'limit' messages, separated by 'limit' skipped messages. Max 5 windows. Default is 1.",
                    "default": 1,
                    "minimum": 1,
                    "maximum": 5
                },
                "deep_search": {
                    "type": "boolean",
                    "description": "Enable deep search mode. When True, the bot will scan up to max_depth messages backward from newest to oldest, stopping early when a match is found. Use this to find older messages that are beyond the last 50 messages. Filtering is applied via explicit parameters (has_image, username, etc.), NOT via operator syntax in search_query.",
                    "default": False
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum number of messages to scan when deep_search is enabled. Default is 500, maximum is 5000.",
                    "default": 500,
                    "minimum": 100,
                    "maximum": 5000
                }
            },
            "required": []
        }

    # Context window defaults
    CONTEXT_BEFORE = 4
    CONTEXT_AFTER = 2

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse a date string into a datetime object.

        Supports ISO 8601 format (e.g., "2026-06-01", "2026-06-01T00:00:00Z").

        Args:
            date_str: Date string to parse.

        Returns:
            datetime object with UTC timezone, or None if parsing fails.
        """
        # Try ISO format with time
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    def _generate_cache_key(self, kwargs: dict) -> Optional[str]:
        """Generate a cache key from the search parameters.
        
        PHASE 4: Creates a deterministic cache key based on the search
        parameters that would trigger a Discord API call.
        
        Args:
            kwargs: Tool execution arguments
            
        Returns:
            Cache key string, or None if messages are provided directly
            (meaning no API call is needed)
        """
        # If messages are provided directly (from bot layer), no caching needed
        # because the caching happens at the bot layer level
        if kwargs.get("messages") is not None:
            return None
        
        # Build a cache key from the key search parameters
        cache_params = {
            "channel": kwargs.get("channel", ""),
            "limit": kwargs.get("limit", 50),
            "search_query": kwargs.get("search_query", ""),
            "username": kwargs.get("username", ""),
        }
        
        # Generate a hash of the parameters
        key_str = json.dumps(cache_params, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

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
        
        PHASE 4: Checks request cache before processing to avoid redundant
        work when the same search is performed within the TTL window.
        
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
            # PHASE 4: Check request cache
            cache_key = self._generate_cache_key(kwargs)
            if cache_key and cache_key in self._request_cache:
                timestamp, cached_result = self._request_cache[cache_key]
                # Check if cache entry is still valid (within TTL)
                if time.time() - timestamp < self._cache_ttl:
                    logger.info(f"[channel_search_cache] Cache hit for key {cache_key}")
                    return cached_result
            
            # PHASE 4: Clean up expired cache entries periodically
            if len(self._request_cache) > 50:
                now = time.time()
                expired = [k for k, (ts, _) in self._request_cache.items()
                           if now - ts > self._cache_ttl]
                for k in expired:
                    del self._request_cache[k]
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
                    status="no_results",
                    message="No messages found in this channel.",
                    success=False,
                    content="No messages found in this channel."
                )

            # =========================================================================
            # NEW PARAMETER-BASED FILTERING LOGIC
            # =========================================================================
            
            # Extract new explicit parameters
            has_image_param = kwargs.get("has_image", False)
            has_link_param = kwargs.get("has_link", False)
            has_file_param = kwargs.get("has_file", False)
            has_video_param = kwargs.get("has_video", False)
            has_audio_param = kwargs.get("has_audio", False)
            username_filter = kwargs.get("username", "").strip() or None
            after_date_param = kwargs.get("after_date", "").strip() or None
            before_date_param = kwargs.get("before_date", "").strip() or None
            raw_search_query = kwargs.get("search_query", "").strip()
            compress_long = kwargs.get("compress_long", True)

            # Extract context window parameters
            context_before = kwargs.get("context_before", self.CONTEXT_BEFORE)
            context_after = kwargs.get("context_after", self.CONTEXT_AFTER)

            # Parse search_query into words (lowercase)
            search_query_words = raw_search_query.lower().split() if raw_search_query else []

            # Recommendation 3: Reject queries shorter than 2 characters
            if raw_search_query and len(raw_search_query) < 2:
                return ToolResult(
                    status="error",
                    message="Search query must be at least 2 characters long. Please provide a more specific search term.",
                    error="Query too short",
                    success=False,
                    content=""
                )

            # Note: Bot layer always fetches 50 messages, so no need to reduce limit here.
            # All messages are passed through for filtering.

            # =========================================================================
            # STEP 1: Apply OR logic for has_* parameters
            # Any matching content type includes the message
            # =========================================================================
            has_any_content_filter = has_image_param or has_link_param or has_file_param or has_video_param or has_audio_param
            if has_any_content_filter:
                filtered = []
                for m in messages:
                    match = False
                    content_types = m.get("content_types", {})
                    
                    # OR logic: check each enabled has_* parameter
                    if has_image_param and not match:
                        if content_types and "image" in content_types:
                            match = True
                        else:
                            has_image_attachments = m.get("has_image", False)
                            has_embeds = m.get("has_embeds", False)
                            has_image_urls = bool(m.get("image_urls", []))
                            match = has_image_attachments or (has_embeds and has_image_urls)
                    
                    if has_link_param and not match:
                        if content_types and "link" in content_types:
                            match = True
                        else:
                            # Check for actual link embeds: use content_types["link"]
                            # which bot_core.py populates with embed URLs.
                            # IMPORTANT: Do NOT use image_urls here because
                            # image_urls also contains attachment URLs which are
                            # not link embeds.
                            match = bool(m.get("content_types", {}).get("link", []))
                    
                    if has_file_param and not match:
                        if content_types and "file" in content_types:
                            match = True
                        else:
                            # Check for non-image file attachments.
                            # IMPORTANT: Do NOT include has_image here - files
                            # should be distinct from images. Images are handled
                            # by has_image filter. We check attachments list
                            # and exclude common image file extensions to
                            # differentiate files from images.
                            attachments = m.get("attachments", [])
                            if attachments:
                                # Filter out image-only attachments
                                for att in attachments:
                                    if isinstance(att, str):
                                        # Check if it's a non-image file extension
                                        non_image_exts = ('.pdf', '.doc', '.docx',
                                            '.txt', '.csv', '.json', '.xml', '.py',
                                            '.js', '.html', '.css', '.md', '.log',
                                            '.zip', '.rar', '.7z', '.exe', '.sh',
                                            '.bat', '.cmd', '.sql', '.yaml', '.yml',
                                            '.toml', '.ini', '.cfg', '.conf')
                                        if any(att.lower().endswith(ext) for ext in non_image_exts):
                                            match = True
                                            break
                            elif m.get("has_files", False):
                                # Fallback: use has_files flag if available
                                match = True
                    
                    if has_video_param and not match:
                        if content_types and "video" in content_types:
                            match = True
                        else:
                            match = False
                    
                    if has_audio_param and not match:
                        if content_types and "audio" in content_types:
                            match = True
                        else:
                            match = False
                    
                    if match:
                        filtered.append(m)
                messages = filtered

            # =========================================================================
            # STEP 2: Apply AND logic for username filter
            # =========================================================================
            if username_filter:
                # Strip Discord discriminator (e.g., "BotGuzu#3756" → "BotGuzu")
                filter_base = re.sub(r'#\d{4}$', '', username_filter).strip()
                filter_lower = filter_base.lower()
                
                filtered = []
                for m in messages:
                    author = m.get("author", "")
                    display_name = m.get("display_name", "")
                    
                    # Strip discriminator from stored values for comparison
                    author_base = re.sub(r'#\d{4}$', '', author).lower()
                    display_base = re.sub(r'#\d{4}$', '', display_name).lower()
                    
                    # Match if: exact match OR filter is contained in author/display_name
                    match = (
                        author_base == filter_lower
                        or display_base == filter_lower
                        or filter_lower in author.lower()
                        or filter_lower in display_name.lower()
                    )
                    if match:
                        filtered.append(m)
                messages = filtered

            # =========================================================================
            # STEP 3: Apply AND logic for after_date filter
            # =========================================================================
            if after_date_param:
                after_dt = self._parse_date(after_date_param)
                if after_dt:
                    # For date-only inputs (no time component), use as-is.
                    # `after_date: 2026-06-03` means "after June 3rd 00:00:00"
                    # (i.e., messages from June 3rd 00:00:01 onwards).
                    # This matches the LLM's natural expectation from the tool description.
                    filtered = []
                    for m in messages:
                        msg_ts = m.get("timestamp", "")
                        if msg_ts:
                            msg_dt = self._parse_date(msg_ts)
                            if msg_dt is not None and msg_dt >= after_dt:
                                filtered.append(m)
                    messages = filtered

            # =========================================================================
            # STEP 4: Apply AND logic for before_date filter
            # =========================================================================
            if before_date_param:
                before_dt = self._parse_date(before_date_param)
                if before_dt:
                    filtered = []
                    for m in messages:
                        msg_ts = m.get("timestamp", "")
                        if msg_ts:
                            msg_dt = self._parse_date(msg_ts)
                            if msg_dt is not None and msg_dt < before_dt:
                                filtered.append(m)
                    messages = filtered

            # =========================================================================
            # STEP 5: Apply AND logic for search_query
            # Single word: match only in message content (not file names)
            # Multiple words: ALL words must appear somewhere in the message content (AND)
            # NOTE: Messages with image URLs are always included regardless of text match,
            # because the user may be searching for an image that was posted without
            # the search term in the message text.
            # =========================================================================
            if search_query_words:
                filtered = []
                for m in messages:
                    content_text = m.get("content", "").lower()
                    replied_content = (m.get("replied_to_content") or "").lower()
                    
                    # Always include messages that have image URLs — they may contain
                    # the image the user is looking for even if the text doesn't match
                    has_image_urls = bool(m.get("image_urls", []))
                    
                    if len(search_query_words) == 1:
                        # Single word: match in content only (not file/attachment names)
                        word_match = (
                            search_query_words[0] in content_text
                            or search_query_words[0] in replied_content
                        )
                    else:
                        # Multiple words: ALL must match somewhere (AND logic)
                        word_match = True
                        for word in search_query_words:
                            if word not in content_text and word not in replied_content:
                                word_match = False
                                break
                    
                    # Include message if text matches OR if it has image URLs
                    if word_match or has_image_urls:
                        filtered.append(m)
                messages = filtered

            if not messages:
                return ToolResult(
                    status="no_results",
                    message="No messages match the specified filters.",
                    success=True,
                    content="No messages match the specified filters."
                )

            # Apply asymmetric context window expansion around matching messages
            # Use the new parameter names for consistency
            if search_query_words or username_filter:
                # Find indices of matching messages
                # Use raw_search_query for context matching (preserve original case for display)
                match_indices = set()
                for i, m in enumerate(messages):
                    content_text = m.get("content", "").lower()
                    content_match = raw_search_query and any(
                        word in content_text
                        for word in search_query_words
                    )
                    username_match = username_filter and (
                        m.get("author", "").lower() == username_filter.lower()
                        or m.get("display_name", "").lower() == username_filter.lower()
                    )
                    if content_match or username_match:
                        match_indices.add(i)

                # Expand context window around each match
                expanded_indices = set()
                for idx in match_indices:
                    # Include messages before the match
                    for j in range(max(0, idx - context_before), idx):
                        expanded_indices.add(j)
                    # Include the match itself
                    expanded_indices.add(idx)
                    # Include messages after the match
                    for j in range(idx + 1, min(len(messages), idx + 1 + context_after)):
                        expanded_indices.add(j)

                # Reorder messages to preserve chronological order with context
                selected_indices = sorted(expanded_indices)
                messages = [messages[i] for i in selected_indices]

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

                # Attachment filenames (non-image files)
                attachments = msg.get("attachments", [])
                for att in attachments:
                    if att:
                        entry_parts.append(f"  [📎 Attachment: {att}]")

                formatted_messages.append("\n".join(entry_parts))

            # Build summary
            summary_lines = [
                f"📋 Channel Search Results ({len(messages)} messages):",
                f"   (context: {context_before} before + match + {context_after} after each match)",
                ""
            ]

            # Add window indicators if using multi-window mode
            if kwargs.get("windows", 1) > 1 or kwargs.get("offset", 0) > 0:
                window_info = []
                if kwargs.get("offset", 0) > 0:
                    window_info.append(f"offset={kwargs['offset']}")
                if kwargs.get("windows", 1) > 1:
                    window_info.append(f"{kwargs['windows']} windows")
                summary_lines.append(f"   [{', '.join(window_info)}]")
                summary_lines.append("")

            summary_lines.extend([
                *formatted_messages,
                "",
                f"Total messages returned: {len(messages)}"
            ])

            result_text = "\n".join(summary_lines)

            # PHASE 4: Cache the result
            if cache_key:
                result_for_cache = ToolResult(
                    status="success",
                    message=result_text,
                    data=result_text,
                    success=True,
                    content=result_text
                )
                self._request_cache[cache_key] = (time.time(), result_for_cache)
                logger.info(f"[channel_search_cache] Cached result for key {cache_key}")

            return ToolResult(
                status="success",
                message=result_text,
                data=result_text,
                success=True,
                content=result_text
            )

        except Exception as exc:
            return ToolResult(
                status="error",
                message=f"An error occurred while searching: {str(exc)}",
                error=f"Failed to format channel search results: {str(exc)}",
                success=False,
                content=""
            )
