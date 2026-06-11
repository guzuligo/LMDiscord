# Implemented Progress - POC: test1

> **Implemented entries have been moved here from [implementation_progress.md](implementation_progress.md).** This file contains historical records of all implemented features, fixes, and improvements. Current pending and in-progress items remain in `implementation_progress.md`.

---

## Memory System Implementation (2026-06-03)

### PHASE2-COMPLETE: Memory LM Studio Tool Interface Marked Complete

| Field | Value |
|-------|-------|
| **ID** | PHASE2-COMPLETE |
| **Date** | 2026-06-03 |
| **Status** | ✅ Implemented (retroactively dated 2026-05-26) |
| **Severity** | N/A |
| **Description** | Phase 2 of the memory module (LM Studio Tool Interface) was documented as "Not Started" but was actually complete. Verified by examining `src/tools/builtins/memory_tool.py` which implements a fully operational `MemoryTool` class with 8 operations: save, search, retrieve, list, delete, statistics, search_recent, search_by_importance. |
| **Components** | 1. `MemoryTool` class with full JSON schema (`parameters` property) 2. `execute()` method handling all 8 operations 3. `_save_memory()` for memory_create 4. `_search_memories()`, `_retrieve_memory()`, `_list_memories()` for memory_recall 5. Tool registered in `tool_executor.py` and `bot_core.py` (FIX-MEMORY-001) 6. System prompt updated in `message_handler.py` |
| **Documentation Updated** | `src/memory/progress.md` — Phase 2 marked complete, progress summary updated from ~4% to ~21% |

---

### FIX-MEMORY-001: LM Studio Not Calling memory_tool to Save Data

| Field | Value |
|-------|-------|
| **ID** | FIX-MEMORY-001 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Implemented |
| **Severity** | Critical |
| **Description** | LM Studio was not calling the memory_tool to save conversation data. The memory system was not persisting any data. |
| **Root Cause** | 1. `memory_tool` was not registered in the tools system — `tool_executor.py` had no handlers for memory operations 2. The `operation` field from LM Studio tool call was not being popped from args before passing **args to `execute()`, causing `TypeError: execute() got multiple values for keyword argument 'operation'` |
| **Fix Applied** | 1. Added `memory_tool` case handlers in `tool_executor.py` for all operations (save, search, update, delete, list, summarize, clear) 2. Added `pop('operation')` from args before passing **args to `self.executor.execute()` to prevent duplicate kwarg error 3. Added memory_tool import and registration in `bot_core.py` |
| **Files Modified** | `src/discord_bot/tool_executor.py`, `src/discord_bot/bot_core.py`, `src/tools/builtins/__init__.py` |

---

### FIX-MEMORY-002: Default Memory Database Path Changed to user/data/memory/memory.db

| Field | Value |
|-------|-------|
| **ID** | FIX-MEMORY-002 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Implemented |
| **Severity** | Low |
| **Description** | Default memory database path was `data/memory.db` which was inconsistent with the project structure. Changed to `user/data/memory/memory.db` for better organization. |
| **Fix Applied** | 1. Changed default in `memorylite.py` `__init__()` parameter 2. Changed default in `config.py` `memory_db_path` property and `get_memory_config()` 3. Updated `DEFAULT_MEMORY_DB_PATH` in `settings.js` |
| **Files Modified** | `src/memory/memorylite.py`, `src/config.py`, `src/static/lib/settings.js` |

---

### FIX-MEMORY-003: Status Message Now Requires LLM-Generated Text (No More Hardcoded Fallbacks)

| Field | Value |
|-------|-------|
| **ID** | FIX-MEMORY-003 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Implemented |
| **Severity** | Medium |
| **Description** | Removed hardcoded tool status message fallback. Status messages are now only sent when the LLM provides a custom `tell_user_you_are_working` message via tool call arguments. This ensures status messages are always in-character and natural, rather than generic hardcoded text like "⏳ Searching channel history...". |
| **Fix Applied** | 1. `_should_send_status()` in `message_processor.py` now takes `custom_message` parameter and returns `True` only if non-None 2. System prompt in `message_handler.py` instructs LLM to always include `tell_user_you_are_working` argument with in-character status messages 3. `_send_tool_status_message()` still has a generic fallback for display text, but the message is only sent if the LLM provided a custom one |
| **Files Modified** | `src/discord_bot/message_processor.py`, `src/discord_bot/message_handler.py` |

---

## Recent Fixes (2026-06-05)

### BUG-IMG-001: image_describe/image_compare Consolidated into Single Tool

| Field | Value |
|-------|-------|
| **ID** | BUG-IMG-001 |
| **Date** | 2026-06-05 |
| **Status** | ✅ Implemented |
| **Severity** | High |
| **Description** | The `image_describe` tool claimed to accept URLs in its description but its `execute()` method only handled base64 data. This caused the LM Studio model to get stuck in a loop calling `channel_search` to find images instead of using `image_describe`. |
| **Root Cause** | `image_describe.py` description said: "The image_data parameter accepts either a URL (e.g., Discord CDN link) or Base64-encoded image data." but `execute()` only processed base64. Meanwhile `image_compare.py` had proper async URL downloading via `compare_images_async()`. |
| **Fix Applied (Initial)** | Consolidated `image_describe` into `image_compare`: (1) Changed `minItems` from 2 to 1 in parameters. (2) Added `is_single_image` detection in `compare_images_async()`. (3) Single image uses description prompt, multiple images use comparison prompt. (4) Removed `ImageDescribeTool` from tool registration. (5) Updated `tool_executor.py` to route `image_describe` calls through `ImageCompareTool.compare_images_async()`. (6) Added legacy fallback methods for base64 format. (7) Deleted `image_describe.py`. |
| **Files Modified** | `src/tools/builtins/image_compare.py`, `src/tools/builtins/__init__.py`, `src/discord_bot/tool_executor.py` |
| **Files Deleted** | `src/tools/builtins/image_describe.py` |
| **Follow-up Cleanup (2026-06-05)** | After the initial consolidation, stale references to `ImageDescribeTool` and `image_describe` remained in several files. The following cleanup was performed: (1) Removed `from src.tools.builtins.image_describe import ImageDescribeTool` import from `bot_core.py`. (2) Removed `ImageDescribeTool()` instantiation from `DiscordBot.__init__()`. (3) Removed `"image_describe"` entry from the `tools` list in `bot_core.py`. (4) Updated `message_processor.py` status message dictionaries to remove `image_describe` entries from `tool_display` in both `_send_tool_status_message()` and `_send_periodic_status()`. (5) Updated `tool_executor.py` docstring to reflect consolidation. (6) Updated system prompt in `message_handler.py` to remove `image_describe` references. |

---

## Recent Fixes (2026-05-27)

### FIX-2026-05-27-001: Debug Page Full-Page Experience

| Field | Value |
|-------|-------|
| **ID** | FIX-2026-05-27-001 |
| **Date** | 2026-05-27 |
| **Status** | ✅ Implemented |
| **Severity** | UX |
| **Description** | Debug panel was opened as a popup window, which is a poor user experience. Changed to open as a full-page tab. |
| **Fix Applied** | 1. Updated `openDebugPanel()` in `script.js` to use `window.open('/debug', '_blank')` instead of popup dimensions 2. Removed close button from `debug.html` 3. Added "← Back to Main" link to `debug.html` 4. Updated `closeDebugPanel()` in `debug_script.js` to inform user to close tab manually |
| **Files Modified** | `src/static/script.js`, `src/templates/debug.html`, `src/static/debug_script.js` |

---

### FIX-2026-05-27-002: Log Level Control Panel

| Field | Value |
|-------|-------|
| **ID** | FIX-2026-05-27-002 |
| **Date** | 2026-05-27 |
| **Status** | ✅ Implemented |
| **Severity** | Feature |
| **Description** | Added log level control to the debug page settings panel, allowing users to dynamically change the application's log verbosity. |
| **Fix Applied** | 1. `loadLogLevel()` fetches current log level from `/api/settings/log_level` and sets the dropdown value 2. `updateLogLevel()` POSTs new log level to `/api/settings/log_level` and refreshes logs 3. Both functions called on debug page initialization |
| **Files Modified** | `src/static/debug_script.js` |

---

### FIX-2026-05-27-003: Model Selection Fix (BUG-010)

| Field | Value |
|-------|-------|
| **ID** | BUG-010 |
| **Date** | 2026-05-27 |
| **Status** | ✅ Implemented |
| **Severity** | High |
| **Description** | Model selection dropdown was not properly updating when models were loaded. The `updateModelSelect()` function was not being called with the correct parameters. |
| **Fix Applied** | 1. Ensured `updateModelSelect()` is called with `data.lm_models`, `data.lm_hostname`, and `data.lm_port` from status API 2. Added `selectModel()` function to POST model change to server |
| **Files Modified** | `src/static/script.js` |

---

### FIX-2026-05-27-004: Reasoning Brevity Fix for LM Timeouts (REASONING-FIX)

| Field | Value |
|-------|-------|
| **ID** | REASONING-FIX |
| **Date** | 2026-05-27 |
| **Status** | ✅ Implemented |
| **Severity** | High |
| **Description** | LM Studio was timing out due to verbose reasoning output. The `reasoning_brevity` setting was not being properly applied to LM calls. |
| **Fix Applied** | 1. Added `reasoning_brevity` parameter to LM API calls in `lm_caller.py` 2. Tools config now includes `reasoning_brevity` toggle 3. System prompt updated to encourage concise reasoning |
| **Files Modified** | `src/discord_bot/lm_caller.py`, `src/tools/builtins/__init__.py`, `src/static/lib/settings.js` |

---

### FIX-2026-05-27-005: Image Processing Fixes (BUG-002, BUG-011, BUG-014)

