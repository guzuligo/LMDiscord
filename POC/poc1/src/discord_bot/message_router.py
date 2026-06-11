"""
Message Router Module

Handles Discord message routing logic:
- Incoming message handling (_handle_on_message)
- New session message handling (_handle_new_session_message)
- Active session batch processing (_process_active_session_batch)
- Queued pending messages processing (_process_queued_pending_messages)
- Image attachment extraction (_extract_image_attachments)
- Display name resolution (_get_display_name_for_user)
"""

import asyncio
import logging
import re
from typing import Dict, List, Any, Optional, Tuple

import discord

logger = logging.getLogger(__name__)

# Regex pattern to extract channel_id and message_id from Discord CDN attachment URLs
# Pattern: https://cdn.discordapp.com/attachments/{channel_id}/{message_id}/{filename}?...
CDN_ATTACHMENT_PATTERN = re.compile(
    r'cdn\.discordapp\.com/attachments/(\d+)/(\d+)/'
)

# Regex pattern to extract Discord message jump links from message content
# Supports both discord.com and discordapp.com domains
# Pattern examples:
#   https://discord.com/channels/123456789/123456789/987654321
#   https://discordapp.com/channels/123456789/123456789/987654321
#   https://discord.com/channels/@me/123456789/987654321  (DMs)
#   https://discord.com/channels/@guild/123456789/987654321  (guild context)
MESSAGE_LINK_PATTERN = re.compile(
    r'discord(app)?\.com/channels/(?:@(?:me|guild)/|(\d+)/)(\d+)/(\d+)'
)


def _extract_message_ids_from_link(link: str) -> Optional[Tuple[int, int]]:
    """Extract (channel_id, message_id) from a Discord message jump link.

    Discord message jump links follow the pattern:
    https://discord.com/channels/{guild_id}/{channel_id}/{message_id}
    https://discord.com/channels/@me/{channel_id}/{message_id}  (DMs)
    https://discord.com/channels/@guild/{channel_id}/{message_id}  (guild context)

    For direct server channels (no @me/@guild), the first group is guild_id,
    second is channel_id, third is message_id.

    Args:
        link: The Discord message URL or any string containing one.

    Returns:
        Tuple of (channel_id, message_id) or None if extraction fails.
    """
    if not link or not isinstance(link, str):
        return None

    match = MESSAGE_LINK_PATTERN.search(link)
    if not match:
        return None

    # Groups:
    # For https://discord.com/channels/123/456/789:
    #   group(1) = guild_id (123), group(2) = channel_id (456), group(3) = message_id (789)
    # For https://discord.com/channels/@me/456/789:
    #   group(1) = None, group(2) = channel_id (456), group(3) = message_id (789)
    channel_id_str = match.group(2)
    message_id_str = match.group(3)

    if channel_id_str and message_id_str:
        return int(channel_id_str), int(message_id_str)

    return None


def _is_expired_cdn_url(url: str) -> bool:
    """Check if a CDN URL contains expired expiration parameters.

    Discord attachment URLs contain time-limited tokens like ?ex=6a167da7&is=6a152c27&hm=...
    These tokens expire and the underlying images may be removed from CDN entirely.

    Args:
        url: The CDN URL to check

    Returns:
        True if the URL appears to contain expired expiration parameters
    """
    if not url or not isinstance(url, str):
        return False
    # Check for expiration-related query parameters
    return '?ex=' in url or '?is=' in url


def _extract_channel_message_from_url(url: str) -> Optional[Tuple[str, str]]:
    """Extract (channel_id, message_id) from a Discord CDN attachment URL.

    Discord attachment URLs follow the pattern:
    https://cdn.discordapp.com/attachments/{channel_id}/{message_id}/{filename}

    Args:
        url: The CDN URL to parse

    Returns:
        Tuple of (channel_id, message_id) or None if extraction fails
    """
    if not url or not isinstance(url, str):
        return None
    match = CDN_ATTACHMENT_PATTERN.search(url)
    if match:
        return match.group(1), match.group(2)
    return None


