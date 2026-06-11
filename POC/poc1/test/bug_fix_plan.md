# Bug Fix Plan — Critical Issues

> **Created**: 2026-06-05
> **Priority**: Critical — Bot hangs and fails to respond
> **Estimated Total Time**: ~2 hours

---

## Overview

The bot is experiencing critical failures where it hangs, posts empty responses, or crashes. This plan addresses the 4 most critical issues in priority order, with dependencies tracked.

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