| Field | Value |
|-------|-------|
| **ID** | BUG-002, BUG-011, BUG-014 |
| **Date** | 2026-05-27 |
| **Status** | ✅ Implemented |
| **Severity** | Medium |
| **Description** | Multiple image-related issues: 1) Base64 images causing context overflow, 2) Image download failures for certain CDN paths, 3) Image description not being generated properly. |
| **Fix Applied** | 1. Image downloads now use direct URL with proper headers 2. Image descriptions are generated via LM instead of storing raw base64 3. Added retry logic for image downloads with exponential backoff |
| **Files Modified** | `src/discord_bot/image_downloader.py`, `src/tools/builtins/image_describe.py` |

---

### FIX-2026-05-27-006: Turn Limit and Retry Logic (PENDING-002)

| Field | Value |
|-------|-------|
| **ID** | PENDING-002 |
| **Date** | 2026-05-27 |
| **Status** | ✅ Implemented |
| **Severity** | Medium |
| **Description** | Bot was getting stuck in retry loops when LM calls failed. No proper turn limit enforcement. |
| **Fix Applied** | 1. Added `max_turns` configuration to message processing 2. Turn counter tracks request/response pairs per turn cycle 3. When max turns reached, bot sends a final message and exits the turn loop |
| **Files Modified** | `src/discord_bot/message_processor.py`, `src/config.py` |

---

### FIX-2026-05-27-007: Session State Consistency (PENDING-004)

| Field | Value |
|-------|-------|
| **ID** | PENDING-004 |
| **Date** | 2026-05-27 |
| **Status** | ✅ Implemented |
| **Severity** | Medium |
| **Description** | Session state was not being properly synchronized between Discord bot and web UI. |
| **Fix Applied** | 1. Session state is now stored in a shared state object 2. Web UI polls for status changes every 2 seconds 3. Discord bot updates shared state on every state change |
| **Files Modified** | `src/discord_bot/bot_core.py`, `src/app.py`, `src/static/script.js` |

---

### FIX-2026-05-27-008: Context Management Tools (FEAT-008)

| Field | Value |
|-------|-------|
| **ID** | FEAT-008 |
| **Date** | 2026-05-27 |
| **Status** | ✅ Implemented (Channel Search wired; Context Compression pending) |
| **Severity** | Feature |
| **Description** | Context management tools for channel search and context compression. Channel search tool is implemented and wired. Context compression tool is implemented but not yet wired. |
| **Planned** | 1. Wire context_compress tool into tool_executor.py 2. Register ContextCompressor tool in bot_core.py 3. Add context_management config section to config.py 4. Session start context injection in message_handler.py 5. Context compression auto-trigger in message_handler.py |
| **Files Created** | `src/tools/builtins/channel_search.py`, `src/tools/builtins/context_compressor.py`, `src/discord_bot/context_management.md` |

---

### LOGGING-001: Unify Python Standard Logging with Custom Logger (User-Filtered)

| Field | Value |
|-------|-------|
| **ID** | LOGGING-001 |
| **Date** | 2026-05-27 |
| **Status** | ✅ Implemented |
| **Severity** | Feature |
| **Description** | Unified Python's standard logging module with the custom Logger class, enabling all Python library logs (discord.py, LM Studio client, Flask, etc.) to appear in the web UI's log buffer with module-level filtering. Noisy modules (typing_indicator, token_tracker) are suppressed in user-facing logs by DEFAULT_MODULE_FILTER in logger.py. |
| **Implementation** | 1. Added `LoggingHandler` class to `logger.py` — a Python `logging.Handler` subclass that bridges standard logging to the custom Logger's in-memory buffer. 2. Added `DEFAULT_MODULE_FILTER` set in `logger.py` — default list of noisy module names to suppress (`typing_indicator`, `token_tracker`). 3. Added `setup_logging()` function in `logger.py` — registers `LoggingHandler` with the root logger. 4. Called `setup_logging()` at Flask app startup in `app.py`. 5. Added module filter UI to `debug.html` — textarea for filtering module names, Save/Reset buttons. 6. Added module filter API endpoints in `app.py` — `GET/POST /api/settings/module_filter`. 7. Added `loadModuleFilter()`, `saveModuleFilter()`, `resetModuleFilter()` functions to `debug_script.js`. |
| **Files Modified** | `src/logger.py`, `src/app.py`, `src/templates/debug.html`, `src/static/debug_script.js` |
| **Default Filtered Modules** | `typing_indicator`, `token_tracker` |
| **API Endpoints** | `GET /api/settings/module_filter` — Get current module filter list<br>`POST /api/settings/module_filter` — Update module filter list |

---

## Recent Fixes (2026-05-21)

### CHANNEL-SEARCH-FIX: channel_search Result Format & Bot Silence Issues

| Field | Value |
|-------|-------|
| **ID** | CHANNEL-SEARCH-FIX |
| **Date** | 2026-05-21 |
| **Status** | ✅ Implemented |
| **Severity** | High |
| **Description** | Two issues with channel_search tool: (1) After channel_search returned results, LM Studio sometimes misinterpreted them and gave incorrect responses (e.g., "it only found your messages asking to find it" when matching messages existed). (2) Bot went silent after tool execution — no final response was posted. |
| **Root Cause** | 1. Tool result format was too loose — didn't clearly indicate which messages contained the search term. 2. After channel_search tool result was added, the loop broke without making a final LM call to produce a response. |
| **Fix Applied** | 1. **Improved result format** — Added structured `=== Channel Search Results ===` headers with explicit `Search query`, `Total matches`, and `CONTENT:` labels for each message. 2. **Added LM instructions** — Appended explicit instructions: "Read the messages above. If the search query was 'X', identify which messages contain this term and provide a direct answer to the user's original question." 3. **Return "" after channel_search** — Changed to return empty string to signal the loop should continue for a final response (prevents bot going silent). 4. **Max tool call limit** — Added `MAX_TOOL_CALLS_PER_SESSION = 3` to prevent infinite tool-calling loops. When limit is reached, a user message is added to force the LM to produce a final response. |
| **Files Modified** | `src/discord_bot/tool_executor.py` → `_handle_channel_search()`, `_handle_channel_search_active()`, `src/discord_bot/message_processor.py` → `process_active_session()` |

---

## Recent Fixes (2026-05-19)

### REASONING-FIX: Model Excessive Reasoning Causing 120s Read Timeout

| Field | Value |
|-------|-------|
| **ID** | REASONING-FIX |
| **Date** | 2026-05-19 |
| **Status** | ✅ Implemented |
| **Severity** | Critical |
| **Description** | The model (qwen3.6-35b-a3b) was entering extremely long internal reasoning loops (6383 reasoning tokens observed), causing 120-second READ TIMEOUT errors from LM Studio when processing tool calls like `image_compare`. The default max_tokens=2500 was insufficient for the model's extended reasoning. |
| **Root Cause** | 1) The model's default behavior produces very long internal reasoning before responding. 2) No temperature control for tool-calling turns (temperature was always 0.7). 3) No max_tokens differentiation between tool-calling turns and final responses. 4) No system prompt instruction to keep reasoning brief. |
| **Fix Applied** | Multi-part fix: |
| **Fix Details** | 1. **Reasoning Brevity Instruction**: Added critical instructions to system prompt in `message_handler.py` `handle_new_session()` that tell the model to keep reasoning SHORT, respond directly after tool results, and avoid extended chain-of-thought. <br> 2. **Tool-Specific max_tokens**: Modified `_call_lm_studio_via_processor()` in `message_handler.py` to use `tool_max_tokens` (2048) for tool-calling turns and `final_max_tokens` (8192) for final responses after tool results. Detected by checking for `role: "tool"` messages in context. <br> 3. **Lower Tool Temperature**: Tool-calling turns now use `tool_temperature` (0.3) instead of the default 0.7, producing more consistent tool arguments. <br> 4. **Tools Config Web UI**: Added new "⚙️ Tools Config" tab to the web UI with form fields for all settings. <br> 5. **Config Persistence**: Added `tools_config` section to config.py with `get_tools_config()`/`set_tools_config()` methods and API endpoints in app.py. |
| **Files Modified** | `src/config.py`, `src/app.py`, `src/discord_bot/bot_core.py`, `src/discord_bot/message_handler.py`, `src/templates/index.html`, `src/static/lm-instances.css`, `src/static/script.js` |
| **Config Schema** | ```json
{
  "tools_config": {
    "reasoning_brevity": true,
    "tool_max_tokens": 2048,
    "tool_temperature": 0.3,
    "final_max_tokens": 8192,
    "use_tool_calling": true
  }
}
``` |
| **Live Test Verification** | ✅ Verified 2026-05-26: Full image_compare pipeline executed successfully. Turn 1 tool call: 393 reasoning tokens. Mini-context comparison: 1234 reasoning tokens. Turn 2 final response: 283 reasoning tokens. Total session: 3305 tokens (2643p + 662c). No timeouts, no OOM. Reasoning brevity instructions working as expected. |
| **Testing** | ✅ Complete - Live tested 2026-05-26 |

---

## Recent Fixes (2026-05-26)

### BUG-014: channel_search Cannot Fetch Image URLs from Referenced Messages

