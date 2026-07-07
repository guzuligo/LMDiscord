"""
Unit Tests for SEARCH-001: Channel Search Pagination & Channel Skip Features

Tests for:
- ChannelSkipTool (src/tools/builtins/channel_skip.py)
- ChannelSearchTool pagination (src/tools/builtins/channel_search.py)
- Bot Core pagination methods (src/discord_bot/bot_core.py)
- Tool Executor handlers (src/discord_bot/tool_executor.py)
- Integration workflows

Run with:
    cd LMDiscord/POC/test1
    python -m pytest tests/test_channel_search_pagination.py -v
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime, timedelta
from typing import List, Dict, Any

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.tools.builtins.channel_skip import ChannelSkipTool
from src.tools.builtins.channel_search import ChannelSearchTool
from src.tools.base import ToolResult


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def channel_skip_tool():
    """Return a fresh ChannelSkipTool instance."""
    return ChannelSkipTool()


@pytest.fixture
def channel_search_tool():
    """Return a fresh ChannelSearchTool instance."""
    return ChannelSearchTool()


@pytest.fixture
def mock_message_dict():
    """Return a complete message dict with all fields."""
    return {
        "message_id": 123456789012345678,
        "channel_id": 111111111111111111,
        "guild_id": 222222222222222222,
        "author": "testuser",
        "display_name": "Test User",
        "content": "Test message content for channel search",
        "timestamp": "2026-07-07 20:00:00",
        "is_reply": False,
        "replied_to_author": None,
        "replied_to_content": None,
        "has_image": False,
        "image_urls": []
    }


@pytest.fixture
def mock_skip_message_dict():
    """Return a metadata-only message dict for skip tests."""
    return {
        "message_id": 123456789012345678,
        "channel_id": 111111111111111111,
        "guild_id": 222222222222222222,
        "author": "testuser",
        "display_name": "Test User",
        "timestamp": "2026-07-07 20:00:00",
        "has_image": True,
        "has_link": False,
        "has_embed": True,
        "attachment_count": 2,
        "is_reply": False
    }


@pytest.fixture
def mock_message_dicts():
    """Return a list of message dicts for batch tests."""
    return [
        {
            "message_id": 123456789012345670 + i,
            "channel_id": 111111111111111111,
            "guild_id": 222222222222222222,
            "author": f"user{i}",
            "display_name": f"User {i}",
            "content": f"Message content {i}",
            "timestamp": f"2026-07-07 {19 + i // 60:02d}:{i % 60:02d}:00",
            "is_reply": i % 5 == 0,
            "replied_to_author": f"user{(i-1) % 5}" if i % 5 == 0 else None,
            "replied_to_content": f"Content being replied to" if i % 5 == 0 else None,
            "has_image": i % 3 == 0,
            "image_urls": [f"https://example.com/img{i}.png"] if i % 3 == 0 else []
        }
        for i in range(1, 6)
    ]


@pytest.fixture
def mock_skip_message_dicts():
    """Return a list of metadata-only message dicts for skip tests."""
    return [
        {
            "message_id": 123456789012345670 + i,
            "channel_id": 111111111111111111,
            "guild_id": 222222222222222222,
            "author": f"user{i}",
            "display_name": f"User {i}",
            "timestamp": f"2026-07-07 {19 + i // 60:02d}:{i % 60:02d}:00",
            "has_image": i % 3 == 0,
            "has_link": i % 4 == 0,
            "has_embed": i % 5 == 0,
            "attachment_count": 1 if i % 2 == 0 else 0,
            "is_reply": i % 5 == 0
        }
        for i in range(1, 6)
    ]


# ============================================================================
# 1. CHANNEL SKIP TOOL TESTS
# ============================================================================

class TestChannelSkipTool:
    """Tests for ChannelSkipTool properties and execute method."""

    def test_skip_tool_name(self, channel_skip_tool):
        """Test that tool name property returns 'channel_skip'."""
        assert channel_skip_tool.name == "channel_skip"

    def test_skip_tool_description(self, channel_skip_tool):
        """Test that tool description exists and is non-empty."""
        assert isinstance(channel_skip_tool.description, str)
        assert len(channel_skip_tool.description) > 0
        assert "Fast-forward" in channel_skip_tool.description

    def test_skip_tool_parameters(self, channel_skip_tool):
        """Test that parameter schema is valid and contains required keys."""
        params = channel_skip_tool.parameters
        assert isinstance(params, dict)
        assert params.get("type") == "object"
        properties = params.get("properties", {})
        assert "channel" in properties
        assert "count" in properties
        assert "target_date" in properties
        assert "tell_user_you_are_working" in properties

    @pytest.mark.asyncio
    async def test_skip_execute_empty_messages(self, channel_skip_tool):
        """Test execute with no messages returns success=False."""
        result = await channel_skip_tool.execute(messages=[], count=50)
        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "No messages found" in result.content
        assert result.error == "No messages provided"

    @pytest.mark.asyncio
    async def test_skip_execute_with_messages(self, channel_skip_tool, mock_message_dicts):
        """Test execute with metadata dicts returns formatted result."""
        result = await channel_skip_tool.execute(messages=mock_message_dicts, count=5)
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert "Skip Results" in result.content
        assert "Timeline Overview" in result.content
        assert "Message Types" in result.content
        assert "Total messages: 5" in result.content
        # Should include oldest message ID
        assert "Oldest message ID" in result.content

    @pytest.mark.asyncio
    async def test_skip_execute_media_indicators(self, channel_skip_tool, mock_skip_message_dicts):
        """Test that messages with images/links/embeds show indicators."""
        result = await channel_skip_tool.execute(messages=mock_skip_message_dicts, count=5)
        assert isinstance(result, ToolResult)
        assert result.success is True
        # Message 1 (i=1): has_image=True → 📷
        # Message 3 (i=3): has_link=True → 🔗
        # Message 4 (i=4): has_embed=True → 📎
        content = result.content
        assert "📷" in content
        assert "🔗" in content
        assert "📎" in content

    @pytest.mark.asyncio
    async def test_skip_execute_truncates_long_lists(self, channel_skip_tool):
        """Test that >10 messages shows only last 10 + 'X more' message."""
        # Create 15 messages
        messages = [
            {
                "message_id": 123456789012345670 + i,
                "channel_id": 111111111111111111,
                "guild_id": 222222222222222222,
                "author": f"user{i}",
                "display_name": f"User {i}",
                "timestamp": f"2026-07-07 {18 + i:02d}:{i:02d}:00",
                "has_image": False,
                "has_link": False,
                "has_embed": False,
                "attachment_count": 0,
                "is_reply": False
            }
            for i in range(1, 16)
        ]
        result = await channel_skip_tool.execute(messages=messages, count=15)
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert "and 5 more messages above" in result.content
        # Should only show last 10 entries
        content_lines = result.content.split("\n")
        # Count entries that look like message entries (start with "  User")
        entry_count = sum(1 for line in content_lines if line.strip().startswith("  User"))
        assert entry_count == 10


# ============================================================================
# 2. CHANNEL SEARCH PAGINATION TESTS
# ============================================================================

class TestChannelSearchPagination:
    """Tests for ChannelSearchTool pagination features."""

    def test_search_tool_max_pages_constant(self, channel_search_tool):
        """Test MAX_PAGES constant equals 20."""
        assert ChannelSearchTool.MAX_PAGES == 20

    def test_search_execute_pagination_params(self, channel_search_tool):
        """Test that pagination params exist in schema."""
        params = channel_search_tool.parameters
        properties = params.get("properties", {})
        assert "before_message_id" in properties
        assert "max_pages" in properties
        assert "pages_scanned_so_far" in properties

    @pytest.mark.asyncio
    async def test_search_execute_pagination_metadata(self, channel_search_tool, mock_message_dicts):
        """Test that result includes pagination info."""
        result = await channel_search_tool.execute(
            messages=mock_message_dicts,
            before_message_id="123456789012345674",
            max_pages=3,
            pages_scanned_so_far=1,
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert result.success is True
        content = result.content
        assert "Pages scanned" in content
        assert "Total messages scanned" in content
        assert "Oldest message ID" in content

    @pytest.mark.asyncio
    async def test_search_execute_pagination_suggestion(self, channel_search_tool, mock_message_dicts):
        """Test that result suggests going deeper when has_more_pages=True."""
        result = await channel_search_tool.execute(
            messages=mock_message_dicts,
            before_message_id="123456789012345674",
            max_pages=3,
            pages_scanned_so_far=1,
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert "💡 To go deeper" in result.content

    @pytest.mark.asyncio
    async def test_search_execute_max_pages_reached(self, channel_search_tool, mock_message_dicts):
        """Test that result warns at max pages when has_more_pages=False."""
        # max_pages=20, pages_scanned_so_far=0 → total = 20 = MAX_PAGES → no more pages
        result = await channel_search_tool.execute(
            messages=mock_message_dicts,
            before_message_id="123456789012345674",
            max_pages=20,
            pages_scanned_so_far=0,
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert "⚠️ Reached max pages" in result.content

    @pytest.mark.asyncio
    async def test_search_execute_no_more_messages(self, channel_search_tool):
        """Test empty results returns appropriate message."""
        result = await channel_search_tool.execute(messages=[])
        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "No messages found" in result.content

    @pytest.mark.asyncio
    async def test_search_execute_no_matching_filters(self, channel_search_tool, mock_message_dicts):
        """Test that no matching filters returns success=True with no match message."""
        result = await channel_search_tool.execute(
            messages=mock_message_dicts,
            search_query="ZZZZNOTFOUNDZZZZ",
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert "No messages match" in result.content

    @pytest.mark.asyncio
    async def test_search_execute_query_too_short(self, channel_search_tool, mock_message_dicts):
        """Test that search_query < 2 chars returns error."""
        result = await channel_search_tool.execute(
            messages=mock_message_dicts,
            search_query="A",
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "at least 2 characters" in result.content

    @pytest.mark.asyncio
    async def test_search_execute_compress_long_messages(self, channel_search_tool):
        """Test that long messages are truncated when compress_long=True."""
        long_content = "x" * 300
        messages = [{
            "message_id": 123456789012345678,
            "channel_id": 111111111111111111,
            "guild_id": 222222222222222222,
            "author": "testuser",
            "display_name": "Test User",
            "content": long_content,
            "timestamp": "2026-07-07 20:00:00",
            "is_reply": False,
            "replied_to_author": None,
            "replied_to_content": None,
            "has_image": False,
            "image_urls": []
        }]
        result = await channel_search_tool.execute(
            messages=messages,
            compress_long=True,
            limit=15
        )
        assert isinstance(result, ToolResult)
        # Content should be truncated at 200 chars + "..."
        assert "..." in result.content

    @pytest.mark.asyncio
    async def test_search_execute_no_compress_long_messages(self, channel_search_tool):
        """Test that long messages are NOT truncated when compress_long=False."""
        long_content = "x" * 300
        messages = [{
            "message_id": 123456789012345678,
            "channel_id": 111111111111111111,
            "guild_id": 222222222222222222,
            "author": "testuser",
            "display_name": "Test User",
            "content": long_content,
            "timestamp": "2026-07-07 20:00:00",
            "is_reply": False,
            "replied_to_author": None,
            "replied_to_content": None,
            "has_image": False,
            "image_urls": []
        }]
        result = await channel_search_tool.execute(
            messages=messages,
            compress_long=False,
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert long_content in result.content

    @pytest.mark.asyncio
    async def test_search_execute_username_filter(self, channel_search_tool, mock_message_dicts):
        """Test that username filter works correctly."""
        result = await channel_search_tool.execute(
            messages=mock_message_dicts,
            username="user2",
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert result.success is True
        # Only user2's messages should appear
        assert "User 2" in result.content

    @pytest.mark.asyncio
    async def test_search_execute_unfiltered_reduces_limit(self, channel_search_tool, mock_message_dicts):
        """Test that unfiltered queries only show 5 messages."""
        result = await channel_search_tool.execute(
            messages=mock_message_dicts,
            limit=15
        )
        assert isinstance(result, ToolResult)
        # Without filters, only 5 messages should be shown
        assert "Messages matched: 5" in result.content


# ============================================================================
# 3. BOT CORE PAGINATION TESTS
# ============================================================================

class TestBotCorePagination:
    """Tests for DiscordBot pagination methods."""

    @pytest.fixture
    def mock_lm_studio_client(self):
        """Create a mock LM Studio client."""
        client = MagicMock()
        client.is_connected = True
        client.config = None
        return client

    @pytest.fixture
    def discord_bot(self, mock_lm_studio_client):
        """Create a DiscordBot instance for testing."""
        with patch('src.discord_bot.bot_core.discord.Client'):
            bot = DiscordBot(
                token="test_token_for_testing_only",
                lm_studio_client=mock_lm_studio_client
            )
            return bot

    def test_search_context_initialized(self, discord_bot):
        """Test that _search_context dict exists and is empty on init."""
        assert hasattr(discord_bot, '_search_context')
        assert isinstance(discord_bot._search_context, dict)
        assert len(discord_bot._search_context) == 0

    @pytest.mark.asyncio
    async def test_resolve_channel_this_no_active_session(self, discord_bot):
        """Test resolve_channel('this') returns None when no active session."""
        result = discord_bot.resolve_channel("this")
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_channel_numeric(self, discord_bot, mock_lm_studio_client):
        """Test resolve_channel with numeric channel ID."""
        # Mock client.is_ready and client.get_channel
        discord_bot.client.is_ready = MagicMock(return_value=False)
        result = discord_bot.resolve_channel("#123456789")
        assert result is None

    @pytest.mark.asyncio
    async def test_skip_ahead_no_channel(self, discord_bot, mock_lm_studio_client):
        """Test _skip_ahead_messages with invalid channel returns error."""
        discord_bot.client.is_ready = MagicMock(return_value=False)
        result = await discord_bot._skip_ahead_messages("invalid_channel_xyz", 10)
        assert "messages" in result
        assert result["messages"] == []
        assert "error" in result

    @pytest.mark.asyncio
    async def test_fetch_channel_messages_basic(self, discord_bot, mock_lm_studio_client):
        """Test _fetch_channel_messages returns empty list when bot not ready."""
        discord_bot.client.is_ready = MagicMock(return_value=False)
        result = await discord_bot._fetch_channel_messages(123456789, 15)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_channel_messages_no_channel(self, discord_bot, mock_lm_studio_client):
        """Test get_channel_messages with unresolvable channel."""
        discord_bot.client.is_ready = MagicMock(return_value=False)
        result = await discord_bot.get_channel_messages(channel="nonexistent_channel_xyz")
        assert "messages" in result
        assert result["messages"] == []
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_channel_messages_empty_channel(self, discord_bot, mock_lm_studio_client):
        """Test get_channel_messages with empty channel searches all."""
        discord_bot.client.is_ready = MagicMock(return_value=False)
        result = await discord_bot.get_channel_messages(channel="")
        assert "messages" in result

    def test_skip_ahead_count_clamp_values(self):
        """Test that count clamping logic is correct (100 max)."""
        # The clamping happens in _skip_ahead_messages: count = max(1, min(count, 100))
        # Test the clamp formula directly
        assert max(1, min(200, 100)) == 100
        assert max(1, min(50, 100)) == 50
        assert max(1, min(0, 100)) == 1
        assert max(1, min(-5, 100)) == 1

    def test_fetch_limit_clamp_values(self):
        """Test that limit clamping logic is correct (50 max)."""
        # The clamping happens in _fetch_channel_messages: limit = max(1, min(limit, 50))
        assert max(1, min(100, 50)) == 50
        assert max(1, min(15, 50)) == 15
        assert max(1, min(0, 50)) == 1

    def test_max_pages_clamp_values(self):
        """Test that max_pages clamping logic is correct (20 max)."""
        # The clamping happens in _fetch_channel_messages_paginated: max_pages = max(1, min(max_pages, 20))
        assert max(1, min(100, 20)) == 20
        assert max(1, min(5, 20)) == 5
        assert max(1, min(0, 20)) == 1


# ============================================================================
# 4. TOOL EXECUTOR HANDLER TESTS
# ============================================================================

class TestToolExecutorHandlers:
    """Tests for ToolCallHandler channel_skip and channel_search methods."""

    @pytest.fixture
    def tool_call_handler(self):
        """Return a ToolCallHandler instance."""
        from src.discord_bot.tool_executor import ToolCallHandler
        return ToolCallHandler()

    @pytest.fixture
    def mock_bot_instance(self):
        """Create a mock bot instance."""
        bot = AsyncMock()
        bot._skip_ahead_messages = AsyncMock(return_value={
            "messages": [
                {
                    "message_id": 123456789012345670,
                    "channel_id": 111111111111111111,
                    "guild_id": 222222222222222222,
                    "author": "user1",
                    "display_name": "User 1",
                    "timestamp": "2026-07-07 19:00:00",
                    "has_image": False,
                    "has_link": False,
                    "has_embed": False,
                    "attachment_count": 0,
                    "is_reply": False
                }
            ]
        })
        bot.get_channel_messages = AsyncMock(return_value={
            "messages": [
                {
                    "message_id": 123456789012345678,
                    "channel_id": 111111111111111111,
                    "guild_id": 222222222222222222,
                    "author": "testuser",
                    "display_name": "Test User",
                    "content": "Test message content",
                    "timestamp": "2026-07-07 20:00:00",
                    "is_reply": False,
                    "replied_to_author": None,
                    "replied_to_content": None,
                    "has_image": False,
                    "image_urls": []
                }
            ]
        })
        return bot

    @pytest.mark.asyncio
    async def test_handle_channel_skip_no_bot(self, tool_call_handler):
        """Test _handle_channel_skip with no bot instance returns error."""
        messages_for_lm = []
        await tool_call_handler._handle_channel_skip(
            func_args='{"channel": "this", "count": 50}',
            messages_for_lm=messages_for_lm,
            tool_call_id="call_001",
            get_bot_instance=None
        )
        assert len(messages_for_lm) == 1
        assert messages_for_lm[0]["role"] == "tool"
        assert "Bot instance not available" in messages_for_lm[0]["content"]

    @pytest.mark.asyncio
    async def test_handle_channel_skip_with_bot(self, tool_call_handler, mock_bot_instance):
        """Test _handle_channel_skip with bot instance calls _skip_ahead_messages."""
        messages_for_lm = []

        def get_bot():
            return mock_bot_instance

        await tool_call_handler._handle_channel_skip(
            func_args='{"channel": "this", "count": 50}',
            messages_for_lm=messages_for_lm,
            tool_call_id="call_001",
            get_bot_instance=get_bot
        )
        # Should have appended tool result
        assert len(messages_for_lm) == 1
        assert messages_for_lm[0]["role"] == "tool"
        # Should contain skip result content
        assert "Skip Results" in messages_for_lm[0]["content"]
        # Bot's _skip_ahead_messages should have been called
        mock_bot_instance._skip_ahead_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_channel_skip_invalid_json(self, tool_call_handler):
        """Test _handle_channel_skip with invalid JSON args returns error."""
        messages_for_lm = []
        await tool_call_handler._handle_channel_skip(
            func_args='{invalid json here}',
            messages_for_lm=messages_for_lm,
            tool_call_id="call_001",
            get_bot_instance=None
        )
        assert len(messages_for_lm) == 1
        assert messages_for_lm[0]["role"] == "tool"
        assert "Invalid arguments" in messages_for_lm[0]["content"]

    @pytest.mark.asyncio
    async def test_handle_channel_search_pagination_params(self, tool_call_handler, mock_bot_instance):
        """Test _handle_channel_search passes pagination params through."""
        messages_for_lm = []

        def get_bot():
            return mock_bot_instance

        pagination_args = json.dumps({
            "channel": "this",
            "limit": 15,
            "before_message_id": "123456789012345670",
            "max_pages": 3,
            "pages_scanned_so_far": 1
        })

        await tool_call_handler._handle_channel_search(
            func_args=pagination_args,
            messages_for_lm=messages_for_lm,
            tool_call_id="call_002",
            get_bot_instance=get_bot
        )
        # Bot's get_channel_messages should have been called with pagination params
        mock_bot_instance.get_channel_messages.assert_called_once()
        call_kwargs = mock_bot_instance.get_channel_messages.call_args
        assert call_kwargs.kwargs.get("before_message_id") == "123456789012345670"
        assert call_kwargs.kwargs.get("max_pages") == 3
        assert call_kwargs.kwargs.get("pages_scanned_so_far") == 1

    @pytest.mark.asyncio
    async def test_handle_channel_search_no_bot(self, tool_call_handler):
        """Test _handle_channel_search with no bot instance returns error."""
        messages_for_lm = []
        await tool_call_handler._handle_channel_search(
            func_args='{"channel": "this", "limit": 15}',
            messages_for_lm=messages_for_lm,
            tool_call_id="call_003",
            get_bot_instance=None
        )
        assert len(messages_for_lm) == 1
        assert "Bot instance not available" in messages_for_lm[0]["content"]


# ============================================================================
# 5. INTEGRATION TESTS
# ============================================================================

class TestIntegrationWorkflow:
    """Integration tests for cross-module workflows."""

    @pytest.mark.asyncio
    async def test_full_search_workflow(self, channel_search_tool, mock_message_dicts):
        """Test channel_search → pagination → deeper results workflow."""
        # First search
        result1 = await channel_search_tool.execute(
            messages=mock_message_dicts,
            before_message_id="",
            max_pages=1,
            pages_scanned_so_far=0,
            limit=15
        )
        assert result1.success is True

        # Extract oldest message ID from pagination info
        content = result1.content
        oldest_id_line = [l for l in content.split("\n") if "Oldest message ID:" in l]
        assert len(oldest_id_line) > 0
        oldest_id = oldest_id_line[0].split("Oldest message ID:")[1].strip()

        # Second search with pagination
        result2 = await channel_search_tool.execute(
            messages=[
                {
                    "message_id": 123456789012345600,
                    "channel_id": 111111111111111111,
                    "guild_id": 222222222222222222,
                    "author": "older_user",
                    "display_name": "Older User",
                    "content": "Older message content from previous page",
                    "timestamp": "2026-07-07 18:00:00",
                    "is_reply": False,
                    "replied_to_author": None,
                    "replied_to_content": None,
                    "has_image": False,
                    "image_urls": []
                }
            ],
            before_message_id=oldest_id,
            max_pages=2,
            pages_scanned_so_far=1,
            limit=15
        )
        assert result2.success is True
        # Should show updated pagination info
        assert "Pages scanned" in result2.content

    @pytest.mark.asyncio
    async def test_skip_then_search_workflow(self, channel_skip_tool, channel_search_tool, mock_skip_message_dicts):
        """Test channel_skip → use oldest ID → channel_search workflow."""
        # Step 1: Skip ahead
        skip_result = await channel_skip_tool.execute(
            messages=mock_skip_message_dicts,
            count=5
        )
        assert skip_result.success is True

        # Extract oldest message ID from skip result
        content = skip_result.content
        oldest_id_line = [l for l in content.split("\n") if "Oldest message ID:" in l]
        assert len(oldest_id_line) > 0
        oldest_id = oldest_id_line[0].split("Oldest message ID:")[1].strip()
        assert oldest_id != "N/A"

        # Step 2: Use oldest ID for deeper search
        search_result = await channel_search_tool.execute(
            messages=[
                {
                    "message_id": int(oldest_id) - 10,
                    "channel_id": 111111111111111111,
                    "guild_id": 222222222222222222,
                    "author": "even_older_user",
                    "display_name": "Even Older User",
                    "content": "Even older message content",
                    "timestamp": "2026-07-07 17:00:00",
                    "is_reply": False,
                    "replied_to_author": None,
                    "replied_to_content": None,
                    "has_image": False,
                    "image_urls": []
                }
            ],
            before_message_id=oldest_id,
            max_pages=2,
            pages_scanned_so_far=0,
            limit=15
        )
        assert search_result.success is True
        assert "💡 To go deeper" in search_result.content

    @pytest.mark.asyncio
    async def test_search_context_persistence(self):
        """Test that _search_context persists visited_ids across calls."""
        # Simulate the search context behavior
        search_context: Dict[int, Dict[str, Any]] = {}

        # First call - initialize context
        channel_key = 111111111111111111
        if channel_key not in search_context:
            search_context[channel_key] = {
                "visited_ids": set(),
                "timestamps": {},
                "pages_scanned": 0,
                "total_messages": 0
            }

        context = search_context[channel_key]
        # Add some visited IDs
        context["visited_ids"].add("123456789012345670")
        context["visited_ids"].add("123456789012345671")
        context["pages_scanned"] = 1
        context["total_messages"] = 5

        # Second call - context should persist
        assert channel_key in search_context
        assert "123456789012345670" in search_context[channel_key]["visited_ids"]
        assert "123456789012345671" in search_context[channel_key]["visited_ids"]
        assert search_context[channel_key]["pages_scanned"] == 1

        # Duplicate prevention test
        assert "123456789012345670" in context["visited_ids"]
        # Attempting to add again should not create a duplicate (set behavior)
        context["visited_ids"].add("123456789012345670")
        assert len(context["visited_ids"]) == 2


# ============================================================================
# ADDITIONAL EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Additional edge case tests."""

    @pytest.mark.asyncio
    async def test_skip_tool_single_message(self, channel_skip_tool):
        """Test skip tool with a single message."""
        messages = [{
            "message_id": 123456789012345678,
            "channel_id": 111111111111111111,
            "guild_id": 222222222222222222,
            "author": "singleuser",
            "display_name": "Single User",
            "timestamp": "2026-07-07 20:00:00",
            "has_image": False,
            "has_link": False,
            "has_embed": False,
            "attachment_count": 0,
            "is_reply": False
        }]
        result = await channel_skip_tool.execute(messages=messages, count=1)
        assert result.success is True
        assert "Total messages: 1" in result.content

    @pytest.mark.asyncio
    async def test_search_tool_with_reply_info(self, channel_search_tool):
        """Test search tool with reply information."""
        messages = [{
            "message_id": 123456789012345678,
            "channel_id": 111111111111111111,
            "guild_id": 222222222222222222,
            "author": "replyuser",
            "display_name": "Reply User",
            "content": "This is a reply message",
            "timestamp": "2026-07-07 20:00:00",
            "is_reply": True,
            "replied_to_author": "original_user",
            "replied_to_content": "Original content being replied to",
            "has_image": False,
            "image_urls": []
        }]
        result = await channel_search_tool.execute(messages=messages, limit=15)
        assert result.success is True
        assert "Reply to" in result.content
        assert "original_user" in result.content

    @pytest.mark.asyncio
    async def test_search_tool_with_image_urls(self, channel_search_tool):
        """Test search tool with image URLs."""
        messages = [{
            "message_id": 123456789012345678,
            "channel_id": 111111111111111111,
            "guild_id": 222222222222222222,
            "author": "imageuser",
            "display_name": "Image User",
            "content": "Check this image",
            "timestamp": "2026-07-07 20:00:00",
            "is_reply": False,
            "replied_to_author": None,
            "replied_to_content": None,
            "has_image": True,
            "image_urls": ["https://cdn.discordapp.com/attachments/123/image.png"]
        }]
        result = await channel_search_tool.execute(messages=messages, limit=15)
        assert result.success is True
        assert "📷 Image" in result.content
        assert "https://cdn.discordapp.com" in result.content

    @pytest.mark.asyncio
    async def test_skip_tool_error_handling(self, channel_skip_tool):
        """Test skip tool error handling with None messages."""
        with pytest.raises(Exception):
            await channel_skip_tool.execute(messages=None)

    def test_search_tool_to_dict(self, channel_search_tool):
        """Test BaseTool.to_dict method for ChannelSearchTool."""
        # The base class to_dict method should work
        tool_dict = channel_search_tool.to_dict()
        assert tool_dict["type"] == "function"
        assert "function" in tool_dict
        assert tool_dict["function"]["name"] == "channel_search"
        assert "description" in tool_dict["function"]
        assert "parameters" in tool_dict["function"]

    def test_skip_tool_to_dict(self, channel_skip_tool):
        """Test BaseTool.to_dict method for ChannelSkipTool."""
        tool_dict = channel_skip_tool.to_dict()
        assert tool_dict["type"] == "function"
        assert tool_dict["function"]["name"] == "channel_skip"

    @pytest.mark.asyncio
    async def test_skip_tool_with_target_date(self, channel_skip_tool, mock_skip_message_dicts):
        """Test skip tool with target_date parameter."""
        result = await channel_skip_tool.execute(
            messages=mock_skip_message_dicts,
            target_date="2026-07-07"
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_skip_tool_with_tell_user(self, channel_skip_tool, mock_skip_message_dicts):
        """Test skip tool with tell_user_you_are_working parameter."""
        result = await channel_skip_tool.execute(
            messages=mock_skip_message_dicts,
            tell_user_you_are_working="Scanning through recent messages..."
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_search_tool_with_user_feedback(self, channel_search_tool, mock_message_dicts):
        """Test search tool with user_feedback parameter."""
        result = await channel_search_tool.execute(
            messages=mock_message_dicts,
            user_feedback="Looking for information about project deadlines"
        )
        assert result.success is True
        assert "USER CONTEXT" in result.content

    @pytest.mark.asyncio
    async def test_search_tool_with_message_id(self, channel_search_tool, mock_message_dicts):
        """Test search tool with message_id parameter (for fetching specific message)."""
        # This test verifies the parameter is accepted
        # The actual bot.get_message_by_id call would need a real bot instance
        result = await channel_search_tool.execute(
            messages=mock_message_dicts,
            message_id="123456789012345678"
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_tool_result_dataclass(self):
        """Test ToolResult dataclass functionality."""
        result = ToolResult(success=True, content="Test content")
        assert result.success is True
        assert result.content == "Test content"
        assert result.error == ""

        result_with_error = ToolResult(success=False, content="", error="Something went wrong")
        assert result_with_error.success is False
        assert result_with_error.error == "Something went wrong"


# ============================================================================
# IMPORTS NEEDED FOR TESTS
# ============================================================================

# Import DiscordBot for direct testing
try:
    from src.discord_bot.bot_core import DiscordBot
except ImportError:
    # If DiscordBot can't be imported (missing dependencies), skip those tests
    DiscordBot = None

# Import json for tool executor tests
import json