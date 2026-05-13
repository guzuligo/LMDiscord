# Discord Bot + LM Studio Integration App - Plan

## Overview
A Python desktop application with a GUI that connects a Discord bot to a local LM Studio instance, enabling AI-powered chat responses with configurable tools.

---

## Project Context (From Test Files)

Based on testing in the `test/` folder, the following has been explored:

1. **test/bot.py** - Basic Discord bot setup using `discord.py` with:
   - Environment variable loading via `python-dotenv`
   - Message content intent enabled
   - Simple keyword-based response ("hello" → "Hello World!")

2. **test/lmTest.py** - LM Studio connection test using:
   - OpenAI Python client pointing to `http://localhost:1234/v1`
   - Basic chat completion with system + user messages
   - Model: `local-model`, max_tokens: 2500, temperature: 0.7

3. **test/lmTest_2.py** - LM Studio tool calling test using:
   - OpenAI-compatible tools API (function calling)
   - Two tools defined: `add_numbers` and `describe_image`
   - Tool execution loop: request → tool_calls → execute → send result → final response
   - Vision/image support: base64 encoding, MIME type handling, image resizing
   - Image processing with Pillow (resize, format conversion, JPEG compression)

4. **test/comfyui_api_client.py** - ComfyUI API client for image generation:
   - Sends workflow JSON to ComfyUI server (`http://localhost:8188`)
   - Polls for completion
   - Downloads generated images

5. **test/comfyui_RefToRef_api.json** - ComfyUI workflow for reference-to-reference image generation using Flux2 model

### Key Takeaways
- User has experience with OpenAI client for LM Studio
- Tool calling / function calling is a core feature needed
- Image processing and vision capabilities are important
- ComfyUI integration (image generation) is a likely tool to expose
- Current `requirements.txt` has: `discord.py`, `python-dotenv`, `Pillow`

---

## Architecture

### High-Level Flow
```
Discord Chat → Bot receives message → Bot sends to LM Studio → 
LM Studio processes with tools → LM Studio returns response → 
Bot posts response to Discord
```

### Component Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                        GUI Application                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Discord     │  │  LM Studio   │  │   Tools          │  │
│  │  Connector   │  │  Connector   │  │   Manager        │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                    │            │
│         ▼                 ▼                    │            │
│  ┌──────────────────────────────────────────────────┐     │
│  │              Discord Bot Module                   │     │
│  │         (discord.py client)                       │     │
│  └────────────────────────┬─────────────────────────┘     │
│                           │                                │
└───────────────────────────┼────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
     ┌────────────────┐          ┌─────────────────┐
     │   Discord API  │          │   LM Studio API  │
     │   (discord.com)│          │  (localhost:1234)│
     └────────────────┘          └─────────────────┘
```

---

## Core Components

### 1. Discord Bot Module (`src/discord_bot.py`)
- Uses `discord.py` library
- Connects/disconnects from Discord
- Listens to chat messages (mentions and replies)
- Forwards messages to LM Studio client for response generation
- Posts LM Studio responses back to Discord chat
- Handles tool call results from LM Studio
- Logs all activities to the GUI log area

**Key Features:**
- Async message handling
- Mention-triggered responses (e.g., `@Bot hello`)
- Reply chains context preservation
- Rate limiting awareness
- Error handling for failed responses

### 2. LM Studio Client Module (`src/lm_studio_client.py`)
- HTTP client to communicate with LM Studio API
- Uses OpenAI-compatible endpoint (`/v1/chat/completions`)
- Configurable hostname and port
- Sends message context and receives AI responses
- Handles tool definitions and tool calls
- Manages conversation history per channel/user

**Key Features:**
- Configurable connection (hostname/port)
- Connect/disconnect with status check
- Async API calls
- Tool call execution coordination
- Conversation state management

### 3. Tools System (`src/tools/`)

#### Tool Registry (`src/tools/registry.py`)
- Central registry of available tools
- Tool registration/unregistration
- Tool enabling/disabling per session

#### Tool Base (`src/tools/base.py`)
- Base class for all tools
- Defines tool interface (name, description, parameters, execute)

### 3a. Session Management Tools (Discord Bot Integrated)

#### Session End Tool (`src/discord_bot.py` - `END_SESSION_TOOL`)
A tool calling-based session management feature where LM Studio autonomously decides when to end sessions.

**How It Works:**
1. **Tool Definition**: `END_SESSION_TOOL` is sent to LM Studio with every request during active sessions
2. **LM Studio Decision**: The language model analyzes conversation context and decides if/when to call `end_session`
3. **Farewell Generation**: LM Studio generates a natural farewell message as part of the tool call
4. **Cleanup**: Bot clears conversation history and session state
5. **Idle State**: Bot stops responding until next mention

**Tool Definition (OpenAI-compatible format):**
```json
{
  "type": "function",
  "function": {
    "name": "end_session",
    "description": "End the current conversation session. Use this when the user wants to leave, say goodbye, end the conversation, or when the conversation is naturally concluding. The model should respond with a farewell message before calling this tool.",
    "parameters": {
      "type": "object",
      "properties": {
        "farewell_message": {
          "type": "string",
          "description": "The farewell/response message to send to the user before ending the session. Should be polite and natural."
        }
      },
      "required": ["farewell_message"]
    }
  }
}
```

**Session Lifecycle:**
```
Idle State → Bot Mentioned → Active Session → LM Studio calls end_session → Farewell Posted → Idle State
    ↑                                                                        ↓
    └────────────── Next mention restarts session ───────────────────────────┘