| Field | Value |
|-------|-------|
| **ID** | BUG-014 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Implemented |
| **Severity** | High |
| **Description** | When the LM Studio model wanted to describe an image referenced in a Discord message, it used `channel_search` with `message_id` parameter. However, `channel_search` results did not include image URLs from the referenced message. The LM received empty image data and could not proceed with `image_describe`. |
| **Root Cause** | 1. `channel_search` tool did not support fetching a specific message by `message_id` — it only searched recent messages by text. 2. When `message_id` was passed, the tool ignored it and performed a regular channel search. 3. The `fetch_message_by_id` method existed in `bot_core.py` but was not wired into `channel_search`. 4. Image URLs were not extracted and displayed in channel_search results. |
| **Fix Applied** | 1. Added `get_message_by_id()` public method in `bot_core.py` — wraps `fetch_message_by_id()` for external access. 2. Updated `channel_search` tool — when `message_id` is provided, fetches that specific message instead of searching channel history. 3. Added image URL extraction — `channel_search` now extracts and displays image URLs from message attachments in the result. 4. Updated `tool_executor.py` — passes `message_id` through to `channel_search` and handles the new message-by-ID flow. |
| **Files Modified** | `src/discord_bot/bot_core.py` (added `get_message_by_id()` public method), `src/tools/builtins/channel_search.py` (added `message_id` support, image URL extraction), `src/discord_bot/tool_executor.py` (updated handlers to pass `message_id`, display image URLs in results) |
| **Live Test Verification** | ✅ Verified 2026-05-26: User sent "What about this?" with image attachment → LM called `channel_search` with `message_id` → Tool fetched the message and extracted image URL → LM called `image_describe` with the URL → Image described successfully → Full pipeline working. |

---

## Recent Fixes (2026-05-19)

### FIX-003: Empty Response After Tool Processing (max_tokens Overflow)

| Field | Value |
|-------|-------|
| **ID** | FIX-003 |
| **Date** | 2026-05-19 |
| **Status** | ✅ Implemented |
| **Severity** | High |
| **Description** | After tool processing (image_describe, image_compare), LM Studio returns empty content on Turn 2 with exactly 2500 completion tokens — hit max_tokens limit |
| **Root Cause** | Tool result message + conversation history exceeds context window; LM Studio uses all tokens on reasoning/context |
| **Solution** |
  1. Added `_execute_lm_call()` with `max_tokens_override` parameter
  2. When Turn N returns empty content after tool processing, auto-retry with `max_tokens * 2` (capped at 8192)
  3. Added warning message appended to context suggesting to increase max_tokens
  4. If retry also empty → OOM detection → user-friendly error message
  5. Added `_is_oom_error()` helper to detect OOM in exception strings
  6. Applied to both `_process_session()` and `process_active_session()`
| **Files Modified** | `src/discord_bot/message_processor.py` |

---

### FIX-004: image_compare Discord CDN URL Retry (text/plain Content-Type)

| Field | Value |
|-------|-------|
| **ID** | FIX-004 |
| **Date** | 2026-05-19 |
| **Status** | ✅ Implemented |
| **Severity** | Medium |
| **Description** | Second image URL fails with "Blocked: disallowed content type 'text/plain'" — Discord CDN returns redirect page |
| **Root Cause** | Discord CDN URLs with `?ex=...&is=...` params are temporary redirects without proper headers |
| **Solution** | Added `_download_image_with_retry()` static method — on content-type error, retries with `Referer: https://discord.com/` header. Graceful fallback: proceeds with available images + failure note |
| **Files Modified** | `src/tools/builtins/image_compare.py` |

---

### FIX-001: Enhanced Tool Result Message to Prevent LM Studio Re-calling image_describe

| Field | Value |
|-------|-------|
| **ID** | FIX-001 |
| **Date** | 2026-05-19 |
| **Status** | ✅ Implemented |
| **Severity** | Medium |
| **Description** | After mini-context correctly describes an image, Turn 2 of the main conversation returns `content=''` with a tool call, causing LM Studio to re-call image_describe |
| **Root Cause** | Tool result message was too weak: "The image has been described. Here's what was in the image: [description]. Please continue the conversation naturally, incorporating this information." |
| **Fix** | Changed to explicit, authoritative message: "IMAGE DESCRIPTION COMPLETE: [description]. You now have full information about this image. DO NOT call image_describe again for this image. Respond to the user's question using this description." |
| **Files Modified** | `src/discord_bot/tool_executor.py` → `_handle_image_describe()` and `_handle_image_describe_active()` (both variants) |

---

### FIX-002: Handle URL Strings Passed as image_data Parameter

| Field | Value |
|-------|-------|
| **ID** | FIX-002 |
| **Date** | 2026-05-19 |
| **Status** | ✅ Implemented |
| **Severity** | Low |
| **Description** | When LM Studio calls image_describe with a URL string instead of base64 data, the tool should detect and auto-download |
| **Fix** | Added `_handle_image_data()` helper method that:
  1. Detects if image_data starts with "http" (URL string)
  2. Downloads via SafeImageDownloader if URL
  3. Detects MIME type from content bytes
  4. Resizes and converts to base64
  5. Returns (base64_data, mime_type) tuple
| **Files Modified** | `src/discord_bot/tool_executor.py` → new `_handle_image_data()` method |

---

### FEAT-007: New image_compare Tool for Multi-Image Comparison

| Field | Value |
|-------|-------|
| **ID** | FEAT-007 |
| **Date** | 2026-05-19 |
| **Status** | ✅ Implemented |
| **Severity** | Feature |
| **Description** | Tool that accepts 2-3 image URLs, downloads each, describes via mini-context, then generates structured comparison |
| **New Files Created** |
| | File | Lines | Purpose |
| |------|-------|---------|
| | `src/tools/builtins/image_compare.py` | ~220 | ImageCompareTool class with async comparison via mini-context |
| **Files Modified** |
| | File | Changes |
| |------|---------|
| | `src/tools/builtins/__init__.py` | Added ImageCompareTool export |
| | `src/discord_bot/bot_core.py` | Added ImageCompareTool import and registration |
| | `src/discord_bot/tool_executor.py` | Added `_handle_image_compare()` and `_handle_image_compare_active()` methods |
| | `src/discord_bot/message_handler.py` | Updated system prompt with image_compare tool description and re-call prevention |
| **Features** |
  - Accepts `image_urls` array (2-3 items) and optional `comparison_prompt`
  - Downloads all images via SafeImageDownloader
  - Describes each image via isolated mini-context (no conversation history)
  - Combines descriptions into structured comparison prompt
  - Returns formatted comparison covering: similarities, differences, key elements, patterns
| **Tool Definition** |
  ```json
  {
    "type": "function",
    "function": {
      "name": "image_compare",
      "description": "Compare up to 3 images side by side...",
      "parameters": {
        "type": "object",
        "properties": {
          "image_urls": {"type": "array", "minItems": 2, "maxItems": 3},
          "comparison_prompt": {"type": "string"}
        },
        "required": ["image_urls"]
      }
    }
  }
  ``` |

---

## Recent Fixes (2026-05-16)

### ISS-019: DelayProcessor Parameter Mismatch (Solved)

| Field | Value |
|-------|-------|
| **ID** | ISS-019 |
| **Date** | 2026-05-16 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Symptom** | `TypeError: DelayProcessor.process_active_session_with_delay() got an unexpected keyword argument 'author_nick'` |
| **Root Cause** | `bot_core.py` was passing `author_nick=author_nick` to `process_active_session_with_delay()`, but the method signature only accepts `author_name` and `author_display` |
| **Fix** | Removed `author_nick=author_nick` from the call in `bot_core.py` line 388 |
| **Files Modified** | `src/discord_bot/bot_core.py` |

---

### ISS-020: Global LM Studio Lock to Prevent Concurrent Requests / OOM (Implemented)

| Field | Value |
|-------|-------|
| **ID** | ISS-020 |
| **Date** | 2026-05-16 |
| **Status** | ✅ Implemented |
| **Severity** | High |
| **Problem** | When messages arrive in two different channels simultaneously, both get submitted to the thread pool and call LM Studio concurrently, potentially causing OOM errors |
| **Solution** | Added `asyncio.Lock()` in `bot_core.py` that serializes all LM Studio API calls |
| **Implementation** |
  1. Added `self._lm_studio_lock = asyncio.Lock()` to `DiscordBot.__init__()`
  2. Added `lm_studio_lock` parameter to `MessageHandler.__init__()`
  3. Added `_call_lm_studio()` helper method that acquires the global lock before each API call
  4. Wrapped all 6 LM Studio API call sites with `_call_lm_studio()`:
     - `_process_message`: tool calling, non-tool calling, mini-context image description
     - `_process_active_session`: tool calling, non-tool calling, mini-context image description
  5. Added logging: "Waiting for LM Studio lock", "Acquired LM Studio lock", "Released LM Studio lock"
| **Files Modified** | `src/discord_bot/bot_core.py`, `src/discord_bot/message_handler.py` |
| **Verification** | Logs confirm channel 1502926836970291232 acquires lock first, channel 1503498074851508476 waits and acquires after release |

---

### ISS-021: DelayProcessor Handler Callback Signature Mismatch (Solved)

| Field | Value |
|-------|-------|
| **ID** | ISS-021 |
| **Date** | 2026-05-16 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Symptom** | `TypeError: DiscordBot._process_active_session_batch() missing 1 required positional argument: 'pending_messages'` |
| **Root Cause** | `delay_processor.py` passed `pending` as the 6th positional argument, but `_process_active_session_batch` expects `pending_messages` as the 7th positional arg (after `author_nick`) |
| **Fix** | Changed call to pass `None` for `author_nick` and `pending_messages=pending` as keyword arg |
| **Files Modified** | `src/discord_bot/delay_processor.py` |

---

### Configuration Updates (2026-05-16)

| Field | Value |
|-------|-------|
| **Date** | 2026-05-16 |
| **Status** | ✅ Completed |
| **Changes** |
  1. `allowed_image_hostnames` defaults set to `["cdn.discordapp.com", "media.discordapp.net"]` in all config files
  2. `message_delay` default set to 5 in all config files
  3. `config_template.json` updated with missing settings (`suppress_werkzeug_logging`, `message_delay`, `system_prompt`, `allowed_image_hostnames`, `servers`)