class MessageRouter:
    """Routes incoming Discord messages to appropriate handlers."""

    def __init__(
        self,
        bot_instance: Any,
        session_manager: Any,
        processing_lock: Dict[int, bool],
        pending_messages: Dict[int, List[Dict[str, str]]],
        conversation_history: Dict[int, List[Dict[str, str]]],
        typing_indicator: Any,
        delay_processor: Any,
        lm_studio_lock: Any,
        config: Any = None
    ):
        """Initialize message router.

        Args:
            bot_instance: Reference to the DiscordBot instance
            session_manager: SessionManager instance
            processing_lock: Dict tracking processing state per channel
            pending_messages: Dict of queued messages per channel
            conversation_history: Dict of conversation history per channel
            typing_indicator: TypingIndicator instance
            delay_processor: DelayProcessor instance
            lm_studio_lock: Asyncio lock for LM Studio API calls
            config: Config instance for server configuration
        """
        self._bot = bot_instance
        self._session_manager = session_manager
        self._processing_lock = processing_lock
        self._pending_messages = pending_messages
        self._conversation_history = conversation_history
        self._typing_indicator = typing_indicator
        self._delay_processor = delay_processor
        self._lm_studio_lock = lm_studio_lock
        self._config = config

    async def _fetch_fresh_image_url(self, cdn_url: str) -> Optional[str]:
        """Fetch a fresh image URL from Discord API when the cached CDN URL has expired.

        When Discord attachment URLs expire (contain ?ex=, ?is= tokens), the underlying
        images may be removed from CDN entirely. This method fetches fresh proxy URLs
        by calling the Discord API to retrieve the message object.

        Discord attachment URLs follow the pattern:
        https://cdn.discordapp.com/attachments/{channel_id}/{message_id}/{filename}

        Strategy:
        1. Extract channel_id and message_id from the CDN URL
        2. Use client.get_channel(id) for fast cache-based lookup
        3. Fallback to guild iteration if channel not in cache
        4. Fetch the message via Discord API — returns fresh attachment URLs

        Args:
            cdn_url: The expired CDN URL

        Returns:
            Fresh proxy URL from Discord API, or None if fetch fails.
        """
        # Extract channel_id and message_id from the URL
        extracted = _extract_channel_message_from_url(cdn_url)
        if not extracted:
            logger.debug(f"Cannot extract channel/message IDs from CDN URL: {cdn_url[:80]}...")
            return None

        channel_id_str, message_id_str = extracted
        channel_id = int(channel_id_str)
        message_id = int(message_id_str)

        try:
            # Strategy 1: Direct cache lookup via client.get_channel() (fastest)
            channel = self._bot.client.get_channel(channel_id)

            # Strategy 2: Fallback — iterate guilds if channel not in cache
            if channel is None:
                for guild in self._bot.client.guilds:
                    if guild is None:
                        continue
                    channel = guild.get_channel(channel_id) or guild.get_text_channel(channel_id)
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

        except discord.NotFound:
            logger.warning(f"Message {message_id} not found in channel {channel_id}")
            return None
        except discord.Forbidden:
            logger.warning(f"No permission to fetch message {message_id} in channel {channel_id}")
            return None
        except Exception as e:
            logger.warning(f"Error fetching fresh URL for message {message_id}: {e}")
            return None

    async def _refresh_expired_image_urls(self, image_attachments: List[Dict]) -> List[Dict]:
        """Refresh expired image URLs in an attachment list via Discord API.

        For each image attachment that contains expired CDN parameters,
        attempt to fetch a fresh URL from the Discord API.

        Args:
            image_attachments: List of image attachment dicts with 'url' key

        Returns:
            Updated list of image attachments with fresh URLs where possible
        """
        if not image_attachments:
            return image_attachments

        refreshed = []
        for att in image_attachments:
            url = att.get("url", "")
            if _is_expired_cdn_url(url):
                logger.info(f"Detected expired CDN URL, fetching fresh URL: {url[:80]}...")
                fresh_url = await self._fetch_fresh_image_url(url)
                if fresh_url:
                    logger.info(f"URL refreshed: {url[:60]}... -> {fresh_url[:60]}...")
                    refreshed.append({
                        "url": fresh_url,
                        "filename": att.get("filename", "unknown"),
                        "is_image": True
                    })
                else:
                    # Keep original URL as fallback - it may still work
                    logger.warning(f"Could not refresh URL, keeping original: {url[:60]}...")
                    refreshed.append(att)
            else:
                refreshed.append(att)

        return refreshed

    def get_display_name_for_user(
        self,
        author_nick: Optional[str],
        author_display: str,
        author_name: str
    ) -> str:
        """Get the best name to use when addressing this user.

        Priority: per-server nickname > display name > username.

        Args:
            author_nick: Per-server nickname (can be None)
            author_display: Global display name
            author_name: Discord username (stable)

        Returns:
            The best name to address this user by
        """
        if author_nick:
            return author_nick
        if author_display and author_display != author_name:
            return author_display
        return author_name

    async def extract_image_attachments(self, message: Any) -> List[Dict]:
        """Extract image attachments from a Discord message.

        After extracting attachments, checks for expired CDN URLs and attempts
        to refresh them via the Discord API by fetching fresh proxy URLs.

        Args:
            message: Discord message object

        Returns:
            List of dicts with keys: url, filename, is_image
        """
        attachments = []

        try:
            # Check message attachments
            if hasattr(message, 'attachments'):
                att_list = message.attachments
                if att_list:
                    for attachment in att_list:
                        try:
                            if hasattr(attachment, 'is_image'):
                                is_img = attachment.is_image if hasattr(attachment.is_image, '__call__') else attachment.is_image
                            else:
                                is_img = False
                                if attachment.filename:
                                    ext = attachment.filename.lower().split('.')[-1]
                                    is_img = ext in ('png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp')
                            logger.info(f"Debug: attachment {attachment.filename} is_image={is_img}")
                            if is_img:
                                attachments.append({
                                    "url": attachment.url,
                                    "filename": attachment.filename,
                                    "is_image": True
                                })
                                logger.info(f"Found image attachment: {attachment.filename} ({attachment.url})")
                        except Exception as e:
                            logger.warning(f"Error checking if attachment is image: {e}")
                            if attachment.filename:
                                ext = attachment.filename.lower().split('.')[-1]
                                if ext in ('png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'):
                                    attachments.append({
                                        "url": attachment.url,
                                        "filename": attachment.filename,
                                        "is_image": True
                                    })
                                    logger.info(f"Found image attachment (by extension): {attachment.filename}")

        except Exception as e:
            logger.warning(f"Error extracting attachments: {e}")

        # Check embedded images (embeds can contain images)
        try:
            if hasattr(message, 'embeds') and message.embeds:
                for embed in message.embeds:
                    if hasattr(embed, 'thumbnail') and embed.thumbnail and hasattr(embed.thumbnail, 'url') and embed.thumbnail.url:
                        url = embed.thumbnail.url
                        if url not in [a["url"] for a in attachments]:
                            attachments.append({
                                "url": url,
                                "filename": embed.thumbnail.filename or "thumbnail",
                                "is_image": True
                            })
                    if hasattr(embed, 'image') and embed.image and hasattr(embed.image, 'url') and embed.image.url:
                        url = embed.image.url
                        if url not in [a["url"] for a in attachments]:
                            attachments.append({
                                "url": url,
                                "filename": embed.image.filename or "embed_image",
                                "is_image": True
                            })
        except Exception as e:
            logger.warning(f"Error extracting embed images: {e}")

        # Refresh expired CDN URLs via Discord API
        if attachments:
            attachments = await self._refresh_expired_image_urls(attachments)

        return attachments

    async def extract_images_from_message_links(
        self,
        message_content: str,
        channel_id: int,
        message: Any
    ) -> List[Dict]:
        """Extract image attachments from Discord message jump links in message content.

        Parses Discord message URLs from the content, fetches each referenced message
        via the Discord API, and extracts image attachments from them.

        Args:
            message_content: The raw message content that may contain Discord message links
            channel_id: The current channel ID (used to find the guild for fetching messages)
            message: The current Discord message object (used to access the guild)

        Returns:
            List of dicts with keys: url, filename, is_image
        """
        if not message_content or not isinstance(message_content, str):
            return []

        images = []
        seen_message_ids = set()

        # Find all Discord message links in the content
        matches = MESSAGE_LINK_PATTERN.finditer(message_content)
        for match in matches:
            channel_id_str = match.group(3)
            message_id_str = match.group(4)

            if not channel_id_str or not message_id_str:
                continue

            target_channel_id = int(channel_id_str)
            target_message_id = int(message_id_str)

            # Skip if we already processed this message ID
            if target_message_id in seen_message_ids:
                continue
            seen_message_ids.add(target_message_id)

            try:
                # Determine which channel to fetch from:
                # If the link points to the current channel, use current channel
                # Otherwise, try to find the channel in the guild
                if target_channel_id == channel_id:
                    fetch_channel = message.channel
                else:
                    # Try to get the channel from the guild
                    guild = message.guild
                    if guild:
                        fetch_channel = guild.get_channel(target_channel_id)
                    else:
                        # DM message - try to get from client
                        fetch_channel = message.client.get_channel(target_channel_id)

                if fetch_channel is None:
                    logger.debug(f"Could not find channel {target_channel_id} for message link")
                    continue

                if not hasattr(fetch_channel, 'fetch_message'):
                    logger.debug(f"Channel {target_channel_id} does not support fetch_message")
                    continue

                # Fetch the referenced message
                ref_msg = await fetch_channel.fetch_message(target_message_id)
                if ref_msg is None:
                    logger.warning(f"Message {target_message_id} not found in channel {target_channel_id}")
                    continue

                # Extract images from the referenced message using the full
                # extract_image_attachments() which includes CDN URL refresh
                # logic — critical for message links whose URLs may have
                # expired since the original message was sent.
                ref_images = await self.extract_image_attachments(ref_msg)
                if ref_images:
                    logger.info(f"Extracted {len(ref_images)} image(s) from message link (message {target_message_id})")
                    images.extend(ref_images)

            except discord.NotFound:
                logger.warning(f"Message {target_message_id} not found (404) in channel {target_channel_id}")
            except discord.Forbidden:
                logger.warning(f"No permission to fetch message {target_message_id} in channel {target_channel_id}")
            except Exception as e:
                logger.warning(f"Error extracting images from message link (channel={target_channel_id}, msg={target_message_id}): {e}")

        return images

    async def _extract_images_from_message(self, message: Any) -> List[Dict]:
        """DEPRECATED — Use extract_image_attachments() instead.

        This method exists for backward compatibility but is no longer used
        in the message link flow. The extract_image_attachments() method
        provides the same functionality with added CDN URL refresh support.

        Args:
            message: Discord message object

        Returns:
            List of dicts with keys: url, filename, is_image
        """
        attachments = []

        try:
            # Check message attachments
            if hasattr(message, 'attachments'):
                att_list = message.attachments
                if att_list:
                    for attachment in att_list:
                        try:
                            if hasattr(attachment, 'is_image'):
                                is_img = attachment.is_image if hasattr(attachment.is_image, '__call__') else attachment.is_image
                            else:
                                is_img = False
                                if attachment.filename:
                                    ext = attachment.filename.lower().split('.')[-1]
                                    is_img = ext in ('png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp')
                            if is_img:
                                attachments.append({
                                    "url": attachment.url,
                                    "filename": attachment.filename,
                                    "is_image": True
                                })
                        except Exception as e:
                            logger.warning(f"Error checking if attachment is image: {e}")
                            if attachment.filename:
                                ext = attachment.filename.lower().split('.')[-1]
                                if ext in ('png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'):
                                    attachments.append({
                                        "url": attachment.url,
                                        "filename": attachment.filename,
                                        "is_image": True
                                    })

        except Exception as e:
            logger.warning(f"Error extracting attachments: {e}")

        # Check embedded images (embeds can contain images)
        try:
            if hasattr(message, 'embeds') and message.embeds:
                for embed in message.embeds:
                    if hasattr(embed, 'thumbnail') and embed.thumbnail and hasattr(embed.thumbnail, 'url') and embed.thumbnail.url:
                        url = embed.thumbnail.url
                        if url not in [a["url"] for a in attachments]:
                            attachments.append({
                                "url": url,
                                "filename": embed.thumbnail.filename or "thumbnail",
                                "is_image": True
                            })
                    if hasattr(embed, 'image') and embed.image and hasattr(embed.image, 'url') and embed.image.url:
                        url = embed.image.url
                        if url not in [a["url"] for a in attachments]:
                            attachments.append({
                                "url": url,
                                "filename": embed.image.filename or "embed_image",
                                "is_image": True
                            })
        except Exception as e:
            logger.warning(f"Error extracting embed images: {e}")

        return attachments

    async def handle_on_message(self, message: Any) -> None:
        """Handle incoming Discord messages.

        Args:
            message: The discord.Message object
        """
        # Ignore bot's own messages
        if message.author == self._bot.client.user:
            return

        # Only process when LM Studio client is available and connected
        if not self._bot.lm_studio_client or not self._bot.lm_studio_client.is_connected:
            return

        # Server/Channel Access Control
        channel_id = message.channel.id if hasattr(message.channel, 'id') else None
        if not channel_id:
            return

        # Skip if guild is None (DM messages - still allow them)
        if message.guild is None:
            guild_id = "dm"
            guild_name = "DM"
        else:
            guild_id = str(message.guild.id)
            guild_name = message.guild.name

            # Check if server is enabled
            if self._config and not self._config.is_server_enabled(guild_id):
                logger.info(f"🚫 Server '{guild_name}' ({guild_id}) is disabled, ignoring message")
                return

            # Debug: Log channel filtering details
            if self._config:
                server_config = self._config.get_server_config(guild_id)
                logger.info(f"🔍 Channel filter debug for guild={guild_id} ({guild_name}), channel={channel_id} ({message.channel.name if hasattr(message.channel, 'name') else 'DM'}):")
                logger.info(f"   allowed_channels={server_config.get('allowed_channels', [])}")
                logger.info(f"   denied_channels={server_config.get('denied_channels', [])}")
                is_allowed = self._config.is_channel_allowed(guild_id, str(channel_id))
                logger.info(f"   is_channel_allowed({channel_id}) = {is_allowed}")
                if not is_allowed:
                    logger.info(f"🚫 Channel '{message.channel.name}' ({channel_id}) not allowed in server '{guild_name}', ignoring message")
                    return
            else:
                logger.info(f"⚠️ No config available, skipping channel filter for channel={channel_id}")

        # Extract image attachments from message (async - refreshes expired CDN URLs)
        message_content = (message.content or "").strip()
        image_attachments = await self.extract_image_attachments(message)

        # Extract images from Discord message jump links in message content
        message_link_images = await self.extract_images_from_message_links(
            message_content, channel_id, message
        )
        if message_link_images:
            logger.info(f"Extracted {len(message_link_images)} image(s) from message links in content")
            # Merge with existing image attachments (avoid duplicates by URL)
            existing_urls = {a["url"] for a in image_attachments}
            for img in message_link_images:
                if img["url"] not in existing_urls:
                    image_attachments.append(img)
                    existing_urls.add(img["url"])

        # If processing, queue the message (active sessions only)
        if self._processing_lock.get(channel_id, False):
            if self._session_manager.is_active(channel_id):
                if channel_id not in self._pending_messages:
                    self._pending_messages[channel_id] = []
                author_name = message.author.name
                author_display = message.author.display_name
                author_nick = message.author.nick
                message_content = (message.content or "").strip()
                session_user = self._session_manager.get_user(channel_id)
                if author_name == session_user:
                    formatted_content = message_content
                else:
                    formatted_content = f"{author_display} says: {message_content}"

                pending_data = {
                    "author_name": author_name,
                    "author_display": author_display,
                    "author_nick": author_nick,
                    "content": message_content,
                    "formatted_content": formatted_content,
                    "image_attachments": image_attachments
                }
                self._pending_messages[channel_id].append(pending_data)
                logger.info(f"Queued message from {author_display} for channel {channel_id} "
                           f"(queue size: {len(self._pending_messages[channel_id])})")
                if image_attachments:
                    logger.info(f"  Queued {len(image_attachments)} image attachment(s)")
            return

        author_name = message.author.name
        author_display = message.author.display_name
        author_nick = message.author.nick
        user_id = str(message.author.id)
        message_content = (message.content or "").strip()

        # Check for mention or reply
        mention_str = f"<@{self._bot.client.user.id}>"
        mention_str_alt = f"<@!{self._bot.client.user.id}>"
        is_mention = mention_str in message_content or mention_str_alt in message_content
        is_reply_to_bot = False
        reply_context = None

        # Extract image attachments from the referenced message if this is a reply
        referenced_image_attachments = []
        if message.reference and message.reference.message_id:
            try:
                referenced_msg = await message.channel.fetch_message(message.reference.message_id)
                if referenced_msg:
                    if referenced_msg.author == self._bot.client.user:
                        is_reply_to_bot = True
                    ref_author = referenced_msg.author.display_name or referenced_msg.author.name
                    ref_content = (referenced_msg.content or "").strip()
                    if len(ref_content) > 500:
                        ref_content = ref_content[:497] + "..."
                    reply_context = f"{ref_author}: {ref_content}"
                    logger.info(f"Reply context extracted: {reply_context[:80]}...")

                    # Extract image attachments from the referenced message
                    referenced_images = await self._extract_images_from_message(referenced_msg)
                    if referenced_images:
                        # Refresh any expired CDN URLs in referenced message images
                        referenced_images = await self._refresh_expired_image_urls(referenced_images)
                        referenced_image_attachments = referenced_images
                        logger.info(f"Extracted {len(referenced_images)} image(s) from referenced message")
            except discord.NotFound:
                pass
            except discord.Forbidden:
                logger.warning("No permission to fetch referenced message for reply context")

        # Merge images from current message and referenced message
        all_image_attachments = list(image_attachments)
        if referenced_image_attachments:
            # Avoid duplicates by URL
            existing_urls = {a["url"] for a in all_image_attachments}
            for ref_img in referenced_image_attachments:
                if ref_img["url"] not in existing_urls:
                    all_image_attachments.append(ref_img)
            logger.info(f"Total image attachments: {len(all_image_attachments)} ({len(image_attachments)} from current message, {len(referenced_image_attachments)} from referenced message)")

        # Case 1: Active session - process with delay
        if self._session_manager.is_active(channel_id):
            await self._typing_indicator.show(message.channel)
            if all_image_attachments:
                logger.info(f"Message has {len(all_image_attachments)} image attachment(s) in active session")
            if reply_context:
                logger.info(f"Active session reply context: {reply_context[:80]}...")
            asyncio.create_task(
                self._delay_processor.process_active_session_with_delay(
                    message=message,
                    content=message_content,
                    channel_id=channel_id,
                    author_name=author_name,
                    author_display=author_display,
                    processing_lock=self._processing_lock,
                    pending_messages=self._pending_messages,
                    handler_callback=self._process_active_session_batch,
                    delay=None,
                    image_attachments=all_image_attachments,
                    reply_context=reply_context
                )
            )

        # Case 2: New session - respond to mentions/replies immediately
        elif is_mention or is_reply_to_bot:
            actual_content = message_content
            if is_mention:
                actual_content = message_content.replace(mention_str, "").replace(mention_str_alt, "").strip()

            await self._typing_indicator.show(message.channel)
            if all_image_attachments:
                logger.info(f"Message has {len(all_image_attachments)} image attachment(s) in new session")
            if reply_context:
                logger.info(f"New session reply context: {reply_context[:80]}...")
            asyncio.create_task(
                self._handle_new_session_message(
                    message, actual_content, "mention", channel_id, author_name,
                    author_display, author_nick, user_id,
                    image_attachments=all_image_attachments,
                    reply_context=reply_context
                )
            )

    async def _handle_new_session_message(
        self,
        message: Any,
        content: str,
        message_type: str,
        channel_id: int,
        author_name: str,
        author_display: str,
        author_nick: Optional[str],
        user_id: str,
        image_attachments: Optional[List[Dict]] = None,
        reply_context: Optional[str] = None
    ) -> None:
        """Handle a new session message.

        Args:
            message: Discord message object
            content: Message content
            message_type: 'mention' or 'reply'
            channel_id: Discord channel ID
            author_name: Author's Discord username
            author_display: Author's Discord display name
            author_nick: Author's per-server nickname
            user_id: Author's Discord user ID
            image_attachments: List of image attachment dicts
            reply_context: String with the referenced message content
        """
        self._processing_lock[channel_id] = True
        try:
            logger.info(f"[{message_type}] @{author_name} (display: {author_display}, "
                       f"nick: {author_nick or '(none)'}, id: {user_id}): {content[:50]}...")
            if image_attachments:
                logger.info(f"  Message has {len(image_attachments)} image attachment(s)")

            # Start session with full identity info for memory tracking
            self._session_manager.start_session(
                channel_id, author_name,
                user_id=user_id,
                author_display=author_display,
                initial_nick=author_nick,
                guild_id=str(message.guild.id) if message.guild else "dm"
            )

            # Inject wake-up memory into system prompt
            await self._bot._on_session_started(channel_id, user_id, author_name)

            # Handle via message handler and capture result
            result = await self._bot._message_handler.handle_new_session(
                message=message,
                content=content,
                message_type=message_type,
                channel_id=channel_id,
                author_name=author_name,
                author_display=author_display,
                author_nick=author_nick,
                user_id=user_id,
                conversation_history=self._conversation_history,
                typing_callback=self._typing_indicator.show,
                on_message_callback=self._bot._on_message_callback,
                image_attachments=image_attachments,
                reply_context=reply_context
            )

            # Check if processing was interrupted by a pending message
            if isinstance(result, dict) and result.get("interrupted", False):
                pending_msg = result.get("pending_message")
                if pending_msg:
                    logger.info(f"New session interrupted by pending message from {pending_msg.get('author_display', 'unknown')}")
                    self._processing_lock[channel_id] = False
                    queued_attachments = pending_msg.get("image_attachments", [])
                    await self._handle_new_session_message(
                        message,
                        pending_msg["content"],
                        pending_msg.get("message_type", "mention"),
                        channel_id,
                        pending_msg["author_name"],
                        pending_msg["author_display"],
                        pending_msg.get("author_nick"),
                        pending_msg.get("user_id", ""),
                        image_attachments=queued_attachments
                    )
                    return

            # Store token usage if available
            usage = result.get("usage") if isinstance(result, dict) else None
            if usage:
                self._bot._token_tracker.store_token_usage(channel_id, usage)
        finally:
            self._processing_lock[channel_id] = False

        # Check for queued messages after new session completes
        await self._process_queued_pending_messages(channel_id, message)

    async def _process_active_session_batch(
        self,
        message: Any,
        content: str,
        channel_id: int,
        author_name: str,
        author_display: str,
        author_nick: Optional[str],
        pending_messages: List[Dict[str, str]],
        image_attachments: Optional[List[Dict]] = None,
        reply_context: Optional[str] = None
    ) -> None:
        """Process active session message batch.

        Args:
            message: Discord message object
            content: Main message content
            channel_id: Discord channel ID
            author_name: Author's Discord username
            author_display: Author's Discord display name
            author_nick: Author's current per-server nickname
            pending_messages: List of pending message dicts
            image_attachments: List of image attachment dicts
            reply_context: String with the referenced message content
        """
        try:
            # Get session info for identity tracking
            session_info = self._session_manager.get_session(channel_id) or {}
            initial_nick = session_info.get("initial_nick")
            session_user = session_info.get("author_name") or author_name

            # Determine if nickname has changed since session start
            nick_changed = author_nick and initial_nick and author_nick != initial_nick
            display_changed = author_display != session_info.get("initial_display", author_display)

            # Handle via message handler
            result = await self._bot._message_handler.handle_active_session_batch(
                message=message,
                content=content,
                channel_id=channel_id,
                author_name=author_name,
                author_display=author_display,
                author_nick=author_nick,
                initial_nick=initial_nick,
                session_user=session_user,
                pending_messages=pending_messages,
                conversation_history=self._conversation_history,
                typing_callback=self._typing_indicator.show,
                on_message_callback=self._bot._on_message_callback,
                image_attachments=image_attachments,
                nick_changed=nick_changed,
                display_changed=display_changed,
                reply_context=reply_context
            )

            # Check if processing was interrupted by a pending message
            if isinstance(result, dict) and result.get("interrupted", False):
                pending_msg = result.get("pending_message")
                if pending_msg:
                    logger.info(f"Active session interrupted by pending message from {pending_msg.get('author_display', 'unknown')}")
                    self._processing_lock[channel_id] = False
                    queued_attachments = pending_msg.get("image_attachments", [])
                    await self._process_active_session_batch(
                        message,
                        pending_msg["content"],
                        channel_id,
                        pending_msg["author_name"],
                        pending_msg["author_display"],
                        pending_msg.get("author_nick"),
                        [],
                        image_attachments=queued_attachments
                    )
                    return

            # Update session activity after successful processing
            self._session_manager.update_activity(channel_id)

            # Get result data
            usage = result.get("usage") if isinstance(result, dict) else None
            message_handler_should_end_session = result.get("should_end_session", False) if isinstance(result, dict) else False

            # Store token usage if available
            if usage:
                self._bot._token_tracker.store_token_usage(channel_id, usage)

            # Clear session if LM Studio requested end_session
            if message_handler_should_end_session:
                self._bot.clear_session(channel_id)
                logger.info(f"Session cleared for channel {channel_id} after end_session")

            # Clear lock and process queued messages
            self._processing_lock[channel_id] = False

            # Process any new queued messages
            await self._process_queued_pending_messages(channel_id, message)

        except Exception as e:
            logger.error(f"Error in active session processing: {e}", module="bot_core", exc_info=True)
            self._processing_lock[channel_id] = False
            try:
                await message.channel.send("Sorry, I encountered an unexpected error.")
            except Exception:
                pass

    async def _process_queued_pending_messages(self, channel_id: int, message: Any) -> None:
        """Process queued pending messages after posting a response.

        Shows a typing indicator before processing queued messages.

        Args:
            channel_id: Discord channel ID
            message: Discord message object (for channel reference)
        """
        pending = self._pending_messages.pop(channel_id, [])
        if not pending:
            logger.info(f"No queued messages for channel {channel_id}")
            return

        logger.info(f"Processing {len(pending)} queued message(s) for channel {channel_id}")

        # Show typing indicator before processing queued messages
        await self._typing_indicator.show(message.channel)

        self._processing_lock[channel_id] = True

        first_pending = pending[0]
        queued_attachments = first_pending.get("image_attachments", [])
        await self._process_active_session_batch(
            message,
            first_pending["content"],
            channel_id,
            first_pending["author_name"],
            first_pending["author_display"],
            first_pending.get("author_nick"),
            pending[1:],
            image_attachments=queued_attachments
        )