```

**Implementation Details:**
- `END_SESSION_TOOL`: Class attribute defining the tool in OpenAI-compatible format
- `chat_with_tools()`: Method in `LMStudioClient` that sends tools to LM Studio API
- `use_tool_calling`: Boolean flag to enable/disable tool calling
- `tool_choice: "auto"`: Lets LM Studio decide whether to use tools
- Tool call detection: Bot parses `tool_calls` from response and extracts `farewell_message`
- `clear_session(channel_id)`: Clears conversation history and active session for a channel
- Session auto-expiration after 10 minutes of inactivity (`_session_timeout`)

**Active Session Message Handling:**
- During active session, ALL messages in the channel are sent to LM Studio
- Messages formatted with context:
  - Same user: Direct message content
  - Different user: `"{display_name} says: {content}"`
- LM Studio decides whether to respond based on context
- Empty responses skipped when tool calls are present

#### Built-in Tools (`src/tools/builtins/`)
- `math_calc.py` - Mathematical calculations (add, subtract, multiply, divide)
- `image_describe.py` - Describe images from file paths (vision)
- `web_search.py` - Web search (placeholder/future)
- `comfyui_generate.py` - Trigger ComfyUI image generation


**Tool Definition Format (OpenAI-compatible):**
```json
{
  "type": "function",
  "function": {
    "name": "tool_name",
    "description": "Tool description",
    "parameters": {
      "type": "object",
      "properties": {
        "param_name": {
          "type": "string",
          "description": "Parameter description"
        }
      },
      "required": ["param_name"]
    }
  }
}
```

### 4. Configuration Management (`src/config.py`)
- Load/save configuration from/to JSON file
- Default config file: `config.json` in project root
- Environment variable fallback for sensitive data

**Config Schema:**
```json
{
  "discord": {
    "bot_token": "",
    "app_id": "",
    "public_key": ""
  },
  "lm_studio": {
    "hostname": "localhost",
    "port": 1234,
    "api_endpoint": "/v1/chat/completions"
  },
  "settings": {
    "bot_prefix": "@",
    "max_response_length": 2000,
    "temperature": 0.7,
    "max_tokens": 2500,
    "enabled_tools": ["math_calc", "image_describe"]
  }
}
```

### 5. Web GUI Module (Flask-based)

**Note:** The original plan specified tkinter for the GUI, but tkinter was not available for Python 3.13 on Fedora/Nobara Linux. The project switched to a Flask web-based interface which provides the same functionality with broader compatibility.

#### Main Page (`src/templates/index.html` + `src/static/script.js` + `src/static/styles.css`)
Built with Flask backend and vanilla JavaScript frontend with Catppuccin Mocha dark theme.

**UI Elements:**
| Element | Type | Description |
|---------|------|-------------|
| LM Studio Hostname | Input | Text field for LM Studio hostname |
| LM Studio Port | Input | Text field for LM Studio port (default: 1234) |
| Connect to LM Studio | Button | Establishes connection to LM Studio |
| Disconnect from LM Studio | Button | Closes connection to LM Studio |
| Connect to Discord | Button | Starts the Discord bot |
| Disconnect from Discord | Button | Stops the Discord bot |
| Connection Status | Indicator | Shows current connection states |
| Bot Username | Label | Shows current bot username |

**Tabs:**
| Tab | Description |
|-----|-------------|
| 💬 Chat | Main chat interface with message sending and response display |
| 🔑 Tokens | Token usage statistics with real-time streaming display |
| ⚙️ Settings | Configuration for temperature, max_tokens, max_response_length, system_prompt, message_delay |
| 📝 Logs | Full log history with filtering, color-coding, and unread badge |

#### Debug Panel (`src/templates/debug.html` + `src/static/debug_script.js` + `src/static/debug_styles.css`)
Separate page at `/debug` route with advanced debugging tools.

**Features:**
| Feature | Description |
|---------|-------------|
| Connection Status | Real-time LM Studio + Discord status |
| Session Manager | View/clear active Discord sessions |
| Token Metrics | Token usage stats for Discord bot |
| Settings Override | Quick setting changes with validation |
| LM Studio Override | Host/port inputs for reconnection |
| Diagnostics | Test connections, force disconnect |
| Application Logs | Full log viewer with filtering |

#### API Endpoints (`src/chat_api.py` + `src/discord_api.py`)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message to LM Studio |
| `/api/chat/stream` | POST | SSE stream with token chunks |
| `/api/discord/connect` | POST | Connect Discord bot |
| `/api/discord/disconnect` | POST | Disconnect Discord bot |
| `/api/discord/status` | GET | Get Discord bot status |
| `/api/discord/info` | GET | Get Discord bot info |
| `/api/discord/sessions` | GET | Get active sessions |
| `/api/discord/clear_session` | POST | Clear specific channel session |
| `/api/discord/clear_all_sessions` | POST | Clear all sessions |
| `/api/logs` | GET | Get application logs |
| `/api/logs/clear` | POST | Clear logs |
| `/api/logs/stats` | GET | Get log statistics |
| `/api/settings/temperature` | GET/POST | Get/set temperature |
| `/api/settings/max_tokens` | GET/POST | Get/set max tokens |
| `/api/settings/max_response_length` | GET/POST | Get/set max response length |
| `/api/settings/system_prompt` | GET/POST | Get/set system prompt |
| `/api/settings/delay` | GET/POST | Get/set message delay |
| `/api/tokens/last` | GET | Get last token usage |
| `/api/tokens/reset` | POST | Reset token usage |
| `/api/status` | GET | Get full application status |

### 6. Application Entry Point (`src/app.py`)
- Flask app factory pattern
- Registers blueprints for chat and Discord endpoints
- Loads configuration
- Starts Flask development server

---

## Current File Structure (Flask Web GUI)

```
Project6_Discord_helloWorld/
├── .env.example                     # Environment variable template
├── .gitignore                       # Git ignore rules
├── README.md                        # Project documentation
├── app_Plan.md                      # This plan file
├── requirements.txt                 # Dependencies
│
├── src/
│   ├── __init__.py
│   ├── app.py                       # Flask app factory with Blueprint registration
│   ├── config.py                    # Configuration management with JSON persistence
│   ├── chat_api.py                  # Chat/LM Studio API endpoints (Blueprint)
│   ├── discord_api.py               # Discord API endpoints + thread management (Blueprint)
│   ├── lm_studio_client.py          # LM Studio API communication
│   ├── logger.py                    # Logging utility with in-memory buffer
│   │
│   ├── discord_bot.py               # Backward-compat wrapper (~18 lines)
│   ├── discord_api_client.py        # (if separate Discord API client exists)
│   │
│   ├── discord_bot/                 # Discord bot package (modular design)
│   │   ├── __init__.py
│   │   ├── bot_core.py              # Main DiscordBot class, events, lifecycle
│   │   ├── message_handler.py       # Message processing, LM Studio interaction
│   │   ├── session_manager.py       # Session lifecycle, timeout cleanup
│   │   ├── token_tracker.py         # Token usage tracking per channel
│   │   ├── typing_indicator.py      # Discord typing indicator
│   │   └── delay_processor.py       # Delayed message processing
│   │
│   ├── gui/                         # (Not used - replaced by Flask web UI)
│   │   ├── __init__.py
│   │   └── ...                      # Placeholder for future tkinter GUI
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py                  # Base tool class
│   │   ├── executor.py              # Tool execution handler
│   │   ├── registry.py              # Tool registry
│   │   └── builtins/
│   │       ├── __init__.py
│   │       ├── comfyui_generate.py  # ComfyUI image generation
│   │       ├── image_describe.py    # Image description
│   │       ├── math_calc.py         # Math calculator
│   │       └── memory_tool.py       # Memory save/search
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── memory_manager.py        # Memory management
│   │   └── memorylite.py            # Memory lite client
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── conversation.py          # Conversation state model
│   │   └── session.py               # Session state model
│   │
│   ├── static/
│   │   ├── script.js                # Main page JavaScript
│   │   ├── debug_script.js          # Debug page JavaScript
│   │   ├── styles.css               # Main page CSS (Catppuccin Mocha)
│   │   └── debug_styles.css         # Debug page CSS
│   │
│   └── templates/
│       ├── index.html               # Main page template
│       └── debug.html               # Debug page template
│
└── test/                            # Existing test files (kept)
    ├── bot.py
    ├── lmTest.py
    ├── lmTest_2.py
    ├── comfyui_api_client.py
    ├── comfyui_RefToRef_api.json
    └── output_images/
