"""
Integration tests for ToolExecutor channel search with real LM Studio connection.

These tests require a running LM Studio instance at LM_STUDIO_BASE_URL (default: http://localhost:1234/v1).

Run with:
    cd POC/test1
    python -m pytest test/test_integration_channel_search.py -v -k integration
    # or with custom LM Studio URL:
    LM_STUDIO_BASE_URL=http://your-lm-studio:1234/v1 python -m pytest test/test_integration_channel_search.py -v

Skip these tests if LM_STUDIO_SKIP is set to 1:
    LM_STUDIO_SKIP=1 python -m pytest test/test_integration_channel_search.py -v
"""

import asyncio
import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

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

# Integration test configuration
LM_STUDIO_BASE_URL = os.environ.get(
    "LM_STUDIO_BASE_URL",
    "http://localhost:1234/v1"
)
LM_STUDIO_SKIP = os.environ.get("LM_STUDIO_SKIP", "0") == "1"


def _load_fixture_messages():
    """Load real Discord message fixtures for integration tests."""
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "channel_messages.json")
    with open(fixture_path, 'r') as f:
        return json.load(f)


def _format_for_lm(conversation: list) -> list:
    """Format conversation for LM API chat/completions endpoint."""
    formatted_messages = []
    for i, msg in enumerate(conversation):
        role = "user" if i % 2 == 0 else "assistant"
        formatted_messages.append({"role": role, "content": msg["content"]})
    if not formatted_messages or formatted_messages[-1]["role"] != "user":
        formatted_messages.append({"role": "user", "content": "Please summarize these messages."})
    return formatted_messages


def _make_real_lm_call(base_url: str):
    """Create a real LM call function that connects to LM Studio.
    
    Uses aiohttp if available, otherwise falls back to urllib.
    """
    aiohttp_available = False
    try:
        import aiohttp  # noqa: F401
        aiohttp_available = True
    except ImportError:
        pass

    async def real_lm_call(messages, channel_id=None, use_tool_calling=False, max_tokens=None):
        """Make a real call to LM Studio API."""
        # Build conversation from messages
        conversation = []
        for msg in messages[:50]:  # Limit to avoid token limits
            content = f"[{msg.get('author', 'Unknown')}] {msg.get('content', '')}"
            if msg.get("is_reply") and msg.get("replied_to_author"):
                content = f"[{msg.get('author', 'Unknown')} replied to {msg.get('replied_to_author', '')}] {msg.get('content', '')}"
            if msg.get("has_image"):
                content += " [Contains images]"
            conversation.append({"content": content})

        if aiohttp_available:
            return await _call_lm_studio_aiohttp(base_url, conversation, max_tokens)
        else:
            return await _call_lm_studio_urllib(base_url, conversation, max_tokens)

    return real_lm_call


