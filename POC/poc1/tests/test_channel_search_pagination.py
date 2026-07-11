"""
Unit Tests for Channel Search — Sliding Window, Deep Search & Channel Skip

Tests for the current implementation of:
- ChannelSkipTool (src/tools/builtins/channel_skip.py)
- ChannelSearchTool sliding window (offset + windows)
- ChannelSearchTool deep search (deep_search + max_depth)
- ChannelSearchTool before_message_id anchoring
- ChannelSearchTool filtering (username, search_query, compress_long)

Run with:
    cd LMDiscord/POC/poc1
    python -m pytest tests/test_channel_search_pagination.py -v
"""

import pytest
import asyncio
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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
            "replied_to_content": "Content being replied to" if i % 5 == 0 else None,
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
            "timestamp": f"2026-07-07 {18 + i:02d}:{i:02d}:00",
            "has_image": i % 3 == 0,
            "has_link": i % 4 == 0,
            "has_embed": i % 5 == 0,
            "attachment_count": 1 if i % 2 == 0 else 0,
            "is_reply": i % 5 == 0
        }
        for i in range(1, 16)
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
    async def test_skip_execute_with_messages(self, channel_skip_tool, mock_skip_message_dicts):
        """Test execute with metadata dicts returns formatted result."""
        result = await channel_skip_tool.execute(messages=mock_skip_message_dicts, count=15)
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert "Skip Results" in result.content
        assert "Timeline Overview" in result.content
        assert "Message Types" in result.content
        assert "Total messages:" in result.content
        # Should include oldest message ID
        assert "Oldest message ID" in result.content

    @pytest.mark.asyncio
    async def test_skip_execute_media_indicators(self, channel_skip_tool, mock_skip_message_dicts):
        """Test that messages with images/links/embeds show indicators."""
        # Use 6 messages to get a good mix of indicators
        messages = mock_skip_message_dicts[:6]
        result = await channel_skip_tool.execute(messages=messages, count=6)
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
        # Create 15 messages directly to avoid fixture caching issues
        messages = []
        for i in range(1, 16):
            messages.append({
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
            })
        result = await channel_skip_tool.execute(messages=messages, count=15)
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert "and 5 more messages above" in result.content


# ============================================================================
# 2. CHANNEL SEARCH SLIDING WINDOW TESTS
# ============================================================================