```

## POC Structure

```
POC/
└── test1/                           # Current active POC (Flask Web GUI)
    ├── plan.md
    ├── implementation_progress.md
    ├── issues_tracker.md
    ├── requirements.txt
    ├── main.py
    ├── README.md
    ├── config_template.json
    ├── config.json
    ├── app.log
    └── src/                         # (same as main src/ above)
```

---

## Dependencies (Updated requirements.txt)

```
# Discord
discord.py>=2.3.2

# Environment
python-dotenv>=1.0.0

# Image Processing
Pillow>=10.0.0

# LM Studio API (OpenAI client)
openai>=1.0.0

# HTTP requests (for ComfyUI and other APIs)
requests>=2.31.0

# GUI (tkinter is built-in, or use customtkinter for modern look)
# customtkinter>=5.2.0   # Optional - uncomment if using
```

---

## Implementation Phases

### Phase 1: Foundation
- [ ] Set up project file structure
- [ ] Create `src/__init__.py`, `src/gui/__init__.py`, `src/tools/__init__.py`, `src/tools/builtins/__init__.py`, `src/models/__init__.py`
- [ ] Implement `src/config.py` - Configuration loading/saving
- [ ] Implement `src/logger.py` - Logging utility
- [ ] Update `requirements.txt`

### Phase 2: Core Modules
- [ ] Implement `src/lm_studio_client.py` - LM Studio API client
- [ ] Implement `src/models/conversation.py` - Conversation state
- [ ] Implement `src/models/message.py` - Message model

### Phase 3: Tools System
- [ ] Implement `src/tools/base.py` - Base tool class
- [ ] Implement `src/tools/registry.py` - Tool registry
- [ ] Implement `src/tools/executor.py` - Tool execution handler
- [ ] Implement `src/tools/builtins/math_calc.py` - Math calculator
- [ ] Implement `src/tools/builtins/image_describe.py` - Image description

### Phase 4: Discord Bot
- [ ] Implement `src/discord_bot.py` - Discord bot with tool support
- [ ] Integrate with LM Studio client
- [ ] Integrate with tools system

### Phase 5: GUI
- [ ] Implement `src/gui/styles.py` - GUI styling
- [ ] Implement `src/gui/config_window.py` - Configuration window
- [ ] Implement `src/gui/main_window.py` - Main window
- [ ] Implement `src/main.py` - Application entry point

### Phase 6: Integration & Testing
- [ ] Wire all components together in `main.py`
- [ ] Test Discord connection flow
- [ ] Test LM Studio connection flow
- [ ] Test tool calling from Discord messages
- [ ] Test configuration persistence
- [ ] Test log display

### Phase 7: Bug Fixes & Improvements (Added 5/11/2026)
- [x] Add 5-second delay before message processing
- [x] Add `show_typing` tool for Discord typing indicator
- [x] Implement multi-turn tool calling
- [x] **ISS-007**: Fix typing indicator - moved to immediate display, fixed discord.py 2.x API (`channel.typing()`), run LM Studio calls in ThreadPoolExecutor
- [x] **ISS-008**: Fix duplicate goodbye message on session end - set `response_text = None` when end_session detected
- [x] **ISS-004**: Fix extra "The session has ended." text in farewell response - ⏳ Requires testing (appears fixed, needs verification)
- [x] **ISS-005**: Add config option to disable Werkzeug HTTP request logging ✅ (suppress_werkzeug_logging setting added)
- [x] **Feature**: Make max_tokens configurable in GUI settings window ✅

### Phase 8: Configuration Enhancements (Added 5/11/2026)
- [x] Add max_tokens input field to config window
- [x] Add temperature input field to config window
- [x] Add max_response_length input field to config window
- [x] Wire GUI inputs to Config class and save to config.json
- [x] Apply settings to Discord bot and LM Studio client dynamically

### Debug Panel (Added 5/12/2026)
- [x] Create separate debug page at `/debug` route
- [x] Create debug_styles.css for debug page styling
- [x] Create debug_script.js for debug page functionality
- [x] Add session management endpoints
- [x] Add diagnostics tools (test connections, force disconnect)
- [x] Add settings override controls
- [x] Add application log viewer with filtering
- [x] Fix missing LM Studio host/port inputs
- [x] Fix log display initialization

### Phase 9: Modular Refactoring (Added 5/12/2026)
- [x] **ISS-014**: Refactor `discord_bot.py` (1077 lines) into 6 focused modules under `src/discord_bot/`
  - `bot_core.py` (~470 lines) - Main DiscordBot class, event registration, lifecycle
  - `message_handler.py` (~546 lines) - Message processing, LM Studio interaction, tool calling
  - `session_manager.py` (~129 lines) - Session lifecycle, timeout cleanup, state queries
  - `token_tracker.py` (~100 lines) - Token usage tracking per channel for web UI sync
  - `typing_indicator.py` (~40 lines) - Discord typing indicator using async typing() context manager
  - `delay_processor.py` (~110 lines) - Delayed message processing for follow-up batching
- [x] `discord_bot.py` now a backward-compat wrapper (~18 lines)
- [x] Package renamed from `discord` to `discord_bot` to avoid naming conflict with discord.py library

### Phase 10: Message Processing Fixes (Added 5/12/2026)
- [x] **ISS-015**: Pending messages not included in LM Studio batch - fixed `extend(pending_messages)` in `handle_active_session_batch()`
- [x] **Context Overflow Fix**: Added history truncation - keeps system prompt + last 20 messages (10 exchanges)
- [x] **Session End Fix**: Added `break` after `end_session` in both inner and outer loops
- [x] **Session Clear Fix**: Added `should_end_session` return value → `bot_core.py` calls `clear_session()` when True
- [x] **Race Condition Fix**: Moved `processing_lock[channel_id] = True` to BEFORE `await asyncio.sleep()` in delay_processor
- [x] **ISS-016**: Queue not checked after new session - added `_process_queued_pending_messages()` call
- [x] **ISS-017**: No typing indicator for queue processing - added typing indicator before queued message processing

### Phase 11: Context Persistence Fix (Added 5/12/2026)
- [x] **ISS-018**: Active session context loss - bot forgets previous messages
  - Root cause: `conversation_history = {channel_id: history}` created new local dict instead of mutating shared one
  - Fix: Changed to `conversation_history[channel_id] = history` and added parameter to method signature
  - Verified: Bot now correctly maintains context within sessions

### Phase 12: Planned Features (Added 5/12/2026)
- [ ] **🆕 Discord Channel Search Tool** - Tool for LM Studio to search Discord channel messages
  - Actions: `search`, `list_channels`, `get_channel_info`, `search_by_user`
  - Configurable scope: `active_channel`, `all_channels`, `specified_channels`
  - Source metadata included in results (channel, author, timestamp, message ID)
  - Disabled by default (`enable_tool: false`)
  - New file: `src/tools/builtins/discord_search.py`
- [ ] **Discord Token Metrics Push to Web UI** - Real-time token sync from Discord bot to web UI
- [ ] **Built-in Tools Integration** - math_calc, image_describe, comfyui_generate, memory_tool
- [ ] **Memory Integration** - memorylite post-session memory creation
- [ ] **Channel Configuration Window** - Per-channel settings UI

### Phase 13: Image Handling Bug Fixes (Added 5/13/2026) - BUG-002
All fixes verified with live testing on Discord (GuzuBot).

### Phase 14: Server Configuration System (Added 5/13/2026) - FEAT-001
- **Status**: 🔄 In Progress
- **Description**: Per-server enable/disable and per-channel allow/deny lists with web UI management
- **User Story**: As an admin, I want to control which Discord servers and channels the bot responds to, so it can be selectively enabled across multiple servers

#### Configuration Structure
```json
{
  "servers": {
    "default": {
      "enabled": true,
      "allowed_channels": [],
      "denied_channels": []
    },
    "123456789012345678": {
      "enabled": true,
      "allowed_channels": ["111111111111111111", "222222222222222222"],
      "denied_channels": ["333333333333333333"]
    },
    "987654321098765432": {
      "enabled": false,
      "allowed_channels": [],
      "denied_channels": []
    }
  }
}
```

#### Configuration Rules
| Rule | Behavior |
|------|----------|
| `enabled: false` | Bot ignores ALL messages from this server |
| `enabled: true`, `allowed_channels: []` (empty) | Bot responds to ALL channels in this server |
| `enabled: true`, `allowed_channels: [...]` (non-empty) | Bot only responds to messages in listed channels |
| `denied_channels: [...]` | Bot ignores messages from these channels (takes precedence over allowed_channels) |
| Server not in config | Default: enabled, all channels allowed |

#### Implementation Plan
| Step | File | Changes |
|------|------|---------|
| 1 | `src/config.py` | Add `servers` section, `is_server_enabled()`, `is_channel_allowed()` methods |
| 2 | `src/discord_bot/bot_core.py` | Add `_check_server_access()` in `on_message` handler |
| 3 | `src/discord_api.py` | Add `GET /api/servers`, `POST /api/servers/update` endpoints |
| 4 | `src/templates/index.html` | Add "Server Config" tab |
| 5 | `src/static/script.js` | Add server config UI logic |
| 6 | `src/static/styles.css` | Add server config panel styling |

#### Web UI Design
```
┌────────────────────────────────────────────────────────────┐
│ 🔧 Server Configuration                                    │
├────────────────────────────────────────────────────────────┤
│ Server ID: [________________]    [🔍 Load Server Info]      │
│                                                            │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ Server: My Discord Server (123456789012345678)         │ │
│ │                                                        │ │
│ │ Enabled:  [●] Yes  [○] No                              │ │
│ │                                                        │ │
│ │ Channel Mode:  [●] All Channels  [○] Specific Only     │ │
│ │                                                        │ │
│ │ Allowed Channels:                                      │ │
│ │ [111111111111111111]                    [➖ Remove]     │ │
│ │ [222222222222222222]                    [➖ Remove]     │ │
│ │ [______________________________]              [➕ Add]   │ │
│ │                                                        │ │
│ │ Denied Channels:                                       │ │
│ │ [333333333333333333]                    [➖ Remove]     │ │
│ │ [______________________________]              [➕ Add]   │ │
│ │                                                        │ │
│ │                        [💾 Save Configuration]          │ │
│ └────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

#### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/servers` | GET | Get all configured servers |
| `/api/servers/<server_id>` | GET | Get specific server config |
| `/api/servers/update` | POST | Update server configuration |
| `/api/servers/add` | POST | Add a new server to config |
| `/api/servers/remove/<server_id>` | DELETE | Remove server from config |

#### Bot Message Handler Changes
```python
async def on_message(self, message):
    # Skip bot's own messages
    if message.author == self.user:
        return
    
    # NEW: Check if server is enabled
    if not self._is_server_enabled(message.guild):
        logger.info(f"Server '{message.guild.name}' is disabled, ignoring message")
        return
    
    # NEW: Check if channel is allowed
    if not self._is_channel_allowed(message.guild.id, message.channel.id):
        logger.info(f"Channel {message.channel.id} not allowed in server {message.guild.id}")
        return
    
    # ... rest of message handling
```

- [x] **BUG-002: Image Describe Breaks Conversation Flow & Causes 400 Errors**
  - **Severity**: Critical
  - **Status**: ✅ Solved & Verified

  #### Fix 2a: System Prompt for Intent-Based Image Tool Usage
  - **Problem**: LM Studio called `image_describe` for ANY image, even casual messages like "Check this out..."
  - **Root Cause**: System prompt told LM Studio to call `image_describe` when images are attached, without distinguishing explicit vs. implicit requests
  - **Fix**: Updated system prompt in `handle_new_session()` to guide LM Studio:
    - "Call this ONLY when the user explicitly asks for an image to be described"
    - "If the user sends an image but does NOT explicitly ask for it to be described, respond naturally"
    - "IMPORTANT: Do not call image_describe for every image"
  - **Files Modified**: `src/discord_bot/message_handler.py` → `handle_new_session()` system prompt

  #### Fix 2b: User-Friendly Blocked Hostname Error Messages
  - **Problem**: Raw security error (`"Security: URL blocked: Hostname 'x' not in allowed hostnames"`) sent to LM Studio → robotic user response
  - **Root Cause**: `ValueError` from `SafeImageDownloader` caught and sent as raw tool result text
  - **Fix**: Replaced with user-friendly message in both `_process_message()` and `_process_active_session()`:
    - "The image URL could not be processed. This may be due to the image being hosted on an unsupported domain, or the URL may not be publicly accessible. Please try using an image from Discord's CDN instead."
  - **Files Modified**: `src/discord_bot/message_handler.py` → ValueError handlers in both processing paths

  #### Fix 2c: Isolated Context Window for Image Describe (Context Overflow Prevention)
  - **Problem**: Image base64 data in conversation history grew to 6917 tokens → LM Studio returned 400 Bad Request → conversation broke
  - **Root Cause**: Full base64 image data included in conversation history on every turn. Current truncation (20 messages) kept too much image data.
  - **Fix (Fix E - Isolated Mini-Context)**:
    1. When `image_describe` tool is called, download and resize the image
    2. Create an ISOLATED mini-context with ONLY the image + "describe this image in detail, up to 3-4 sentences" prompt (no conversation history)
    3. Get the description text from LM Studio using the mini-context
    4. Replace the tool call in the main conversation with the description as plain text: "The image has been described. Here's what was in the image: [description]. Please continue the conversation naturally."
    5. This prevents base64 image data from polluting the main conversation history
  - **Verification**: Live test showed 1160 tokens (well within limits) vs. previous 6917 tokens
  - **Files Modified**: `src/discord_bot/message_handler.py` → image_describe handling in both `_process_message()` and `_process_active_session()`

  #### Fix 2d: discord.py `Attachment.is_image()` Compatibility Fix
  - **Problem**: `WARNING - Error checking if attachment is image: 'Attachment' object has no attribute 'is_image'`
  - **Root Cause**: `is_image()` is a property in discord.py 2.x, not a method. Calling `attachment.is_image()` raises AttributeError.
  - **Fix**: Added `hasattr()` guard in `_extract_image_attachments()`:
    - Checks if `is_image` attribute exists before accessing
    - If callable, calls it; if property, uses it directly
    - Falls back to extension-based detection if attribute doesn't exist
  - **Verification**: Log showed `Debug: attachment ComfyUI_00004_.png is_image=True` with no warnings
  - **Files Modified**: `src/discord_bot/bot_core.py` → `_extract_image_attachments()` method

