# Discord Bot + LM Studio Integration - POC test1

## Overview
Proof of Concept implementation for a Python application with a **Flask web-based GUI** (http://localhost:5000) that connects a Discord bot to a local LM Studio instance, enabling AI-powered chat responses with configurable tools.

**GUI Type**: Flask web interface (not desktop — uses browser-based UI with HTML/CSS/JavaScript). **Note**: This is NOT a tkinter desktop app; the GUI was migrated from tkinter to Flask due to Python 3.13/Fedora compatibility issues.

## Structure
- `main.py` - Application entry point
- `src/` - Source code modules
- `src/discord_bot/` - Modular Discord bot (6 focused modules)
- `src/tools/` - Tools system (registry, executor, built-in tools)
- `config_template.json` - Configuration template

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Copy `config_template.json` to `config.json` and fill in your values
3. Set `DISCORD_BOT_TOKEN` in `.env` file
4. Run: `python src/app.py`
5. Open http://localhost:5000 in browser

## Features
- Discord bot with mention-triggered responses
- LM Studio integration via OpenAI-compatible API
- Tool calling system (context_compress, image_compare, channel_search, math_calculate, comfyui_generate*)
- Flask web interface with Chat, Tokens, **Servers**, Settings, Logs tabs
- **ComfyUI Generate***: Stub tool registered but not implemented (TODO placeholder)
- **Server Configuration System** (FEAT-001 + UX-001): Per-server enable/disable and per-channel allow/deny lists
  - **Auto-discovery**: Click "📡 Load Servers from Discord" to browse servers the bot is connected to
  - **Quick-add servers**: Select a server from dropdown and add it to config instantly
  - **Server names**: Servers displayed with human-readable names (e.g., "My Server (123456789012345678)")
  - **Channel auto-discovery**: Click "🔍 Load Channels from Discord" when editing a server
  - **Channel names**: Channels displayed with names (e.g., "#general (111111111111111111)")
  - **Quick-add channels**: Select channels from dropdown to add to allowed/denied lists
- Debug panel at /debug route
- Session-based conversation management
- Message queuing during processing
- Configurable settings (temperature, max_tokens, delay, system prompt)
- Safe image download with hostname whitelist
- Token metrics streaming display
- **Terminal Log (terminal.log)**: Auto-generated log file that mirrors ALL terminal output exactly (via stdout + stderr redirection), cleared on app startup for easy debugging sharing. Just tell me to check `terminal.log` and I can read it directly.

## Recent Features (5/14/2026 - UX-001)
- **Server Config Auto-Discovery**: Added auto-discovery of Discord servers and channels
  - Backend: `get_guilds_info()` and `get_guild_channels()` methods in `bot_core.py`
  - API: `/api/discord/servers` and `/api/discord/channels/<guild_id>` endpoints
  - Frontend: Auto-discovery UI with server/channel dropdown pickers
  - Server list now shows names alongside IDs
  - Channel list now shows names alongside IDs

## Known Limitations
- **ComfyUI Generate Tool (comfyui_generate)**: Registered in the tool system but NOT implemented. The file `src/tools/builtins/comfyui_generate.py` contains only TODO comments (28 lines). A working reference implementation exists at `helloworlds/comfyui_api_client.py`.
- **Image Compare**: Uses LM Studio vision model for visual analysis, NOT algorithmic comparison (no SSIM/MSE/pixel-level diff). Single image = description, multiple images = LM-based visual comparison.
- **Context Compression Auto-Trigger**: Configuration settings exist (`context_compression_enabled`, `context_token_threshold`, `context_message_threshold`) but the auto-trigger logic is NOT wired into the message processing loop. The tool is available for manual LM calls but won't auto-fire.

## Recent Features (5/13/2026 - FEAT-001)
- **Server Configuration System**: Per-server enable/disable and per-channel allow/deny lists
  - Web UI "Servers" tab for managing server configurations
  - Config methods: `is_server_enabled()`, `is_channel_allowed()`, `set_server_config()`
  - API endpoints: `/api/servers`, `/api/servers/update`, `/api/servers/add_channel`, `/api/servers/remove_channel`, `/api/servers/remove`
  - Bot automatically skips messages from disabled servers or non-allowed channels
  - Configuration stored in `config.json` under `servers` section

## Recent Fixes (5/13/2026 - BUG-002)
- **Fix 2a**: System prompt updated for intent-based image tool usage
- **Fix 2b**: User-friendly blocked hostname error messages
- **Fix 2c**: Isolated mini-context for image describe (prevents context overflow, 1160 tokens vs 6917)
- **Fix 2d**: discord.py 2.x `is_image()` compatibility fix

## Testing Results
- ✅ Flask server starts on port 5000
- ✅ Discord bot connects and responds to mentions
- ✅ LM Studio integration for AI-powered responses
- ✅ Session-based conversation context per channel
- ✅ LM Studio tool calling (end_session, image_describe)
- ✅ Message queuing during processing
- ✅ All BUG-002 fixes verified with live testing
- ✅ Terminal log (terminal.log) auto-created and mirrors terminal output exactly (stdout + stderr)

## Feature Requests
### FEAT-003: Debug Mode Flag for Logging
- **Problem**: Verbose DEBUG-level logs (discord.py HTTP traces, urllib3 connection details) appear on every startup even when not debugging
- **Request**: Add `--debug` CLI flag or `DEBUG_MODE` config option to control logging verbosity
  - Debug mode: `logging.basicConfig(level=logging.DEBUG)` — full verbose output
  - Normal mode: `logging.basicConfig(level=logging.INFO)` — suppress library DEBUG output
