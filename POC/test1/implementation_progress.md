# Implementation Progress - POC: test1

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
| **Testing** | Requires live testing with image_compare tool to verify timeout no longer occurs. Monitor LM Studio logs for reasoning token count. |

---

## Potential Issues (To Monitor) - Added 2026-05-21

### PENDING-001: Error Handling in channel.send() After LM Studio Failures

| Field | Value |
|-------|-------|
| **ID** | PENDING-001 |
| **Date** | 2026-05-21 |
| **Status** | 🔄 Open |
| **Severity** | Low |
| **Description** | In `message_processor.py`, when a `ConnectionError` or general `Exception` occurs during LM Studio response, `await channel.send(response_text)` is called without error handling. If the send fails (e.g., channel deleted, bot missing permissions, Discord API error), the error propagates unhandled. |
| **Code Location** | `src/discord_bot/message_processor.py` → `_process_session()` lines 184-201 |
| **Recommended Fix** | Wrap `channel.send()` in try/except to handle `discord.HTTPException`, `discord.Forbidden`, `discord.NotFound` gracefully. |
| **Files To Modify** | `src/discord_bot/message_processor.py` |

---

### PENDING-002: Hardcoded Turn Limit in Message Processing (range(3))

| Field | Value |
|-------|-------|
| **ID** | PENDING-002 |
| **Date** | 2026-05-21 |
| **Status** | 🔄 Open |
| **Severity** | Low |
| **Description** | Both `_process_session()` and `process_active_session()` use `for turn in range(3)` which hard-codes a maximum of 3 turns for tool calling. If a tool requires more than 2 retries, the loop exits silently. |
| **Code Location** | `src/discord_bot/message_processor.py` → `_process_session()` line 106, `process_active_session()` line 254 |
| **Recommended Fix** | Make the turn limit configurable (e.g., `max_tool_turns=5` parameter) or increase the default. |
| **Files To Modify** | `src/discord_bot/message_processor.py` |

---

### PENDING-003: Config Path Dependency Hardcoded

| Field | Value |
|-------|-------|
| **ID** | PENDING-003 |
| **Date** | 2026-05-21 |
| **Status** | 🔄 Open |
| **Severity** | Low |
| **Description** | Config path in `app.py` is computed as `Path(__file__).parent.parent / "config.json"` which assumes a specific project structure. |
| **Code Location** | `src/app.py` line 598 |
| **Recommended Fix** | Use an environment variable (e.g., `LM_CONFIG_PATH`) with fallback to the default path. |
| **Files To Modify** | `src/app.py` |

---

### PENDING-004: Session State Consistency on Processing Failure

| Field | Value |
|-------|-------|
| **ID** | PENDING-004 |
| **Date** | 2026-05-21 |
| **Status** | 🔄 Open |
| **Severity** | Low |
| **Description** | In `bot_core.py` `_process_active_session_batch()`, `self._session_manager.update_activity(channel_id)` is called before processing. If processing fails and the lock is released in the except block, there's no guarantee about session state consistency. |
| **Code Location** | `src/discord_bot/bot_core.py` → `_process_active_session_batch()` lines 532, 580-586 |
| **Recommended Fix** | Consider updating session activity only after successful processing, or use a try/finally pattern. |
| **Files To Modify** | `src/discord_bot/bot_core.py` |

---

### PENDING-005: Missing src/utils.py Import Verification

| Field | Value |
|-------|-------|
| **ID** | PENDING-005 |
| **Date** | 2026-05-21 |
| **Status** | 🔄 Open |
| **Severity** | Medium |
| **Description** | `tool_executor.py` imports `from src.utils import resize_image_bytes, image_to_base64`. This import chain should be verified to ensure image processing doesn't fail at runtime with ImportError. |
| **Code Location** | `src/discord_bot/tool_executor.py` lines 189, 263, 319 |
| **Recommended Fix** | Add a startup verification check in `app.py` or add unit tests for the image processing pipeline. |
| **Files To Verify** | `src/utils.py`, `src/discord_bot/tool_executor.py` |

---

## Memory Manager Sub-Project (Planned)

### FEAT-005: Memory Integration with memorylite - Restructured as Standalone Sub-Project

| Field | Value |
|-------|-------|
| **ID** | FEAT-005 |
| **Date** | 2026-05-21 |
| **Status** | ⏳ Planned - Restructured as `memory_manager` sub-project |
| **Description** | The memory integration feature was originally planned as a simple module under `src/memory/`. Due to its complexity and scope (entire memory system with SQLite persistence, user tracking, session association, and LM Studio tool calling), it has been restructured as a standalone sub-project under `memory_manager/` with its own documentation, issue tracking, and progress tracking. |
| **New Sub-Project Structure** | ``` memory_manager/ ├── README.md              - Description and architecture overview ├── issues_tracker.md      - Issue tracking for memory manager ├── progress.md            - Implementation progress tracking ``` |
| **Planned Features** | 1. User identity persistence across sessions 2. Per-channel conversation memory 3. Per-server memory isolation 4. Post-session memory creation 5. LM Studio tool calling for memory recall 6. SQLite-based persistent storage 7. Memory summarization and pruning |
| **Integration Points** | - `src/discord_bot/session_manager.py` - Session lifecycle hooks  - `src/discord_bot/bot_core.py` - Memory tool registration  - `src/tools/builtins/memory_tool.py` - Existing memory tool (to be refactored)  - `src/memory/memorylite.py` - Existing memorylite wrapper (to be moved) |
| **Files Created** | `memory_manager/README.md`, `memory_manager/issues_tracker.md`, `memory_manager/progress.md` |

---

## Known UX Improvements (Not Yet Fixed)

### UX-002: Mini-Context Image Descriptions Use Generic Prompt (Not User-Specific)

| Field | Value |
|-------|-------|
| **ID** | UX-002 |
| **Date** | 2026-05-19 |
| **Status** | 🔄 Known, Improvement Planned |
| **Severity** | Low (UX improvement) |
| **Description** | When LM Studio calls `image_describe` or `image_compare`, the mini-context prompt is always "Please describe this image in detail, up to 3-4 sentences." regardless of what the user actually asked. For example, when the user asks "Is the person in these images the same?", the mini-context should prompt "Describe the facial features and appearance relevant to identifying this person" instead of a generic description request. |
| **Current Behavior** | Mini-context sends generic "Please describe this image in detail, up to 3-4 sentences." → Generic description returned → Comparison/response uses generic descriptions |
| **Desired Behavior** | Mini-context should extract the user's question from conversation history and rephrase the prompt to focus on what the user is asking about → Targeted description returned → Better comparison/response |
| **Fix Required** | 1. Modify `_build_mini_context()` in `tool_executor.py` to accept optional `user_context` parameter 2. Extract user's last message from `messages_for_lm` history in `_handle_image_describe()` and `_handle_image_compare()` 3. Pass user context through to mini-context so prompt becomes: "The user asked: [question]. Describe the visual elements relevant to this question." 4. Apply same fix to `image_compare.py` → `compare_images_async()` |
| **Files To Modify** | `src/discord_bot/tool_executor.py`, `src/tools/builtins/image_compare.py` |

---

## Overview
Discord Bot + LM Studio Integration - First POC implementation

## Known UX Improvements (Not Yet Fixed)

### UX-002: Mini-Context Image Descriptions Use Generic Prompt (Not User-Specific)