---

## Design Decisions

1. **GUI Framework**: `tkinter` (built-in, no extra dependency) - can switch to `customtkinter` if modern look is preferred
2. **Async vs Sync**: Discord bot requires async (`discord.py` is async-first), GUI is sync - use threading for GUI updates from async bot
3. **Config Format**: JSON file for flexibility and ease of editing
4. **Tool System**: Plugin-based with registry pattern - easy to add new tools
5. **Logging**: Dual output - GUI log area + file log (`app.log`)
6. **Conversation Context**: Per-channel conversation history maintained by the bot

---

## Session & Memory System

### Reference: memorylite (`/home/user1/Documents/mcp/memorylite.md`, `/home/user1/Documents/mcp/memorylite.py`)
The user has an existing memory system (memorylite) that uses SQLite to store memories for LLM context. It provides:
- Save, search, retrieve, update, delete memories
- Memory types (0-6 built-in, 100+ user-defined)
- Keywords for semantic search
- Related IDs for memory graphs
- MCP server interface

### Session Management
The Discord bot app should have a **session-based architecture**:

#### Session Lifecycle
```
Idle State → Bot Mentioned → Active Session → Session Timeout → Memory Creation → Idle State
```

1. **Idle State** (Default)
   - Bot is connected to Discord but NOT sending messages to LM Studio
   - Bot monitors chat for mentions using Discord API (code-level, NOT LLM)
   - No conversation context maintained for LM Studio
   - Minimal resource usage

