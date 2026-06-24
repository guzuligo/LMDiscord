"""
Bot Core Module

Main DiscordBot class that integrates all sub-modules:
- SessionManager
- TokenTracker
- TypingIndicator
- DelayProcessor
- MessageHandler
- MessageRouter (extracted from old bot_core.py)
- MemoryCallbackHandler (new module)

This module handles Discord connection lifecycle and event registration.
"""

import os
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Callable, Dict, List, Any
from datetime import datetime

import discord
from dotenv import load_dotenv

# Import sub-modules
from src.discord_bot.session_manager import SessionManager
from src.discord_bot.token_tracker import TokenTracker
from src.discord_bot.typing_indicator import TypingIndicator
from src.discord_bot.delay_processor import DelayProcessor
from src.discord_bot.message_handler import MessageHandler
from src.discord_bot.message_router import MessageRouter
from src.discord_bot.memory_callbacks import MemoryCallbackHandler

# Import tools
from src.tools.registry import ToolRegistry
from src.tools.builtins.image_compare import ImageCompareTool
from src.tools.builtins.channel_search import ChannelSearchTool
from src.tools.builtins.memory_tool import MemoryTool
from src.tools.builtins.context_compressor import ContextCompressorTool

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

        # Initialize memory callback handler
        self._memory_callback_handler = MemoryCallbackHandler(
            memory_manager=self._memory_manager,
            memory_tool=self._memory_tool,
            session_manager=self._session_manager
        )

        # Set up tool registry and register built-in tools
        self._tool_registry = ToolRegistry()
        self._image_compare_tool = ImageCompareTool()
        self._channel_search_tool = ChannelSearchTool()
        self._context_compressor = ContextCompressorTool()

        self._tool_registry.register(self._image_compare_tool)
        self._tool_registry.register(self._channel_search_tool)
        self._tool_registry.register(self._memory_tool)
        self._tool_registry.register(self._context_compressor)

        # Get tool definitions for LM Studio
        self._tool_definitions = self._tool_registry.get_all_definitions()
        # Add end_session tool to the list
        self._tool_definitions.append(MessageHandler.END_SESSION_TOOL)

        # Get allowed image hostnames from config
        allowed_hostnames = []
        if hasattr(lm_studio_client, 'config') and lm_studio_client.config:
            allowed_hostnames = lm_studio_client.config.allowed_image_hostnames if hasattr(lm_studio_client.config, 'allowed_image_hostnames') else []

        # Get tools config from config (REASONING-FIX)
        # NOTE: This must happen BEFORE test tools registration so tool definitions
        # are computed after test tools are added to the registry.
        tools_config = {}
        if hasattr(lm_studio_client, 'config') and lm_studio_client.config:
            tools_config = lm_studio_client.config.get_tools_config()

        # Register test tools if enabled (FEAT-TEST-001)
        _register_test_tools(self)

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
            bot_instance=self,
            # Memory integration
            memory_manager=self._memory_manager,
            memory_recall_limit=self._memory_manager._recall_limit if hasattr(self._memory_manager, '_recall_limit') else 5,
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

        # Initialize message router
        self._message_router = MessageRouter(
            bot_instance=self,
            session_manager=self._session_manager,
            processing_lock=self._processing_lock,
            pending_messages=self._pending_messages,
            conversation_history=self._conversation_history,
            typing_indicator=self._typing_indicator,
            delay_processor=self._delay_processor,
            lm_studio_lock=self._lm_studio_lock,
            config=self._config
        )

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

            # Update Discord status
            try:
                import sys
                discord_api = sys.modules.get('src.discord_api')
                if discord_api is None:
                    discord_api = sys.modules.get('discord_api')
                if discord_api is not None:
                    discord_api.discord_connected = True
                    discord_api.discord_status_message = str(self.client.user)
                    logger.info(f"Status updated via on_ready: connected=True, status={self.client.user}")
                elif self._on_status_change_callback:
                    asyncio.create_task(
                        self._on_status_change_callback("connected", str(self.client.user))
                    )
            except Exception as e:
                logger.error(f"Failed to update Discord status in on_ready: {e}", exc_info=True)
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

    async def _handle_on_message(self, message) -> None:
        """Handle incoming Discord messages.

        Delegates to MessageRouter.

        Args:
            message: The discord.Message object
        """
        await self._message_router.handle_on_message(message)

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
        # Save conversation to memory before clearing
        session_info = self._session_manager.get_session(channel_id)
        if session_info:
            user_id = session_info.get("user_id", "")
            author_name = session_info.get("author_name", "")
            try:
                import asyncio
                asyncio.create_task(
                    self._memory_callback_handler.on_session_ended(
                        channel_id, user_id, author_name, self
                    )
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

        # Prune low-importance memories
        try:
            asyncio.create_task(self._memory_callback_handler.on_session_cleanup(channel_id))
        except Exception as e:
            logger.error(f"Failed to schedule memory pruning for channel {channel_id}: {e}")

        logger.info(f"Cleared session for channel {channel_id}")

    # --- Session Cancellation ---

    async def cancel_session(self, channel_id: int) -> bool:
        """Cancel the current session processing for a channel.

        Args:
            channel_id: Discord channel ID

        Returns:
            True if cancellation was successfully signaled, False if no active session
        """
        from src.discord_bot.cancellation import get_cancellation_manager

        if not self._session_manager.is_active(channel_id) and not self._processing_lock.get(channel_id, False):
            logger.info(f"No active session or processing for channel {channel_id}, nothing to cancel")
            return False

        manager = get_cancellation_manager()
        await manager.request_cancel(channel_id)
        logger.info(f"Cancellation signaled for channel {channel_id}")

        try:
            channel = self.client.get_channel(channel_id)
            if channel:
                await channel.send("⚠️ Session cancelled. I've stopped processing your request.")
        except Exception as e:
            logger.error(f"Failed to send cancellation message to channel {channel_id}: {e}")

        return True

    async def cancel_all_sessions(self) -> int:
        """Cancel all active sessions.

        Returns:
            Number of sessions that were cancelled
        """
        channels = self._session_manager.get_active_channels()
        count = 0

        for channel_id in channels:
            if await self.cancel_session(channel_id):
                count += 1

        logger.info(f"Cancelled {count} session(s)")
        return count

    @property
    def cancellation_manager(self):
        """Get the cancellation manager instance."""
        from src.discord_bot.cancellation import get_cancellation_manager
        return get_cancellation_manager()

    # --- Token Usage ---

    def _store_token_usage(self, channel_id: int, usage: Dict[str, Any]) -> None:
        """Store token usage data (backward compat wrapper)."""
        self._token_tracker.store_token_usage(channel_id, usage)

    def get_channel_token_usage(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Get token usage data for a Discord channel."""
        return self._token_tracker.get_channel_token_usage(channel_id)

    def get_last_discord_token_usage(self) -> Optional[Dict[str, Any]]:
        """Get the most recent Discord token usage."""
        return self._token_tracker.get_last_discord_token_usage()

    # --- Guild Info ---

    def get_guilds_info(self) -> list:
        """Get information about guilds the bot is in."""
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
        """Get server access status for a specific server."""
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
        """Get all server configurations."""
        if not self._config:
            return {}
        return self._config.get_servers()

    # --- Channel Discovery (UX-001) ---

    def get_guild_channels(self, guild_id: str) -> list:
        """Get information about text channels in a specific guild."""
        if not self.client.is_ready():
            return []

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

        channels.sort(key=lambda x: x["position"])
        return channels

    # --- Channel Search (FEAT-008) ---

    def get_channel_mapping(self) -> Dict[str, str]:
        """Get a mapping of channel names to channel IDs for all visible channels."""
        if not self.client.is_ready():
            return {}

        mapping = {}
        for guild in self.client.guilds:
            for channel in guild.text_channels:
                mapping[channel.name] = str(channel.id)
        return mapping

    # ====================================================================
    # CHANNEL MESSAGES (FEAT-008)
    # ====================================================================

    async def get_channel_messages(
        self,
        channel: str = "",
        limit: int = 50,
        search_query: str = "",
        username: str = "",
        compress_long: bool = True,
        offset: int = 0,
        windows: int = 1,
        deep_search: bool = False,
        max_depth: int = 500,
        message_id: Optional[int] = None,
        link_channel_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Fetch recent messages from Discord channels.

        Resolves the channel specification, fetches messages via the
        Discord API, applies filters, and returns structured results.

        When deep_search is enabled and search_query contains operators
        (has:, from:, etc.), the bot iteratively scans deeper into message
        history using backward pagination until matches are found or
        max_depth messages have been scanned.

        Args:
            channel: Channel spec — '#123456789', '@channelname', 'this', or empty for all.
            limit: Messages per channel (default 50, max 50). Discord API max is 50 per request.
            search_query: Text filter. Supports Discord-style operators.
            username: Author filter.
            compress_long: Truncate long messages.
            offset: Number of most recent messages to skip before fetching (default 0).
            windows: Number of non-contiguous message windows to fetch (default 1, max 5).
                     Each window fetches 'limit' messages, separated by 'limit' skipped messages.
            deep_search: If True and operators detected, scan deeper into history using
                         backward pagination until matches found or max_depth reached.
            max_depth: Maximum number of messages to scan when deep_search is enabled
                       (default 500, max 5000).

        Returns:
            Dict with 'messages', 'available_channels', and optionally 'error'.
        """
        import discord

        # Resolve channel
        resolved_channel_id = None
        if channel and channel.strip():
            resolved_channel_id = self.resolve_channel(channel)
            if resolved_channel_id is None:
                return {
                    "error": f"Could not resolve channel: {channel}",
                    "messages": [],
                    "available_channels": {},
                }
            target_channel = self.client.get_channel(resolved_channel_id)
        else:
            target_channel = None

        # Gather available channels mapping
        available_channels = self.get_channel_mapping()

        all_messages = []

        # Detect if we should use deep search
        # Deep search is enabled when:
        # 1. deep_search flag is True, AND
        # 2. search_query contains Discord-style operators (has:, from:, etc.)
        use_deep_search = False
        if deep_search and search_query and search_query.strip():
            import re
            operator_pattern = r'\b(has|from|in|after|before|is|contains|edited|pinned):'
            has_operators = bool(re.search(operator_pattern, search_query, re.IGNORECASE))
            if has_operators:
                use_deep_search = True

        # Clamp max_depth to reasonable limits
        max_depth = min(max(100, max_depth), 5000)

        if target_channel:
            # Single channel fetch
            if use_deep_search:
                logger.info(f"[deep_search] Enabled for channel {target_channel.name} (max_depth={max_depth})")
                messages = await self._fetch_channel_history_deep(
                    target_channel, search_query, username,
                    max_depth=max_depth,
                    has_image_filter=self._extract_has_filter(search_query),
                    from_filter=username or self._extract_from_filter(search_query),
                )
            else:
                messages = await self._fetch_channel_history(
                    target_channel, limit, offset=offset, windows=windows
                )
            all_messages = messages
        else:
            # Multi-channel: search across all visible channels
            # Deep search is only supported for single channel
            channels_to_search = []
            for guild in self.client.guilds:
                for ch in guild.text_channels:
                    channels_to_search.append(ch)

            # Limit total channels to search to avoid excessive API calls
            max_channels = 10
            channels_to_search = channels_to_search[:max_channels]

            per_channel_limit = max(5, limit // max(1, len(channels_to_search)))
            per_channel_limit = min(per_channel_limit, 50)

            for ch in channels_to_search:
                msgs = await self._fetch_channel_history(
                    ch, per_channel_limit, offset=offset, windows=windows
                )
                all_messages.extend(msgs)

        # ====================================================================
        # BUG-MESSAGE-001 FIX: Direct message fetch when message_id is provided
        # ====================================================================
        # If message_id and link_channel_id are provided, fetch the message directly
        # from the original channel instead of searching.
        if message_id and link_channel_id:
            try:
                msg_data = await self.get_message_by_id(link_channel_id, message_id)
                if msg_data and msg_data.get("message"):
                    fetched_msg = msg_data["message"]
                    logger.info(f"[channel_search] Direct fetch message {message_id}: has_image={fetched_msg.get('has_image', False)}, image_urls={fetched_msg.get('image_urls', [])}")
                    return {
                        "messages": [fetched_msg],
                        "available_channels": available_channels,
                    }
                else:
                    logger.warning(f"[channel_search] Direct fetch failed for message {message_id} from channel {link_channel_id}")
            except Exception as e:
                logger.warning(f"[channel_search] Direct fetch exception for message {message_id}: {e}")

        # Apply search_query filter — two-tier search with internal keyword splitting
        # First word = primary (sent to Discord API), remaining words = secondary (local filter)
        # However, if the query contains Discord search operators (has:, from:, in:, after:, before:),
        # skip the bot-layer naive text filtering and pass all messages to the tool layer
        # for proper operator-based parsing.
        if search_query and search_query.strip():
            raw_query = search_query.strip()
            
            # Detect Discord-style search operators
            # These operators indicate the query should be handled by the tool layer
            import re
            operator_pattern = r'\b(has|from|in|after|before|is|contains|edited|pinned):'
            has_operators = bool(re.search(operator_pattern, raw_query, re.IGNORECASE))
            
            if not has_operators:
                # Standard text search with naive filtering (original behavior)
                query_parts = raw_query.split()
                primary_keyword = query_parts[0].lower() if query_parts else ""
                secondary_keywords = [k.lower() for k in query_parts[1:]]
                
                filtered = []
                for m in all_messages:
                    content_text = m.get("content", "").lower()
                    attachment_names = [a or "" for a in m.get("attachments", [])]
                    image_urls_list = [u or "" for u in m.get("image_urls", [])]
                    replied_content = (m.get("replied_to_content") or "").lower()
                    
                    # Primary keyword: check content, attachments, image_urls
                    primary_match = (
                        primary_keyword in content_text
                        or any(primary_keyword in a for a in attachment_names)
                        or any(primary_keyword in u for u in image_urls_list)
                        or primary_keyword in replied_content
                    )
                    
                    # Secondary keywords: ALL must match somewhere (AND logic)
                    secondary_match = True
                    if secondary_keywords:
                        for sq in secondary_keywords:
                            keyword_found = (
                                sq in content_text
                                or any(sq in a for a in attachment_names)
                                or any(sq in u for u in image_urls_list)
                                or sq in replied_content
                            )
                            if not keyword_found:
                                secondary_match = False
                                break
                    
                    # Primary must match AND all secondary keywords must match
                    if primary_match and secondary_match:
                        filtered.append(m)
                all_messages = filtered
            # else: has_operators detected — skip bot-layer filtering, pass all messages to tool layer

        # Apply username filter — supports Discord username formats with discriminators
        # e.g., "BotGuzu#3756" matches author "BotGuzu" (strips #1234 discriminator)
        if username and username.strip():
            import re
            # Strip discriminator from filter (e.g., "BotGuzu#3756" → "BotGuzu")
            filter_base = re.sub(r'#\d{4}$', '', username).strip()
            filter_lower = filter_base.lower()
            
            filtered = []
            for m in all_messages:
                author = m.get("author", "")
                display_name = m.get("display_name", "")
                # Strip discriminator from stored values for comparison
                author_base = re.sub(r'#\d{4}$', '', author).lower()
                display_base = re.sub(r'#\d{4}$', '', display_name).lower()
                if author_base == filter_lower or display_base == filter_lower or filter_lower in author.lower() or filter_lower in display_name.lower():
                    filtered.append(m)
            all_messages = filtered

        # Apply compress_long
        if compress_long:
            for m in all_messages:
                content = m.get("content", "")
                if len(content) > 200:
                    m["content"] = content[:200] + "..."

        return {
            "messages": all_messages,
            "available_channels": available_channels,
        }

    async def _fetch_channel_history(
        self,
        channel: discord.TextChannel,
        limit: int = 15,
        offset: int = 0,
        windows: int = 1,
    ) -> List[Dict[str, Any]]:
        """Fetch recent messages from a Discord text channel.

        Supports sliding window pattern for accessing older messages.
        When windows > 1, each window fetches 'limit' messages, separated
        by 'limit' skipped messages (non-contiguous windows).

        Args:
            channel: The Discord text channel.
            limit: Maximum number of messages to fetch per window.
            offset: Number of most recent messages to skip before first window.
            windows: Number of non-contiguous message windows to fetch.

        Returns:
            List of message dicts (messages from all windows, newest first).
        """
        all_messages = []

        try:
            for w in range(windows):
                # Calculate the skip offset for this window:
                # Window 0: skip 'offset' messages
                # Window 1+: skip 'offset + (w * limit)' messages
                window_skip = offset + (w * limit) if w > 0 else offset

                # Fetch (limit + skip) to be able to skip and then take 'limit'
                fetch_limit = window_skip + limit
                fetched = []
                try:
                    async for msg in channel.history(limit=fetch_limit, oldest_first=False):
                        fetched.append(msg)
                except Exception as e:
                    logger.warning(f"Failed to fetch messages from channel {channel.id} (window {w}): {e}")
                    break

                # Skip the first 'window_skip' messages, then take 'limit'
                if window_skip > 0:
                    # If we have fewer messages than skip, this window is empty
                    if len(fetched) <= window_skip:
                        logger.info(f"Channel {channel.id}: Window {w} has no messages at offset {window_skip}")
                        continue
                    start_idx = window_skip
                else:
                    start_idx = 0

                window_messages = fetched[start_idx:start_idx + limit]

                for msg in window_messages:
                    msg_data = await self._format_message(msg)
                    if msg_data:
                        all_messages.append(msg_data)

        except Exception as e:
            logger.warning(f"Failed to fetch messages from channel {channel.id}: {e}")

        return all_messages

    async def _format_message(self, msg) -> Optional[Dict[str, Any]]:
        """Format a Discord message into a structured dict.

        Args:
            msg: The discord.Message object.

        Returns:
            Message dict or None.
        """
        # Skip bot's own messages
        if msg.author == self.client.user:
            return None

        # Gather image URLs
        # Priority order:
        # 1. Attachment URLs (always fresh, use current session auth)
        # 2. Embed URLs (may contain expired tokens — strip query params)
        image_urls = []
        has_image = False
        attachments = []
        for attachment in msg.attachments:
            url = str(attachment.url)
            if attachment.content_type and attachment.content_type.startswith("image/"):
                image_urls.append(url)
                has_image = True
            else:
                attachments.append(attachment.filename)

        # Check embeds for image URLs (Discord auto-embeds images from links)
        # NOTE: Embed URLs may contain expired expiration tokens (e.g., ?ex=6a167da7).
        # We strip query parameters to get the base CDN URL, which sometimes works
        # for public CDN resources. For private/expired resources, the downloader
        # will attempt retry logic with Referer headers.
        for embed in msg.embeds:
            # Direct image embeds
            if embed.type == "image" and embed.url:
                # Strip query parameters (expiration tokens) from embed URLs
                embed_url = embed.url.split('?')[0]
                image_urls.append(embed_url)
                has_image = True
            # Thumbnail images
            if embed.thumbnail and embed.thumbnail.url:
                # Strip query parameters from thumbnail URLs
                thumb_url = embed.thumbnail.url.split('?')[0]
                image_urls.append(thumb_url)
                has_image = True
            # Embedded image field
            if embed.image and embed.image.url:
                # Strip query parameters from image URLs
                img_url = embed.image.url.split('?')[0]
                image_urls.append(img_url)
                has_image = True

        # Build reply info
        is_reply = False
        replied_to_author = None
        replied_to_content = None
        if msg.reference:
            try:
                replied_message = await msg.channel.fetch_message(msg.reference.message_id)
                if replied_message:
                    is_reply = True
                    replied_to_author = replied_message.author.display_name or replied_message.author.name
                    replied_to_content = replied_message.content[:100]
            except Exception:
                pass

        # Check if message has embeds (for has: link operator support)
        has_embeds = len(msg.embeds) > 0

        # Build content_types dict for comprehensive has: operator support
        # This tracks ALL content types present in the message
        content_types: Dict[str, Any] = {}
        if has_image:
            content_types["image"] = image_urls
        if has_embeds:
            # Collect all embed URLs for link detection
            embed_urls = []
            for embed in msg.embeds:
                if embed.url and embed.url.strip():
                    embed_urls.append(embed.url.split('?')[0])
                if embed.thumbnail and embed.thumbnail.url:
                    embed_urls.append(embed.thumbnail.url.split('?')[0])
                if embed.image and embed.image.url:
                    embed_urls.append(embed.image.url.split('?')[0])
                # Check for embedded fields with URLs (author_url, footer_url, etc.)
                if hasattr(embed, 'author') and embed.author and getattr(embed.author, 'url', None):
                    embed_urls.append(embed.author.url)
                if hasattr(embed, 'footer') and embed.footer and getattr(embed.footer, 'text', None):
                    pass  # footer text is not a URL
            if embed_urls:
                content_types["link"] = embed_urls
        if attachments:
            content_types["file"] = attachments

        # Check for video attachments
        video_urls = []
        for attachment in msg.attachments:
            if attachment.content_type and attachment.content_type.startswith("video/"):
                video_urls.append(str(attachment.url))
        if video_urls:
            content_types["video"] = video_urls

        # Check for audio attachments
        audio_urls = []
        for attachment in msg.attachments:
            if attachment.content_type and attachment.content_type.startswith("audio/"):
                audio_urls.append(str(attachment.url))
        if audio_urls:
            content_types["audio"] = audio_urls

        return {
            "message_id": str(msg.id),
            "channel_id": str(msg.channel.id),
            "guild_id": str(msg.guild.id) if msg.guild else None,
            "author": msg.author.name,
            "display_name": msg.author.display_name or msg.author.name,
            "content": msg.content,
            "timestamp": msg.created_at.isoformat(),
            "is_reply": is_reply,
            "replied_to_author": replied_to_author,
            "replied_to_content": replied_to_content,
            "has_image": has_image,
            "has_embeds": has_embeds,
            "image_urls": image_urls,
            "attachments": attachments,
            "content_types": content_types,
        }

    async def get_message_by_id(
        self,
        channel_id: int,
        message_id: int,
    ) -> Dict[str, Any]:
        """Fetch a specific message by its ID.

        Args:
            channel_id: Discord channel ID.
            message_id: Discord message ID.

        Returns:
            Dict with 'message' key containing the formatted message dict.
        """
        try:
            channel = self.client.get_channel(channel_id)
            if channel is None:
                # Try to get channel from guild
                for guild in self.client.guilds:
                    channel = guild.get_channel(channel_id)
                    if channel:
                        break

            if channel is None:
                return {"error": "Channel not found", "message": None}

            msg = await channel.fetch_message(message_id)
            formatted = await self._format_message(msg)
            if formatted:
                return {"message": formatted}
            return {"message": None}
        except Exception as e:
            logger.warning(f"Failed to fetch message {message_id} from channel {channel_id}: {e}")
            return {"error": str(e), "message": None}

    # ====================================================================
    # DEEP SEARCH (FEAT-008 EXTENSION)
    # ====================================================================

    def _extract_has_filter(self, search_query: str) -> Optional[str]:
        """Extract the 'has:' filter value from a search query.
        
        Args:
            search_query: The search query string.
            
        Returns:
            The filter value (e.g., 'image', 'link', 'file') or None.
        """
        if not search_query:
            return None
        import re
        match = re.search(r'\bhas:\s*(\S+)', search_query, re.IGNORECASE)
        return match.group(1).lower() if match else None

    def _extract_from_filter(self, search_query: str) -> Optional[str]:
        """Extract the 'from:' filter value from a search query.
        
        Args:
            search_query: The search query string.
            
        Returns:
            The filter value (e.g., 'BotGuzu') or None.
        """
        if not search_query:
            return None
        import re
        match = re.search(r'\bfrom:\s*(\S+)', search_query, re.IGNORECASE)
        return match.group(1) if match else None

    async def _fetch_channel_history_deep(
        self,
        channel: discord.TextChannel,
        search_query: str,
        username: str = "",
        max_depth: int = 500,
        has_image_filter: Optional[str] = None,
        from_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch messages from a Discord channel using iterative backward pagination.
        
        Scans messages from newest to oldest, stopping early when a matching
        message is found. This is much more efficient than fetching all messages
        when the match is relatively recent.
        
        Args:
            channel: The Discord text channel.
            search_query: The full search query (for logging).
            username: Username filter (overrides from_filter if set).
            max_depth: Maximum number of messages to scan.
            has_image_filter: If set, only match messages with this content type.
            from_filter: Username filter extracted from 'from:' operator.
            
        Returns:
            List of matching message dicts (empty list if none found).
        """
        matched_messages = []
        oldest_id = None
        scanned = 0
        batch_size = 50  # Discord API max per request

        # Determine the effective from_filter
        effective_from = username.strip() if (username and username.strip()) else (from_filter or "")
        # Strip Discord discriminator from from_filter
        if effective_from:
            import re
            effective_from = re.sub(r'#\d{4}$', '', effective_from).strip()

        logger.info(f"[deep_search] Scanning channel {channel.name} (id={channel.id}) for '{search_query}', max_depth={max_depth}")
        if has_image_filter:
            logger.info(f"[deep_search] Filtering by content type: has:{has_image_filter}")
        if effective_from:
            logger.info(f"[deep_search] Filtering by author: {effective_from}")

        while scanned < max_depth:
            # Calculate remaining messages to scan
            remaining = max_depth - scanned
            current_limit = min(batch_size, remaining)

            # Fetch next batch using backward pagination
            try:
                batch = []
                async for msg in channel.history(limit=current_limit, before=oldest_id):
                    batch.append(msg)
                scanned += len(batch)
            except Exception as e:
                logger.warning(f"[deep_search] Failed to fetch batch from channel {channel.id}: {e}")
                break

            if not batch:
                logger.info(f"[deep_search] No more messages to scan at offset {scanned}")
                break

            # The last message in the batch becomes the 'before' cursor for next iteration
            oldest_id = batch[-1].id

            # Check each message in this batch
            for msg in batch:
                # Skip bot's own messages
                if msg.author == self.client.user:
                    continue

                # Quick pre-filter without full formatting
                if has_image_filter:
                    # Check if message has relevant content types
                    has_match = False
                    if has_image_filter == "image":
                        has_match = msg.attachments or msg.embeds
                    elif has_image_filter == "link":
                        has_match = len(msg.embeds) > 0
                    elif has_image_filter == "file":
                        has_match = len(msg.attachments) > 0
                    
                    if not has_match:
                        continue

                if effective_from:
                    # Quick author pre-filter
                    author_name = re.sub(r'#\d{4}$', '', msg.author.name).lower()
                    display_name = re.sub(r'#\d{4}$', '', msg.author.display_name or msg.author.name).lower()
                    if author_name != effective_from.lower() and display_name != effective_from.lower() and effective_from.lower() not in msg.author.name.lower():
                        continue

                # Full formatting (message passed pre-filters)
                msg_data = await self._format_message(msg)
                if msg_data is None:
                    continue

                # Additional post-format filtering
                if has_image_filter:
                    content_types = msg_data.get("content_types", {})
                    if has_image_filter == "image":
                        if "image" not in content_types and not (msg_data.get("has_embeds") and msg_data.get("image_urls")):
                            continue
                    elif has_image_filter == "link":
                        if "link" not in content_types and not msg_data.get("has_embeds"):
                            continue
                    elif has_image_filter == "file":
                        if "file" not in content_types and not msg_data.get("attachments"):
                            continue

                if effective_from:
                    author = re.sub(r'#\d{4}$', '', msg_data.get("author", "")).lower()
                    display = re.sub(r'#\d{4}$', '', msg_data.get("display_name", "")).lower()
                    if author != effective_from.lower() and display != effective_from.lower():
                        continue

                matched_messages.append(msg_data)
                logger.info(f"[deep_search] Found match at offset {scanned}: {msg.author.name}: {msg.content[:50]}")
                # Early exit — we found a match!
                break

            if matched_messages:
                break

        logger.info(f"[deep_search] Scanned {scanned} messages, found {len(matched_messages)} match(es)")
        return matched_messages

    def resolve_channel(self, channel_spec: str) -> Optional[int]:
        """Resolve a channel specification to a channel ID.

        Supports multiple formats:
        - "#123456789" — numeric channel ID
        - "#general" or "@channelname" — channel name
        - "this" / "current" — current active session channel
        - "123456789" — plain numeric channel ID
        - "general" — plain channel name
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

        mapping = self.get_channel_mapping()
        mapping_lower = {name.lower(): cid for name, cid in mapping.items()}

        # "#123456789" → numeric channel ID
        if spec.startswith("#"):
            name_or_id = spec[1:].strip()
            name_or_id_lower = name_or_id.lower()

            try:
                channel_id = int(name_or_id)
                channel = self.client.get_channel(channel_id)
                if channel:
                    return channel_id
                logger.warning(f"[resolve_channel] Channel {channel_id} not found")
                return None
            except ValueError:
                if name_or_id_lower in mapping_lower:
                    return int(mapping_lower[name_or_id_lower])
                logger.warning(f"[resolve_channel] Channel not found: {name_or_id}")
                return None

        # "@channelname" → channel name lookup
        if spec.startswith("@"):
            channel_name = spec[1:].strip().lower()
            if channel_name in mapping_lower:
                return int(mapping_lower[channel_name])
            logger.warning(f"[resolve_channel] Channel not found: {channel_name}")
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

        # Plain text → try as channel name
        if spec_lower in mapping_lower:
            return int(mapping_lower[spec_lower])

        logger.warning(f"[resolve_channel] Could not resolve channel: {channel_spec}")
        return None

    # ====================================================================
    # MEMORY INTEGRATION (REQ-004, CONCEPT-001)
    # ====================================================================

    async def _on_session_started(self, channel_id: int, user_id: str, author_name: str) -> None:
        """REQ-004 / CONCEPT-001: On new session, inject wake-up memory into system prompt."""
        await self._memory_callback_handler.on_session_started(channel_id, user_id, author_name, self)

    async def _on_session_ended(self, channel_id: int, user_id: str, author_name: str) -> None:
        """REQ-004 / REQ-005: On session end, save conversation summary to memory."""
        await self._memory_callback_handler.on_session_ended(channel_id, user_id, author_name, self)

    async def _on_session_cleanup(self, channel_id: int) -> None:
        """REQ-004: On session cleanup, prune low-importance memories."""
        await self._memory_callback_handler.on_session_cleanup(channel_id)

    # ====================================================================
    # Tools Configuration (REASONING-FIX)
    # ====================================================================

    def apply_tools_config(self, tools_config: dict) -> None:
        """Apply tools configuration to the message handler."""
        reasoning_brevity = tools_config.get("reasoning_brevity", True)
        
        # Re-register test tools if they were just enabled (FEAT-TEST-001)
        if tools_config.get("_test_tools_enabled"):
            _register_test_tools(self)
        elif tools_config.get("_test_tools_enabled") is False:
            # Remove test tools from registry if they were disabled
            global _enable_test_tools
            _enable_test_tools = False
            # Remove test tools from registry and rebuild definitions
            test_tool_names = {"test_echo", "test_tool_call", "test_memory"}
            self._tool_registry._tools = {
                k: v for k, v in self._tool_registry._tools.items()
                if v.name not in test_tool_names
            }
            self._tool_definitions = self._tool_registry.get_all_definitions()
            # Re-add end_session tool
            self._tool_definitions.append(MessageHandler.END_SESSION_TOOL)
            logger.info("Test tools removed from registry", module="bot_core")
        tool_max_tokens = tools_config.get("tool_max_tokens", 2048)
        tool_temperature = tools_config.get("tool_temperature", 0.3)
        final_max_tokens = tools_config.get("final_max_tokens", 8192)
        use_tool_calling = tools_config.get("use_tool_calling", True)

        # Context compression settings
        context_compression_enabled = tools_config.get("context_compression_enabled", True)
        context_token_threshold = tools_config.get("context_token_threshold", 80)
        context_message_threshold = tools_config.get("context_message_threshold", 20)
        context_messages_to_keep_fresh = tools_config.get("context_messages_to_keep_fresh", 6)
        context_summary_length = tools_config.get("context_summary_length", 300)
        context_lm_max_tokens = tools_config.get("context_lm_max_tokens", 4096)

        self._message_handler.apply_tools_config(
            reasoning_brevity=reasoning_brevity,
            tool_max_tokens=tool_max_tokens,
            tool_temperature=tool_temperature,
            final_max_tokens=final_max_tokens,
            use_tool_calling=use_tool_calling,
            # Context compression settings
            context_compression_enabled=context_compression_enabled,
            context_token_threshold=context_token_threshold,
            context_message_threshold=context_message_threshold,
            context_messages_to_keep_fresh=context_messages_to_keep_fresh,
            context_summary_length=context_summary_length,
            context_lm_max_tokens=context_lm_max_tokens
        )

        self._tools_config = tools_config

        logger.info(
            f"Tools config applied: reasoning_brevity={reasoning_brevity}, "
            f"tool_max_tokens={tool_max_tokens}, tool_temperature={tool_temperature}, "
            f"final_max_tokens={final_max_tokens}, use_tool_calling={use_tool_calling}, "
            f"context_compression={context_compression_enabled}, token_threshold={context_token_threshold}"
        )


# ==================== Test Tools Toggle (FEAT-TEST-001) ====================

# Global flag for enabling test tools in production/debug
# Controlled via /api/settings/test_tools API endpoint
_enable_test_tools = False


def set_test_tools_enabled(enabled: bool) -> None:
    """Enable or disable test tools.
    
    When enabled, debug/test tools are registered with the bot's tool registry.
    These tools are useful for testing and debugging but should not be used in production.
    
    Args:
        enabled: True to enable test tools, False to disable
    """
    global _enable_test_tools
    _enable_test_tools = enabled
    logger.info(f"Test tools {'enabled' if enabled else 'disabled'}", module="bot_core")


def is_test_tools_enabled() -> bool:
    """Check if test tools are enabled.
    
    Returns:
        True if test tools are enabled, False otherwise
    """
    return _enable_test_tools


# Global bot instance reference for cross-module access
_bot_instance = None


def set_bot_instance(bot):
    """Set the global bot instance reference.

    Args:
        bot: DiscordBotCore instance
    """
    global _bot_instance
    _bot_instance = bot


def get_bot_instance():
    """Get the global bot instance reference.

    Returns:
        DiscordBotCore instance or None
    """
    return _bot_instance


# ====================================================================
# TEST TOOLS REGISTRATION HELPER
# ====================================================================

def _register_test_tools(bot_instance):
    """Register test tools with the bot's tool registry if enabled.
    
    This is called during bot initialization to add test tools
    when the _enable_test_tools flag is True.
    
    Args:
        bot_instance: DiscordBot instance
    """
    global _enable_test_tools
    
    if not _enable_test_tools:
        return
    
    if bot_instance is None or bot_instance._tool_registry is None:
        return
    
    registry = bot_instance._tool_registry
    
    # Test echo tool - returns the input as-is
    class TestEchoTool:
        """Test tool that echoes input back."""
        name = "test_echo"
        description = "Test tool: echoes back the input message. Useful for testing tool calling."
        
        @staticmethod
        def execute(message: str = "") -> dict:
            return {
                "success": True,
                "echo": message or "No message provided",
                "tool": "test_echo"
            }
    
    # Test tool call tool - simulates a tool call response
    class TestToolCallTool:
        """Test tool that simulates a tool call response."""
        name = "test_tool_call"
        description = "Test tool: simulates a tool call response with configurable output."
        
        @staticmethod
        def execute(response: str = "Test response", delay: int = 0) -> dict:
            import time
            if delay > 0:
                time.sleep(delay)
            return {
                "success": True,
                "response": response,
                "delay": delay,
                "tool": "test_tool_call"
            }
    
    # Test memory tool - tests memory operations
    class TestMemoryTool:
        """Test tool for memory operations."""
        name = "test_memory"
        description = "Test tool: tests memory operations. Returns memory status."
        
        @staticmethod
        def execute(operation: str = "status") -> dict:
            return {
                "success": True,
                "operation": operation,
                "message": "Test memory operation completed",
                "tool": "test_memory"
            }
    
    # Register test tools
    registry.register(TestEchoTool())
    registry.register(TestToolCallTool())
    registry.register(TestMemoryTool())
    
    # Update tool definitions
    bot_instance._tool_definitions = registry.get_all_definitions()
    
    logger.info(f"Test tools registered: test_echo, test_tool_call, test_memory", module="bot_core")
