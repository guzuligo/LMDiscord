"""
CDN URL Refresher Module

Provides shared functionality to refresh expired Discord CDN attachment URLs
by fetching fresh URLs from the Discord API.

Discord attachment URLs contain time-limited tokens that expire quickly.
This module extracts channel_id and message_id from CDN URLs and fetches
fresh proxy URLs via the Discord API.

URL pattern:
https://cdn.discordapp.com/attachments/{channel_id}/{message_id}/{filename}?...
https://media.discordapp.net/attachments/{channel_id}/{message_id}/{filename}?...
"""

import logging
import re
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# Regex pattern to extract channel_id and message_id from Discord CDN attachment URLs
# Pattern: https://cdn.discordapp.com/attachments/{channel_id}/{message_id}/{filename}?...
#          https://media.discordapp.net/attachments/{channel_id}/{message_id}/{filename}?...
CDN_ATTACHMENT_PATTERN = re.compile(
    r'(?:cdn\.discordapp\.com|media\.discordapp\.net)/attachments/(\d+)/(\d+)/'
)


def _extract_channel_message_from_url(url: str) -> Optional[tuple]:
    """Extract (channel_id, message_id) from a Discord CDN attachment URL.

    Args:
        url: The CDN URL to parse

    Returns:
        Tuple of (channel_id, message_id) as integers, or None if extraction fails
    """
    if not url or not isinstance(url, str):
        return None
    match = CDN_ATTACHMENT_PATTERN.search(url)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def _is_expired_cdn_url(url: str) -> bool:
    """Check if a CDN URL contains expired expiration parameters.

    Discord attachment URLs contain time-limited tokens like ?ex=6a167da7&is=6a152c27&hm=...

    Args:
        url: The CDN URL to check

    Returns:
        True if the URL appears to contain expiration parameters
    """
    if not url or not isinstance(url, str):
        return False
    return '?ex=' in url or '?is=' in url


async def refresh_cdn_url(bot_instance: Any, cdn_url: str) -> Optional[str]:
    """Fetch a fresh image URL from Discord API when the cached CDN URL has expired.

    Since Discord CDN URLs expire very quickly, this function always attempts to
    refresh the URL via the Discord API before downloading.

    Strategy:
    1. Extract channel_id and message_id from the CDN URL
    2. Use client.get_channel(id) for fast cache-based lookup
    3. Fallback to guild iteration if channel not in cache
    4. Fetch the message via Discord API — returns fresh attachment URLs

    Args:
        bot_instance: Reference to the DiscordBot instance (must have client attribute)
        cdn_url: The CDN URL to refresh

    Returns:
        Fresh proxy URL from Discord API, or None if fetch fails.
    """
    extracted = _extract_channel_message_from_url(cdn_url)
    if not extracted:
        logger.debug(f"Cannot extract channel/message IDs from CDN URL: {cdn_url[:80]}...")
        return None

    channel_id, message_id = extracted

    try:
        # Strategy 1: Direct cache lookup via client.get_channel() (fastest)
        channel = bot_instance.client.get_channel(channel_id)

        # Strategy 2: Fallback — iterate guilds if channel not in cache
        if channel is None and hasattr(bot_instance, 'client') and bot_instance.client:
            for guild in bot_instance.client.guilds:
                if guild is None:
                    continue
                channel = guild.get_channel(channel_id) or getattr(guild, 'get_text_channel', lambda x: None)(channel_id)
                if channel:
                    break

        if channel is None:
            logger.debug(f"Channel {channel_id} not accessible (not in cache or guild iteration), skipping fresh URL fetch")
            return None

        if not hasattr(channel, 'fetch_message'):
            logger.debug(f"Channel {channel_id} does not support fetch_message")
            return None

        # Fetch the message via Discord API — returns fresh attachment URLs
        message = await channel.fetch_message(message_id)
        if message and hasattr(message, 'attachments') and message.attachments:
            # Try to match by filename first
            url_parts = cdn_url.split('/')
            original_filename = url_parts[-1].split('?')[0] if url_parts else ""

            for attachment in message.attachments:
                if hasattr(attachment, 'filename') and attachment.filename:
                    if attachment.filename == original_filename:
                        fresh_url = attachment.url
                        logger.info(f"Fresh CDN URL obtained for {original_filename}")
                        return fresh_url

            # If no filename match, return the first attachment URL
            fresh_url = message.attachments[0].url
            logger.info(f"Fresh CDN URL obtained (first attachment) for message {message_id}")
            return fresh_url

        logger.debug(f"No attachments found in message {message_id}")
        return None

    except Exception as e:
        logger.warning(f"Error refreshing CDN URL for message {message_id}: {e}")
        return None


async def refresh_all_cdn_urls(bot_instance: Any, image_urls: List[str]) -> List[str]:
    """Refresh multiple CDN URLs via Discord API.

    For each URL, attempts to fetch a fresh URL from the Discord API.

    Args:
        bot_instance: Reference to the DiscordBot instance
        image_urls: List of CDN URLs to refresh

    Returns:
        List of refreshed URLs (original URL kept if refresh fails)
    """
    if not image_urls:
        return []

    refreshed = []
    for url in image_urls:
        fresh_url = await refresh_cdn_url(bot_instance, url)
        if fresh_url:
            logger.info(f"CDN URL refreshed: {url[:60]}... -> {fresh_url[:60]}...")
            refreshed.append(fresh_url)
        else:
            logger.debug(f"Could not refresh URL, keeping original: {url[:60]}...")
            refreshed.append(url)

    return refreshed


async def refresh_image_attachments(bot_instance: Any, image_attachments: List[Dict]) -> List[Dict]:
    """Refresh expired image URLs in an attachment list via Discord API.

    Args:
        bot_instance: Reference to the DiscordBot instance
        image_attachments: List of image attachment dicts with 'url' key

    Returns:
        Updated list of image attachments with fresh URLs where possible
    """
    if not image_attachments:
        return image_attachments

    refreshed = []
    for att in image_attachments:
        url = att.get("url", "")
        fresh_url = await refresh_cdn_url(bot_instance, url)
        if fresh_url:
            logger.info(f"Image URL refreshed: {url[:60]}... -> {fresh_url[:60]}...")
            refreshed.append({
                "url": fresh_url,
                "filename": att.get("filename", "unknown"),
                "is_image": True
            })
        else:
            refreshed.append(att)

    return refreshed