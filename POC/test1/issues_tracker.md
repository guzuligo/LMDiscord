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
| **Status** | ✅ Backend Complete, UI Needs UX Improvements |
| **Severity** | Medium |
| **Description** | Implement per-server enable/disable and per-channel allow/deny lists so the bot can be selectively enabled across multiple Discord servers. Also includes a "Server Config" tab in the web UI for managing these settings. |
| **Features Implemented** | 1. Per-server enable/disable toggle in `config.json` ✅ 2. Per-server channel allow/deny lists ✅ 3. Web UI "Server Config" tab ✅ 4. API endpoints for server management ✅ 5. Bot_core checks to skip messages from disabled servers/channels ✅ |
| **Files Modified** | `src/config.py`, `src/discord_bot/bot_core.py`, `src/discord_api.py`, `src/templates/index.html`, `src/static/lib/server-config.js` |
| **Known UX Limitations** | See UX-001 below |

---

### 🆕 UX-001: Server Config Missing Auto-Discovery Features

| Field | Value |
|-------|-------|
| **ID** | UX-001 |
| **Date** | 2026-05-14 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Date Solved** | 2026-05-14 |
| **Description** | The Server Config UI required users to manually type Discord Server IDs and Channel IDs, which was cumbersome and error-prone. |
| **Fixes Applied** | 1. Added `get_guilds_info()` and `get_guild_channels()` methods to DiscordBot class in `bot_core.py` 2. Added `/api/discord/servers` endpoint to list all guilds with names 3. Added `/api/discord/channels/<guild_id>` endpoint to list channels with names and categories 4. Added "📡 Load Servers from Discord" button in Server Config tab header 5. Added quick-add dropdown for servers when discovered 6. Added "🔍 Load Channels from Discord" button when editing a server 7. Added quick-add dropdown for channels when discovered 8. Server list now displays names: "My Server (123456789012345678)" 9. Channel list now displays names: "#general (111111111111111111)" |
| **Files Modified** | `src/discord_bot/bot_core.py` (added get_guild_channels method), `src/discord_api.py` (added /api/discord/servers and /api/discord/channels endpoints), `src/static/lib/server-config.js` (added auto-discovery UI logic), `src/templates/index.html` (added Load Servers button) |

---

### 🆕 BUG-004: Channel Filter Shows Empty Config Due to Server ID Mismatch

| Field | Value |
|-------|-------|
| **ID** | BUG-004 |
| **Date** | 2026-05-14 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | The bot processes messages from all channels despite denied_channels being configured in config.json. Debug logs show `allowed_channels=[]` and `denied_channels=[]` for the active server. |
| **Root Cause** | **Server ID Mismatch**: The server ID in config.json (`1502926835862864000`) did NOT match the actual Discord guild ID (`1502926835862863944`). The last 3 digits differed (000 vs 944). The bot looks up the config using the actual guild ID from the message, finds no matching entry, and uses the default config (enabled, all channels allowed). |
| **Fix Applied** | Updated `config.json` server ID from `1502926835862864000` to `1502926835862863944` to match the actual Discord guild ID. |
| **Files Modified** | `config.json` (server ID corrected), `src/discord_bot/bot_core.py` (added debug logging), `src/discord_api.py` (added config save/verify logging, channel API logging) |

---

### 🆕 BUG-005: Server Config Changes Not Applied to Running Bot (Stale Config Reference)

| Field | Value |
|-------|-------|
| **ID** | BUG-005 |
| **Date** | 2026-05-14 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | Server/channel config changes saved to disk via the web UI were not reflected in bot behavior. The bot continued showing `allowed_channels=[]` and `denied_channels=[]` even after saving config. |
| **Root Cause** | The Discord bot holds a stale `Config` instance from startup. When the API saves config, it creates a **new** `Config()` instance, saves to disk, and returns. The bot's `_config` is never updated with the new data. |
| **Fix Applied** | After saving config in `update_server_config()`, `add_channel_to_server()`, and `remove_channel_from_server()` endpoints, the bot instance's `_config` is now replaced with a fresh `Config()` instance that reloads from disk. |
| **Files Modified** | `src/discord_api.py` → `update_server_config()`, `add_channel_to_server()`, `remove_channel_from_server()` |

---

### 🆕 BUG-006: Auto-Discover Returns Wrong Server ID (JavaScript Integer Precision Loss)

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

### 🆕 Discord Channel Search Tool (Server Config UI Filter) - FEAT-002

| Field | Value |
|-------|-------|
| **ID** | FEAT-002 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Date Solved** | 2026-05-14 |
| **Description** | Add search/filter functionality to the Server Config tab's channel lists so users can quickly find and identify channels when configuring allowed/denied channels. |
| **Solution** | 1. Added search input fields above both Allowed and Denied channel lists in the Server Config tab 2. Real-time filtering matches against channel name, ID, and category 3. Search rows only appear when channels are loaded from Discord 4. Non-matching channels are hidden, matching ones remain visible 5. Filter clears automatically when search input is emptied |
| **Files Modified** | `src/templates/index.html` (added search input fields), `src/static/minimal.css` (added search input styles), `src/static/lib/server-config.js` (added filterChannelList() function, updated renderChannelList() to store metadata in data attributes, updated loadDiscordChannels() to show search rows) |

---

### 🆕 FEAT-003: Debug Mode Flag for Logging (Planned)

| Field | Value |
|-------|-------|
| **ID** | FEAT-003 |
| **Date** | 2026-05-27 |
| **Status** | ⏳ Planned |
| **Description** | Verbose DEBUG-level logs (discord.py HTTP traces, urllib3 connection details, etc.) appear on every startup even when not debugging. Add `--debug` CLI flag or `DEBUG_MODE` config option to control logging verbosity. |
| **Requirements** | 1. Add `debug_mode` config option in `config.py` 2. `setup_logging()` in `logger.py` to accept `debug_level` parameter 3. Debug mode: `logging.basicConfig(level=logging.DEBUG)` — full verbose output 4. Normal mode: `logging.basicConfig(level=logging.INFO)` — suppress library DEBUG output |
| **Files to Modify** | `src/logger.py`, `src/app.py`, `src/config.py` |

---

### 🆕 Discord Token Metrics Push to Web UI (Planned)

| Field | Value |
|-------|-------|
| **ID** | FEAT-004 |
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

_No open issues._

---

## Recent Fixes

### BUG-003: Bot Cannot Identify Discord Users (No User Identity in Context) - 2026-05-14

| Field | Value |
|-------|-------|
| **ID** | BUG-003 |
| **Date** | 2026-05-13 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | The bot had no knowledge of who is talking to it. When asked "What is my name?" the bot responded "I don't know your name." This is because Discord user identity information was never fully communicated to the LM Studio. |
| **Root Cause** | 1. `author_name` and `author_display` were extracted but `author_nick` (per-server nickname) was never extracted 2. The system prompt had partial identity info but no nickname 3. First user message had basic attribution but no nickname context 4. SessionManager didn't store identity data for memory integration |
| **Fix Applied** | **Phase 1 (P0):** 1. Extract `author_nick = message.author.nick` in `bot_core.py` 2. Pass `author_nick` through entire call chain: `_handle_on_message` → `_handle_new_session_message` → `_process_active_session_batch` → `MessageHandler` methods 3. Added `_get_display_name_for_user()` helper (priority: nick > display > username) 4. Updated system prompt with full identity context including per-server nickname explanation 5. Updated message attribution format to include nickname: `[From guzu (nickname: Picatchu)]: hello` 6. Active session messages show nickname changes: `[guzu (was: Guzu, now: Picatchu)]: I changed my name` **Phase 2 (P1):** 7. Extended `SessionManager.start_session()` to accept `user_id`, `author_display`, `initial_nick`, `guild_id` 8. Added `_session_data` dict storing full identity context per channel 9. Added `get_session()` method returning full identity data for memory integration |
| **Identity Model** | ``` user_id (immutable) ──────────────────┐                                     │ author_name (stable) ────────────────  │  Primary identifiers for session tracking per_server_nick (per-guild) ──────┘  → Used when addressing user in chat ``` **Addressing Priority:** nick > display_name > username **Memory Key:** user_id (immutable) **Per-Server:** Each server can have different nicknames for same user |
| **Files Modified** | `src/discord_bot/bot_core.py` (extract nick, pass through chain, helper method, session init), `src/discord_bot/message_handler.py` (accept nick params, update system prompt, update attribution), `src/discord_bot/session_manager.py` (store initial nick + guild_id, add get_session method) |
| **Memory Integration Prep** | SessionManager now stores: `{user_id, author_name, initial_display, initial_nick, current_display, current_nick, guild_id}` per channel. This enables future memory module to: (1) Key by immutable user_id, (2) Track display/nick name history, (3) Store per-server identity separately |

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

