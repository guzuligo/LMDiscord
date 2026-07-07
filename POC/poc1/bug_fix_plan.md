# Bug Fix Plan — Critical Issues

> **Created**: 2026-06-05
> **Last Updated**: 2026-06-10
> **Priority**: Critical — Bot hangs and fails to respond
> **Estimated Total Time**: ~3 hours

---

## Overview

The bot is experiencing critical failures where it hangs, posts empty responses, or crashes. This plan addresses the most critical issues in priority order, with dependencies tracked.

---

## 🆕 Phase 7: Image Fetch Failure — Expired CDN URLs (NEW — 2026-06-11 Terminal Log)

**Issue**: BUG-MESSAGE-002
**Estimated Time**: 15 minutes
**Risk**: Low — Retry logic in image_downloader.py
**Status**: ✅ **COMPLETED** (2026-06-11)

### Problem (from terminal.log 2026-06-11 08:35)

When the bot tries to fetch images from Discord CDN URLs with expired authentication tokens, the download fails with:
```
ValueError: Blocked: disallowed content type 'text/plain' (expected one of {...})
```

This happens because:
1. Discord CDN URLs contain time-limited query params (`ex=`, `is=`, `hm=`, `token=`)
2. These params expire, causing the CDN to return an error page (text/plain) instead of the image
3. The error page passes the initial content-type check (text/plain is not rejected immediately)
4. The code raises ValueError BEFORE the Referer retry logic for 403/404 errors

### Root Cause

The `image_downloader.py` had retry logic for 403/404 errors but the content-type mismatch error was raised BEFORE those handlers could trigger. The Referer header retry was only available for 404 errors, not for content-type errors.

### Files Modified
- `src/discord_bot/image_downloader.py` — Added Referer+Origin header retry for content-type errors BEFORE raising ValueError

### Changes Required

#### 1. Add Referer retry for content-type errors (BEFORE 403/404 handling)
```python
# Handle content-type mismatch — CDN may have returned an error page (text/plain)
# This commonly happens when CDN URLs have expired. Try with Referer header before giving up.
if hostname in DISCORD_CDN_HOSTS and isinstance(e, ValueError) and "content type" in error_str:
    logger.warning(f"Content-type mismatch for {url}: {error_str}, retrying with Referer header")
    try:
        referer_headers = {"Referer": "https://discord.com", "Origin": "https://discord.com"}
        raw_bytes = await self._download_with_session(url, headers=referer_headers)
        logger.info(f"Successfully downloaded {len(raw_bytes)} bytes from {hostname} with Referer+Origin headers (content-type retry)")
        return raw_bytes
    except Exception as retry_error:
        logger.warning(f"Referer retry also failed for {url}: {retry_error}")
        # Continue to 403/404 handling below
```

### Verification Steps
1. Run bot, share a message with an image that has expired CDN URL
2. Confirm the bot retries with Referer header before giving up
3. Confirm the user sees a friendly "Image URL has expired" message if all retries fail

---

## 🆕 Phase 6: Message Link Fetch Failure (NEW — 2026-06-11 Terminal Log)

**Issue**: BUG-MESSAGE-001
**Estimated Time**: 30 minutes
**Risk**: Low — Targeted fix in tool_executor.py and bot_core.py
**Status**: ✅ **COMPLETED** (2026-06-11)
**Test Results**: All 26 bug fix tests pass (`unittest/test_bug_fixes.py`)

### What Was Fixed
1. ✅ `bot_core.py` `get_channel_messages()` now accepts `message_id` and `link_channel_id` parameters (lines 564-565)
2. ✅ Direct message fetch logic added at lines 666-684 in `bot_core.py`
3. ✅ `tool_executor.py` `_handle_channel_search()` extracts `message_id` and `link_channel_id` from args (lines 744-746)
4. ✅ Parameters are passed to `bot.get_channel_messages()` (lines 757-758)

### BUG-MESSAGE-002: System Prompt + Fallback (2026-06-11)

**Status**: ✅ **COMPLETED** (2026-06-11)

**Problem**: The LM Studio model was **never instructed** to include `message_id` and `channel_id` in its tool call arguments when the user shares a Discord message link.

**Solution Applied**:

