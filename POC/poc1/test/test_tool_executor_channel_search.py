"""
Unit tests for ToolExecutor channel search batched summarization.

Tests cover:
- _summarize_channel_search_batched: batched LM summarization
- _format_messages_for_summarization: message formatting helper
- _format_channel_search_direct: direct formatting without summarization

Run with:
    cd POC/test1
    python -m pytest test/test_tool_executor_channel_search.py -v
    # or
    cd POC/test1
    python test/test_tool_executor_channel_search.py
"""

import asyncio
import sys
import os
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

# Mock discord module BEFORE importing tool_executor
sys.modules["discord"] = MagicMock()
sys.modules["discord.ext"] = MagicMock()
sys.modules["discord.commands"] = MagicMock()

# Now add src to path and import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import only the specific class we need, bypassing __init__.py chain
import importlib.util
spec = importlib.util.spec_from_file_location(
    "tool_executor",
    os.path.join(os.path.dirname(__file__), "..", "src", "discord_bot", "tool_executor.py")
)
tool_executor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool_executor_module)
ToolCallHandler = tool_executor_module.ToolCallHandler


class TestFormatMessagesForSummarization(unittest.TestCase):
    """Tests for _format_messages_for_summarization helper."""

    def setUp(self):
        self.handler = ToolCallHandler()

    def test_simple_message(self):
        messages = [{
            "author": "alice",
            "display_name": "Alice",
            "content": "Hello world",
            "timestamp": "2026-06-04 10:00:00",
            "is_reply": False,
            "has_image": False,
            "image_urls": [],
        }]
        result = self.handler._format_messages_for_summarization(messages)
        self.assertIn("Alice", result)
        self.assertIn("Hello world", result)
        self.assertIn("2026-06-04 10:00:00", result)
        self.assertIn("--- Message 1 by Alice", result)

    def test_message_with_channel(self):
        messages = [{
            "author": "bob",
            "display_name": "Bob",
            "content": "Test message",
            "timestamp": "2026-06-04 11:00:00",
            "is_reply": False,
            "has_image": False,
            "image_urls": [],
            "_channel_name": "general",
        }]
        result = self.handler._format_messages_for_summarization(messages)
        self.assertIn("#general", result)

    def test_message_is_reply(self):
        messages = [{
            "author": "charlie",
            "display_name": "Charlie",
            "content": "Reply content",
            "timestamp": "2026-06-04 12:00:00",
            "is_reply": True,
            "replied_to_author": "Alice",
            "replied_to_content": "Original message content here",
            "has_image": False,
            "image_urls": [],
        }]
        result = self.handler._format_messages_for_summarization(messages)
        self.assertIn("Reply to Alice", result)
        self.assertIn("Original message content", result)

    def test_message_with_image(self):
        messages = [{
            "author": "dave",
            "display_name": "Dave",
            "content": "Look at this",
            "timestamp": "2026-06-04 13:00:00",
            "is_reply": False,
            "has_image": True,
            "image_urls": ["https://example.com/img1.png", "https://example.com/img2.png"],
        }]
        result = self.handler._format_messages_for_summarization(messages)
        self.assertIn("[Contains 2 image(s)]", result)

    def test_message_with_image_no_urls(self):
        messages = [{
            "author": "eve",
            "display_name": "Eve",
            "content": "Has image but no URLs",
            "timestamp": "2026-06-04 14:00:00",
            "is_reply": False,
            "has_image": True,
            "image_urls": [],
        }]
        result = self.handler._format_messages_for_summarization(messages)
        self.assertIn("[Contains image]", result)

    def test_empty_content_message(self):
        messages = [{
            "author": "frank",
            "display_name": "Frank",
            "content": "",
            "timestamp": "2026-06-04 15:00:00",
            "is_reply": False,
            "has_image": False,
            "image_urls": [],
        }]
        result = self.handler._format_messages_for_summarization(messages)
        self.assertIn("Frank", result)
        self.assertIn("--- Message 1 by Frank", result)

    def test_multiple_messages(self):
        messages = [
            {
                "author": "alice",
                "display_name": "Alice",
                "content": "First message",
                "timestamp": "2026-06-04 10:00:00",
                "is_reply": False,
                "has_image": False,
                "image_urls": [],
            },
            {
                "author": "bob",
                "display_name": "Bob",
                "content": "Second message",
                "timestamp": "2026-06-04 11:00:00",
                "is_reply": False,
                "has_image": False,
                "image_urls": [],
            },
        ]
        result = self.handler._format_messages_for_summarization(messages)
        self.assertIn("Message 1 by Alice", result)
        self.assertIn("Message 2 by Bob", result)
        self.assertIn("First message", result)
        self.assertIn("Second message", result)

    def test_missing_author_uses_author_key(self):
        messages = [{
            "content": "No display_name",
            "timestamp": "2026-06-04 10:00:00",
            "is_reply": False,
            "has_image": False,
            "image_urls": [],
            "author": "noreply",
        }]
        result = self.handler._format_messages_for_summarization(messages)
        self.assertIn("noreply", result)

    def test_missing_author_uses_unknown_fallback(self):
        messages = [{
            "content": "No author at all",
            "timestamp": "2026-06-04 10:00:00",
            "is_reply": False,
            "has_image": False,
            "image_urls": [],
        }]
        result = self.handler._format_messages_for_summarization(messages)
        self.assertIn("Unknown", result)

    def test_from_real_fixture_data(self):
        """Test formatting with real Discord message data from terminal.log."""
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "channel_messages.json")
        with open(fixture_path, 'r') as f:
            real_messages = json.load(f)

        # Filter to first 5 messages for a quick test
        sample = real_messages[:5]
        self.assertGreater(len(sample), 0, "Fixture should have at least 1 message")

        result = self.handler._format_messages_for_summarization(sample)
        # Should contain display names (used in formatting, not raw author field)
        display_names = set(m.get("display_name", m.get("author", "")) for m in sample)
        for name in display_names:
            if name:
                self.assertIn(name, result)
        # Should contain message numbering
        self.assertIn("--- Message 1 by", result)
        self.assertIn("--- Message 5 by", result)

    def test_from_fixture_with_replies(self):
        """Test that reply messages from fixture are formatted correctly."""
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "channel_messages.json")
        with open(fixture_path, 'r') as f:
            real_messages = json.load(f)

        reply_msgs = [m for m in real_messages if m.get("is_reply")]
        if reply_msgs:
            result = self.handler._format_messages_for_summarization(reply_msgs[:2])
            self.assertIn("Reply to", result)

    def test_from_fixture_with_images(self):
        """Test that image messages from fixture are formatted correctly."""
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "channel_messages.json")
        with open(fixture_path, 'r') as f:
            real_messages = json.load(f)

        image_msgs = [m for m in real_messages if m.get("has_image")]
        if image_msgs:
            result = self.handler._format_messages_for_summarization(image_msgs[:2])
            self.assertIn("image", result.lower())