| Field | Value |
|-------|-------|
| **ID** | UX-002 |
| **Date** | 2026-05-19 |
| **Status** | 🔄 Known, Improvement Planned |
| **Severity** | Low (UX improvement) |
| **Description** | When LM Studio calls `image_describe` or `image_compare`, the mini-context prompt is always "Please describe this image in detail, up to 3-4 sentences." regardless of what the user actually asked. For example, when the user asks "Is the person in these images the same?", the mini-context should prompt "Describe the facial features and appearance relevant to identifying this person" instead of a generic description request. |
| **Current Behavior** | Mini-context sends generic "Please describe this image in detail, up to 3-4 sentences." → Generic description returned → Comparison/response uses generic descriptions |
| **Desired Behavior** | Mini-context should extract the user's question from conversation history and rephrase the prompt to focus on what the user is asking about → Targeted description returned → Better comparison/response |
| **Fix Required** | 1. Modify `_build_mini_context()` in `tool_executor.py` to accept optional `user_context` parameter 2. Extract user's last message from `messages_for_lm` history in `_handle_image_describe()` and `_handle_image_compare()` 3. Pass user context through to mini-context so prompt becomes: "The user asked: [question]. Describe the visual elements relevant to this question." 4. Apply same fix to `image_compare.py` → `compare_images_async()` |
| **Files To Modify** | `src/discord_bot/tool_executor.py`, `src/tools/builtins/image_compare.py` |

---

## Approach
Web-based chat interface using Flask for LM Studio communication.
Switched from tkinter GUI to Flask web app due to tkinter unavailability on Fedora/Nobara with Python 3.13.

## Implementation Status

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

### In Progress 🔄
| Component | Status | Notes |
|-----------|--------|-------|
| Discord bot integration | 🔄 In Progress | Basic bot implemented, connected via GUI |
| LM Studio + Discord integration | ✅ Done | Bot forwards messages to LM Studio and posts responses |
| Tools system | ⏳ Not started | Phase 3 of original plan |
| Memory integration | ⏳ Not started | Phase 6 of original plan |

### Completed ✅ (Updated)
| Component | Status | Notes |
|-----------|--------|-------|
| Discord bot module | ✅ Done | `src/discord_bot.py` with mention/reply handling |
| Discord Flask endpoints | ✅ Done | connect, disconnect, status, info endpoints |
| GUI Discord integration | ✅ Done | Added Discord connect/disconnect UI in index.html |

### Not Started ⏳
| Component | Status | Notes |
|-----------|--------|-------|
| GUI module (tkinter) | ⏳ Skipped | Replaced with Flask web interface |
| Channel configuration | ⏳ Not started | Requires Discord bot |
| Built-in tools | ⏳ Not started | math_calc, image_describe, etc. |
| Models (conversation, session) | ⏳ Not started | Data models for state management |
| Memory module | ⏳ Not started | memorylite integration |

## Key Decisions
1. **Web GUI instead of tkinter**: tkinter not available for Python 3.13 on Fedora/Nobara. Flask web interface provides same functionality with broader compatibility.
2. **Session-based chat**: Flask sessions used for conversation history.
3. **Catppuccin Mocha theme**: Dark theme for comfortable long-term use.

## Testing Results
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

## Lessons Learned
- tkinter is not bundled with Python 3.13 on Fedora/Nobara
- Python version mismatch between system (3.14 with tkinter) and venv (3.13)
- Flask web interface is more portable than desktop GUI
- Using Flask sessions for conversation history works well for POC

## Next Steps
1. ✅ Test bot module import - PASSED
2. ✅ Test Flask app routes - PASSED (all 10 routes working)
3. ✅ Test Flask server startup with Discord bot - PASSED
4. ✅ Test Discord connection via web GUI - PASSED
5. ✅ Verify bot responds to mentions on Discord - PASSED
6. ✅ Fix Discord disconnect functionality - PASSED
7. ✅ Integrate LM Studio responses with Discord bot messages - DONE
8. ✅ Implement session end via LM Studio tool calling - DONE
9. ✅ Add chat_with_tools method to LM Studio client - DONE
10. ✅ Full end-to-end test on Discord - PASSED
11. ✅ Implement centralized logging system - DONE
12. ✅ Add real-time log feed to web UI - DONE
13. ✅ Add logging endpoints to Flask API - DONE
14. ✅ Add 5-second delay before message processing - DONE
15. ✅ Add show_typing tool for Discord typing indicator - DONE
16. ✅ Modular refactoring (app.py → app.py, chat_api.py, discord_api.py) - DONE
17. ✅ Token metrics streaming with real-time display - DONE
18. ✅ Add tools system (math, image description) - COMPLETED
19. ✅ message_handler.py modular refactoring (1025 → 6 files, all under 400) - DONE
20. ✅ bot_core.py modular refactoring (844 → split with delay_processor) - DONE
21. ✅ Fix image_describe tool not called by model (reasoning timeout) - DONE
22. ✅ Fix SessionManager.sessions attribute error in app.py - DONE
23. ✅ Fix image_describe channel_id duplicate kwarg bug - DONE
24. ⏳ JavaScript/HTML/CSS refactoring (server-config.js, script.js, debug_script.js)
25. ⏳ Add memory integration (restructured as memory_manager sub-project)
26. ⏳ Add channel configuration window

## FEAT-006: LM Studio Multi-Instance Management (2026-05-18)

### Problem
- No way to manage multiple LM Studio instances
- No UI to select which model to use
- Model selection only available via code/config

### Solution
- Created `src/lm_models/` package with data models, instance manager, and Flask API
- Added model dropdown to model info bar (appears when connected)
- Added "🧠 LM Instances" tab for multi-instance management
- Full CRUD for instances: add, remove, activate, test/discover models

### New Files Created
| File | Lines | Purpose |
|------|-------|---------|
| `src/lm_models/__init__.py` | ~10 | Package init |
| `src/lm_models/models.py` | ~88 | `ModelInfo`, `LmInstanceConfig`, `LmInstance` dataclasses |
| `src/lm_models/manager.py` | ~283 | `InstanceManager` with CRUD, model discovery, model selection |
| `src/lm_models/api.py` | ~194 | Flask Blueprint with 11 API endpoints |
| `src/static/lm-instances.css` | ~197 | Instance card styling |
| `src/static/lib/lm-instances.js` | ~200 | Instance management UI logic |

### Files Modified
| File | Changes |
|------|---------|
| `src/app.py` | Added `init_instance_manager()`, `lm_bp` blueprint, registered LM endpoints |
| `src/lm_studio_client.py` | Added `switch_instance()`, `selected_model` property, `chat_with_tools_stream()` |
| `src/config.py` | Added `lm_instances` and `active_instance` support |
| `src/templates/index.html` | Added model dropdown, LM Instances tab, linked CSS/JS |
| `src/static/script.js` | Added `updateModelSelect()`, `selectModel()`, LM instance state tracking |

### API Endpoints
- `GET /api/lm_instances` - List all instances
- `POST /api/lm_instances` - Add instance
- `GET/DELETE /api/lm_instances/<id>` - Get/remove instance
- `POST /api/lm_instances/<id>/activate` - Activate instance
- `POST /api/lm_instances/<id>/discover` - Discover models
- `GET/POST /api/lm_instances/<id>/select_model` - Model selection
- `GET/POST /api/lm_instances/active/model` - Active model management

### Bugs Fixed During Implementation
1. Config path: `parent.parent.parent` → `parent.parent`
2. Manager `_load()` didn't create default instance
3. API path mismatch: `/api/lm/...` vs `/api/lm_instances`
4. Field name mismatch: `connected` vs `is_connected`
5. Duplicate DOM ID: `lm-instances-tab` on both button and content

### Verification
- Backend API returns 1 instance with 15 discovered models
- UI tested and verified working by user

## Image Tools Fixes & New Feature (5/18/2026)

### Known Bugs (Not Yet Fixed)