1. **System prompt update** in `message_handler.py`:
   Added instruction to the channel_search tool definition:
   ```
   IMPORTANT: If the user shares a Discord message link (e.g., discord.com/channels/GUILD_ID/CHANNEL_ID/MESSAGE_ID), you MUST include both 'message_id' and 'channel_id' parameters extracted from the link to fetch that specific message directly.
   ```

2. **Fallback mechanism** in `tool_executor.py`:
   Added `_extract_message_link_ids_from_history()` static method that scans the last 10 user messages in conversation history for Discord message link patterns:
   - `discord.com/channels/GUILD_ID/CHANNEL_ID/MESSAGE_ID`
   - `discordapp.com/channels/GUILD_ID/CHANNEL_ID/MESSAGE_ID`
   
   When `message_id` or `channel_id` are not provided in tool call args, the fallback extracts them from conversation history automatically.

**Files Modified**:
- `src/discord_bot/message_handler.py` — Added message_id/channel_id instruction to system prompt
- `src/discord_bot/tool_executor.py` — Added `_extract_message_link_ids_from_history()` method and fallback logic in `_handle_channel_search()`

**Data flow**:
1. User shares link: `discord.com/channels/1502926835862863944/1503498099081871470/1508736219281096804`
2. `message_router.py` extracts `channel_id=1503498099081871470` and `message_id=1508736219281096804` — but only for image fetching
3. LM Studio receives the message and calls `channel_search` — but the system prompt does NOT mention `message_id`/`channel_id` parameters
4. `tool_executor.py` looks for `message_id` and `channel_id` in args — but they are **never provided by the LM**
5. `bot_core.py` direct fetch logic receives `None` for both → falls through to regular channel search → empty query → generic response

**System prompt evidence** (`message_handler.py` lines 258-264):
```
"- 'channel_search': Call this to read recent messages from Discord channels to gather context for conversation. Returns a list of recent messages with author, content, timestamp, reply info, and image attachment URLs. Use this when you need to understand ongoing conversations, find specific information, or gather context before responding.\n"
"  Channel specification (the 'channel' parameter):\n"
"    - '#123456789' — search by channel ID (e.g., '#1503498099081871470')\n"
"    - '@channelname' — search by channel name (e.g., '@c3', '@general')\n"
"    - 'this' — search the current active session channel\n"
"    - leave empty or omit — search ALL visible channels\n"
"  Optional parameters: limit (default 15, max 50), search_query (text filter), username (author filter), compress_long (truncate long messages)\n"
```

**Missing**: No mention of `message_id` or `channel_id` parameters in the system prompt.

### Required Fix
1. Update system prompt in `message_handler.py` to instruct LM:
   "IMPORTANT: If the user shares a Discord message link (e.g., discord.com/channels/.../CHANNEL_ID/MESSAGE_ID), include the `message_id` and `channel_id` parameters in your channel_search tool call with the values extracted from the link."
2. Add fallback in `tool_executor.py` `_handle_channel_search()`: If `message_id` and `channel_id` are not in the tool call args, scan the conversation history for Discord message links and extract the IDs automatically.

### Problem (from terminal.log 2026-06-11 08:35)

When a user shares a Discord message link, the bot fails to fetch the message content with a 404 error:

```
2026-06-11 08:35:44 [DEBUG] [discord.http] GET https://discord.com/api/v10/channels/1502926836970291232/messages/1508736219281096804 with None has returned 404
2026-06-11 08:35:44 [WARNING] [src.discord_bot.bot_core] Failed to fetch message 1508736219281096804 from channel 1502926836970291232: 404 Not Found (error code: 10008): Unknown Message
```

### Root Cause

**Two bugs in `tool_executor.py` `_handle_channel_search()` method (lines 744-769):**

1. **`message_id` is never passed to `get_channel_messages()`**: The `message_id` is extracted from args (line 744) but never forwarded to `bot.get_channel_messages()` (lines 746-754).

2. **Wrong channel ID used for message fetch** (lines 759-763): After the search returns messages, the code tries to fetch the specific message using `messages[0].get("channel_id")` — which is the channel where the **search matched**, NOT the channel where the **message link was found**. This causes a 404 because the message ID doesn't exist in that channel.

**Data flow problem**: When a user shares a Discord message link like:
`discordapp.com/channels/1502926835862863944/1503498099081871470/1508736219281096804`

