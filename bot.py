import os
import discord
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the bot token from environment variables
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not TOKEN:
    raise ValueError("No DISCORD_BOT_TOKEN found in .env file")

# Configure intents to read message content
intents = discord.Intents.default()
intents.message_content = True

# Create the Discord client
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    """Called when the bot is ready and connected to Discord."""
    print(f'✅ {client.user} has connected to Discord!')
    print(f'📖 Application ID: {os.getenv("DISCORD_APP_ID")}')

@client.event
async def on_message(message):
    """Called when a message is sent in any server the bot can see."""
    # Ignore messages from the bot itself to prevent infinite loops
    if message.author == client.user:
        return

    # Reply with "Hello World!" if the message is exactly "hello" (case-insensitive)
    if message.content.lower() == 'hello':
        await message.channel.send('Hello World!')

# Run the bot
if __name__ == '__main__':
    client.run(TOKEN)
