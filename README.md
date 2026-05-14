# 🤖 Discord LM Studio Bot

A Python application that connects a Discord bot to a local LM Studio instance, enabling AI-powered chat responses with configurable tools via a Flask web interface.

## 📦 Prerequisites

- Python 3.8+
- [LM Studio](https://lmstudio.ai/) running locally (default: `http://localhost:1234`)
- A Discord account
- A Discord server where you have admin/moderator permissions

## 🚀 Setup Instructions

### 1. Navigate to the POC Directory

```bash
cd POC/test1
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example environment file and add your bot token:
```bash
cp .env.example .env
```

Edit `.env` and replace `your_bot_token_here` with your actual bot token from the [Discord Developer Portal](https://discord.com/developers/applications/).

### 4. Run the Application

```bash
python main.py
```

Or alternatively:
```bash
python src/app.py
```

You should see:
```
LM Studio Chat POC

Starting web server...
Open your browser and go to: http://localhost:5000
```

### 5. Open the Web Interface

Navigate to `http://localhost:5000` in your browser to access the control panel where you can:
- Connect to LM Studio
- Connect/disconnect the Discord bot
- Chat with the AI directly
- View token metrics
- Configure settings (temperature, max_tokens, system prompt)
- Manage server/channel access

## 🎮 How to Use

1. Start the application (`python main.py`)
2. Open `http://localhost:5000` in your browser
3. Configure LM Studio connection (hostname/port)
4. Click "Connect LM Studio"
5. Configure your Discord bot token in `.env`
6. Click "Connect Discord" to start the bot
7. Mention the bot in Discord to start a conversation

## 📁 Project Structure

```
Project6_Discord_helloWorld/
├── README.md                       # This file
├── app_Plan.md                     # Full architecture plan
├── requirements.txt                # Root dependencies
├── .env.example                    # Environment variables template
│
├── POC/
│   └── test1/                      # Active POC (Flask Web GUI)
│       ├── main.py                 # ✅ Entry point - launches Flask app
│       ├── README.md               # POC-specific documentation
│       ├── requirements.txt        # POC dependencies
│       ├── config_template.json    # Configuration template
│       ├── plan.md                 # POC implementation notes
│       ├── implementation_progress.md  # Progress tracking
│       ├── issues_tracker.md       # Issues log
│       └── src/                    # Source code
│           ├── app.py              # Flask app factory
│           ├── config.py           # Configuration management
│           ├── lm_studio_client.py # LM Studio API client
│           ├── chat_api.py         # Chat/LM Studio endpoints
│           ├── discord_api.py      # Discord endpoints
│           ├── discord_bot/        # Discord bot modules
│           ├── tools/              # Tools system
│           ├── templates/          # HTML templates
│           └── static/             # CSS/JS assets
│
└── test/                           # Basic test files
    ├── bot.py                      # Simple Hello World bot test
    ├── lmTest.py                   # LM Studio connection test
    └── ...                         # Other test utilities
```

## 🔐 Security Note

- **Never commit your `.env` file** to version control
- Keep your `DISCORD_BOT_TOKEN` secret
- The Application ID and Public Key are safe to commit as they are public identifiers

## 📖 Next Steps

Want to expand the bot? Consider adding:
- More built-in tools (math, web search, ComfyUI image generation)
- Memory integration with memorylite
- Slash commands
- Advanced moderation tools

---
*Built with [Flask](https://flask.palletsprojects.com/), [discord.py](https://github.com/Rapptz/discord.py), and [LM Studio](https://lmstudio.ai/)*