### 🆕 CHANNEL-001: channel_search Result Format Causes LM Misinterpretation

| Field | Value |
|-------|-------|
| **ID** | CHANNEL-001 |
| **Date** | 2026-05-21 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | After channel_search tool returned results, LM Studio sometimes misinterpreted them and gave incorrect responses. For example, when searching for "Mannequin" in a channel, the bot said "it only found your messages asking to find it" even though the search returned matching messages. |
| **Root Cause** | The tool result format was too loose and didn't clearly indicate which messages contained the search term. LM Studio couldn't distinguish matching messages from non-matching ones. |
| **Fix Applied** | 1. **Improved result format** — Added structured `=== Channel Search Results ===` headers with explicit `Search query`, `Total matches`, and `CONTENT:` labels for each message 2. **Added LM instructions** — Appended explicit instructions: "Read the messages above. If the search query was 'X', identify which messages contain this term and provide a direct answer to the user's original question." 3. **Return "" after channel_search** — Changed to return empty string to signal the loop should continue for a final response (prevents bot going silent) |
| **Files Modified** | `src/discord

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

### Issue #14: DelayProcessor Parameter Mismatch (ISS-019) - 2026-05-16
- **Problem**: `TypeError: DelayProcessor.process_active_session_with_delay() got an unexpected keyword argument 'author_nick'`
- **Root Cause**: `bot_core.py` was passing `author_nick=author_nick` to `process_active_session_with_delay()`, but the method signature only accepts `author_name` and `author_display`
- **Fix**: Removed `author_nick=author_nick` from the call in `bot_core.py` line 388
- **Code Location**: `src/discord_bot/bot_core.py` → `_handle_on_message()`, `src/discord_bot/delay_processor.py` → `process_active_session_with_delay()`

---

### Issue #15: Concurrent LM Studio Requests Causing OOM Risk (ISS-020) - 2026-05-16
- **Problem**: When messages arrive in two different channels simultaneously, both get submitted to the thread pool and call LM Studio concurrently, potentially causing OOM errors on the LM Studio server
- **Solution**: Added global `asyncio.Lock()` that serializes all LM Studio API calls
- **Implementation**:
  1. Added `self._lm_studio_lock = asyncio.Lock()` to `DiscordBot.__init__()`
  2. Added `lm_studio_lock` parameter to `MessageHandler.__init__()`
  3. Added `_call_lm_studio()` helper method that acquires the global lock before each API call
  4. Wrapped all 6 LM Studio API call sites with `_call_lm_studio()`
  5. Added logging: "Waiting for LM Studio lock", "Acquired LM Studio lock", "Released LM Studio lock"
- **Verification**: Logs confirm channels are serialized — first channel acquires lock, second waits and acquires after release
- **Code Location**: `src/discord_bot/bot_core.py`, `src/discord_bot/message_handler.py`

---

### Issue #16: DelayProcessor Handler Callback Signature Mismatch (ISS-021) - 2026-05-16
- **Problem**: `TypeError: DiscordBot._process_active_session_batch() missing 1 required positional argument: 'pending_messages'`
- **Root Cause**: `delay_processor.py` passed `pending` as the 6th positional argument, but `_process_active_session_batch` expects `pending_messages` as the 7th positional arg (after `author_nick`)
- **Fix**: Changed call to pass `None` for `author_nick` and `pending_messages=pending` as keyword arg
- **Code Location**: `src/discord_bot/delay_processor.py` → `process_active_session_with_delay()`

---

### Issue #6: Infinite `show_typing` Tool Calling Loop (ISS-006) - 2026-05-11
- **Problem**: LM Studio entered infinite loop calling `show_typing` tool
- **Fix**: Removed `show_typing` from LM Studio tools, made typing indicator deterministic after configurable delay
- **New Feature**: Configurable message delay (1-30 seconds) via web UI

---

### BUG-007: image_describe Tool Not Called by LM Studio Model (Model Reasoning Timeout)

| Field | Value |
|-------|-------|
| **ID** | BUG-007 |
| **Date** | 2026-05-16 |
| **Status** | ✅ Solved |
| **Severity** | Critical |
| **Date Solved** | 2026-05-16 |
| **Symptom** | When user sent an image with "What do you see?", LM Studio hit max_tokens (2500) during reasoning, returned empty response with no tool calls. LM Studio logs showed the model was still writing its internal reasoning when it ran out of tokens. |
| **Log Evidence** | ```"finish_reason": "length"``` and ```"content": "", "tool_calls": []``` in LM Studio response. Token usage: 3479 total (979 prompt + 2500 completion = all tokens used for reasoning). |
| **Root Cause** | The `image_describe` tool definition told the model `image_data` must be "Base64-encoded image data", but the model only had a URL. This caused an infinite reasoning loop as the model debated whether it could produce Base64 from a URL, burning all 2500 tokens on reasoning without making the tool call. |
| **Fix Applied** | 1. Updated `src/tools/builtins/image_describe.py` tool description: "The image_data parameter accepts either a URL (e.g., Discord CDN link) or Base64-encoded image data. URLs will be automatically downloaded and processed." 2. Updated `image_data` parameter description: "URL of the image (e.g., Discord CDN link) or Base64-encoded image data (without data: URL prefix). URLs will be automatically downloaded." 3. Updated `mime_type` parameter description: "MIME type of the image (e.g., image/png, image/jpeg). Can be inferred from URL." 4. Updated system prompt in `message_handler.py`: "Pass the image URL directly to this tool — it will be automatically downloaded and processed." |
| **Verification** | Full pipeline working — model calls `image_describe` with URL → image downloaded from Discord CDN → resized → mini-context LM Studio call describes it → bot responds with description identifying "Kate from The Little Prince". |
| **Files Modified** | `src/tools/builtins/image_describe.py`, `src/discord_bot/message_handler.py` |

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
| **Log Evidence** | ```ERROR app Error getting sessions: 'SessionManager' object has no attribute 'sessions'``` |
| **Root Cause** | After `discord_bot.py` was modular refactored into `src/discord_bot/` package, `SessionManager` no longer had a public `sessions` attribute. It uses `_active_sessions`, `_session_users`, and `_session_data` internally with public methods like `get_session()`, `get_active_channels()`, etc. The `app.py` endpoints still referenced `_bot._session_manager.sessions.get(channel_id)` and `list(_bot._session_manager.sessions.keys())`. |
| **Fix Applied** | 1. `get_sessions()` endpoint: Changed `_bot._session_manager.sessions.get(channel_id)` to `_bot._session_manager.get_session(channel_id)` which returns a dict with keys `author_name`, `started_at`, etc. Updated attribute access to use dict keys. 2. `clear_all_sessions()` endpoint: Changed `list(_bot._session_manager.sessions.keys())` to `_bot._session_manager.get_active_channels()`. |
| **Files Modified** | `src/app.py` → `get_sessions()`, `clear_all_sessions()` |

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
| **Root Cause** | In `message_processor.py`, lambda wrappers passed `channel_id=None` explicitly: `lambda ctx, **kw: self._lm_caller.call(ctx, channel_id=None, **kw)`. Meanwhile, `tool_executor.py` line 319 also passed `channel_id=None` via `make_lm_call_func(mini_context, channel_id=None, use_tool_calling=False)`. This caused `channel_id=None` to be passed twice to `LMCaller.call()`. |
| **Fix Applied** | Removed explicit `channel_id=None` from both lambda wrappers in `message_processor.py` (lines 140 and 244). The `LMCaller.call()` method already defaults `channel_id` properly, and `tool_executor.py` passes `channel_id=None` when needed — no duplication. |
| **Files Modified** | `src/discord_bot/message_processor.py` |

---

### ISS-022: Modular Refactoring of message_handler.py (1025 lines → 6 files, all under 400)

| Field | Value |
|-------|-------|
| **ID** | ISS-022 |
| **Date** | 2026-05-16 |
| **Status** | ✅ Solved |
| **Severity** | Low (maintenance improvement) |
| **Date Solved** | 2026-05-16 |
| **Problem** | `message_handler.py` was 1025 lines, making it difficult to maintain, debug, and understand. |
| **Solution** | Split into 6 focused modules under `src/discord_bot/` package with single-responsibility design. |
| **New File Structure** | ``` src/discord_bot/ ├── message_handler.py      (~303 lines) - Main handler class, orchestrates new/active sessions ├── message_processor.py    (~310 lines) - Core LM Studio session processing, multi-turn tool calling ├── tool_executor.py        (~345 lines) - Tool call handling (end_session, image_describe) ├── user_identity.py        (~128 lines) - User identity context building and message formatting ├── image_downloader.py     (~123 lines) - Safe image download with hostname whitelist └── lm_caller.py            (~123 lines) - LM Studio API caller with lock serialization ``` |
| **Benefits** | Each file under 400 lines, single responsibility, easier to test and maintain. |
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
| **Date Solved** | 2026-05-16 |
| **Problem** | `bot_core.py` was 844 lines. |
| **Solution** | Delay processing was already in separate `delay_processor.py` module. bot_core.py reduced to ~520 lines. |
| **Files Modified** | `src/discord_bot/bot_core.py` (reduced from 844 to ~520 lines), `src/discord_bot/delay_processor.py` (~110 lines) |

---

### ISS-024: JavaScript/HTML/CSS Refactoring Needed

| Field | Value |
|-------|-------|
| **ID** | ISS-024 |
| **Date** | 2026-05-16 |
| **Status** | ⏳ Planned |
| **Severity** | Low (maintenance improvement) |
| **Description** | Several frontend files exceed the 400-line target for maintainability. |
| **Files to Refactor** | `src/static/server-config.js` (634 lines), `src/static/script.js` (533 lines), `src/static/debug_script.js` (468 lines) |
| **Target** | All files under 400 lines |

---

### 🆕 FEAT-006: LM Studio Multi-Instance Management

| Field | Value |
|-------|-------|
| **ID** | FEAT-006 |
| **Date** | 2026-05-18 |
| **Status** | ✅ Complete & Verified |
| **Description** | Allow managing multiple LM Studio instances and selecting models per instance. Model selection dropdown appears in the model info bar after connecting to LM Studio. A new "🧠 LM Instances" tab provides full multi-instance management. |

#### Implementation Details

**New Files Created:**
| File | Lines | Purpose |
|------|-------|---------|
| `src/lm_models/__init__.py` | ~10 | Package init |
| `src/lm_models/models.py` | ~88 | Data classes: `ModelInfo`, `LmInstanceConfig`, `LmInstance` |
| `src/lm_models/manager.py` | ~283 | `InstanceManager` - CRUD operations, model discovery, model selection, config persistence |
| `src/lm_models/api.py` | ~194 | Flask Blueprint with endpoints: list, add, get, delete, activate, discover, select model |
| `src/static/lm-instances.css` | ~197 | Styling for instance cards, add form, status messages |
| `src/static/lib/lm-instances.js` | ~200 | Frontend JS: load instances, add/remove/activate instances, model selection per instance |

**Files Modified:**
| File | Changes |
|------|---------|
| `src/app.py` | Added `init_instance_manager()` call, created `lm_bp` blueprint, registered LM endpoints |
| `src/lm_studio_client.py` | Added `switch_instance()` method, `selected_model` property, `chat_with_tools_stream()` for tool calling with streaming |
| `src/config.py` | Added `lm_instances` and `active_instance` to config template |
| `src/templates/index.html` | Added model dropdown to model info bar, added "🧠 LM Instances" tab with instance management UI, linked CSS/JS assets |
| `src/static/script.js` | Added `updateModelSelect()`, `selectModel()`, state tracking for LM hostname/port, tab switching for LM Instances |

**API Endpoints Added:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/lm_instances` | GET | List all LM Studio instances |
| `/api/lm_instances` | POST | Add a new instance |
| `/api/lm_instances/<id>` | GET | Get a specific instance |
| `/api/lm_instances/<id>` | DELETE | Remove an instance |
| `/api/lm_instances/<id>/activate` | POST | Activate an instance |
| `/api/lm_instances/<id>/discover` | POST | Discover models on an instance |
| `/api/lm_instances/<id>/models` | GET | Get models for an instance |
| `/api/lm_instances/<id>/select_model` | POST | Select a model for an instance |
| `/api/lm_instances/active` | GET | Get active instance |
| `/api/lm_instances/active/model` | GET | Get active model |
| `/api/lm_instances/active/model` | POST | Set active model |