The regex extracts: `guild_id=1502926835862863944`, `channel_id=1503498099081871470`, `message_id=1508736219281096804`

But `channel_search` is called with `channel=""` (all channels), so it searches across channels. When it finds matching messages, those messages may be from a **different channel** than the one in the link. The code then tries to fetch `message_id` from that wrong channel → 404.

### Files to Modify
- `src/discord_bot/tool_executor.py`
- `src/discord_bot/bot_core.py`
- `src/discord_bot/message_router.py`

### Changes Required

#### 1. Pass `message_id` to `get_channel_messages()` in `tool_executor.py` (line 746-754)
```python
# BEFORE:
result = await bot.get_channel_messages(
    channel=str(channel),
    limit=int(limit),
    search_query=str(search_query),
    username=str(username),
    compress_long=bool(compress_long),
    offset=int(offset),
    windows=int(windows),
)

# AFTER:
result = await bot.get_channel_messages(
    channel=str(channel),
    limit=int(limit),
    search_query=str(search_query),
    username=str(username),
    compress_long=bool(compress_long),
    offset=int(offset),
    windows=int(windows),
    message_id=message_id,  # ← ADD THIS
)
```

#### 2. Accept `message_id` parameter in `bot_core.py` `get_channel_messages()` method
```python
# Add message_id parameter to the method signature
async def get_channel_messages(
    self,
    channel: str = "",
    limit: int = 15,
    search_query: str = "",
    username: str = "",
    compress_long: bool = True,
    offset: int = 0,
    windows: int = 1,
    message_id: Optional[int] = None,  # ← ADD THIS
) -> Dict[str, Any]:
```

When `message_id` is provided, directly fetch that specific message from its channel instead of doing a channel search.

#### 3. Use correct channel_id in `tool_executor.py` (lines 759-769)
The `message_router.py` should pass both `channel_id` and `message_id` from the link parsing. The `tool_executor.py` should use the **original channel_id from the message link** (not `messages[0].get("channel_id")`) when fetching the specific message.

### Verification Steps
1. Send a message containing a Discord message link
2. Confirm the bot successfully fetches the message content (no 404 error)
3. Confirm the bot responds with the correct message content

---

## 🆕 Phase 0: Max Tool Calls Limit Increase (NEW — 2026-06-10 Terminal Log)

**Issues**: BUG-SEARCH-006
**Estimated Time**: 5 minutes
**Risk**: Very Low — Simple constant change

### Problem (from terminal.log 2026-06-10 22:21)

`MAX_TOOL_CALLS_PER_SESSION` is set to 3, which is too low for batched summarization workflows. The observed sequence was:

1. Turn 1: `channel_search` tool call → 15 messages fetched → batched summarization (2 LM calls for 2 batches) → empty summaries
2. Turn 2: LM re-calls `channel_search` → same empty result
3. Turn 3: Another tool call → max reached → force-response triggered
4. Force-response gives: "I couldn't find that specific message in the channel..."

**Terminal Evidence**:
```
22:21:32 [WARNING] [src.discord_bot.message_processor] Max tool calls (3) reached for channel 1503498074851508476, forcing response
22:21:37 [INFO] [src.discord_bot.message_processor] Final response obtained: "I couldn't find that specific message in the channel..."
```

### Root Cause

1. `MAX_TOOL_CALLS_PER_SESSION = 3` does not account for batched summarization which requires 2+ LM calls per tool execution.
2. The force-response mechanism adds a hint message but does NOT inject the actual tool results, leaving the LM without data.

### Files to Modify
- `src/discord_bot/message_processor.py`

### Changes Required

#### 1. Increase MAX_TOOL_CALLS_PER_SESSION
```python
# BEFORE:
MAX_TOOL_CALLS_PER_SESSION = 3

# AFTER:
MAX_TOOL_CALLS_PER_SESSION = 10  # Increased to accommodate batched summarization
```

#### 2. Enhance force-response mechanism to inject tool results
When max is reached, inject the actual tool results (not just a hint) so the LM can form a meaningful response.

### Verification Steps
1. Run bot, send a message that triggers `channel_search` with 15+ messages
2. Confirm the bot completes batched summarization without hitting max tool calls
3. Confirm the bot responds with useful information from the search results

---