class TestSummarizeChannelSearchBatched(unittest.TestCase):
    """Tests for _summarize_channel_search_batched method."""

    def setUp(self):
        self.handler = ToolCallHandler()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def _run_async(self, coro):
        """Run an async coroutine synchronously for testing."""
        return self.loop.run_until_complete(coro)

    def _make_sample_messages(self, count: int = 3) -> List[Dict[str, Any]]:
        """Generate sample messages for testing."""
        messages = []
        for i in range(count):
            messages.append({
                "author": f"user{i}",
                "display_name": f"User{i}",
                "content": f"Message content number {i}",
                "timestamp": f"2026-06-04 {10 + i}:00:00",
                "is_reply": i % 2 == 0,
                "replied_to_author": "Alice" if i % 2 == 0 else None,
                "replied_to_content": "Reply target" if i % 2 == 0 else None,
                "has_image": i == 1,
                "image_urls": ["https://example.com/img.png"] if i == 1 else [],
                "_channel_name": "general",
            })
        return messages

    def test_summarize_batched_success(self):
        """Test that a successful LM call returns the summary content."""
        mock_lm_call = AsyncMock(return_value={
            "choices": [{"message": {"content": "The messages discuss project updates and deadlines."}}]
        })
        messages = self._make_sample_messages(2)

        result = self._run_async(
            self.handler._summarize_channel_search_batched(
                messages=messages,
                search_query="project",
                user_feedback="Looking for project updates",
                make_lm_call_func=mock_lm_call,
                batch_size=10,
            )
        )

        self.assertIn("project", result.lower())
        self.assertIn("The messages discuss project updates and deadlines.", result)
        self.assertIn("=== END OF RESULTS ===", result)
        mock_lm_call.assert_called_once()

    def test_summarize_batched_empty_content(self):
        """Test when LM returns empty content (the bug scenario)."""
        mock_lm_call = AsyncMock(return_value={
            "choices": [{"message": {"content": ""}}]
        })
        messages = self._make_sample_messages(3)

        result = self._run_async(
            self.handler._summarize_channel_search_batched(
                messages=messages,
                search_query="image",
                user_feedback="",
                make_lm_call_func=mock_lm_call,
            )
        )

        # Empty content should still produce a summary line (but with empty content)
        self.assertIn("--- Batch 1 Summary ---", result)
        # The summary content after the header should be empty
        self.assertIn("=== END OF RESULTS ===", result)
        self.assertIn("image", result.lower())

    def test_summarize_batched_no_choices(self):
        """Test when LM returns response with no choices."""
        mock_lm_call = AsyncMock(return_value={"choices": []})
        messages = self._make_sample_messages(2)

        result = self._run_async(
            self.handler._summarize_channel_search_batched(
                messages=messages,
                search_query="test",
                user_feedback="",
                make_lm_call_func=mock_lm_call,
            )
        )

        self.assertIn("[No summary generated]", result)
        self.assertIn("=== END OF RESULTS ===", result)

    def test_summarize_batched_exception(self):
        """Test when LM call raises an exception."""
        mock_lm_call = AsyncMock(side_effect=Exception("Connection refused"))
        messages = self._make_sample_messages(2)

        result = self._run_async(
            self.handler._summarize_channel_search_batched(
                messages=messages,
                search_query="test",
                user_feedback="",
                make_lm_call_func=mock_lm_call,
            )
        )

        self.assertIn("[Summarization error:", result)
        self.assertIn("Connection refused", result)
        self.assertIn("=== END OF RESULTS ===", result)

    def test_summarize_batched_whitespace_only_content(self):
        """Test when LM returns only whitespace content."""
        mock_lm_call = AsyncMock(return_value={
            "choices": [{"message": {"content": "   \n  \t  "}}]
        })
        messages = self._make_sample_messages(2)

        result = self._run_async(
            self.handler._summarize_channel_search_batched(
                messages=messages,
                search_query="test",
                user_feedback="",
                make_lm_call_func=mock_lm_call,
            )
        )

        # Whitespace should be stripped, resulting in empty summary content
        self.assertIn("--- Batch 1 Summary ---", result)
        self.assertIn("=== END OF RESULTS ===", result)

    def test_summarize_batched_multiple_batches(self):
        """Test with more messages than batch_size to create multiple batches."""
        call_count = 0

        async def multi_response(messages, channel_id=None, use_tool_calling=False, max_tokens=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"choices": [{"message": {"content": "Batch 1 summary"}}]}
            return {"choices": [{"message": {"content": "Batch 2 summary"}}]}

        mock_lm_call = AsyncMock(side_effect=multi_response)
        # 25 messages with batch_size=10 → 3 batches, but we only have 2 responses
        # So batch 3 will get the second response again (side_effect cycles)
        messages = self._make_sample_messages(25)

        result = self._run_async(
            self.handler._summarize_channel_search_batched(
                messages=messages,
                search_query="multi",
                user_feedback="Multi-batch test",
                make_lm_call_func=mock_lm_call,
                batch_size=10,
            )
        )

        # Should have 3 batch headers
        self.assertIn("--- Batch 1 Summary ---", result)
        self.assertIn("--- Batch 2 Summary ---", result)
        self.assertIn("--- Batch 3 Summary ---", result)
        self.assertIn("=== END OF RESULTS ===", result)
        self.assertIn("25 messages", result)

    def test_summarize_batched_with_user_feedback(self):
        """Test that user_feedback is included in the prompt."""
        captured_prompt = None

        async def capture_prompt(messages, channel_id=None, use_tool_calling=False, max_tokens=None):
            nonlocal captured_prompt
            captured_prompt = messages[0]["content"]
            return {"choices": [{"message": {"content": "Summary with feedback context"}}]}

        mock_lm_call = AsyncMock(side_effect=capture_prompt)
        messages = self._make_sample_messages(1)

        self._run_async(
            self.handler._summarize_channel_search_batched(
                messages=messages,
                search_query="test",
                user_feedback="Please focus on the budget topic",
                make_lm_call_func=mock_lm_call,
            )
        )

        self.assertIn("budget", captured_prompt)
        self.assertIn("Please focus on the budget topic", captured_prompt)

    def test_summarize_batched_empty_messages(self):
        """Test with empty messages list."""
        mock_lm_call = AsyncMock()
        messages = []

        result = self._run_async(
            self.handler._summarize_channel_search_batched(
                messages=messages,
                search_query="empty",
                user_feedback="",
                make_lm_call_func=mock_lm_call,
            )
        )

        # No batches should be processed, but result should still be formatted
        self.assertNotIn("--- Batch", result)
        self.assertIn("0 messages", result)
        self.assertIn("=== END OF RESULTS ===", result)
        mock_lm_call.assert_not_called()

    def test_summarize_batched_result_contains_search_query(self):
        """Test that the search query appears in the result."""
        mock_lm_call = AsyncMock(return_value={
            "choices": [{"message": {"content": "Summary content"}}]
        })
        messages = self._make_sample_messages(1)

        result = self._run_async(
            self.handler._summarize_channel_search_batched(
                messages=messages,
                search_query="my_special_query",
                user_feedback="",
                make_lm_call_func=mock_lm_call,
            )
        )

        self.assertIn("my_special_query", result)

    def test_summarize_batched_max_tokens_passed(self):
        """Test that max_tokens parameter is passed to LM call."""
        captured_max_tokens = None

        async def capture_max_tokens(messages, channel_id=None, use_tool_calling=False, max_tokens=None):
            nonlocal captured_max_tokens
            captured_max_tokens = max_tokens
            return {"choices": [{"message": {"content": "Summary"}}]}

        mock_lm_call = AsyncMock(side_effect=capture_max_tokens)
        messages = self._make_sample_messages(1)

        self._run_async(
            self.handler._summarize_channel_search_batched(
                messages=messages,
                search_query="test",
                user_feedback="",
                make_lm_call_func=mock_lm_call,
                max_tokens=2048,
            )
        )

        self.assertEqual(captured_max_tokens, 2048)


