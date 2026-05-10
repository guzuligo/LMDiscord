# 🤖 Discord Hello World Bot

A basic Discord bot that replies with "Hello World!" when it receives a "hello" message.

## 📦 Prerequisites

- Python 3.8+
- A Discord account
- A Discord server where you have admin/moderator permissions

## 🚀 Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy the example environment file and add your bot token:
```bash
cp .env.example .env
```

Edit `.env` and replace `your_bot_token_here` with your actual bot token from the [Discord Developer Portal](https://discord.com/developers/applications/1502925472353488906).

### 3. Run the Bot
```bash
python bot.py
```

You should see:
```
✅ HelloWorldBot#1234 has connected to Discord!
📖 Application ID: 1502925472353488906
```

## 🎮 How to Test

1. Go to your Discord server
2. Type `hello` in any text channel the bot can access
3. The bot will reply with `Hello World!`

## 📁 Project Structure

```
Project6_Discord_helloWorld/
├── bot.py              # Main bot code
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## 🔐 Security Note

- **Never commit your `.env` file** to version control
- Keep your `DISCORD_BOT_TOKEN` secret
- The Application ID and Public Key are safe to commit as they are public identifiers

## 📖 Next Steps

Want to expand your bot? Consider adding:
- Slash commands (`/ping`, `/roll`, etc.)
- Reactions and embeds
- External API integrations
- Database connectivity
- Advanced moderation tools

---
*Built with [discord.py](https://github.com/Rapptz/discord.py)*
