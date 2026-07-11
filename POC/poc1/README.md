# Discord AI Bot

A Discord bot powered by local AI (LM Studio) that provides intelligent chat responses directly in your server. It features a web-based management dashboard for easy configuration and monitoring.

## What It Does

- **AI Chat Responses**: Mention the bot in Discord to get intelligent answers powered by your local LM Studio instance
- **Conversation Memory**: Maintains context per channel so conversations feel natural and continuous
- **Web Dashboard**: Manage everything from your browser at http://localhost:5000
- **Tool Support**: The bot can perform math calculations, describe images, search channel messages, and more

## Quick Start

### Prerequisites

- Python 3.10 or higher
- [LM Studio](https://lmstudio.ai/) running locally with an AI model loaded
- A Discord bot token ([create one at Discord Developer Portal](https://discord.com/developers/applications))

### Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure the bot**:
   ```bash
   cp config_template.json config.json
   ```
   Then edit `config.json` with your Discord bot token and LM Studio connection details.

3. **Set your Discord bot token** (alternative to config.json):
   Create a `.env` file with:
   ```
   DISCORD_BOT_TOKEN=your_discord_bot_token_here
   ```

4. **Start the bot**:
   ```bash
   python src/app.py
   ```

5. **Open the web dashboard**:
   Visit http://localhost:5000 in your browser

## Using the Bot

### In Discord

- **Start a conversation**: Mention the bot in any channel (e.g., `@YourBot hello`)
- **Follow up**: Just reply normally — the bot remembers the conversation
- **End a session**: Say goodbye, and the bot will end the conversation automatically

### Web Dashboard (http://localhost:5000)

| Tab | Description |
|-----|-------------|
| 💬 **Chat** | View and interact with the bot's conversations |
| 🔑 **Tokens** | Monitor AI token usage in real-time |
| 🖥️ **Servers** | Configure which Discord servers and channels the bot responds in |
| ⚙️ **Settings** | Adjust AI response parameters (temperature, max tokens, system prompt) |
| 📝 **Logs** | View application logs with filtering |

## Configuration

Edit `config.json` to customize:

- **Discord credentials**: Bot token, app ID, public key
- **LM Studio connection**: Hostname and port (default: `localhost:1234`)
- **Bot behavior**: Response length, temperature, enabled tools
- **Server access control**: Enable/disable per server or per channel

See `config_template.json` for all available options.

## Available Tools

The bot can use these tools when the AI decides they're relevant:

| Tool | Description |
|------|-------------|
| `math_calc` | Perform mathematical calculations |
| `image_describe` | Describe or analyze images sent in chat |
| `channel_search` | Search through Discord channel messages |
| `context_compress` | Compress long conversation context |
| `memory` | Save and search memories across sessions |

## Troubleshooting

- **"Bot not responding"**: Make sure LM Studio is running and a model is loaded
- **"Token not set"**: Check your `config.json` or `.env` file has the correct bot token
- **Port 5000 already in use**: The web dashboard uses port 5000 by default — change it if needed
- Check `terminal.log` for detailed application logs (auto-created on startup)

## License

This is a proof-of-concept project.