class TestFormatChannelSearchDirect(unittest.TestCase):
    """Tests for _format_channel_search_direct method."""

    def setUp(self):
        self.handler = ToolCallHandler()

    def test_empty_messages(self):
        result = self.handler._format_channel_search_direct(
            messages=[],
            search_query="test",
            user_feedback="",
        )
        self.assertIn("No messages found", result)

    def test_empty_messages_with_channels(self):
        result = self.handler._format_channel_search_direct(
            messages=[],
            search_query="test",
            user_feedback="",
            available_channels={"general": 123, "random": 456},
        )
        self.assertIn("No messages found", result)
        self.assertIn("general", result)
        self.assertIn("random", result)

    def test_single_message(self):
        messages = [{
            "author": "alice",
            "display_name": "Alice",
            "content": "Hello there",
            "timestamp": "2026-06-04 10:00:00",
            "is_reply": False,
            "replied_to_author": None,
            "has_image": False,
            "image_urls": [],
            "_channel_name": "general",
            "message_id": "999",
            "channel_id": "123",
            "guild_id": "456",
        }]
        result = self.handler._format_channel_search_direct(
            messages=messages,
            search_query="hello",
            user_feedback="",
        )
        self.assertIn("=== Channel Search Results ===", result)
        self.assertIn("hello", result)
        self.assertIn("Alice", result)
        self.assertIn("Hello there", result)
        self.assertIn("=== END OF RESULTS ===", result)
        self.assertIn("https://discord.com/channels/456/123/999", result)

    def test_message_with_image_urls(self):
        messages = [{
            "author": "bob",
            "display_name": "Bob",
            "content": "Check this out",
            "timestamp": "2026-06-04 11:00:00",
            "is_reply": False,
            "replied_to_author": None,
            "has_image": False,
            "image_urls": ["https://cdn.discord.com/img1.png"],
            "_channel_name": "images",
            "message_id": "100",
            "channel_id": "789",
            "guild_id": "456",
        }]
        result = self.handler._format_channel_search_direct(
            messages=messages,
            search_query="check",
            user_feedback="",
        )
        self.assertIn("IMAGES:", result)
        self.assertIn("cdn.discord.com", result)

    def test_reply_message(self):
        messages = [{
            "author": "charlie",
            "display_name": "Charlie",
            "content": "I agree",
            "timestamp": "2026-06-04 12:00:00",
            "is_reply": True,
            "replied_to_author": "Alice",
            "has_image": False,
            "image_urls": [],
            "_channel_name": "general",
            "message_id": "200",
            "channel_id": "123",
            "guild_id": "456",
        }]
        result = self.handler._format_channel_search_direct(
            messages=messages,
            search_query="agree",
            user_feedback="",
        )
        self.assertIn("Reply to Alice", result)

    def test_user_feedback_included(self):
        messages = [{
            "author": "dave",
            "display_name": "Dave",
            "content": "Test",
            "timestamp": "2026-06-04 13:00:00",
            "is_reply": False,
            "replied_to_author": None,
            "has_image": False,
            "image_urls": [],
            "message_id": "300",
            "channel_id": "123",
            "guild_id": "456",
        }]
        result = self.handler._format_channel_search_direct(
            messages=messages,
            search_query="test",
            user_feedback="User wants to know about deadlines",
        )
        self.assertIn("USER CONTEXT: User wants to know about deadlines", result)

    def test_instructions_included(self):
        messages = [{
            "author": "eve",
            "display_name": "Eve",
            "content": "Test",
            "timestamp": "2026-06-04 14:00:00",
            "is_reply": False,
            "replied_to_author": None,
            "has_image": False,
            "image_urls": [],
            "message_id": "400",
            "channel_id": "123",
            "guild_id": "456",
        }]
        result = self.handler._format_channel_search_direct(
            messages=messages,
            search_query="deadline",
            user_feedback="",
        )
        self.assertIn("INSTRUCTIONS:", result)
        self.assertIn("deadline", result)