**Known Bugs Fixed During Implementation:**
1. Config path was wrong (`parent.parent.parent` → `parent.parent`)
2. Manager `_load()` didn't create default instance when config had no `lm_instances` section
3. Frontend API paths used `/api/lm/...` but backend used `/api/lm_instances` (underscore)
4. Frontend checked `inst.connected` but backend returns `inst.is_connected`
5. Tab button and tab content both had `id="lm-instances-tab"` causing DOM conflict → fixed to `lm-instances-btn` and `lm-instances-content`

**Verification:**
- `curl /api/lm_instances` → Returns 1 instance ("Local LM Studio") with 15 discovered models
- `curl -X POST /api/lm_instances/local/discover` → Found 15 models on localhost:1234
- UI tested and verified working by user

---

### 🆕 FIX-001: Enhanced Tool Result Message to Prevent LM Studio Re-calling image_describe

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

### 🆕 FIX-002: Handle URL Strings Passed as image_data Parameter

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

### 🆕 FEAT-007: New image_compare Tool for Multi-Image Comparison

| Field | Value |
|-------|-------|
| **ID** | FEAT-007 |
| **Date** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Description** | Tool that accepts 2-3 image URLs, downloads each, describes via mini-context, then generates structured comparison. |
| **New Files** | `src/tools/builtins/image_compare.py` (~280 lines) |
| **Files Modified** | `src/tools/builtins/__init__.py`, `src/discord_bot/bot_core.py`, `src/discord_bot/tool_executor.py`, `src/discord_bot/message_handler.py` |
| **Features** | Accepts `image_urls` array (2-3 items) and optional `comparison_prompt`. Downloads all images via SafeImageDownloader with Referer header retry for Discord CDN. Describes each via isolated mini-context. Returns structured comparison. Graceful fallback when some images fail. |

---

### 🆕 FIX-003: Empty Response After Tool Processing (max_tokens Overflow)

| Field | Value |
|-------|-------|
| **ID** | FIX-003 |
| **Date** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Severity** | High |
| **Description** | After tool processing (image_describe, image_compare), LM Studio returns empty content on Turn 2. Token usage shows exactly 2500 completion tokens — the response hit max_tokens limit. |
| **Root Cause** | The tool result message combined with conversation history exceeds the context window. LM Studio uses all available tokens on reasoning/context and returns empty content. |
| **Fix Applied** | 1. Added `_execute_lm_call()` with `max_tokens_override` parameter 2. When Turn N returns empty content after tool processing, automatically retry with `max_tokens * 2` (capped at 8192) 3. Added warning message in tool result suggesting to increase max_tokens 4. If retry also returns empty → OOM detection → user-friendly error message 5. Added `_is_oom_error()` helper to detect OOM errors in exception messages 6. Applied to both `_process_session()` and `process_active_session()` |
| **Files Modified** | `src/discord_bot/message_processor.py` → `_process_session()`, `process_active_session()`, `_execute_lm_call()`, new `_is_oom_error()` and `_is_max_tokens_overflow()` methods |

---

### 🆕 FIX-004: image_compare Discord CDN URL Retry (text/plain Content-Type)

