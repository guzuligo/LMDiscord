"""
Test script to search real Discord channel for images.
Connects to the Discord server and tests the has: image operator.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

import discord

async def test_real_search():
    """Connect to Discord and search the general channel for images."""
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("ERROR: DISCORD_BOT_TOKEN not found in .env file")
        return
    
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        print(f"Connected as: {client.user}")
        print(f"In {len(client.guilds)} guilds")
        
        # Find the general channel
        general_channel = None
        for guild in client.guilds:
            print(f"\nGuild: {guild.name} (ID: {guild.id})")
            for channel in guild.text_channels:
                print(f"  Channel: #{channel.name} (ID: {channel.id})")
                if channel.name == "general":
                    general_channel = channel
        
        if not general_channel:
            print("\nERROR: No #general channel found")
            await client.close()
            return
        
        print(f"\nSearching channel: #{general_channel.name} (ID: {general_channel.id})")
        
        # Fetch recent messages and check for images
        print("\n--- Fetching 20 most recent messages ---")
        messages = []
        async for msg in general_channel.history(limit=20, oldest_first=False):
            messages.append(msg)
        
        print(f"\nTotal messages fetched: {len(messages)}")
        
        # Count messages with images
        image_count = 0
        for msg in messages:
            has_image = False
            image_urls = []
            for attachment in msg.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    has_image = True
                    image_urls.append(attachment.url)
                    image_count += 1
            
            for embed in msg.embeds:
                if embed.type == "image" and embed.url:
                    has_image = True
                    image_urls.append(embed.url.split('?')[0])
                    image_count += 1
                if embed.thumbnail and embed.thumbnail.url:
                    has_image = True
                    image_urls.append(embed.thumbnail.url.split('?')[0])
                if embed.image and embed.image.url:
                    has_image = True
                    image_urls.append(embed.image.url.split('?')[0])
            
            if has_image:
                print(f"\n  [IMAGE] {msg.author.name}: {msg.content[:80]}")
                for url in image_urls:
                    print(f"    URL: {url[:100]}...")
        
        print(f"\n--- Summary ---")
        print(f"Total messages: {len(messages)}")
        print(f"Messages with images: {image_count}")
        
        # Now test the has: image operator by simulating the search
        print("\n--- Testing has: image operator ---")
        # Simulate what the ChannelSearchTool would do
        from datetime import datetime, timezone
        
        # Build message dicts like the bot does
        message_dicts = []
        for msg in messages:
            has_image = False
            image_urls = []
            attachments = []
            for attachment in msg.attachments:
                url = str(attachment.url)
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    image_urls.append(url)
                    has_image = True
                else:
                    attachments.append(attachment.filename)
            
            for embed in msg.embeds:
                if embed.type == "image" and embed.url:
                    embed_url = embed.url.split('?')[0]
                    image_urls.append(embed_url)
                    has_image = True
                if embed.thumbnail and embed.thumbnail.url:
                    thumb_url = embed.thumbnail.url.split('?')[0]
                    image_urls.append(thumb_url)
                if embed.image and embed.image.url:
                    img_url = embed.image.url.split('?')[0]
                    image_urls.append(img_url)
            
            message_dicts.append({
                "message_id": str(msg.id),
                "channel_id": str(msg.channel.id),
                "guild_id": str(msg.guild.id) if msg.guild else None,
                "author": msg.author.name,
                "display_name": msg.author.display_name or msg.author.name,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat(),
                "is_reply": False,
                "replied_to_author": None,
                "replied_to_content": None,
                "has_image": has_image,
                "has_embeds": len(msg.embeds) > 0,
                "image_urls": image_urls,
                "attachments": attachments,
            })
        
        # Apply has: image filter (what the tool does - UPDATED to check embeds too)
        filtered = []
        for m in message_dicts:
            has_image_attachments = m.get("has_image", False)
            has_embeds = m.get("has_embeds", False)
            has_image_urls = bool(m.get("image_urls", []))
            match = has_image_attachments or (has_embeds and has_image_urls)
            if match:
                filtered.append(m)
        print(f"Messages matching 'has: image' (with embed fix): {len(filtered)}")
        
        # Print the filtered results
        for m in filtered:
            print(f"  - {m['author']} ({m['display_name']}): {m['content'][:60]}")
            print(f"    has_image={m['has_image']}, image_urls={len(m['image_urls'])}")
        
        print("\n--- Test complete ---")
        await client.close()
    
    try:
        await client.start(token)
    except discord.errors.LoginFailure as e:
        print(f"Login failed: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_real_search())