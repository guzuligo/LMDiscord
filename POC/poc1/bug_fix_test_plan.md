# Bug Fix Test Plan

> **Created**: 2026-06-11
> **Purpose**: Verify all critical bug fixes are working correctly
> **Status**: Ready for testing

---

## Overview

This document provides step-by-step test procedures for all critical bug fixes applied to the Discord bot. Each test includes prerequisites, steps, expected results, and pass/fail criteria.

---

## Test Suite Summary

| Test ID | Bug ID | Description | Risk Level | Estimated Time |
|---------|--------|-------------|------------|----------------|
| T-001 | BUG-SEARCH-006 | Max Tool Calls Limit Increase | Low | 5 min |
| T-002 | BUG-SEARCH-006 | Force-Response Tool Result Injection | Low | 5 min |
| T-003 | BUG-SEARCH-005 | Batch Summarization Fallback | Medium | 10 min |
| T-004 | BUG-HANG-003 | Empty Response Detection | Low | 5 min |
| T-005 | BUG-CONTEXT-001 | ContextCompressorTool LM Client Fix | Medium | 10 min |
| T-006 | BUG-MESSAGE-001 | Message Link Fetch Failure (404 Not Found) | Low | 10 min |

---

## T-001: Max Tool Calls Limit Increase

**Bug**: `MAX_TOOL_CALLS_PER_SESSION` was 3, too low for batched summarization.

**Prerequisites**:
- Bot is running and connected to Discord
- LM Studio server is accessible
- Target channel has 15+ messages

**Steps**:
1. Open `src/discord_bot/message_processor.py`
2. Verify `MAX_TOOL_CALLS_PER_SESSION = 10` (or at least 6)
3. Send a message to the Discord channel that triggers `channel_search` with 15+ messages
4. Watch the terminal logs

**Expected Results**:
- Logs show `MAX_TOOL_CALLS_PER_SESSION = 10` (or 6+)
- Bot completes batched summarization without hitting the limit
- Bot responds with meaningful search results

**Pass Criteria**:
- [ ] `MAX_TOOL_CALLS_PER_SESSION` is set to 10 (or 6+)
- [ ] No "Max tool calls reached" warning appears during batched summarization
- [ ] Bot responds with search results

**Fail Criteria**:
- [ ] `MAX_TOOL_CALLS_PER_SESSION` is still 3
- [ ] Bot hits max tool calls before completing summarization

---

## T-002: Force-Response Tool Result Injection

**Bug**: Force-response mechanism added a hint but did NOT inject actual tool results.

**Prerequisites**:
- Same as T-001
- May need to artificially limit tool calls to trigger force-response

**Steps**:
1. Temporarily set `MAX_TOOL_CALLS_PER_SESSION = 2` in `message_processor.py` to force early trigger
2. Send a message that triggers `channel_search` with 10+ messages
3. Watch the terminal logs for force-response activation
4. Check the final bot response

**Expected Results**:
- Logs show: `Final response obtained: "..."` with actual content
- The force-response mechanism injects tool results into `messages_for_lm`
- Bot responds with meaningful information from search results

**Pass Criteria**:
- [ ] When force-response is triggered, tool results are injected into conversation history
- [ ] Bot response contains actual data from tool results (not generic "I couldn't find...")

**Fail Criteria**:
- [ ] Force-response produces generic fallback message
- [ ] Tool results are not injected into `messages_for_lm`

---

## T-003: Batch Summarization Fallback

**Bug**: LM returned empty summaries for all batches, resulting in empty final output.

**Prerequisites**:
- Same as T-001
- LM Studio server must be running

**Steps**:
1. Open `src/discord_bot/tool_executor.py`
2. Verify `_summarize_channel_search_batched()` has fallback logic
3. Send a message that triggers `channel_search` with 15+ messages
4. Watch the terminal logs for batch summarization

**Expected Results**:
- Logs show batch summarization progress: `Summarizing batch N (messages X-Y/15)`
- If LM returns empty content, fallback to `_format_channel_search_direct()` is triggered
- Logs show: `Batch N: No choices in LM response, using fallback` or `Mini-context summarization failed`
- Final combined result contains meaningful content (not empty)

**Pass Criteria**:
- [ ] Batch summarization prompt includes explicit instruction to list image URLs
- [ ] Fallback mechanism activates when LM returns empty content
- [ ] Final result contains actual message content

