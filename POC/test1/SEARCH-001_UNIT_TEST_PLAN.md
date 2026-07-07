# SEARCH-001 Unit Testing Plan

> **⚠️ TEMPORARY FILE** — Delete this file after creating the unit test file `test_channel_search_pagination.py`

---

## Test Targets

### 1. ChannelSkipTool (`src/tools/builtins/channel_skip.py`)

| Test Name | What It Tests | Expected Result |
|-----------|--------------|-----------------|
| `test_skip_tool_name` | Tool name property | Returns `"channel_skip"` |
| `test_skip_tool_description` | Tool description exists | Non-empty string |
| `test_skip_tool_parameters` | Parameter schema valid | Has `channel`, `count`, `target_date`, `tell_user_you_are_working` |
| `test_skip_execute_empty_messages` | Execute with no messages | Returns `success=False`, content="No messages found" |
| `test_skip_execute_with_messages` | Execute with metadata dicts | Returns formatted result with timeline overview, stats, oldest ID |
| `test_skip_execute_media_indicators` | Messages with images/links/embeds | Shows 📷🔗📎 indicators in result |
| `test_skip_execute_truncates_long_lists` | >10 messages in batch | Shows only last 10 entries + "X more" message |

---

### 2. ChannelSearchTool Pagination (`src/tools/builtins/channel_search.py`)

| Test Name | What It Tests | Expected Result |
|-----------|--------------|-----------------|
| `test_search_tool_max_pages_constant` | MAX_PAGES constant | Equals 20 |
| `test_search_execute_pagination_params` | Pagination params in schema | Has `before_message_id`, `max_pages`, `pages_scanned_so_far` |
| `test_search_execute_pagination_metadata` | Result includes pagination info | Shows "Pages scanned", "Total messages scanned", "Oldest message ID" |
| `test_search_execute_pagination_suggestion` | Result suggests going deeper | Contains "💡 To go deeper" when has_more_pages=True |
| `test_search_execute_max_pages_reached` | Result warns at max pages | Contains "⚠️ Reached max pages" when has_more_pages=False |
| `test_search_execute_no_more_messages` | Empty results after pagination | Contains "⚠️ No more messages" |

---

### 3. Bot Core Pagination Methods (`src/discord_bot/bot_core.py`)

| Test Name | What It Tests | Expected Result |
|-----------|--------------|-----------------|
| `test_search_context_initialized` | `_search_context` dict exists | Empty dict on init |
| `test_fetch_paginated_basic` | `_fetch_channel_messages_paginated()` fetches messages | Returns list of message dicts |
| `test_fetch_paginated_before_id` | Pagination with `before_message_id` | Fetches messages older than anchor |
| `test_fetch_paginated_max_pages_clamp` | max_pages > 20 gets clamped | Clamped to 20 |
| `test_fetch_paginated_limit_clamp` | limit > 50 gets clamped | Clamped to 50 |
| `test_fetch_paginated_duplicate_prevention` | Same message fetched twice | Skips via visited_ids check |
| `test_skip_ahead_basic` | `_skip_ahead_messages()` returns metadata | Returns list of metadata dicts (no content) |
| `test_skip_ahead_count_clamp` | count > 100 gets clamped | Clamped to 100 |
| `test_skip_ahead_no_channel` | Invalid channel spec | Returns error dict |
| `test_get_channel_messages_with_pagination` | `get_channel_messages()` passes pagination params | Calls paginated fetch when before_message_id provided |

---

### 4. Tool Executor Handlers (`src/discord_bot/tool_executor.py`)

| Test Name | What It Tests | Expected Result |
|-----------|--------------|-----------------|
| `test_handle_channel_skip_no_bot` | No bot instance available | Returns error in messages_for_lm |
| `test_handle_channel_skip_with_bot` | Bot instance provided | Calls `_skip_ahead_messages`, formats result |
| `test_handle_channel_skip_invalid_json` | Invalid JSON args | Returns error, logs message |
| `test_handle_channel_search_pagination_params` | Pagination params passed through | `get_channel_messages()` called with before_message_id, max_pages |

---

### 5. Integration Tests

| Test Name | What It Tests | Expected Result |
|-----------|--------------|-----------------|
| `test_full_search_workflow` | channel_search → pagination → deeper results | Tool returns matching messages across pages |
| `test_skip_then_search_workflow` | channel_skip → use oldest ID → channel_search | Search anchors correctly at skip result |
| `test_search_context_persistence` | Multiple searches on same channel | visited_ids persist across calls |

---

## Test Setup

```python
# pytest fixtures needed
@pytest.fixture
def channel_skip_tool():
    return ChannelSkipTool()

@pytest.fixture
def channel_search_tool():
    return ChannelSearchTool()

@pytest.fixture
def mock_message_dict():
    return {
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

@pytest.fixture
def mock_skip_message_dict():
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
```

---

## Mocking Strategy

- **Discord API calls**: Mock `channel.history()`, `channel.fetch_message()` using `asyncio` mocks
- **Bot instance**: Mock `bot._skip_ahead_messages()`, `bot.get_channel_messages()`, `bot.resolve_channel()`
- **Tool executor**: Mock `get_bot_instance()` to return a mock bot

---

## Run Commands

```bash
cd LMDiscord/POC/test1
python -m pytest tests/test_channel_search_pagination.py -v
```

---

## Notes

- All async tests should use `pytest-asyncio`
- Mock Discord objects should implement minimal interface (id, name, history(), fetch_message())
- Test pagination logic independently from actual Discord API calls
- Test tool schema/parameter validation separately from bot integration