# Issues Tracker - POC: test1

> **Solved issues details have been moved to [solved_issues.md](solved_issues.md).** This file contains current open, planned, and documented issues with full details, plus titles of resolved issues for reference.

---

## Solved Issues (Titles Only — Full Details in [solved_issues.md](solved_issues.md))

### Infrastructure & Setup
- [ISS-001](solved_issues.md#iss-001): tkinter Not Available in Python 3.13 venv ✅
- [ISS-002](solved_issues.md#iss-002): Corrupted venv Directory ✅
- [ISS-003](solved_issues.md#iss-003): pip Command Not Found (sudo) ✅

### Discord Bot Core
- [ISS-006](solved_issues.md#iss-006): Infinite `show_typing` Tool Calling Loop ✅
- [ISS-007](solved_issues.md#iss-007): Typing Indicator Not Showing ✅
- [ISS-008](solved_issues.md#iss-008): Duplicate Goodbye Message on Session End ✅
- [ISS-009](solved_issues.md#iss-009): Messages Lost During Active Session Processing ✅
- [ISS-010](solved_issues.md#iss-010): Security - Error Tracebacks Exposed to Discord Users ✅
- [ISS-011](solved_issues.md#iss-011): Duplicate Message Handlers Running Simultaneously ✅
- [ISS-012](solved_issues.md#iss-012): Empty Messages Cause LM Studio API Errors ✅
- [ISS-013](solved_issues.md#iss-013): Discord Disconnect Button Not Working ✅
- [ISS-014](solved_issues.md#iss-014): discord_bot.py Too Large for Maintenance ✅
- [ISS-016](solved_issues.md#iss-016): Queue Not Checked After New Session ✅
- [ISS-017](solved_issues.md#iss-017): No Typing Indicator When Processing Queued Messages ✅
- [ISS-018](solved_issues.md#iss-018): Active Session Context Loss - Bot Forgets Previous Messages ✅
- [ISS-019](solved_issues.md#iss-019): DelayProcessor Parameter Mismatch ✅
- [ISS-020](solved_issues.md#iss-020): Concurrent LM Studio Requests Causing OOM Risk ✅
- [ISS-021](solved_issues.md#iss-021): DelayProcessor Handler Callback Signature Mismatch ✅
- [ISS-022](solved_issues.md#iss-022): Modular Refactoring of message_handler.py ✅
- [ISS-023](solved_issues.md#iss-023): Modular Refactoring of bot_core.py ✅

### Discord UI & API
- [DISCORD-001](solved_issues.md#discord-001): Discord Bot Stuck After Flask App Restart ✅
- [DISCORD-002](solved_issues.md#discord-002): UI Shows "Not Connected" Despite Bot Thread Running ✅
- [DISCORD-003](solved_issues.md#discord-003): UnboundLocalError in get_sessions ✅
- [UX-001](solved_issues.md#ux-001): Server Config Missing Auto-Discovery Features ✅
- [BUG-004](solved_issues.md#bug-004): Channel Filter Shows Empty Config Due to Server ID Mismatch ✅
- [BUG-005](solved_issues.md#bug-005): Server Config Changes Not Applied to Running Bot ✅
- [BUG-006](solved_issues.md#bug-006): Auto-Discover Returns Wrong Server ID ✅

### LM Studio & Model Integration
- [REASONING-FIX](solved_issues.md#reasoning-fix): Model Excessive Reasoning Causing 120s Read Timeout ✅
- [BUG-010](solved_issues.md#bug-010): LM Instance Model Selection Not Activating ✅
- [HANG-001](solved_issues.md#hang-001): NameError — undefined 'timeout' variable in bot_core.py ✅
- [FIX-HANG-001](solved_issues.md#fix-hang-001): N+1 Query Fix + max_tool_calls Enforcement ✅
- [BUG-016](solved_issues.md#bug-016): LM Studio Model Loading Error Leaks Internal Details ✅

### Image Processing
- [BUG-002](solved_issues.md#bug-002): Image Describe Breaks Conversation Flow & Causes 400 Errors ✅
- [BUG-002 (CDN)](solved_issues.md#bug-002-cdn): image_describe Fails on Discord CDN Images ✅
- [BUG-007](solved_issues.md#bug-007): image_describe Tool Not Called by LM Studio Model ✅
- [BUG-009](solved_issues.md#bug-009): image_describe channel_id Duplicate Keyword Argument ✅
- [BUG-011](solved_issues.md#bug-011): Channel Name Resolution Fails for `#general` ✅
- [BUG-014 (image URLs)](solved_issues.md#bug-014-image-urls): channel_search Cannot Fetch Image URLs ✅
- [BUG-014 (embeds)](solved_issues.md#bug-014-embeds): channel_search Only Checks Attachments, Not Embeds ✅
- [BUG-017 (reply)](solved_issues.md#bug-017-reply): image_compare Fails on Expired CDN URLs from Referenced Messages ✅
- [BUG-UX-002-REG](solved_issues.md#bug-ux-002-reg): image_compare Infinite Loop ✅
- [UX-002](solved_issues.md#ux-002): Mini-Context Image Descriptions Use Generic Prompt ✅
- [UX-003](solved_issues.md#ux-003): image_compare Uses 3-Step Describe-Then-Compare ✅
- [BUG-IMG-001](#bug-img-001): image_describe/image_compare Consolidated into Single Tool ✅

### Message Processing & Tool Calling
- [CHANNEL-001](solved_issues.md#channel-001): channel_search Result Format Causes LM Misinterpretation ✅
- [FIX-003](solved_issues.md#fix-003): Empty Response After Tool Processing (max_tokens Overflow) ✅
- [FIX-004](solved_issues.md#fix-004): image_compare Discord CDN URL Retry ✅
- [BUG-007 (duplicate)](solved_issues.md#bug-007-duplicate): max_tokens Retry Loop Exits Early ✅
- [FIX-001](solved_issues.md#fix-001): Enhanced Tool Result Message to Prevent Re-calling ✅
- [FIX-002](solved_issues.md#fix-002): Handle URL Strings Passed as image_data Parameter ✅

### Memory System
- [REQ-004](solved_issues.md#req-004): Discord Bot Integration ✅
- [CONCEPT-001](solved_issues.md#concept-001): Wake-up Memory System ✅
- [CONCEPT-003](solved_issues.md#concept-003): MemoryBot Architecture with Multi-Turn Search ✅
- [FIX-MEMORY-001](solved_issues.md#fix-memory-001): LM Studio Not Calling memory_tool ✅
- [FIX-MEMORY-002](solved_issues.md#fix-memory-002): Default Memory Database Path Changed ✅

### Tools & Built-ins
- [FEAT-002](solved_issues.md#feat-002): Discord Channel Search Tool (Server Config UI Filter) ✅
- [FEAT-006](solved_issues.md#feat-006): LM Studio Multi-Instance Management ✅
- [FEAT-007](solved_issues.md#feat-007): New image_compare Tool for Multi-Image Comparison ✅
- [BUG-008](solved_issues.md#bug-008): Debug Panel Sessions API Error ✅

### Configuration & Settings
- [BUG-003](solved_issues.md#bug-003): Bot Cannot Identify Discord Users ✅
- [STATUSMSG-001](solved_issues.md#statusmsg-001): Status Message Now Requires LLM-Generated Text ✅
- [PENDING-002](solved_issues.md#pending-002): Hardcoded Turn Limit in Message Processing ✅
- [PENDING-004](solved_issues.md#pending-004): Session State Consistency on Processing Failure ✅
- [PENDING-005](solved_issues.md#pending-005): Missing src/utils.py Import Verification ✅

### Refactoring & Code Quality
- [CSS-001](solved_issues.md#css-001): CSS Files Too Large - Over-Engineered Styling ✅
- [ISS-024](#iss-024): Message Router Module Not Documented ✅ (documented 2026-06-04)
- [ISS-025](#iss-025): Cancellation Module Not Documented ✅ (documented 2026-06-04)

### Debugging & Development Tools
- [DEBUG-001](solved_issues.md#debug-001): Debug Page Not Showing Logs ✅
- [DEBUG-002](solved_issues.md#debug-002): JavaScript Syntax Error on Token Refresh ✅
- [DEBUG-003](solved_issues.md#debug-003): Discord Status Always Shows "Not Connected" ✅
- [BUG-LOG-001](solved_issues.md#bug-log-001): Terminal Log File Gets Deleted/Cleared ✅

---

## Pending Issues

### 📋 ISS-024: Message Router Module — Undocumented Architecture

| Field | Value |
|-------|-------|
| **ID** | ISS-024 |
| **Date** | 2026-06-04 |
| **Status** | ✅ Documented (Code Audit) |
| **Severity** | Low (documentation only) |
| **Description** | `src/discord_bot/message_router.py` (538 lines) exists as a dedicated message routing module but was not documented in any tracking file. Code audit confirms it is fully wired and functional. |
| **Module Purpose** | Routes incoming Discord messages to appropriate handlers: new session handling, active session batch processing, queued pending messages, image attachment extraction, display name resolution. |
| **Key Class** | `MessageRouter` — initialized with bot_instance, session_manager, processing_lock, pending_messages, conversation_history, typing_indicator, delay_processor, lm_studio_lock, config. |
| **Key Methods** | `get_display_name_for_user()` — resolves best name for addressing user. `extract_image_attachments()` — extracts images from message attachments and embeds. `handle_on_message()` — main entry point for incoming messages, handles mention/reply detection, channel filtering, session state checks. `_handle_new_session_message()` — starts new sessions with identity info and wake-up memory. `_process_active_session_batch()` — processes active session messages with pending message support. `_process_queued_pending_messages()` — processes queued messages after posting a response. |
| **Wiring Status** | ✅ Fully wired — instantiated in `bot_core.py` as `self._message_router`, called from `_handle_on_message()`. |
| **Note** | This module was likely created as part of ISS-022 (modular refactoring of message_handler.py) but the documentation was never updated to reflect the new module. |

---

### 📋 ISS-025: Cancellation Module — Undocumented Architecture

| Field | Value |
|-------|-------|
| **ID** | ISS-025 |
| **Date** | 2026-06-04 |
| **Status** | ✅ Documented (Code Audit) |
| **Severity** | Low (documentation only) |
| **Description** | `src/discord_bot/cancellation.py` (228 lines) exists as a dedicated cancellation management module but was not documented in any tracking file. Code audit confirms it is wired into `bot_core.py` but has known bugs (see BUG-CANCEL-001 through BUG-CANCEL-005 in this file). |
| **Module Purpose** | Provides cancellation support for long-running bot operations: per-channel cancellation tracking, global cancellation management, cancel command support. |
| **Key Class** | `CancellationEvent` — per-channel cancellation tracking with asyncio.Event. `CancellationManager` — global singleton manager for all cancellation events. |
| **Key Methods** | `request_cancel()` — request cancellation of a channel's operation. `reset_event()` — reset cancellation event after operation completes. `check_and_reset()` — check cancellation status and reset atomically. `check_during_execution()` — check cancellation without consuming (for repeated checks during long operations). `get_all_events()` — get status of all cancellation events. `cleanup_inactive()` — remove events for inactive channels. |
| **Wiring Status** | ⚠️ Partially wired — `bot_core.py` imports `get_cancellation_manager()` in `cancel_session()` and `cancellation_manager` property. However, known bugs exist: method name mismatch (BUG-CANCEL-001), missing import (BUG-CANCEL-005), no command trigger (BUG-CANCEL-004), not checked during tool execution (BUG-CANCEL-002). |
| **Related Issues** | BUG-CANCEL-001 through BUG-CANCEL-005, BUG-HANG-002 |

---

### 🔄 PENDING-001: Error Handling in channel.send() After LM Studio Failures

| Field | Value |
|-------|-------|
| **ID** | PENDING-001 |
| **Date** | 2026-05-21 |
| **Status** | 🔄 Open |
| **Severity** | Low |
| **Description** | In `message_processor.py`, when a `ConnectionError` or general `Exception` occurs during LM Studio response, `await channel.send(response_text)` is called without error handling. If the send fails (e.g., channel deleted, bot missing permissions, Discord API error), the error propagates unhandled. |
| **Code Location** | `src/discord_bot/message_processor.py` → `_process_session()` lines 184-201 |
| **Recommended Fix** | Wrap `channel.send()` in try/except to handle `discord.HTTPException`, `discord.Forbidden`, `discord.NotFound` gracefully. Log the failure but don't crash the processing pipeline. |
| **Files To Modify** | `src/discord_bot/message_processor.py` |

---

### 🔄 PENDING-003: Config Path Dependency Hardcoded

| Field | Value |
|-------|-------|
| **ID** | PENDING-003 |
| **Date** | 2026-05-21 |
| **Status** | 🔄 Open |
| **Severity** | Low |
| **Description** | Config path in `app.py` is computed as `Path(__file__).parent.parent / "config.json"` which assumes a specific project structure. If files are moved or the app is deployed differently, the config may not be found. |
| **Code Location** | `src/app.py` line 598 |
| **Recommended Fix** | Use an environment variable (e.g., `LM_CONFIG_PATH`) with fallback to the default path. |
| **Files To Modify** | `src/app.py` |

---

## Known Bugs (Not Yet Fixed)

---

### 📋 BUG-HANG-001: Bot Hangs — Context Overload (LM Studio Returns Empty Content + Tool Calls)

| Field | Value |
|-------|-------|
| **ID** | BUG-HANG-001 |
| **Date** | 2026-06-03 |
| **Status** | 🔴 Confirmed Active — Terminal Log Evidence (2026-06-04) |
| **Severity** | Critical |
| **Description** | The bot appears to hang when users send messages. Typing indicator appears, then silence — no response posted to Discord. Root cause: LM Studio API returns HTTP 200 with empty `content` AND tool calls. The force-response break logic discards tool calls (max tool calls reached), resulting in empty text response (`'\n\n'`), which is not sent to Discord. |
| **Log Evidence** | ```17:17:52.334 - Waiting for LM Studio lock ... 17:18:03.112 - LM Studio API response: 200 1938 bytes (10.8s call) 17:18:03.113 - WARNING: Final response still had tool calls, discarding them (max_tool_turns=5 reached) 17:18:03.113 - INFO: Final response obtained: '\n\n'    ← EMPTY 17:18:03.113 - INFO: LM Studio used tool call, no text response to post``` |
| **New Evidence (2026-06-04)** | Terminal log shows **5 instances** of empty content responses across multiple sessions: ```09:45:47 - Turn 1: content='\n\n' 09:45:52 - Turn 2: content='\n\n' 09:46:14 - Turn 3: content='\n\n' 09:48:00 - Turn 1: content='\n\n' 09:49:07 - Turn 3: content='\n\n'``` |
| **Root Cause** | **Context overload**: Conversation history grew to 11,244+ prompt tokens (max is typically 16K-32K). The model burns all available tokens on reasoning/context before responding, leaving no room for actual content. |
| **Trigger Pattern** | Occurs after extended conversation sessions with many messages, tool calls (especially image operations), and channel searches. |
| **Related Issues** | ISS-018 (context overflow fix kept history to 20 messages), FIX-003 (max_tokens retry logic), BUG-013 (channel_search tool call loop), BUG-015 (channel_search rate limit exhaustion) |
| **Proposed Fix** | **Short-term**: 1. Reduce conversation history limit from 20 messages to 10-12. 2. Add context size monitoring — if prompt tokens >80% of model max, auto-truncate. 3. Add explicit system message after force-response break. **Long-term**: 1. Implement context compression (FEAT-008). 2. Add automatic memory offloading for old messages. 3. Monitor token usage per turn and warn/cap. |
| **Files To Modify** | `src/discord_bot/message_processor.py`, `src/discord_bot/message_handler.py`, `src/config.py` |

---

### 📋 BUG-HANG-003: Bot Posts Empty/Whitespace Response After Tool Processing (Empty Detection Bug)

| Field | Value |
|-------|-------|
| **ID** | BUG-HANG-003 |
| **Date** | 2026-06-04 |
| **Status** | 🔴 Confirmed — Terminal Log Evidence (2026-06-04) |
| **Severity** | Critical |
| **Description** | After tool execution completes, LM Studio API returns HTTP 200 with empty/whitespace content (`'\n\n'`). The bot treats this as a valid response and posts empty content to Discord. The existing fallback logic in `message_processor.py` does not catch whitespace-only strings because `not '\n\n'` evaluates to `False` in Python. |
| **Log Evidence** | ```09:45:47 - INFO - Turn 1: content='''\n\n''', tool_calls=0 09:45:47 - INFO - Got final response on turn 1 09:45:47 - INFO - Response posted to Discord 09:45:48 - INFO - CLEARED session for channel 1432099372148165396```<br>```09:45:52 - Turn 2: content='\n\n', tool_calls=0 09:46:14 - Turn 3: content='\n\n', tool_calls=0 09:48:00 - Turn 1: content='\n\n', tool_calls=0 09:49:07 - Turn 3: content='\n\n', tool_calls=0``` |
| **Root Cause** | 1. LM Studio returns whitespace-only content (`'\n\n'`) after tool processing. 2. Existing fallback in `message_processor.py` checks `not response_text` which is `False` for whitespace strings. 3. The fallback only triggers when `response_text` is empty/None, not when it's whitespace-only. |
| **Existing Fallback Code** | ```python # Fallback: if max turns exhausted with no text response, send something if not response_text and final_tool_calls: response_text = "I've processed the available information but couldn't generate a complete response..." elif not response_text and final_tool_calls is None: response_text = "Sorry, I couldn't generate a response. This might be a temporary issue..."``` |
| **Problem with Existing Fallback** | `not '\n\n'` → `False`, so the fallback conditions are never met for whitespace responses. |
| **Related Issues** | BUG-HANG-001 (context overload), BUG-013 (tool call loop), FIX-003 (max_tokens retry logic) |
| **Proposed Fix** | 1. **Enhance empty detection**: Change `not response_text` to `not response_text or not response_text.strip()`. 2. **Inject tool results**: When empty response detected, inject a system message with gathered tool results before forcing a response. 3. **Retry mechanism**: After injecting results, call LM Studio one more turn with explicit instruction to respond using the data. |
| **Implementation Plan** | **Priority 1** — Highest impact, lowest risk. Modify `_process_session()` and `process_active_session()` in `message_processor.py`: ```python def _is_empty_response(text): return not text or not text.strip() # Usage: if _is_empty_response(response_text) and final_tool_calls: # Inject tool results as system message # Retry one more turn with explicit instruction ``` |
| **Files To Modify** | `src/discord_bot/message_processor.py` → `_process_session()` and `process_active_session()` methods |

---

### 📋 BUG-HANG-004: TypeError — response_text[:50] Crashes When response_text Is None

| Field | Value |
|-------|-------|
| **ID** | BUG-HANG-004 |
| **Date** | 2026-06-04 |
| **Status** | 🔴 Confirmed — Terminal Log Evidence (2026-06-04) |
| **Severity** | Critical |
| **Description** | When LM Studio returns `None` for `response_text` (not just empty string), the error logging code at line 335 in `message_processor.py` crashes with `TypeError: 'NoneType' object is not subscriptable` because it tries to slice `response_text[:50]` without checking for None first. |
| **Log Evidence** | ```09:49:13 - TypeError: 'NoneType' object is not subscriptable File ".../message_processor.py", line 335, in _process_session f"response={repr(response_text[:50])}"``` |
| **Root Cause** | 1. LM Studio returns `None` for `response_text` (not `'\n\n'` or `''`). 2. `_is_empty_response(None)` returns `True` (enters the block). 3. `response_text[:50]` crashes because `None` is not subscriptable. |
| **Trigger Pattern** | Occurs when LM Studio API returns a response where the message content field is null/None rather than an empty string or whitespace. |
| **Related Issues** | BUG-HANG-001 (context overload), BUG-HANG-003 (empty response handling), BUG-013 (tool call loop) |
| **Proposed Fix** | Add null check before slicing: `response_text_safe = response_text or ''; f"response={repr(response_text_safe[:50])}"` |
| **Files To Modify** | `src/discord_bot/message_processor.py` → line 335 in `_process_session()` method |

---

### 📋 BUG-013: channel_search Tool Call Loop — Model Re-calls Instead of Using Results

| Field | Value |
|-------|-------|
| **ID** | BUG-013 |
| **Date** | 2026-05-27 |
| **Status** | 🔴 Confirmed Active — Terminal Log Evidence (2026-06-04) |
| **Severity** | High |
| **Description** | When the LM Studio model calls `channel_search` tool, it re-calls the tool up to 5 times (tool limit: 5, max_tool_calls: 3) without using the returned results. After hitting limits, it returns `content='\n\n'` (empty response). The model fails to process the search results and respond to the user's original question. |
| **Log Evidence** | ```Turn 1: content='', tool_calls=1 → 🔧 Turn 1: LM Studio called tool: channel_search ... Turn 2: content='', tool_calls=1 → 🔧 Turn 2: LM Studio called tool: channel_search ... Turn 3: content='', tool_calls=1 → 🔧 Turn 3: LM Studio called tool: channel_search ... Turn 4: content='\n\n', tool_calls=0 → ❌ Empty response after max tool calls (3)``` |
| **New Evidence (2026-06-04)** | ```09:46:15 - WARNING: Max tool calls (3) reached for channel 1503498099081871470, forcing response 09:47:34 - WARNING: Tool 'channel_search' called 5 times (limit: 5), forcing response 09:49:09 - WARNING: Max tool calls (3) reached for channel 1503498099081871470, forcing response 09:49:13 - WARNING: Final response still had tool calls, discarding them``` |
| **Root Cause** | 1. The tool result from `channel_search` is appended to the conversation history 2. LM Studio does not recognize the results as sufficient to answer the user's question 3. The model re-calls `channel_search` thinking it needs more data 4. After hitting max_tool_calls (3) or tool limit (5), the model returns empty content |
| **Related Issues** | CHANNEL-001 (result format improvement), ISS-006 (same pattern with show_typing tool), BUG-HANG-001 (context overload), BUG-014 (channel_id) |
| **Proposed Fix** | 1. Add explicit instruction in tool result: "You now have the search results. Respond to the user's question using this data." 2. After max_tool_calls is reached, force the model to respond with the gathered data by injecting a system message 3. Consider reducing max_tool_calls for channel_search specifically 4. Fix BUG-014 (channel_id parameter) to ensure search results are meaningful |
| **Files To Modify** | `src/discord_bot/message_processor.py` (max tool call handling), `src/discord_bot/tool_executor.py` (tool result format), `src/discord_bot/message_handler.py` (system prompt) |

---

### 📋 BUG-014 (channel_id): channel_search — LM Passes Channel Name Instead of Numeric ID

| Field | Value |
|-------|-------|
| **ID** | BUG-014 (channel_id) |
| **Date** | 2026-06-04 |
| **Status** | 🔴 Confirmed — Root Cause Identified + Terminal Evidence (2026-06-04) |
| **Severity** | High |
| **Description** | The LM Studio model passes channel names ("this", "general") as `channel_id` parameter instead of actual Discord channel ID numbers. While `resolve_channel()` in `bot_core.py` correctly resolves these names to numeric IDs, the LM keeps re-calling `channel_search` with different queries instead of using the returned results (see BUG-013). |
| **Log Evidence** | ```09:45:48 - [channel_search] Searching channel this (limit=20, query='mannequin') 09:45:52 - [channel_search] Searching channel this (limit=20, query='') 09:46:15 - [channel_search] Searching channel this (limit=30, query='image') 09:47:07 - [channel_search] Searching channel this (limit=50, query='mannequin') 09:47:35 - [channel_search] Searching channel c2 (limit=50, query='mannequin') 09:47:50 - [channel_search] Searching channel c3 (limit=50, query='mannequin') 09:48:01 - [channel_search] Searching channel this (limit=50, query='mannequin') 09:48:24 - [channel_search] Searching channel this (limit=50, query='') 09:49:08 - [channel_search] Searching channel this (limit=50, query='png')``` |
| **Root Cause** | 1. The LM model interprets `channel_id` as a human-readable channel name rather than a numeric Discord channel ID. 2. The tool result message format does not clearly indicate that a numeric ID is required. 3. **IMPORTANT**: `resolve_channel()` already handles channel name resolution — the channel names ARE being resolved correctly. The real issue is the tool call loop (BUG-013). |
| **Related** | BUG-013 (tool call loop), CHANNEL-001 (result format improvement) |
| **Proposed Fix** | 1. **Primary**: Fix BUG-013 (tool call loop) — the model needs to use returned results instead of re-calling. 2. Add explicit instruction in tool result: "You now have the search results. Respond to the user's question using this data." 3. After max_tool_calls is reached, force the model to respond with the gathered data by injecting a system message. |
| **Files To Modify** | `src/discord_bot/message_processor.py` (max tool call handling), `src/discord_bot/tool_executor.py` (tool result format), `src/discord_bot/message_handler.py` (system prompt) |

---

### 📋 BUG-014 (embeds): channel_search Only Checks Attachments, Not Embeds (Missing Image Embeds)

| Field | Value |
|-------|-------|
| **ID** | BUG-014 (embeds) |
| **Date** | 2026-05-27 |
| **Status** | 🔴 Confirmed — Terminal Log Evidence (2026-06-04) |
| **Severity** | Medium |
| **Description** | The `channel_search` tool only checks `message.attachments` for images, but Discord messages can also contain images via `message.embeds`. Messages with image embeds (e.g., links that Discord auto-embeds as image previews) are incorrectly reported as `has_image=False`. |
| **Log Evidence** | Message `1509036589081432225` has 5 image embeds in `message.embeds` array but `has_image=False` in channel_search results. **NEW EVIDENCE (2026-06-04)**: Terminal log shows messages with image embeds containing `.png` URLs that are NOT detected. |
| **Root Cause** | In `channel_search.py`, the `_has_image()` function only checks `message.attachments`, not `message.embeds`. |
| **Proposed Fix** | Update `_has_image()` to also check embeds: ```python def _has_image(message): # Check attachments ... # Check embeds for embed in (message.embeds or []): if embed.type == 'image' or (embed.thumbnail and embed.thumbnail.url): return True return False ``` |
| **Files To Modify** | `src/tools/builtins/channel_search.py` → `_has_image()` function |

---

### 📋 BUG-015: channel_search Rate Limit Exhaustion (Too Many API Calls Per Search)

| Field | Value |
|-------|-------|
| **ID** | BUG-015 |
| **Date** | 2026-05-27 |
| **Status** | 🔴 Confirmed — Terminal Log Evidence (2026-06-04) |
| **Severity** | High |
| **Description** | Each `channel_search` call makes 16+ Discord API calls: 1 batch fetch (50 messages) + up to 15 individual message fetches for full content. When the model re-calls `channel_search` 3 times (BUG-013), this results in 48+ API calls, accelerating rate limit bucket exhaustion. |
| **Log Evidence** | Rate limit warnings appear after multiple channel_search calls: ```WARNING - Rate limit bucket exhausted: 429 Too Many Request``` **NEW EVIDENCE (2026-06-04)**: Terminal log shows the LM calling `channel_search` 10+ times in a single conversation, each triggering multiple Discord API calls. |
| **Root Cause** | 1. Each channel_search fetches message bodies individually via `channel.fetch_message()` 2. The model re-calls channel_search instead of using results (BUG-013) 3. No caching of channel_search results to prevent redundant calls |
| **Proposed Fix** | 1. Fix BUG-013 (tool call loop) to prevent redundant calls 2. Add result caching for channel_search with TTL 3. Consider batching message fetches where possible |
| **Files To Modify** | `src/tools/builtins/channel_search.py`, `src/discord_bot/message_processor.py` |

---

### 📋 BUG-CANCEL-001: Cancellation Feature — Method Name Mismatch

| Field | Value |
|-------|-------|
| **ID** | BUG-CANCEL-001 |
| **Date** | 2026-05-27 |
| **Status** | 📋 Documented |
| **Severity** | High |
| **Description** | `bot_core.py` calls `manager.cancel(channel_id)` but `CancellationManager` only has a `request_cancel()` method. This will cause an `AttributeError` when attempting to cancel a session. |
| **Root Cause** | Method name mismatch between `bot_core.py` (which calls `cancel()`) and `CancellationManager` (which defines `request_cancel()`). |
| **Fix Required** | Change `manager.cancel(channel_id)` to `await manager.request_cancel(channel_id)` in `bot_core.py` `cancel_session()` method. |
| **Files To Modify** | `src/discord_bot/bot_core.py` → `cancel_session()` method |

---

### 📋 BUG-CANCEL-002: Cancellation Not Checked During Tool Execution Loop

| Field | Value |
|-------|-------|
| **ID** | BUG-CANCEL-002 |
| **Date** | 2026-05-27 |
| **Status** | 📋 Documented |
| **Severity** | High |
| **Description** | The `message_processor.py` has a `_process_tool_calls_with_status()` method (lines 919-983) that includes cancellation checking at each tool call turn. However, this method is NEVER called — the code directly calls `self._tool_call_handler.process_tool_calls()` instead. |
| **Root Cause** | The `_process_tool_calls_with_status()` method exists but is not wired into the processing pipeline. |
| **Fix Required** | Replace `self._tool_call_handler.process_tool_calls()` call with `self._process_tool_calls_with_status()` to enable cancellation checking during tool execution. |
| **Files To Modify** | `src/discord_bot/message_processor.py` → main tool execution path |

---

### 📋 BUG-CANCEL-003: No Cancellation Integration in MessageHandler

| Field | Value |
|-------|-------|
| **ID** | BUG-CANCEL-003 |
| **Date** | 2026-05-27 |
| **Status** | 📋 Documented |
| **Severity** | Medium |
| **Description** | The `message_handler.py` module has no imports or usage of the cancellation module. Neither `handle_new_session()` nor `handle_active_session_batch()` check for cancellation requests during processing. |
| **Fix Required** | 1. Add `from src.discord_bot.cancellation import get_cancellation_manager` import. 2. Add cancellation checks in `handle_new_session()` and `handle_active_session_batch()`. |
| **Files To Modify** | `src/discord_bot/message_handler.py` |

---

### 📋 BUG-CANCEL-004: No Discord Command Trigger for Cancellation

| Field | Value |
|-------|-------|
| **ID** | BUG-CANCEL-004 |
| **Date** | 2026-05-27 |
| **Status** | 📋 Documented |
| **Severity** | Medium |
| **Description** | There is no Discord command (e.g., `/cancel` or `!stop`) that users can send to trigger session cancellation. |
| **Fix Required** | Add a command check in `_handle_on_message()` to detect `/cancel` or `!stop` commands and call `self.cancel_session(channel_id)`. |
| **Files To Modify** | `src/discord_bot/bot_core.py` → `_handle_on_message()` method |

---

### 📋 BUG-CANCEL-005: Cancellation Manager Not Imported in bot_core.py

| Field | Value |
|-------|-------|
| **ID** | BUG-CANCEL-005 |
| **Date** | 2026-05-27 |
| **Status** | 📋 Documented |
| **Severity** | Medium |
| **Description** | `bot_core.py` calls `get_cancellation_manager()` in `cancel_session()` (line 876) and `cancellation_manager` property (line 916), but does not import it. This will cause a `NameError` when these methods are called. |
| **Fix Required** | Add `from src.discord_bot.cancellation import get_cancellation_manager` at the top of `bot_core.py`. |
| **Files To Modify** | `src/discord_bot/bot_core.py` → imports section |

---

### 📋 BUG-HANG-002: Bot Cannot Be Interrupted During Long Tool Operations

| Field | Value |
|-------|-------|
| **ID** | BUG-HANG-002 |
| **Date** | 2026-06-03 |
| **Status** | 🔴 Confirmed — Blocking Due to BUG-CANCEL-* Issues |
| **Severity** | High |
| **Description** | When the bot is processing a long-running tool operation (e.g., image generation via ComfyUI, channel search with multiple channels), users cannot interrupt it. Sending `/endsession` or any other message has no effect until the current tool operation completes. |
| **Root Cause** | Multiple issues documented in BUG-CANCEL-001 through BUG-CANCEL-005. |
| **Proposed Fix** | **Immediate**: 1. Fix BUG-CANCEL-005 (add missing import). 2. Fix BUG-CANCEL-001 (rename `cancel()` to `request_cancel()`). 3. Fix BUG-CANCEL-002 (wire `_process_tool_calls_with_status` into pipeline). 4. Fix BUG-CANCEL-004 (add `/cancel` command). |
| **Files To Modify** | `src/discord_bot/bot_core.py`, `src/discord_bot/message_processor.py`, `src/discord_bot/message_handler.py` |

---

### 📋 BUG-IMG-001: image_describe Tool Consolidated into image_compare

| Field | Value |
|-------|-------|
| **ID** | BUG-IMG-001 |
| **Date** | 2026-06-05 |
| **Status** | ✅ Resolved |
| **Severity** | High |
| **Description** | The `image_describe` tool claimed to accept URLs in its description but its `execute()` method only handled base64 data. This caused the LM Studio model to get stuck in a loop calling `channel_search` to find images instead of using `image_describe`. |
| **Root Cause** | `image_describe.py` description said: "The image_data parameter accepts either a URL (e.g., Discord CDN link) or Base64-encoded image data." but `execute()` only processed base64. Meanwhile `image_compare.py` had proper async URL downloading via `compare_images_async()`. |
| **Fix Applied** | Consolidated `image_describe` into `image_compare`: (1) Changed `minItems` from 2 to 1 in parameters. (2) Added `is_single_image` detection in `compare_images_async()`. (3) Single image uses description prompt, multiple images use comparison prompt. (4) Removed `ImageDescribeTool` from tool registration. (5) Updated `tool_executor.py` to route `image_describe` calls through `ImageCompareTool.compare_images_async()`. (6) Deleted `image_describe.py`. |
| **Files Modified** | `src/tools/builtins/image_compare.py`, `src/tools/builtins/__init__.py`, `src/discord_bot/tool_executor.py`, `src/tools/builtins/image_describe.py` (deleted) |
| **Follow-up Cleanup (2026-06-05)** | Removed stale `ImageDescribeTool` import and registration from `bot_core.py`. Updated `message_processor.py` status message dictionaries to remove `image_describe` references. Updated `tool_executor.py` docstring to reflect consolidation. |

---

### 📋 BUG-IMG-002: image_describe/image_compare Fail on Expired Discord CDN URLs (404)

| Field | Value |
|-------|-------|
| **ID** | BUG-IMG-002 |
| **Date** | 2026-06-04 |
| **Status** | 📋 Documented — Not Yet Implemented |
| **Severity** | Medium |
| **Description** | When `image_compare` tool receives Discord CDN URLs that have expired, the HTTP request fails with 404 Not Found. The tools do not handle this gracefully. |
| **Root Cause** | Discord CDN URLs expire after a certain period. |
| **Proposed Fix** | In `image_compare.py`, catch HTTP 404 errors and return a user-friendly message. |
| **Files To Modify** | `src/tools/builtins/image_compare.py` |

---

### 📋 BUG-SEARCH-001: channel_search Fails on Discord API Rate Limit (429)

| Field | Value |
|-------|-------|
| **ID** | BUG-SEARCH-001 |
| **Date** | 2026-06-04 |
| **Status** | 📋 Documented — Not Yet Implemented |
| **Severity** | High |
| **Description** | When `channel_search` hits Discord API rate limits (429 Too Many Requests), the tool does not handle the error gracefully. This is especially problematic given BUG-013 (tool call loop) which causes the model to re-call `channel_search` multiple times. |
| **Root Cause** | Discord API has rate limits per guild/channel. When `channel_search` makes 16+ API calls per search, and the model re-calls it 3+ times, the rate limit bucket is quickly exhausted. |
| **Proposed Fix** | In `channel_search.py` and `bot_core.py`, catch 429 errors and return partial results with a warning. |
| **Files To Modify** | `src/tools/builtins/channel_search.py`, `src/discord_bot/bot_core.py` → `get_channel_messages()` and `_fetch_channel_messages()` methods |

---

### 📋 BUG-SEARCH-002: channel_search Multi-Keyword Search Doesn't Check Image URLs or Embeds

| Field | Value |
|-------|-------|
| **ID** | BUG-SEARCH-002 |
| **Date** | 2026-06-04 |
| **Status** | 🔴 Confirmed — Root Cause Identified |
| **Severity** | High |
| **Description** | The `channel_search` tool fails to find messages containing image filenames (e.g., "image.png") because the search only checks message `content` text and attachment filenames. Discord auto-embeds images from URLs into the `embeds` field, and the actual image URLs are stored in the `image_urls` list extracted by `_format_message()`. |
| **Root Cause** | Two filtering layers both incomplete: (1) `bot_core.py get_channel_messages()`: Only checks `content` field. (2) `channel_search.py execute()`: Checks `content` + `attachments` filenames, but NOT `image_urls`. |
| **Proposed Fix** | **Two-tier search with internal keyword splitting**: First word = primary (sent to Discord API), remaining words = secondary (client-side AND filtering). Secondary filter checks ALL fields: content, image_urls, attachments, replied_to_content. |
| **Files To Modify** | `src/discord_bot/bot_core.py` → `get_channel_messages()`, `src/tools/builtins/channel_search.py` → `execute()` |

---

## Observations

### 📋 OBS-001: LM Studio Response Size Discrepancy

| Field | Value |
|-------|-------|
| **ID** | OBS-001 |
| **Date** | 2026-06-03 |
| **Status** | 📋 Documented — Observation Only |
| **Severity** | Low |
| **Description** | LM Studio API responses show inconsistent size patterns. In hang cases: response is ~1938 bytes with 10.8s latency but empty content. In normal cases: responses are typically 500-3000 bytes with content. |
| **Monitoring** | Track response size, latency, and content length ratio. If latency >15s AND content length <10 chars, treat as context overload and apply truncation. |

---

### 📋 OBS-002: Tool Call Result Messages Contribute to Context Bloat

| Field | Value |
|-------|-------|
| **ID** | OBS-002 |
| **Date** | 2026-06-03 |
| **Status** | 📋 Documented — Observation Only |
| **Severity** | Low |
| **Description** | Tool call results (especially channel_search, image_describe, image_compare) are appended to conversation history as full text. Each channel_search can return 15-50 messages with full content. |
| **Monitoring** | Track token usage per tool result. Consider truncating tool results to last 500 chars before appending to conversation history. |

---

### 📋 OBS-003: Memory Recall Before LM Calls Not Implemented (Phase 3)

| Field | Value |
|-------|-------|
| **ID** | OBS-003 |
| **Date** | 2026-06-03 |
| **Status** | 📋 Documented — Phase 3 Not Complete |
| **Severity** | Medium |
| **Description** | According to memory/progress.md, Phase 3 "Discord Bot Integration" is ~40% complete. The "Memory recall before LM calls" task is NOT done — no automatic memory injection into context during message processing. |
| **Related** | progress.md line 79: "Memory recall before LM calls — ❌ Not done" |

---

## Known Bugs (Resolved — Titles Only)

### 📋 HANG-002: Fallback Fetch Timeouts During channel_search (3.0s Timeout)

| Field | Value |
|-------|-------|
| **ID** | HANG-002 |
| **Date** | 2026-06-03 |
| **Status** | 📋 Documented — Non-Breaking, Adds Latency |
| **Severity** | Low |
| **Description** | During `channel_search` tool execution, the fallback fetch mechanism in `_fetch_channel_messages()` times out for older messages. The 3-second timeout is frequently hit for older messages that take longer to fetch via Discord API. |
| **Impact** | Non-breaking: The tool still completes successfully and returns results. The timeouts are debug-level warnings that add latency but don't prevent the search from returning data. |
| **Proposed Fix** | 1. Increase `_fetch_timeout` from 3.0 to 5.0 seconds. 2. Or: Add exponential backoff for successive fallback fetches. 3. Or: Remove individual message fallback entirely and rely on batch fetch only. |
| **Files To Modify** | `src/discord_bot/bot_core.py` → `_fetch_channel_messages()` method (`_fetch_timeout` variable) |

---

### 📋 BUG-SEARCH-003: channel_search image_urls Not Communicated to Main Bot After Mini-Context Summarization

| Field | Value |
|-------|-------|
| **ID** | BUG-SEARCH-003 |
| **Date** | 2026-06-05 |
| **Status** | 🔴 Confirmed Active — Terminal Log Evidence (2026-06-05) |
| **Severity** | Critical |
| **Description** | The `channel_search` tool correctly extracts `image_urls` from Discord messages and includes them in the raw message data. However, when the tool uses the **mini-context batched summarization** approach (for large result sets), the LM summarizer receives the messages with image URLs but returns **empty summaries** (`Batch 1 summary content: ''`). This means the final combined result contains NO information about image URLs found during the search, even though the search did encounter messages with image URLs (as seen in terminal log line 733 with an image attachment `technical_guide_to_network_2600x1732_2601.png.webp`). |
| **Root Cause** | The batch summarization flow in `tool_executor.py` `_summarize_channel_search_batched()` formats messages via `_format_messages_for_summarization()` which includes image URLs in the prompt text. However, the LM Studio model returns empty content for the summarization prompt. This could be due to: (1) The summarization prompt not being explicit enough about what to summarize. (2) The model being confused by the image URL format. (3) The model context being overwhelmed by the message data. |
| **Evidence** | Terminal log shows: ```01:03:02 [INFO] [src.discord_bot.tool_executor] [channel_search] Batch 1 summary content: '' 01:03:02 [INFO] [src.discord_bot.tool_executor] [channel_search] Batch summarization complete: 10 messages -> 1 summaries 01:03:02 [INFO] [src.discord_bot.tool_executor] [channel_search] Final combined result (157 chars): "📋 Channel Search Results (batch-summarized from 10 messages):\n\nSearch query: ''\n\n--- Batch 1 Summary ---\n\n\nTotal messages searched: 10\n=== END OF RESULTS ==="``` All batch summaries are empty strings. |
| **Flow Analysis** | 1. `channel_search` tool is called with a search query. 2. Messages are fetched from Discord channel (including `image_urls` field). 3. If messages > batch_size (10), the tool uses `_summarize_channel_search_batched()`. 4. `_format_messages_for_summarization()` formats messages with image URLs included. 5. LM is called with summarization prompt. 6. LM returns empty content. 7. Final result has no image URL information. |
| **Why This Matters** | When a user searches for "image.png" and the search finds messages containing that image, the empty summary means the main bot never learns about the image URLs. The main bot then cannot use `image_compare` or respond with image-related information. |
| **Related Issues** | BUG-013 (tool call loop), BUG-014 (embeds), BUG-HANG-001 (context overload), BUG-HANG-003 (empty response handling) |
| **Proposed Fix** | **Option A (Recommended)**: Add explicit instruction to summarization prompt: "IMPORTANT: If any messages contain image URLs, list them in your summary. Format: 'Images found: [URL1], [URL2]'." **Option B**: Use direct formatting (`_format_channel_search_direct()`) instead of mini-context summarization when image URLs are present. **Option C**: Extract image URLs separately before summarization and append them to the final result regardless of what the LM summarizes. |
| **Files To Modify** | `src/discord_bot/tool_executor.py` → `_summarize_channel_search_batched()`, `_format_messages_for_summarization()` |

---

### 📋 BUG-SEARCH-004: image_urls Present in channel_search Results But Not Passed to Main Bot Conversation

| Field | Value |
|-------|-------|
| **ID** | BUG-SEARCH-004 |
| **Date** | 2026-06-05 |
| **Status** | 🔴 Confirmed — Root Cause Identified |
| **Severity** | Critical |
| **Description** | Even when `channel_search` correctly finds messages with `image_urls`, the image URLs are NOT communicated to the main bot for follow-up actions (like `image_compare`). The issue is in the **result format**: the mini-context summarization output does not preserve image URLs in a structured way that the LM can use. |
| **Root Cause** | The `_summarize_channel_search_batched()` method returns a text summary that focuses on "key points, topics discussed" but does not explicitly include image URLs. The `_format_channel_search_direct()` method DOES include image URLs (`IMAGES: [URL1], [URL2]`), but this format is only used when `use_mini_context=False`. |
| **Evidence** | Terminal log shows direct format result includes image URLs: ```IMAGES: https://cdn.discordapp.com/attachments/...``` but mini-context result has: ```--- Batch 1 Summary ---\n\n\n``` (empty). |
| **Related Issues** | BUG-SEARCH-003, BUG-014 (embeds), BUG-IMG-001 (image_describe consolidation) |
| **Proposed Fix** | **Short-term**: In `_summarize_channel_search_batched()`, after getting the LM summary, extract and append any image URLs found in the original messages. **Long-term**: Create a structured result format that always includes image URLs regardless of summarization approach. |
| **Files To Modify** | `src/discord_bot/tool_executor.py` → `_summarize_channel_search_batched()` |

---

## Planned Enhancements

### ⏳ FEAT-008: Context Management System — Channel Search, Session Start Context, Context Compression

| Field | Value |
|-------|-------|
| **ID** | FEAT-008 |
| **Date** | 2026-05-21 |
| **Status** | ⏳ Planned |
| **Severity** | Medium |
| **Description** | Implement a system that enables the Main Bot to manage conversation context efficiently. Three interconnected features: |

#### Feature 1: Channel Search Tool (Foundation)
- **Purpose**: Fetch recent Discord channel messages with optional filtering and compression
- **Tool**: `channel_search(channel_id, limit, search_query, username, compress_long)`
- **Returns**: List of `{author, display_name, content, timestamp, is_reply, replied_to_author, replied_to_content, has_image}`
- **Behavior**: Skips bot's own messages, truncates long messages to 200 chars, includes full referenced message for replies
- **File**: `src/tools/builtins/channel_search.py`

#### Feature 2: Session Start Context Initialization
- **Purpose**: Before starting a new session, generate a compact summary of recent channel activity
- **Flow**: ChannelSearch → LM summarize → Inject `[CHANNEL CONTEXT: ...]` into conversation history
- **LM System prompt**: "You are a conversation summarizer. Summarize who is talking to whom, what topics are discussed, and what is resolved vs ongoing."
- **Output format**: `[CHANNEL CONTEXT: <summary>]` (~300 chars max)
- **Trigger**: Always at session start
- **File**: `bot_core.py` → `_handle_new_session_message()` (modified)

#### Feature 3: Context Compression Tool
- **Purpose**: Compress old conversation messages into a compact summary when conversation grows too long
- **Tool**: `context_compress(compress_before_message_index, target_summary_length)`
- **Auto-trigger**: Token consumption >80% OR message count >20
- **Manual trigger**: Bot calls when it "feels like it" (via LM judgment)
- **Compression**: Keep last 6 messages fresh, summarize the rest
- **Output format**: `[CONTEXT: <summary>]` (~300 chars)
- **File**: `src/tools/builtins/context_compressor.py`

#### Configuration
```json
{
  "context_management": {
    "session_start": {
      "recent_messages_limit": 15,
      "message_truncate_length": 200,
      "summary_max_length": 300
    },
    "compression": {
      "token_threshold_percent": 80,
      "message_count_threshold": 20,
      "messages_to_keep_fresh": 6,
      "default_summary_length": 300
    }
  }
}
```

#### Design Decisions (Resolved)
| Question | Decision | Rationale |
|----------|----------|-----------|
| Channel Search: sync or async? | To be determined during implementation | Discord.py history() is async, current architecture uses run_in_executor |
| Context Compression trigger? | Token >80% + message count >20 + bot judgment | Three complementary signals |
| Auto-trigger or bot-decided? | Both — auto on thresholds, bot can also decide | Auto ensures reliability, bot handles nuance |
| LM-generated or rule-based summary? | LM-generated | Too complex for rule-based effectively |

#### Implementation Plan
1. Channel Search Tool (foundation — no LM call needed)
2. Session Start Context Initialization (uses ChannelSearchTool)
3. Context Compression Tool (LM-based summarization)
4. Integration: update system prompt, test full flow

#### Files Created
- `src/tools/builtins/channel_search.py`
- `src/tools/builtins/context_compressor.py`
- `src/discord_bot/context_management.md`

#### Files Modified
- `bot_core.py`
- `message_handler.py`
- `config.py`
- `app.py`

---

### 📋 FEAT-LOG-001: Verbose Mode Toggle + Log Level Control Panel (Planned)

| Field | Value |
|-------|-------|
| **ID** | FEAT-LOG-001 |
| **Date** | 2026-05-27 |
| **Status** | 📋 Documented, Ready for Implementation |
| **Severity** | Low |
| **Description** | Add a toggle to enable/disable verbose logging mode and a log level control panel in the web UI. Currently, the logger supports `LogLevel` levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) and `_current_log_level_filter` in `app.py`, but there's no UI control to change it dynamically. |
| **Current State** | 1. `logger.py` has full `LogLevel` enum with CSS colors and icons. 2. `app.py` has `_current_log_level_filter = LogLevel.DEBUG` and `set_log_level` API endpoint. 3. `get_logs()` supports `level_filter` parameter. 4. Web UI has a "Logs" tab but no log level selector. |
| **Proposed Implementation** | **1. Add `verbose_mode` toggle** to config (default `false` after testing). When `false`, only WARNING+ logs are shown. When `true`, DEBUG+ logs are shown. **2. Add log level selector** to web UI (dropdown: DEBUG, INFO, WARNING, ERROR, CRITICAL). **3. Wire the selector** to the existing `set_log_level` API endpoint. **4. Keep verbose mode disabled by default** — the feature should be "ready for later" with the toggle in the UI. |
| **Config Schema** | ```json { "logging": { "verbose_mode": false, "default_level": "WARNING" } } ``` |
| **Files To Modify** | `src/config.py` (add logging config), `src/app.py` (wire verbose_mode to log level), `src/templates/index.html` (add log level dropdown), `src/static/script.js` (wire dropdown to API) |
| **Design Decisions** | 1. **Default to non-verbose**: After full testing, verbose mode should be OFF by default. 2. **Toggle persists**: Verbose mode setting should be saved in config and survive restarts. 3. **Log level dropdown**: Simple select element with 5 options matching LogLevel enum. 4. **Backward compatible**: If no config exists, default to WARNING level (quiet mode). |

---

### ✅ CONCEPT-004: Channel Search Sliding Window — IMPLEMENTED (2026-06-04)

| Field | Value |
|-------|-------|
| **ID** | CONCEPT-004 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Implemented |
| **Severity** | Low |
| **Description** | Add sliding window support to `channel_search` so the LM can fetch non-contiguous message windows from different points in channel history. Currently, `channel_search` fetches at most 50 messages per channel. If the content the LM is looking for is older than the 50 most recent messages, it gets nothing. |
| **Implemented Parameters** | **`offset`** (integer, default 0): Number of most recent messages to skip before fetching the first window. **`windows`** (integer, default 1, max 5): Number of non-contiguous windows to fetch. Each window fetches `limit` messages, separated by `limit` skipped messages. |
| **Example Usage** | `channel_search(channel="this", offset=50, limit=50)` → Skips messages 1-50, fetches 51-100. `channel_search(channel="this", offset=0, limit=20, windows=3)` → Window 1: messages 1-20, Window 2: messages 71-90, Window 3: messages 141-160. |
| **Result Format** | Results include window indicator header when multi-window mode is active: `[offset=50, 3 windows]`. |
| **Design Decisions** | 1. **Max windows = 5**: Prevents excessive API calls (5 × 50 = 250 messages max per channel). 2. **Non-contiguous windows**: Each window is separated by `limit` skipped messages, creating a "skip pattern" that lets the LM jump through history efficiently. 3. **Backward compatibility**: `offset=0, windows=1` (defaults) preserves current behavior. 4. **Batch fetch optimization**: Uses Discord.py's `channel.history(limit=N)` to fetch all needed messages in a single API call per window, then slices the list. |
| **Files Modified** | ✅ `src/tools/builtins/channel_search.py` (tool schema + description + result formatting). ✅ `src/discord_bot/bot_core.py` (message fetching with offset/windows in `get_channel_messages()` and `_fetch_channel_history()`). ✅ `src/discord_bot/tool_executor.py` (pass new parameters through to bot layer). |
| **Implementation Notes** | `_fetch_channel_history()` now iterates over `range(windows)`, calculating `window_skip = offset + (w * limit)` for each window. It fetches `window_skip + limit` messages from Discord.py history, then slices to get the desired window. This is more efficient than the original concept which suggested using `after` cursors. |

---

*Last updated: 2026-06-04*