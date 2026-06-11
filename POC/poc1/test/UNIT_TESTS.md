# Unit Test Documentation

## Overview

This directory contains unit and integration tests for the `ToolExecutor` channel search functionality, specifically testing the batched summarization and direct formatting features.

## Test Files

### 1. `test_tool_executor_channel_search.py`

Core unit tests for the `ToolCallHandler` class in `src/discord_bot/tool_executor.py`.

#### Test Classes

##### `TestFormatMessagesForSummarization`
Tests the `_format_messages_for_summarization()` helper method.

| Test | Description |
|------|-------------|
| `test_simple_message` | Single message formatting with author, content, timestamp |
| `test_message_with_channel` | Message includes `#channel_name` annotation |
| `test_message_is_reply` | Reply messages show "Reply to [author]" header |
| `test_message_with_image` | Messages with images show `[Contains N image(s)]` |
| `test_message_with_image_no_urls` | Messages with `has_image=True` but no URLs show `[Contains image]` |
| `test_empty_content_message` | Empty content messages still format correctly |
| `test_multiple_messages` | Multi-message formatting with sequential numbering |
| `test_missing_author_uses_author_key` | Fallback to `author` key when `display_name` is missing |
| `test_missing_author_uses_unknown_fallback` | Fallback to "Unknown" when no author info exists |
| `test_from_real_fixture_data` | **Fixture test** - validates formatting with real Discord message data |
| `test_from_fixture_with_replies` | **Fixture test** - validates reply message formatting |
| `test_from_fixture_with_images` | **Fixture test** - validates image message formatting |

##### `TestSummarizeChannelSearchBatched`
Tests the `_summarize_channel_search_batched()` async method.

| Test | Description |
|------|-------------|
| `test_summarize_batched_success` | Successful LM call returns summary content |
| `test_summarize_batched_empty_content` | LM returns empty content (bug scenario) |
| `test_summarize_batched_no_choices` | LM returns response with no choices array |
| `test_summarize_batched_exception` | LM call raises an exception |
| `test_summarize_batched_whitespace_only_content` | LM returns only whitespace |
| `test_summarize_batched_multiple_batches` | Messages exceeding batch_size create multiple batches |
| `test_summarize_batched_with_user_feedback` | User feedback is included in the LM prompt |
| `test_summarize_batched_empty_messages` | Empty message list skips LM call |
| `test_summarize_batched_result_contains_search_query` | Search query appears in output |
| `test_summarize_batched_max_tokens_passed` | `max_tokens` parameter is forwarded to LM |

##### `TestFormatChannelSearchDirect`
Tests the `_format_channel_search_direct()` method (non-summarized output).

| Test | Description |
|------|-------------|
| `test_empty_messages` | Empty messages shows "No messages found" |
| `test_empty_messages_with_channels` | Empty messages includes channel names |
| `test_single_message` | Single message with full metadata formatting |
| `test_message_with_image_urls` | Image URLs included in IMAGES section |
| `test_reply_message` | Reply messages show "Reply to [author]" |
| `test_user_feedback_included` | USER CONTEXT section included |
| `test_instructions_included` | INSTRUCTIONS section included |

##### `TestGetMiniContextResponse`
Tests the `_get_mini_context_response()` helper.

| Test | Description |
|------|-------------|
| `test_mini_context_with_func` | `make_lm_call_func` is called with correct arguments |
| `test_mini_context_without_func` | Missing func returns empty choices with warning log |

##### `TestExtractDescription`
Tests the `_extract_description()` helper.

| Test | Description |
|------|-------------|
| `test_successful_extraction` | Valid response returns content string |
| `test_empty_choices` | No choices returns error message |
| `test_missing_content` | Missing message.content returns error message |
| `test_missing_message_key` | Missing message key returns error message |

---

### 2. `test_integration_channel_search.py`

Integration tests that use real fixture data and optionally connect to a live LM Studio instance.

#### Test Classes

##### `TestChannelSearchWithFixtures`
Tests using real Discord message fixtures from `fixtures/channel_messages.json`.

| Test | Description |
|------|-------------|
| `test_fixture_messages_have_valid_structure` | Verifies fixture data has required fields |
| `test_fixture_messages_have_authors` | All messages have valid author names |
| `test_fixture_messages_have_content` | Messages have non-empty content |
| `test_fixture_messages_have_timestamps` | Messages have valid timestamps |
| `test_batched_summarization_with_real_messages_mocked_lm` | Batched flow with real messages + mocked LM |
| `test_format_channel_search_direct_with_real_data` | Direct formatting with real fixture data |
| `test_summarize_real_messages_with_lm_studio` | **Live test** - connects to LM Studio (skipped if `LM_STUDIO_SKIP=1`) |

##### `TestChannelSearchEdgeCases`
Edge case tests using fixture data.

| Test | Description |
|------|-------------|
| `test_empty_messages_batched` | Empty message list skips LM call |
| `test_single_message_batched` | Single message processes correctly |
| `test_large_message_set` | 50 messages with batch_size=10 creates 5 batches |

---

## Fixture Data

### `fixtures/channel_messages.json`

Generated from `terminal.log` (lines 907-1435) using `fixtures/extract_messages.py`.

**Source:** Real Discord bot conversation logs from terminal output.

**Record Count:** 104 messages

**Schema:**
```json
{
  "author": "string",           // Discord username (e.g., ".guzu", "BotGuzu")
  "display_name": "string",     // Display name (e.g., "guzu", "BotGuzu")
  "content": "string",          // Message content
  "timestamp": "string",        // ISO 8601 timestamp
  "message_id": "string",       // Discord message ID
  "channel_id": "string",       // Discord channel ID
  "image_urls": ["string"],     // List of image URLs (if any)
  "has_image": false,           // Whether message contains images
  "is_reply": false             // Whether message is a reply
}
```

### Extracting New Fixture Data

```bash
cd POC/test1
python test/fixtures/extract_messages.py
```

This parses `terminal.log` and regenerates `test/fixtures/channel_messages.json`.

---

## Running the Tests

### Run all tests:
```bash
cd POC/test1
python -m unittest test.test_tool_executor_channel_search test.test_integration_channel_search -v
```

### Run only unit tests (no LM Studio integration):
```bash
cd POC/test1
python -m unittest test.test_tool_executor_channel_search -v
```

### Run only integration tests:
```bash
cd POC/test1
python -m unittest test.test_integration_channel_search -v
```

### Skip LM Studio live tests:
```bash
LM_STUDIO_SKIP=1 python -m unittest test.test_integration_channel_search -v
```

### Run with custom LM Studio URL:
```bash
LM_STUDIO_BASE_URL=http://your-server:1234/v1 python -m unittest test.test_integration_channel_search -v
```

---

## Architecture

```
test/
├── test_tool_executor_channel_search.py   # Core unit tests
├── test_integration_channel_search.py     # Integration tests with fixtures
├── UNIT_TESTS.md                          # This file
└── fixtures/
    ├── extract_messages.py                # Terminal log parser
    └── channel_messages.json              # Generated fixture data
```

The tests verify:
1. **Message formatting** - `_format_messages_for_summarization()` and `_format_channel_search_direct()`
2. **Batched summarization** - `_summarize_channel_search_batched()` with configurable batch sizes
3. **Mini-context responses** - Image description and other mini-summarization tasks
4. **Edge cases** - Empty inputs, exceptions, missing fields, large message sets