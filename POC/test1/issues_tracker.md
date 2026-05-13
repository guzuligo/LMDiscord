# Issues Tracker - POC: test1

## How to Use
- Add any issues, errors, or problems encountered during implementation
- Include the status (Open, In Progress, Solved, Won't Fix)
- Document workarounds or solutions

---

### Issue #1: tkinter Not Available in Python 3.13 venv

| Field | Value |
|-------|-------|
| **ID** | ISS-001 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | tkinter module not found when running the application. System has python3-tkinter installed for Python 3.14, but the venv uses Python 3.13 which doesn't have tkinter bundled. |
| **Environment** | Fedora/Nobara Linux, Python 3.13.13, venv |
| **Root Cause** | Python 3.13 on Fedora doesn't include tkinter by default. The system's python3-tkinter package is for Python 3.14. |
| **Solution** | Switched from tkinter desktop GUI to Flask web-based interface. Flask provides the same functionality with broader compatibility. |
| **Workaround** | N/A - Full solution implemented |
| **Lesson** | tkinter availability varies by OS and Python version. Web-based GUI is more portable. |

---

### Issue #2: Corrupted venv Directory

| Field | Value |
|-------|-------|
| **ID** | ISS-002 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | The venv directory was in a corrupted state after previous deletion attempts. The venv/bin/python3 file was missing. |
| **Environment** | Fedora/Nobara Linux |
| **Root Cause** | Partial deletion of venv directory without fully removing all files. |
| **Solution** | Deactivated the venv, removed the directory completely with `rm -rf venv .venv`, then recreated with `python3 -m venv venv`. |
| **Workaround** | N/A - Full solution implemented |

---

### Issue #3: pip Command Not Found (sudo)

| Field | Value |
|-------|-------|
| **ID** | ISS-003 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Severity** | Low |
| **Description** | Initially tried to use `apt-get` which is not available on Fedora. |
| **Environment** | Fedora/Nobara Linux |
| **Root Cause** | Confused Debian/Ubuntu package manager (apt) with Fedora's (dnf). |
| **Solution** | Used `dnf` instead. However, python3-tkinter was already installed via dnf. The real fix was switching to Flask. |
| **Workaround** | N/A - Full solution implemented |

---

## Open Issues

### Issue #5: Werkzeug HTTP 200 Logs Clutter Terminal

| Field | Value |
|-------|-------|
| **ID** | ISS-005 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Severity** | Low |
| **Description** | Flask/Werkzeug logs every HTTP request including successful GET requests to `/api/logs`. |
| **Solution** | Added conditional logging in `get_logs()` and `clear_logs()` endpoints based on `suppress_werkzeug_logging` config. When suppressed, API requests and debug logs are not written to the log buffer. |
| **Code Location** | `POC/test1/src/app.py` → `get_logs()`, `clear_logs()` endpoints |

---

### Issue #16: Queue Not Checked After New Session

| Field | Value |
|-------|-------|
| **ID** | ISS-016 |
| **Date** | 2026-05-12 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | Messages arriving during new session processing were queued but never processed after the response was posted. |
| **Root Cause** | `_handle_new_session_message()` cleared the lock in `finally` block but never called `_process_queued_pending_messages()`. |
| **Fix** | Added `await self._process_queued_pending_messages(channel_id, message)` at end of `_handle_new_session_message()` in `bot_core.py`. |
| **Code Location** | `POC/test1/src/discord_bot/bot_core.py` → `_handle_new_session_message()` |

---

### Issue #17: No Typing Indicator When Processing Queued Messages

| Field | Value |
|-------|-------|
| **ID** | ISS-017 |
| **Date** | 2026-05-12 |
| **Status** | ✅ Solved |
| **Severity** | Low |
| **Description** | When processing queued messages after a response, users didn't see "Bot is typing..." indicator. |
| **Fix** | Added `await self._typing_indicator.show(message.channel)` in `_process_queued_pending_messages()` in `bot_core.py`. |
| **Code Location** | `POC/test1/src/discord_bot/bot_core.py` → `_process_queued_pending_messages()` |

---

### Issue #6: Infinite `show_typing` Tool Calling Loop

| Field | Value |
|-------|-------|
| **ID** | ISS-006 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | LM Studio enters an infinite loop calling the `show_typing` tool repeatedly (Turn 1, Turn 2, Turn 3...) with empty text responses (`content='\n\n'`), eventually causing a Discord websocket connection error (`ClientConnectionResetError: Cannot write to closing transport`). |
| **Log Evidence** | ``` 2026-05-11 20:54:15,968 - 📝 Turn 1: content='\n\n', tool_calls=1 → 🔧 Turn 1: LM Studio called tool: show_typing ... 2026-05-11 20:54:17,356 - ℹ️ LM Studio used tool call, no text response to post ``` |
| **Root Cause** | The `show_typing` tool was sent to LM Studio as part of the tools list. After LM Studio called `show_typing`, the tool result was added to the conversation and the loop continued. LM Studio kept calling `show_typing` again and again without producing a text response, causing an infinite loop. |
| **Code Location** | `POC/test1/src/discord_bot.py` - `SHOW_TYPING_TOOL` definition, `tools` property, `_delayed_handle_message()`, `_delayed_process_active_session()`, `_handle_message()`, `_handle_active_session_message()` |
| **Solution** | 1. **Removed `show_typing` from LM Studio tools** - No longer sent to the model for tool calling 2. **Typing indicator now shown deterministically** - After the configurable delay expires (default 5s), `channel.send_typing()` is called before message processing 3. **Made delay configurable** - Added `message_delay` setting (1-30 seconds) in config, API endpoints (`/api/settings/delay`), and UI input field 4. **Removed tool handling code** - Removed `show_typing` case from tool processing in both `_handle_message()` and `_handle_active_session_message()` 5. **Updated system prompt** - Removed `show_typing` references from the system prompt |
| **Files Modified** | `POC/test1/src/discord_bot.py`, `POC/test1/src/config.py`, `POC/test1/src/app.py`, `POC/test1/src/templates/index.html` |


---

## Won't Fix

_No issues marked as won't fix._

---

## In Progress

### 🆕 Server Configuration System (Server/Channel Access Control)

| Field | Value |
|-------|-------|
| **ID** | FEAT-001 |
| **Date** | 2026-05-13 |
| **Status** | 🔄 In Progress |
| **Severity** | Medium |
| **Description** | Implement per-server enable/disable and per-channel allow/deny lists so the bot can be selectively enabled across multiple Discord servers. Also includes a "Server Config" tab in the web UI for managing these settings. |
| **Features** | 1. Per-server enable/disable toggle in `config.json` 2. Per-server channel allow/deny lists 3. Web UI "Server Config" tab 4. API endpoints for server management 5. Bot_core checks to skip messages from disabled servers/channels |
| **Files to Modify** | `src/config.py`, `src/discord_bot/bot_core.py`, `src/discord_api.py`, `src/templates/index.html`, `src/static/script.js`, `src/static/styles.css`, `app_Plan.md` |

---

### 🆕 Discord Channel Search Tool (Planned)

| Field | Value |
|-------|-------|
| **ID** | FEAT-002 |
| **Date** | 2026-05-13 |
| **Status** | ⏳ Planned |
| **Description** | A tool that allows LM Studio to search through Discord channel messages for context. Actions: search, list_channels, get_channel_info, search_by_user. |

---

### 🆕 Discord Token Metrics Push to Web UI (Planned)

| Field | Value |
|-------|-------|
| **ID** | FEAT-003 |
| **Date** | 2026-05-13 |
| **Status** | ⏳ Planned |
| **Description** | Push token metrics from Discord bot to web UI's Tokens tab in real-time. Toggle-based sync with polling every 5s. |

---

### 🆕 Built-in Tools Integration (Planned)

| Field | Value |
|-------|-------|
| **ID** | FEAT-004 |
| **Date** | 2026-05-13 |
| **Status** | ⏳ Planned |
| **Description** | Full integration of math_calc, comfyui_generate, and memory_tool as LM Studio-callable tools. |

---

### 🆕 Memory Integration with memorylite (Planned)

| Field | Value |
|-------|-------|
| **ID** | FEAT-005 |
| **Date** | 2026-05-13 |
| **Status** | ⏳ Planned |
| **Description** | Post-session memory creation using memorylite SQLite-based memory system. |

---

### Issue #7: Typing Indicator Not Showing (show_typing Function Never Called)

| Field | Value |
|-------|-------|
| **ID** | ISS-007 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | The `_show_typing_indicator` function is defined but never called. The typing indicator ("Bot is typing...") should appear when a message is sent to LM Studio, but users don't see any typing indicator. |
| **Root Cause** | Multiple issues: (1) `_show_typing_indicator` was defined but never called - (2) LM Studio API calls used synchronous `requests.post()` which blocks the async event loop, preventing typing indicator from being processed - (3) Typing indicator was only shown after delay, not immediately when message received - (4) `channel.send_typing()` method was deprecated in discord.py 2.x |
| **Solution** | 1. **Called `_show_typing_indicator()` immediately** in `on_message` handler when mention/reply is received (no delay for first messages) 2. **Removed delay for new session messages** - first messages now process immediately, delay only applies to active session messages (to allow follow-up batching) 3. **Run LM Studio calls in ThreadPoolExecutor** - synchronous `requests.post()` calls now run in background thread (`asyncio.get_event_loop().run_in_executor()`) so the async event loop is not blocked and typing indicator can be processed by Discord's WebSocket 4. **Fixed discord.py 2.x API** - replaced deprecated `channel.send_typing()` with `async with channel.typing():` context manager 5. Added additional typing indicator calls on retry turns (turn > 0) to keep indicator visible during multi-turn tool calling |
| **Files Modified** | `POC/test1/src/discord_bot.py` |

---

### Issue #8: Duplicate Goodbye Message on Session End

| Field | Value |
|-------|-------|
| **ID** | ISS-008 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | When LM Studio calls `end_session`, the goodbye message is posted twice to Discord. |
| **Root Cause** | Multi-turn tool calling flow: Turn 1 returns empty content with `end_session` tool call → tool result added → Turn 2 returns farewell text → Both the Turn 2 `response_text` AND the `farewell_message` from tool call arguments are posted to Discord. |
| **Solution** | When `end_session` tool is detected in `_handle_active_session_message()`, set `response_text = None` so the "Post response to Discord" section won't post it. Only the farewell message from tool call arguments will be posted via the session end handler. |
| **Code Location** | `POC/test1/src/discord_bot.py` → `_handle_active_session_message()` |

---

### Issue #9: Messages Lost During Active Session Processing

| Field | Value |
|-------|-------|
| **ID** | ISS-009 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | When multiple messages are sent quickly during an active session, only the first message is processed. Subsequent messages arriving while the bot is processing are completely dropped/skipped because the `_processing_lock` prevents them from being handled. |
| **Log Evidence** | ``` 22:38:06,371 - 💬 [user] in active session: What is your name?... 22:38:06,626 - ⏳ Queued message from user (queue size: 1) 22:38:10,464 - ⏳ Queued message from user (queue size: 2) 22:38:18,704 - ⏳ Queued message from user (queue size: 3) ``` Messages were queued but only processed AFTER the bot posted its reply to the first message. |
| **Root Cause** | The `_processing_lock` was acquired when processing started, and any new messages arriving were silently dropped with `return` at line 165-166 in `on_message` handler. |
| **Solution** | 1. Added `_pending_messages` dict to queue messages instead of dropping them 2. Modified `on_message` to queue messages when lock is active 3. Created `_handle_active_session_message_batch()` that combines main + queued messages 4. Added `_process_queued_pending_messages()` for post-response chain processing 5. Bot now processes queued messages immediately after posting each response |
| **Code Location** | `POC/test1/src/discord_bot.py` → `__init__()`, `on_message()`, `_delayed_process_active_session()`, `_handle_active_session_message_batch()`, `_process_queued_pending_messages()` |

---

### Issue #10: Security - Error Tracebacks Exposed to Discord Users

| Field | Value |
|-------|-------|
| **ID** | ISS-010 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Severity** | Critical |
| **Description** | When LM Studio returns an error (e.g., 400 Bad Request for empty messages), the internal error details including stack traces, URLs, and error messages were being posted to Discord, exposing internal system information. |
| **Log Evidence** | ``` 2026-05-11 22:48:29,191 - ERROR - Error getting LM Studio response: 400 Client Error: Bad Request for url: http://localhost:1234/v1/chat/completions Traceback (most recent call last): ... ``` |
| **Root Cause** | Error handlers in `_handle_message()` and `_handle_active_session_message_batch()` were using `str(e)[:150]` which exposed internal error details including URLs and traceback information. |
| **Solution** | Replaced all error responses that were sent to Discord with generic sanitized messages: "⚠️ Sorry, I encountered an error processing your message." Error tracebacks are still logged server-side with full details via `logger.error(..., exc_info=True)`. |
| **Code Location** | `POC/test1/src/discord_bot.py` → `_handle_message()`, `_handle_active_session_message_batch()` |

---

### Issue #11: Duplicate Message Handlers Running Simultaneously

| Field | Value |
|-------|-------|
| **ID** | ISS-011 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | After implementing message queuing, two handlers were running simultaneously for the same channel. When the bot posted a response and called `_process_queued_pending_messages()`, the lock was already released by the `finally` block, allowing a new message to slip through and start its own handler. |
| **Log Evidence** | ``` 22:50:42,621 - ⏰ Delay complete, processing active session message now 22:50:42,621 - 💬 [user] in active session: Are you ok?... 22:50:45,188 - ⏰ Delay complete, processing active session message now 22:50:45,188 - 💬 [user] in active session: I love you... ``` Two handlers running in parallel. |
| **Root Cause** | The `_process_queued_pending_messages()` was called from inside the `try` block of `_handle_active_session_message_batch`, and the `finally` block released the lock before the queued processing completed. |
| **Solution** | 1. Lock is cleared BEFORE calling `_process_queued_pending_messages()` 2. `_process_queued_pending_messages()` re-acquires the lock before calling batch handler 3. Added try/except wrapper in batch handler with proper lock cleanup 4. Empty messages now skipped with early return that properly manages lock |
| **Code Location** | `POC/test1/src/discord_bot.py` → `_handle_active_session_message_batch()`, `_process_queued_pending_messages()` |

---

### Issue #12: Empty Messages Cause LM Studio API Errors

| Field | Value |
|-------|-------|
| **ID** | ISS-012 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Severity** | Low |
| **Description** | Empty or whitespace-only messages sent to the bot cause LM Studio API to return 400 Bad Request errors. These errors were initially exposing internal details to users (see ISS-010). |
| **Root Cause** | Empty messages have no meaningful content to send to LM Studio, but the bot was still attempting to process them. |
| **Solution** | Added early check in `_handle_active_session_message_batch()` to skip empty/whitespace-only messages with logging: "⏭️ Skipping empty message for channel {channel_id}". |
| **Code Location** | `POC/test1/src/discord_bot.py` → `_handle_active_session_message_batch()` |

---

### Issue #8: Duplicate Goodbye Message on Session End

| Field | Value |
|-------|-------|
| **ID** | ISS-008 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | When LM Studio calls `end_session`, the goodbye message is posted twice to Discord. |
| **Root Cause** | Multi-turn tool calling flow: Turn 1 returns empty content with `end_session` tool call → tool result added → Turn 2 returns farewell text → Both the Turn 2 `response_text` AND the `farewell_message` from tool call arguments are posted to Discord. |
| **Solution** | When `end_session` tool is detected in `_handle_active_session_message()`, set `response_text = None` so the "Post response to Discord" section won't post it. Only the farewell message from tool call arguments will be posted via the session end handler. |
| **Code Location** | `POC/test1/src/discord_bot.py` → `_handle_active_session_message()` |

---

## Open Issues

### BUG-003: Bot Cannot Identify Discord Users (No User Identity in Context)

| Field | Value |
|-------|-------|
| **ID** | BUG-003 |
| **Date** | 2026-05-13 |
| **Status** | 🔄 In Progress |
| **Severity** | High |
| **Description** | The bot has no knowledge of who is talking to it. When asked "What is my name?" the bot responds "I don't know your name." This is because Discord user identity information (username, display name, user ID) is never communicated to the LM Studio. |
| **Log Evidence** | ```2026-05-13 12:33:28,469 - Turn 1: content='What is your name?...``` → ```2026-05-13 12:33:30,430 - Turn 1: content='\n\nMy name is BotGuzu.'``` (bot confuses its own name with user's name) |
| **Root Cause** | 1. `author_name` and `author_display` are extracted in `bot_core.py` but never passed to `handle_new_session()` in `message_handler.py` 2. The system prompt does not include any user identity information 3. The first user message in conversation history has no author attribution |
| **Fix Applied** | 1. Added `author_display` and `user_id` parameters to `handle_new_session()` method signature 2. Added identity context to system prompt that explains Discord identifiers (username, display name, user ID) and instructs LM Studio to remember the user 3. Added author attribution prefix to first user message (e.g., `[From user 'guzu']: hello`) 4. Updated `_handle_new_session_message()` in `bot_core.py` to extract and pass `author_display` and `user_id` |
| **Files Modified** | `src/discord_bot/message_handler.py` (handle_new_session method), `src/discord_bot/bot_core.py` (_handle_new_session_message method) |

---

### BUG-001: Allowed Hostnames Not Passed from Config to SafeImageDownloader

| Field | Value |
|-------|-------|
| **ID** | BUG-001 |
| **Date** | 2026-05-12 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Date Solved** | 2026-05-13 |
| **Symptom** | `Safe image downloader initialized with allowed hostnames: []` - empty list, all image downloads blocked |
| **Log Evidence** | ```2026-05-12 12:55:10,052 - src.discord_bot.message_handler - INFO - Safe image downloader initialized with allowed hostnames: []```<br>```WARNING - BLOCKED: hostname 'cdn.discordapp.com' is NOT in allowed list: []``` |
| **Root Cause** | The Config object was created in `app.py` but never assigned to `LMStudioClient`. `bot_core.py` tried to access `lm_studio_client.config.allowed_image_hostnames` but `LMStudioClient` had no `config` attribute, so `hasattr()` returned False and `allowed_hostnames` defaulted to `[]`. |
| **Fix** | 1. Added `_config` attribute and `config` property (getter/setter) to `LMStudioClient` in `src/lm_studio_client.py` 2. Assigned `client.config = config` in `src/app.py` after creating the client |
| **Files Modified** | `src/lm_studio_client.py` (added config property), `src/app.py` (added config assignment) |
| **Impact** | Image description tool can now download images from allowed hosts (cdn.discordapp.com, media.discordapp.net) |

---

### BUG-002: Image Describe Breaks Conversation Flow & Causes 400 Errors

| Field | Value |
|-------|-------|
| **ID** | BUG-002 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Severity** | Critical |
| **Date Solved** | 2026-05-13 |
| **Symptom** | Four related issues with image handling in Discord bot |

#### Sub-Issue 2a: LM Studio Acts as Image Description Tool Instead of Conversational Assistant
- **Description**: When user sends an image with a message like "Check this out...", LM Studio calls `image_describe` and responds with just the image description, ignoring the user's actual intent/question.
- **Root Cause**: System prompt says "Call this when the user wants an image described" — LM Studio interprets ANY image attachment as a description request.
- **Fix Applied**: Updated system prompt in `handle_new_session()` to guide LM Studio: "Call this ONLY when the user explicitly asks for an image to be described. If the user sends an image but does NOT explicitly ask for it to be described, respond naturally about the image in text."
- **Files Modified**: `src/discord_bot/message_handler.py` → `handle_new_session()` system prompt (lines 269-277)

#### Sub-Issue 2b: Blocked Hostname Error Gives Poor User Experience
- **Description**: When image URL is from a non-allowed hostname, LM Studio gets `"Security: URL blocked: Hostname 'x' not in allowed hostnames"` and responds with a robotic error instead of a helpful message.
- **Root Cause**: The `ValueError` from `SafeImageDownloader` is caught and sent as tool result text. LM Studio doesn't have enough context to give a user-friendly response.
- **Fix Applied**: Replaced raw security error with user-friendly message: "The image URL could not be processed. This may be due to the image being hosted on an unsupported domain, or the URL may not be publicly accessible. Please try using an image from Discord's CDN instead."
- **Files Modified**: `src/discord_bot/message_handler.py` → ValueError handlers in `_process_message()` (line ~569) and `_process_active_session()` (line ~812)

#### Sub-Issue 2c: Conversation Context Overflow (400 Error)
- **Description**: After multiple image interactions, conversation history grows to 6917 tokens. LM Studio returns 400 Bad Request, breaking the conversation.
- **Log Evidence**: ```Token usage stored: 6917 tokens (1417p + 5500c) @ 0 tok/s``` followed by ```Error in active session: 400 Client Error: Bad Request```
- **Root Cause**: Image base64 data is included in the conversation history sent to LM Studio on every turn. Current truncation keeps 20 messages but image data makes them too large.
- **Fix Applied (Fix E)**: Isolated context window for image describe:
  1. When `image_describe` tool is called, download and resize the image
  2. Create an ISOLATED mini-context with ONLY the image + "describe this image" prompt (no conversation history)
  3. Get the description text from LM Studio using the mini-context
  4. Replace the tool call in the main conversation with the description as plain text: "The image has been described. Here's what was in the image: [description]. Please continue the conversation naturally."
  5. This prevents base64 image data from polluting the main conversation history
- **Files Modified**: `src/discord_bot/message_handler.py` → image_describe handling in `_process_message()` (lines ~502-580) and `_process_active_session()` (lines ~752-815)

#### Sub-Issue 2d: discord.py `Attachment.is_image()` Compatibility Warning
- **Description**: Log shows `WARNING - Error checking if attachment is image: 'Attachment' object has no attribute 'is_image'`
- **Root Cause**: `is_image()` is a property in discord.py 2.x, not a method. Calling it as `attachment.is_image()` raises AttributeError.
- **Fix Applied**: Added `hasattr()` guard to check for `is_image` attribute before accessing it. If it's callable, call it; if it's a property, use it directly. Falls back to extension-based detection if the attribute doesn't exist.
- **Files Modified**: `src/discord_bot/bot_core.py` → `_extract_image_attachments()` method (lines 181-193)

---

---

## Recent Additions (5/12/2026)

### Debug Panel Implementation
- **Status**: ✅ Solved
- **Description**: Created separate debug page at `/debug` with connection status, session management, token metrics, settings override, diagnostics, and log viewer
- **New Files**: `src/templates/debug.html`, `src/static/debug_styles.css`, `src/static/debug_script.js`
- **Modified**: `src/templates/index.html`, `src/static/script.js`, `src/app.py`
- **Fixes**: Added missing LM Studio host/port inputs, fixed log display initialization

### Temperature Configurable from Web UI
- **Status**: ✅ Solved
- **Description**: Added temperature input field, API endpoints, and dynamic application to Discord bot

### Max Response Length Configurable from Web UI
- **Status**: ✅ Solved
- **Description**: Added max_response_length input field, API endpoints, and config setter

### Dynamic Settings Application to Discord Bot
- **Status**: ✅ Solved
- **Description**: Settings changes (temperature, max_tokens, message_delay, system_prompt) now apply immediately to running Discord bot without restart

---

# Debug Page Fixes (5/13/2026)

### DEBUG-001: Debug Page Not Showing Logs
- **Problem**: Debug page at `/debug` was not displaying any log entries despite logs being generated server-side
- **Root Cause**: The `updateDebugLogDisplay` function in `lib/logs.js` was not being called properly from the debug page's own `fetchDebugLogs()` function in `debug_script.js`. The shared `fetchLogs()` function was calling it, but the debug page's direct call was missing and had no error handling.
- **Fix Applied**: 
  1. Rewrote `fetchDebugLogs()` in `debug_script.js` to directly call the API and `updateDebugLogDisplay()`
  2. Added comprehensive console logging for debugging
  3. Added `testLogDisplay()` function to verify log pipeline on page load
  4. Fixed `updateDebugLogDisplay()` in `lib/logs.js` with better error handling and console output

### DEBUG-002: JavaScript Syntax Error on Token Refresh
- **Problem**: `Uncaught SyntaxError: invalid assignment left-hand side` on line 355 of `debug_script.js`
- **Root Cause**: Optional chaining `?.` was used on the left-hand side of an assignment: `document.getElementById('...')?.textContent = value` - this is invalid JavaScript because `?.` can only be used for reading, not writing
- **Fix Applied**: Changed to explicit element checks:
  ```javascript
  const el = document.getElementById('debugPromptTokens');
  if (el) el.textContent = data.value;
  ```

### DEBUG-003: Discord Status Always Shows "Not Connected"
- **Problem**: Discord bot status always shows `discord_connected: false` in `/api/status` response even after clicking "Connect" on the main page. The bot IS connecting to Discord (confirmed by user), but the status global variable is never being set to `True`.
- **Root Cause**: The `on_ready()` callback in `bot_core.py` uses `asyncio.create_task(self._on_status_change_callback(...))` to notify the parent module of the connection status. However, this callback mechanism fails silently because:
  1. The callback is an async function defined in `_discord_bot_thread_func()` in a **different thread**
  2. `asyncio.create_task()` swallows exceptions if no custom exception handler is set on the task
  3. The event loop running the callback is created in the bot thread via `get_or_create_event_loop()`, but the callback's `global discord_connected` update may fail because the task never actually executes
  4. The `on_ready()` event fires in the discord.py internal event loop, NOT in the bot thread's event loop
- **Fix Applied**: Added direct global variable update in `on_ready()` using `sys.modules.get('src.discord_api')` to access and update the `discord_connected` and `discord_status_message` globals directly. The callback is kept as a fallback.
- **Files Modified**: `POC/test1/src/discord_bot/bot_core.py` → `_register_events()` → `on_ready()`
- **Lesson**: Cross-thread async callbacks are unreliable for updating module-level globals. Always update shared state directly in event handlers, and use callbacks only for notification purposes.
- **Status**: ✅ Solved (requires Flask app restart to test)

---

## Open Issues

### DISCORD-003: UnboundLocalError in get_sessions (sessions variable not initialized)

| Field | Value |
|-------|-------|
| **ID** | DISCORD-003 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | `get_sessions()` endpoint throws `UnboundLocalError: cannot access local variable 'sessions' where it is not associated with a value` when `get_session_info()` returns a dict with `channels` being a list instead of dict. |
| **Root Cause** | The `sessions` list was only defined inside the `if isinstance(channels, dict)` block. When `channels` was a list, `sessions` was never initialized before the `return jsonify(...)` statement. |
| **Fix** | Moved `sessions = []` to the top of the try block. Added `elif isinstance(channels, list)` branch to handle list-type channels. |
| **Files Modified** | `src/app.py` → `get_sessions()` endpoint |

---

### DISCORD-002: UI Shows "Not Connected" Despite Bot Thread Running (Stale Import)

| Field | Value |
|-------|-------|
| **ID** | DISCORD-002 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Severity** | Critical |
| **Description** | After the Discord bot thread starts successfully (confirmed by logs), the UI still shows "Not connected". The `/api/status` endpoint returns `discord_connected: false` even though the bot thread is running. |
| **Root Cause** | Python's `from module import variable` creates a **local reference** to the value at import time, not a live link to the module attribute. In `app.py`, the code used: `from src.discord_api import discord_connected, ...`. When `bot_core.py` updated `discord_api.discord_connected = True` directly, this only changed the module attribute, not `app.py`'s local `discord_connected` variable. The `/api/status` endpoint read from the stale local variable. |
| **Fix** | Changed `app.py` to import the module (`from src import discord_api`) instead of individual variables. Created helper functions `_get_discord_connected()`, `_get_discord_bot_instance()`, `_get_discord_status_message()` that always read from the module attribute dynamically. Updated all endpoints to use these helpers. |
| **Files Modified** | `src/app.py` → changed import style, added getter functions, updated all route handlers |

---

### DISCORD-001: Discord Bot Stuck After Flask App Restart (Stale State)

| Field | Value |
|-------|-------|
| **ID** | DISCORD-001 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | When the Flask app is restarted (via debug reloader), the Discord bot fails to connect/disconnect properly. Error message: "❌ Discord connection failed: Bot is already connected to Discord". This happens because the Flask debug reloader restarts the Python process but module-level globals in `discord_api.py` get reset while the old Discord bot thread from the previous process may still be running. |
| **Root Cause** | 1. Flask's debug reloader spawns a new process, resetting module globals (`discord_connected = False`, `discord_bot_thread = None`) 2. The old Discord bot thread from the previous process may still be running 3. When `on_ready()` fires on the old thread, it updates `discord_connected = True` via `sys.modules` 4. The new Flask app sees `discord_connected = True` even though its own `discord_bot_thread` is `None` 5. `/api/discord/connect` checks `if discord_connected:` and rejects with "Bot is already connected" |
| **Solution** | 1. Added `force_reset_discord_state()` function in `discord_api.py` to reset all Discord-related globals 2. Called `force_reset_discord_state()` at Flask app startup to ensure clean state 3. Improved `start_discord_bot_thread()` to detect and clean up stale state before starting 4. Improved `stop_discord_bot()` to handle edge cases (None thread, None stop event, bot instance) 5. Added `/api/discord/force_reset` endpoint for manual reset from debug page 6. Added "🔥 Force Reset Discord" button on the debug page |
| **Files Modified** | `src/discord_api.py` (added `force_reset_discord_state()`, improved `start_discord_bot_thread()`, improved `stop_discord_bot()`, added `/api/discord/force_reset` endpoint), `src/app.py` (added import and startup call), `src/templates/debug.html` (added force reset button), `src/static/debug_script.js` (added `forceResetDiscord()` function) |
| **Testing** | Restart the Flask app and try to connect Discord bot. It should now connect successfully without the "Bot is already connected" error. The "Force Reset Discord" button can be used as a manual recovery option. |

---

### CSS-001: CSS Files Too Large - Over-Engineered Styling (CSS-001)

| Field | Value |
|-------|-------|
| **ID** | CSS-001 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Severity** | Low (Developer Experience) |
| **Description** | CSS files were massive: `styles.css` had 1,221 lines and `debug_styles.css` had 437 lines (1,658 total). The styling was over-engineered for an internal admin tool with excessive animations, hover effects, custom scrollbars, transitions, and decorative elements that waste AI tokens during development. |
| **Solution** | Replaced both files with a single `minimal.css` (~238 lines) containing only essential layout and styling. Removed: custom scrollbars, all @keyframes animations, hover effects, transitions, collapsible panel animations, resize handles, decorative pseudo-elements, responsive design rules. The page looks like a functional admin panel (terminal-style) instead of a polished website. |
| **Files Changed** | Removed: `src/static/styles.css`, `src/static/debug_styles.css`. Added: `src/static/minimal.css`. Updated: `src/templates/index.html`, `src/templates/debug.html`. |
| **Future Work** | Aesthetics can be improved later once functionality is stable. See `plan.md` for details. |

---

### Issue #18: Active Session Context Loss - Bot Forgets Previous Messages

| Field | Value |
|-------|-------|
| **ID** | ISS-018 |
| **Date** | 2026-05-12 |
| **Status** | ✅ Solved & Verified |
| **Severity** | Critical |
| **Description** | During active sessions, the bot loses conversation context after each message. Every message is treated as "turn 1" and the bot cannot remember previous questions/answers in the same conversation. For example, when asked "What did I ask you?" the bot responds "You said hi." instead of remembering the math questions. |
| **Log Evidence** | ``` 2026-05-12 10:33:11,483 - Active session turn 1 for channel <channel_id> ... 2026-05-12 10:33:28,755 - Active session turn 1 for channel <channel_id> ... 2026-05-12 10:35:15,240 - Active session turn 1 for channel <channel_id> ``` Every message shows "turn 1" because history is never persisted. |
| **Root Cause** | In `message_handler.py` → `_process_active_session()` at line 521, the code used `conversation_history = {channel_id: history}` which creates a **new local dictionary reference** and assigns it to the local parameter variable. This does NOT modify the original `self._conversation_history` dictionary in `bot_core.py`. Additionally, `_process_active_session` did not receive `conversation_history` as a parameter. |
| **Fix** | 1. Changed `conversation_history = {channel_id: history}` to `conversation_history[channel_id] = history` at line 521. 2. Added `conversation_history` parameter to `_process_active_session()` method signature. 3. Updated `handle_active_session_batch()` to pass `conversation_history` to `_process_active_session()`. |
| **Code Location** | `POC/test1/src/discord_bot/message_handler.py` → `_process_active_session()` method, `handle_active_session_batch()` method |
| **Verification** | Tested 5/12/2026: Bot now correctly maintains context within sessions. When asked to summarize questions, it returns all previous questions in a table. Session clears properly after `end_session` and new sessions start fresh. |

---

## Solved (Recent)

### Issue #14: discord_bot.py Too Large for Maintenance (ISS-014) - 2026-05-12
- **Problem**: `discord_bot.py` was 1077 lines, making maintenance and debugging difficult
- **Solution**: Refactored into 6 focused modules under `src/discord_bot/` package
- **New Files**:
  - `src/discord_bot/bot_core.py` - Main DiscordBot class, event registration, lifecycle
  - `src/discord_bot/message_handler.py` - Message processing, LM Studio interaction, tool calling
  - `src/discord_bot/session_manager.py` - Session lifecycle, timeout cleanup, state queries
  - `src/discord_bot/token_tracker.py` - Token usage tracking per channel for web UI sync
  - `src/discord_bot/typing_indicator.py` - Discord typing indicator using async typing() context manager
  - `src/discord_bot/delay_processor.py` - Delayed message processing for follow-up batching
- **Modified**: `src/discord_bot.py` - Now a backward-compat wrapper (~18 lines)
- **Note**: Package renamed from `discord` to `discord_bot` to avoid naming conflict with discord.py library
- **Benefits**: Single responsibility, easier testing, easier debugging, better navigation

### Issue #13: Discord Disconnect Button Not Working (ISS-013) - 2026-05-11
- **Problem**: Clicking "Disconnect" button did not disconnect the Discord bot
- **Root Cause**: `_bot_stop_event` was created but never used; `stop_discord_bot()` had race condition accessing `discord_bot_instance`
- **Fix**: Added `_wait_for_stop_event()` async poller, modified `run_with_stop()` to use `asyncio.wait()` with `FIRST_COMPLETED`, rewrote `stop_discord_bot()` to properly signal thread shutdown
- **Syntax Error Fix**: `_run_bot_safely()` had `global` declaration after assignments causing SyntaxError; fixed by returning status tuple instead of using global variables
- **Code Location**: `POC/test1/src/app.py` → `_discord_bot_thread_func()`, `_wait_for_stop_event()`, `_run_bot_safely()`, `stop_discord_bot()`

---

### Issue #6: Infinite `show_typing` Tool Calling Loop (ISS-006) - 2026-05-11
- **Problem**: LM Studio entered infinite loop calling `show_typing` tool
- **Fix**: Removed `show_typing` from LM Studio tools, made typing indicator deterministic after configurable delay
- **New Feature**: Configurable message delay (1-30 seconds) via web UI