async def _call_lm_studio_aiohttp(base_url: str, conversation: list, max_tokens: int = None):
    """Call LM Studio using aiohttp."""
    import aiohttp
    import asyncio

    formatted_messages = _format_for_lm(conversation)
    payload = {
        "model": "local-model",
        "messages": formatted_messages,
        "max_tokens": max_tokens or 1024,
        "temperature": 0.7,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    return {"error": f"HTTP {response.status}: {error_text}", "choices": []}
    except asyncio.TimeoutError:
        return {"error": "LM Studio request timed out", "choices": []}
    except Exception as e:
        return {"error": str(e), "choices": []}


async def _call_lm_studio_urllib(base_url: str, conversation: list, max_tokens: int = None):
    """Call LM Studio using urllib (fallback when aiohttp not available)."""
    import urllib.request
    import urllib.error

    formatted_messages = _format_for_lm(conversation)
    payload = {
        "model": "local-model",
        "messages": formatted_messages,
        "max_tokens": max_tokens or 1024,
        "temperature": 0.7,
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}", "choices": []}
    except urllib.error.URLError as e:
        return {"error": f"Connection failed: {e.reason}", "choices": []}
    except Exception as e:
        return {"error": str(e), "choices": []}


class TestChannelSearchWithFixtures(unittest.TestCase):
    """Integration tests using real Discord message fixtures."""

    def setUp(self):
        self.handler = ToolCallHandler()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.fixture_messages = _load_fixture_messages()

    def tearDown(self):
        self.loop.close()

    def _run_async(self, coro):
        return self.loop.run_until_complete(coro)

    @unittest.skipIf(LM_STUDIO_SKIP, "LM Studio integration tests skipped")
    def test_summarize_real_messages_with_lm_studio(self):
        """Test summarizing real Discord messages through LM Studio."""
        if not self.fixture_messages:
            self.skipTest("No fixture messages available")

        # Use first 10 real messages
        sample = self.fixture_messages[:10]
        lm_call = _make_real_lm_call(LM_STUDIO_BASE_URL)

        result = self._run_async(
            self.handler._summarize_channel_search_batched(
                messages=sample,
                search_query="image.png",
                user_feedback="",
                make_lm_call_func=lm_call,
                batch_size=10,
            )
        )

        # The result should contain the search query
        self.assertIn("image.png", result.lower())
        # Should have end marker
        self.assertIn("=== END OF RESULTS ===", result)

    @unittest.skipIf(LM_STUDIO_SKIP, "LM Studio integration tests skipped")
    def test_format_channel_search_direct_with_real_data(self):
        """Test direct formatting with real Discord message data."""
        if not self.fixture_messages:
            self.skipTest("No fixture messages available")

        sample = self.fixture_messages[:5]

        # Add required fields for direct formatting
        messages_for_direct = []
        for msg in sample:
            formatted = {
                "author": msg["author"],
                "display_name": msg.get("display_name", msg["author"]),
                "content": msg["content"],
                "timestamp": msg.get("timestamp", ""),
                "is_reply": msg.get("is_reply", False),
                "replied_to_author": None,
                "has_image": msg.get("has_image", False),
                "image_urls": msg.get("image_urls", []),
                "message_id": msg.get("message_id", "0"),
                "channel_id": msg.get("channel_id", "0"),
                "guild_id": "0",
                "_channel_name": "general",
            }
            messages_for_direct.append(formatted)

        result = self.handler._format_channel_search_direct(
            messages=messages_for_direct,
            search_query="ghibli",
            user_feedback="",
        )

        self.assertIn("=== Channel Search Results ===", result)
        self.assertIn("ghibli", result.lower())
        # Should contain at least one author
        authors = set(m["author"] for m in messages_for_direct)
        found_any = any(a in result for a in authors)
        self.assertTrue(found_any, f"Expected at least one author in result. Authors: {authors}")

    def test_fixture_messages_have_valid_structure(self):
        """Verify that the fixture data has the expected structure."""
        self.assertGreater(len(self.fixture_messages), 0, "Fixture should have messages")

        required_fields = ["author", "content", "timestamp"]
        for msg in self.fixture_messages[:5]:
            for field in required_fields:
                self.assertIn(field, msg, f"Message missing required field: {field}")

    def test_fixture_messages_have_authors(self):
        """Verify that fixture messages have valid author names."""
        valid_authors = set()
        for msg in self.fixture_messages:
            author = msg.get("author", "")
            if author:
                valid_authors.add(author)

        # Should have at least the bot and user
        self.assertGreater(len(valid_authors), 0, "Should have at least one author")

    def test_fixture_messages_have_content(self):
        """Verify that fixture messages have non-empty content."""
        messages_with_content = [m for m in self.fixture_messages if m.get("content", "").strip()]
        self.assertGreater(len(messages_with_content), 0, "Should have messages with content")

    def test_fixture_messages_have_timestamps(self):
        """Verify that fixture messages have valid timestamps."""
        messages_with_ts = [m for m in self.fixture_messages if m.get("timestamp", "").strip()]
        self.assertGreater(len(messages_with_ts), 0, "Should have messages with timestamps")

    def test_batched_summarization_with_real_messages_mocked_lm(self):
        """Test batched summarization flow with real messages but mocked LM."""
        if not self.fixture_messages:
            self.skipTest("No fixture messages available")

        sample = self.fixture_messages[:15]  # Use 15 messages to test batching

        mock_lm_call = AsyncMock(return_value={
            "choices": [{"message": {"content": "The user is searching for image.png references in the channel."}}]
        })

        result = self._run_async(
            self.handler._summarize_channel_search_batched(
                messages=sample,
                search_query="image.png",
                user_feedback="",
                make_lm_call_func=mock_lm_call,
                batch_size=10,
            )
        )

        # Should have 2 batches (15 messages / batch_size 10)
        self.assertIn("--- Batch 1 Summary ---", result)
        self.assertIn("--- Batch 2 Summary ---", result)
        self.assertIn("=== END OF RESULTS ===", result)
        self.assertIn("image.png", result)
        # LM call should have been made twice
        self.assertEqual(mock_lm_call.call_count, 2)


class TestChannelSearchEdgeCases(unittest.TestCase):
    """Edge case tests for channel search with real message data."""

    def setUp(self):
        self.handler = ToolCallHandler()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.fixture_messages = _load_fixture_messages()

    def tearDown(self):
        self.loop.close()

    def _run_async(self, coro):
        return self.loop.run_until_complete(coro)

    def test_empty_messages_batched(self):
        """Test batched summarization with empty message list."""
        mock_lm_call = AsyncMock()
        result = self._run_async(
            self.handler._summarize_channel_search_batched(
                messages=[],
                search_query="test",
                user_feedback="",
                make_lm_call_func=mock_lm_call,
            )
        )
        self.assertNotIn("--- Batch", result)
        mock_lm_call.assert_not_called()

    def test_single_message_batched(self):
        """Test batched summarization with a single message."""
        if not self.fixture_messages:
            self.skipTest("No fixture messages available")

        mock_lm_call = AsyncMock(return_value={
            "choices": [{"message": {"content": "Single message summary"}}]
        })

        result = self._run_async(
            self.handler._summarize_channel_search_batched(
                messages=[self.fixture_messages[0]],
                search_query="test",
                user_feedback="",
                make_lm_call_func=mock_lm_call,
            )
        )

        self.assertIn("--- Batch 1 Summary ---", result)
        mock_lm_call.assert_called_once()

    def test_large_message_set(self):
        """Test with a large set of messages to verify batching."""
        if not self.fixture_messages:
            self.skipTest("No fixture messages available")

        # Use 50 messages with batch_size 10 = 5 batches
        sample = self.fixture_messages[:50]
        call_count = 0

        async def counting_lm_call(messages, **kwargs):
            nonlocal call_count
            call_count += 1
            return {"choices": [{"message": {"content": f"Batch {call_count} summary"}}]}

        mock_lm_call = AsyncMock(side_effect=counting_lm_call)

        result = self._run_async(
            self.handler._summarize_channel_search_batched(
                messages=sample,
                search_query="test",
                user_feedback="",
                make_lm_call_func=mock_lm_call,
                batch_size=10,
            )
        )

        # Should have 5 batches
        for i in range(1, 6):
            self.assertIn(f"--- Batch {i} Summary ---", result)
        self.assertEqual(call_count, 5)


if __name__ == "__main__":
    unittest.main()