2. **Session Start** (Triggered by Bot Mention)
   - When user mentions the bot (e.g., `@Bot hello` or direct reply to bot)
   - Mention detection is done via discord.py code (fast, no LLM needed)
   - Session begins, conversation context initialized
   - Messages start flowing to LM Studio

3. **Active Session**
   - All bot-relevant messages are sent to LM Studio
   - Tools can be called and executed
   - Conversation history is maintained
   - Session timer resets on each interaction

4. **Session Timeout**
   - After a period of inactivity (configurable, e.g., 10 minutes)
   - Session ends automatically
   - Conversation context is flushed from LM Studio

5. **Memory Creation** (Post-Session)
   - Once session ends, a memory creation tool is triggered
   - Summary of the conversation is saved to memorylite SQLite database
   - Keywords extracted for future searchability
   - Memory type assigned (e.g., type=4 for Chat, type=6 for Technical)
   - Memory is stored but does NOT trigger a bot response

6. **Back to Idle**
   - Bot returns to monitoring mode
   - Waits for next mention to start a new session

#### Session State Model (`src/models/session.py`)
```python
class SessionState:
    status: str          # "idle", "active", "ending", "memory_saving"
    last_activity: datetime
    messages: list       # Current session message history
    channel_id: str      # Discord channel where session is active
    user_id: str         # User who started the session
    timeout_minutes: int # Configurable timeout
```