#### BUG-007: max_tokens Retry Loop Exits Early
- **Status**: 🔄 Known, Will Fix Later
- **Problem**: The max_tokens retry logic in `message_processor.py` has a `break` statement that exits the loop instead of `continue`, preventing the retry with increased max_tokens from ever executing.
- **Evidence**: Logs show `Turn 2: content=''` with `completion_tokens: 2500` (hit max_tokens limit), `finish_reason: "length"`
- **Fix Required**: Change `break` to `continue` in `_process_session()` and `process_active_session()` methods
- **File**: `src/discord_bot/message_processor.py`

#### BUG-008: image_compare Fails on Same-Attachment URLs
- **Status**: 🔄 Known, Will Fix Later
- **Problem**: When user provides two URLs pointing to the same Discord attachment (one with query params, one without), the second URL fails to download.
- **Evidence**: Both URLs had same attachment ID `1505963986271731844`. Discord CDN returns `text/plain` even with Referer header retry.
- **Workaround**: Users should re-upload the second image if comparing different images.

---

### FIX-003: Empty Response After Tool Processing (max_tokens Overflow)
- **Status**: ✅ Implemented
- **Problem**: After tool processing (image_describe, image_compare), LM Studio returns empty content on Turn 2 with exactly 2500 completion tokens — hit max_tokens limit
- **Root Cause**: Tool result message + conversation history exceeds context window; LM Studio uses all tokens on reasoning/context
- **Solution**:
  1. Added `_execute_lm_call()` with `max_tokens_override` parameter
  2. When Turn N returns empty content after tool processing, auto-retry with `max_tokens * 2` (capped at 8192)
  3. Added warning message appended to context suggesting to increase max_tokens
  4. If retry also empty → OOM detection → user-friendly error message
  5. Added `_is_oom_error()` helper to detect OOM in exception strings
  6. Applied to both `_process_session()` and `process_active_session()`
- **Files Modified**: `src/discord_bot/message_processor.py`

### FIX-004: image_compare Discord CDN URL Retry (text/plain Content-Type)
- **Status**: ✅ Implemented
- **Problem**: Second image URL fails with "Blocked: disallowed content type 'text/plain'" — Discord CDN returns redirect page
- **Root Cause**: Discord CDN URLs with `?ex=...&is=...` params are temporary redirects without proper headers
- **Solution**: Added `_download_image_with_retry()` static method — on content-type error, retries with `Referer: https://discord.com/` header. Graceful fallback: proceeds with available images + failure note
- **Files Modified**: `src/tools/builtins/image_compare.py`

---

### FIX-001: Enhanced Tool Result Message to Prevent LM Studio Re-calling image_describe
- **Status**: ✅ Implemented
- **Problem**: After mini-context correctly describes an image, Turn 2 of the main conversation returns `content=''` with a tool call, causing LM Studio to re-call image_describe
- **Root Cause**: Tool result message was too weak: "The image has been described. Here's what was in the image: [description]. Please continue the conversation naturally, incorporating this information."
- **Fix**: Changed to explicit, authoritative message: "IMAGE DESCRIPTION COMPLETE: [description]. You now have full information about this image. DO NOT call image_describe again for this image. Respond to the user's question using this description."
- **Files Modified**: `src/discord_bot/tool_executor.py` → `_handle_image_describe()` and `_handle_image_describe_active()` (both variants)

### FIX-002: Handle URL Strings Passed as image_data Parameter
- **Status**: ✅ Implemented
- **Problem**: When LM Studio calls image_describe with a URL string instead of base64 data, the tool should detect and auto-download
- **Fix**: Added `_handle_image_data()` helper method that:
  1. Detects if image_data starts with "http" (URL string)
  2. Downloads via SafeImageDownloader if URL
  3. Detects MIME type from content bytes
  4. Resizes and converts to base64
  5. Returns (base64_data, mime_type) tuple
- **Files Modified**: `src/discord_bot/tool_executor.py` → new `_handle_image_data()` method

### FEAT-007: New image_compare Tool for Multi-Image Comparison
- **Status**: ✅ Implemented
- **Description**: Tool that accepts 2-3 image URLs, downloads each, describes via mini-context, then generates structured comparison
- **New Files Created**:
  | File | Lines | Purpose |
  |------|-------|---------|
  | `src/tools/builtins/image_compare.py` | ~220 | ImageCompareTool class with async comparison via mini-context |
- **Files Modified**:
  | File | Changes |
  |------|---------|
  | `src/tools/builtins/__init__.py` | Added ImageCompareTool export |
  | `src/discord_bot/bot_core.py` | Added ImageCompareTool import and registration |
  | `src/discord_bot/tool_executor.py` | Added `_handle_image_compare()` and `_handle_image_compare_active()` methods |
  | `src/discord_bot/message_handler.py` | Updated system prompt with image_compare tool description and re-call prevention |
- **Features**:
  - Accepts `image_urls` array (2-3 items) and optional `comparison_prompt`
  - Downloads all images via SafeImageDownloader
  - Describes each image via isolated mini-context (no conversation history)
  - Combines descriptions into structured comparison prompt
  - Returns formatted comparison covering: similarities, differences, key elements, patterns