| Field | Value |
|-------|-------|
| **ID** | FIX-004 |
| **Date** | 2026-05-18 |
| **Status** | ✅ Implemented |
| **Severity** | Medium |
| **Description** | Second image URL in image_compare fails with "Blocked: disallowed content type 'text/plain'" because Discord CDN returns a redirect page instead of the actual image. |
| **Root Cause** | Discord CDN URLs with `?ex=...&is=...` params are temporary redirects. When downloaded without proper headers, they return HTML redirect pages with `text/plain` content type. |
| **Fix Applied** | 1. Added `_download_image_with_retry()` static method in ImageCompareTool 2. On content-type error, retries with `Referer: https://discord.com/` header 3. If all images fail → user-friendly error 4. If some images fail → proceeds with available images + failure note |
| **Files Modified** | `src/tools/builtins/image_compare.py` → new `_download_image_with_retry()` method, updated `compare_images_async()` |

---

## Recent Fixes

### BUG-007: max_tokens Retry Loop Exits Early (break → continue) - 2026-05-19

| Field | Value |
|-------|-------|
| **ID** | BUG-007 |
| **Date** | 2026-05-18 |
| **Date Solved** | 2026-05-19 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | The max_tokens retry logic in `message_processor.py` had a `break` statement that exits the loop instead of `continue`, preventing the retry with increased max_tokens from ever executing. |
| **Root Cause** | In `_process_session()` and `process_active_session()`, after detecting empty response on Turn N (post-tool-processing), the code appends a warning message to `messages_for_lm` but then uses `break` instead of `continue`. The `break` exits the turn loop immediately, so the next iteration (which would use `max_tokens_override`) never runs. |
| **Fix Applied** | Changed `break` to `continue` at line 167 in `_process_session()` and line 312 in `process_active_session()` in `src/discord_bot/message_processor.py`. This allows the turn loop to continue, which will now execute the retry with doubled max_tokens (up to 8192). |
| **Files Modified** | `src/discord_bot/message_processor.py` |

---

### REQ-004: Discord Bot Integration (MEMORY-004)

| Field | Value |
|-------|-------|
| **ID** | REQ-004 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | Integrate memory system with Discord bot session lifecycle |
| **Implementation** | 1. Added MemoryManager to bot_core.py with shared DB path |
  2. _on_session_started(): Injects wake-up memory into system prompt on new session |
  3. _on_session_ended(): Saves conversation summary to memory, updates wake-up memory |
  4. _on_session_cleanup(): Prunes low-importance memories on session cleanup |
  5. Wired hooks into _handle_new_session_message() and clear_session() |
  6. Memory save and pruning run as background tasks (non-blocking) |
| **Files Modified** | src/discord_bot/bot_core.py |


### CONCEPT-001: Wake-up Memory System

| Field | Value |
|-------|-------|
| **ID** | CONCEPT-001 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | Compact summary of recent conversations shown at session start |
| **Implementation** | 1. Uses MemoryManager.get_wake_up_memory(user_id) to retrieve per-user wake-up memory |
  2. Uses MemoryManager.generate_sleep_summary() to update on session end |
  3. Content injected into system prompt before conversation starts |
  4. Truncated to ~500 chars for compactness |
| **Files Modified** | src/discord_bot/bot_core.py |



### FIX-MEMORY-001: LM Studio Not Calling memory_tool to Save Data

| Field | Value |
|-------|-------|
| **ID** | FIX-MEMORY-001 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Solved |
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
| **Status** | ✅ Solved |
| **Severity** | Low |
| **Description** | Default memory database path was `data/memory.db` which was inconsistent with the project structure. Changed to `user/data/memory/memory.db` for better organization. |
| **Fix Applied** | 1. Changed default in `memorylite.py` `__init__()` parameter 2. Changed default in `config.py` `memory_db_path` property and `get_memory_config()` 3. Updated `DEFAULT_MEMORY_DB_PATH` in `settings.js` |
| **Files Modified** | `src/memory/memorylite.py`, `src/config.py`, `src/static/lib/settings.js` |

---

## Potential Issues (To Monitor)

### 🆕 STATUSMSG-001: Status Message Now Requires LLM-Generated Text

| Field | Value |
|-------|-------|
| **ID** | STATUSMSG-001 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Implemented |
| **Severity** | Medium |
| **Description** | Removed hardcoded tool status message fallback. Status messages are now only sent when the LLM provides a custom `tell_user_you_are_working` message via tool call arguments. This ensures status messages are always in-character and natural, rather than generic hardcoded text like "⏳ Searching channel history...". |
| **Fix Applied** | 1. `_should_send_status()` in `message_processor.py` now takes `custom_message` parameter and returns `True` only if non-None 2. System prompt in `message_handler.py` instructs LLM to always include `tell_user_you_are_working` argument with in-character status messages 3. `_send_tool_status_message()` still has a generic fallback for display text, but the message is only sent if the LLM provided a custom one |
| **Files Modified** | `src/discord_bot/message_processor.py`, `src/discord_bot/message_handler.py` |

---

## Potential Issues (To Monitor)

---

### ✅ CONCEPT-003: MemoryBot Architecture with Multi-Turn Search

| Field | Value |
|-------|-------|
| **ID** | CONCEPT-003 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Completed |

---

### 🆕 CONCEPT-004: Channel Search Sliding Window (Planned Enhancement)

| Field | Value |
|-------|-------|
| **ID** | CONCEPT-004 |
| **Date** | 2026-05-26 |
| **Status** | 📋 Documented, Enhancement Planned |
| **Severity** | Low |
| **Description** | Add sliding window support to `channel_search` so the LM can fetch non-contiguous message windows from different points in channel history. Currently, `channel_search` fetches at most 50 messages per channel. If the content the LM is looking for is older than the 50 most recent messages, it gets nothing. |
| **Proposed Parameters** | **`offset`** (integer, default 0): Number of most recent messages to skip before fetching. **`windows`** (integer, default 1, max 5): Number of non-contiguous windows to fetch. Each window is `limit` messages, separated by `limit` skipped messages. |
| **Example Usage** | `channel_search(channel="this", offset=50, limit=50)` → Skips messages 1-50, fetches 51-100. `channel_search(channel="this", offset=0, limit=20, windows=3)` → Window 1: messages 1-20, Window 2: messages 71-90, Window 3: messages 141-160. |
| **Result Format** | Results grouped by window with headers: `[Window 1: Messages 1-20]`, `[Window 2: Messages 71-90]`, etc. |
| **Design Decisions** | 1. **Max windows = 5**: Prevents excessive API calls (5 × 50 = 250 messages max per channel). 2. **Non-contiguous windows**: Each window is separated by `limit` skipped messages, creating a "skip pattern" that lets the LM jump through history efficiently. 3. **Backward compatibility**: `offset=0, windows=1` (defaults) preserves current behavior. 4. **Discord.py compatibility**: Uses `after` parameter with message objects to skip N messages from history. |
| **Files To Modify** | `src/tools/builtins/channel_search.py` (tool schema + description), `src/discord_bot/bot_core.py` (message fetching with offset/windows), `src/discord_bot/tool_executor.py` (pass new parameters through) |
| **Implementation Notes** | Discord.py's `channel.history()` supports `after` parameter with a message object. To skip N messages, fetch N messages and use the last one as the `after` cursor. For multiple windows, repeat this process N times. |

---

### 🆕 BUG-015: Channel Search 50-Message Limit is Restrictive (Planned Enhancement)

| Field | Value |
|-------|-------|
| **ID** | BUG-015 |
| **Date** | 2026-05-26 |
| **Status** | 📋 Documented, Enhancement Planned |
| **Severity** | Medium |
| **Description** | The `channel_search` tool currently fetches at most 50 messages per channel. If the content the LM is looking for is older than the 50 most recent messages, it gets nothing. The LM has no way to "look further back" in the channel history. |
| **Current Behavior** | `limit` parameter capped at 50. If the search target is beyond the 50 most recent messages, no results are returned. |
| **Desired Behavior** | Implement a sliding window approach that allows the LM to skip past recent messages and fetch older ones. |

