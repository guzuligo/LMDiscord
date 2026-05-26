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
from src.tools.builtins.image_compare import ImageCompareTool
from src.tools.builtins.channel_search import ChannelSearchTool
from src.tools.builtins.memory_tool import MemoryTool

# Import memory manager
from src.memory.memory_manager import MemoryManager

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
        # Global lock to serialize LM Studio API calls and prevent OOM
        self._lm_studio_lock = asyncio.Lock()
        self._session_manager = SessionManager(timeout_seconds=600)
        self._token_tracker = TokenTracker()
        self._typing_indicator = TypingIndicator()
        self._delay_processor = DelayProcessor(default_delay=message_delay)
        # Set up tool registry and register built-in tools
        self._tool_registry = ToolRegistry()
        self._image_describe_tool = ImageDescribeTool()
        self._image_compare_tool = ImageCompareTool()
        self._channel_search_tool = ChannelSearchTool()
        
        # Determine memory database path from config
        memory_db_path = "data/memory.db"
        if config is not None and hasattr(config, "memory_db_path"):
            memory_db_path = config.memory_db_path
        self._memory_tool_path = memory_db_path
        self._memory_tool = MemoryTool(db_path=memory_db_path)
        
        # Initialize MemoryManager for session lifecycle integration
        self._memory_manager = MemoryManager(
            db_path=memory_db_path,
            keyword_count=8,
            recall_limit=5,
        )
        
        self._tool_registry.register(self._image_describe_tool)
        self._tool_registry.register(self._image_compare_tool)
        self._tool_registry.register(self._channel_search_tool)
        self._tool_registry.register(self._memory_tool)
        
        # Get tool definitions for LM Studio
        self._tool_definitions = self._tool_registry.get_all_definitions()
        # Add end_session tool to the list
        self._tool_definitions.append(MessageHandler.END_SESSION_TOOL)

        # Get allowed image hostnames from config (will be passed via config)
        allowed_hostnames = []
        if hasattr(lm_studio_client, 'config') and lm_studio_client.config:
            allowed_hostnames = lm_studio_client.config.allowed_image_hostnames if hasattr(lm_studio_client.config, 'allowed_image_hostnames') else []
            
        # Get tools config from config (REASONING-FIX)
        tools_config = {}
        if hasattr(lm_studio_client, 'config') and lm_studio_client.config:
            tools_config = lm_studio_client.config.get_tools_config()
        
        self._message_handler = MessageHandler(
            lm_studio_client=lm_studio_client,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            use_tool_calling=use_tool_calling,
            tools=self._tool_definitions,
            executor=self._executor,
            allowed_image_hostnames=allowed_hostnames,
            lm_studio_lock=self._lm_studio_lock,
            # Tools config (REASONING-FIX)
            reasoning_brevity=tools_config.get('reasoning_brevity', True),
            tool_max_tokens=tools_config.get('tool_max_tokens', 2048),
            tool_temperature=tools_config.get('tool_temperature', 0.3),
            final_max_tokens=tools_config.get('final_max_tokens', 8192),
            max_tool_turns=tools_config.get('max_tool_turns', 5),
            bot_instance=self  # Pass self for channel_search tool
        )
        
        # Store tools config for apply_tools_config
        self._tools_config = tools_config

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

        # Extract image attachments from message
        image_attachments = self._extract_image_attachments(message)
        
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
                
                # Include attachment info and identity in queued message
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
        author_nick = message.author.nick  # Per-server nickname (can be None)
        user_id = str(message.author.id)
        message_content = (message.content or "").strip()

        # Check for mention or reply
        mention_str = f"<@{self.client.user.id}>"
        mention_str_alt = f"<@!{self.client.user.id}>"
        is_mention = mention_str in message_content or mention_str_alt in message_content
        is_reply_to_bot = False
        reply_context = None

        if message.reference and message.reference.message_id:
            try:
                referenced_msg = await message.channel.fetch_message(message.reference.message_id)
                if referenced_msg:
                    if referenced_msg.author == self.client.user:
                        is_reply_to_bot = True
                    # Extract reply context so the LM knows what message is being replied to
                    ref_author = referenced_msg.author.display_name or referenced_msg.author.name
                    ref_content = (referenced_msg.content or "").strip()
                    # Truncate long messages to prevent context overflow (max 500 chars)
                    if len(ref_content) > 500:
                        ref_content = ref_content[:497] + "..."
                    reply_context = f"{ref_author}: {ref_content}"
                    logger.info(f"Reply context extracted: {reply_context[:80]}...")
            except discord.NotFound:
                pass
            except discord.Forbidden:
                logger.warning("No permission to fetch referenced message for reply context")

        # Case 1: Active session - process with delay
        if self._session_manager.is_active(channel_id):
            await self._typing_indicator.show(message.channel)
            if image_attachments:
                logger.info(f"Message has {len(image_attachments)} image attachment(s) in active session")
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
                    image_attachments=image_attachments,
                    reply_context=reply_context
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
            if reply_context:
                logger.info(f"New session reply context: {reply_context[:80]}...")
            asyncio.create_task(
                self._handle_new_session_message(
                    message, actual_content, "mention", channel_id, author_name,
                    author_display, author_nick, user_id,
                    image_attachments=image_attachments,
                    reply_context=reply_context
                )
            )

    # --- Message Handling Delegation ---

    def _get_display_name_for_user(
        self, author_nick: Optional[str], author_display: str, author_name: str
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

    async def _handle_new_session_message(
        self, message, content, message_type, channel_id, author_name,
        author_display: str, author_nick: Optional[str], user_id: str,
        image_attachments: Optional[List[Dict]] = None,
        reply_context: Optional[str] = None
    ) -> None:
        """Handle a new session message.

        Args:
            message: Discord message object
            content: Message content
            message_type: 'mention' or 'reply'
            channel_id: Discord channel ID
            author_name: Author's Discord username (stable identifier)
            author_display: Author's Discord display name (can be changed)
            author_nick: Author's per-server nickname (can be None, server-specific)
            user_id: Author's Discord user ID (immutable unique identifier)
            image_attachments: List of image attachment dicts
            reply_context: String with the referenced message content for Discord replies
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

            # REQ-004 / CONCEPT-001: Inject wake-up memory into system prompt
            await self._on_session_started(channel_id, user_id, author_name)

            # Handle via message handler
            await self._message_handler.handle_new_session(
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
                on_message_callback=self._on_message_callback,
                image_attachments=image_attachments,
                reply_context=reply_context
            )

            # Store token usage
            # Note: usage is returned from message handler in future refactoring
        finally:
            self._processing_lock[channel_id] = False

        # Check for queued messages after new session completes
        await self._process_queued_pending_messages(channel_id, message)

    async def _process_active_session_batch(
        self, message, content, channel_id, author_name,
        author_display, author_nick, pending_messages,
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
            author_nick: Author's current per-server nickname (can be None)
            pending_messages: List of pending message dicts
            image_attachments: List of image attachment dicts
            reply_context: String with the referenced message content for Discord replies
        """
        try:
            # Get session info for identity tracking (before processing, needed for nick comparison)
            session_info = self._session_manager.get_session(channel_id) or {}
            initial_nick = session_info.get("initial_nick")
            session_user = session_info.get("author_name") or author_name

            # Determine if nickname has changed since session start
            nick_changed = author_nick and initial_nick and author_nick != initial_nick
            display_changed = author_display != session_info.get("initial_display", author_display)

            # Handle via message handler
            result = await self._message_handler.handle_active_session_batch(
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
                on_message_callback=self._on_message_callback,
                image_attachments=image_attachments,
                nick_changed=nick_changed,
                display_changed=display_changed,
                reply_context=reply_context
            )

            # Update session activity AFTER successful processing (PENDING-004 fix)
            # This ensures failed sessions don't incorrectly refresh the last-active timestamp
            self._session_manager.update_activity(channel_id)

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
            first_pending.get("author_nick"),
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
        # REQ-004: Save conversation to memory before clearing
        session_info = self._session_manager.get_session(channel_id)
        if session_info:
            user_id = session_info.get("user_id", "")
            author_name = session_info.get("author_name", "")
            # Run memory save in background (non-blocking)
            try:
                import asyncio
                asyncio.create_task(
                    self._on_session_ended(channel_id, user_id, author_name)
                )
            except Exception as e:
                logger.error(f"Failed to schedule memory save for channel {channel_id}: {e}")

        if channel_id in self._conversation_history:
            del self._conversation_history[channel_id]
        self._session_manager.clear(channel_id)
        if channel_id in self._processing_lock:
            del self._processing_lock[channel_id]
        if channel_id in self._pending_messages:
            del self._pending_messages[channel_id]
        # Clear token usage for this channel
        self._token_tracker.clear_channel_usage(channel_id)
        
        # REQ-004: Prune low-importance memories
        try:
            asyncio.create_task(self._on_session_cleanup(channel_id))
        except Exception as e:
            logger.error(f"Failed to schedule memory pruning for channel {channel_id}: {e}")
        
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
                "id": str(guild.id),
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

    # --- Channel Discovery (UX-001) ---

    def get_guild_channels(self, guild_id: str) -> list:
        """Get information about text channels in a specific guild.
        
        Args:
            guild_id: Discord guild/server ID
            
        Returns:
            List of dicts with channel info (id, name, position)
        """
        if not self.client.is_ready():
            return []
        
        # Find the guild by ID
        guild = None
        for g in self.client.guilds:
            if str(g.id) == str(guild_id):
                guild = g
                break
        
        if not guild:
            return []
        
        channels = []
        for channel in guild.text_channels:
            channels.append({
                "id": str(channel.id),
                "name": channel.name,
                "position": channel.position,
                "category": channel.category.name if channel.category else "Uncategorized"
            })
        
        # Sort by position ( Discord API already returns sorted, but ensure it)
        channels.sort(key=lambda x: x["position"])
        return channels

    # --- Channel Search (FEAT-008) ---

    def get_channel_mapping(self) -> Dict[str, str]:
        """Get a mapping of channel names to channel IDs for all visible channels.
        
        Returns:
            Dict mapping {channel_name: channel_id} for all text channels across all guilds
        """
        if not self.client.is_ready():
            return {}
        
        mapping = {}
        for guild in self.client.guilds:
            for channel in guild.text_channels:
                mapping[channel.name] = str(channel.id)
        return mapping

    def resolve_channel(self, channel_spec: str) -> Optional[int]:
        """Resolve a channel specification to a channel ID.

        Supports multiple formats and falls back gracefully:
        - "#123456789" — numeric channel ID (prefix stripped)
        - "#general"    — channel name (prefix stripped, case-insensitive)
        - "@channelname" — channel name (prefix stripped, case-insensitive)
        - "this" / "current" — current active session channel
        - "123456789"   — plain numeric channel ID
        - "general"     — plain channel name (case-insensitive)

        Args:
            channel_spec: Channel specification string

        Returns:
            Channel ID as integer, or None if not found
        """
        if not self.client.is_ready():
            return None

        spec = channel_spec.strip()
        spec_lower = spec.lower()

        # "this" or "current" → resolve from active session
        if spec_lower in ("this", "current"):
            active_channels = self._session_manager.get_active_channels()
            if active_channels:
                return int(active_channels[0])
            logger.warning("[resolve_channel] 'this' specified but no active session")
            return None

        # Build case-insensitive channel mapping: {name_lower: channel_id}
        mapping = self.get_channel_mapping()
        mapping_lower = {name.lower(): cid for name, cid in mapping.items()}

        # "#123456789" → numeric channel ID
        # "#general"  → channel name (fall through to name lookup below)
        if spec.startswith("#"):
            name_or_id = spec[1:].strip()
            name_or_id_lower = name_or_id.lower()

            # Try as numeric ID first
            try:
                channel_id = int(name_or_id)
                channel = self.client.get_channel(channel_id)
                if channel:
                    return channel_id
                logger.warning(f"[resolve_channel] Channel {channel_id} not found")
                return None
            except ValueError:
                # Not a number — try as channel name (case-insensitive)
                if name_or_id_lower in mapping_lower:
                    return int(mapping_lower[name_or_id_lower])
                logger.warning(
                    f"[resolve_channel] Channel not found: {name_or_id}. "
                    f"Available: {list(mapping_lower.keys())[:10]}"
                )
                return None

        # "@channelname" → channel name lookup (case-insensitive)
        if spec.startswith("@"):
            channel_name = spec[1:].strip().lower()
            if channel_name in mapping_lower:
                return int(mapping_lower[channel_name])
            logger.warning(
                f"[resolve_channel] Channel not found: {channel_name}. "
                f"Available: {list(mapping_lower.keys())[:10]}"
            )
            return None

        # Plain number → assume channel ID
        try:
            channel_id = int(spec)
            channel = self.client.get_channel(channel_id)
            if channel:
                return channel_id
            return None
        except ValueError:
            pass

        # Plain text → try as channel name (case-insensitive)
        if spec_lower in mapping_lower:
            return int(mapping_lower[spec_lower])

        logger.warning(
            f"[resolve_channel] Could not resolve channel: {channel_spec}. "
            f"Available: {list(mapping_lower.keys())[:10]}"
        )
        return None

    async def fetch_message_by_id(
        self, channel_id: int, message_id: int
    ) -> Optional[Dict[str, Any]]:
        """Fetch a specific message by ID and extract its attachments.
        
        This method is used when the LM needs to get image URLs from a
        specific message (e.g., when the user shared an image in a
        referenced message that wasn't in the recent history).
        
        Args:
            channel_id: Discord channel ID
            message_id: Discord message ID
            
        Returns:
            Dict with message data including image_urls, or None if not found
        """
        if not self.client.is_ready():
            logger.warning("Bot not ready, cannot fetch message")
            return None
        
        try:
            channel = self.client.get_channel(channel_id)
            if channel is None:
                # Try to get from guild
                for guild in self.client.guilds:
                    channel = guild.get_channel(channel_id)
                    if channel is not None:
                        break
            
            if channel is None:
                logger.warning(f"Channel {channel_id} not found for message fetch")
                return None
            
            msg = await channel.fetch_message(message_id)
            
            # Extract image attachments
            image_urls = []
            has_image = False
            attachments = []
            
            if hasattr(msg, 'attachments') and msg.attachments:
                attachments = list(msg.attachments)
                for attachment in attachments:
                    if attachment.filename:
                        ext = attachment.filename.lower().split('.')[-1]
                        if ext in ('png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'):
                            has_image = True
                            image_urls.append(attachment.url)
            
            content = (msg.content or "").strip()
            if not content:
                content = "[Image/Attachment only]"
            
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            
            # Check for reply
            is_reply = False
            replied_to_author = None
            replied_to_content = None
            if msg.reference:
                try:
                    referenced_msg = await msg.channel.fetch_message(msg.reference.message_id)
                    if referenced_msg:
                        is_reply = True
                        replied_to_author = referenced_msg.author.name
                        replied_to_content = (referenced_msg.content or "").strip()[:100]
                except (discord.NotFound, AttributeError):
                    pass
            
            return {
                "message_id": msg.id,
                "channel_id": channel.id,
                "guild_id": msg.guild.id if msg.guild else None,
                "author": msg.author.name,
                "display_name": msg.author.display_name,
                "content": content,
                "timestamp": timestamp,
                "is_reply": is_reply,
                "replied_to_author": replied_to_author,
                "replied_to_content": replied_to_content,
                "has_image": has_image,
                "image_urls": image_urls,
                "attachments": [a.filename for a in attachments]
            }
            
        except discord.NotFound:
            logger.warning(f"Message {message_id} not found in channel {channel_id}")
            return None
        except discord.Forbidden:
            logger.warning(f"No permission to fetch message {message_id} in channel {channel_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching message {message_id}: {e}", exc_info=True)
            return None
    
    async def _fetch_channel_messages(
        self,
        channel_id: int,
        limit: int = 15,
        filter_bots: bool = False
    ) -> List[Dict[str, Any]]:
        """Fetch recent messages from a Discord channel for context building.

        This method is called by the ChannelSearchTool to get pre-fetched
        message data. The actual Discord API calls are async.

        Args:
            channel_id: Discord channel ID
            limit: Number of messages to fetch (1-50)
            filter_bots: If True, skip bot messages. Default False.

        Returns:
            List of message dicts with author, content, timestamp, reply info, image info
        """
        if not self.client.is_ready():
            logger.warning("Bot not ready, cannot fetch channel messages")
            return []

        # Clamp limit
        limit = max(1, min(limit, 50))

        try:
            # Get the channel
            channel = self.client.get_channel(channel_id)
            if channel is None:
                # Try to fetch from guild
                for guild in self.client.guilds:
                    channel = guild.get_channel(channel_id)
                    if channel is not None:
                        break

            if channel is None:
                logger.warning(f"Channel {channel_id} not found")
                return []

            # Fetch messages from history
            messages = []

            async for msg in channel.history(limit=limit, oldest_first=False):
                # Optionally skip messages from other bots (but always include bot's own messages)
                if filter_bots and msg.author.bot:
                    continue

                # Get author info
                author = msg.author.name
                display_name = msg.author.display_name

                # Get content
                content = (msg.content or "").strip()
                if not content:
                    content = "[Image/Attachment only]"

                # Get timestamp
                timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")

                # Check for reply
                is_reply = False
                replied_to_author = None
                replied_to_content = None
                if msg.reference:
                    try:
                        referenced_msg = await msg.channel.fetch_message(msg.reference.message_id)
                        if referenced_msg:
                            is_reply = True
                            replied_to_author = referenced_msg.author.name
                            replied_to_content = (referenced_msg.content or "").strip()[:100]
                    except (discord.NotFound, AttributeError):
                        pass

                # Check for image attachment — extract URLs and metadata
                image_urls = []
                has_image = False
                attachments = []
                
                # ALWAYS fetch the full message to ensure attachments are populated.
                # channel.history() may not fully populate attachments for messages
                # that were sent before the bot started or for messages where the
                # gateway didn't include full attachment data.
                try:
                    full_msg = await channel.fetch_message(msg.id)
                    if hasattr(full_msg, 'attachments') and full_msg.attachments:
                        attachments = list(full_msg.attachments)
                        logger.debug(
                            f"[fetch_message] Message {msg.id}: found {len(attachments)} attachment(s) "
                            f"from fetch_message: {[a.filename for a in attachments]}"
                        )
                    else:
                        logger.debug(
                            f"[fetch_message] Message {msg.id}: no attachments found via fetch_message"
                        )
                except discord.NotFound:
                    logger.warning(f"[fetch_message] Message {msg.id} not found (may have been deleted)")
                except discord.Forbidden:
                    logger.warning(f"[fetch_message] No permission to fetch message {msg.id}")
                except AttributeError:
                    logger.warning(f"[fetch_message] channel.fetch_message is not available")
                except Exception as e:
                    logger.warning(f"[fetch_message] Error fetching message {msg.id}: {e}")
                
                # Fallback: If fetch_message didn't return attachments, try the history object
                if not attachments:
                    if hasattr(msg, 'attachments') and msg.attachments:
                        attachments = list(msg.attachments)
                        logger.debug(
                            f"[history fallback] Message {msg.id}: found {len(attachments)} attachment(s) "
                            f"from history: {[a.filename for a in attachments]}"
                        )
                
                # Extract image URLs from attachments
                if attachments:
                    for attachment in attachments:
                        if attachment.filename:
                            ext = attachment.filename.lower().split('.')[-1]
                            if ext in ('png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'):
                                has_image = True
                                # Extract the attachment URL (Discord CDN URL)
                                image_urls.append(attachment.url)
                                   
                # Log image detection status for debugging
                if attachments:
                    logger.info(
                        f"[image_detection] Message {msg.id} by {author}: "
                        f"{len(attachments)} total attachment(s), "
                        f"{len(image_urls)} image(s): {image_urls}"
                    )
                else:
                    logger.debug(
                        f"[image_detection] Message {msg.id} by {author}: no attachments"
                    )

                messages.append({
                    "message_id": msg.id,
                    "channel_id": channel.id,
                    "guild_id": msg.guild.id if msg.guild else None,
                    "author": author,
                    "display_name": display_name,
                    "content": content,
                    "timestamp": timestamp,
                    "is_reply": is_reply,
                    "replied_to_author": replied_to_author,
                    "replied_to_content": replied_to_content,
                    "has_image": has_image,
                    "image_urls": image_urls  # List of Discord CDN URLs for image attachments
                })

            # Reverse to show oldest first (chronological order)
            messages.reverse()
            return messages

        except Exception as e:
            logger.error(f"Error fetching channel messages: {e}", exc_info=True)
            return []

    async def search_all_channels(
        self,
        limit: int = 15,
        search_query: str = "",
        username: str = "",
        compress_long: bool = True
    ) -> Dict[str, Any]:
        """Search messages across all visible channels.
        
        Args:
            limit: Number of messages to fetch per channel
            search_query: Optional text filter
            username: Optional username filter
            compress_long: Whether to truncate long messages
        
        Returns:
            Dict with 'messages' key containing all matching messages from all channels
        """
        all_messages = []
        
        if not self.client.is_ready():
            return {"messages": [], "error": "Bot not ready"}
        
        for guild in self.client.guilds:
            for channel in guild.text_channels:
                channel_messages = await self._fetch_channel_messages(channel.id, limit)
                
                # Apply search_query filter
                if search_query:
                    search_lower = search_query.lower()
                    channel_messages = [
                        m for m in channel_messages
                        if search_lower in m.get("content", "").lower()
                    ]
                
                # Apply username filter
                if username:
                    username_lower = username.lower()
                    channel_messages = [
                        m for m in channel_messages
                        if m.get("author", "").lower() == username_lower
                        or m.get("display_name", "").lower() == username_lower
                    ]
                
                # Add channel info to each message
                for msg in channel_messages:
                    msg["_channel_name"] = channel.name
                    msg["_channel_id"] = str(channel.id)
                
                all_messages.extend(channel_messages)
        
        # Sort by timestamp (newest first), then truncate
        all_messages.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
        
        # Truncate long messages if compress_long
        if compress_long:
            for msg in all_messages:
                content = msg.get("content", "")
                if len(content) > 200:
                    msg["content"] = content[:200] + "..."
        
        return {"messages": all_messages}

    async def get_message_by_id(
        self, channel_id: int, message_id: int
    ) -> Dict[str, Any]:
        """Public method to fetch a specific message by ID for tool execution.
        
        This method is called by the tool_executor to fetch a specific message
        and its attachments when the LM needs to get image URLs from a
        specific message.
        
        Args:
            channel_id: Discord channel ID
            message_id: Discord message ID
            
        Returns:
            Dict with 'message' key containing the message data, or error info
        """
        result = await self.fetch_message_by_id(channel_id, message_id)
        if result:
            return {"message": result}
        else:
            return {
                "message": None,
                "error": f"Message {message_id} not found in channel {channel_id}"
            }

    async def get_channel_messages(
        self,
        channel: str = "",
        limit: int = 15,
        search_query: str = "",
        username: str = "",
        compress_long: bool = True
    ) -> Dict[str, Any]:
        """Public method to get channel messages for tool execution.
        
        This method is called by the tool_executor to fetch and format
        channel messages for the ChannelSearchTool.
        
        Args:
            channel: Channel specification. Formats:
                - "#123456789" — channel ID
                - "@channelname" — channel name
                - "this" — current active session channel
                - "" or None — search all channels
            limit: Number of messages to fetch per channel
            search_query: Optional text filter
            username: Optional username filter
            compress_long: Whether to truncate long messages

        Returns:
            Dict with 'messages' key containing the formatted message list
        """
        # Handle empty/None channel → search all
        if not channel or channel.strip().lower() in ("", "all", "*"):
            return await self.search_all_channels(limit, search_query, username, compress_long)
        
        # Resolve channel specification to ID
        channel_id = self.resolve_channel(channel)
        if channel_id is None:
            logger.error(f"Could not resolve channel: {channel}")
            available = self.get_channel_mapping()
            return {
                "messages": [],
                "error": f"Could not resolve channel: {channel}",
                "available_channels": available
            }
        
        messages = await self._fetch_channel_messages(channel_id, limit)
        
        # Apply search_query filter
        if search_query:
            search_lower = search_query.lower()
            messages = [
                m for m in messages
                if search_lower in m.get("content", "").lower()
            ]
        
        # Apply username filter
        if username:
            username_lower = username.lower()
            messages = [
                m for m in messages
                if m.get("author", "").lower() == username_lower
                or m.get("display_name", "").lower() == username_lower
            ]
        
        # Truncate long messages if compress_long
        if compress_long:
            for msg in messages:
                content = msg.get("content", "")
                if len(content) > 200:
                    msg["content"] = content[:200] + "..."
        
        return {"messages": messages}

    # ====================================================================
    # MEMORY INTEGRATION (REQ-004, CONCEPT-001)
    # ====================================================================

    async def _on_session_started(self, channel_id: int, user_id: str, author_name: str) -> None:
        """REQ-004 / CONCEPT-001: On new session, inject wake-up memory into system prompt.
        
        Retrieves relevant memories for the user and prepends them to the
        system prompt so the LM has persistent context from the start.
        
        Args:
            channel_id: Discord channel ID
            user_id: Discord user ID
            author_name: Author's Discord username
        """
        # Get wake-up memory for this user
        wake_up = self._memory_manager.get_wake_up_memory(user_id)
        
        if wake_up and wake_up.get("content"):
            context = f"\n\n=== PERSISTENT CONTEXT (from previous conversations) ===\n{wake_up['content']}\n=== End of persistent context ===\n"
            self._message_handler.set_system_prompt(self.system_prompt + context)
            logger.info(f"Injected wake-up memory for user {user_id} (channel {channel_id})")
        else:
            logger.info(f"No wake-up memory for user {user_id} (channel {channel_id})")

    async def _on_session_ended(self, channel_id: int, user_id: str, author_name: str) -> None:
        """REQ-004 / REQ-005: On session end, save conversation summary to memory.
        
        Extracts keywords, assigns memory type, and stores the conversation
        as a persistent memory entry. Also updates wake-up memory.
        
        Args:
            channel_id: Discord channel ID
            user_id: Discord user ID
            author_name: Author's Discord username
        """
        history = self._conversation_history.get(channel_id, [])
        if not history:
            logger.info(f"No conversation history for channel {channel_id}, skipping memory save")
            return

        # Extract conversation text from history (skip system message)
        conversation_parts = []
        for msg in history:
            if isinstance(msg, dict) and msg.get("role") != "system":
                content = msg.get("content", "")
                if content:
                    conversation_parts.append(content)

        conversation_text = "\n".join(conversation_parts)
        if not conversation_text.strip():
            logger.info(f"Empty conversation for channel {channel_id}, skipping memory save")
            return

        # Truncate to ~2000 chars to avoid oversized memories
        if len(conversation_text) > 2000:
            conversation_text = conversation_text[:1997] + "..."

        try:
            # Create session memory
            result = self._memory_manager.create_session_memory(
                session_id=f"channel_{channel_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                conversation=conversation_text,
                user_id=user_id,
                guild_id="",
                channel_id=str(channel_id),
                topic=author_name,
                memory_type=self._memory_manager.assign_memory_type(conversation_text),
                explicit_weight=0.5,
            )

            logger.info(
                f"Saved session memory for user {user_id} (channel {channel_id}): "
                f"memory_id={result['memory_id']}, type={result['type']}, "
                f"keywords={result['keywords']}"
            )

            # Update wake-up memory (CONCEPT-001)
            self._memory_manager.generate_sleep_summary(
                session_id=f"channel_{channel_id}",
                conversation=conversation_text,
                user_id=user_id,
            )
        except Exception as e:
            logger.error(f"Failed to save session memory for channel {channel_id}: {e}", exc_info=True)

    async def _on_session_cleanup(self, channel_id: int) -> None:
        """REQ-004: On session cleanup, prune low-importance memories.
        
        Args:
            channel_id: Discord channel ID being cleaned up
        """
        try:
            stats = self._memory_manager.prune(keep=100, min_importance=0.1)
            logger.info(f"Memory pruning after session cleanup (channel {channel_id}): {stats}")
        except Exception as e:
            logger.error(f"Memory pruning failed for channel {channel_id}: {e}", exc_info=True)

    # ====================================================================
    # Tools Configuration (REASONING-FIX)
    # ====================================================================

    def apply_tools_config(self, tools_config: dict) -> None:
        """Apply tools configuration to the message handler.
        
        This method is called when the tools config is updated via the web UI
        while the bot is running, to dynamically apply the new settings.
        
        Args:
            tools_config: Dict with keys: reasoning_brevity, tool_max_tokens,
                         tool_temperature, final_max_tokens, use_tool_calling
        """
        reasoning_brevity = tools_config.get("reasoning_brevity", True)
        tool_max_tokens = tools_config.get("tool_max_tokens", 2048)
        tool_temperature = tools_config.get("tool_temperature", 0.3)
        final_max_tokens = tools_config.get("final_max_tokens", 8192)
        use_tool_calling = tools_config.get("use_tool_calling", True)
        
        # Update the message handler with new settings
        self._message_handler.apply_tools_config(
            reasoning_brevity=reasoning_brevity,
            tool_max_tokens=tool_max_tokens,
            tool_temperature=tool_temperature,
            final_max_tokens=final_max_tokens,
            use_tool_calling=use_tool_calling
        )
        
        # Store on bot instance for reference
        self._tools_config = tools_config
        
        logger.info(
            f"Tools config applied: reasoning_brevity={reasoning_brevity}, "
            f"tool_max_tokens={tool_max_tokens}, tool_temperature={tool_temperature}, "
            f"final_max_tokens={final_max_tokens}, use_tool_calling={use_tool_calling}"
        )