- **Tool Definition**:
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
  ```

---

## Recent Fixes (5/16/2026)

### ISS-019: DelayProcessor Parameter Mismatch (Solved)
- **Status**: ✅ Solved
- **Symptom**: `TypeError: DelayProcessor.process_active_session_with_delay() got an unexpected keyword argument 'author_nick'`
- **Root Cause**: `bot_core.py` was passing `author_nick=author_nick` to `process_active_session_with_delay()`, but the method signature only accepts `author_name` and `author_display`
- **Fix**: Removed `author_nick=author_nick` from the call in `bot_core.py` line 388
- **Files Modified**: `src/discord_bot/bot_core.py`

### ISS-020: Global LM Studio Lock to Prevent Concurrent Requests / OOM (Implemented)
- **Status**: ✅ Implemented
- **Problem**: When messages arrive in two different channels simultaneously, both get submitted to the thread pool and call LM Studio concurrently, potentially causing OOM errors
- **Solution**: Added `asyncio.Lock()` in `bot_core.py` that serializes all LM Studio API calls
- **Implementation**:
  1. Added `self._lm_studio_lock = asyncio.Lock()` to `DiscordBot.__init__()`
  2. Added `lm_studio_lock` parameter to `MessageHandler.__init__()`
  3. Added `_call_lm_studio()` helper method that acquires the global lock before each API call
  4. Wrapped all 6 LM Studio API call sites with `_call_lm_studio()`:
     - `_process_message`: tool calling, non-tool calling, mini-context image description
     - `_process_active_session`: tool calling, non-tool calling, mini-context image description
  5. Added logging: "Waiting for LM Studio lock", "Acquired LM Studio lock", "Released LM Studio lock"
- **Files Modified**: `src/discord_bot/bot_core.py`, `src/discord_bot/message_handler.py`
- **Verification**: Logs confirm channel 1502926836970291232 acquires lock first, channel 1503498074851508476 waits and acquires after release

### ISS-021: DelayProcessor Handler Callback Signature Mismatch (Solved)
- **Status**: ✅ Solved
- **Symptom**: `TypeError: DiscordBot._process_active_session_batch() missing 1 required positional argument: 'pending_messages'`
- **Root Cause**: `delay_processor.py` passed `pending` as the 6th positional argument, but `_process_active_session_batch` expects `pending_messages` as the 7th positional arg (after `author_nick`)
- **Fix**: Changed call to pass `None` for `author_nick` and `pending_messages=pending` as keyword arg
- **Files Modified**: `src/discord_bot/delay_processor.py`

### Configuration Updates (5/16/2026)
- **Status**: ✅ Completed
- **Changes**:
  1. `allowed_image_hostnames` defaults set to `["cdn.discordapp.com", "media.discordapp.net"]` in all config files
  2. `message_delay` default set to 5 in all config files
  3. `config_template.json` updated with missing settings (`suppress_werkzeug_logging`, `message_delay`, `system_prompt`, `allowed_image_hostnames`, `servers`)
- **Files Modified**: `src/config.py`, `config.json`, `config_template.json`

## Logging System Implementation (Added 5/11/2026)
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

## Message Processing Improvements (Added 5/11/2026)
| Component | Status | Notes |
|-----------|--------|-------|
| 5-second delay | ✅ Done | Messages wait 5 seconds before processing (allows for follow-up messages) |
| `show_typing` tool | ✅ Done | LM Studio can call this tool to show "Bot is typing..." indicator |
| Tool calling with both tools | ✅ Done | Both show_typing and end_session tools sent to LM Studio |
| Delayed message handlers | ✅ Done | `_delayed_handle_message` and `_delayed_process_active_session` methods |
| Typing indicator execution | ✅ Done | `_show_typing_indicator` method executes when LM Studio calls the tool |
| Multi-turn tool calling | ✅ Done | Loop until LM Studio returns response without tool calls |

## Typing Indicator & Message Processing Fixes (Added 5/11/2026 - ISS-007)
| Component | Status | Notes |
|-----------|--------|-------|
| Immediate typing indicator | ✅ Done | Typing indicator now shows immediately in `on_message` handler when mention/reply received |
| No delay for first messages | ✅ Done | First messages (new session) process immediately; delay only applies to active session messages |
| ThreadPoolExecutor for LM Studio | ✅ Done | LM Studio API calls run in background thread to prevent blocking async event loop |
| discord.py 2.x typing API | ✅ Done | Fixed deprecated `channel.send_typing()` → `async with channel.typing():` context manager |
| Multiple typing indicator refresh | ✅ Done | Typing indicator refreshed on each retry turn (turn > 0) during multi-turn tool calling |

## Session End Fixes (Added 5/11/2026 - ISS-008)
| Component | Status | Notes |
|-----------|--------|-------|
| Duplicate goodbye fix | ✅ Done | Set `response_text = None` when end_session detected in `_handle_active_session_message()` |
| Only farewell from tool args | ✅ Done | Only the farewell message from tool call arguments is posted, not both response and farewell |

## Message Queue & Processing Improvements (Added 5/11/2026)
| Component | Status | Notes |
|-----------|--------|-------|
| Pending messages queue | ✅ Done | `_pending_messages` dict stores messages received while bot is processing |
| Queue on processing lock | ✅ Done | When `_processing_lock` is active, messages are queued instead of dropped |
| Batch message processing | ✅ Done | `_handle_active_session_message_batch()` combines main + queued messages into single request |
| Post-response queue check | ✅ Done | After posting response, `_process_queued_pending_messages()` checks for queued messages |
| Chain reaction processing | ✅ Done | Bot processes queued messages immediately after posting, keeps going until queue empty |
| Empty message skip | ✅ Done | Empty/whitespace-only messages are skipped with logging |
| Lock management | ✅ Done | Lock cleared before queue processing, re-acquired by queue handler |

## Security Fixes (Added 5/11/2026)
| Component | Status | Notes |
|-----------|--------|-------|
| Error message sanitization | ✅ Done | Internal error details no longer exposed to Discord users |
| Generic error responses | ✅ Done | All error handlers return "⚠️ Sorry, I encountered an error processing your message." |
| Traceback protection | ✅ Done | Error tracebacks logged server-side only, never sent to Discord |

## BUG-003: Discord User Identity Tracking (5/14/2026)

### Problem
- Bot had no knowledge of who is talking to it
- When asked "What is my name?" the bot responded "I don't know your name"
- Per-server nicknames were never extracted or communicated to LM Studio

### Solution
- Extracted `author_nick = message.author.nick` (per-server nickname)
- Extended identity tracking through entire call chain
- Updated system prompt with full identity context (username, display, nickname, user ID)
- Extended SessionManager to store identity data for memory integration

### Identity Model
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

### Attribution Examples
- **New session:** `[From guzu (nickname: Picatchu, display: Guzu)]: hello`
- **Session with nick change:** `[guzu (was: Guzu, now: Picatchu)]: I changed my name`
- **Different user in channel:** `Picatchu (guzu) says: I'm here too`

### New/Modified Files
| File | Changes |
|------|---------|
| `src/discord_bot/bot_core.py` | Extract `author_nick`, pass through call chain, add `_get_display_name_for_user()` helper, extend session start with identity data |
| `src/discord_bot/message_handler.py` | Accept `author_nick`/`initial_nick` params, update system prompt with identity context, update message attribution format |
| `src/discord_bot/session_manager.py` | Add `_session_data` dict, extend `start_session()` with identity fields, add `get_session()` method |

---

## Known Issues (Pending Fix)

### ISS-005: Werkzeug HTTP 200 Log Spam
- **Status**: 🔄 Open
- **Symptom**: `/api/logs` requests every 3 seconds clutter terminal with 200 status logs
- **Impact**: Makes troubleshooting other issues difficult
- **Fix**: Add config option to disable/reduce Werkzeug request logging

## Security: Safe Image Download with Hostname Whitelist (Added 5/12/2026)

### Problem
- LM Studio calls `image_describe` with image URLs
- Original code downloaded from ANY URL without validation
- Security risks: SSRF (Server-Side Request Forgery), arbitrary file downloads

### Solution
- Added `SafeImageDownloader` class with whitelist-based hostname validation
- Allowed hostnames configurable via `config.json` → `settings.allowed_image_hostnames`
- All allow/deny decisions are logged

### New Files/Changes
| File | Changes |
|------|---------|
| `src/config.py` | Added `allowed_image_hostnames` property with default `["cdn.discordapp.com", "media.discordapp.net"]` |
| `src/discord_bot/message_handler.py` | Added `SafeImageDownloader` class, `get_safe_downloader()` function |
| `src/discord_bot/bot_core.py` | Pass `allowed_image_hostnames` from config to `MessageHandler` |

### SafeImageDownloader Features
| Feature | Description |
|---------|-------------|
| **Hostname whitelist** | Only URLs from allowed hostnames are downloaded |
| **Scheme validation** | Only `http` and `https` schemes allowed |
| **Content-type validation** | Only image content types (`image/jpeg`, `image/png`, etc.) |
| **Size limit** | Max 10MB download (with chunked reading) |
| **Timeout** | 30 second timeout per download |
| **Logging** | ALLOWED/BLOCKED decisions logged with hostname and reason |

### Log Examples
```
# Allowed URL
INFO - ALLOWED: hostname 'cdn.discordapp.com' is in allowed list
INFO - Downloading image from allowed host: cdn.discordapp.com
INFO - Content type allowed: image/jpeg
INFO - Successfully downloaded 123456 bytes from cdn.discordapp.com

# Blocked URL
WARNING - BLOCKED: hostname 'evil.com' is NOT in allowed list: ['cdn.discordapp.com', 'media.discordapp.net']
WARNING - Image download blocked: URL blocked: Hostname 'evil.com' not in allowed hostnames (URL: http://evil.com/malware.exe)
```

---

### Bug: Allowed Hostnames Not Passed from Config (Solved)

| Field | Value |
|-------|-------|
| **ID** | BUG-001 |
| **Date** | 2026-05-12 |
| **Status** | ✅ Solved |
| **Date Solved** | 2026-05-13 |
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