#### Memory Integration
After session ends, the bot should:
1. Compile conversation messages
2. Call a memory tool (either local or via memorylite MCP)
3. Save a summary with appropriate memory_type and keywords
4. Link to previous related memories if any

### Async & Concurrency Handling

#### Core Principle
The GUI must remain **responsive at all times**, even when tools are executing.

#### Message Queue System
- Incoming messages are queued when bot is processing
- Messages during processing are NOT sent to LM Studio immediately
- They are either:
  - Buffered and sent after current response (if short gap)
  - Queued and processed sequentially (if tool is fast)
  - Acknowledged with "I'll get back to you" message (if tool is slow)

#### Tool Execution Strategy

**Category 1: Synchronous Tools** (execute immediately, no concurrency issues)
- Calculator/math tools
- Memory lookup/save tools
- These should block the tool call but not the GUI

**Category 2: Asynchronous Tools** (execute in background, may take time)
- ComfyUI image generation (can take minutes)
- Web search
- Large file processing
- These run in background threads/async tasks
- GUI remains responsive during execution
- LM Studio can still receive responses about tool progress

**Category 3: Duplicate Prevention**
- If a slow tool (e.g., ComfyUI generation) is already running:
  - NEW requests for the SAME tool should be rejected or queued
  - User gets feedback: "Image generation already in progress, please wait..."
  - Prevents resource exhaustion and halting

#### Concurrency Architecture
```
GUI Thread (tkinter)
    │
    ├── Main loop (sync)
    │
    └── Threading for:
         ├── Discord bot event loop (asyncio)
         ├── LM Studio API calls (asyncio)
         ├── Tool execution (thread pool for sync tools)
         ├── Tool execution (async for long-running tools)
         └── GUI log updates (thread-safe queue)
```

**Implementation:**
- Discord bot runs in its own asyncio event loop
- LM Studio client uses async HTTP calls
- GUI updates via `root.after()` for thread safety
- Tool executor uses `concurrent.futures` for mixed sync/async tools
- Message processor uses a semaphore to prevent duplicate tool calls

#### Processing Flow
```
Message Received
    │
    ├─ Is bot being mentioned? ──No──→ Ignore (not our message)
    │       │Yes
    │       ▼
    ├─ Is session active? ──No──→ Start session, process message
    │       │Yes
    │       ▼
    ├─ Is bot processing? ──No──→ Send to LM Studio
    │       │Yes
    │       ▼
    ├─ Queue message (buffer)
    │       │
    │       ▼
    ├─ After current response:
    │   Process queued messages sequentially
    │
    ▼
Send to LM Studio
    │
    ├─ LM Studio calls tool?
    │   │
    │   ├─ Sync tool (calc, memory) → Execute immediately
    │   │
    │   └─ Async tool (comfyui) → Execute in background
    │       │
    │       ├─ Same tool already running? → Reject/Queue
    │       └─ Otherwise → Execute & report progress
    │
    └─ LM Studio returns response
        │
        ├─ Post to Discord
        ├─ Check for new queued messages
        └─ If idle → Start timeout timer
```

---

## Updated File Structure (with Session & Memory)

```
Project6_Discord_helloWorld/
├── main.py                          # Entry point - launches GUI
├── config.json                      # Saved configuration (generated)
├── config_template.json             # Template for config
├── requirements.txt                 # Dependencies
├── README.md                        # Project documentation
├── app Plan.md                      # This plan file
│
├── src/
│   ├── __init__.py
│   ├── main.py                      # GUI application class
│   ├── config.py                    # Configuration management
│   ├── discord_bot.py               # Discord bot with session management
│   ├── lm_studio_client.py          # LM Studio API communication
│   ├── logger.py                    # Logging utility
│   ├── utils.py                     # General helper functions
│   │
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py           # Main GUI window
│   │   ├── config_window.py         # Configuration popup window
│   │   └── styles.py                # GUI styling constants
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py              # Tool registry
│   │   ├── base.py                  # Base tool class
│   │   ├── executor.py              # Tool execution handler (sync/async)
│   │   └── builtins/
│   │       ├── __init__.py
│   │       ├── math_calc.py         # Math calculator tool (sync)
│   │       ├── image_describe.py    # Image description tool (sync)
│   │       ├── memory_tool.py       # Memory save/search tool (sync)
│   │       └── comfyui_generate.py  # ComfyUI generation tool (async)
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── conversation.py          # Conversation state model
│   │   ├── message.py               # Message model
│   │   └── session.py               # Session state management
│   │
│   └── memory/
│       ├── __init__.py
│       ├── memorylite.py            # Memory lite client (copied/adapted)
│       └── memory_manager.py        # Memory management for bot
│
└── test/                            # Existing test files (kept)
    ├── bot.py
    ├── lmTest.py
    ├── lmTest_2.py
    ├── comfyui_api_client.py
    ├── comfyui_RefToRef_api.json
    └── output_images/
```

---

## Updated Dependencies