| **Date Completed** | 2026-05-26 |
| **Severity** | Medium |
| **Description** | Implement a specialized MemoryBot sub-bot with fresh isolated context that handles memory search operations, protecting the main conversation context from being saturated with irrelevant memory results. |
| **Architecture** | Main Bot requests memory search → MemoryBot (fresh context) calls memory_recall → Memory System returns results → MemoryBot filters noise and distills findings → Main Bot receives only relevant info |
| **Design Decisions** | 1. **Name**: MemoryBot 2. **Single vs Multiple**: One shared MemoryBot per session 3. **Synchronous vs Async**: Synchronous - Main Bot waits for response 4. **Fallback**: If MemoryBot unavailable, Main Bot calls memory tools directly |
| **Implementation** | **Phase 1**: Created `src/memory/memorybot.py` with `search_memories()`, `filter_results()`, `distill_results()`, `run_search()` methods. **Phase 2**: Created `src/memory/memorybot_prompt.py` with system prompt template, user prompt template, refinement prompt, and helper functions. **Phase 3**: Wired into `src/memory/__init__.py` exports. **Phase 4**: Added topic tracking, multi-turn support (max 3 turns), timeout expiration (60s), query refinement logic — all built into MemoryBot class. |
| **Files Created** | `src/memory/memorybot.py`, `src/memory/memorybot_prompt.py` |
| **Files Modified** | `src/memory/__init__.py` (added MemoryBot and prompt exports) |
| **Features** | 1. Isolated session management with topic tracking 2. Multi-turn search with query refinement (max 3 turns) 3. Timeout-based context expiration (60s) 4. Completion signal detection (`[SEARCH_COMPLETE]`, `[NO_RELEVANT_MEMORIES]`) 5. System prompt template with context flush rules 6. Query refinement prompt for when initial search returns no results 7. Exported via `src/memory/__init__.py` for easy import |

---

### 🆕 PENDING-001: Error Handling in channel.send() After LM Studio Failures

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

### 🆕 PENDING-002: Hardcoded Turn Limit in Message Processing (range(3))

| Field | Value |
|-------|-------|
| **ID** | PENDING-002 |
| **Date** | 2026-05-21 |
| **Status** | ✅ Solved (2026-05-26) |
| **Severity** | Low |
| **Description** | Both `_process_session()` and `process_active_session()` use `for turn in range(3)` which hard-codes a maximum of 3 turns for tool calling. If a tool requires more than 2 retries (turn 0 initial + turn 1 tool result + turn 2 retry), the loop exits silently without attempting further tool calls. |
| **Fix Applied** | 1. Added `max_tool_turns` parameter to `MessageProcessor.__init__()` (default 5, clamped 1-10) 2. Added `max_tool_turns` to `MessageHandler.__init__()` and passed through to processor 3. Added `max_tool_turns` to `tools_config` in `config.py` (default 5) 4. Updated `bot_core.py` to read `max_tool_turns` from config and pass to `MessageHandler` 5. Turn loops in `_process_session()` and `process_active_session()` now use `range(max_tool_turns)` instead of `range(3)` 6. Added retry logic: when Turn N returns empty content after tool processing, automatically retry with doubled max_tokens (up to 8192) |
| **Warning** | The retry logic (doubling max_tokens on empty responses) can cause the model to use more tokens than expected. Monitor token usage after this change. If a retry also returns empty, OOM detection kicks in and posts a user-friendly error. |
| **Files Modified** | `src/discord_bot/message_processor.py`, `src/discord_bot/message_handler.py`, `src/discord_bot/bot_core.py`, `src/config.py` |

---

### 🆕 PENDING-003: Config Path Dependency Hardcoded

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

### 🆕 PENDING-004: Session State Consistency on Processing Failure

| Field | Value |
|-------|-------|
| **ID** | PENDING-004 |
| **Date** | 2026-05-21 |
| **Status** | 🔄 Open |
| **Severity** | Low |
| **Description** | In `bot_core.py` `_process_active_session_batch()`, `self._session_manager.update_activity(channel_id)` is called before processing. If processing fails and the lock is released in the except block, there's no guarantee about session state consistency. |
| **Code Location** | `src/discord_bot/bot_core.py` → `_process_active_session_batch()` lines 532, 580-586 |
| **Recommended Fix** | Consider updating session activity only after successful processing, or use a try/finally pattern to ensure consistent state. |
| **Files To Modify** | `src/discord_bot/bot_core.py` |

---

### 🆕 PENDING-005: Missing src/utils.py Import Verification

| Field | Value |
|-------|-------|
| **ID** | PENDING-005 |
| **Date** | 2026-05-21 |
| **Status** | ✅ Deprioritized (2026-05-27) |
| **Severity** | Low |
| **Description** | `tool_executor.py` imports `from src.utils import resize_image_bytes, image_to_base64`. While `src/utils.py` exists in the file listing, this import chain should be verified to ensure image processing doesn't fail at runtime with ImportError. |
| **Resolution** | **Deprioritized** — This is an internal code import check, not an external dependency issue. Since the Flask app is running and processing messages (including image_compare which uses these functions), the imports are verified working. Python catches import errors at module load time, so any broken imports would cause immediate startup failure. The `requirements.txt` file lists external pip packages, not internal module imports — these are unrelated concerns. |
| **Files Verified** | `src/utils.py`, `src/discord_bot/tool_executor.py` |

---

## Known Bugs (Not Yet Fixed)

---

### 🆕 BUG-UX-002-REG: image_compare Infinite Loop (image_instruction Extracts Base64 Data)

| Field | Value |
|-------|-------|
| **ID** | BUG-UX-002-REG |
| **Date** | 2026-05-20 |
| **Date Solved** | 2026-05-20 |
| **Status** | ✅ Solved |
| **Severity** | Critical |
| **Description** | After UX-002 fix, `image_compare` took ~6.5 minutes and got stuck in an infinite re-calling loop. LM Studio logs showed the model re-calling `image_compare` on Turn 2, Turn 3, etc. with empty responses. |
| **Log Evidence** | ```21:04:59 - [image_compare] Description for image 1: '' ← EMPTY``` and ```Turn 2: tool_calls=1 (re-calls image_compare)``` and ```Turn 3: tool_calls=1 (re-calls image_compare again)``` |
| **Root Cause** | `_extract_last_user_message()` extracted the Discord-formatted message which includes base64 image data from attachment extraction. This base64 data became the `image_instruction` in the mini-context, causing LM Studio to burn all 2500 tokens on reasoning and return empty content (`finish_reason: "length"`). The empty response then caused LM Studio to re-call `image_compare` indefinitely. |
| **Fix Applied** | **Two-pronged fix:** <br>1. **`_extract_last_user_message()`** — Added regex to strip base64 data patterns (`[A-Za-z0-9+/]{50,}`), URLs (`http://`, `https://`), Discord CDN URLs (`cdn.discordapp.com`, `cdn.discordix.com`), and `data:image/...;base64,...` schemes before returning the text. <br>2. **`_handle_image_compare`/`_handle_image_compare_active`** — Changed to use `comparison_prompt` from tool arguments as `image_instruction` instead of the extracted user message. This avoids the risk of extracting a message containing URLs/base64 data since the comparison_prompt already contains the proper prompt template. |
| **Files Modified** | `src/discord_bot/tool_executor.py` (added `re` import, updated `_extract_last_user_message()` with URL/base64 stripping, updated `_handle_image_compare()` and `_handle_image_compare_active()` to use `comparison_prompt` as `image_instruction`) |
| **Note** | `image_describe` handlers still use `_extract_last_user_message()` for `image_instruction`, but the function now strips URLs/base64 data so it won't cause overflow. |

---

### 🆕 UX-003: image_compare Uses 3-Step Describe-Then-Compare Instead of Direct Multi-Image Comparison