class TestGetMiniContextResponse(unittest.TestCase):
    """Tests for _get_mini_context_response helper."""

    def setUp(self):
        self.handler = ToolCallHandler()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def _run_async(self, coro):
        return self.loop.run_until_complete(coro)

    def test_mini_context_with_func(self):
        """Test that make_lm_call_func is called with correct args."""
        mock_func = AsyncMock(return_value={"choices": [{"message": {"content": "desc"}}]})
        mini_context = [{"role": "user", "content": "Describe this image"}]

        result = self._run_async(
            self.handler._get_mini_context_response(mini_context, mock_func)
        )

        mock_func.assert_called_once_with(
            mini_context, channel_id=None, use_tool_calling=False, max_tokens=None
        )
        self.assertEqual(result, {"choices": [{"message": {"content": "desc"}}]})

    def test_mini_context_without_func(self):
        """Test that missing func returns empty choices."""
        mini_context = [{"role": "user", "content": "Describe this image"}]

        result = self._run_async(
            self.handler._get_mini_context_response(mini_context, make_lm_call_func=None)
        )

        self.assertEqual(result, {"choices": []})


class TestExtractDescription(unittest.TestCase):
    """Tests for _extract_description helper."""

    def setUp(self):
        self.handler = ToolCallHandler()

    def test_successful_extraction(self):
        response = {"choices": [{"message": {"content": "A cat sitting on a table"}}]}
        result = self.handler._extract_description(response)
        self.assertEqual(result, "A cat sitting on a table")

    def test_empty_choices(self):
        response = {"choices": []}
        result = self.handler._extract_description(response)
        self.assertEqual(result, "Could not describe the image (no response from LM Studio).")

    def test_missing_content(self):
        response = {"choices": [{"message": {}}]}
        result = self.handler._extract_description(response)
        self.assertEqual(result, "Could not describe the image.")

    def test_missing_message_key(self):
        response = {"choices": [{}]}
        result = self.handler._extract_description(response)
        self.assertEqual(result, "Could not describe the image.")


if __name__ == "__main__":
    unittest.main()