# Implementation Progress - POC: test1

> **This file tracks implementation status of features, enhancements, and architectural changes.**
> **Bug tracking and issue details are maintained in [issues_tracker.md](issues_tracker.md).**
> **Solved issue details are in [solved_issues.md](solved_issues.md).**

---

## Implemented Features & Enhancements

### ✅ CONCEPT-004: Channel Search Sliding Window

| Field | Value |
|-------|-------|
| **ID** | CONCEPT-004 |
| **Date Implemented** | 2026-06-04 |
| **Status** | ✅ Implemented |
| **Severity** | Low |
| **Description** | Add sliding window support to `channel_search` so the LM can fetch non-contiguous message windows from different points in channel history. |
| **Implemented Parameters** | **`offset`** (integer, default 0): Number of most recent messages to skip. **`windows`** (integer, default 1, max 5): Number of non-contiguous windows to fetch. |
| **Files Modified** | ✅ `src/tools/builtins/channel_search.py` (tool schema + description + result formatting). ✅ `src/discord_bot/bot_core.py` (message fetching with offset/windows in `get_channel_messages()` and `_fetch_channel_history()`). ✅ `src/discord_bot/tool_executor.py` (pass new parameters through to bot layer). |
| **Implementation Notes** | `_fetch_channel_history()` iterates over `range(windows)`, calculating `window_skip = offset + (w * limit)` for each window. Fetches `window_skip + limit` messages from Discord.py history, then slices to get the desired window. |

---

### ✅ FEAT-002: Discord Channel Search Tool

| Field | Value |
|-------|-------|
| **ID** | FEAT-002 |
| **Date Implemented** | 2026-05-21 |
| **Status** | ✅ Implemented |
| **Description** | Discord channel search tool with server config UI filter. |
| **Files Created** | `src/tools/builtins/channel_search.py` |
| **Files Modified** | `bot_core.py`, `config.py`, `app.py` |

---

### ✅ FEAT-006: LM Studio Multi-Instance Management

| Field | Value |
|-------|-------|
| **ID** | FEAT-006 |
| **Date Implemented** | 2026-05-21 |
| **Status** | ✅ Implemented |
| **Description** | LM Studio multi-instance management for loading/unloading models. |

---

### ✅ FEAT-007: image_compare Tool for Multi-Image Comparison

| Field | Value |
|-------|-------|
| **ID** | FEAT-007 |
| **Date Implemented** | 2026-05-20 |
| **Status** | ✅ Implemented |
| **Description** | New image_compare tool for direct multi-image comparison (refactored from 3-step describe-then-compare to single multi-image call). |
| **Files Modified** | `src/tools/builtins/image_compare.py`, `src/discord_bot/lm_caller.py`, `src/discord_bot/tool_executor.py` |

---

### ✅ UX-003: image_compare Direct Multi-Image Comparison

| Field | Value |
|-------|-------|
| **ID** | UX-003 |
| **Date Implemented** | 2026-05-20 |
| **Status** | ✅ Implemented |
| **Description** | Complete refactor of `compare_images_async()` — single mini-context with ALL images, single LM call, no second step needed. |

---

### ✅ UX-002: Mini-Context Image Descriptions Use User-Specific Prompt

| Field | Value |
|-------|-------|
| **ID** | UX-002 |
| **Date Implemented** | 2026-05-19 |
| **Status** | ✅ Implemented |
| **Description** | Added `image_instruction` parameter to `_build_mini_context()` and `compare_images_async()`. Added `_extract_last_user_message()` helper to extract the last user message from conversation history. |
| **Regression** | UX-002 introduced BUG-UX-002-REG (infinite loop in image_compare). Fixed by stripping URLs/base64 from extracted messages. |
| **Files Modified** | `src/discord_bot/tool_executor.py`, `src/tools/builtins/image_compare.py` |

---

### ✅ BUG-IMG-001: image_describe/image_compare Consolidated into Single Tool