| Field | Value |
|-------|-------|
| **ID** | UX-003 |
| **Date** | 2026-05-20 |
| **Date Solved** | 2026-05-20 |
| **Status** | ✅ Solved |
| **Severity** | Medium (architecture improvement) |
| **Description** | The `image_compare` tool used a 3-step process: (1) describe image 1 via mini-context, (2) describe image 2 via mini-context, (3) compare the two text descriptions. This approach is suboptimal because the model compares written descriptions rather than seeing both images simultaneously, losing visual information and requiring 3 separate LM calls. |
| **Root Cause** | Original design chose to describe each image separately then compare descriptions, rather than sending all images in one multi-image mini-context call. |
| **Fix Applied** | **Complete refactor of `compare_images_async()` in `image_compare.py`:** <br>1. Download all images and build base64 payloads <br>2. Build **single** mini-context with ALL images in the content array: `{"role": "user", "content": [{"type": "text", "text": "Compare these 2 images..."}, {"type": "image_url", ...}, {"type": "image_url", ...}]}` <br>3. Single `make_lm_call_func()` call with `max_tokens=4096` to accommodate multi-image base64 payloads <br>4. Direct comparison result returned — no second step needed <br><br>**`lm_caller.py`**: Added `max_tokens` parameter to `call()` and `_make_lm_call()` for per-call token override. <br>**`tool_executor.py`**: Updated `_handle_image_compare()` and `_handle_image_compare_active()` to pass `mini_context_max_tokens=4096`. Updated `_get_mini_context_response()` to forward `max_tokens` override. <br><br>**Result**: Reduced from 3 LM calls to 1 LM call. Model sees all images simultaneously for direct visual comparison. |
| **Files Modified** | `src/tools/builtins/image_compare.py` (complete `compare_images_async()` rewrite), `src/discord_bot/lm_caller.py` (max_tokens override), `src/discord_bot/tool_executor.py` (max_tokens forwarding) |

---

### 🆕 UX-002: Mini-Context Image Descriptions Use Generic Prompt (Not User-Specific)

| Field | Value |
|-------|-------|
| **ID** | UX-002 |
| **Date** | 2026-05-19 |
| **Date Solved** | 2026-05-20 |
| **Status** | ✅ Solved (with regression fix) |
| **Severity** | Low (UX improvement) |
| **Description** | When LM Studio calls `image_describe` or `image_compare`, the mini-context prompt was always "Please describe this image in detail, up to 3-4 sentences." regardless of what the user actually asked. |
| **Fix Applied** | Added `image_instruction` parameter to `_build_mini_context()` and `compare_images_async()`. Added `_extract_last_user_message()` helper to extract the last user message from conversation history. All four handlers now extract the user's message and pass it as `image_instruction`. Falls back to generic description prompt when no user message is found. |
| **Regression** | UX-002 introduced BUG-UX-002-REG (infinite loop in image_compare) because the extracted user message contained base64 data. Fixed by stripping URLs/base64 from extracted messages and using `comparison_prompt` for image_compare. |
| **Files Modified** | `src/discord_bot/tool_executor.py` (added `image_instruction` param, `_extract_last_user_message()` helper with URL/base64 stripping, updated all 4 handlers), `src/tools/builtins/image_compare.py` (added `image_instruction` param to `compare_images_async()`) |
| **Example** | User: "Is the person in these images the same?" → Mini-context: "Is the person in these images the same?" → Focused description about facial features → Better comparison response |

---

---

### REASONING-FIX: Model Excessive Reasoning Causing 120s Read Timeout

| Field | Value |
|-------|-------|
| **ID** | REASONING-FIX |
| **Date** | 2026-05-19 |
| **Date Solved** | 2026-05-19 |
| **Status** | ✅ Solved |
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

### 🆕 BUG-010: LM Instance Model Selection Not Activating (Model Doesn't Switch)

| Field | Value |
|-------|-------|
| **ID** | BUG-010 |
| **Date** | 2026-05-20 |
| **Date Solved** | 2026-05-20 |
| **Status** | ✅ Solved |
| **Severity** | Critical |
| **Description** | When selecting a model from the LM Instances tab dropdown, the model selection was not taking effect. The bot continued using the default/first model instead of the selected one. |
| **Root Causes** | Three issues were found: <br>1. **manager.py**: `select_model()` required `model_id` to be in `inst.available_models`, but discovery only happens when "Test" is clicked. Without discovery, the list is empty, so all selections were rejected. <br>2. **lm_studio_client.py**: `connect()` always picked the first available model from LM Studio instead of respecting `_selected_model`. <br>3. **api.py + app.py**: The `selected_model` was saved to config but never synced to the `LMStudioClient` instance. The client's `_selected_model` attribute was never updated after startup. |
| **Fix Applied** | **Fix #1** — `manager.py`: Removed `available_models` check from `select_model()`. Any model can now be selected (discovery is optional browsing only). <br>**Fix #2** — `lm_studio_client.py`: Updated `connect()` to prioritize `_selected_model` over first available model. Also updated the `selected_model` setter to immediately update `_model` when already connected, so no reconnect is needed. <br>**Fix #3** — `api.py`: Added `_sync_client_selected_model()` helper and called it from both `select_model` and `set_active_model` endpoints. Added `_client` global to `api.py`. <br>**Fix #4** — `app.py`: Updated `init_instance_manager()` call to pass the `client` reference so the sync can work. |
| **Files Modified** | `src/lm_models/manager.py` (removed available_models check), `src/lm_studio_client.py` (connect() + setter), `src/lm_models/api.py` (added _sync_client_selected_model, _client global), `src/app.py` (pass client to init_instance_manager) |
| **Workflow** | Activate instance → Test (discover models) → Select model → Works immediately (no reconnect needed) |

---

### 🆕 FEAT-008: Context Management System — Channel Search, Session Start Context, Context Compression

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

| **Files Created** | `src/tools/builtins/channel_search.py`, `src/tools/builtins/context_compressor.py`, `src/discord_bot/context_management.md` |
| **Files Modified** | `bot_core.py`, `message_handler.py`, `config.py`, `app.py` |

---

### 🆕 PENDING-004: Session State Consistency on Processing Failure — Solved

| Field | Value |
|-------|-------|
| **ID** | PENDING-004 |
| **Date** | 2026-05-21 |
| **Date Solved** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | Low |
| **Description** | In `bot_core.py` `_process_active_session_batch()`, `self._session_manager.update_activity(channel_id)` was called **before** processing begins. If processing fails and the lock is released in the `except` block, there's no guarantee about session state consistency — the session appears "active" even though it may have failed mid-processing. |
| **Root Cause** | `update_activity()` was at line 560, before the message handler call. Failed processing would still refresh the last-active timestamp. |
| **Fix Applied** | Moved `self._session_manager.update_activity(channel_id)` to **after** the `handle_active_session_batch()` call succeeds. Now the activity timestamp is only updated when processing completes successfully. Added comment explaining the fix. |
| **Files Modified** | `src/discord_bot/bot_core.py` → `_process_active_session_batch()` method |

---

### 🆕 BUG-002: image_describe Fails on Discord CDN Images — "This content is no longer available"

| Field | Value |
|-------|-------|
| **ID** | BUG-002 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | When LM Studio calls `image_describe` with a Discord CDN attachment URL, the download fails with "This content is no longer available" error. The error page is Discord's HTML response, not a 404 — the CDN returns `text/html` content type instead of the actual image. |
| **Root Cause** | Discord CDN attachment URLs require proper HTTP headers (User-Agent, Referer) to be treated as legitimate browser requests. The `SafeImageDownloader` was making raw `aiohttp` requests without these headers, causing Discord's CDN to return an error page instead of the image. |
| **Fix Applied** | **1. Auto User-Agent injection**: Modified `_download_with_session()` to automatically add a browser-like `User-Agent` header (`Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...`) for Discord CDN hosts (`cdn.discordapp.com`, `media.discordapp.net`). <br> **2. Content-type error retry**: Added a second retry path that triggers when the initial response has an unexpected content type (e.g., `text/html` error page). This retries with a `Referer: https://discord.com` header. <br> **3. Improved logging**: Added detailed logging for each download attempt, retry, and success/failure outcome. |
| **Files Modified** | `src/discord_bot/image_downloader.py` → `_download_with_session()` (User-Agent injection), `download_image()` (content-type error retry path) |
| **Testing** | Pending — requires live test with Discord image attachment |

---

### 🆕 BUG-011: Channel Name Resolution Fails for `#general` (Treated as ID, Not Name)