## 🆕 Phase 0.5: Empty Batch Summaries Debug (NEW — 2026-06-10 Terminal Log)

**Issues**: BUG-SEARCH-005
**Estimated Time**: 30 minutes
**Risk**: Medium — Changes summarization logic

### Problem (from terminal.log 2026-06-10 22:21)

The `channel_search` tool uses batched mini-context summarization for large result sets. When the LM model summarizes each batch, it returns **empty content** for all batches:

```
22:21:14 [INFO] [src.discord_bot.tool_executor] [channel_search] Batch 1 summary content: ''
22:21:14 [INFO] [src.discord_bot.tool_executor] [channel_search] Summarizing batch 2 (messages 11-15/15)
22:21:32 [INFO] [src.discord_bot.tool_executor] [channel_search] Batch 2 summary content: ''
22:21:32 [INFO] [src.discord_bot.tool_executor] [channel_search] Final combined result (183 chars): "📋 Channel Search Results (batch-summarized from 15 messages):

Search query: ''

--- Batch 1 Summary ---


--- Batch 2 Summary ---


Total messages searched: 15
=== END OF RESULTS ==="
```

### Root Cause

The `_summarize_channel_search_batched()` method in `tool_executor.py` sends messages to LM Studio with a summarization prompt, but the model returns empty content. Possible causes:
1. The summarization prompt lacks explicit instruction to list image URLs and key content.
2. The message formatting may not provide enough structured context.
3. The LM model may not recognize the summarization task as requiring output.

### Files to Modify
- `src/discord_bot/tool_executor.py`

### Changes Required

#### 1. Enhance the summarization prompt
Add explicit instruction to the summarization prompt:
```
IMPORTANT: Summarize the key content of these messages. If any messages contain image URLs, list them. If any messages contain important information, mention it. Do NOT return an empty summary.
```

#### 2. Add fallback when LM returns empty summary
If the LM returns empty content for a batch, fall back to direct formatting for that batch:
```python
if not summary or not summary.strip():
    # LM returned empty, use direct formatting as fallback
    summary = self._format_channel_search_direct(batch_messages)
```

### Verification Steps
1. Run bot, send a message that triggers `channel_search` with 15+ messages
2. Confirm batch summaries contain actual content (not empty)
3. Confirm the final combined result has meaningful information

---

## Phase 1: Empty Response Detection & None Crash Fix

---

## Phase 1: Empty Response Detection & None Crash Fix

**Issues**: BUG-HANG-003 + BUG-HANG-004
**Estimated Time**: 15 minutes
**Risk**: Low — Simple, targeted fixes

### Problem
1. **BUG-HANG-003**: LM Studio returns whitespace-only content (`'\n\n'`) after tool processing. The bot treats this as valid and posts empty content to Discord.
2. **BUG-HANG-004**: When `response_text` is `None`, the error logging code crashes with `TypeError: 'NoneType' object is not subscriptable` because it tries to slice `response_text[:50]`.

### Root Cause
- `_is_empty_response()` only checks `not response_text` which is `False` for whitespace strings.
- `response_text[:50]` is called without null check.

### Files to Modify
- `src/discord_bot/message_processor.py`

### Changes Required

#### 1. Fix `_is_empty_response()` method (line ~996)
```python
# BEFORE:
def _is_empty_response(self, text: Optional[str]) -> bool:
    """Check if a response is effectively empty (None, empty string, or whitespace-only)."""
    ...

# AFTER:
def _is_empty_response(self, text: Optional[str]) -> bool:
    """Check if a response is effectively empty (None, empty string, or whitespace-only)."""
    return not text or not text.strip()
```

#### 2. Fix None slicing in `_process_session()` (line ~333)
```python
# BEFORE:
response_text_safe = response_text if response_text is not None else "(None)"
logger.warning(
    f"[empty_response] Channel {channel_id}: empty/whitespace response after tool processing. "
    f"final_tool_calls=present, failed_tool_turns={len(failed_tool_turns)}, "
    f"response={repr(response_text_safe[:50])}"
)

# AFTER: (already fixed in current code — verify it's correct)
response_text_safe = response_text if response_text is not None else "(None)"
```

#### 3. Fix None slicing in `process_active_session()` (line ~714)
```python
# BEFORE:
response_text_safe = response_text if response_text is not None else "(None)"

# AFTER: (verify it's correct — should already be guarded)
```