| Field | Value |
|-------|-------|
| **ID** | BUG-IMG-001 |
| **Date Implemented** | 2026-06-05 |
| **Status** | ✅ Implemented |
| **Description** | Consolidated `image_describe` and `image_compare` into a single `image_compare` tool that handles both single-image description and multi-image comparison. This resolved the root cause where `image_describe` claimed URL support but only handled base64. |
| **Changes Made** | 1. Changed `minItems` from 2 to 1 in `image_compare.py` parameters. 2. Added `is_single_image` detection in `compare_images_async()`. 3. Single image uses description prompt, multiple images use comparison prompt. 4. Removed `ImageDescribeTool` from tool registration. 5. Updated `tool_executor.py` to route `image_describe` calls through `ImageCompareTool.compare_images_async()`. 6. Added legacy fallback methods for base64 format. 7. Deleted `image_describe.py`. |
| **Files Modified** | `src/tools/builtins/image_compare.py`, `src/tools/builtins/__init__.py`, `src/discord_bot/tool_executor.py` |
| **Files Deleted** | `src/tools/builtins/image_describe.py` |

---

### ✅ FIX-001: Enhanced Tool Result Message to Prevent Re-calling image_describe

| Field | Value |
|-------|-------|
| **ID** | FIX-001 |
| **Date Implemented** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Description** | Changed tool result message format to prevent LM Studio from re-calling image_describe. |
| **Files Modified** | `src/discord_bot/tool_executor.py` → `_handle_image_describe()` and `_handle_image_describe_active()` |

---

### ✅ FIX-002: Handle URL Strings Passed as image_data Parameter

| Field | Value |
|-------|-------|
| **ID** | FIX-002 |
| **Date Implemented** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Description** | Added `_handle_image_data()` helper method that detects URL vs base64, downloads via SafeImageDownloader if URL, detects MIME type, resizes, and returns (base64_data, mime_type) tuple. |
| **Files Modified** | `src/discord_bot/tool_executor.py` |

---

### ✅ FIX-003: Empty Response After Tool Processing (max_tokens Overflow)

| Field | Value |
|-------|-------|
| **ID** | FIX-003 |
| **Date Implemented** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Description** | Added `_execute_lm_call()` with `max_tokens_override` parameter. When Turn N returns empty content after tool processing, automatically retry with `max_tokens * 2` (capped at 8192). |
| **Files Modified** | `src/discord_bot/message_processor.py` → `_process_session()`, `process_active_session()`, `_execute_lm_call()`, new `_is_oom_error()` and `_is_max_tokens_overflow()` methods |

---

### ✅ FIX-004: image_compare Discord CDN URL Retry

| Field | Value |
|-------|-------|
| **ID** | FIX-004 |
| **Date Implemented** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Description** | Added `_download_image_with_retry()` static method in ImageCompareTool. On content-type error, retries with `Referer: https://discord.com/` header. |
| **Files Modified** | `src/tools/builtins/image_compare.py` → new `_download_image_with_retry()` method |

---

### ✅ CHANNEL-001: channel_search Result Format Improvement

| Field | Value |
|-------|-------|
| **ID** | CHANNEL-001 |
| **Date Implemented** | 2026-05-21 |
| **Status** | ✅ Implemented |
| **Description** | Improved result format with structured headers, explicit labels, and LM instructions. Return "" after channel_search to signal loop should continue. |
| **Files Modified** | `src/tools/builtins/channel_search.py`, `src/discord_bot/tool_executor.py`, `src/discord_bot/message_handler.py` |

---

### ✅ Memory Tool Integration (FIX-MEMORY-001)

| Field | Value |
|-------|-------|
| **ID** | FIX-MEMORY-001 |
| **Date Implemented** | 2026-05-26 |
| **Status** | ✅ Implemented |
| **Description** | Memory tool fully operational with 8 operations, wired into `tool_executor.py` and `bot_core.py`. |
| **Files Modified** | `src/tools/builtins/memory_tool.py`, `src/discord_bot/tool_executor.py`, `src/discord_bot/bot_core.py`, `src/discord_bot/message_handler.py` |

---

### ✅ Memory Session Lifecycle Hooks

| Field | Value |
|-------|-------|
| **Date Implemented** | 2026-06-03 |
| **Status** | ✅ Implemented |
| **Description** | Session lifecycle hooks in `bot_core.py`: `_on_session_started()` injects wake-up memory, `_on_session_ended()` saves conversation + sleep summary, `_on_session_cleanup()` prunes memories. |
| **Lines** | bot_core.py Line 535: `_on_session_started()`, Line 838: `_on_session_ended()`, Line 855: `_on_session_cleanup()`, Lines 1609-1701: Full wake-up injection, memory save, and pruning logic |

---

### ✅ Modular Refactoring of message_handler.py (ISS-022)