| **Files Modified** | `src/config.py`, `config.json`, `config_template.json` |

---

## Logging System Implementation (2026-05-11)

| Component | Status | Notes |
|-----------|--------|-------|
| `src/logger.py` | ✅ Done | Centralized logger with in-memory buffer + file output |
| Log levels | ✅ Done | DEBUG, INFO, WARNING, ERROR, CRITICAL with colors/icons |
| Thread-safe logging | ✅ Done | Using threading.Lock for concurrent access |
| Log API endpoints | ✅ Done | /api/logs, /api/logs/clear, /api/logs/stats, /api/logs/config |
| Log panel UI | ✅ Done | Bottom panel with stats, filter, collapse/resize |
| Logs tab | ✅ Done | Full log history view in tabbed interface |
| Real-time log polling | ✅ Done | 3-second polling interval for new logs |
| Unread log badge | ✅ Done | Shows count of new logs when on Chat tab |
| Log file output | ✅ Done | app.log in project root |

---

## Message Processing Improvements (2026-05-11)

| Component | Status | Notes |
|-----------|--------|-------|
| 5-second delay | ✅ Done | Messages wait 5 seconds before processing (allows for follow-up messages) |
| `show_typing` tool | ✅ Done | LM Studio can call this tool to show "Bot is typing..." indicator |
| Tool calling with both tools | ✅ Done | Both show_typing and end_session tools sent to LM Studio |
| Delayed message handlers | ✅ Done | `_delayed_handle_message` and `_delayed_process_active_session` methods |
| Typing indicator execution | ✅ Done | `_show_typing_indicator` method executes when LM Studio calls the tool |
| Multi-turn tool calling | ✅ Done | Loop until LM Studio returns response without tool calls |

---

## Typing Indicator & Message Processing Fixes (2026-05-11)

| Component | Status | Notes |
|-----------|--------|-------|
| Immediate typing indicator | ✅ Done | Typing indicator now shows immediately in `on_message` handler when mention/reply received |
| No delay for first messages | ✅ Done | First messages (new session) process immediately; delay only applies to active session messages |
| ThreadPoolExecutor for LM Studio | ✅ Done | LM Studio API calls run in background thread to prevent blocking async event loop |
| discord.py 2.x typing API | ✅ Done | Fixed deprecated `channel.send_typing()` → `async with channel.typing():` context manager |
| Multiple typing indicator refresh | ✅ Done | Typing indicator refreshed on each retry turn (turn > 0) during multi-turn tool calling |

---

## Session End Fixes (2026-05-11)

| Component | Status | Notes |
|-----------|--------|-------|
| Duplicate goodbye fix | ✅ Done | Set `response_text = None` when end_session detected in `_handle_active_session_message()` |
| Only farewell from tool args | ✅ Done | Only the farewell message from tool call arguments is posted, not both response and farewell |

---

## Message Queue & Processing Improvements (2026-05-11)

| Component | Status | Notes |
|-----------|--------|-------|
| Pending messages queue | ✅ Done | `_pending_messages` dict stores messages received while bot is processing |
| Queue on processing lock | ✅ Done | When `_processing_lock` is active, messages are queued instead of dropped |
| Batch message processing | ✅ Done | `_handle_active_session_message_batch()` combines main + queued messages into single request |
| Post-response queue check | ✅ Done | After posting response, `_process_queued_pending_messages()` checks for queued messages |
| Chain reaction processing | ✅ Done | Bot processes queued messages immediately after posting, keeps going until queue empty |
| Empty message skip | ✅ Done | Empty/whitespace-only messages are skipped with logging |
| Lock management | ✅ Done | Lock cleared before queue processing, re-acquired by queue handler |

---

## Security Fixes (2026-05-11)

| Component | Status | Notes |
|-----------|--------|-------|
| Error message sanitization | ✅ Done | Internal error details no longer exposed to Discord users |
| Generic error responses | ✅ Done | All error handlers return "⚠️ Sorry, I encountered an error processing your message." |
| Traceback protection | ✅ Done | Error tracebacks logged server-side only, never sent to Discord |

---

## BUG-003: Discord User Identity Tracking (2026-05-14)

| Field | Value |
|-------|-------|
| **ID** | BUG-003 |
| **Date** | 2026-05-14 |
| **Status** | ✅ Implemented |
| **Severity** | Medium |
| **Description** | Bot had no knowledge of who is talking to it. When asked "What is my name?" the bot responded "I don't know your name". Per-server nicknames were never extracted or communicated to LM Studio. |
| **Solution** |
  - Extracted `author_nick = message.author.nick` (per-server nickname)
  - Extended identity tracking through entire call chain
  - Updated system prompt with full identity context (username, display, nickname, user ID)
  - Extended SessionManager to store identity data for memory integration
| **Identity Model** |
  ```
  user_id (immutable) ──────────────────┐
                                        │
  author_name (stable) ────────────────  │  Primary identifiers for session tracking
  per_server_nick (per-guild) ────────  │  → Used when addressing user in chat
  display_name (global, changeable) ───┘
  ```
  **Addressing Priority:** nick > display_name > username
  **Memory Key:** user_id (immutable)
  **Per-Server:** Each server can have different nicknames for same user
| **New/Modified Files** |
| | File | Changes |
| |------|---------|
| | `src/discord_bot/bot_core.py` | Extract `author_nick`, pass through call chain, add `_get_display_name_for_user()` helper, extend session start with identity data |
| | `src/discord_bot/message_handler.py` | Accept `author_nick`/`initial_nick` params, update system prompt with identity context, update message attribution format |
| | `src/discord_bot/session_manager.py` | Add `_session_data` dict, extend `start_session()` with identity fields, add `get_session()` method |

---

## Safe Image Download with Hostname Whitelist (2026-05-12)

### BUG-001: Allowed Hostnames Not Passed from Config (Solved)

| Field | Value |
|-------|-------|
| **ID** | BUG-001 |
| **Date** | 2026-05-12 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Symptom** | `Safe image downloader initialized with allowed hostnames: []` - empty list |
| **Log Evidence** | ```WARNING - BLOCKED: hostname 'cdn.discordapp.com' is NOT in allowed list: []``` |
| **Root Cause** | The Config object was created in `app.py` but never assigned to `LMStudioClient`. `bot_core.py` tried to access `lm_studio_client.config.allowed_image_hostnames` but `LMStudioClient` had no `config` attribute. |
| **Fix** | 1. Added `_config` attribute and `config` property (getter/setter) to `LMStudioClient` (`src/lm_studio_client.py`) 2. Assigned `client.config = config` in `src/app.py` |
| **Files Modified** | `src/lm_studio_client.py`, `src/app.py` |

---

### BUG-002: Image Describe Breaks Conversation Flow (Solved - 2026-05-13)

| Field | Value |
|-------|-------|
| **ID** | BUG-002 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Severity** | Critical |
| **Date Solved** | 2026-05-13 |

#### Sub-Issue 2a: LM Studio Acts as Image Description Tool
- **Symptom**: "Check this out..." with image → LM Studio responds with only image description
- **Root Cause**: System prompt tells LM Studio to call `image_describe` for any image
- **Fix Applied**: Updated system prompt in `handle_new_session()` to guide LM Studio: "Call this ONLY when the user explicitly asks for an image to be described. If the user sends an image but does NOT explicitly ask for it to be described, respond naturally about the image in text. IMPORTANT: Do not call image_describe for every image."
- **Files Modified**: `src/discord_bot/message_handler.py` → `handle_new_session()` system prompt (lines 269-277)

#### Sub-Issue 2b: Poor Blocked Hostname Error Message
- **Symptom**: Robotic error to LM Studio → unhelpful user response
- **Root Cause**: Raw `ValueError` from `SafeImageDownloader` sent as tool result text
- **Fix Applied**: Replaced with user-friendly message: "The image URL could not be processed. This may be due to the image being hosted on an unsupported domain, or the URL may not be publicly accessible. Please try using an image from Discord's CDN instead."
- **Files Modified**: `src/discord_bot/message_handler.py` → ValueError handlers in `_process_message()` (~line 569) and `_process_active_session()` (~line 812)

#### Sub-Issue 2c: Context Overflow (400 Error)
- **Symptom**: 6917-token context → 400 Bad Request → conversation breaks
- **Root Cause**: Image base64 data pollutes conversation history on every turn
- **Fix Applied (Fix E)**: Isolated context window for image describe:
  1. When `image_describe` tool is called, download and resize the image
  2. Create an ISOLATED mini-context with ONLY the image + "describe this image in detail, up to 3-4 sentences" prompt (no conversation history)
  3. Get the description text from LM Studio using the mini-context
  4. Replace the tool call in the main conversation with the description as plain text: "The image has been described. Here's what was in the image: [description]. Please continue the conversation naturally, incorporating this information."
  5. This prevents base64 image data from polluting the main conversation history
- **Files Modified**: `src/discord_bot/message_handler.py` → image_describe handling in `_process_message()` (~lines 502-580) and `_process_active_session()` (~lines 752-815)

#### Sub-Issue 2d: discord.py `is_image()` Compatibility Warning
- **Symptom**: `WARNING - Error checking if attachment is image: 'Attachment' object has no attribute 'is_image'`
- **Root Cause**: `is_image()` is a property in discord.py 2.x, not a method. Calling `attachment.is_image()` raises AttributeError.
- **Fix Applied**: Added `hasattr()` guard to check for `is_image` attribute before accessing it. If callable, call it; if property, use directly. Falls back to extension-based detection if attribute doesn't exist.
- **Files Modified**: `src/discord_bot/bot_core.py` → `_extract_image_attachments()` method (lines 181-193)