## Tools System Implementation (Added 5/12/2026)

### Image Describe Tool Implementation
- **Status**: ✅ Solved
- **Description**: Implemented the full tools system infrastructure and image_describe tool
- **New Files Created**:
  - `src/tools/base.py` (~70 lines) - BaseTool abstract class, ToolResult dataclass
  - `src/tools/executor.py` (~120 lines) - ToolExecutor with text and image result handling
  - `src/tools/registry.py` (~90 lines) - ToolRegistry for managing tool lifecycle
  - `src/tools/builtins/image_describe.py` (~130 lines) - ImageDescribeTool class
  - `src/utils.py` (~160 lines) - Image processing utilities (resize, base64, MIME detection)
- **Modified Files**:
  - `src/tools/builtins/__init__.py` - Export ImageDescribeTool
  - `src/discord_bot/bot_core.py` - Register ImageDescribeTool, pass tool definitions to MessageHandler
  - `src/discord_bot/message_handler.py` - Add register_tool method, update system prompt with image_describe
- **Features Implemented**:
  - BaseTool abstract class with to_dict() for OpenAI-compatible format
  - ToolExecutor with execute() and execute_with_image_support() methods
  - ToolRegistry for registration, filtering by enabled status
  - ImageDescribeTool with security measures (5MB limit, 768px max dimension, in-memory processing)
  - Integration with Discord bot via tool definitions list
  - System prompt updated to include image_describe tool description
- **Security Measures**:
  - Max image size: 5MB
  - Max dimension: 768px (auto-resized)
  - In-memory processing only (no disk writes)
  - Base64 URL prefix handling
  - Error handling for corrupted/malformed images

---

## Recent Fixes (5/11-5/12/2026)

### Modular Refactoring (5/12/2026)
- **Problem**: `app.py` was 785 lines and `discord_bot.py` was 1005 lines, making maintenance difficult
- **Solution**: Split Flask endpoints into separate modules using Blueprints
- **Files Created**:
  - `src/chat_api.py` (~200 lines) - Chat/LM Studio endpoints
  - `src/discord_api.py` (~230 lines) - Discord endpoints + thread management
- **Files Modified**:
  - `src/app.py` (~230 lines) - Now clean Flask app factory with Blueprint registration
- **Benefits**: Better separation of concerns, easier to maintain and test

### Token Metrics Streaming Display (5/12/2026)
- **Problem**: No way to see token usage statistics or debug LM Studio responses
- **Solution**: Added streaming SSE endpoint with real-time token metrics display
- **New Files**:
  - Token Metrics tab in web UI with metrics panel and live stream display
  - CSS styles for token metrics panels
- **Modified Files**:
  - `lm_studio_client.py` - Added `chat_stream_with_usage()` and `chat_with_tools_stream()` methods
  - `chat_api.py` - Added `/api/chat/stream`, `/api/tokens/last`, `/api/tokens/reset` endpoints
  - `index.html` - Added Tokens tab with metrics grid and stream content area
  - `styles.css` - Added token metrics panel styling
  - `script.js` - Added `sendStreamingMessage()`, token update functions, SSE event reader
- **Features**:
  - Real-time token generation display (completion tokens, speed, time)
  - Prompt/Completion/Total token breakdown
  - Tokens per second speed metric
  - Live text streaming in Tokens tab
  - Usage summary after generation completes
- **API Endpoints**:
  - `POST /api/chat/stream` - SSE stream with token chunks + usage data
  - `GET /api/tokens/last` - Get last token usage stats
  - `POST /api/tokens/reset` - Reset token usage data
- **Fix**: Set `response_text = None` when end_session detected in active session

### ISS-009: Messages Lost During Active Session Processing
- **Status**: ✅ Solved
- **Fix**: Message queuing with `_pending_messages` dict and batch processing

### ISS-010: Security - Error Tracebacks Exposed to Users
- **Status**: ✅ Solved
- **Fix**: Generic sanitized error messages sent to Discord

### ISS-011: Duplicate Message Handlers Running Simultaneously
- **Status**: ✅ Solved
- **Fix**: Lock management improvements

### ISS-012: Empty Messages Cause LM Studio API Errors
- **Status**: ✅ Solved
- **Fix**: Early skip for empty/whitespace-only messages

### max_tokens Configurable from Web UI
- **Status**: ✅ Solved
- **Fix**: Added UI input, JS functions, API endpoints, and config setter for max_tokens (1-8192)

### Message Delay Configurable from Web UI
- **Status**: ✅ Solved
- **Fix**: Added UI input, JS functions, API endpoints for message delay (1-30 seconds)

### System Prompt Configurable from Web UI
- **Status**: ✅ Solved
- **Fix**: Added textarea, save/reset buttons, API endpoints for system prompt

### Temperature Configurable from Web UI (2026-05-12)
- **Status**: ✅ Solved
- **Fix**: Added UI input, JS functions, API endpoints, and config setter for temperature (0.0-2.0)
- **Files Modified**:
  - `config.py` - Added temperature getter/setter properties
  - `app.py` - Added GET/POST `/api/settings/temperature` endpoints with Discord bot integration
  - `index.html` - Added temperature input field in settings section
  - `script.js` - Added loadTemperature(), updateTemperature(), updateTemperatureStatusText() functions

### Max Response Length Configurable from Web UI (2026-05-12)
- **Status**: ✅ Solved
- **Fix**: Added UI input, JS functions, API endpoints, and config setter for max_response_length (100-10000)
- **Files Modified**:
  - `config.py` - Added max_response_length getter/setter properties
  - `app.py` - Added GET/POST `/api/settings/max_response_length` endpoints
  - `index.html` - Added max_response_length input field in settings section
  - `script.js` - Added loadMaxResponseLength(), updateMaxResponseLength(), updateMaxResponseLengthStatusText() functions

### Dynamic Settings Application to Discord Bot (2026-05-12) - Task 5
- **Status**: ✅ Solved
- **Description**: When settings are changed from the web UI while Discord bot is running, the changes are now applied immediately without restart
- **Settings Applied Dynamically**:
  - `temperature` - Applied via `set_lm_studio_params()` when changed
  - `max_tokens` - Already applied via `set_lm_studio_params()` (was pre-existing)
  - `message_delay` - Applied via `set_message_delay()` when changed
  - `system_prompt` - Applied via `set_system_prompt()` when changed
- **Files Modified**:
  - `app.py` - Added `discord_bot_instance.set_lm_studio_params()` call in temperature endpoint
  - `app.py` - Added `discord_bot_instance.set_message_delay()` call in delay endpoint
  - `app.py` - Already had `discord_bot_instance.set_system_prompt()` call in system_prompt endpoint

### Discord Bot Modular Refactoring (5/12/2026)
- **Problem**: `discord_bot.py` was 1077 lines, making maintenance and debugging difficult
- **Solution**: Split into 6 focused modules under `src/discord_bot/` package with single-responsibility design
- **New File Structure**:
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
- **Modified Files**:
  - `src/discord_bot.py` (~18 lines) - Now a backward-compat wrapper that imports from `src/discord_bot/`
- **Benefits**:
  - Single Responsibility: Each file has one clear purpose
  - Easier Testing: Unit tests can target individual modules
  - Easier Debugging: Issues are isolated to specific files
  - Better Navigation: Developers find code faster in smaller files
  - Scalable: Easy to add new features without bloating one file
- **Token Usage Tracking**: Added `TokenTracker` class with thread-safe per-channel token usage storage
  - `store_token_usage(channel_id, usage)` - Stores token metrics
  - `get_channel_token_usage(channel_id)` - Gets usage for a specific channel
  - `get_last_discord_token_usage()` - Gets most recent usage across all channels