| Field | Value |
|-------|-------|
| **ID** | ISS-022 |
| **Date Implemented** | 2026-05-21 |
| **Status** | ✅ Implemented |
| **Description** | Split large `message_handler.py` into smaller focused modules. |

---

### ✅ Modular Refactoring of bot_core.py (ISS-023)

| Field | Value |
|-------|-------|
| **ID** | ISS-023 |
| **Date Implemented** | 2026-05-21 |
| **Status** | ✅ Implemented |
| **Description** | Split large `bot_core.py` into smaller focused modules. |

---

## In-Progress / Pending Implementation

### ✅ SEARCH-001: Enhanced channel_search Username Matching & Increased Default Limit

| Field | Value |
|-------|-------|
| **ID** | SEARCH-001 |
| **Date Implemented** | 2026-06-05 |
| **Status** | ✅ Implemented |
| **Description** | Fixed two limitations that prevented the bot from matching official Discord search capabilities for `has: image from: username` queries. |

#### Fix 1: Username Partial Matching with Discriminator Support
- **Problem**: The `from:` filter did exact match, so `from: BotGuzu#3756` would NOT match author `"BotGuzu"` (Discord usernames stored without discriminator)
- **Solution**: Added regex-based discriminator stripping (`re.sub(r'#\d{4}$', '', username)`) and partial matching — the filter now matches if the base username is contained in the author or display_name
- **Files Modified**: 
  - ✅ `src/tools/builtins/channel_search.py` (lines 403-424: enhanced `from:` filter with discriminator stripping and `in` check)
  - ✅ `src/discord_bot/bot_core.py` (lines 662-680: enhanced username filter in `get_channel_messages()`)

#### Fix 2: Increased Default Message Fetch Limit
- **Problem**: Bot only fetched 15 messages by default, while official Discord searches the entire channel history
- **Solution**: Changed default limit from 15 to 50 (Discord API maximum per request)
- **Files Modified**:
  - ✅ `src/discord_bot/bot_core.py` (line 547: changed `limit: int = 15` to `limit: int = 50`)

#### Comparison After Fix

| Feature | Official Discord | LMDiscord Bot (Before) | LMDiscord Bot (After) |
|---------|-----------------|----------------------|---------------------|
| `has: image` | Full history | Last 15 messages | Last 50 messages |
| `from: username` | Partial/fuzzy | Exact match only | Partial match with discriminator support |
| Message depth | Unlimited | 15 (default) | 50 (default) + sliding window |

---

### ✅ FEAT-008: Context Management System — Channel Search, Session Start Context, Context Compression

| Field | Value |
|-------|-------|
| **ID** | FEAT-008 |
| **Date** | 2026-05-21 |
| **Date Implemented** | 2026-06-10 |
| **Status** | ✅ **FULLY IMPLEMENTED** |
| **Severity** | Medium |
| **Description** | Three interconnected features for conversation context management. |

#### Feature 1: Channel Search Tool — ✅ COMPLETE
- **File**: `src/tools/builtins/channel_search.py`
- **Status**: Implemented with sliding window support (CONCEPT-004)

