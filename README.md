# 🤖 Discord LM Studio Bot

A Discord bot powered by local AI (LM Studio) that provides intelligent chat responses in your Discord server. Features a web-based dashboard for easy configuration and monitoring.

## What It Does

- **AI-Powered Conversations**: Mention the bot in Discord to start chatting with a local AI model
- **Context Awareness**: Remembers conversation context per channel for natural follow-ups
- **Tool Support**: Can calculate math, describe images, search messages, and more
- **Web Dashboard**: Manage everything from a browser — no CLI expertise needed

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Follow detailed setup instructions
# See POC/poc1/README.md for step-by-step guide
```

**Requirements**: Python 3.10+, LM Studio running locally, Discord bot token

📖 **Full setup guide**: [POC/poc1/README.md](POC/poc1/README.md)

## Features

- 💬 Mention-based AI chat responses in Discord
- 🌐 Flask web dashboard at `http://localhost:5000`
- 🔧 Per-server and per-channel access control
- 📊 Real-time token usage monitoring
- ⚙️ Configurable AI parameters (temperature, max tokens, system prompt)
- 🔍 Channel message search, math calculations, image description

## License

Proof-of-concept project.

---
*Built with [Flask](https://flask.palletsprojects.com/), [discord.py](https://github.com/Rapptz/discord.py), and [LM Studio](https://lmstudio.ai/)*