---

## Tools System Implementation (2026-05-12)

### Image Describe Tool Implementation

| Field | Value |
|-------|-------|
| **Date** | 2026-05-12 |
| **Status** | ✅ Implemented |
| **Description** | Implemented the full tools system infrastructure and image_describe tool |
| **New Files Created** |
| | File | Lines | Purpose |
| |------|-------|---------|
| | `src/tools/base.py` | ~70 | BaseTool abstract class, ToolResult dataclass |
| | `src/tools/executor.py` | ~120 | ToolExecutor with text and image result handling |
| | `src/tools/registry.py` | ~90 | ToolRegistry for managing tool lifecycle |
| | `src/tools/builtins/image_describe.py` | ~130 | ImageDescribeTool class |
| | `src/utils.py` | ~160 | Image processing utilities (resize, base64, MIME detection) |
| **Modified Files** |
| | File | Changes |
| |------|---------|
| | `src/tools/builtins/__init__.py` | Export ImageDescribeTool |
| | `src/discord_bot/bot_core.py` | Register ImageDescribeTool, pass tool definitions to MessageHandler |
| | `src/discord_bot/message_handler.py` | Add register_tool method, update system prompt with image_describe |
| **Features Implemented** |
  - BaseTool abstract class with to_dict() for OpenAI-compatible format
  - ToolExecutor with execute() and execute_with_image_support() methods
  - ToolRegistry for registration, filtering by enabled status
  - ImageDescribeTool with security measures (5MB limit, 768px max dimension, in-memory processing)
  - Integration with Discord bot via tool definitions list
  - System prompt updated to include image_describe tool description
| **Security Measures** |
  - Max image size: 5MB
  - Max dimension: 768px (auto-resized)
  - In-memory processing only (no disk writes)
  - Base64 URL prefix handling
  - Error handling for corrupted/malformed images |

---

## Modular Refactoring (2026-05-12)

| Field | Value |
|-------|-------|
| **Date** | 2026-05-12 |
| **Status** | ✅ Completed |
| **Problem** | `app.py` was 785 lines and `discord_bot.py` was 1005 lines, making maintenance difficult |
| **Solution** | Split Flask endpoints into separate modules using Blueprints |
| **Files Created** |
| | File | Lines | Purpose |
| |------|-------|---------|
| | `src/chat_api.py` | ~200 | Chat/LM Studio endpoints |
| | `src/discord_api.py` | ~230 | Discord endpoints + thread management |
| **Files Modified** |
| | File | Lines | Notes |
| |------|-------|-------|
| | `src/app.py` | ~230 | Now clean Flask app factory with Blueprint registration |
| **Benefits** | Better separation of concerns, easier to maintain and test |

---

## Token Metrics Streaming Display (2026-05-12)

| Field | Value |
|-------|-------|
| **Date** | 2026-05-12 |
| **Status** | ✅ Implemented |
| **Problem** | No way to see token usage statistics or debug LM Studio responses |
| **Solution** | Added streaming SSE endpoint with real-time token metrics display |
| **New Files** |
  - Token Metrics tab in web UI with metrics panel and live stream display
  - CSS styles for token metrics panels
| **Modified Files** |
  - `lm_studio_client.py` - Added `chat_stream_with_usage()` and `chat_with_tools_stream()` methods
  - `chat_api.py` - Added `/api/chat/stream`, `/api/tokens/last`, `/api/tokens/reset` endpoints
  - `index.html` - Added Tokens tab with metrics grid and stream content area
  - `styles.css` - Added token metrics panel styling
  - `script.js` - Added `sendStreamingMessage()`, token update functions, SSE event reader
| **Features** |
  - Real-time token generation display (completion tokens, speed, time)
  - Prompt/Completion/Total token breakdown
  - Tokens per second speed metric
  - Live text streaming in Tokens tab
  - Usage summary after generation completes
| **API Endpoints** |
  - `POST /api/chat/stream` - SSE stream with token chunks + usage data
  - `GET /api/tokens/last` - Get last token usage stats
  - `POST /api/tokens/reset` - Reset token usage data |

---

## ISS-009: Messages Lost During Active Session Processing

| Field | Value |
|-------|-------|
| **ID** | ISS-009 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Fix** | Message queuing with `_pending_messages` dict and batch processing |

---

## ISS-010: Security - Error Tracebacks Exposed to Users

| Field | Value |
|-------|-------|
| **ID** | ISS-010 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Fix** | Generic sanitized error messages sent to Discord |

---

## ISS-011: Duplicate Message Handlers Running Simultaneously

| Field | Value |
|-------|-------|
| **ID** | ISS-011 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Fix** | Lock management improvements |

---

## ISS-012: Empty Messages Cause LM Studio API Errors

| Field | Value |
|-------|-------|
| **ID** | ISS-012 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Fix** | Early skip for empty/whitespace-only messages |

---

## max_tokens Configurable from Web UI

| Field | Value |
|-------|-------|
| **Date** | 2026-05-12 |
| **Status** | ✅ Solved |
| **Fix** | Added UI input, JS functions, API endpoints, and config setter for max_tokens (1-8192) |

---

## Message Delay Configurable from Web UI

| Field | Value |
|-------|-------|
| **Date** | 2026-05-12 |
| **Status** | ✅ Solved |
| **Fix** | Added UI input, JS functions, API endpoints for message delay (1-30 seconds) |

---

## System Prompt Configurable from Web UI

| Field | Value |
|-------|-------|
| **Date** | 2026-05-12 |
| **Status** | ✅ Solved |
| **Fix** | Added textarea, save/reset buttons, API endpoints for system prompt |

---

## Temperature Configurable from Web UI (2026-05-12)

| Field | Value |
|-------|-------|
| **Date** | 2026-05-12 |
| **Status** | ✅ Solved |
| **Fix** | Added UI input, JS functions, API endpoints, and config setter for temperature (0.0-2.0) |
| **Files Modified** |
  - `config.py` - Added temperature getter/setter properties
  - `app.py` - Added GET/POST `/api/settings/temperature` endpoints with Discord bot integration
  - `index.html` - Added temperature input field in settings section
  - `script.js` - Added loadTemperature(), updateTemperature(), updateTemperatureStatusText() functions |

---

## Max Response Length Configurable from Web UI (2026-05-12)

| Field | Value |
|-------|-------|
| **Date** | 2026-05-12 |
| **Status** | ✅ Solved |
| **Fix** | Added UI input, JS functions, API endpoints, and config setter for max_response_length (100-10000) |
| **Files Modified** |
  - `config.py` - Added max_response_length getter/setter properties
  - `app.py` - Added GET/POST `/api/settings/max_response_length` endpoints
  - `index.html` - Added max_response_length input field in settings section
  - `script.js` - Added loadMaxResponseLength(), updateMaxResponseLength(), updateMaxResponseLengthStatusText() functions |

---

## Dynamic Settings Application to Discord Bot (2026-05-12)

| Field | Value |
|-------|-------|
| **Date** | 2026-05-12 |
| **Status** | ✅ Solved |
| **Description** | When settings are changed from the web UI while Discord bot is running, the changes are now applied immediately without restart |
| **Settings Applied Dynamically** |
  - `temperature` - Applied via `set_lm_studio_params()` when changed
  - `max_tokens` - Already applied via `set_lm_studio_params()` (was pre-existing)
  - `message_delay` - Applied via `set_message_delay()` when changed
  - `system_prompt` - Applied via `set_system_prompt()` when changed
| **Files Modified** |
  - `app.py` - Added `discord_bot_instance.set_lm_studio_params()` call in temperature endpoint
  - `app.py` - Added `discord_bot_instance.set_message_delay()` call in delay endpoint
  - `app.py` - Already had `discord_bot_instance.set_system_prompt()` call in system_prompt endpoint |

---

## Discord Bot Modular Refactoring (2026-05-12)

| Field | Value |
|-------|-------|
| **Date** | 2026-05-12 |
| **Status** | ✅ Completed |
| **Problem** | `discord_bot.py` was 1077 lines, making maintenance and debugging difficult |
| **Solution** | Split into 6 focused modules under `src/discord_bot/` package with single-responsibility design |
| **New File Structure** |
  ```
  src/discord_bot/
  ├── __init__.py              - Package init, re-exports DiscordBot
  ├── bot_core.py              (~522 lines) - Main DiscordBot class, event registration, lifecycle
  ├── message_handler.py       (~546 lines) - Message processing, LM Studio interaction, tool calling
  ├── session_manager.py       (~129 lines) - Session lifecycle, timeout cleanup, state queries
  ├── token_tracker.py         (~100 lines) - Token usage tracking per channel for web UI sync
  ├── typing_indicator.py      (~40 lines)  - Discord typing indicator using async typing() context manager
  └── delay_processor.py       (~110 lines) - Delayed message processing for follow-up batching
  ```
| **Modified Files** |
  - `src/discord_bot.py` (~18 lines) - Now a backward-compat wrapper that imports from `src/discord_bot/`
| **Benefits** |
  - Single Responsibility: Each file has one clear purpose
  - Easier Testing: Unit tests can target individual modules
  - Easier Debugging: Issues are isolated to specific files
  - Better Navigation: Developers find code faster in smaller files
  - Scalable: Easy to add new features without bloating one file
| **Token Usage Tracking**: Added `TokenTracker` class with thread-safe per-channel token usage storage |

---

## Context Persistence Fix (2026-05-12) - ISS-018