#### Feature 2: Session Start Context Initialization — ✅ IMPLEMENTED (2026-06-10)
- **Flow**: Fetch recent channel messages → Format as readable list → Inject into system prompt
- **Implementation**: `memory_callbacks.py` → `_fetch_recent_channel_context()` method
- **Behavior**: 
  1. Fetches last 10 messages from Discord channel (skips bot's own messages)
  2. Filters to last 24 hours only
  3. Truncates messages to 300 chars
  4. Includes `[media]` indicator for messages with attachments
  5. Combined with wake-up memory into system prompt
- **Output format**: `📋 [RECENT CHANNEL CONTEXT: Last N messages]` with numbered message list
- **Files Modified**: ✅ `src/discord_bot/memory_callbacks.py` (added `_fetch_recent_channel_context()` method)

#### Feature 3: Context Compression Tool — ✅ FULLY IMPLEMENTED (BUG-CONTEXT-001 FIXED)
- **Tool**: `context_compress(compress_before_index, target_summary_length, messages_to_keep_fresh)`
- **File**: `src/tools/builtins/context_compressor.py`
- **Status**: ✅ **Fully functional with real LM-based summarization**
- **Fix Applied**: 
  1. `ContextCompressorTool.execute()` now accepts `messages_for_lm` parameter
  2. Sends pre-compression messages to LM Studio for real summarization
  3. `tool_executor.py` passes `messages_for_lm` to compressor
  4. Compressed messages are replaced with summary in `messages_for_lm`
- **Auto-Trigger**: Implemented in `message_processor.py` — checks context size after each turn
- **Thresholds**: Token >80% OR message count >20 triggers automatic compression
- **Files Modified**: ✅ `src/tools/builtins/context_compressor.py` (real LM summarization), ✅ `src/discord_bot/tool_executor.py` (pass messages_for_lm + replace compressed messages), ✅ `src/discord_bot/message_processor.py` (auto-trigger logic), ✅ `src/discord_bot/message_handler.py` (threshold evaluation), ✅ `src/discord_bot/memory_callbacks.py` (session start context)

#### Mini-Context Handover Fix — ✅ IMPLEMENTED (2026-06-10)
- **Problem**: Legacy image describe methods in `tool_executor.py` did not support `check_pending` callback, causing the bot to be unable to interrupt image processing when a new message arrives during a new session.
- **Fix**: Added `check_pending` parameter to `_handle_image_describe_legacy()` method with two interruption points:
  1. After image download (before processing)
  2. Before mini-context LM call
- **Files Modified**: ✅ `src/discord_bot/tool_executor.py` (added `check_pending` support to legacy image describe)

#### Configuration Schema
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

#### Files Created/Modified (2026-06-10)
| File | Change |
|------|--------|
| `src/discord_bot/memory_callbacks.py` | Added `_fetch_recent_channel_context()` method for session start context initialization |
| `src/discord_bot/tool_executor.py` | Added `check_pending` support to `_handle_image_describe_legacy()`, fixed `_handle_context_compress()` to pass `messages_for_lm` |
| `src/discord_bot/message_processor.py` | Added auto-trigger compression logic (context size monitoring) |
| `src/discord_bot/message_handler.py` | Added `_check_and_trigger_compression()` threshold evaluation |

---

### ✅ BUG-SEARCH-006: channel_search Batch Summarization Latency — Performance Fix

| Field | Value |
|-------|-------|
| **ID** | BUG-SEARCH-006 |
| **Date Implemented** | 2026-07-11 |
| **Status** | ✅ Implemented |
| **Severity** | Critical |
| **Description** | Fixed the batch summarization system that causes 4+ minute latency for simple channel_search requests. |

#### Root Cause
When `channel_search` returns >5 messages, `_summarize_channel_search_batched()` splits them into batches of 10 and sends EACH batch to LM Studio for summarization BEFORE the main bot sees results. 40 messages → 5 batches → 5 LM calls → 4+ minutes.

#### Fix A: Conditional Batch Summarization Threshold ✅ IMPLEMENTED
- **File**: `src/discord_bot/tool_executor.py` → `_handle_channel_search()`
- **Change**: Only use batch summarization when result text would exceed 3000 chars. Otherwise use direct formatting.
- **Logic**:
  - Estimate direct format size: `len(messages) * 150 + 500`
  - Threshold: 3000 chars
  - If estimated size > 3000 → batch summarize
  - If estimated size <= 3000 → direct format (includes image URLs)
- **Impact**: For 40 messages from the original log, estimated size = 40 * 150 + 500 = 6500 > 3000, so batch would still be used. But for smaller result sets (e.g., 10 messages = 2000 chars), direct formatting avoids unnecessary LM calls.

#### Fix B: Intelligent Token-Aware Batching ✅ IMPLEMENTED
- **File**: `src/discord_bot/tool_executor.py` → `_summarize_channel_search_batched()`
- **Change**: Replace fixed `batch_size=10` with token-aware packing:
  - Estimate tokens per formatted message: ~40 tokens
  - Target: 50% of max_tokens per batch (6144 tokens for 12k max)
  - Effective batch size: `max(5, 6144 / 40) = min(153, 20) = 20`
  - With max_tokens=12288: batch_size = 20, so 40 messages → 2 batches (was 5)
- **Impact**: 40 messages → 2 LM calls instead of 5 (60% reduction)

#### Fix C: Increase Default max_tokens for Mini-Context ✅ IMPLEMENTED
- **File**: `src/discord_bot/tool_executor.py` → `_summarize_channel_search_batched()`
- **Change**: Default `max_tokens=4096` → `max_tokens=12288`
- **Impact**: Prevents `finish_reason: "length"` truncation that caused wasted computation

#### Fix D: Add Output Length Constraints ✅ IMPLEMENTED
- **File**: `src/discord_bot/tool_executor.py` → `_summarize_channel_search_batched()` summarization prompt
- **Change**: Added rules 5-7 to prompt:
  - "MAX 400 CHARACTERS per batch summary"
  - "List image URLs compactly — one per line, no extra text"
  - "List only UNIQUE image URLs (deduplicate)"
- **Impact**: More concise summaries, less wasted tokens

#### Fix E: Make Mini-Context max_tokens Configurable via UI ✅ IMPLEMENTED
- **Files**: `src/static/lib/settings.js`, `src/app.py`, `src/config.json`, `src/templates/index.html`, `src/static/script.js`
- **UI Location**: Tools Config tab → Context Compression section
- **Default**: 12288
- **Status**: Fully implemented
- **Changes**:
  1. `config.json` — Added `mini_context_max_tokens: 12288` to tools_config
  2. `app.py` — Added GET/POST endpoints for mini_context_max_tokens in `/api/tools_config`
  3. `index.html` — Added "Mini-Context Max Tokens" input field in Context Compression section
  4. `script.js` — Added load/save functions for miniContextMaxTokens

#### Expected Performance Improvement
| Scenario | Before | After |
|----------|--------|-------|
| 10 messages (found answer quickly) | 1 batch LM call (~60s) | 0 batch calls (direct format) |
| 40 messages (original log case) | 5 batch LM calls (~270s) | 2 batch LM calls (~100s) |
| First batch hit max_tokens | Yes (wasted 74s) | No (12k limit) |

---

### ⏳ FEAT-LOG-001: Verbose Mode Toggle + Log Level Control Panel

| Field | Value |
|-------|-------|
| **ID** | FEAT-LOG-001 |
| **Date** | 2026-05-27 |
| **Status** | ⏳ Ready for Implementation |
| **Severity** | Low |
| **Description** | Add toggle for verbose logging mode and log level selector in web UI. |
| **Implementation Plan** | 1. Add `verbose_mode` toggle to config. 2. Add log level dropdown to web UI. 3. Wire dropdown to existing `set_log_level` API endpoint. |
| **Files To Modify** | `src/config.py`, `src/app.py`, `src/templates/index.html`, `src/static/script.js` |

---

### ⏳ Memory Module — Phase 3: Memory Recall Before LM Calls

| Field | Value |
|-------|-------|
| **Date** | 2026-06-03 |
| **Status** | ⏳ Not Started |
| **Severity** | Medium |
| **Description** | According to `memory/progress.md`, Phase 3 "Discord Bot Integration" is ~40% complete. The "Memory recall before LM calls" task is NOT done — no automatic memory injection into context during message processing. |
| **Related** | `memory/progress.md` line 79: "Memory recall before LM calls — ❌ Not done" |
| **Implementation Plan** | 1. Add memory recall call before LM Studio API calls. 2. Inject relevant memories into conversation context. 3. Test with existing memory tools. |
| **Files To Modify** | `src/discord_bot/message_handler.py`, `src/memory/memory_manager.py` |

---

### ⏳ Memory Module — Phase 4: Memory Fusion + Background Cleanup

| Field | Value |
|-------|-------|
| **Date** | 2026-06-03 |
| **Status** | ⏳ Not Started |
| **Severity** | Low |
| **Description** | Memory fusion (combining related memories), background cleanup task, LM-generated sleep summaries. |
| **Files To Modify** | `src/memory/memorylite.py`, `src/memory/memory_manager.py` |

---

### ⏳ Memory Module — Phase 5: Testing & Optimization

| Field | Value |
|-------|-------|
| **Date** | 2026-06-03 |
| **Status** | ⏳ Not Started |
| **Severity** | Low |
| **Description** | Unit tests, integration tests, performance benchmarks, memory caching, batch operations. |
| **Files To Create** | `tests/test_memorylite.py`, `tests/test_memory_manager.py` |

---

### ⏳ CONCEPT-003: MemoryBot Architecture

| Field | Value |
|-------|-------|
| **ID** | CONCEPT-003 |
| **Date** | 2026-05-21 |
| **Status** | ⏳ Documented — Not Yet Implemented |
| **Severity** | Low |
| **Description** | MemoryBot is a specialized sub-bot with fresh isolated context that handles memory search operations. |
| **Architecture** | Main Bot → MemoryBot → Memory System → Distilled Results |
| **Implementation Plan** | 1. Create `memorybot.py` core. 2. Create `memorybot_prompt.py` for prompt templates. 3. Route memory queries in `message_handler.py`. 4. Support concurrent LM calls in `api.py`. 5. Implement context flush logic. |
| **Estimated Effort** | 3-5 days |

---

---

### ✅ BUG-007: Channel Search Image URL Extraction Fix (2026-07-10)

| Field | Value |
|-------|-------|
| **ID** | BUG-007 |
| **Date Implemented** | 2026-07-10 |
| **Status** | ✅ Implemented |
| **Description** | Channel search was not finding image URLs in bot responses. When the bot searched for images (e.g., `search_query="image.png"`), it found messages that referenced image files but the image URLs were NOT included in the summarization results. |
| **Root Causes** | 1. Text search filter filtered out messages with image URLs when text didn't match. 2. `_format_messages_for_summarization` didn't extract image URLs from message content text. 3. Referenced messages by message_id were never fetched. 4. `max_tokens=1024` was too small for mini-context summarization. |
| **Fixes Applied** | 1. Text search filter preserves messages with image URLs (`bot_core.py`, `channel_search.py`). 2. Image URLs extracted from message content using regex (`tool_executor.py` — `_format_messages_for_summarization`). 3. New `_extract_message_ids_from_content()` and `_fetch_referenced_messages()` methods to fetch referenced messages by ID (`tool_executor.py`). 4. `max_tokens` increased from 1024 to 4096 for mini-context summarization (`tool_executor.py`). |
| **Files Modified** | `src/discord_bot/tool_executor.py`, `src/discord_bot/bot_core.py`, `src/tools/builtins/channel_search.py` |
| **New Test Files** | `tests/test_message_reference_extraction.py` (22 tests), `tests/test_integration_channel_search.py` (5 tests) |
| **Test Results** | ✅ 47 unit tests pass (25 new + 22 existing), LMStudio integration test PASSED |
| **Live Verification** | ✅ Verified 2026-07-10: Bot successfully found and returned 3 image.png CDN URLs from channel history |

---

## Architecture Notes

### Module Structure (Post-Refactoring)

```
src/discord_bot/
├── bot_core.py              — Main bot orchestration, event registration, lifecycle
├── message_router.py        — Message routing, mention detection, command parsing
├── message_processor.py     — Message pipeline, batch handling, pending queue management
├── message_handler.py       — LM Studio interaction, tool calling, image handling, session logic
├── tool_executor.py         — Tool execution framework (sync/async dispatch)
├── session_manager.py       — Session lifecycle, timeout cleanup, state queries
├── cancellation.py          — Cancellation management (task-based)
├── image_downloader.py      — Safe image downloading from URLs
├── lm_caller.py             — LM Studio API caller abstraction
├── memory_callbacks.py      — Memory system callbacks (save on session end)
├── delay_processor.py       — Delayed message processing for follow-up batching
├── token_tracker.py         — Token usage tracking per channel for web UI sync
├── typing_indicator.py      — Discord typing indicators
└── user_identity.py         — User identity tracking (display names, mentions)
```

**Module Responsibility Summary:**
| Module | Primary Responsibility | Secondary Responsibility |
|--------|----------------------|------------------------|
| `bot_core.py` | Bot lifecycle, event registration | Session state, image extraction |
| `message_router.py` | Route messages to correct handler | Mention/command detection |
| `message_processor.py` | Pipeline orchestration, batch handling | Pending queue, race condition prevention |
| `message_handler.py` | LM Studio interaction, tool calling | Image handling, context management, session logic |
| `lm_caller.py` | LM Studio API abstraction | Model selection, tool definitions |

### Memory Module Structure

```
src/memory/
├── memorylite.py            — SQLite storage backend (1032 lines)
├── memory_manager.py        — Core memory engine (864 lines)
├── memory_tool.py           — LM Studio tool interface (8 operations)
├── memorybot_prompt.py      — MemoryBot prompt templates
├── memorybot.py             — MemoryBot core (not yet implemented)
├── progress.md              — Implementation progress tracking
├── issues_tracker.md        — Memory-specific issue tracking
└── README.md                — Module documentation
```

---

*Last updated: 2026-06-10*