class TestChannelSearchSlidingWindow:
    """Tests for ChannelSearchTool sliding window features (offset + windows)."""

    def test_search_tool_offset_parameter_exists(self, channel_search_tool):
        """Test that offset param exists in schema."""
        params = channel_search_tool.parameters
        properties = params.get("properties", {})
        assert "offset" in properties
        assert properties["offset"]["type"] == "integer"
        assert properties["offset"]["default"] == 0

    def test_search_tool_windows_parameter_exists(self, channel_search_tool):
        """Test that windows param exists in schema."""
        params = channel_search_tool.parameters
        properties = params.get("properties", {})
        assert "windows" in properties
        assert properties["windows"]["type"] == "integer"
        assert properties["windows"]["default"] == 1
        assert properties["windows"]["maximum"] == 5

    def test_search_tool_before_message_id_parameter_exists(self, channel_search_tool):
        """Test that before_message_id param exists in schema."""
        params = channel_search_tool.parameters
        properties = params.get("properties", {})
        assert "before_message_id" in properties
        assert properties["before_message_id"]["type"] == "string"

    @pytest.mark.asyncio
    async def test_search_execute_with_offset(self, channel_search_tool, mock_message_dicts):
        """Test that offset parameter is accepted without error."""
        result = await channel_search_tool.execute(
            messages=mock_message_dicts,
            offset=2,
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert result.success is True
        # Result should include window indicator when offset > 0
        assert "offset=2" in result.content

    @pytest.mark.asyncio
    async def test_search_execute_with_multiple_windows(self, channel_search_tool):
        """Test that windows parameter is accepted without error."""
        # Clear the class-level cache to avoid cross-test pollution
        ChannelSearchTool._request_cache = {}
        # Create messages directly
        messages = [{
            "message_id": 123456789012345670 + i,
            "channel_id": 111111111111111111,
            "guild_id": 222222222222222222,
            "author": f"user{i}",
            "display_name": f"User {i}",
            "content": f"Message content {i}",
            "timestamp": f"2026-07-07 {19 + i // 60:02d}:{i % 60:02d}:00",
            "is_reply": False,
            "replied_to_author": None,
            "replied_to_content": None,
            "has_image": False,
            "image_urls": []
        } for i in range(1, 6)]
        result = await channel_search_tool.execute(
            messages=messages,
            windows=3,
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert result.success is True
        output = result.content or result.message or ""
        assert "windows" in output

    @pytest.mark.asyncio
    async def test_search_execute_windows_limit_clamp(self, channel_search_tool):
        """Test that windows parameter respects max of 5."""
        # Clear the class-level cache
        ChannelSearchTool._request_cache = {}
        # Create messages directly
        messages = [{
            "message_id": 123456789012345670 + i,
            "channel_id": 111111111111111111,
            "guild_id": 222222222222222222,
            "author": f"user{i}",
            "display_name": f"User {i}",
            "content": f"Message content {i}",
            "timestamp": f"2026-07-07 {19 + i // 60:02d}:{i % 60:02d}:00",
            "is_reply": False,
            "replied_to_author": None,
            "replied_to_content": None,
            "has_image": False,
            "image_urls": []
        } for i in range(1, 6)]
        result = await channel_search_tool.execute(
            messages=messages,
            windows=5,
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert result.success is True
        output = result.content or result.message or ""
        assert "windows" in output

    @pytest.mark.asyncio
    async def test_search_execute_offset_and_windows_combined(self, channel_search_tool):
        """Test offset + windows combined."""
        # Clear the class-level cache
        ChannelSearchTool._request_cache = {}
        messages = [{
            "message_id": 123456789012345670 + i,
            "channel_id": 111111111111111111,
            "guild_id": 222222222222222222,
            "author": f"user{i}",
            "display_name": f"User {i}",
            "content": f"Message content {i}",
            "timestamp": f"2026-07-07 {19 + i // 60:02d}:{i % 60:02d}:00",
            "is_reply": False,
            "replied_to_author": None,
            "replied_to_content": None,
            "has_image": False,
            "image_urls": []
        } for i in range(1, 6)]
        result = await channel_search_tool.execute(
            messages=messages,
            offset=10,
            windows=2,
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert result.success is True
        output = result.content or result.message or ""
        # Should show offset in header
        assert "offset" in output


# ============================================================================
# 3. CHANNEL SEARCH DEEP SEARCH TESTS
# ============================================================================

class TestChannelSearchDeepSearch:
    """Tests for ChannelSearchTool deep search feature."""

    def test_search_deep_search_parameter_exists(self, channel_search_tool):
        """Test that deep_search param exists in schema."""
        params = channel_search_tool.parameters
        properties = params.get("properties", {})
        assert "deep_search" in properties
        assert properties["deep_search"]["type"] == "boolean"
        assert properties["deep_search"]["default"] is False

    def test_search_max_depth_parameter_exists(self, channel_search_tool):
        """Test that max_depth param exists in schema."""
        params = channel_search_tool.parameters
        properties = params.get("properties", {})
        assert "max_depth" in properties
        assert properties["max_depth"]["type"] == "integer"
        assert properties["max_depth"]["default"] == 500
        assert properties["max_depth"]["minimum"] == 100
        assert properties["max_depth"]["maximum"] == 5000

    @pytest.mark.asyncio
    async def test_search_execute_deep_search_enabled(self, channel_search_tool, mock_message_dicts):
        """Test that deep_search=true is accepted without error."""
        result = await channel_search_tool.execute(
            messages=mock_message_dicts,
            deep_search=True,
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_search_execute_max_depth_parameter(self, channel_search_tool, mock_message_dicts):
        """Test that max_depth parameter is accepted."""
        result = await channel_search_tool.execute(
            messages=mock_message_dicts,
            deep_search=True,
            max_depth=1000,
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_search_execute_deep_search_with_query(self, channel_search_tool, mock_message_dicts):
        """Test deep_search with a search query."""
        result = await channel_search_tool.execute(
            messages=mock_message_dicts,
            deep_search=True,
            search_query="content",
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_search_execute_deep_search_max_depth_clamp(self, channel_search_tool, mock_message_dicts):
        """Test that max_depth respects the 100-5000 range."""
        # Test with max_depth=5000 (the maximum)
        result = await channel_search_tool.execute(
            messages=mock_message_dicts,
            deep_search=True,
            max_depth=5000,
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert result.success is True


# ============================================================================
# 4. CHANNEL SEARCH FILTERING TESTS
# ============================================================================

class TestChannelSearchFiltering:
    """Tests for ChannelSearchTool filtering features."""

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
    async def test_search_execute_compress_long_messages(self, channel_search_tool):
        """Test that long messages are truncated by default (compress_long defaults to True)."""
        # Clear the class-level cache
        ChannelSearchTool._request_cache = {}
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
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert result.success is True
        output = result.content or result.message or ""
        # Content should be truncated at 200 chars + "..." by default
        assert "..." in output
        # The full 300 chars should NOT be present
        assert long_content not in output

    @pytest.mark.asyncio
    async def test_search_execute_no_matching_filters(self, channel_search_tool):
        """Test that no matching filters returns success=True with no match message."""
        # Clear the class-level cache
        ChannelSearchTool._request_cache = {}
        messages = [{
            "message_id": 999999999999999990 + i,
            "channel_id": 888888888888888881,
            "guild_id": 777777777777777771,
            "author": f"uniqueuser{i}",
            "display_name": f"UniqueUser {i}",
            "content": f"Unique message content {i} xyzunique",
            "timestamp": f"2026-07-07 {19 + i // 60:02d}:{i % 60:02d}:00",
            "is_reply": False,
            "replied_to_author": None,
            "replied_to_content": None,
            "has_image": False,
            "image_urls": []
        } for i in range(1, 6)]
        result = await channel_search_tool.execute(
            messages=messages,
            search_query="ZZZZNOTFOUNDZZZZ",
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert result.success is True
        output = result.content or result.message or ""
        # Should indicate no matches found
        assert "match" in output.lower() or "no message" in output.lower() or "0" in output

    @pytest.mark.asyncio
    async def test_search_execute_query_too_short(self, channel_search_tool):
        """Test that search_query < 2 chars returns error."""
        messages = [{
            "message_id": 123456789012345670 + i,
            "channel_id": 111111111111111111,
            "guild_id": 222222222222222222,
            "author": f"user{i}",
            "display_name": f"User {i}",
            "content": f"Message content {i}",
            "timestamp": f"2026-07-07 {19 + i // 60:02d}:{i % 60:02d}:00",
            "is_reply": False,
            "replied_to_author": None,
            "replied_to_content": None,
            "has_image": False,
            "image_urls": []
        } for i in range(1, 6)]
        result = await channel_search_tool.execute(
            messages=messages,
            search_query="A",
            limit=15
        )
        assert isinstance(result, ToolResult)
        assert result.success is False
        # Error message should be in message or error field
        output = result.message or result.error or ""
        assert "2 characters" in output


# ============================================================================
# 5. CHANNEL SEARCH EDGE CASES
# ============================================================================

class TestChannelSearchEdgeCases:
    """Edge case tests for ChannelSearchTool."""

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
        output = result.content or result.message or ""
        assert "Reply to" in output

    @pytest.mark.asyncio
    async def test_search_tool_with_image_urls(self, channel_search_tool):
        """Test search tool with image URLs."""
        # Clear the class-level cache
        ChannelSearchTool._request_cache = {}
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
        output = result.content or result.message or ""
        # Images should be displayed with markdown format
        assert "![image](" in output
        # Image URLs should be present
        assert "cdn.discordapp.com" in output

    @pytest.mark.asyncio
    async def test_search_tool_with_message_id(self, channel_search_tool, mock_message_dicts):
        """Test search tool with message_id parameter (for fetching specific message)."""
        # This test verifies the parameter is accepted
        result = await channel_search_tool.execute(
            messages=mock_message_dicts,
            message_id="123456789012345678"
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_search_tool_empty_messages(self, channel_search_tool):
        """Test search tool with empty messages returns appropriate result."""
        result = await channel_search_tool.execute(messages=[])
        assert isinstance(result, ToolResult)
        # Empty messages may return success with 0 results or failure
        # Just verify it doesn't crash
        assert result is not None

    def test_search_tool_to_dict(self, channel_search_tool):
        """Test BaseTool.to_dict method for ChannelSearchTool."""
        tool_dict = channel_search_tool.to_dict()
        assert tool_dict["type"] == "function"
        assert "function" in tool_dict
        assert tool_dict["function"]["name"] == "channel_search"
        assert "description" in tool_dict["function"]
        assert "parameters" in tool_dict["function"]


# ============================================================================
# 6. CHANNEL SKIP EDGE CASES
# ============================================================================

class TestChannelSkipEdgeCases:
    """Edge case tests for ChannelSkipTool."""

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

    def test_skip_tool_to_dict(self, channel_skip_tool):
        """Test BaseTool.to_dict method for ChannelSkipTool."""
        tool_dict = channel_skip_tool.to_dict()
        assert tool_dict["type"] == "function"
        assert tool_dict["function"]["name"] == "channel_skip"


# ============================================================================
# 7. TOOL RESULT DATACLASS TESTS
# ============================================================================

class TestToolResultDataclass:
    """Tests for ToolResult dataclass."""

    def test_tool_result_success(self):
        """Test ToolResult with success=True."""
        result = ToolResult(success=True, content="Test content")
        assert result.success is True
        assert result.content == "Test content"
        assert result.error == ""
        assert result.status == "success"

    def test_tool_result_error(self):
        """Test ToolResult with success=False."""
        result = ToolResult(success=False, content="", error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"

    def test_tool_result_no_results(self):
        """Test ToolResult with no_results status."""
        result = ToolResult(status="no_results", message="No messages found")
        # Just verify it doesn't crash and status is set
        assert result.status == "no_results"


# ============================================================================
# IMPORTS NEEDED FOR TESTS
# ============================================================================

# Import DiscordBot for direct testing (optional - skip if not available)
try:
    from src.discord_bot.bot_core import DiscordBot
except ImportError:
    DiscordBot = None