### Context Persistence Fix (5/12/2026) - ISS-018
- **Problem**: Bot loses conversation context after each message in active sessions. Every message treated as "turn 1".
- **Root Cause**: `conversation_history = {channel_id: history}` in `_process_active_session()` created a new local dict instead of mutating the shared one. Additionally, `_process_active_session` did not receive `conversation_history` as a parameter.
- **Fix**: 
  1. Changed `conversation_history = {channel_id: history}` to `conversation_history[channel_id] = history`
  2. Added `conversation_history` parameter to `_process_active_session()` method signature
  3. Updated `handle_active_session_batch()` to pass `conversation_history` to `_process_active_session()`
- **Verification**: Bot now correctly maintains context within sessions. When asked to summarize questions, it returns all previous questions in a table.

### Discord Bot Message Processing Fixes (5/12/2026)
- **Problem**: Multiple issues with message queuing, context overflow, and session management
- **Fixes Applied**:

#### ISS-014: Naming Conflict Fix
- **Problem**: `src/discord/` package shadowed discord.py library
- **Fix**: Renamed package to `src/discord_bot/`

#### ISS-015: Pending Messages Not Included in LM Studio Batch
- **Problem**: Queued messages were popped but never sent to LM Studio
- **Fix**: Changed `all_user_messages.extend(pending_messages)` to include pending messages in batch content

#### Context Overflow Fix
- **Problem**: Conversation history grew unbounded, causing 5990-token contexts and empty LM Studio responses
- **Fix**: Added history truncation in `_process_active_session()` - keeps system prompt + last 20 messages (10 exchanges)

#### Session End Fix
- **Problem**: `end_session` tool call continued to Turn 2 after farewell
- **Fix**: Added `break` after `end_session` in both inner (tool loop) and outer (turn loop) loops

#### Session Clear Fix
- **Problem**: Session was never cleared after `end_session` tool call
- **Fix**: Added `should_end_session` return value from `handle_active_session_batch()` → `bot_core.py` now calls `clear_session()` when `should_end_session=True`

#### Race Condition Fix
- **Problem**: Lock set AFTER delay, so messages during delay were not queued
- **Fix**: Moved `processing_lock[channel_id] = True` to BEFORE `await asyncio.sleep()` in delay_processor

#### Queue Check After New Session
- **Problem**: Messages queued during new session were never processed after response
- **Fix**: Added `await self._process_queued_pending_messages()` at end of `_handle_new_session_message()`

#### Typing Indicator for Queue Processing
- **Problem**: No typing indicator shown when processing queued messages
- **Fix**: Added `await self._typing_indicator.show(message.channel)` in `_process_queued_pending_messages()`

### Message Processing Flow (Current)
1. **New session** (mention/reply) → Send to LM Studio immediately
2. **Active session** → Set lock → Start delay → Messages queue during delay
3. **Delay complete** → Main message + pending messages → LM Studio as batch
4. **Response posted** → Check queue → If not empty → Typing indicator → Process next batch
5. **Queue empty** → Wait for new messages
6. **"bye"** → LM Studio calls `end_session` → Session cleared → Back to step 1

## Discord Connection Fixes (5/13/2026)

### DISCORD-001: Discord Bot Stuck After Flask App Restart (Stale State)
- **Problem**: When Flask app is restarted via debug reloader, Discord bot fails to connect/disconnect properly. Error: "Bot is already connected to Discord"
- **Root Cause**: Flask's debug reloader restarts the Python process, resetting module globals (`discord_connected = False`, `discord_bot_thread = None`) while old Discord bot threads from the previous process may still be running. When `on_ready()` fires on the old thread, it updates `discord_connected = True` via `sys.modules`. The new Flask app sees `discord_connected = True` even though its own `discord_bot_thread` is `None`.
- **Fix Applied**:
  1. Added `force_reset_discord_state()` function in `discord_api.py` to reset all Discord-related globals
  2. Called `force_reset_discord_state()` at Flask app startup in `app.py`
  3. Improved `start_discord_bot_thread()` to detect and clean up stale state before starting
  4. Improved `stop_discord_bot()` to handle edge cases (None thread, None stop event, bot instance)
  5. Added `/api/discord/force_reset` endpoint for manual reset from debug page
  6. Added "🔥 Force Reset Discord" button on the debug page
- **Files Modified**: `src/discord_api.py`, `src/app.py`, `src/templates/debug.html`, `src/static/debug_script.js`

### DISCORD-002: UI Shows "Not Connected" Despite Bot Thread Running (Stale Import)
- **Problem**: After the Discord bot thread starts successfully (confirmed by logs), the UI still shows "Not connected". The `/api/status` endpoint returns `discord_connected: false` even though the bot thread is running.
- **Root Cause**: Python's `from module import variable` creates a **local reference** to the value at import time, not a live link to the module attribute. In `app.py`, the code used: `from src.discord_api import discord_connected, ...`. When `bot_core.py` updated `discord_api.discord_connected = True` directly, this only changed the module attribute, not `app.py`'s local `discord_connected` variable.
- **Fix Applied**: Changed `app.py` to import the module (`from src import discord_api`) instead of individual variables. Created helper functions `_get_discord_connected()`, `_get_discord_bot_instance()`, `_get_discord_status_message()` that always read from the module attribute dynamically. Updated all endpoints to use these helpers.
- **Files Modified**: `src/app.py`

### DISCORD-003: UnboundLocalError in get_sessions (sessions variable not initialized)
- **Problem**: `get_sessions()` endpoint throws `UnboundLocalError: cannot access local variable 'sessions' where it is not associated with a value`
- **Root Cause**: The `sessions` list was only defined inside the `if isinstance(channels, dict)` block. When `channels` was a list, `sessions` was never initialized.
- **Fix Applied**: Moved `sessions = []` to the top of the try block. Added `elif isinstance(channels, list)` branch to handle list-type channels.
- **Files Modified**: `src/app.py`

### Discord Disconnect RuntimeWarning Fix
- **Problem**: `RuntimeWarning: coroutine 'wait_for' was never awaited` when disconnecting Discord bot
- **Root Cause**: `close_client()` async function was defined and called via `loop.run_until_complete()` from the Flask main thread's event loop. But the event loop was created in the **bot thread**, not the Flask main thread. Calling `run_until_complete()` from a different thread's event loop causes undefined behavior.
- **Fix Applied**: Removed the problematic `close_client()` coroutine attempt. Now relies on the bot thread's own `_wait_for_stop_event()` mechanism for graceful shutdown. The stop event is set, and the bot thread handles cleanup internally.
- **Files Modified**: `src/discord_api.py`

### Main Page "Connect LM Studio First" Warning Fix
- **Problem**: The warning "⚠️ Connect LM Studio first for AI responses" was stuck on the main page even after LM Studio was connected.
- **Root Cause**: `checkStatus()` in `script.js` updated `state.lmConnected` but never called `updateModelInfo()` to sync the integration note. The note was only updated when `connectLM()` was called explicitly.
- **Fix Applied**: Added `updateModelInfo(data.lm_model, data.lm_models, state)` call at the end of `checkStatus()` so the note updates on every status poll (every 2 seconds).
- **Files Modified**: `src/static/script.js`

---

## Debug Panel Fixes (5/13/2026)

