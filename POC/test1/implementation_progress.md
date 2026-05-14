
# Implementation Progress - POC: test1

## Overview
Discord Bot + LM Studio Integration - First POC implementation

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
18. ⏳ Add tools system (math, image description)
19. ⏳ Add memory integration
20. ⏳ Add channel configuration window

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

### 🆕 BUG-004: Channel Filter Not Working Due to Server ID Mismatch (Investigating - 2026-05-14)
- **Status**: 🔄 Investigating
- **Description**: The bot processes messages from all channels despite denied_channels being configured in config.json.
- **Root Cause Found**: Server ID mismatch between config.json and actual Discord guild ID.
  - Config saved for: `1502926835862864000`
  - Actual Discord guild: `1502926835862863944`
  - The bot looks up config using actual guild ID, finds no match, uses default (all channels allowed)
- **Debug Logging Added**:
  1. **bot_core.py** - Added detailed channel filter debug logging (guild_id, channel_id, allowed_channels, denied_channels, is_channel_allowed result)
  2. **discord_api.py** - Added config save/verify logging and channel API request logging
- **Fix Required**: User must update config.json server ID to match actual Discord guild ID, or use the "Load Servers from Discord" feature to auto-discover the correct ID.

---

### 🆕 Discord Channel Search Tool (Planned)
- **Status**: ⏳ Planned
- **Description**: A tool that allows LM Studio to search through Discord channel messages for context
- **User Story**: As the bot, I need to search Discord message history to answer questions about previous conversations

#### Implementation Plan

##### Tool Definition (OpenAI-compatible format)
```json
{
  "type": "function",
  "function": {
    "name": "search_discord_channels",
    "description": "Search through Discord channel messages for keywords or list available channels. Use when the user asks about previous conversations, who said something, or when you need context from Discord message history.",
    "parameters": {
      "type": "object",
      "properties": {
        "action": {
          "type": "string",
          "enum": ["search", "list_channels", "get_channel_info", "search_by_user"],
          "description": "The search action to perform"
        },
        "query": {
          "type": "string",
          "description": "Search keyword/query (used with 'search' action)"
        },
        "channel_id": {
          "type": "string",
          "description": "Discord channel ID (used with 'get_channel_info' action)"
        },
        "user_id": {
          "type": "string",
          "description": "Discord user ID (used with 'search_by_user' action)"
        },
        "limit": {
          "type": "integer",
          "description": "Maximum number of results to return (default: 10)",
          "default": 10
        }
      },
      "required": ["action"]
    }
  }
}
```

##### Configuration Options
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `search_scope` | string | "active_channel" | Where to search: "active_channel", "all_channels", "specified_channels" |
| `specified_channel_ids` | array | [] | List of channel IDs to search (used when scope = "specified_channels") |
| `include_source_info` | boolean | true | Include source metadata (channel name, message ID, author, timestamp) in results |
| `enable_tool` | boolean | false | Master toggle to enable/disable this tool |

##### Source Metadata (included when `include_source_info = true`)
Each search result will include:
- `channel_id`: Discord channel ID
- `channel_name`: Human-readable channel name
- `message_id`: Discord message ID
- `author`: Message author display name
- `author_id`: Discord user ID
- `timestamp`: ISO 8601 timestamp
- `is_in_channel`: Whether this channel was explicitly targeted

##### File Structure
| File | Purpose |
|------|---------|
| `src/tools/builtins/discord_search.py` | New tool implementation |
| `src/tools/builtins/__init__.py` | Register the new tool |
| `src/config.py` | Add search configuration options |
| `src/discord_bot/message_handler.py` | Wire tool into tools list |
| `src/templates/index.html` | Add settings UI for search config |
| `src/static/script.js` | Add UI handlers for search settings |

##### Data Flow
```
LM Studio calls search_discord_channels(action="search", query="hello")
        ↓
message_handler.py receives tool call
        ↓
discord_search.py executes search based on config scope
        ↓
Results with source metadata returned to LM Studio
        ↓
LM Studio decides how to use the data in response
```

##### Tool Execution Examples

**Example 1: Search current channel**
```
Input: {"action": "search", "query": "hello", "limit": 5}
Output: [
  {"message": "Hello bot!", "author": "User1", "timestamp": "...", "source": {"channel": "general", ...}},
  ...
]
```

**Example 2: List all accessible channels**
```
Input: {"action": "list_channels"}
Output: [
  {"channel_id": "123...", "channel_name": "general", "message_count": 150},
  {"channel_id": "456...", "channel_name": "random", "message_count": 89}
]
```

**Example 3: Get specific channel info**
```
Input: {"action": "get_channel_info", "channel_id": "123..."}
Output: {
  "channel_name": "general",
  "last_messages": [...],
  "total_messages": 150
}
```

##### Security Considerations
- Tool is disabled by default (`enable_tool: false`)
- Admin-only configuration (only accessible via web UI settings)
- Source metadata helps LM Studio understand context and trust level of results
- Search scope limits prevent accidental access to restricted channels

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
