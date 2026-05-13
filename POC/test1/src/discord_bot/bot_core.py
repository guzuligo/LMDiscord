"""
Bot Core Module

Main DiscordBot class that integrates all sub-modules:
- SessionManager
- TokenTracker
- TypingIndicator
- DelayProcessor
- MessageHandler

This module handles Discord connection lifecycle and event registration.
"""

import os
import asyncio
import logging
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Callable, Dict, List, Any
from datetime import datetime

import discord
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import sub-modules
from src.discord_bot.session_manager import SessionManager
from src.discord_bot.token_tracker import TokenTracker
from src.discord_bot.typing_indicator import TypingIndicator
from src.discord_bot.delay_processor import DelayProcessor
from src.discord_bot.message_handler import MessageHandler

# Import tools
from src.tools.registry import ToolRegistry
from src.tools.builtins.image_describe import ImageDescribeTool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DiscordBot:
    """Discord bot with LM Studio integration for AI-powered responses.
    
    This is the main bot class that integrates all sub-modules for
    modular, maintainable Discord bot functionality.
    """

    def __init__(self, token: Optional[str] = None, lm_studio_client: Optional[Any] = None,
                 system_prompt: str = "You are a helpful assistant in a Discord server.",
                 temperature: float = 0.7, max_tokens: int = 2500,
                 use_tool_calling: bool = True, message_delay: int = 5,
                 config: Optional[Any] = None):
        """Initialize the Discord bot.

        Args:
            token: Discord bot token. If None, loads from environment.
            lm_studio_client: LMStudioClient instance for AI responses.
            system_prompt: System prompt to send to LM Studio.
            temperature: Temperature for LM Studio responses.
            max_tokens: Max tokens for LM Studio responses.
            use_tool_calling: Whether to use LM Studio's tool calling.
            message_delay: Delay in seconds before processing messages (default: 5).
            config: Config instance for server configuration (FEAT-001).
        """
        self._config = config
        self.token = token or os.getenv("DISCORD_BOT_TOKEN")
        if not self.token:
            raise ValueError("Discord bot token is required. Set DISCORD_BOT_TOKEN in .env file.")

        self.lm_studio_client = lm_studio_client
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.use_tool_calling = use_tool_calling
        self.message_delay = message_delay

        # Create sub-modules
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._session_manager = SessionManager(timeout_seconds=600)
        self._token_tracker = TokenTracker()
        self._typing_indicator = TypingIndicator()
        self._delay_processor = DelayProcessor(default_delay=message_delay)
        # Set up tool registry and register built-in tools
        self._tool_registry = ToolRegistry()
        self._image_describe_tool = ImageDescribeTool()
        self._tool_registry.register(self._image_describe_tool)
        
        # Get tool definitions for LM Studio
        self._tool_definitions = self._tool_registry.get_all_definitions()
        # Add end_session tool to the list
        self._tool_definitions.append(MessageHandler.END_SESSION_TOOL)

        # Get allowed image hostnames from config (will be passed via config)
        allowed_hostnames = []
        if hasattr(lm_studio_client, 'config') and lm_studio_client.config:
            allowed_hostnames = lm_studio_client.config.allowed_image_hostnames if hasattr(lm_studio_client.config, 'allowed_image_hostnames') else []
        
        self._message_handler = MessageHandler(
            lm_studio_client=lm_studio_client,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            use_tool_calling=use_tool_calling,
            tools=self._tool_definitions,
            executor=self._executor,
            allowed_image_hostnames=allowed_hostnames
        )

        # Discord client setup
        self.intents = discord.Intents.default()
        self.intents.message_content = True
        self.intents.guilds = True
        self.client = discord.Client(intents=self.intents)

        # State
        self._is_connected = False
        self._on_message_callback: Optional[Callable] = None
        self._on_status_change_callback: Optional[Callable] = None

        # Conversation history: channel_id -> list of messages
        self._conversation_history: Dict[int, List[Dict[str, str]]] = {}
        # Processing lock: channel_id -> bool
        self._processing_lock: Dict[int, bool] = {}
        # Pending messages queue: channel_id -> list of message dicts
        self._pending_messages: Dict[int, List[Dict[str, str]]] = {}

        # Register events
        self._register_events()

    # --- Event Registration ---

    def _register_events(self) -> None:
        """Register Discord event handlers."""

        @self.client.event
        async def on_ready():
            """Called when the bot is ready and connected."""
            self._is_connected = True
            logger.info(f"Bot connected as {self.client.user}")
            logger.info(f"Bot is in {len(self.client.guilds)} guilds")

            # Start session cleanup task
            asyncio.create_task(self._session_manager.cleanup_expired())

            # CRITICAL: Update Discord status global directly here.
            # The callback mechanism can fail silently because:
            # 1. The callback is an async function defined in a different thread
            # 2. asyncio.create_task() swallows exceptions if no exception handler is set
            # 3. The global variable update may not persist if the task fails
            # By updating here, we ensure the status is set regardless of callback issues.
            try:
                import importlib
                import sys
                # Import the discord_api module to update the global variable
                discord_api = sys.modules.get('src.discord_api')
                if discord_api is None:
                    # Try alternative import path
                    discord_api = sys.modules.get('discord_api')
                if discord_api is not None:
                    discord_api.discord_connected = True
                    discord_api.discord_status_message = str(self.client.user)
                    logger.info(f"Status updated via on_ready: connected=True, status={self.client.user}")
                else:
                    # Fallback: try direct import (less reliable)
                    from src.discord_api import discord_connected as _dc
                    logger.warning("discord_api module not found in sys.modules, callback will handle status update")
                    # Fall through to callback below
                    if self._on_status_change_callback:
                        asyncio.create_task(
                            self._on_status_change_callback("connected", str(self.client.user))
                        )
            except Exception as e:
                logger.error(f"Failed to update Discord status in on_ready: {e}", exc_info=True)
                # Last resort: try callback
                if self._on_status_change_callback:
                    asyncio.create_task(
                        self._on_status_change_callback("connected", str(self.client.user))
                    )

        @self.client.event
        async def on_message(message):
            """Called when a message is received."""
            try:
                await self._handle_on_message(message)
            except Exception as e:
                logger.error(f"Error in on_message handler: {e}", exc_info=True)

        @self.client.event
        async def on_error(event, *args, **kwargs):
            """Handle Discord errors."""
            logger.error(f"Discord error in {event}: {args}")

    def _extract_image_attachments(self, message) -> list:
        """Extract image attachments from a Discord message.
        
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
                logger.info(f"Debug: message.attachments = {att_list} (type: {type(att_list)})")
                if att_list:
                    for attachment in att_list:
                        try:
                            # Fix 2d: Use hasattr() guard for is_image() compatibility
                            # discord.py 2.x has is_image() as a property, not a method
                            if hasattr(attachment, 'is_image'):
                                is_img = attachment.is_image if hasattr(attachment.is_image, '__call__') else attachment.is_image
                            else:
                                # Fallback: check filename extension
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
                            # Fallback: check filename extension
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
                    # Check thumbnail
                    if hasattr(embed, 'thumbnail') and embed.thumbnail and hasattr(embed.thumbnail, 'url') and embed.thumbnail.url:
                        url = embed.thumbnail.url
                        if url not in [a["url"] for a in attachments]:
                            attachments.append({
                                "url": url,
                                "filename": embed.thumbnail.filename or "thumbnail",
                                "is_image": True
                            })
                    # Check image
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

    async def _handle_on_message(self, message) -> None:
        """Handle incoming Discord messages.

        Args:
            message: The discord.Message object
        """
        # Ignore bot's own messages
        if message.author == self.client.user:
            return

        # Only process when LM Studio client is available and connected
        if not self.lm_studio_client or not self.lm_studio_client.is_connected:
            return

        # FEAT-001: Server/Channel Access Control
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
            
            # Check if channel is allowed
            if self._config and not self._config.is_channel_allowed(guild_id, str(channel_id)):
                logger.info(f"🚫 Channel '{message.channel.name}' ({channel_id}) not allowed in server '{guild_name}'")
                return

        # Extract image attachments from message
        image_attachments = self._extract_image_attachments(message)
        
        # If processing, queue the message (active sessions only)
        if self._processing_lock.get(channel_id, False):
            if self._session_manager.is_active(channel_id):
                if channel_id not in self._pending_messages:
                    self._pending_messages[channel_id] = []
                author_name = message.author.name
                author_display = message.author.display_name
                message_content = (message.content or "").strip()
                session_user = self._session_manager.get_user(channel_id)
                if author_name == session_user:
                    formatted_content = message_content
                else:
                    formatted_content = f"{author_display} says: {message_content}"
                
                # Include attachment info in queued message
                pending_data = {
                    "author_name": author_name,
                    "author_display": author_display,
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
        message_content = (message.content or "").strip()

        # Check for mention or reply
        mention_str = f"<@{self.client.user.id}>"
        mention_str_alt = f"<@!{self.client.user.id}>"
        is_mention = mention_str in message_content or mention_str_alt in message_content
        is_reply_to_bot = False

        if message.reference and message.reference.message_id:
            try:
                referenced_msg = await message.channel.fetch_message(message.reference.message_id)
                if referenced_msg and referenced_msg.author == self.client.user:
                    is_reply_to_bot = True
            except discord.NotFound:
                pass

        # Case 1: Active session - process with delay
        if self._session_manager.is_active(channel_id):
            await self._typing_indicator.show(message.channel)
            if image_attachments:
                logger.info(f"Message has {len(image_attachments)} image attachment(s) in active session")
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
                    image_attachments=image_attachments
                )
            )

        # Case 2: New session - respond to mentions/replies immediately
        elif is_mention or is_reply_to_bot:
            actual_content = message_content
            if is_mention:
                actual_content = message_content.replace(mention_str, "").replace(mention_str_alt, "").strip()

            await self._typing_indicator.show(message.channel)
            if image_attachments:
                logger.info(f"Message has {len(image_attachments)} image attachment(s) in new session")
            asyncio.create_task(
                self._handle_new_session_message(
                    message, actual_content, "mention", channel_id, author_name,
                    image_attachments=image_attachments
                )
            )

    # --- Message Handling Delegation ---

    async def _handle_new_session_message(
        self, message, content, message_type, channel_id, author_name,
        image_attachments: Optional[List[Dict]] = None
    ) -> None:
        """Handle a new session message.

        Args:
            message: Discord message object
            content: Message content
            message_type: 'mention' or 'reply'
            channel_id: Discord channel ID
            author_name: Author's username
            image_attachments: List of image attachment dicts
        """
        self._processing_lock[channel_id] = True
        try:
            author_display = message.author.display_name
            user_id = str(message.author.id)
            logger.info(f"[{message_type}] @{author_name} (display: {author_display}, id: {user_id}): {content[:50]}...")
            if image_attachments:
                logger.info(f"  Message has {len(image_attachments)} image attachment(s)")

            # Start session
            self._session_manager.start_session(channel_id, author_name)

            # Handle via message handler
            await self._message_handler.handle_new_session(
                message=message,
                content=content,
                message_type=message_type,
                channel_id=channel_id,
                author_name=author_name,
                author_display=author_display,
                user_id=user_id,
                conversation_history=self._conversation_history,
                typing_callback=self._typing_indicator.show,
                on_message_callback=self._on_message_callback,
                image_attachments=image_attachments
            )

            # Store token usage
            # Note: usage is returned from message handler in future refactoring
        finally:
            self._processing_lock[channel_id] = False

        # Check for queued messages after new session completes
        await self._process_queued_pending_messages(channel_id, message)

    async def _process_active_session_batch(
        self, message, content, channel_id, author_name,
        author_display, pending_messages,
        image_attachments: Optional[List[Dict]] = None
    ) -> None:
        """Process active session message batch.

        Args:
            message: Discord message object
            content: Main message content
            channel_id: Discord channel ID
            author_name: Author's username
            author_display: Author's display name
            pending_messages: List of pending message dicts
            image_attachments: List of image attachment dicts
        """
        try:
            # Update session activity
            self._session_manager.update_activity(channel_id)

            # Get session user
            session_user = self._session_manager.get_user(channel_id) or author_name

            # Handle via message handler
            result = await self._message_handler.handle_active_session_batch(
                message=message,
                content=content,
                channel_id=channel_id,
                author_name=author_name,
                author_display=author_display,
                session_user=session_user,
                pending_messages=pending_messages,
                conversation_history=self._conversation_history,
                typing_callback=self._typing_indicator.show,
                on_message_callback=self._on_message_callback,
                image_attachments=image_attachments
            )
            # result is a dict with 'usage' and 'should_end_session' keys
            usage = result.get("usage") if isinstance(result, dict) else None
            message_handler_should_end_session = result.get("should_end_session", False) if isinstance(result, dict) else False

            # Store token usage if available
            if usage:
                self._token_tracker.store_token_usage(channel_id, usage)

            # Clear session if LM Studio requested end_session
            if message_handler_should_end_session:
                self.clear_session(channel_id)
                logger.info(f"Session cleared for channel {channel_id} after end_session")

            # Clear lock and process queued messages
            self._processing_lock[channel_id] = False

            # Process any new queued messages
            await self._process_queued_pending_messages(channel_id, message)

        except Exception as e:
            logger.error(f"Error in active session processing: {e}", module="bot_core", exc=True)
            self._processing_lock[channel_id] = False
            try:
                await message.channel.send("Sorry, I encountered an unexpected error.")
            except Exception:
                pass

    async def _process_queued_pending_messages(self, channel_id, message) -> None:
        """Process queued pending messages after posting a response.

        Shows a typing indicator before processing queued messages
        so the user sees the bot is working.

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
        # Merge attachment info from first pending with queued messages
        queued_attachments = first_pending.get("image_attachments", [])
        await self._process_active_session_batch(
            message,
            first_pending["content"],
            channel_id,
            first_pending["author_name"],
            first_pending["author_display"],
            pending[1:],
            image_attachments=queued_attachments
        )

    # --- Properties ---

    @property
    def is_connected(self) -> bool:
        """Check if the bot is connected to Discord."""
        return self._is_connected and self.client.is_ready()

    @property
    def user(self) -> Optional[discord.User]:
        """Get the bot's user object."""
        return self.client.user if self.client.is_ready() else None

    # --- Callbacks ---

    def set_on_message_callback(self, callback: Callable) -> None:
        """Set callback for received messages.

        Args:
            callback: Async function with signature: callback(message_type, author, content, response)
        """
        self._on_message_callback = callback

    def set_on_status_change_callback(self, callback: Callable) -> None:
        """Set callback for status changes.

        Args:
            callback: Async function with signature: callback(status, details)
        """
        self._on_status_change_callback = callback

    # --- Lifecycle ---

    async def start_async(self) -> None:
        """Start the bot asynchronously."""
        if not self.token:
            raise ValueError("Bot token is not set.")
        await self.client.start(self.token)

    def start(self, token: Optional[str] = None) -> None:
        """Start the bot synchronously."""
        bot_token = token or self.token
        if not bot_token:
            raise ValueError("Bot token is not set.")
        asyncio.run(self.client.start(bot_token))

    async def stop_async(self) -> None:
        """Stop the bot asynchronously."""
        await self.client.close()
        self._is_connected = False

    def stop(self) -> None:
        """Stop the bot synchronously."""
        asyncio.run(self.client.close())
        self._is_connected = False

    async def send_message(self, channel_id: int, content: str) -> None:
        """Send a message to a specific channel.

        Args:
            channel_id: Discord channel ID
            content: Message content
        """
        channel = self.client.get_channel(channel_id)
        if channel:
            await channel.send(content)
        else:
            logger.error(f"Channel {channel_id} not found")

    # --- Configuration ---

    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt for LM Studio."""
        self.system_prompt = prompt
        self._message_handler.set_system_prompt(prompt)

    def set_lm_studio_params(self, temperature: float = 0.7, max_tokens: int = 2500) -> None:
        """Set LM Studio response parameters."""
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._message_handler.set_params(temperature, max_tokens)

    def set_message_delay(self, delay: int) -> None:
        """Set the message processing delay."""
        self.message_delay = delay
        self._delay_processor.default_delay = delay

    # --- Session Info ---

    def get_session_info(self) -> Dict:
        """Get information about active sessions.

        Returns:
            Dict with session information
        """
        return {
            "active_sessions": self._session_manager.get_active_count(),
            "channels": self._session_manager.get_active_channels(),
            "history_lengths": {k: len(v) for k, v in self._conversation_history.items()}
        }

    def clear_session(self, channel_id: int) -> None:
        """Clear the conversation session for a specific channel.

        Args:
            channel_id: Discord channel ID
        """
        if channel_id in self._conversation_history:
            del self._conversation_history[channel_id]
        self._session_manager.clear(channel_id)
        if channel_id in self._processing_lock:
            del self._processing_lock[channel_id]
        if channel_id in self._pending_messages:
            del self._pending_messages[channel_id]
        # Clear token usage for this channel
        self._token_tracker.clear_channel_usage(channel_id)
        logger.info(f"Cleared session for channel {channel_id}")

    # --- Token Usage ---

    def _store_token_usage(self, channel_id: int, usage: Dict[str, Any]) -> None:
        """Store token usage data (backward compat wrapper).

        Args:
            channel_id: Discord channel ID
            usage: Usage dict
        """
        self._token_tracker.store_token_usage(channel_id, usage)

    def get_channel_token_usage(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Get token usage data for a Discord channel.

        Args:
            channel_id: Discord channel ID

        Returns:
            Usage dict or None
        """
        return self._token_tracker.get_channel_token_usage(channel_id)

    def get_last_discord_token_usage(self) -> Optional[Dict[str, Any]]:
        """Get the most recent Discord token usage.

        Returns:
            Usage dict with channel_id and usage data, or None
        """
        return self._token_tracker.get_last_discord_token_usage()

    # --- Guild Info ---

    def get_guilds_info(self) -> list:
        """Get information about guilds the bot is in.

        Returns:
            List of dicts with guild info
        """
        if not self.client.is_ready():
            return []

        guilds = []
        for guild in self.client.guilds:
            guilds.append({
                "id": guild.id,
                "name": guild.name,
                "member_count": guild.member_count,
                "channels": len(guild.text_channels)
            })
        return guilds

    # --- Server Configuration Access (FEAT-001) ---

    def get_server_access_status(self, guild_id: str) -> dict:
        """Get server access status for a specific server.
        
        Args:
            guild_id: Discord guild/server ID
            
        Returns:
            Dict with server access information
        """
        if not self._config:
            return {"error": "No config available"}
        
        server_config = self._config.get_server_config(guild_id)
        return {
            "server_id": guild_id,
            "enabled": server_config["enabled"],
            "allowed_channels": server_config["allowed_channels"],
            "denied_channels": server_config["denied_channels"]
        }

    def get_all_server_configs(self) -> dict:
        """Get all server configurations.
        
        Returns:
            Dict of all server configurations
        """
        if not self._config:
            return {}
        
        return self._config.get_servers()