| Field | Value |
|-------|-------|
| **ID** | BUG-011 |
| **Date** | 2026-05-26 |
| **Date Solved** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | When the LM Studio model returns a channel specification like `#general` (a channel name prefixed with `#`), the `resolve_channel()` method fails to resolve it. It tries to parse `general` as an integer channel ID, gets a `ValueError`, and returns `None` instead of falling through to try it as a channel name. |
| **Root Cause** | In `resolve_channel()`, the `#` prefix handler had two paths: (1) try `int(spec[1:])` for numeric IDs, and (2) on `ValueError`, just log a warning and return `None`. It never tried the stripped text as a channel name. Additionally, the plain text channel name lookup at the end was case-sensitive. |
| **Fix Applied** | 1. **`#` prefix fallback**: When `int(spec[1:])` raises `ValueError`, now tries the stripped text as a channel name (case-insensitive) before returning `None`. <br> 2. **Case-insensitive name lookup**: Built a `mapping_lower` dict (`{name.lower(): cid}`) used for all name-based lookups (`#`, `@`, and plain text). <br> 3. **Better debug logging**: All resolution failures now include available channel names in the log message. <br> 4. **Updated docstring**: Documents all supported formats including `#general` as channel name. |
| **Supported Formats** | `#123456789` (numeric ID), `#general` (channel name), `@channelname` (channel name), `this`/`current` (active session), `123456789` (plain ID), `general` (plain name) — all case-insensitive for names |
| **Files Modified** | `src/discord_bot/bot_core.py` → `resolve_channel()` method |

---

### 🆕 BUG-014: channel_search Cannot Fetch Image URLs from Referenced Messages

| Field | Value |
|-------|-------|
| **ID** | BUG-014 |
| **Date** | 2026-05-26 |
| **Date Solved** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Description** | When the LM Studio model wanted to describe an image referenced in a Discord message, it used `channel_search` with `message_id` parameter. However, `channel_search` results did not include image URLs from the referenced message. The LM received empty image data and could not proceed with `image_describe`. |
| **Root Cause** | 1. `channel_search` tool did not support fetching a specific message by `message_id` — it only searched recent messages by text. 2. When `message_id` was passed, the tool ignored it and performed a regular channel search. 3. The `fetch_message_by_id` method existed in `bot_core.py` but was not wired into `channel_search`. 4. Image URLs were not extracted and displayed in channel_search results. |
| **Fix Applied** | **1. Added `get_message_by_id()` public method** in `bot_core.py` — wraps `fetch_message_by_id()` for external access. **2. Updated `channel_search` tool** — when `message_id` is provided, fetches that specific message instead of searching channel history. **3. Added image URL extraction** — `channel_search` now extracts and displays image URLs from message attachments in the result. **4. Updated `tool_executor.py`** — passes `message_id` through to `channel_search` and handles the new message-by-ID flow. |
| **Files Modified** | `src/discord_bot/bot_core.py` (added `get_message_by_id()` public method), `src/tools/builtins/channel_search.py` (added `message_id` support, image URL extraction), `src/discord_bot/tool_executor.py` (updated handlers to pass `message_id`, display image URLs in results) |
| **Live Test Verification** | ✅ Verified 2026-05-26: User sent "What about this?" with image attachment → LM called `channel_search` with `message_id` → Tool fetched the message and extracted image URL → LM called `image_describe` with the URL → Image described successfully → Full pipeline working. |

---

### 🆕 FEAT-LOG-001: Verbose Mode Toggle + Log Level Control Panel (Planned)

| Field | Value |
|-------|-------|
| **ID** | FEAT-LOG-001 |
| **Date** | 2026-05-27 |
| **Status** | 📋 Documented, Ready for Implementation |
| **Severity** | Low |
| **Description** | Add a toggle to enable/disable verbose logging mode and a log level control panel in the web UI. Currently, the logger supports `LogLevel` levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) and `_current_log_level_filter` in `app.py`, but there's no UI control to change it dynamically. The verbose mode should be disabled by default once the feature is fully tested, but the infrastructure should remain ready for later use. |
| **Current State** | 1. `logger.py` has full `LogLevel` enum with CSS colors and icons. 2. `app.py` has `_current_log_level_filter = LogLevel.DEBUG` and `set_log_level` API endpoint. 3. `get_logs()` supports `level_filter` parameter. 4. Web UI has a "Logs" tab but no log level selector. |
| **Proposed Implementation** | **1. Add `verbose_mode` toggle** to config (default `false` after testing). When `false`, only WARNING+ logs are shown. When `true`, DEBUG+ logs are shown. **2. Add log level selector** to web UI (dropdown: DEBUG, INFO, WARNING, ERROR, CRITICAL). **3. Wire the selector** to the existing `set_log_level` API endpoint. **4. Keep verbose mode disabled by default** — the feature should be "ready for later" with the toggle in the UI. |
| **Config Schema** | ```json
{
  "logging": {
    "verbose_mode": false,
    "default_level": "WARNING"
  }
}
``` |
| **Files To Modify** | `src/config.py` (add logging config), `src/app.py` (wire verbose_mode to log level), `src/templates/index.html` (add log level dropdown), `src/static/script.js` (wire dropdown to API) |
| **Design Decisions** | 1. **Default to non-verbose**: After full testing, verbose mode should be OFF by default. 2. **Toggle persists**: Verbose mode setting should be saved in config and survive restarts. 3. **Log level dropdown**: Simple select element with 5 options matching LogLevel enum. 4. **Backward compatible**: If no config exists, default to WARNING level (quiet mode). |

---

### 🆕 FEAT-008: Context Management System — Channel Search, Session Start Context, Context Compression

---

### 🆕 BUG-013: channel_search Tool Call Loop — Model Re-calls Instead of Using Results

| Field | Value |
|-------|-------|
| **ID** | BUG-013 |
| **Date** | 2026-05-27 |
| **Status** | 📋 Documented |
| **Severity** | High |
| **Description** | When the LM Studio model calls `channel_search` tool, it re-calls the tool up to 3 times (max_tool_calls) without using the returned results. After the 3rd call, it returns `content='\n\n'` (empty response). The model fails to process the search results and respond to the user's original question. |
| **Log Evidence** | ```Turn 1: content='', tool_calls=1 → 🔧 Turn 1: LM Studio called tool: channel_search ... Turn 2: content='', tool_calls=1 → 🔧 Turn 2: LM Studio called tool: channel_search ... Turn 3: content='', tool_calls=1 → 🔧 Turn 3: LM Studio called tool: channel_search ... Turn 4: content='\n\n', tool_calls=0 → ❌ Empty response after max tool calls (3)``` |
| **Root Cause** | 1. The tool result from `channel_search` is appended to the conversation history 2. LM Studio does not recognize the results as sufficient to answer the user's question 3. The model re-calls `channel_search` thinking it needs more data 4. After hitting max_tool_calls (3), the model returns empty content |
| **Related Issues** | CHANNEL-001 (result format improvement), ISS-006 (same pattern with show_typing tool), BUG-010 (existing - different issue), BUG-011 (existing - different issue) |
| **Proposed Fix** | 1. Add explicit instruction in tool result: "You now have the search results. Respond to the user's question using this data." 2. After max_tool_calls is reached, force the model to respond with the gathered data by injecting a system message 3. Consider reducing max_tool_calls for channel_search specifically |
| **Files To Modify** | `src/discord_bot/message_processor.py` (max tool call handling), `src/discord_bot/tool_executor.py` (tool result format), `src/discord_bot/message_handler.py` (system prompt) |

---

### 🆕 BUG-014: channel_search Only Checks Attachments, Not Embeds (Missing Image Embeds)

| Field | Value |
|-------|-------|
| **ID** | BUG-014 |
| **Date** | 2026-05-27 |
| **Status** | 📋 Documented |
| **Severity** | Medium |
| **Description** | The `channel_search` tool only checks `message.attachments` for images, but Discord messages can also contain images via `message.embeds`. Messages with image embeds (e.g., links that Discord auto-embeds as image previews) are incorrectly reported as `has_image=False`. |
| **Log Evidence** | Message `1509036589081432225` has 5 image embeds in `message.embeds` array but `has_image=False` in channel_search results. |
| **Root Cause** | In `channel_search.py`, the `_has_image()` function only checks `message.attachments`: ```python def _has_image(message): return any(f.filename.lower().endswith(('.png', '.jpg', ...)) for f in message.attachments) ``` It does not check `message.embeds` for image embeds. |
| **Discord.py Embed Structure** | Embeds with images have: `embed.type == 'image'` or `embed.thumbnail and embed.thumbnail.url`. The embed array can contain multiple images. |
| **Proposed Fix** | Update `_has_image()` to also check embeds: ```python def _has_image(message): # Check attachments ... # Check embeds for embed in (message.embeds or []): if embed.type == 'image' or (embed.thumbnail and embed.thumbnail.url): return True return False ``` |
| **Files To Modify** | `src/tools/builtins/channel_search.py` → `_has_image()` function |