### DEBUG-001: Debug Page Not Showing Logs
- **Problem**: Debug page at `/debug` was not displaying any log entries despite logs being generated server-side
- **Root Cause**: The `updateDebugLogDisplay` function in `lib/logs.js` was not being called properly from the debug page's own `fetchDebugLogs()` function. The shared `fetchLogs()` function was calling it, but the debug page's direct call had no error handling and relied on the shared function.
- **Fix Applied**:
  1. Rewrote `fetchDebugLogs()` in `debug_script.js` to directly call the API and `updateDebugLogDisplay()`
  2. Added comprehensive console logging for debugging (`[DebugPanel]` prefix)
  3. Added `testLogDisplay()` function to verify log pipeline on page load
  4. Added `lastApiResponse` and `lastLogApiResponse` tracking in `debugState`
  5. Fixed `updateDebugLogDisplay()` in `lib/logs.js` with better error handling and console output
- **Files Modified**: `src/static/debug_script.js`, `src/static/lib/logs.js`

### DEBUG-002: JavaScript Syntax Error on Token Refresh
- **Problem**: `Uncaught SyntaxError: invalid assignment left-hand side` on line 355 of `debug_script.js`
- **Root Cause**: Optional chaining `?.` was used on the left-hand side of an assignment: `document.getElementById('...')?.textContent = value`. This is invalid JavaScript because `?.` can only be used for reading, not writing.
- **Fix Applied**: Changed to explicit element checks:
  ```javascript
  const el = document.getElementById('debugPromptTokens');
  if (el) el.textContent = data.usage.prompt_tokens?.toLocaleString() || '-';
  ```
- **Files Modified**: `src/static/debug_script.js` → `refreshDebugTokens()`

### DEBUG-003: Discord Status Always Shows "Not Connected"
- **Problem**: Discord bot status always shows `discord_connected: false` in `/api/status` response even after clicking "Connect" on the main page. The bot IS connecting to Discord (confirmed by user).
- **Root Cause**: The `on_ready()` callback in `bot_core.py` uses `asyncio.create_task(self._on_status_change_callback(...))` to notify the parent module of the connection status. However, this callback mechanism fails silently because:
  1. The callback is an async function defined in `_discord_bot_thread_func()` in a **different thread**
  2. `asyncio.create_task()` swallows exceptions if no custom exception handler is set on the task
  3. The event loop running the callback is created in the bot thread, but the callback's `global discord_connected` update may fail because the task never actually executes
  4. The `on_ready()` event fires in the discord.py internal event loop, NOT in the bot thread's event loop
- **Fix Applied**: Added direct global variable update in `on_ready()` using `sys.modules.get('src.discord_api')` to access and update the `discord_connected` and `discord_status_message` globals directly. The callback is kept as a fallback.
- **Files Modified**: `src/discord_bot/bot_core.py` → `_register_events()` → `on_ready()`
- **Lesson**: Cross-thread async callbacks are unreliable for updating module-level globals. Always update shared state directly in event handlers, and use callbacks only for notification purposes.
- **Status**: ✅ Requires Flask app restart to test

### DEBUG-004: Added Discord Connect Button to Debug Page
- **Problem**: No way to test Discord connection directly from the debug page
- **Fix Applied**: Added token input field and "Connect Discord" button to the debug page's Discord status panel, plus `connectDiscordFromDebug()` function
- **Files Modified**: `src/templates/debug.html`, `src/static/debug_script.js`

---

## Debug Panel Implementation (Added 5/12/2026)

### Problem
- Debug/logging tools were mixed with the main user interface
- Flask debug mode caused duplicate log entries in terminal
- No dedicated page for monitoring sessions, diagnostics, and advanced settings

### Solution
- Created separate debug page at `/debug` route
- Moved advanced debugging tools to dedicated page
- Kept user-facing settings in main page

### New Files Created
| File | Purpose | Lines |
|------|---------|-------|
| `src/templates/debug.html` | Debug panel UI | ~160 |
| `src/static/debug_styles.css` | Debug page styling (Catppuccin Mocha) | ~350 |
| `src/static/debug_script.js` | Debug page JavaScript | ~380 |

### Modified Files
| File | Changes |
|------|---------|
| `src/templates/index.html` | Added "🔧 Debug Panel" button |
| `src/static/script.js` | Added `openDebugPanel()` function |
| `src/app.py` | Added `/debug` route, session management endpoints, token debug endpoint |

### Debug Panel Features
| Feature | Description | Endpoint |
|---------|-------------|----------|
| Connection Status | Real-time LM Studio + Discord status | `/api/status` |
| Session Manager | View/clear active Discord sessions | `/api/discord/sessions` |
| Token Metrics | Token usage stats for Discord bot | `/api/tokens/debug/refresh` |
| Settings Override | Quick setting changes with validation | `/api/settings/*` |
| LM Studio Override | Host/port inputs for reconnection | N/A |
| Diagnostics | Test connections, force disconnect | Various |
| Application Logs | Full log viewer with filtering | `/api/logs` |

### New API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/debug` | GET | Render debug panel page |
| `/api/discord/sessions` | GET | Get active sessions |
| `/api/discord/clear_session` | POST | Clear specific channel session |
| `/api/discord/clear_all_sessions` | POST | Clear all sessions |
| `/api/tokens/debug/refresh` | GET | Get Discord token metrics |

### Usage
1. Open main page at `http://localhost:5000/`
2. Click "🔧 Debug Panel" button
3. Opens new tab with debug tools
4. Close debug tab to return to main page

### Debug Panel Fixes (Added 5/12/2026)
| Issue | Fix |
|-------|-----|
| Missing `debugLmHost`/`debugLmPort` elements | Added LM Studio Override section with Host/Port inputs |
| Logs not displaying on page load | Fixed initialization: `lastLogCount` set to 0, all logs render on first fetch |
| "No logs" state not shown | Added "No logs available" placeholder when log API returns empty |
| Unclear Discord test error | Improved message: "please connect via main page first" |

---

## Planned Features

### 🆕 Server Configuration System (Backend Complete, UX Improvements Planned - FEAT-001)
- **Status**: ✅ Backend Complete, UI UX Improvements In Progress (UX-001)
- **Description**: Per-server enable/disable and per-channel allow/deny lists with web UI management
- **Completed Implementation**:
  1. **config.py** - ✅ Added `servers` configuration section with per-server settings (lines 204-343)
  2. **bot_core.py** - ✅ Added `_is_server_enabled()` and `_is_channel_allowed()` checks in message handler
  3. **discord_api.py** - ✅ Added all server management API endpoints (lines 391-587)
  4. **index.html** - ✅ Added "Server Config" tab (lines 175-260)
  5. **server-config.js** - ✅ Full CRUD UI logic (280 lines)
- **Known UX Limitations** (See UX-001 in issues_tracker.md):
  1. ❌ No auto-discovery of Discord servers - must manually type server IDs
  2. ❌ Server list shows only raw IDs, no human-readable server names
  3. ❌ No auto-discovery of channels - must manually type channel IDs
  4. ❌ Channel lists show only raw IDs, no channel names or #prefix

### 🆕 UX-001: Server Config Auto-Discovery (Completed - 2026-05-14)
- **Status**: ✅ Completed
- **Description**: Add auto-discovery of Discord servers and channels to the Server Config UI
- **Implementation Status**:
  1. **bot_core.py** - ✅ Added `get_guilds_info()` and `get_guild_channels(guild_id)` methods to DiscordBot class
  2. **discord_api.py** - ✅ Added `GET /api/discord/servers` endpoint (list all guilds with names)
  3. **discord_api.py** - ✅ Added `GET /api/discord/channels/<guild_id>` endpoint (list channels with names and categories)
  4. **server-config.js** - ✅ Added "📡 Load Servers from Discord" button and auto-discovery logic
  5. **server-config.js** - ✅ Added "🔍 Load Channels from Discord" button when editing a server
  6. **server-config.js** - ✅ Server list now shows names: "My Server (123456789012345678)"
  7. **server-config.js** - ✅ Channel list now shows names: "#general (111111111111111111) (Category)"
  8. **index.html** - ✅ Added "📡 Load Servers from Discord" button in Server Config tab header
  9. **server-config.js** - ✅ Added quick-add dropdown for servers when discovered
  10. **server-config.js** - ✅ Added quick-add dropdown for channels when discovered