**Fail Criteria**:
- [ ] Empty summaries are returned without fallback
- [ ] No fallback mechanism exists in code

---

## T-004: Empty Response Detection

**Bug**: Whitespace-only responses (`'\n\n'`) were treated as valid, causing empty Discord posts.

**Prerequisites**:
- Bot is running

**Steps**:
1. Open `src/discord_bot/message_processor.py`
2. Verify `_is_empty_response()` method:
   ```python
   def _is_empty_response(self, text: Optional[str]) -> bool:
       return not text or not text.strip()
   ```
3. Test the method manually:
   ```python
   # In Python REPL:
   from src.discord_bot.message_processor import MessageProcessor
   mp = MessageProcessor()
   assert mp._is_empty_response(None) == True
   assert mp._is_empty_response("") == True
   assert mp._is_empty_response("\n\n") == True
   assert mp._is_empty_response("   ") == True
   assert mp._is_empty_response("hello") == False
   ```

**Expected Results**:
- `_is_empty_response()` returns `True` for `None`, `""`, `"\n\n"`, `"   "`
- `_is_empty_response()` returns `False` for non-empty strings

**Pass Criteria**:
- [ ] `_is_empty_response()` properly handles all edge cases
- [ ] No empty responses are posted to Discord

**Fail Criteria**:
- [ ] `_is_empty_response("\n\n")` returns `False`
- [ ] Empty responses are posted to Discord

---

## T-005: ContextCompressorTool LM Client Fix

**Bug**: `ContextCompressorTool` tried to create its own `LMStudioClient()` instance, which failed in tool execution context.

**Prerequisites**:
- Bot is running
- Conversation history has grown large enough to trigger context compression

**Steps**:
1. Open `src/tools/builtins/context_compressor.py`
2. Verify `_generate_lm_summary()` accepts `make_lm_call_func` parameter:
   ```python
   def _generate_lm_summary(
       self,
       messages_text: str,
       target_length: int,
       make_lm_call_func: Optional[Callable] = None
   ) -> Optional[str]:
   ```
3. Open `src/discord_bot/tool_executor.py`
4. Verify `_handle_context_compress()` passes `make_lm_call_func`:
   ```python
   async def _handle_context_compress(
       self,
       func_args: str,
       messages_for_lm: List[Dict],
       tool_call_id: str,
       make_lm_call_func: Optional[Any] = None
   ) -> Optional[str]:
   ```
5. Verify `compressor.execute()` receives `make_lm_call_func`:
   ```python
   result = compressor.execute(
       compress_before_index=compress_before_index,
       target_summary_length=target_summary_length,
       messages_to_keep_fresh=messages_to_keep_fresh,
       messages_for_lm=messages_for_lm,
       make_lm_call_func=make_lm_call_func
   )
   ```
6. Send a message that triggers `context_compress` tool call from the LM

**Expected Results**:
- `ContextCompressorTool` uses the injected `make_lm_call_func` instead of creating its own client
- No `LMStudioClient not connected` errors during context compression
- Context compression produces a valid summary

**Pass Criteria**:
- [ ] `_generate_lm_summary()` accepts and uses `make_lm_call_func`
- [ ] `_handle_context_compress()` passes `make_lm_call_func` to compressor
- [ ] Context compression works without LM client connection errors

**Fail Criteria**:
- [ ] `ContextCompressorTool` still creates its own `LMStudioClient()` instance
- [ ] Context compression fails with connection errors

---

## T-006: Message Link Fetch Failure (404 Not Found)

**Bug**: When a user shares a Discord message link, the bot fails to fetch the message content with a 404 error because `message_id` is not passed to `get_channel_messages()` and the wrong channel_id is used for message fetch.

**Prerequisites**:
- Bot is running
- LM Studio server is accessible
- A message exists in a channel that the bot can access

**Steps**:
1. Open `src/discord_bot/tool_executor.py`
2. Verify `_handle_channel_search()` passes `message_id` to `get_channel_messages()`:
   ```python
   result = await bot.get_channel_messages(
       channel=str(channel),
       limit=int(limit),
       search_query=str(search_query),
       username=str(username),
       compress_long=bool(compress_long),
       offset=int(offset),
       windows=int(windows),
       message_id=message_id,  # ← Must be present
   )
   ```
