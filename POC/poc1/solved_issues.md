# Solved Issues - POC: test1

> This file contains the full details of all resolved/solved issues. For current open and planned issues, see [issues_tracker.md](issues_tracker.md).

---

## Table of Contents

- [Infrastructure & Setup](#infrastructure--setup)
- [Discord Bot Core](#discord-bot-core)
- [Discord UI & API](#discord-ui--api)
- [LM Studio & Model Integration](#lm-studio--model-integration)
- [Image Processing](#image-processing)
- [Message Processing & Tool Calling](#message-processing--tool-calling)
- [Memory System](#memory-system)
- [Tools & Built-ins](#tools--built-ins)
- [Configuration & Settings](#configuration--settings)
- [Refactoring & Code Quality](#refactoring--code-quality)
- [Debugging & Development Tools](#debugging--development-tools)
- [Performance & Optimization](#performance--optimization)
- [Cancellation System](#cancellation-system)
- [Error Handling & User Feedback](#error-handling--user-feedback)

---

## Error Handling & User Feedback

### BUG-LM-001: LM Studio Error Handler Crashes on Non-Standard Error Response Structure
| Field | Value |
|-------|-------|
| **ID** | BUG-LM-001 |
| **Date** | 2026-06-05 |
| **Status** | ✅ Solved |
| **Severity** | Critical |
| **Description** | When LM Studio returns an HTTP error response (e.g., 400 Bad Request), the error handling code in `lm_studio_client.py` assumed the JSON response always has a `{"error": {"message": "..."}}` structure. Sometimes the `error` field is a string directly (e.g., `"error": "Failed to load model"`) or missing entirely. This caused an `AttributeError` when calling `.get("message", ...)` on a string, crashing the exception handler itself. |
| **Log Evidence** | ```AttributeError: 'str' object has no attribute 'get'``` at line 285 in `lm_studio_client.py` where `error_data.get("error", {}).get("message", str(e))` was called. |
| **Root Cause** | The error extraction code did not handle the case where `error_data.get("error")` returns a string instead of a dict. Python's `.get()` method doesn't exist on strings, causing the exception handler to crash. |
| **Solution** | Added safe error message extraction that handles three possible formats: (1) `error` is a dict → extract `error["message"]` or fall back to `json.dumps(error)`. (2) `error` is a string → use it directly. (3) `error` is None/missing → fall back to `json.dumps(error_data)`. Detailed errors are logged via `logger.error()` in `lm_studio_client.py`. User-facing messages are handled by `_format_lm_studio_error_message()` in `message_processor.py` which returns generic messages without leaking internal details. |
| **Files Modified** | `src/lm_studio_client.py` → `chat()` and `chat_with_tools()` methods, lines ~280-295 |
| **User-Facing Result** | No change — users still see the same generic error messages as before. The fix only prevents the bot from crashing when LM Studio returns unexpected error response formats. |

---

### BUG-016: LM Studio Model Loading Error Leaks Internal Details to Users

| Field | Value |
|-------|-------|
| **ID** | BUG-016 |
| **Date** | 2026-06-04 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | When LM Studio fails to load a model (HTTP 400 with "Failed to load model" error), the error message exposed to Discord users leaked internal details including the specific model name (`qwen3.6-35b-a3b`) and error type (`invalid_request_error`). The original error message was: ```⚠️ MODEL NOT CONNECTED — I couldn't load my AI model in LM Studio. Error: Type: invalid_request_error, Failed to load model "qwen3.6-35b-a3b". Error: Failed to load model. Please make sure LM Studio is running and a compatible model is loaded before chatting.``` |
| **Log Evidence** | ```http://localhost:1234 "POST /v1/chat/completions HTTP/1.1" 400 205 "Failed to load model \"qwen3.6-35b-a3b\". Error: Failed to load model."``` |
| **Root Cause** | 1. `_format_lm_studio_error_message()` called `_parse_model_load_error()` which extracted model name and error type from the JSON response body. 2. The legacy `_is_model_load_error()` handler in `_process_session()` and `process_active_session()` also included model-specific details. 3. No abstraction layer to separate internal error details from user-facing messages. |
| **Solution** | 1. **Simplified `_format_lm_studio_error_message()`** — Removed call to `_parse_model_load_error()`. Now returns a generic message for 400 errors: ```⚠️ UNABLE TO RESPOND I couldn't connect to my AI brain. Please make sure LM Studio is running and a model is loaded before chatting.``` 2. **Updated `_parse_model_load_error()`** — Now returns `None` always. Kept for logging/debugging purposes only. 3. **Updated legacy handlers** — Both `_process_session()` and `process_active_session()` now use generic error messages without model names. |
| **Files Modified** | `src/discord_bot/message_processor.py` → `_format_lm_studio_error_message()`, `_parse_model_load_error()`, `_process_session()`, `process_active_session()` |
| **User-Facing Result** | Users now see: ```⚠️ UNABLE TO RESPOND I couldn't connect to my AI brain. Please make sure LM Studio is running and a model is loaded before chatting.``` No model names, error types, or internal details are leaked. |
| **Lesson** | Never expose internal error details (model names, error types, stack traces) directly to end users. Always use a generic, actionable message that tells the user what to do without revealing internal system state. |

---

## Infrastructure & Setup

### ISS-001: tkinter Not Available in Python 3.13 venv

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
| **Lesson** | tkinter availability varies by OS and Python version. Web-based GUI is more portable. |

---

### ISS-002: Corrupted venv Directory

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

---

### ISS-003: pip Command Not Found (sudo)

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

---

## Discord Bot Core

### ISS-006: Infinite `show_typing` Tool Calling Loop

| Field | Value |
|-------|-------|
| **ID** | ISS-006 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | LM Studio enters an infinite loop calling the `show_typing` tool repeatedly (Turn 1, Turn 2, Turn 3...) with empty text responses (`content='\n\n'`), eventually causing a Discord websocket connection error (`ClientConnectionResetError: Cannot write to closing transport`). |
| **Log Evidence** | ``` 2026-05-11 20:54:15,968 - 📝 Turn 1: content='\n\n', tool_calls=1 → 🔧 Turn 1: LM Studio called tool: show_typing ... 2026-05-11 20:54:17,356 - ℹ️ LM Studio used tool call, no text response to post ``` |
| **Root Cause** | The `show_typing` tool was sent to LM Studio as part of the tools list. After LM Studio called `show_typing`, the tool result was added to the conversation and the loop continued. LM Studio kept calling `show_typing` again and again without producing a text response, causing an infinite loop. |
| **Solution** | 1. **Removed `show_typing` from LM Studio tools** - No longer sent to the model for tool calling 2. **Typing indicator now shown deterministically** - After the configurable delay expires (default 5s), `channel.send_typing()` is called before message processing 3. **Made delay configurable** - Added `message_delay` setting (1-30 seconds) in config, API endpoints (`/api/settings/delay`), and UI input field 4. **Removed tool handling code** - Removed `show_typing` case from tool processing in both `_handle_message()` and `_handle_active_session_message()` 5. **Updated system prompt** - Removed `show_typing` references from the system prompt |
| **Files Modified** | `POC/test1/src/discord_bot.py`, `POC/test1/src/config.py`, `POC/test1/src/app.py`, `POC/test1/src/templates/index.html` |

---

### ISS-007: Typing Indicator Not Showing (show_typing Function Never Called)

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

### ISS-008: Duplicate Goodbye Message on Session End

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

### ISS-009: Messages Lost During Active Session Processing

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

### ISS-010: Security - Error Tracebacks Exposed to Discord Users

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

### ISS-011: Duplicate Message Handlers Running Simultaneously

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

### ISS-012: Empty Messages Cause LM Studio API Errors

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

### ISS-013: Discord Disconnect Button Not Working

| Field | Value |
|-------|-------|
| **ID** | ISS-013 |
| **Date** | 2026-05-11 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | Clicking "Disconnect" button did not disconnect the Discord bot. |
| **Root Cause** | `_bot_stop_event` was created but never used; `stop_discord_bot()` had race condition accessing `discord_bot_instance` |
| **Fix** | Added `_wait_for_stop_event()` async poller, modified `run_with_stop()` to use `asyncio.wait()` with `FIRST_COMPLETED`, rewrote `stop_discord_bot()` to properly signal thread shutdown |
| **Syntax Error Fix** | `_run_bot_safely()` had `global` declaration after assignments causing SyntaxError; fixed by returning status tuple instead of using global variables |
| **Code Location** | `POC/test1/src/app.py` → `_discord_bot_thread_func()`, `_wait_for_stop_event()`, `_run_bot_safely()`, `stop_discord_bot()` |

---

### ISS-014: discord_bot.py Too Large for Maintenance

| Field | Value |
|-------|-------|
| **ID** | ISS-014 |
| **Date** | 2026-05-12 |
| **Status** | ✅ Solved |
| **Severity** | Low (maintenance improvement) |
| **Description** | `discord_bot.py` was 1077 lines, making maintenance and debugging difficult. |
| **Solution** | Refactored into 6 focused modules under `src/discord_bot/` package |
| **New Files**: | `src/discord_bot/bot_core.py`, `src/discord_bot/message_handler.py`, `src/discord_bot/session_manager.py`, `src/discord_bot/token_tracker.py`, `src/discord_bot/typing_indicator.py`, `src/discord_bot/delay_processor.py` |
| **Modified**: | `src/discord_bot.py` - Now a backward-compat wrapper (~18 lines) |
| **Note**: | Package renamed from `discord` to `discord_bot` to avoid naming conflict with discord.py library |

---

### ISS-016: Queue Not Checked After New Session

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

### ISS-017: No Typing Indicator When Processing Queued Messages

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

### ISS-018: Active Session Context Loss - Bot Forgets Previous Messages

| Field | Value |
|-------|-------|
| **ID** | ISS-018 |
| **Date** | 2026-05-12 |
| **Status** | ✅ Solved & Verified |
| **Severity** | Critical |
| **Description** | During active sessions, the bot loses conversation context after each message. Every message is treated as "turn 1" and the bot cannot remember previous questions/answers in the same conversation. |
| **Log Evidence** | ``` 2026-05-12 10:33:11,483 - Active session turn 1 for channel <channel_id> ... 2026-05-12 10:33:28,755 - Active session turn 1 for channel <channel_id> ... ``` Every message shows "turn 1" because history is never persisted. |
| **Root Cause** | In `message_handler.py` → `_process_active_session()` at line 521, the code used `conversation_history = {channel_id: history}` which creates a **new local dictionary reference** and assigns it to the local parameter variable. This does NOT modify the original `self._conversation_history` dictionary in `bot_core.py`. |
| **Fix** | 1. Changed `conversation_history = {channel_id: history}` to `conversation_history[channel_id] = history` at line 521. 2. Added `conversation_history` parameter to `_process_active_session()` method signature. |
| **Code Location** | `POC/test1/src/discord_bot/message_handler.py` → `_process_active_session()` method, `handle_active_session_batch()` method |

---

### ISS-019: DelayProcessor Parameter Mismatch

| Field | Value |
|-------|-------|
| **ID** | ISS-019 |
| **Date** | 2026-05-16 |
| **Status** | ✅ Solved |
| **Severity** | Low |
| **Description** | `TypeError: DelayProcessor.process_active_session_with_delay() got an unexpected keyword argument 'author_nick'` |
| **Root Cause** | `bot_core.py` was passing `author_nick=author_nick` to `process_active_session_with_delay()`, but the method signature only accepts `author_name` and `author_display` |
| **Fix** | Removed `author_nick=author_nick` from the call in `bot_core.py` line 388 |
| **Code Location** | `src/discord_bot/bot_core.py` → `_handle_on_message()`, `src/discord_bot/delay_processor.py` → `process_active_session_with_delay()` |

---

### ISS-020: Concurrent LM Studio Requests Causing OOM Risk

| Field | Value |
|-------|-------|
| **ID** | ISS-020 |
| **Date** | 2026-05-16 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | When messages arrive in two different channels simultaneously, both get submitted to the thread pool and call LM Studio concurrently, potentially causing OOM errors on the LM Studio server |
| **Solution** | Added global `asyncio.Lock()` that serializes all LM Studio API calls |
| **Implementation**: | 1. Added `self._lm_studio_lock = asyncio.Lock()` to `DiscordBot.__init__()` 2. Added `lm_studio_lock` parameter to `MessageHandler.__init__()` 3. Added `_call_lm_studio()` helper method that acquires the global lock before each API call 4. Wrapped all 6 LM Studio API call sites with `_call_lm_studio()` |

---

### ISS-021: DelayProcessor Handler Callback Signature Mismatch

| Field | Value |
|-------|-------|
| **ID** | ISS-021 |
| **Date** | 2026-05-16 |
| **Status** | ✅ Solved |
| **Severity** | Low |
| **Description** | `TypeError: DiscordBot._process_active_session_batch() missing 1 required positional argument: 'pending_messages'` |
| **Root Cause** | `delay_processor.py` passed `pending` as the 6th positional argument, but `_process_active_session_batch` expects `pending_messages` as the 7th positional arg (after `author_nick`) |
| **Fix** | Changed call to pass `None` for `author_nick` and `pending_messages=pending` as keyword arg |
| **Code Location** | `src/discord_bot/delay_processor.py` → `process_active_session_with_delay()` |

---

### ISS-022: Modular Refactoring of message_handler.py (1025 lines → 6 files, all under 400)

| Field | Value |
|-------|-------|
| **ID** | ISS-022 |
| **Date** | 2026-05-16 |
| **Status** | ✅ Solved |
| **Severity** | Low (maintenance improvement) |
| **Problem** | `message_handler.py` was 1025 lines, making it difficult to maintain, debug, and understand. |
| **Solution** | Split into 6 focused modules under `src/discord_bot/` package with single-responsibility design. |
| **New File Structure** | ``` src/discord_bot/ ├── message_handler.py      (~303 lines) - Main handler class, orchestrates new/active sessions ├── message_processor.py    (~310 lines) - Core LM Studio session processing, multi-turn tool calling ├── tool_executor.py        (~345 lines) - Tool call handling (end_session, image_describe) ├── user_identity.py        (~128 lines) - User identity context building and message formatting ├── image_downloader.py     (~123 lines) - Safe image download with hostname whitelist └── lm_caller.py            (~123 lines) - LM Studio API caller with lock serialization ``` |
| **Files Created** | `src/discord_bot/message_processor.py`, `src/discord_bot/tool_executor.py`, `src/discord_bot/user_identity.py`, `src/discord_bot/image_downloader.py`, `src/discord_bot/lm_caller.py` |
| **Files Modified** | `src/discord_bot/message_handler.py` (reduced from 1025 to 303 lines) |

---

### ISS-023: Modular Refactoring of bot_core.py (844 lines → split with delay_processor)

| Field | Value |
|-------|-------|
| **ID** | ISS-023 |
| **Date** | 2026-05-16 |
| **Status** | ✅ Solved |
| **Severity** | Low (maintenance improvement) |
| **Problem** | `bot_core.py` was 844 lines. |
| **Solution** | Delay processing was already in separate `delay_processor.py` module. bot_core.py reduced to ~520 lines. |
| **Files Modified** | `src/discord_bot/bot_core.py` (reduced from 844 to ~520 lines), `src/discord_bot/delay_processor.py` (~110 lines) |

---

## Discord UI & API

### DISCORD-001: Discord Bot Stuck After Flask App Restart (Stale State)

| Field | Value |
|-------|-------|
| **ID** | DISCORD-001 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | When the Flask app is restarted (via debug reloader), the Discord bot fails to connect/disconnect properly. Error message: "❌ Discord connection failed: Bot is already connected". |
| **Root Cause** | 1. Flask's debug reloader spawns a new process, resetting module globals 2. The old Discord bot thread from the previous process may still be running 3. When `on_ready()` fires on the old thread, it updates `discord_connected = True` via `sys.modules` 4. The new Flask app sees `discord_connected = True` even though its own `discord_bot_thread` is `None` |
| **Solution** | 1. Added `force_reset_discord_state()` function in `discord_api.py` 2. Called `force_reset_discord_state()` at Flask app startup 3. Improved `start_discord_bot_thread()` to detect and clean up stale state 4. Improved `stop_discord_bot()` to handle edge cases 5. Added `/api/discord/force_reset` endpoint |
| **Files Modified** | `src/discord_api.py`, `src/app.py`, `src/templates/debug.html`, `src/static/debug_script.js` |

---

### DISCORD-002: UI Shows "Not Connected" Despite Bot Thread Running (Stale Import)

| Field | Value |
|-------|-------|
| **ID** | DISCORD-002 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Severity** | Critical |
| **Description** | After the Discord bot thread starts successfully (confirmed by logs), the UI still shows "Not connected". The `/api/status` endpoint returns `discord_connected: false` even though the bot thread is running. |
| **Root Cause** | Python's `from module import variable` creates a **local reference** to the value at import time, not a live link to the module attribute. When `bot_core.py` updated `discord_api.discord_connected = True` directly, this only changed the module attribute, not `app.py`'s local `discord_connected` variable. |
| **Fix** | Changed `app.py` to import the module (`from src import discord_api`) instead of individual variables. Created helper functions that always read from the module attribute dynamically. |
| **Files Modified** | `src/app.py` → changed import style, added getter functions, updated all route handlers |

---

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

### UX-001: Server Config Missing Auto-Discovery Features

| Field | Value |
|-------|-------|
| **ID** | UX-001 |
| **Date** | 2026-05-14 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | The Server Config UI required users to manually type Discord Server IDs and Channel IDs, which was cumbersome and error-prone. |
| **Fixes Applied** | 1. Added `get_guilds_info()` and `get_guild_channels()` methods to DiscordBot class 2. Added `/api/discord/servers` endpoint to list all guilds with names 3. Added `/api/discord/channels/<guild_id>` endpoint to list channels with names and categories 4. Added "📡 Load Servers from Discord" button in Server Config tab header 5. Added quick-add dropdown for servers when discovered 6. Added "🔍 Load Channels from Discord" button when editing a server 7. Added quick-add dropdown for channels when discovered 8. Server list now displays names: "My Server (123456789012345678)" 9. Channel list now displays names: "#general (111111111111111111)" |
| **Files Modified** | `src/discord_bot/bot_core.py`, `src/discord_api.py`, `src/static/lib/server-config.js`, `src/templates/index.html` |

---

### BUG-004: Channel Filter Shows Empty Config Due to Server ID Mismatch

| Field | Value |
|-------|-------|
| **ID** | BUG-004 |
| **Date** | 2026-05-14 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | The bot processes messages from all channels despite denied_channels being configured in config.json. Debug logs show `allowed_channels=[]` and `denied_channels=[]` for the active server. |
| **Root Cause** | **Server ID Mismatch**: The server ID in config.json (`1502926835862864000`) did NOT match the actual Discord guild ID (`1502926835862863944`). The last 3 digits differed (000 vs 944). |
| **Fix Applied** | Updated `config.json` server ID from `1502926835862864000` to `1502926835862863944` to match the actual Discord guild ID. |
| **Files Modified** | `config.json`, `src/discord_bot/bot_core.py` (added debug logging), `src/discord_api.py` (added config save/verify logging) |

---

### BUG-005: Server Config Changes Not Applied to Running Bot (Stale Config Reference)

| Field | Value |
|-------|-------|
| **ID** | BUG-005 |
| **Date** | 2026-05-14 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | Server/channel config changes saved to disk via the web UI were not reflected in bot behavior. |
| **Root Cause** | The Discord bot holds a stale `Config` instance from startup. When the API saves config, it creates a **new** `Config()` instance, saves to disk, and returns. The bot's `_config` is never updated. |
| **Fix Applied** | After saving config in `update_server_config()`, `add_channel_to_server()`, and `remove_channel_from_server()` endpoints, the bot instance's `_config` is now replaced with a fresh `Config()` instance. |
| **Files Modified** | `src/discord_api.py` → `update_server_config()`, `add_channel_to_server()`, `remove_channel_from_server()` |

---

### BUG-006: Auto-Discover Returns Wrong Server ID (JavaScript Integer Precision Loss)

| Field | Value |
|-------|-------|
| **ID** | BUG-006 |
| **Date** | 2026-05-14 |
| **Status** | ✅ Solved |
| **Severity** | Critical |
| **Description** | The "Load Servers from Discord" feature returned server IDs with corrupted last digits (e.g., `1502926835862863944` became `1502926835862864000`). |
| **Root Cause** | Discord snowflake IDs are 19 digits, exceeding JavaScript's `MAX_SAFE_INTEGER` (16 digits). The `get_guilds_info()` method returned guild IDs as **integers**, which get corrupted when passed through JSON → JavaScript → backend. |
| **Fix Applied** | Changed `get_guilds_info()` to return `str(guild.id)` instead of `guild.id`, matching how channel IDs are handled in `get_guild_channels()`. |
| **Files Modified** | `src/discord_bot/bot_core.py` → `get_guilds_info()` method |

---

## LM Studio & Model Integration

### REASONING-FIX: Model Excessive Reasoning Causing 120s Read Timeout

| Field | Value |
|-------|-------|
| **ID** | REASONING-FIX |
| **Date** | 2026-05-19 |
| **Status** | ✅ Solved |
| **Severity** | Critical |
| **Description** | The model (qwen3.6-35b-a3b-a4b) was entering extremely long internal reasoning loops (6383 reasoning tokens observed), causing 120-second READ TIMEOUT errors from LM Studio when processing tool calls like `image_compare`. |
| **Root Cause** | 1) The model's default behavior produces very long internal reasoning before responding. 2) No temperature control for tool-calling turns (temperature was always 0.7). 3) No max_tokens differentiation between tool-calling turns and final responses. 4) No system prompt instruction to keep reasoning brief. |
| **Fix Applied** | 1. **Reasoning Brevity Instruction**: Added critical instructions to system prompt in `message_handler.py` 2. **Tool-Specific max_tokens**: Modified `_call_lm_studio_via_processor()` to use `tool_max_tokens` (2048) for tool-calling turns and `final_max_tokens` (8192) for final responses 3. **Lower Tool Temperature**: Tool-calling turns now use `tool_temperature` (0.3) 4. **Tools Config Web UI**: Added new "⚙️ Tools Config" tab to the web UI |
| **Files Modified** | `src/config.py`, `src/app.py`, `src/discord_bot/bot_core.py`, `src/discord_bot/message_handler.py`, `src/templates/index.html`, `src/static/lm-instances.css`, `src/static/script.js` |

---

### BUG-010: LM Instance Model Selection Not Activating (Model Doesn't Switch)

| Field | Value |
|-------|-------|
| **ID** | BUG-010 |
| **Date** | 2026-05-20 |
| **Status** | ✅ Solved |
| **Severity** | Critical |
| **Description** | When selecting a model from the LM Instances tab dropdown, the model selection was not taking effect. The bot continued using the default/first model instead of the selected one. |
| **Root Causes** | Three issues: <br>1. **manager.py**: `select_model()` required `model_id` to be in `inst.available_models`, but discovery only happens when "Test" is clicked. <br>2. **lm_studio_client.py**: `connect()` always picked the first available model from LM Studio instead of respecting `_selected_model`. <br>3. **api.py + app.py**: The `selected_model` was saved to config but never synced to the `LMStudioClient` instance. |
| **Fix Applied** | **Fix #1** — `manager.py`: Removed `available_models` check from `select_model()`. <br>**Fix #2** — `lm_studio_client.py`: Updated `connect()` to prioritize `_selected_model`. <br>**Fix #3** — `api.py`: Added `_sync_client_selected_model()` helper. <br>**Fix #4** — `app.py`: Updated `init_instance_manager()` to pass the `client` reference. |
| **Files Modified** | `src/lm_models/manager.py`, `src/lm_studio_client.py`, `src/lm_models/api.py`, `src/app.py` |

---

### HANG-001: NameError — undefined 'timeout' variable in bot_core.py fetch_message fallback

| Field | Value |
|-------|-------|
| **ID** | HANG-001 |
| **Date** | 2026-06-03 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | When the fallback fetch in `_fetch_channel_messages()` times out, the debug log tries to reference `{timeout}s` but the variable is named `_fetch_timeout`, causing a `NameError`. |
| **Root Cause** | Line 1383 in `bot_core.py`: `logger.debug(f"[fetch_message] Fallback fetch timed out for msg {msg.id} after {timeout}s")` references `timeout` but the actual variable defined on line 1365 is `_fetch_timeout`. |
| **Fix Applied** | Changed `{timeout}s` to `{_fetch_timeout}s` in the debug log message on line 1383 of `src/discord_bot/bot_core.py`. |
| **Files Modified** | `src/discord_bot/bot_core.py` → `_fetch_channel_messages()` method (line 1383) |

---

### FIX-HANG-001: N+1 Query Fix + max_tool_calls Enforcement

| Field | Value |
|-------|-------|
| **ID** | FIX-HANG-001 |
| **Date** | 2026-06-03 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | Two separate issues that could cause bot hangs during `channel_search` tool execution: (1) N+1 query pattern in `_fetch_channel_messages()` where `channel.fetch_message(msg.id)` was called for every message lacking attachments, and (2) undefined `timeout` variable in the fallback fetch code. |
| **Root Cause** | **N+1 Query**: In `bot_core.py` `_fetch_channel_messages()`, the code had a conditional fallback that called `channel.fetch_message(msg.id)` for every message that lacked attachments in the history response. **Undefined Variable**: The fallback code referenced `timeout` variable but it was never defined in the method scope. |
| **Fix Applied** | **N+1 Query Fix**: Added conditional optimization — only call `channel.fetch_message(msg.id)` as fallback when history didn't populate attachments/embeds AND the message content hints at images. **Undefined Variable Fix**: Added `_fetch_timeout = 3.0` variable before the conditional block. |
| **Files Modified** | `src/discord_bot/bot_core.py` → `_fetch_channel_messages()` method |

---

## Image Processing

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
| **Root Cause** | The Config object was created in `app.py` but never assigned to `LMStudioClient`. `bot_core.py` tried to access `lm_studio_client.config.allowed_image_hostnames` but `LMStudioClient` had no `config` attribute. |
| **Fix** | 1. Added `_config` attribute and `config` property (getter/setter) to `LMStudioClient` in `src/lm_studio_client.py` 2. Assigned `client.config = config` in `src/app.py` after creating the client |
| **Files Modified** | `src/lm_studio_client.py` (added config property), `src/app.py` (added config assignment) |

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
- **Root Cause**: System prompt says "Call this when the user wants an image to be described" — LM Studio interprets ANY image attachment as a description request.
- **Fix Applied**: Updated system prompt in `handle_new_session()` to guide LM Studio: "Call this ONLY when the user explicitly asks for an image to be described. If the user sends an image but does NOT explicitly ask for it to be described, respond naturally about the image in text."
- **Files Modified**: `src/discord_bot/message_handler.py` → `handle_new_session()` system prompt (lines 269-277)

#### Sub-Issue 2b: Blocked Hostname Error Gives Poor User Experience
- **Description**: When image URL is from a non-allowed hostname, LM Studio gets `"Security: URL blocked: Hostname 'x' not in allowed hostnames"` and responds with a robotic error.
- **Fix Applied**: Replaced raw security error with user-friendly message: "The image URL could not be processed. This may be due to the image being hosted on an unsupported domain, or the URL may not be publicly accessible."
- **Files Modified**: `src/discord_bot/message_handler.py` → ValueError handlers

#### Sub-Issue 2c: Conversation Context Overflow (400 Error)
- **Description**: After multiple image interactions, conversation history grows to 6917 tokens. LM Studio returns 400 Bad Request, breaking the conversation.
- **Fix Applied (Fix E)**: Isolated context window for image describe:
  1. When `image_describe` tool is called, download and resize the image
  2. Create an ISOLATED mini-context with ONLY the image + "describe this image" prompt
  3. Get the description text from LM Studio using the mini-context
  4. Replace the tool call in the main conversation with the description as plain text
- **Files Modified**: `src/discord_bot/message_handler.py` → image_describe handling

#### Sub-Issue 2d: discord.py `Attachment.is_image()` Compatibility Warning
- **Description**: Log shows `WARNING - Error checking if attachment is image: 'Attachment' object has no attribute 'is_image'`
- **Root Cause**: `is_image()` is a property in discord.py 2.x, not a method.
- **Fix Applied**: Added `hasattr()` guard to check for `is_image` attribute before accessing it.
- **Files Modified**: `src/discord_bot/bot_core.py` → `_extract_image_attachments()` method

---

### BUG-007: image_describe Tool Not Called by LM Studio Model (Model Reasoning Timeout)

| Field | Value |
|-------|-------|
| **ID** | BUG-007 |
| **Date** | 2026-05-16 |
| **Status** | ✅ Solved |
| **Severity** | Critical |
| **Date Solved** | 2026-05-16 |
| **Symptom** | When user sent an image with "What do you see?", LM Studio hit max_tokens (2500) during reasoning, returned empty response with no tool calls. |
| **Log Evidence** | ```"finish_reason": "length"``` and ```"content": "", "tool_calls": []``` in LM Studio response. Token usage: 3479 total (979 prompt + 2500 completion). |
| **Root Cause** | The `image_describe` tool definition told the model `image_data` must be "Base64-encoded image data", but the model only had a URL. This caused an infinite reasoning loop. |
| **Fix Applied** | 1. Updated `src/tools/builtins/image_describe.py` tool description: "The image_data parameter accepts either a URL (e.g., Discord CDN link) or Base64-encoded image data." 2. Updated `image_data` parameter description. 3. Updated `mime_type` parameter description. 4. Updated system prompt in `message_handler.py`. |
| **Files Modified** | `src/tools/builtins/image_describe.py`, `src/discord_bot/message_handler.py` |

---

### BUG-009: image_describe channel_id Duplicate Keyword Argument

| Field | Value |
|-------|-------|
| **ID** | BUG-009 |
| **Date** | 2026-05-16 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Date Solved** | 2026-05-16 |
| **Symptom** | `TypeError: got multiple values for keyword argument 'channel_id'` when LM Studio called `image_describe` tool. |
| **Root Cause** | In `message_processor.py`, lambda wrappers passed `channel_id=None` explicitly. Meanwhile, `tool_executor.py` line 319 also passed `channel_id=None`. This caused `channel_id=None` to be passed twice. |
| **Fix Applied** | Removed explicit `channel_id=None` from both lambda wrappers in `message_processor.py` (lines 140 and 244). |
| **Files Modified** | `src/discord_bot/message_processor.py` |

---

### BUG-002 (CDN): image_describe Fails on Discord CDN Images — "This content is no longer available"

| Field | Value |
|-------|-------|
| **ID** | BUG-002 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | When LM Studio calls `image_describe` with a Discord CDN attachment URL, the download fails with "This content is no longer available" error. The error page is Discord's HTML response, not a 404. |
| **Root Cause** | Discord CDN attachment URLs require proper HTTP headers (User-Agent, Referer) to be treated as legitimate browser requests. The `SafeImageDownloader` was making raw `aiohttp` requests without these headers. |
| **Fix Applied** | **1. Auto User-Agent injection**: Modified `_download_with_session()` to automatically add a browser-like `User-Agent` header for Discord CDN hosts. <br> **2. Content-type error retry**: Added a second retry path that triggers when the initial response has an unexpected content type. |
| **Files Modified** | `src/discord_bot/image_downloader.py` → `_download_with_session()`, `download_image()` |

---

### BUG-014 (image URLs): channel_search Cannot Fetch Image URLs from Referenced Messages

| Field | Value |
|-------|-------|
| **ID** | BUG-014 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | When the LM Studio model wanted to describe an image referenced in a Discord message, it used `channel_search` with `message_id` parameter. However, `channel_search` results did not include image URLs from the referenced message. |
| **Root Cause** | 1. `channel_search` tool did not support fetching a specific message by `message_id`. 2. When `message_id` was passed, the tool ignored it and performed a regular channel search. 3. Image URLs were not extracted and displayed in channel_search results. |
| **Fix Applied** | **1. Added `get_message_by_id()` public method** in `bot_core.py`. **2. Updated `channel_search` tool** — when `message_id` is provided, fetches that specific message. **3. Added image URL extraction** — `channel_search` now extracts and displays image URLs from message attachments. |
| **Files Modified** | `src/discord_bot/bot_core.py`, `src/tools/builtins/channel_search.py`, `src/discord_bot/tool_executor.py` |

---

### BUG-011: Channel Name Resolution Fails for `#general` (Treated as ID, Not Name)

| Field | Value |
|-------|-------|
| **ID** | BUG-011 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | When the LM Studio model returns a channel specification like `#general` (a channel name prefixed with `#`), the `resolve_channel()` method fails to resolve it. |
| **Root Cause** | In `resolve_channel()`, the `#` prefix handler had two paths: (1) try `int(spec[1:])` for numeric IDs, and (2) on `ValueError`, just log a warning and return `None`. It never tried the stripped text as a channel name. |
| **Fix Applied** | 1. **`#` prefix fallback**: When `int(spec[1:])` raises `ValueError`, now tries the stripped text as a channel name (case-insensitive). <br> 2. **Case-insensitive name lookup**: Built a `mapping_lower` dict for all name-based lookups. |
| **Files Modified** | `src/discord_bot/bot_core.py` → `resolve_channel()` method |

---

### BUG-UX-002-REG: image_compare Infinite Loop (image_instruction Extracts Base64 Data)

| Field | Value |
|-------|-------|
| **ID** | BUG-UX-002-REG |
| **Date** | 2026-05-20 |
| **Status** | ✅ Solved |
| **Severity** | Critical |
| **Description** | After UX-002 fix, `image_compare` took ~6.5 minutes and got stuck in an infinite re-calling loop. LM Studio logs showed the model re-calling `image_compare` on Turn 2, Turn 3, etc. with empty responses. |
| **Log Evidence** | ```21:04:59 - [image_compare] Description for image 1: '' ← EMPTY``` and ```Turn 2: tool_calls=1 (re-calls image_compare)``` |
| **Root Cause** | `_extract_last_user_message()` extracted the Discord-formatted message which includes base64 image data from attachment extraction. This base64 data became the `image_instruction` in the mini-context, causing LM Studio to burn all 2500 tokens on reasoning. |
| **Fix Applied** | **Two-pronged fix:** <br>1. **`_extract_last_user_message()`** — Added regex to strip base64 data patterns, URLs, Discord CDN URLs, and `data:image/...;base64,...` schemes. <br>2. **`_handle_image_compare`/`_handle_image_compare_active`** — Changed to use `comparison_prompt` from tool arguments as `image_instruction`. |
| **Files Modified** | `src/discord_bot/tool_executor.py` (added `re` import, updated `_extract_last_user_message()`, updated handlers) |

---

### UX-002: Mini-Context Image Descriptions Use Generic Prompt (Not User-Specific)

| Field | Value |
|-------|-------|
| **ID** | UX-002 |
| **Date** | 2026-05-19 |
| **Status** | ✅ Solved |
| **Severity** | Low (UX improvement) |
| **Description** | When LM Studio calls `image_describe` or `image_compare`, the mini-context prompt was always "Please describe this image in detail, up to 3-4 sentences." regardless of what the user actually asked. |
| **Fix Applied** | Added `image_instruction` parameter to `_build_mini_context()` and `compare_images_async()`. Added `_extract_last_user_message()` helper to extract the last user message from conversation history. |
| **Regression** | UX-002 introduced BUG-UX-002-REG (infinite loop in image_compare) because the extracted user message contained base64 data. Fixed by stripping URLs/base64 from extracted messages. |
| **Files Modified** | `src/discord_bot/tool_executor.py`, `src/tools/builtins/image_compare.py` |

---

### UX-003: image_compare Uses 3-Step Describe-Then-Compare Instead of Direct Multi-Image Comparison

| Field | Value |
|-------|-------|
| **ID** | UX-003 |
| **Date** | 2026-05-20 |
| **Status** | ✅ Solved |
| **Severity** | Medium (architecture improvement) |
| **Description** | The `image_compare` tool used a 3-step process: (1) describe image 1 via mini-context, (2) describe image 2 via mini-context, (3) compare the two text descriptions. |
| **Fix Applied** | **Complete refactor of `compare_images_async()` in `image_compare.py`:** <br>1. Download all images and build base64 payloads <br>2. Build **single** mini-context with ALL images in the content array <br>3. Single `make_lm_call_func()` call with `max_tokens=4096` <br>4. Direct comparison result returned — no second step needed |
| **Files Modified** | `src/tools/builtins/image_compare.py`, `src/discord_bot/lm_caller.py`, `src/discord_bot/tool_executor.py` |

---

## Message Processing & Tool Calling

### CHANNEL-001: channel_search Result Format Causes LM Misinterpretation

| Field | Value |
|-------|-------|
| **ID** | CHANNEL-001 |
| **Date** | 2026-05-21 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | After channel_search tool returned results, LM Studio sometimes misinterpreted them and gave incorrect responses. |
| **Root Cause** | The tool result format was too loose and didn't clearly indicate which messages contained the search term. |
| **Fix Applied** | 1. **Improved result format** — Added structured `=== Channel Search Results ===` headers with explicit `Search query`, `Total matches`, and `CONTENT:` labels 2. **Added LM instructions** — Appended explicit instructions to read messages and identify matches 3. **Return "" after channel_search** — Changed to return empty string to signal the loop should continue for a final response |
| **Files Modified** | `src/tools/builtins/channel_search.py`, `src/discord_bot/tool_executor.py`, `src/discord_bot/message_handler.py` |

---

### FIX-003: Empty Response After Tool Processing (max_tokens Overflow)

| Field | Value |
|-------|-------|
| **ID** | FIX-003 |
| **Date** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Severity** | High |
| **Description** | After tool processing (image_describe, image_compare), LM Studio returns empty content on Turn 2. Token usage shows exactly 2500 completion tokens — the response hit max_tokens limit. |
| **Root Cause** | The tool result message combined with conversation history exceeds the context window. LM Studio uses all available tokens on reasoning/context and returns empty content. |
| **Fix Applied** | 1. Added `_execute_lm_call()` with `max_tokens_override` parameter 2. When Turn N returns empty content after tool processing, automatically retry with `max_tokens * 2` (capped at 8192) 3. Added warning message in tool result suggesting to increase max_tokens |
| **Files Modified** | `src/discord_bot/message_processor.py` → `_process_session()`, `process_active_session()`, `_execute_lm_call()`, new `_is_oom_error()` and `_is_max_tokens_overflow()` methods |

---

### FIX-004: image_compare Discord CDN URL Retry (text/plain Content-Type)

| Field | Value |
|-------|-------|
| **ID** | FIX-004 |
| **Date** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Severity** | Medium |
| **Description** | Second image URL in image_compare fails with "Blocked: disallowed content type 'text/plain'" because Discord CDN returns a redirect page instead of the actual image. |
| **Root Cause** | Discord CDN URLs with `?ex=...&is=...` params are temporary redirects. When downloaded without proper headers, they return HTML redirect pages with `text/plain` content type. |
| **Fix Applied** | 1. Added `_download_image_with_retry()` static method in ImageCompareTool 2. On content-type error, retries with `Referer: https://discord.com/` header |
| **Files Modified** | `src/tools/builtins/image_compare.py` → new `_download_image_with_retry()` method |

---

### BUG-007 (duplicate): max_tokens Retry Loop Exits Early (break → continue)

| Field | Value |
|-------|-------|
| **ID** | BUG-007 |
| **Date** | 2026-05-18 |
| **Date Solved** | 2026-05-19 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | The max_tokens retry logic in `message_processor.py` had a `break` statement that exits the loop instead of `continue`, preventing the retry with increased max_tokens from ever executing. |
| **Fix Applied** | Changed `break` to `continue` at line 167 in `_process_session()` and line 312 in `process_active_session()` in `src/discord_bot/message_processor.py`. |
| **Files Modified** | `src/discord_bot/message_processor.py` |

---

### FIX-001: Enhanced Tool Result Message to Prevent LM Studio Re-calling image_describe

| Field | Value |
|-------|-------|
| **ID** | FIX-001 |
| **Date** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Severity** | High |
| **Description** | After mini-context correctly describes an image, Turn 2 of the main conversation returns `content=''` with a tool call, causing LM Studio to re-call image_describe and get stuck in a loop. |
| **Root Cause** | Tool result message was too weak: "The image has been described. Here's what was in the image: [description]. Please continue the conversation naturally..." — LM Studio didn't realize it already had the description. |
| **Fix Applied** | Changed to: "IMAGE DESCRIPTION COMPLETE: [description]. You now have full information about this image. DO NOT call image_describe again for this image. Respond to the user's question using this description." |
| **Files Modified** | `src/discord_bot/tool_executor.py` → `_handle_image_describe()` and `_handle_image_describe_active()` |

---

### FIX-002: Handle URL Strings Passed as image_data Parameter

| Field | Value |
|-------|-------|
| **ID** | FIX-002 |
| **Date** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Severity** | Medium |
| **Description** | When LM Studio calls image_describe with a URL string instead of base64 data, the tool should detect and auto-download. |
| **Fix Applied** | Added `_handle_image_data()` helper method that detects URL vs base64, downloads via SafeImageDownloader if URL, detects MIME type, resizes, and returns (base64_data, mime_type) tuple. |
| **Files Modified** | `src/discord_bot/tool_executor.py` → new `_handle_image_data()` method |

---

## Memory System

### REQ-004: Discord Bot Integration (MEMORY-004)

| Field | Value |
|-------|-------|
| **ID** | REQ-004 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | Integrate memory system with Discord bot session lifecycle |
| **Implementation** | 1. Added MemoryManager to bot_core.py with shared DB path 2. _on_session_started(): Injects wake-up memory into system prompt on new session 3. _on_session_ended(): Saves conversation summary to memory, updates wake-up memory 4. _on_session_cleanup(): Prunes low-importance memories on session cleanup |
| **Files Modified** | `src/discord_bot/bot_core.py` |

---

### CONCEPT-001: Wake-up Memory System

| Field | Value |
|-------|-------|
| **ID** | CONCEPT-001 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | Compact summary of recent conversations shown at session start |
| **Implementation** | 1. Uses MemoryManager.get_wake_up_memory(user_id) to retrieve per-user wake-up memory 2. Uses MemoryManager.generate_sleep_summary() to update on session end 3. Content injected into system prompt before conversation starts 4. Truncated to ~500 chars for compactness |
| **Files Modified** | `src/discord_bot/bot_core.py` |

---

### CONCEPT-003: MemoryBot Architecture with Multi-Turn Search

| Field | Value |
|-------|-------|
| **ID** | CONCEPT-003 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Completed |
| **Description** | Implement a specialized MemoryBot sub-bot with fresh isolated context that handles memory search operations, protecting the main conversation context from being saturated with irrelevant memory results. |
| **Architecture** | Main Bot requests memory search → MemoryBot (fresh context) calls memory_recall → Memory System returns results → MemoryBot filters noise and distills findings → Main Bot receives only relevant info |
| **Design Decisions** | 1. **Name**: MemoryBot 2. **Single vs Multiple**: One shared MemoryBot per session 3. **Synchronous vs Async**: Synchronous - Main Bot waits for response 4. **Fallback**: If MemoryBot unavailable, Main Bot calls memory tools directly |
| **Implementation** | **Phase 1**: Created `src/memory/memorybot.py` with `search_memories()`, `filter_results()`, `distill_results()`, `run_search()` methods. **Phase 2**: Created `src/memory/memorybot_prompt.py` with system prompt template, user prompt template, refinement prompt, and helper functions. |
| **Files Created** | `src/memory/memorybot.py`, `src/memory/memorybot_prompt.py` |
| **Files Modified** | `src/memory/__init__.py` (added MemoryBot and prompt exports) |
| **Features** | 1. Isolated session management with topic tracking 2. Multi-turn search with query refinement (max 3 turns) 3. Timeout-based context expiration (60s) 4. Completion signal detection (`[SEARCH_COMPLETE]`, `[NO_RELEVANT_MEMORIES]`) |

---

### FIX-MEMORY-001: LM Studio Not Calling memory_tool to Save Data

| Field | Value |
|-------|-------|
| **ID** | FIX-MEMORY-001 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | Critical |
| **Description** | LM Studio was not calling the memory_tool to save conversation data. The memory system was not persisting any data. |
| **Root Cause** | 1. `memory_tool` was not registered in the tools system — `tool_executor.py` had no handlers for memory operations 2. The `operation` field from LM Studio tool call was not being popped from args before passing **args to `execute()`, causing `TypeError: execute() got multiple values for keyword argument 'operation'` |
| **Fix Applied** | 1. Added `memory_tool` case handlers in `tool_executor.py` for all operations (save, search, update, delete, list, summarize, clear) 2. Added `pop('operation')` from args before passing **args to `self.executor.execute()` |
| **Files Modified** | `src/discord_bot/tool_executor.py`, `src/discord_bot/bot_core.py`, `src/tools/builtins/__init__.py` |

---

### FIX-MEMORY-002: Default Memory Database Path Changed to user/data/memory/memory.db

| Field | Value |
|-------|-------|
| **ID** | FIX-MEMORY-002 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | Low |
| **Description** | Default memory database path was `data/memory.db` which was inconsistent with the project structure. Changed to `user/data/memory/memory.db` for better organization. |
| **Fix Applied** | 1. Changed default in `memorylite.py` `__init__()` parameter 2. Changed default in `config.py` `memory_db_path` property and `get_memory_config()` 3. Updated `DEFAULT_MEMORY_DB_PATH` in `settings.js` |
| **Files Modified** | `src/memory/memorylite.py`, `src/config.py`, `src/static/lib/settings.js` |

---

## Tools & Built-ins

### FEAT-002: Discord Channel Search Tool (Server Config UI Filter)

| Field | Value |
|-------|-------|
| **ID** | FEAT-002 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Date Solved** | 2026-05-14 |
| **Description** | Add search/filter functionality to the Server Config tab's channel lists so users can quickly find and identify channels when configuring allowed/denied channels. |
| **Solution** | 1. Added search input fields above both Allowed and Denied channel lists 2. Real-time filtering matches against channel name, ID, and category 3. Search rows only appear when channels are loaded from Discord 4. Non-matching channels are hidden, matching ones remain visible |
| **Files Modified** | `src/templates/index.html`, `src/static/minimal.css`, `src/static/lib/server-config.js` |

---

### FEAT-006: LM Studio Multi-Instance Management

| Field | Value |
|-------|-------|
| **ID** | FEAT-006 |
| **Date** | 2026-05-18 |
| **Status** | ✅ Complete & Verified |
| **Description** | Allow managing multiple LM Studio instances and selecting models per instance. Model selection dropdown appears in the model info bar after connecting to LM Studio. |
| **New Files Created:** | `src/lm_models/__init__.py`, `src/lm_models/models.py`, `src/lm_models/manager.py`, `src/lm_models/api.py`, `src/static/lm-instances.css`, `src/static/lib/lm-instances.js` |
| **Files Modified:** | `src/app.py`, `src/lm_studio_client.py`, `src/config.py`, `src/templates/index.html`, `src/static/script.js` |
| **API Endpoints Added:** | `/api/lm_instances` (GET/POST), `/api/lm_instances/<id>` (GET/DELETE), `/api/lm_instances/<id>/activate` (POST), `/api/lm_instances/<id>/discover` (POST), `/api/lm_instances/<id>/models` (GET), `/api/lm_instances/<id>/select_model` (POST), `/api/lm_instances/active` (GET), `/api/lm_instances/active/model` (GET/POST) |

---

### FEAT-007: New image_compare Tool for Multi-Image Comparison

| Field | Value |
|-------|-------|
| **ID** | FEAT-007 |
| **Date** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Description** | Tool that accepts 2-3 image URLs, downloads each, describes via mini-context, then generates structured comparison. |
| **New Files** | `src/tools/builtins/image_compare.py` (~280 lines) |
| **Files Modified** | `src/tools/builtins/__init__.py`, `src/discord_bot/bot_core.py`, `src/discord_bot/tool_executor.py`, `src/discord_bot/message_handler.py` |
| **Features** | Accepts `image_urls` array (2-3 items) and optional `comparison_prompt`. Downloads all images via SafeImageDownloader with Referer header retry for Discord CDN. Describes each via isolated mini-context. Returns structured comparison. |

---

### BUG-008: Debug Panel Sessions API Error (SessionManager.sessions Attribute Missing)

| Field | Value |
|-------|-------|
| **ID** | BUG-008 |
| **Date** | 2026-05-16 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Date Solved** | 2026-05-16 |
| **Symptom** | Debug panel repeatedly logged `'SessionManager' object has no attribute 'sessions'` error every 2 seconds when polling for session data. |
| **Root Cause** | After `discord_bot.py` was modular refactored into `src/discord_bot/` package, `SessionManager` no longer had a public `sessions` attribute. |
| **Fix Applied** | 1. `get_sessions()` endpoint: Changed `_bot._session_manager.sessions.get(channel_id)` to `_bot._session_manager.get_session(channel_id)`. 2. `clear_all_sessions()` endpoint: Changed `list(_bot._session_manager.sessions.keys())` to `_bot._session_manager.get_active_channels()`. |
| **Files Modified** | `src/app.py` → `get_sessions()`, `clear_all_sessions()` |

---

### BUG-014 (embeds): channel_search Only Checks Attachments, Not Embeds (Missing Image Embeds)

| Field | Value |
|-------|-------|
| **ID** | BUG-014 |
| **Date** | 2026-05-27 |
| **Status** | 📋 Documented |
| **Severity** | Medium |
| **Description** | The `channel_search` tool only checks `message.attachments` for images, but Discord messages can also contain images via `message.embeds`. |
| **Note** | This entry was marked as "Documented" not "Solved" — kept for reference. |

---

## Configuration & Settings

### BUG-003: Bot Cannot Identify Discord Users (No User Identity in Context)

| Field | Value |
|-------|-------|
| **ID** | BUG-003 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | The bot had no knowledge of who is talking to it. When asked "What is my name?" the bot responded "I don't know your name." |
| **Root Cause** | 1. `author_name` and `author_display` were extracted but `author_nick` (per-server nickname) was never extracted 2. The system prompt had partial identity info but no nickname 3. First user message had basic attribution but no nickname context |
| **Fix Applied** | **Phase 1 (P0):** 1. Extract `author_nick = message.author.nick` in `bot_core.py` 2. Pass `author_nick` through entire call chain 3. Added `_get_display_name_for_user()` helper 4. Updated system prompt with full identity context 5. Updated message attribution format to include nickname **Phase 2 (P1):** 6. Extended `SessionManager.start_session()` to accept `user_id`, `author_display`, `initial_nick`, `guild_id` |
| **Files Modified** | `src/discord_bot/bot_core.py`, `src/discord_bot/message_handler.py`, `src/discord_bot/session_manager.py` |

---

### STATUSMSG-001: Status Message Now Requires LLM-Generated Text

| Field | Value |
|-------|-------|
| **ID** | STATUSMSG-001 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Implemented |
| **Severity** | Medium |
| **Description** | Removed hardcoded tool status message fallback. Status messages are now only sent when the LLM provides a custom `tell_user_you_are_working` message via tool call arguments. |
| **Fix Applied** | 1. `_should_send_status()` in `message_processor.py` now takes `custom_message` parameter and returns `True` only if non-None 2. System prompt in `message_handler.py` instructs LLM to always include `tell_user_you_are_working` argument |
| **Files Modified** | `src/discord_bot/message_processor.py`, `src/discord_bot/message_handler.py` |

---

### PENDING-002: Hardcoded Turn Limit in Message Processing (range(3))

| Field | Value |
|-------|-------|
| **ID** | PENDING-002 |
| **Date** | 2026-05-21 |
| **Status** | ✅ Solved (2026-05-26) |
| **Severity** | Low |
| **Description** | Both `_process_session()` and `process_active_session()` use `for turn in range(3)` which hard-codes a maximum of 3 turns for tool calling. |
| **Fix Applied** | 1. Added `max_tool_turns` parameter to `MessageProcessor.__init__()` (default 5, clamped 1-10) 2. Added `max_tool_turns` to `MessageHandler.__init__()` and passed through to processor 3. Added `max_tool_turns` to `tools_config` in `config.py` (default 5) 4. Updated `bot_core.py` to read `max_tool_turns` from config |
| **Files Modified** | `src/discord_bot/message_processor.py`, `src/discord_bot/message_handler.py`, `src/discord_bot/bot_core.py`, `src/config.py` |

---

### PENDING-004: Session State Consistency on Processing Failure — Solved

| Field | Value |
|-------|-------|
| **ID** | PENDING-004 |
| **Date** | 2026-05-21 |
| **Date Solved** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | Low |
| **Description** | In `bot_core.py` `_process_active_session_batch()`, `self._session_manager.update_activity(channel_id)` was called **before** processing begins. If processing fails, the session appears "active" even though it may have failed mid-processing. |
| **Fix Applied** | Moved `self._session_manager.update_activity(channel_id)` to **after** the `handle_active_session_batch()` call succeeds. |
| **Files Modified** | `src/discord_bot/bot_core.py` → `_process_active_session_batch()` method |

---

### PENDING-005: Missing src/utils.py Import Verification

| Field | Value |
|-------|-------|
| **ID** | PENDING-005 |
| **Date** | 2026-05-21 |
| **Status** | ✅ Deprioritized (2026-05-27) |
| **Severity** | Low |
| **Description** | `tool_executor.py` imports `from src.utils import resize_image_bytes, image_to_base64`. This import chain should be verified. |
| **Resolution** | **Deprioritized** — Since the Flask app is running and processing messages (including image_compare which uses these functions), the imports are verified working. |
| **Files Verified** | `src/utils.py`, `src/discord_bot/tool_executor.py` |

---

## Refactoring & Code Quality

### CSS-001: CSS Files Too Large - Over-Engineered Styling

| Field | Value |
|-------|-------|
| **ID** | CSS-001 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Severity** | Low (Developer Experience) |
| **Description** | CSS files were massive: `styles.css` had 1,221 lines and `debug_styles.css` had 437 lines (1,658 total). The styling was over-engineered for an internal admin tool. |
| **Solution** | Replaced both files with a single `minimal.css` (~238 lines) containing only essential layout and styling. |
| **Files Changed** | Removed: `src/static/styles.css`, `src/static/debug_styles.css`. Added: `src/static/minimal.css`. Updated: `src/templates/index.html`, `src/templates/debug.html`. |

---

## Debugging & Development Tools

### DEBUG-001: Debug Page Not Showing Logs

| Field | Value |
|-------|-------|
| **ID** | DEBUG-001 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Severity** | Low |
| **Problem** | Debug page at `/debug` was not displaying any log entries despite logs being generated server-side |
| **Root Cause** | The `updateDebugLogDisplay` function in `lib/logs.js` was not being called properly from the debug page's own `fetchDebugLogs()` function in `debug_script.js`. |
| **Fix Applied** | 1. Rewrote `fetchDebugLogs()` in `debug_script.js` to directly call the API and `updateDebugLogDisplay()` 2. Added comprehensive console logging 3. Added `testLogDisplay()` function 4. Fixed `updateDebugLogDisplay()` in `lib/logs.js` with better error handling |

---

### DEBUG-002: JavaScript Syntax Error on Token Refresh

| Field | Value |
|-------|-------|
| **ID** | DEBUG-002 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Severity** | Low |
| **Problem** | `Uncaught SyntaxError: invalid assignment left-hand side` on line 355 of `debug_script.js` |
| **Root Cause** | Optional chaining `?.` was used on the left-hand side of an assignment: `document.getElementById('...')?.textContent = value` — this is invalid JavaScript because `?.` can only be used for reading, not writing |
| **Fix Applied** | Changed to explicit element checks: `const el = document.getElementById('debugPromptTokens'); if (el) el.textContent = data.value;` |

---

### DEBUG-003: Discord Status Always Shows "Not Connected"

| Field | Value |
|-------|-------|
| **ID** | DEBUG-003 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Problem** | Discord bot status always shows `discord_connected: false` in `/api/status` response even after clicking "Connect" on the main page. |
| **Root Cause** | The `on_ready()` callback in `bot_core.py` uses `asyncio.create_task(self._on_status_change_callback(...))` to notify the parent module. However, this callback mechanism fails silently because the callback is an async function defined in a **different thread**. |
| **Fix Applied** | Added direct global variable update in `on_ready()` using `sys.modules.get('src.discord_api')` to access and update the `discord_connected` and `discord_status_message` globals directly. |
| **Files Modified** | `POC/test1/src/discord_bot/bot_core.py` → `_register_events()` → `on_ready()` |

---

### BUG-LOG-001: Terminal Log File Gets Deleted/Cleared During Application Runtime

| Field | Value |
|-------|-------|
| **ID** | BUG-LOG-001 |
| **Date** | 2026-05-27 |
| **Date Solved** | 2026-05-27 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | The terminal log file (`POC/test1/terminal.log`) was being truncated during application runtime instead of only at startup. |
| **Root Cause** | `setup_logging()` was called at module level in `app.py` (line 69), which runs every time the Flask debug reloader spawns a new process. |
| **Fix Applied** | **1. `logger.py`**: Removed the incorrect `max_age_minutes` parameter from `_TeeStream.__init__()`. **2. `app.py`**: Moved `setup_logging()` call from module level into the `if __name__ == "__main__":` block. |
| **Files Modified** | `src/logger.py`, `src/app.py` |

---

## Performance & Optimization

### PERF-001: channel_search Returns Both Summaries AND Raw Messages (Token Inefficiency)

| Field | Value |
|-------|-------|
| **ID** | PERF-001 |
| **Date** | 2026-06-03 |
| **Status** | 📋 Documented — Optimization Opportunity |
| **Severity** | Low |
| **Description** | The `channel_search` tool batches messages into groups of 10 and uses LM to summarize each batch, but then still returns all 11 raw messages to the AI. |
| **Note** | This entry was marked as "Documented" not "Solved" — kept for reference. |

---

### BUG-014 (embeds): channel_search Only Checks Attachments, Not Embeds

| Field | Value |
|-------|-------|
| **ID** | BUG-014 (embeds) |
| **Date** | 2026-06-04 |
| **Status** | ✅ Solved |
| **Date Solved** | 2026-06-04 |
| **Severity** | Medium |
| **Problem** | The `channel_search` tool only checks `message.attachments` for images, but Discord messages can also contain images via `message.embeds`. Messages with image embeds (e.g., links that Discord auto-embeds as image previews) were incorrectly reported as `has_image=False`. |
| **Root Cause** | The `_format_message()` function in `bot_core.py` (used to format messages for channel_search results) only checked `message.attachments` for image detection. Discord messages can contain images in two ways: 1) `message.attachments` — direct file uploads, 2) `message.embeds` — links that Discord auto-embeds as image previews (with `embed.type == 'image'`). |
| **Fix Applied** | Updated `_format_message()` in `bot_core.py` to check both `message.attachments` AND `message.embeds` for image detection: ```python # Check attachments has_image = any( f.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')) for f in (message.attachments or []) ) # Check embeds if not has_image: for embed in (message.embeds or []): if embed.type == 'image' and embed.url: has_image = True if not has_image and embed.thumbnail and embed.thumbnail.url: has_image = True ``` |
| **Files Modified** | `src/discord_bot/bot_core.py` → `_format_message()` method (image detection logic) |
| **Verification** | Terminal log confirmed messages with image embeds containing `.png` URLs were previously undetected. After fix, `_format_message()` correctly identifies embed-based images. |

---

### CONCEPT-004: Channel Search Sliding Window — Implemented
| Field | Value |
|-------|-------|
| **ID** | CONCEPT-004 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Date Solved** | 2026-06-04 |
| **Severity** | Low |
| **Problem** | `channel_search` fetches at most 50 messages per channel. If content the LM is looking for is older than the 50 most recent messages, it gets nothing. |
| **Root Cause** | No offset/windows parameters existed in `channel_search` tool or bot layer message fetching. |
| **Fix Applied** | **1. `channel_search.py`**: Added `offset` (integer, default 0) and `windows` (integer, default 1, max 5) parameters to tool schema. Results include window indicator header `[offset=50, 3 windows]` in multi-window mode. **2. `bot_core.py`**: `_fetch_channel_history()` now iterates over `range(windows)`, calculating `window_skip = offset + (w * limit)` for each window. Fetches `window_skip + limit` messages from Discord.py history, then slices to get the desired window. **3. `tool_executor.py`**: Passes new parameters through to bot layer. |
| **Design Decisions** | 1. **Max windows = 5**: Prevents excessive API calls (5 × 50 = 250 messages max per channel). 2. **Non-contiguous windows**: Each window is separated by `limit` skipped messages. 3. **Backward compatibility**: `offset=0, windows=1` (defaults) preserves current behavior. 4. **Batch fetch optimization**: Uses Discord.py's `channel.history(limit=N)` to fetch all needed messages in a single API call per window. |
| **Files Modified** | `src/tools/builtins/channel_search.py`, `src/discord_bot/bot_core.py`, `src/discord_bot/tool_executor.py` |

---

### BUG-017 (reply): image_compare Fails on Expired CDN URLs from Referenced Messages in Reply Context

| Field | Value |
|-------|-------|
| **ID** | BUG-017 (reply) |
| **Date** | 2026-06-04 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | When a user sends a reply message referencing an old message containing images with expired CDN tokens (e.g., `?ex=6a167da7`), the `image_compare` tool receives already-expired URLs and fails with 404 errors. The reply message itself has NO attachments — the images are in the referenced message's embeds. |
| **Log Evidence** | User replied to message `1508736219281096804` containing two mannequin images with expired CDN tokens (`?ex=6a167da7`, `?ex=6a15fc3f`). The reply message `1512019371587797132` had NO attachments and NO embeds. When `image_compare` tool was called, BOTH images failed with 404. |
| **Root Cause** | The `extract_image_attachments()` method in `message_router.py` only checks the current message's `message.attachments` and `message.embeds`. It does NOT traverse into referenced messages (`message.reference`) to extract and refresh their image URLs. When a reply message has no attachments, expired CDN URLs from the referenced message's embeds were passed directly to tools without refresh. |
| **Fix Applied** | **1. Added `_extract_images_from_message()` helper method** — Extracts image URLs from a message's attachments and embeds WITHOUT refreshing (lighter version for referenced messages). **2. Modified `handle_on_message()`** — When `message.reference` exists and `message.reference.message_id` is present: (a) Fetch the referenced message via `message.channel.fetch_message()`, (b) Extract images using `_extract_images_from_message()`, (c) Refresh expired CDN URLs via `_refresh_expired_image_urls()`, (d) Merge with current message images into `all_image_attachments`. **3. Updated session handling** — Both active session and new session paths now receive `all_image_attachments` instead of just `image_attachments`. |
| **Files Modified** | `src/discord_bot/message_router.py` → added `_extract_images_from_message()` method, updated `handle_on_message()` to extract/refresh/merge referenced message images |
| **Verification** | User confirmed: "That worked!" — Reply messages referencing old messages with images now correctly extract and refresh CDN URLs before passing to tools. |

---

### AI-001: AI Fails to Identify Image URLs in channel_search Results

| Field | Value |
|-------|-------|
| **ID** | AI-001 |
| **Date** | 2026-06-03 |
| **Status** | 📋 Documented — Prompt/Context Issue |
| **Severity** | Medium |
| **Description** | After `channel_search` returned 11 messages (including previous conversations where the user explicitly shared mannequin image URLs), the AI responded: "I didn't find any mannequin images in recent messages." |
| **Note** | This entry was marked as "Documented" not "Solved" — kept for reference. |

---

### BUG-013 (search): channel_search Uses Operator-Based Query Syntax That LM Models Don't Learn Correctly

| Field | Value |
|-------|-------|
| **ID** | BUG-013 |
| **Date** | 2026-06-05 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | The `channel_search` tool used operator-based query syntax (`has: image from: BotGuzu#3756`) that the LM model had to learn to use correctly. In practice, the LM model either didn't use operators at all, or degraded the query over repeated calls (e.g., `has:image mannequin` → `manniqu`). This caused the tool to return empty results and the LM to get stuck in a re-calling loop (BUG-013 pattern). |
| **Root Cause** | The tool relied on the LM model to learn and correctly use operator syntax embedded in a single `search_query` string. This is unreliable because: (1) The LM doesn't always learn operator syntax from the tool description. (2) The LM may misspell or truncate operator queries on re-calls. (3) The operator parser was complex and error-prone. |
| **Fix Applied** | **Complete rewrite of the tool's parameter schema and filtering logic:** <br><br>**1. New explicit boolean parameters** — Replaced `has:` operator with dedicated boolean parameters: `has_image`, `has_link`, `has_file`, `has_video`, `has_audio`. The LM model now simply sets `has_image: true` instead of `has: image`. <br><br>**2. New explicit date parameters** — Replaced `after:`/`before:` operators with `after_date` and `before_date` string parameters (YYYY-MM-DD format). <br><br>**3. OR logic for has_* parameters** — All `has_*` boolean parameters act as OR filters. If `has_image: true` OR `has_link: true` OR `has_file: true` etc., the message matches if it has ANY of the specified content types. <br><br>**4. AND logic for other parameters** — `username`, `after_date`, `before_date`, and `search_query` all act as AND filters. All specified filters must match. <br><br>**5. Simplified search_query behavior** — Single-word `search_query`: matches only in message content (not file/attachment names). Multi-word `search_query`: ALL words must appear somewhere in the message content (AND logic). <br><br>**6. Updated tool description** — Removed all operator syntax references. New description clearly explains the boolean parameter approach. |
| **Files Modified** | `src/tools/builtins/channel_search.py` → `description` property, `parameters` property, `execute()` method (complete rewrite of filtering logic) |
| **New Tool Schema** | `has_image` (boolean), `has_link` (boolean), `has_file` (boolean), `has_video` (boolean), `has_audio` (boolean), `after_date` (string), `before_date` (string), `search_query` (string — simplified), `username` (string — unchanged), `channel` (string — unchanged), `limit` (integer — unchanged) |

---

### BUG-013-DEP: Deprecate Operator-Based Query Syntax in channel_search

| Field | Value |
|-------|-------|
| **ID** | BUG-013-DEP |
| **Date** | 2026-06-05 |
| **Status** | ✅ Solved |
| **Severity** | Low (maintenance improvement) |
| **Description** | The `channel_search` tool previously supported an operator-based query syntax (e.g., `"has: image from: BotGuzu#3756"`) that was deprecated in BUG-013. The operator syntax was removed entirely to prevent confusion and ensure the LM model uses only the new explicit parameter-based approach. |
| **Root Cause** | After BUG-013 introduced explicit boolean parameters (`has_image`, `username`, etc.), the old `_parse_operators()` method and `OPERATOR_PATTERN` regex were still present in the codebase. While they were no longer called, their presence could still confuse developers or future LM models into using the deprecated syntax. |
| **Fix Applied** | **1. Removed `_parse_operators()` method** — The entire method that extracted operators from `search_query` strings was deleted. **2. Removed `OPERATOR_PATTERN` regex** — The compiled regex pattern `r'(has|from|in|after|before):\s*(\S+)'` was deleted. **3. Updated tool description** — Added explicit deprecation notice: "DEPRECATED: The old operator-based query syntax (e.g., 'has: image from: BotGuzu') is deprecated. Use explicit boolean parameters instead: has_image=true, username='BotGuzu', etc." **4. Updated `deep_search` parameter description** — Clarified that filtering is applied via explicit parameters, NOT via operator syntax in `search_query`. |
| **Files Modified** | `src/tools/builtins/channel_search.py` → removed `_parse_operators()`, `OPERATOR_PATTERN`, updated `description` and `deep_search` parameter |
| **Migration Guide** | **Old syntax:** `"has: image from: BotGuzu#3756"` → **New parameters:** `has_image: true, username: "BotGuzu#3756"` <br> **Old syntax:** `"has: file after: 2026-06-01 before: 2026-06-05"` → **New parameters:** `has_file: true, after_date: "2026-06-01", before_date: "2026-06-05"` <br> **Old syntax:** `"from: @general mannequin"` → **New parameters:** `username: "@general", search_query: "mannequin"` |

---

### AI-001: AI Fails to Identify Image URLs in channel_search Results

| Field | Value |
|-------|-------|
| **ID** | AI-001 |
| **Date** | 2026-06-03 |
| **Status** | 📋 Documented — Prompt/Context Issue |
| **Severity** | Medium |
| **Description** | After `channel_search` returned 11 messages (including previous conversations where the user explicitly shared mannequin image URLs), the AI responded: "I didn't find any mannequin images in recent messages." |
| **Note** | This entry was marked as "Documented" not "Solved" — kept for reference. |

---

### AI-001: AI Fails to Identify Image URLs in channel_search Results

| Field | Value |
|-------|-------|
| **ID** | AI-001 |
| **Date** | 2026-06-03 |
| **Status** | 📋 Documented — Prompt/Context Issue |
| **Severity** | Medium |
| **Description** | After `channel_search` returned 11 messages (including previous conversations where the user explicitly shared mannequin image URLs), the AI responded: "I didn't find any mannequin images in recent messages." |
| **Note** | This entry was marked as "Documented" not "Solved" — kept for reference. |


| Field | Value |
|-------|-------|
| **ID** | AI-001 |
| **Date** | 2026-06-03 |
| **Status** | 📋 Documented — Prompt/Context Issue |
| **Severity** | Medium |
| **Description** | After `channel_search` returned 11 messages (including previous conversations where the user explicitly shared mannequin image URLs), the AI responded: "I didn't find any mannequin images in recent messages." |
| **Note** | This entry was marked as "Documented" not "Solved" — kept for reference. |

---

*End of Solved Issues. For current open and planned issues, see [issues_tracker.md](issues_tracker.md).*