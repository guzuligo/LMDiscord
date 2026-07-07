"""
Test script to search real Discord channel with combined operators.
Tests: has: image from: guzu
"""
import asyncio
import os
import sys
import re
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

import discord

OPERATOR_PATTERN = re.compile(
    r'(has|from|in|after|before):\s*(\S+)',
    re.IGNORECASE
)

def parse_operators(query):
    """Parse search operators from a query string."""
    operators = {}
    remaining = query
    for match in OPERATOR_PATTERN.finditer(query):
        op_name = match.group(1).lower()
        op_value = match.group(2)
        if op_name == "has":
            op_value = op_value.lower()
        operators[op_name] = op_value
    remaining = OPERATOR_PATTERN.sub('', query).strip()
    remaining = ' '.join(remaining.split())
    return operators, remaining

async def test_real_search():
    """Connect to Discord and test combined operators."""
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
        
        # Find the general channel
        general_channel = None
        for guild in client.guilds:
            for channel in guild.text_channels:
                if channel.name == "general":
                    general_channel = channel
        
        if not general_channel:
            print("ERROR: No #general channel found")
            await client.close()
            return
        
        # Fetch recent messages
        print("\n--- Fetching 50 most recent messages ---")
        messages = []
        async for msg in general_channel.history(limit=50, oldest_first=False):
            messages.append(msg)
        
        print(f"Total messages fetched: {len(messages)}")
        
        # Build message dicts
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
        
        # Test 1: has: image
        print("\n=== Test 1: has: image ===")
        filtered = [m for m in message_dicts if m.get("has_image", False)]
        print(f"Messages with images: {len(filtered)}")
        
        # Test 2: from: guzu
        print("\n=== Test 2: from: guzu ===")
        filtered_from = [m for m in message_dicts 
                        if m.get("author", "").lower() == "guzu" 
                        or m.get("display_name", "").lower() == "guzu"]
        print(f"Messages from 'guzu': {len(filtered_from)}")
        
        # Test 3: has: image from: guzu (combined)
        print("\n=== Test 3: has: image from: guzu ===")
        filtered_combined = [m for m in message_dicts 
                            if m.get("has_image", False) 
                            and (m.get("author", "").lower() == "guzu" 
                                 or m.get("display_name", "").lower() == "guzu")]
        print(f"Messages with images from 'guzu': {len(filtered_combined)}")
        for m in filtered_combined:
            print(f"  - {m['author']}: {m['content'][:60]}")
        
        # Test 4: Parse the query string
        print("\n=== Test 4: Query parsing ===")
        test_queries = [
            "has: image from: guzu",
            "has: image from: @general mannequin",
            "has: image from: BotGuzu mannequin",
            "mannequin",
        ]
        for q in test_queries:
            ops, remaining = parse_operators(q)
            print(f"  Query: '{q}'")
            print(f"    Operators: {ops}")
            print(f"    Remaining: '{remaining}'")
        
        # Test 5: Simulate the full tool flow
        print("\n=== Test 5: Full tool simulation ===")
        search_query = "has: image from: guzu"
        operators, remaining_text = parse_operators(search_query)
        has_filter = operators.get("has", "").lower()
        from_filter = operators.get("from", "").strip()
        
        print(f"  has_filter: '{has_filter}'")
        print(f"  from_filter: '{from_filter}'")
        print(f"  remaining_text: '{remaining_text}'")
        
        # Apply filters
        result = message_dicts
        if has_filter:
            if has_filter == "image":
                result = [m for m in result if m.get("has_image", False)]
        if from_filter:
            result = [m for m in result 
                     if m.get("author", "").lower() == from_filter.lower()
                     or m.get("display_name", "").lower() == from_filter.lower()]
        if remaining_text:
            search_term = remaining_text.lower()
            result = [m for m in result if search_term in m.get("content", "").lower()]
        
        print(f"\n  Final results: {len(result)} messages")
        for m in result:
            print(f"    - {m['author']}: {m['content'][:60]}")
            print(f"      has_image={m['has_image']}, image_urls={len(m['image_urls'])}")
        
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