| Field | Value |
|-------|-------|
| **ID** | ISS-018 |
| **Date** | 2026-05-12 |
| **Status** | ✅ Solved |
| **Problem** | Bot loses conversation context after each message in active sessions. Every message treated as "turn 1". |
| **Root Cause** | `conversation_history = {channel_id: history}` in `_process_active_session()` created a new local dict instead of mutating the shared one. Additionally, `_process_active_session` did not receive `conversation_history` as a parameter. |
| **Fix** |
  1. Changed `conversation_history = {channel_id: history}` to `conversation_history[channel_id] = history`
  2. Added `conversation_history` parameter to `_process_active_session()` method signature
  3. Updated `handle_active_session_batch()` to pass `conversation_history` to `_process_active_session()`
| **Verification** | Bot now correctly maintains context within sessions. When asked to summarize questions, it returns all previous questions in a table. |

---

## Discord Bot Message Processing Fixes (2026-05-12)

| Field | Value |
|-------|-------|
| **Date** | 2026-05-12 |
| **Status** | ✅ Completed |
| **Problem** | Multiple issues with message queuing, context overflow, and session management |
| **Fixes Applied** |

### ISS-014: Naming Conflict Fix
- **Problem**: `src/discord/` package shadowed discord.py library
- **Fix**: Renamed package to `src/discord_bot/`

### ISS-015: Pending Messages Not Included in LM Studio Batch
- **Problem**: Queued messages were popped but never sent to LM Studio
- **Fix**: Changed `all_user_messages.extend(pending_messages)` to include pending messages in batch content

### Context Overflow Fix
- **Problem**: Conversation history grew unbounded, causing 5990-token contexts and empty LM Studio responses
- **Fix**: Added history truncation in `_process_active_session()` - keeps system prompt + last 20 messages (10 exchanges)

### Session End Fix
- **Problem**: `end_session` tool call continued to Turn 2 after farewell
- **Fix**: Added `break` after `end_session` in both inner (tool loop) and outer (turn loop) loops

### Session Clear Fix
- **Problem**: Session was never cleared after `end_session` tool call
- **Fix**: Added `should_end_session` return value from `handle_active_session_batch()` → `bot_core.py` now calls `clear_session()` when `should_end_session=True`

### Race Condition Fix
- **Problem**: Lock set AFTER delay, so messages during delay were not queued
- **Fix**: Moved `processing_lock[channel_id] = True` to BEFORE `await asyncio.sleep()` in delay_processor

### Queue Check After New Session
- **Problem**: Messages queued during new session were never processed after response
- **Fix**: Added `await self._process_queued_pending_messages()` at end of `_handle_new_session_message()`

### Typing Indicator for Queue Processing
- **Problem**: No typing indicator shown when processing queued messages
- **Fix**: Added `await self._typing_indicator.show(message.channel)` in `_process_queued_pending_messages()` |

---

## Discord Connection Fixes (2026-05-13)

### DISCORD-001: Discord Bot Stuck After Flask App Restart (Stale State)

| Field | Value |
|-------|-------|
| **ID** | DISCORD-001 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Problem** | When Flask app is restarted via debug reloader, Discord bot fails to connect/disconnect properly. Error: "Bot is already connected to Discord" |
| **Root Cause** | Flask's debug reloader restarts the Python process, resetting module globals (`discord_connected = False`, `discord_bot_thread = None`) while old Discord bot threads from the previous process may still be running. When `on_ready()` fires on the old thread, it updates `discord_connected = True` via `sys.modules`. The new Flask app sees `discord_connected = True` even though its own `discord_bot_thread` is `None`. |
| **Fix Applied** |
  1. Added `force_reset_discord_state()` function in `discord_api.py` to reset all Discord-related globals
  2. Called `force_reset_discord_state()` at Flask app startup in `app.py`
  3. Improved `start_discord_bot_thread()` to detect and clean up stale state before starting
  4. Improved `stop_discord_bot()` to handle edge cases (None thread, None stop event, bot instance)
  5. Added `/api/discord/force_reset` endpoint for manual reset from debug page
  6. Added "🔥 Force Reset Discord" button on the debug page
| **Files Modified** | `src/discord_api.py`, `src/app.py`, `src/templates/debug.html`, `src/static/debug_script.js` |

---

### DISCORD-002: UI Shows "Not Connected" Despite Bot Thread Running (Stale Import)

| Field | Value |
|-------|-------|
| **ID** | DISCORD-002 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Problem** | After the Discord bot thread starts successfully (confirmed by logs), the UI still shows "Not connected". The `/api/status` endpoint returns `discord_connected: false` even though the bot thread is running. |
| **Root Cause** | Python's `from module import variable` creates a **local reference** to the value at import time, not a live link to the module attribute. In `app.py`, the code used: `from src.discord_api import discord_connected, ...`. When `bot_core.py` updated `discord_api.discord_connected = True` directly, this only changed the module attribute, not `app.py`'s local `discord_connected` variable. |
| **Fix Applied** | Changed `app.py` to import the module (`from src import discord_api`) instead of individual variables. Created helper functions `_get_discord_connected()`, `_get_discord_bot_instance()`, `_get_discord_status_message()` that always read from the module attribute dynamically. Updated all endpoints to use these helpers. |
| **Files Modified** | `src/app.py` |

---

### DISCORD-003: UnboundLocalError in get_sessions (sessions variable not initialized)

| Field | Value |
|-------|-------|
| **ID** | DISCORD-003 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Problem** | `get_sessions()` endpoint throws `UnboundLocalError: cannot access local variable 'sessions' where it is not associated with a value` |
| **Root Cause** | The `sessions` list was only defined inside the `if isinstance(channels, dict)` block. When `channels` was a list, `sessions` was never initialized. |
| **Fix Applied** | Moved `sessions = []` to the top of the try block. Added `elif isinstance(channels, list)` branch to handle list-type channels. |
| **Files Modified** | `src/app.py` |

---

### Discord Disconnect RuntimeWarning Fix

| Field | Value |
|-------|-------|
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Problem** | `RuntimeWarning: coroutine 'wait_for' was never awaited` when disconnecting Discord bot |
| **Root Cause** | `close_client()` async function was defined and called via `loop.run_until_complete()` from the Flask main thread's event loop. But the event loop was created in the **bot thread**, not the Flask main thread. Calling `run_until_complete()` from a different thread's event loop causes undefined behavior. |
| **Fix Applied** | Removed the problematic `close_client()` coroutine attempt. Now relies on the bot thread's own `_wait_for_stop_event()` mechanism for graceful shutdown. The stop event is set, and the bot thread handles cleanup internally. |
| **Files Modified** | `src/discord_api.py` |

---

### Main Page "Connect LM Studio First" Warning Fix

| Field | Value |
|-------|-------|
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Problem** | The warning "⚠️ Connect LM Studio first for AI responses" was stuck on the main page even after LM Studio was connected. |
| **Root Cause** | `checkStatus()` in `script.js` updated `state.lmConnected` but never called `updateModelInfo()` to sync the integration note. The note was only updated when `connectLM()` was called explicitly. |
| **Fix Applied** | Added `updateModelInfo(data.lm_model, data.lm_models, state)` call at the end of `checkStatus()` so the note updates on every status poll (every 2 seconds). |
| **Files Modified** | `src/static/script.js` |

---

## Debug Panel Fixes (2026-05-13)

### DEBUG-001: Debug Page Not Showing Logs

| Field | Value |
|-------|-------|
| **ID** | DEBUG-001 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Problem** | Debug page at `/debug` was not displaying any log entries despite logs being generated server-side |
| **Root Cause** | The `updateDebugLogDisplay` function in `lib/logs.js` was not being called properly from the debug page's own `fetchDebugLogs()` function. The shared `fetchLogs()` function was calling it, but the debug page's direct call had no error handling and relied on the shared function. |
| **Fix Applied** |
  1. Rewrote `fetchDebugLogs()` in `debug_script.js` to directly call the API and `updateDebugLogDisplay()`
  2. Added comprehensive console logging for debugging (`[DebugPanel]` prefix)
  3. Added `testLogDisplay()` function to verify log pipeline on page load
  4. Added `lastApiResponse` and `lastLogApiResponse` tracking in `debugState`
  5. Fixed `updateDebugLogDisplay()` in `lib/logs.js` with better error handling and console output
| **Files Modified** | `src/static/debug_script.js`, `src/static/lib/logs.js` |

---

### DEBUG-002: JavaScript Syntax Error on Token Refresh

| Field | Value |
|-------|-------|
| **ID** | DEBUG-002 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Problem** | `Uncaught SyntaxError: invalid assignment left-hand side` on line 355 of `debug_script.js` |
| **Root Cause** | Optional chaining `?.` was used on the left-hand side of an assignment: `document.getElementById('...')?.textContent = value`. This is invalid JavaScript because `?.` can only be used for reading, not writing. |
| **Fix Applied** | Changed to explicit element checks:
  ```javascript
  const el = document.getElementById('debugPromptTokens');
  if (el) el.textContent = data.usage.prompt_tokens?.toLocaleString() || '-';
  ```
| **Files Modified** | `src/static/debug_script.js` → `refreshDebugTokens()` |

---

### DEBUG-003: Discord Status Always Shows "Not Connected"

| Field | Value |
|-------|-------|
| **ID** | DEBUG-003 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Problem** | Discord bot status always shows `discord_connected: false` in `/api/status` response even after clicking "Connect" on the main page. The bot IS connecting to Discord (confirmed by user). |
| **Root Cause** | The `on_ready()` callback in `bot_core.py` uses `asyncio.create_task(self._on_status_change_callback(...))` to notify the parent module of the connection status. However, this callback mechanism fails silently because:
  1. The callback is an async function defined in `_discord_bot_thread_func()` in a **different thread**
  2. `asyncio.create_task()` swallows exceptions if no custom exception handler is set on the task
  3. The event loop running the callback is created in the bot thread, but the callback's `global discord_connected` update may fail because the task never actually executes
  4. The `on_ready()` event fires in the discord.py internal event loop, NOT in the bot thread's event loop
