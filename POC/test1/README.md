# Discord Bot + LM Studio Integration - POC test1

## Overview
Proof of Concept implementation for a Python desktop application with a GUI that connects a Discord bot to a local LM Studio instance, enabling AI-powered chat responses with configurable tools.

**Current GUI**: Flask web-based interface (http://localhost:5000) — switched from tkinter due to Python 3.13/Fedora compatibility.

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
- Tool calling system (end_session, image_describe)
- Flask web interface with Chat, Tokens, **Servers**, Settings, Logs tabs
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

## Recent Features (5/14/2026 - UX-001)
- **Server Config Auto-Discovery**: Added auto-discovery of Discord servers and channels
  - Backend: `get_guilds_info()` and `get_guild_channels()` methods in DiscordBot class
  - API: `/api/discord/servers` and `/api/discord/channels/<guild_id>` endpoints
  - Frontend: Auto-discovery UI with server/channel dropdown pickers
  - Server list now shows names alongside IDs
  - Channel list now shows names alongside IDs

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