### 🆕 BUG-004: Channel Filter Not Working Due to Server ID Mismatch (Solved - 2026-05-14)
- **Status**: ✅ Solved
- **Description**: The bot processes messages from all channels despite denied_channels being configured in config.json.
- **Root Cause**: Server ID mismatch between config.json and actual Discord guild ID.
  - Config saved for: `1502926835862864000`
  - Actual Discord guild: `1502926835862863944`
  - The bot looks up config using actual guild ID, finds no match, uses default (all channels allowed)
- **Fix Applied**: Updated config.json server ID from `1502926835862864000` to `1502926835862863944`
- **Debug Logging Added**:
  1. **bot_core.py** - Added detailed channel filter debug logging (guild_id, channel_id, allowed_channels, denied_channels, is_channel_allowed result)
  2. **discord_api.py** - Added config save/verify logging and channel API request logging
- **Files Modified**: `config.json`, `src/discord_bot/bot_core.py`, `src/discord_api.py`

### 🆕 BUG-005: Server Config Changes Not Applied to Running Bot (Stale Config Reference - Solved - 2026-05-14)
- **Status**: ✅ Solved
- **Description**: Server/channel config changes saved to disk via the web UI were not reflected in bot behavior. The bot continued showing `allowed_channels=[]` and `denied_channels=[]` even after saving config.
- **Root Cause**: The Discord bot holds a stale `Config` instance from startup. When the API saves config, it creates a **new** `Config()` instance, saves to disk, and returns. The bot's `_config` is never updated with the new data.
- **Fix Applied**: After saving config in `update_server_config()`, `add_channel_to_server()`, and `remove_channel_from_server()` endpoints, the bot instance's `_config` is now replaced with a fresh `Config()` instance that reloads from disk.
- **Files Modified**: `src/discord_api.py` → `update_server_config()`, `add_channel_to_server()`, `remove_channel_from_server()`

### 🆕 BUG-006: Auto-Discover Returns Wrong Server ID (JavaScript Integer Precision Loss - Solved - 2026-05-14)
- **Status**: ✅ Solved
- **Severity**: Critical
- **Description**: The "Load Servers from Discord" feature returned server IDs with corrupted last digits (e.g., `1502926835862863944` became `1502926835862864000`). This caused the server config save to use the wrong ID, so channel filters never worked.
- **Root Cause**: Discord snowflake IDs are 19 digits, exceeding JavaScript's `MAX_SAFE_INTEGER` (16 digits). The `get_guilds_info()` method returned guild IDs as **integers**, which get corrupted when passed through JSON → JavaScript → backend. Channel IDs were already correctly returned as strings.
- **Fix Applied**: Changed `get_guilds_info()` to return `str(guild.id)` instead of `guild.id`, matching how channel IDs are handled in `get_guild_channels()`.
- **Files Modified**: `src/discord_bot/bot_core.py` → `get_guilds_info()` method

### Logger TypeError Fix (Solved - 2026-05-14)
- **Status**: ✅ Solved
- **Description**: Flask app threw `TypeError: Logger.info() got multiple values for argument 'module'` when saving server config from web UI.
- **Root Cause**: `discord_api.py` was calling `logger.info()` with multiple positional string arguments plus a `module` keyword argument, but the custom Logger class only accepts `(message: str, module: str = "")`.
- **Fix Applied**: Changed `logger.info()` call in `update_server_config()` to use a single formatted string: `logger.info(f"[ServerConfig] Server config updated for {server_id}: enabled={enabled}")`
- **Files Modified**: `src/discord_api.py` → `update_server_config()`

---

---

### Discord Token Metrics Push to Web UI (Planned)
- **Status**: ⏳ Planned
- **Description**: When the Discord bot processes messages, push token metrics to the web UI's Tokens tab in real-time
- **User Story**: As a user, I want to see token usage statistics in the web UI when the Discord bot responds to messages

#### Implementation Plan

##### 1. Backend Changes
| File | Changes |
|------|---------|
| `src/discord_bot.py` | - Add `_last_token_usage` dict to track token metrics per channel<br>- After LM Studio response, call `chat_stream_with_usage()` or extract usage from `chat_with_tools()` response<br>- Store usage data in `_channel_token_usage[channel_id]` |
| `src/discord_api.py` | - Add `_channel_token_usage` dict<br>- Add `GET /api/tokens/discord/<channel_id>` endpoint<br>- Add `GET /api/tokens/discord/last` endpoint for most recent Discord token usage |
| `src/chat_api.py` | - No changes needed (shared token tracking) |

##### 2. Frontend Changes
| File | Changes |
|------|---------|
| `src/templates/index.html` | - Add "🔗 Sync Discord Token Metrics" toggle switch in settings section |
| `src/static/styles.css` | - Add toggle switch styling for Discord sync toggle |
| `src/static/script.js` | - Add `state.syncDiscordTokens` boolean<br>- Add toggle UI element and handler<br>- Add `pollDiscordTokenMetrics()` polling function (every 5s when enabled)<br>- Add `updateDiscordTokenMetrics(usage)` function<br>- Modify `switchTab('tokens')` to refresh Discord tokens when enabled |

##### 3. Settings UI Addition
```
┌──────────────────────────────────────────────────┐
│ 🔗 Sync Discord Token Metrics: [ON]  Loading... │
└──────────────────────────────────────────────────┘
```

##### 4. Data Flow
```
Discord Message → discord_bot.py processes
                    ↓
            LM Studio API (with usage)
                    ↓
            Store _channel_token_usage[channel_id]
                    ↓
            GET /api/tokens/discord/last (poll every 5s)
                    ↓
            Frontend receives usage data
                    ↓
            Update Token Metrics panel (if toggle enabled)
```

##### 5. Token Metrics Panel Display for Discord
When Discord tokens are synced, the Tokens tab shows:
- **Source indicator**: "💬 Discord" vs "💬 Web Chat"
- **Channel info**: Which Discord channel the metrics are from
- **Last updated**: Timestamp of last Discord response
- **Same metrics**: prompt_tokens, completion_tokens, total_tokens, tokens_per_second, total_time

##### 6. Toggle States
| State | Behavior |
|-------|----------|
| OFF (default) | Tokens tab only shows web chat metrics |
| ON | Tokens tab polls for Discord token metrics every 5s |
| Discord active | Shows latest Discord channel metrics |
| Discord idle | Shows "No Discord activity" placeholder |

---

## Context Management System (2026-05-21)

### FEAT-008: Context Management — Channel Search, Session Start Context, Context Compression

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
1. **Channel Search Tool** (foundation — no LM call needed) — First
2. **Session Start Context Initialization** (uses ChannelSearchTool)
3. **Context Compression Tool** (LM-based summarization)
4. **Integration**: update system prompt, test full flow

#### Files Created
| File | Purpose |
|------|---------|
| `src/discord_bot/context_management.md` | Complete design documentation |
| `src/tools/builtins/channel_search.py` | NEW — ChannelSearchTool |
| `src/tools/builtins/context_compressor.py` | NEW — ContextCompressor |

#### Files To Modify
| File | Changes |
|------|---------|
| `bot_core.py` | Session start context injection in `_handle_new_session_message()` |
| `message_handler.py` | Context compression tool handling |
| `config.py` | Add `context_management` config section |
| `app.py` | API endpoints for context config |

---

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