| **Fix Applied** | Added direct global variable update in `on_ready()` using `sys.modules.get('src.discord_api')` to access and update the `discord_connected` and `discord_status_message` globals directly. The callback is kept as a fallback. |
| **Files Modified** | `src/discord_bot/bot_core.py` → `_register_events()` → `on_ready()` |
| **Lesson** | Cross-thread async callbacks are unreliable for updating module-level globals. Always update shared state directly in event handlers, and use callbacks only for notification purposes. |

---

### DEBUG-004: Added Discord Connect Button to Debug Page

| Field | Value |
|-------|-------|
| **ID** | DEBUG-004 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Problem** | No way to test Discord connection directly from the debug page |
| **Fix Applied** | Added token input field and "Connect Discord" button to the debug page's Discord status panel, plus `connectDiscordFromDebug()` function |
| **Files Modified** | `src/templates/debug.html`, `src/static/debug_script.js` |

---

## Debug Panel Implementation (2026-05-12)

| Field | Value |
|-------|-------|
| **Date** | 2026-05-12 |
| **Status** | ✅ Completed |
| **Problem** | Debug/logging tools were mixed with the main user interface. Flask debug mode caused duplicate log entries in terminal. No dedicated page for monitoring sessions, diagnostics, and advanced settings. |
| **Solution** | Created separate debug page at `/debug` route. Moved advanced debugging tools to dedicated page. Kept user-facing settings in main page. |
| **New Files Created** |
| | File | Purpose | Lines |
| |------|---------|-------|
| | `src/templates/debug.html` | Debug panel UI | ~160 |
| | `src/static/debug_styles.css` | Debug page styling (Catppuccin Mocha) | ~350 |
| | `src/static/debug_script.js` | Debug page JavaScript | ~380 |
| **Modified Files** |
| | File | Changes |
| |------|---------|
| | `src/templates/index.html` | Added "🔧 Debug Panel" button |
| | `src/static/script.js` | Added `openDebugPanel()` function |
| | `src/app.py` | Added `/debug` route, session management endpoints, token debug endpoint |
| **Debug Panel Features** |
| | Feature | Description | Endpoint |
| |---------|-------------|----------|
| | Connection Status | Real-time LM Studio + Discord status | `/api/status` |
| | Session Manager | View/clear active Discord sessions | `/api/discord/sessions` |
| | Token Metrics | Token usage stats for Discord bot | `/api/tokens/debug/refresh` |
| | Settings Override | Quick setting changes with validation | `/api/settings/*` |
| | LM Studio Override | Host/port inputs for reconnection | N/A |
| | Diagnostics | Test connections, force disconnect | Various |
| | Application Logs | Full log viewer with filtering | `/api/logs` |
| **New API Endpoints** |
| | Endpoint | Method | Description |
| |----------|--------|-------------|
| | `/debug` | GET | Render debug panel page |
| | `/api/discord/sessions` | GET | Get active sessions |
| | `/api/discord/clear_session` | POST | Clear specific channel session |
| | `/api/discord/clear_all_sessions` | POST | Clear all sessions |
| | `/api/tokens/debug/refresh` | GET | Get Discord token metrics |
| **Debug Panel Fixes** |
| | Issue | Fix |
| |-------|-----|
| | Missing `debugLmHost`/`debugLmPort` elements | Added LM Studio Override section with Host/Port inputs |
| | Logs not displaying on page load | Fixed initialization: `lastLogCount` set to 0, all logs render on first fetch |
| | "No logs" state not shown | Added "No logs available" placeholder when log API returns empty |
| | Unclear Discord test error | Improved message: "please connect via main page first" |

---

## Server Configuration System (2026-05-14)

### FEAT-001: Server Configuration System (Backend Complete, UX Improvements Completed)

| Field | Value |
|-------|-------|
| **ID** | FEAT-001 |
| **Date** | 2026-05-14 |
| **Status** | ✅ Backend Complete, UX Improvements Completed |
| **Description** | Per-server enable/disable and per-channel allow/deny lists with web UI management |
| **Completed Implementation** |
  1. **config.py** - ✅ Added `servers` configuration section with per-server settings (lines 204-343)
  2. **bot_core.py** - ✅ Added `_is_server_enabled()` and `_is_channel_allowed()` checks in message handler
  3. **discord_api.py** - ✅ Added all server management API endpoints (lines 391-587)
  4. **index.html** - ✅ Added "Server Config" tab (lines 175-260)
  5. **server-config.js** - ✅ Full CRUD UI logic (280 lines)
| **UX Improvements Completed** |
  1. **bot_core.py** - ✅ Added `get_guilds_info()` and `get_guild_channels(guild_id)` methods to DiscordBot class
  2. **discord_api.py** - ✅ Added `GET /api/discord/servers` endpoint (list all guilds with names)
  3. **discord_api.py** - ✅ Added `GET /api/discord/channels/<guild_id>` endpoint (list channels with names and categories)
  4. **server-config.js** - ✅ Added "📡 Load Servers from Discord" button and auto-discovery logic
  5. **server-config.js** - ✅ Added "🔍 Load Channels from Discord" button when editing a server
  6. **server-config.js** - ✅ Server list now shows names: "My Server (123456789012345678)"
  7. **server-config.js** - ✅ Channel list now shows names: "#general (111111111111111111) (Category)"
  8. **index.html** - ✅ Added "📡 Load Servers from Discord" button in Server Config tab header
  9. **server-config.js** - ✅ Added quick-add dropdown for servers when discovered
  10. **server-config.js** - ✅ Added quick-add dropdown for channels when discovered |

---

### BUG-004: Channel Filter Not Working Due to Server ID Mismatch (Solved - 2026-05-14)

| Field | Value |
|-------|-------|
| **ID** | BUG-004 |
| **Date** | 2026-05-14 |
| **Status** | ✅ Solved |
| **Description** | The bot processes messages from all channels despite denied_channels being configured in config.json. |
| **Root Cause** | Server ID mismatch between config.json and actual Discord guild ID. Config saved for: `1502926835862864000`, Actual Discord guild: `1502926835862863944`. |
| **Fix Applied** | Updated config.json server ID from `1502926835862864000` to `1502926835862863944` |
| **Debug Logging Added** |
  1. **bot_core.py** - Added detailed channel filter debug logging (guild_id, channel_id, allowed_channels, denied_channels, is_channel_allowed result)
  2. **discord_api.py** - Added config save/verify logging and channel API request logging
| **Files Modified** | `config.json`, `src/discord_bot/bot_core.py`, `src/discord_api.py` |

---

### BUG-005: Server Config Changes Not Applied to Running Bot (Stale Config Reference - Solved - 2026-05-14)

| Field | Value |
|-------|-------|
| **ID** | BUG-005 |
| **Date** | 2026-05-14 |
| **Status** | ✅ Solved |
| **Description** | Server/channel config changes saved to disk via the web UI were not reflected in bot behavior. The bot continued showing `allowed_channels=[]` and `denied_channels=[]` even after saving config. |
| **Root Cause** | The Discord bot holds a stale `Config` instance from startup. When the API saves config, it creates a **new** `Config()` instance, saves to disk, and returns. The bot's `_config` is never updated with the new data. |
| **Fix Applied** | After saving config in `update_server_config()`, `add_channel_to_server()`, and `remove_channel_from_server()` endpoints, the bot instance's `_config` is now replaced with a fresh `Config()` instance that reloads from disk. |
| **Files Modified** | `src/discord_api.py` → `update_server_config()`, `add_channel_to_server()`, `remove_channel_from_server()` |

---

### BUG-006: Auto-Discover Returns Wrong Server ID (JavaScript Integer Precision Loss - Solved - 2026-05-14)

| Field | Value |
|-------|-------|
| **ID** | BUG-006 |
| **Date** | 2026-05-14 |
| **Status** | ✅ Solved |
| **Severity** | Critical |
| **Description** | The "Load Servers from Discord" feature returned server IDs with corrupted last digits (e.g., `1502926835862863944` became `1502926835862864000`). This caused the server config save to use the wrong ID, so channel filters never worked. |
| **Root Cause** | Discord snowflake IDs are 19 digits, exceeding JavaScript's `MAX_SAFE_INTEGER` (16 digits). The `get_guilds_info()` method returned guild IDs as **integers**, which get corrupted when passed through JSON → JavaScript → backend. Channel IDs were already correctly returned as strings. |
| **Fix Applied** | Changed `get_guilds_info()` to return `str(guild.id)` instead of `guild.id`, matching how channel IDs are handled in `get_guild_channels()`. |
| **Files Modified** | `src/discord_bot/bot_core.py` → `get_guilds_info()` method |

---

### Logger TypeError Fix (Solved - 2026-05-14)

| Field | Value |
|-------|-------|
| **Date** | 2026-05-14 |
| **Status** | ✅ Solved |
| **Description** | Flask app threw `TypeError: Logger.info() got multiple values for argument 'module'` when saving server config from web UI. |
| **Root Cause** | `discord_api.py` was calling `logger.info()` with multiple positional string arguments plus a `module` keyword argument, but the custom Logger class only accepts `(message: str, module: str = "")`. |
| **Fix Applied** | Changed `logger.info()` call in `update_server_config()` to use a single formatted string: `logger.info(f"[ServerConfig] Server config updated for {server_id}: enabled={enabled}")` |
| **Files Modified** | `src/discord_api.py` → `update_server_config()` |

---

## LM Studio Multi-Instance Management (2026-05-18)

### FEAT-006: LM Studio Multi-Instance Management