---

### 🆕 BUG-015: channel_search Rate Limit Exhaustion (Too Many API Calls Per Search)

| Field | Value |
|-------|-------|
| **ID** | BUG-015 |
| **Date** | 2026-05-27 |
| **Status** | 📋 Documented |
| **Severity** | Medium |
| **Description** | Each `channel_search` call makes 16+ Discord API calls: 1 batch fetch (50 messages) + up to 15 individual message fetches for full content. When the model re-calls `channel_search` 3 times (BUG-013), this results in 48+ API calls, accelerating rate limit bucket exhaustion. |
| **Log Evidence** | Rate limit warnings appear after multiple channel_search calls: ```WARNING - Rate limit bucket exhausted: 429 Too Many Request``` |
| **Root Cause** | 1. Each channel_search fetches message bodies individually via `channel.fetch_message()` 2. The model re-calls channel_search instead of using results (BUG-013) 3. No caching of channel_search results to prevent redundant calls |
| **Proposed Fix** | 1. Fix BUG-013 (tool call loop) to prevent redundant calls 2. Add result caching for channel_search with TTL 3. Consider batching message fetches where possible |
| **Files To Modify** | `src/tools/builtins/channel_search.py`, `src/discord_bot/message_processor.py` |

---

### 🆕 BUG-CANCEL-001: Cancellation Feature Not Fully Implemented — Method Name Mismatch

| Field | Value |
|-------|-------|
| **ID** | BUG-CANCEL-001 |
| **Date** | 2026-05-27 |
| **Status** | 📋 Documented |
| **Severity** | High |
| **Description** | The cancellation feature has been partially implemented but contains a critical bug: `bot_core.py` calls `manager.cancel(channel_id)` but `CancellationManager` only has a `request_cancel()` method. This will cause an `AttributeError` when attempting to cancel a session. |
| **Root Cause** | Method name mismatch between `bot_core.py` (which calls `cancel()`) and `CancellationManager` (which defines `request_cancel()`). The `cancel()` method does not exist on `CancellationManager`. |
| **Code Evidence** | `bot_core.py` line 884: `await manager.cancel(channel_id)` — but `CancellationManager` only defines `async request_cancel(self, channel_id: int)` at line ~55. |
| **Fix Required** | Change `manager.cancel(channel_id)` to `await manager.request_cancel(channel_id)` in `bot_core.py` `cancel_session()` method. |
| **Files To Modify** | `src/discord_bot/bot_core.py` → `cancel_session()` method |

---

### 🆕 BUG-CANCEL-002: Cancellation Not Checked During Tool Execution Loop

| Field | Value |
|-------|-------|
| **ID** | BUG-CANCEL-002 |
| **Date** | 2026-05-27 |
| **Status** | 📋 Documented |
| **Severity** | High |
| **Description** | The `message_processor.py` has a `_process_tool_calls_with_status()` method (lines 919-983) that includes cancellation checking at each tool call turn. However, this method is NEVER called — the code directly calls `self._tool_call_handler.process_tool_calls()` instead. This means cancellation is never actually checked during the tool execution loop. |
| **Root Cause** | The `_process_tool_calls_with_status()` method exists but is not wired into the processing pipeline. The main tool execution path uses `self._tool_call_handler.process_tool_calls()` directly without cancellation checks. |
| **Code Evidence** | `message_processor.py` line ~850: `response = await self._tool_call_handler.process_tool_calls(...)` — no use of `_process_tool_calls_with_status()`. |
| **Fix Required** | Replace `self._tool_call_handler.process_tool_calls()` call with `self._process_tool_calls_with_status()` to enable cancellation checking during tool execution. |
| **Files To Modify** | `src/discord_bot/message_processor.py` → main tool execution path |

---

### 🆕 BUG-CANCEL-003: No Cancellation Integration in MessageHandler

| Field | Value |
|-------|-------|
| **ID** | BUG-CANCEL-003 |
| **Date** | 2026-05-27 |
| **Status** | 📋 Documented |
| **Severity** | Medium |
| **Description** | The `message_handler.py` module has no imports or usage of the cancellation module. Neither `handle_new_session()` nor `handle_active_session_batch()` check for cancellation requests during processing. This means even if cancellation is triggered from `bot_core.py`, it won't be checked during message handling. |
| **Root Cause** | `message_handler.py` does not import `get_cancellation_manager()` and does not call `_check_cancellation()` anywhere. |
| **Fix Required** | 1. Add `from src.discord_bot.cancellation import get_cancellation_manager` import. 2. Add cancellation checks in `handle_new_session()` and `handle_active_session_batch()` before and during LM Studio API calls. |
| **Files To Modify** | `src/discord_bot/message_handler.py` |

---

### 🆕 BUG-CANCEL-004: No Discord Command Trigger for Cancellation

| Field | Value |
|-------|-------|
| **ID** | BUG-CANCEL-004 |
| **Date** | 2026-05-27 |
| **Status** | 📋 Documented |
| **Severity** | Medium |
| **Description** | There is no Discord command (e.g., `/cancel` or `!stop`) that users can send to trigger session cancellation. The `cancel_session()` and `cancel_all_sessions()` methods exist in `bot_core.py` but are never called from any Discord message handler. |
| **Root Cause** | The `on_message` handler in `bot_core.py` does not check for cancellation commands before processing messages. |
| **Fix Required** | Add a command check in `_handle_on_message()` to detect `/cancel` or `!stop` commands and call `self.cancel_session(channel_id)`. |
| **Files To Modify** | `src/discord_bot/bot_core.py` → `_handle_on_message()` method |

---

### 🆕 BUG-CANCEL-005: Cancellation Manager Not Imported in bot_core.py

| Field | Value |
|-------|-------|
| **ID** | BUG-CANCEL-005 |
| **Date** | 2026-05-27 |
| **Status** | 📋 Documented |
| **Severity** | Medium |
| **Description** | `bot_core.py` calls `get_cancellation_manager()` in `cancel_session()` (line 876) and `cancellation_manager` property (line 916), but does not import it. This will cause a `NameError` when these methods are called. |
| **Root Cause** | Missing import statement for `get_cancellation_manager` from `src.discord_bot.cancellation`. |
| **Fix Required** | Add `from src.discord_bot.cancellation import get_cancellation_manager` at the top of `bot_core.py`. |
| **Files To Modify** | `src/discord_bot/bot_core.py` → imports section |

---

### ✅ BUG-LOG-001: Terminal Log File Gets Deleted/Cleared During Application Runtime — Solved

| Field | Value |
|-------|-------|
| **ID** | BUG-LOG-001 |
| **Date** | 2026-05-27 |
| **Date Solved** | 2026-05-27 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | The terminal log file (`POC/test1/terminal.log`) was being truncated during application runtime instead of only at startup. When Flask's debug reloader restarted the process, `setup_logging()` was called at module level, which triggered `enable_terminal_log()` and truncated the log file. |
| **Root Cause** | `setup_logging()` was called at module level in `app.py` (line 69), which runs every time the Flask debug reloader spawns a new process. This caused `enable_terminal_log()` to truncate `terminal.log` on every reloader restart. |
| **Fix Applied** | **1. `logger.py`**: Removed the incorrect `max_age_minutes` parameter from `_TeeStream.__init__()` that was previously added. **2. `app.py`**: Moved `setup_logging()` call from module level into the `if __name__ == "__main__":` block. This ensures `setup_logging()` is only called when the app is actually started by the user, not when the reloader spawns a child process. |
| **Files Modified** | `src/logger.py` (removed `max_age_minutes` parameter from `_TeeStream.__init__()`), `src/app.py` (moved `setup_logging()` into `if __name__ == "__main__"` block) |