```
# Discord
discord.py>=2.3.2

# Environment
python-dotenv>=1.0.0

# Image Processing
Pillow>=10.0.0

# LM Studio API (OpenAI client)
openai>=1.0.0

# HTTP requests (for ComfyUI and other APIs)
requests>=2.31.0

# GUI (tkinter is built-in, or use customtkinter for modern look)
# customtkinter>=5.2.0   # Optional - uncomment if using

# Memory (for memorylite integration)
# sqlite3 is built-in, no extra package needed
```

---

## Experimentation Structure (Proof of Concept)

### POC Folder (`POC/`)
The project will use an **experimentation-based approach** for implementation. Each implementation attempt gets its own isolated folder under `POC/`.

> **Note:** The folder is named `POC/` instead of `proof_of_concept/` for brevity.

#### Required POC Files
Each POC folder **MUST** include the following files for proper documentation and tracking:

| File | Required | Purpose |
|------|----------|---------|
| `plan.md` | Yes | Implementation-specific plan and approach |
| `implementation_progress.md` | Yes | Track what's completed, in progress, and not started |
| `issues_tracker.md` | Yes | Document issues faced and their solutions/status |
| `requirements.txt` | Yes | POC-specific dependencies |
| `main.py` | Yes | Entry point for this POC |
| `README.md` | Recommended | Project documentation |

#### Folder Structure
```
POC/
├── README.md                        # Overview of POC approach
├── test1/                           # First attempt: Basic LM Studio Chat (Flask Web)
│   ├── plan.md                      # Implementation-specific plan/notes
│   ├── implementation_progress.md   # Implementation progress tracking
│   ├── issues_tracker.md            # Issues and solutions log
│   ├── requirements.txt             # POC-specific dependencies
│   ├── main.py                      # Entry point for this POC
│   ├── README.md                    # Project documentation
│   ├── config_template.json         # Configuration template
│   └── src/                         # Source code
│       ├── __init__.py
│       ├── app.py                   # Flask web application
│       ├── config.py                # Configuration management
│       ├── lm_studio_client.py      # LM Studio API client
│       ├── templates/
│       │   └── index.html           # Web interface
│       └── ...                      # Other source files
│
├── discord_bot_tkinter/             # Second attempt: Desktop GUI with tkinter
│   ├── plan.md
│   ├── implementation_progress.md
│   ├── issues_tracker.md
│   ├── requirements.txt
│   └── ...
│
├── discord_bot_async/               # Third attempt: Async-focused implementation
│   ├── plan.md
│   ├── implementation_progress.md
│   ├── issues_tracker.md
│   ├── requirements.txt
│   └── ...
│
└── ...                              # More attempts as needed
```

#### POC Workflow
1. **Create a new POC folder** when starting a fresh implementation attempt
    - Name convention: `discord_bot_<approach_name>` or descriptive name
    - **Mandatory files:** `plan.md`, `implementation_progress.md`, `issues_tracker.md`
    - List any special dependencies in `requirements.txt`

2. **Update documentation during implementation**
    - Record all decisions in `plan.md`
    - Update `implementation_progress.md` as components are completed
    - Log any issues in `issues_tracker.md` with status (Open, Solved, Won't Fix)

3. **Full implementation in each folder**
    - Each POC folder contains a complete, runnable implementation
    - Not partial code - each should be testable end-to-end
    - Copy working code to main `src/` folder when validated

4. **Compare and iterate**
    - If POC A fails, create POC B with a different approach
    - Keep failed POCs for reference (don't delete)
    - Mark the best approach in the main `POC/README.md`

5. **Migration to production**
    - Once a POC works well, extract its patterns into the main `src/` structure
    - Refactor as needed to match the final file structure
    - Document lessons learned in the POC's `implementation_progress.md`

#### POC Plan File Template (`proof_of_concept/<name>/plan.md`)
```markdown
# POC: <Name>

## Approach
Describe the implementation approach being tried.

## Key Decisions
- Why this pattern/library?
- What alternatives were considered?

## Testing Steps
1. Test Discord connection
2. Test LM Studio connection
3. Test tool calling
4. Test GUI responsiveness

## Results
[After testing, document what worked and what didn't]

## Lessons Learned
[Document findings for future reference]
```

#### Benefits of This Approach
- **Isolation**: Each attempt is independent, no conflicts between approaches
- **Learning**: Failed attempts still provide valuable lessons
- **Flexibility**: Try completely different patterns without breaking working code
- **Documentation**: Each attempt documents its decisions and outcomes
- **Progressive improvement**: Each new attempt builds on previous learnings

---

## Notes

- Helper functions should be placed in separate files (e.g., `src/utils.py`, `src/logger.py`) for readability
- Each tool should be in its own file under `src/tools/builtins/`
- Files should be kept small and focused on a single responsibility
- Existing test files in `test/` folder should be preserved for reference
- Memory lite (`memorylite.py` and `memorylite.md`) from `/home/user1/Documents/mcp/` should be adapted and placed in `src/memory/`
- Session management is critical - mention detection must be code-level (fast), not LLM-dependent
- GUI responsiveness is paramount - async tools must not block the main thread
- **POC-first approach**: Implement and test in `proof_of_concept/` folders before integrating into `src/`