| Field | Value |
|-------|-------|
| **ID** | FEAT-006 |
| **Date** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Description** | Created full multi-instance management for LM Studio with UI to select which model to use |
| **New Files Created** |
| | File | Lines | Purpose |
| |------|-------|---------|
| | `src/lm_models/__init__.py` | ~10 | Package init |
| | `src/lm_models/models.py` | ~88 | `ModelInfo`, `LmInstanceConfig`, `LmInstance` dataclasses |
| | `src/lm_models/manager.py` | ~283 | `InstanceManager` with CRUD, model discovery, model selection |
| | `src/lm_models/api.py` | ~194 | Flask Blueprint with 11 API endpoints |
| | `src/static/lm-instances.css` | ~197 | Instance card styling |
| | `src/static/lib/lm-instances.js` | ~200 | Instance management UI logic |
| **Files Modified** |
| | File | Changes |
| |------|---------|
| | `src/app.py` | Added `init_instance_manager()`, `lm_bp` blueprint, registered LM endpoints |
| | `src/lm_studio_client.py` | Added `switch_instance()`, `selected_model` property, `chat_with_tools_stream()` |
| | `src/config.py` | Added `lm_instances` and `active_instance` support |
| | `src/templates/index.html` | Added model dropdown, LM Instances tab, linked CSS/JS |
| | `src/static/script.js` | Added `updateModelSelect()`, `selectModel()`, LM instance state tracking |
| **API Endpoints** |
  - `GET /api/lm_instances` - List all instances
  - `POST /api/lm_instances` - Add instance
  - `GET/DELETE /api/lm_instances/<id>` - Get/remove instance
  - `POST /api/lm_instances/<id>/activate` - Activate instance
  - `POST /api/lm_instances/<id>/discover` - Discover models
  - `GET/POST /api/lm_instances/<id>/select_model` - Model selection
  - `GET/POST /api/lm_instances/active/model` - Active model management
| **Bugs Fixed During Implementation** |
  1. Config path: `parent.parent.parent` → `parent.parent`
  2. Manager `_load()` didn't create default instance
  3. API path mismatch: `/api/lm/...` vs `/api/lm_instances`
  4. Field name mismatch: `connected` vs `is_connected`
  5. Duplicate DOM ID: `lm-instances-tab` on both button and content
| **Verification** | Backend API returns 1 instance with 15 discovered models. UI tested and verified working. |

---

## Image Tools Fixes & New Feature (2026-05-18)

### FIX-003: Empty Response After Tool Processing (max_tokens Overflow)

| Field | Value |
|-------|-------|
| **ID** | FIX-003 |
| **Date** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Description** | After tool processing (image_describe, image_compare), LM Studio returns empty content on Turn 2 with exactly 2500 completion tokens — hit max_tokens limit |
| **Solution** |
  1. Added `_execute_lm_call()` with `max_tokens_override` parameter
  2. When Turn N returns empty content after tool processing, auto-retry with `max_tokens * 2` (capped at 8192)
  3. Added warning message appended to context suggesting to increase max_tokens
  4. If retry also empty → OOM detection → user-friendly error message
  5. Added `_is_oom_error()` helper to detect OOM in exception strings
  6. Applied to both `_process_session()` and `process_active_session()`
| **Files Modified** | `src/discord_bot/message_processor.py` |

---

### FIX-004: image_compare Discord CDN URL Retry (text/plain Content-Type)

| Field | Value |
|-------|-------|
| **ID** | FIX-004 |
| **Date** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Description** | Second image URL fails with "Blocked: disallowed content type 'text/plain'" — Discord CDN returns redirect page |
| **Solution** | Added `_download_image_with_retry()` static method — on content-type error, retries with `Referer: https://discord.com/` header. Graceful fallback: proceeds with available images + failure note |
| **Files Modified** | `src/tools/builtins/image_compare.py` |

---

### FIX-001: Enhanced Tool Result Message to Prevent LM Studio Re-calling image_describe

| Field | Value |
|-------|-------|
| **ID** | FIX-001 |
| **Date** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Description** | After mini-context correctly describes an image, Turn 2 of the main conversation returns `content=''` with a tool call, causing LM Studio to re-call image_describe |
| **Fix** | Changed to explicit, authoritative message: "IMAGE DESCRIPTION COMPLETE: [description]. You now have full information about this image. DO NOT call image_describe again for this image. Respond to the user's question using this description." |
| **Files Modified** | `src/discord_bot/tool_executor.py` → `_handle_image_describe()` and `_handle_image_describe_active()` (both variants) |

---

### FIX-002: Handle URL Strings Passed as image_data Parameter

| Field | Value |
|-------|-------|
| **ID** | FIX-002 |
| **Date** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Description** | When LM Studio calls image_describe with a URL string instead of base64 data, the tool should detect and auto-download |
| **Fix** | Added `_handle_image_data()` helper method that:
  1. Detects if image_data starts with "http" (URL string)
  2. Downloads via SafeImageDownloader if URL
  3. Detects MIME type from content bytes
  4. Resizes and converts to base64
  5. Returns (base64_data, mime_type) tuple
| **Files Modified** | `src/discord_bot/tool_executor.py` → new `_handle_image_data()` method |

---

### FEAT-007: New image_compare Tool for Multi-Image Comparison

| Field | Value |
|-------|-------|
| **ID** | FEAT-007 |
| **Date** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Description** | Tool that accepts 2-3 image URLs, downloads each, describes via mini-context, then generates structured comparison |
| **New Files Created** |
| | File | Lines | Purpose |
| |------|-------|---------|
| | `src/tools/builtins/image_compare.py` | ~220 | ImageCompareTool class with async comparison via mini-context |
| **Files Modified** |
| | File | Changes |
| |------|---------|
| | `src/tools/builtins/__init__.py` | Added ImageCompareTool export |
| | `src/discord_bot/bot_core.py` | Added ImageCompareTool import and registration |
| | `src/discord_bot/tool_executor.py` | Added `_handle_image_compare()` and `_handle_image_compare_active()` methods |
| | `src/discord_bot/message_handler.py` | Updated system prompt with image_compare tool description and re-call prevention |
| **Features** |
  - Accepts `image_urls` array (2-3 items) and optional `comparison_prompt`
  - Downloads all images via SafeImageDownloader
  - Describes each image via isolated mini-context (no conversation history)
  - Combines descriptions into structured comparison prompt
  - Returns formatted comparison covering: similarities, differences, key elements, patterns |

---

## Implementation Status (Original Project)

### Completed ✅
| Component | Status | Notes |
|-----------|--------|-------|
| Project structure | ✅ Done | All folders and placeholder files created |
| Configuration management | ✅ Done | `src/config.py` with JSON persistence |
| LM Studio client | ✅ Done | `src/lm_studio_client.py` with chat and streaming |
| Flask web application | ✅ Done | `src/app.py` with REST API endpoints |
| Web interface | ✅ Done | `src/templates/index.html` with dark theme |
| Entry point | ✅ Done | `main.py` launches Flask server |
| Dependencies | ✅ Done | requirements.txt with all packages |
| Discord bot module | ✅ Done | `src/discord_bot/` package with 6 modules |
| Discord Flask endpoints | ✅ Done | connect, disconnect, status, info, chat, logs, tokens, settings, memory endpoints |
| GUI Discord integration | ✅ Done | Full Discord connect/disconnect UI with status indicators |
| Discord bot integration | ✅ Done | Full bot with session management, tools, memory hooks |
| LM Studio + Discord integration | ✅ Done | Bot forwards messages to LM Studio and posts responses |
| Tools system | ✅ Done | Math, image_describe, image_compare, channel_search, memory, show_typing, end_session |
| Memory integration | ✅ ~55% | Core memory (80%), LM tools (100%), Discord hooks (40%), summarization (60%), testing (0%) |

### Testing Results
- ✅ Flask server starts successfully on port 5000
- ✅ Web interface loads correctly
- ✅ Connection to LM Studio API works
- ✅ Chat messages sent and responses received
- ✅ Discord bot connects via web GUI
- ✅ Discord bot responds to mentions and "hello" command
- ✅ Discord bot disconnects properly via web GUI
- ✅ Discord bot integrates with LM Studio for AI-powered responses
- ✅ Session-based conversation context per Discord channel
- ✅ LM Studio connection required before Discord bot connects
- ✅ Web UI shows LM Studio integration status
- ✅ Session end via LM Studio tool calling - WORKING
- ✅ LM Studio autonomously decides when to call end_session tool
- ✅ LM Studio generates natural farewell messages
- ✅ Session clears automatically after farewell
- ✅ Empty response bug fixed when tool call is used
- ✅ Full end-to-end test passed on Discord (GuzuBot)

### Key Decisions
1. **Web GUI instead of tkinter**: tkinter not available for Python 3.13 on Fedora/Nobara. Flask web interface provides same functionality with broader compatibility.
2. **Session-based chat**: Flask sessions used for conversation history.
3. **Catppuccin Mocha theme**: Dark theme for comfortable long-term use.

### Lessons Learned (From Main Project)

| Lesson | Source | Application |
|--------|--------|-------------|
| User identity tracking is critical | BUG-003 (main) | Memory keys should use immutable user_id |
| Context persistence matters | ISS-018 (main) | Memory system extends session context |
| Per-server nicknames vary | BUG-003 (main) | Memory should track per-server identity |
| Session timeout = 600s | Current config | Memory should persist beyond session timeout |
| Base64 images cause overflow | BUG-002 (main) | Memory should store descriptions, not raw data |
| Cross-thread async callbacks fail silently | DISCORD-003 (main) | Update shared state directly in event handlers |
| Python `from module import var` creates stale reference | DISCORD-002 (main) | Import module, access attributes dynamically |
| JavaScript integer precision loss >16 digits | BUG-006 (main) | Always pass Discord IDs as strings |

---

*Last updated: 2026-06-03*