### Verification Steps
1. Run bot, send a message that triggers tool processing
2. Confirm no empty responses are posted to Discord
3. Confirm no TypeError crashes in logs
4. Confirm fallback message is shown: "Sorry, I couldn't generate a response..."

---

## Phase 2: Tool Call Loop Fix

**Issue**: BUG-013
**Estimated Time**: 30 minutes
**Risk**: Medium — Changes core processing logic

### Problem
The LM Studio model calls `channel_search` up to 5 times without using the returned results. After hitting limits, it returns empty content.

### Root Cause
1. Tool results are appended to conversation history but the model doesn't recognize them as sufficient.
2. After max_tool_calls, the model returns `'\n\n'` (empty).
3. No explicit instruction tells the model to use the gathered data.

### Files to Modify
- `src/discord_bot/message_processor.py`
- `src/discord_bot/tool_executor.py`

### Changes Required

#### 1. Add force-response injection in `_process_session()` (around line 306)
When a tool exceeds its call limit, inject a system message with the gathered tool results:

```python
# After: if exceeded_tool:
# Add explicit instruction to respond
messages_for_lm.append({
    "role": "user",
    "content": (
        f"You have called '{exceeded_tool}' too many times. You MUST now respond to the user "
        f"with a direct answer based on the information you already have. Do NOT call any more tools.\n\n"
        f"Here is the data you have already gathered:\n"
        f"{_extract_gathered_tool_results(messages_for_lm)}"
    )
})
```

#### 2. Add `_extract_gathered_tool_results()` helper method
```python
def _extract_gathered_tool_results(self, messages: List[Dict]) -> str:
    """Extract tool results from conversation history for force-response injection."""
    results = []
    for msg in reversed(messages[-10:]):  # Last 10 messages
        if msg.get("role") == "tool":
            content = msg.get("content", "")
            if content and not content.startswith("Error"):
                results.append(content)
    return "\n\n".join(results[-3:]) if results else "No tool results available."
```

#### 3. Add explicit instruction in tool result format (`tool_executor.py`)
After each `channel_search` result, append:
```
---
NOTE: You have now searched the channel. Use this data to respond to the user's question.
Do NOT call channel_search again unless you have a specific reason.
```

### Verification Steps
1. Send a message that triggers `channel_search`
2. Confirm the model uses the search results instead of re-calling
3. Confirm the model responds to the user's question
4. Check logs for "forcing response" messages

---

## Phase 3: Context Size Reduction

**Issue**: BUG-HANG-001
**Estimated Time**: 15 minutes
**Risk**: Low — Configuration change

### Problem
Conversation history grows to 11,244+ tokens, causing context overload. The model burns all available tokens on reasoning/context before responding.

### Root Cause
- `MAX_HISTORY_MESSAGES = 20` in `message_processor.py` is too large for most models.
- No context size monitoring.

### Files to Modify
- `src/discord_bot/message_processor.py`

### Changes Required

#### 1. Reduce history limit
```python
# BEFORE:
MAX_HISTORY_MESSAGES = 20

# AFTER:
MAX_HISTORY_MESSAGES = 12  # Reduced from 20 to prevent context overload
```

#### 2. Add context size monitoring (optional, future)
```python
# Track token usage per turn
def _estimate_prompt_tokens(self, messages: List[Dict]) -> int:
    """Rough estimate of prompt token count."""
    # Simple character-based estimate: ~1 token per 4 characters
    total_chars = sum(len(str(msg)) for msg in messages)
    return total_chars // 4
```

### Verification Steps
1. Run bot through an extended conversation
2. Confirm context stays under 80% of model's max tokens
3. Confirm no more context overload hangs

---

## Phase 4: Image URL Preservation in Summarization

**Issues**: BUG-SEARCH-003 + BUG-SEARCH-004
**Estimated Time**: 30 minutes
**Risk**: Medium — Changes summarization flow

### Problem
When `channel_search` uses batched summarization for large result sets, the LM returns empty summaries, losing image URL data.

### Root Cause
1. The summarization prompt doesn't explicitly ask for image URLs.
2. The model returns empty content for the summarization prompt.

### Files to Modify
- `src/discord_bot/tool_executor.py`

### Changes Required