3. Open `src/discord_bot/bot_core.py`
4. Verify `get_channel_messages()` accepts `message_id` parameter:
   ```python
   async def get_channel_messages(
       self,
       channel: str = "",
       limit: int = 15,
       search_query: str = "",
       username: str = "",
       compress_long: bool = True,
       offset: int = 0,
       windows: int = 1,
       message_id: Optional[int] = None,  # ← Must be present
   ) -> Dict[str, Any]:
   ```
5. Verify that when `message_id` is provided, the method directly fetches that specific message from its channel
6. Send a message containing a Discord message link to the bot

**Expected Results**:
- Logs show `message_id` being passed to `get_channel_messages()`
- `get_channel_messages()` accepts `message_id` parameter
- When `message_id` is provided, the bot directly fetches the specific message
- No 404 error in logs
- Bot responds with the correct message content

**Pass Criteria**:
- [ ] `message_id` is passed to `get_channel_messages()` in `_handle_channel_search()`
- [ ] `get_channel_messages()` accepts `message_id` parameter
- [ ] When `message_id` is provided, the correct channel_id from the link is used for fetch
- [ ] Bot successfully fetches and responds with the message content (no 404 error)

**Fail Criteria**:
- [ ] `message_id` is not passed to `get_channel_messages()`
- [ ] Wrong channel_id is used for message fetch
- [ ] 404 error appears in logs
- [ ] Bot responds with "Channel not found" or "Unknown Message"

---

## Integration Test: Full Conversation Cycle

**Purpose**: Verify all fixes work together in a real conversation.

**Prerequisites**:
- Bot is running
- LM Studio server is accessible
- Target channel has 15+ messages

**Steps**:
1. Send a greeting message: `Hello bot`
2. Send a message that triggers `channel_search` with 15+ messages: `Search for recent messages in #general`
3. Send a follow-up question: `What were the key points from the search?`
4. Send a message that triggers context compression (if conversation is long enough)
5. Check terminal logs for any errors

**Expected Results**:
- Bot responds to greeting normally
- Bot completes `channel_search` with batched summarization (no empty results)
- Bot uses search results to answer follow-up question
- No empty responses posted
- No crashes or TypeError exceptions in logs

**Pass Criteria**:
- [ ] All tool calls complete successfully
- [ ] No empty responses
- [ ] No crashes or exceptions
- [ ] Bot provides meaningful responses throughout

---

## Quick Verification Commands

### Check MAX_TOOL_CALLS_PER_SESSION
```bash
grep -n "MAX_TOOL_CALLS_PER_SESSION" POC/poc1/src/discord_bot/message_processor.py
```
Expected: Should show value >= 6

### Check _is_empty_response
```bash
grep -A 2 "_is_empty_response" POC/poc1/src/discord_bot/message_processor.py
```
Expected: Should show `return not text or not text.strip()`

### Check ContextCompressorTool make_lm_call_func
```bash
grep -n "make_lm_call_func" POC/poc1/src/tools/builtins/context_compressor.py
```
Expected: Should show parameter in `_generate_lm_summary()` signature

### Check tool_executor passes make_lm_call_func
```bash
grep -n "make_lm_call_func" POC/poc1/src/discord_bot/tool_executor.py
```
Expected: Should show parameter in `_handle_context_compress()` and `_handle_context_compress_active()`

---

## Results Tracking

| Test ID | Status | Notes | Date |
|---------|--------|-------|------|
| T-001 | ⬜ Pending | | |
| T-002 | ⬜ Pending | | |
| T-003 | ⬜ Pending | | |
| T-004 | ⬜ Pending | | |
| T-005 | ⬜ Pending | | |
| T-006 | ⬜ Pending | | |
| Integration | ⬜ Pending | | |

---

## Rollback Instructions

If any fix causes issues:

1. **T-001**: Revert `MAX_TOOL_CALLS_PER_SESSION` to 3
2. **T-002**: Remove tool result injection from force-response block
3. **T-003**: Remove fallback logic from `_summarize_channel_search_batched()`
4. **T-004**: Revert `_is_empty_response()` to `return not text`
5. **T-005**: Revert `ContextCompressorTool` to create its own `LMStudioClient()` instance
5. **T-006**: Revert `message_id` parameter removal from `get_channel_messages()` and `tool_executor.py`

All changes are isolated and can be reverted with a single `git revert`.