#### 1. Add explicit instruction to summarization prompt
```python
# In _format_messages_for_summarization():
# Add to the system prompt:
"IMPORTANT: If any messages contain image URLs, list them in your summary. "
"Format: 'Images found: [URL1], [URL2]'"
```

#### 2. Extract and append image URLs after summarization
```python
# In _summarize_channel_search_batched():
# After getting LM summary, extract image URLs from original messages
image_urls = []
for msg in batch_messages:
    urls = msg.get("image_urls", [])
    image_urls.extend(urls)

if image_urls:
    summary += f"\n\nImages found: {', '.join(image_urls)}"
```

### Verification Steps
1. Search for a message containing an image
2. Confirm image URLs appear in the search result
3. Confirm the main bot can use `image_compare` with those URLs

---

## Phase 5: Cancellation System Fixes

**Issues**: BUG-CANCEL-001 through BUG-CANCEL-005
**Estimated Time**: 30 minutes
**Risk**: Low — Wiring fixes

### Problem
The cancellation system exists but is broken due to method name mismatches, missing imports, and missing wiring.

### Root Cause
1. `bot_core.py` calls `manager.cancel()` but method is `request_cancel()` (BUG-CANCEL-001)
2. Cancellation not imported in `bot_core.py` (BUG-CANCEL-005)
3. `_process_tool_calls_with_status()` exists but is never called (BUG-CANCEL-002)
4. No `/cancel` command (BUG-CANCEL-004)

### Files to Modify
- `src/discord_bot/bot_core.py`
- `src/discord_bot/message_processor.py`
- `src/discord_bot/message_handler.py`

### Changes Required

#### 1. Add missing import in `bot_core.py`
```python
from src.discord_bot.cancellation import get_cancellation_manager
```

#### 2. Fix method name in `cancel_session()`
```python
# BEFORE:
manager.cancel(channel_id)

# AFTER:
await manager.request_cancel(channel_id)
```

#### 3. Wire `_process_tool_calls_with_status()` into pipeline
```python
# In message_processor.py, replace:
self._tool_call_handler.process_tool_calls(...)

# With:
await self._process_tool_calls_with_status(...)
```

#### 4. Add `/cancel` command detection
```python
# In message_handler.py handle_new_session():
if message.content.strip().lower() in ('/cancel', '!stop'):
    await message.channel.send("Session cancelled.")
    # Trigger cancellation
```

### Verification Steps
1. Start a long-running tool operation
2. Send `/cancel` or `/endsession`
3. Confirm the operation is interrupted

---

## Execution Order & Dependencies

```
Phase 1 (Empty Response Fix)
  ├── Phase 2 (Tool Call Loop) — depends on Phase 1 working
  │   └── Phase 4 (Image URLs) — depends on Phase 2 (search results must be used)
  ├── Phase 3 (Context Reduction) — independent, but helps all phases
  └── Phase 5 (Cancellation) — independent, but benefits from Phase 2 working
```

**Recommended Order**: Phase 1 → Phase 3 → Phase 2 → Phase 4 → Phase 5

---

## Testing Strategy

### Unit Tests
1. Test `_is_empty_response()` with various inputs: `None`, `''`, `'\n\n'`, `'hello'`
2. Test `_extract_gathered_tool_results()` with mixed conversation history
3. Test `_estimate_prompt_tokens()` with known message counts

### Integration Tests
1. Send a message that triggers `channel_search` — verify model uses results
2. Send a message in an extended conversation — verify no context overload
3. Search for an image — verify URLs are preserved
4. Send `/cancel` during tool execution — verify interruption

### Manual Testing
1. Run bot through a full conversation cycle
2. Test all tool calls (channel_search, image_compare, math_calc, memory_tool)
3. Test session start/end
4. Test cancellation

---

## Rollback Plan

If any fix causes issues:
1. **Phase 1**: Revert `_is_empty_response()` — no functional impact on normal responses
2. **Phase 2**: Revert force-response injection — model will still loop but won't crash
3. **Phase 3**: Revert `MAX_HISTORY_MESSAGES` to 20 — no functional impact
4. **Phase 4**: Revert summarization changes — image URLs will be lost but no crash
5. **Phase 5**: Revert cancellation wiring — no functional impact

All changes are isolated to specific methods and can be reverted with a single git revert.