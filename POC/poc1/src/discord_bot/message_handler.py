"""
Message Handler Module

Handles Discord message processing including:
- New session message handling
- Active session message batching
- Delegates core processing to MessageProcessor
- Safe image downloading via SafeImageDownloader
- User identity formatting via UserIdentity
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional, Callable

from src.discord_bot.image_downloader import get_safe_downloader
from src.discord_bot.message_processor import MessageProcessor
from src.discord_bot.user_identity import UserIdentity

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handles Discord message processing and LM Studio interaction."""

    # Tool definition for ending session
    END_SESSION_TOOL = {
        "type": "function",
        "function": {
            "name": "end_session",
            "description": "End the current conversation session. Use this when the user wants to leave, say goodbye, end the conversation, or when the conversation is naturally concluding. The model should respond with a farewell message before calling this tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "farewell_message": {
                        "type": "string",
                        "description": "The farewell/response message to send to the user before ending the session. Should be polite and natural."
                    }
                },
                "required": ["farewell_message"]
            }
        }
    }

    def __init__(
        self,
        lm_studio_client: Any,
        system_prompt: str = "You are a helpful assistant in a Discord server.",
        temperature: float = 0.7,
        max_tokens: int = 25000,
        use_tool_calling: bool = True,
        tools: Optional[List[Dict[str, Any]]] = None,
        executor: Optional[ThreadPoolExecutor] = None,
        tool_executor_instance: Optional[Any] = None,
        allowed_image_hostnames: Optional[List[str]] = None,
        lm_studio_lock: Optional[Any] = None,
        # Tools config (REASONING-FIX)
        # Updated defaults for modern models (10x increase from oldschool limits)
        reasoning_brevity: bool = True,
        tool_max_tokens: int = 20480,
        tool_temperature: float = 0.3,
        final_max_tokens: int = 81920,
        max_tool_turns: int = 5,
        bot_instance: Any = None,
        # Memory integration
        memory_manager: Optional[Any] = None,
        memory_recall_limit: int = 5,
    ):
        """Initialize message handler."""
        self.lm_studio_client = lm_studio_client
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.use_tool_calling = use_tool_calling
        self._tools = tools or [self.END_SESSION_TOOL]
        self._executor = executor or ThreadPoolExecutor(max_workers=2)
        self._lm_studio_lock = lm_studio_lock
        self._bot_instance = bot_instance

        # Tools config (REASONING-FIX)
        self._reasoning_brevity = reasoning_brevity
        self._tool_max_tokens = tool_max_tokens
        self._tool_temperature = tool_temperature
        self._final_max_tokens = final_max_tokens

        # Tools config
        self._max_tool_turns = max(1, min(max_tool_turns, 10))

        # Set up tool executor
        self._tool_executor = tool_executor_instance
        self._tools_dict = {}
        if self._tool_executor is None:
            self._tools_dict = {
                "end_session": {"type": "builtin", "definition": self.END_SESSION_TOOL}
            }

        # Set up safe image downloader
        self._allowed_hostnames = allowed_image_hostnames or []
        self._safe_downloader = get_safe_downloader(
            allowed_hostnames=self._allowed_hostnames,
            bot_instance=bot_instance
        )
        logger.info(f"Safe image downloader initialized with allowed hostnames: {self._allowed_hostnames}")

        # Initialize message processor
        self._processor = MessageProcessor(
            lm_studio_client=lm_studio_client,
            temperature=temperature,
            max_tokens=max_tokens,
            use_tool_calling=use_tool_calling,
            tools=self._tools,
            executor=self._executor,
            lm_studio_lock=lm_studio_lock,
            safe_downloader=self._safe_downloader,
            bot_instance=bot_instance,
            max_tool_turns=self._max_tool_turns,
            memory_manager=memory_manager,
            memory_recall_limit=memory_recall_limit,
        )

    @property
    def tools(self) -> List[Dict[str, Any]]:
        """Get the list of tools."""
        return self._tools

    def set_tools(self, tools: List[Dict[str, Any]]) -> None:
        """Set the list of tools."""
        self._tools = tools
        self._processor.set_tools(tools)

    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt."""
        self.system_prompt = prompt

    def set_params(self, temperature: float = 0.7, max_tokens: int = 2500) -> None:
        """Set LM Studio parameters."""
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._processor.set_params(temperature, max_tokens)

    def apply_tools_config(
        self,
        reasoning_brevity: bool = True,
        tool_max_tokens: int = 20480,
        tool_temperature: float = 0.3,
        final_max_tokens: int = 81920,
        use_tool_calling: bool = True,
        # Context compression settings
        context_compression_enabled: bool = True,
        context_token_threshold: int = 80,
        context_message_threshold: int = 20,
        context_messages_to_keep_fresh: int = 6,
        context_summary_length: int = 300
    ) -> None:
        """Apply tools configuration changes.
        
        These settings take effect on new sessions (system prompt rebuild)
        and subsequent LM API calls (temperature/max_tokens).
        
        Args:
            reasoning_brevity: Whether to add brevity instruction to system prompt
            tool_max_tokens: Max tokens for tool-calling requests
            tool_temperature: Temperature for tool-calling requests
            final_max_tokens: Max tokens for final responses
            use_tool_calling: Whether tool calling is enabled
            context_compression_enabled: Whether context compression is enabled
            context_token_threshold: Token threshold percentage for triggering compression
            context_message_threshold: Message count threshold for triggering compression
            context_messages_to_keep_fresh: Number of recent messages to keep uncompressed
            context_summary_length: Length of compression summaries
        """
        self._reasoning_brevity = reasoning_brevity
        self._tool_max_tokens = tool_max_tokens
        self._tool_temperature = tool_temperature
        self._final_max_tokens = final_max_tokens
        self.use_tool_calling = use_tool_calling
        
        # Context compression settings
        self._context_compression_enabled = context_compression_enabled
        self._context_token_threshold = context_token_threshold
        self._context_message_threshold = context_message_threshold
        self._context_messages_to_keep_fresh = context_messages_to_keep_fresh
        self._context_summary_length = context_summary_length
        
        # Forward to processor if it exists
        if hasattr(self, '_processor') and self._processor:
            self._processor.apply_tools_config(
                context_compression_enabled=context_compression_enabled,
                context_token_threshold=context_token_threshold,
                context_message_threshold=context_message_threshold,
                context_messages_to_keep_fresh=context_messages_to_keep_fresh,
                context_summary_length=context_summary_length
            )

    def register_tool(self, tool_name: str, tool_instance: Any) -> None:
        """Register a tool instance for execution."""
        self._tools_dict[tool_name] = {"type": "tool", "instance": tool_instance}
        if hasattr(tool_instance, 'to_dict'):
            tool_def = tool_instance.to_dict()
            if tool_def not in self._tools:
                self._tools.append(tool_def)

    # --- LM Studio Call Helper ---

    async def _call_lm_studio(self, api_call_func, *args, channel_id: Optional[int] = None) -> Dict:
        """Call LM Studio API with global lock to prevent concurrent requests."""
        channel_info = f" (channel {channel_id})" if channel_id else ""

        if self._lm_studio_lock is not None:
            logger.info(f"Waiting for LM Studio lock{channel_info}")
            async with self._lm_studio_lock:
                logger.info(f"Acquired LM Studio lock{channel_info}, calling API")
                result = await asyncio.get_event_loop().run_in_executor(
                    self._executor, api_call_func, *args
                )
                logger.info(f"Released LM Studio lock{channel_info}")
                return result
        else:
            logger.warning(f"No LM Studio lock available{channel_info}, calling API directly")
            return await asyncio.get_event_loop().run_in_executor(
                self._executor, api_call_func, *args
            )

    # --- New Session Message Handling ---

    async def handle_new_session(
        self,
        message: Any,
        content: str,
        message_type: str,
        channel_id: int,
        author_name: str,
        author_display: str = "",
        author_nick: Optional[str] = None,
        user_id: str = "",
        conversation_history: Dict[int, List[Dict[str, str]]] = None,
        typing_callback: Callable = None,
        on_message_callback: Optional[Callable] = None,
        image_attachments: Optional[List[Dict]] = None,
        reply_context: Optional[str] = None
    ) -> None:
        """Handle a new session message (mention or reply)."""
        channel = message.channel

        # Build system prompt with user identity context
        identity_context = UserIdentity.build_context(author_name, author_display, author_nick, user_id)

        # Store for apply_tools_config rebuild
        self._last_author_name = author_name
        self._last_author_display = author_display
        self._last_author_nick = author_nick
        self._last_user_id = user_id

        system_prompt = self.system_prompt + (
            identity_context +
            "\n\nUsers will mention you or reply to you to start conversations.\n"
            "When someone mentions you (e.g., @Bot hello), respond naturally.\n"
            "Only respond when the message appears to be directed at you.\n\n"
            "You have access to the following tools:\n"
            "- 'image_compare': Call this when the user wants to compare 2-3 images side by side. Pass image URLs as an array. Optionally include a comparison_prompt for specific comparison focus.\n"
            "- 'channel_search': Call this to read recent messages from Discord channels to gather context for conversation. Returns a list of recent messages with author, content, timestamp, reply info, and image attachment URLs. Use this when you need to understand ongoing conversations, find specific information, or gather context before responding.\n"
            "  Channel specification (the 'channel' parameter):\n"
            "    - '#123456789' — search by channel ID (e.g., '#1503498099081871470')\n"
            "    - '@channelname' — search by channel name (e.g., '@c3', '@general')\n"
            "    - 'this' — search the current active session channel\n"
            "    - leave empty or omit — search ALL visible channels\n"
            "  Optional parameters: limit (default 50, max 50), search_query (text filter), username (author filter), compress_long (truncate long messages)\n"
            "  IMPORTANT: If the user shares a Discord message link (e.g., discord.com/channels/GUILD_ID/CHANNEL_ID/MESSAGE_ID), you MUST include both 'message_id' and 'channel_id' parameters extracted from the link to fetch that specific message directly.\n"
            "- 'memory_tool': Call this to search, save, or manage long-term memory. Use 'search' action to recall relevant memories, 'save' to store important information, or 'delete' to remove outdated memories.\n"
            "- 'context_compress': Call this when conversation history grows too large and you need to compress old messages into a summary to free up context space. Use compress_before_index to specify where to start compression. This helps prevent context overload errors.\n"
            "- 'end_session': Call this when the conversation is ending and you want to say goodbye\n\n"
            "IMPORTANT: For channel_search, you can use '#ID' for channel ID, '@name' for channel name, 'this' for current channel, or leave empty to search all channels. You do NOT need to ask the user for channel IDs.\n"
            "IMPORTANT: When channel_search results show image URLs with '![image](URL)' format, you can respond naturally about those images — there is no image_describe tool available.\n"
            "IMPORTANT: When sharing image URLs with users, ALWAYS use Discord's markdown image format: ![description](URL). This format renders as a clickable image preview in Discord. DO NOT share raw URLs like 'https://cdn.discordapp.com/...' without wrapping them in ![alt](URL) format.\n"
            "IMPORTANT: When sharing Discord message links, use the format: [link text](https://discord.com/channels/GUILD/CHANNEL/MESSAGE). This creates a clickable jump link to the message.\n"
            "IMPORTANT: When calling any tool, ALWAYS include a 'tell_user_you_are_working' argument with a short, in-character status message so the user knows you are working. Make it sound natural and match your personality (e.g., 'Let me check that for you...', 'Looking through recent messages...', 'Analyzing that image now...'). This message will be posted to Discord immediately while the tool runs.\n\n"
            "WORKFLOW BEST PRACTICES:\n"
            "1. GATHER CONTEXT FIRST: Before responding, always call channel_search to check recent messages for context. This helps you understand ongoing conversations and avoid repeating information.\n"
            "2. USE TOOLS EFFICIENTLY: When you have enough information, respond immediately. Do not call tools unnecessarily.\n"
            "3. AVOID REDUNDANT CALLS: Do not call the same tool multiple times with the same arguments. If you already have the information, use it.\n"
            "4. SEARCH QUERY REQUIREMENT: When using channel_search with a search_query, the query must be at least 2 characters long. Shorter queries will be rejected.\n"
            "5. The bot always fetches 50 messages per channel search for comprehensive results.\n"
            "\n--- SEARCH WORKFLOW (SEARCH-001) ---\n"
            "When the user asks about OLD messages or you need to search beyond recent history:\n"
            "1. START with channel_search(channel='this', limit=50, search_query='keyword') — scans last ~50 messages\n"
            "2. If no results, use the oldest_message_id from the result to search deeper:\n"
            "   channel_search(channel='this', search_query='keyword', before_message_id=<oldest_id>, max_pages=3)\n"
            "   This scans 3 pages × 50 = 150 more messages (total ~200)\n"
            "3. If you need to go back further but don't need message CONTENT, use channel_skip to fast-forward:\n"
            "   channel_skip(channel='this', count=50) — returns only IDs + timestamps + media indicators\n"
            "   Use the oldest ID from skip results with before_message_id to anchor deeper searches\n"
            "4. Use channel_skip when: you need to reach a specific date/time period without scanning every message\n"
            "5. Watch the 'Pages scanned' counter — if it reaches max_pages, increase max_pages to go deeper\n"
            "6. Each skip_ahead returns media indicators (📷 images, 🔗 links, 📎 embeds) so you can decide if more scanning is needed\n"
            "7. MAX 20 pages total per search to avoid rate limits. Increase max_pages incrementally.\n"
            "8. After finding matches, provide a direct answer using the search results — do not re-call channel_search.\n"
        )
        
        # REASONING-FIX: Add reasoning brevity instruction if enabled
        if self._reasoning_brevity:
            system_prompt += (
                "\n\n⚠️ CRITICAL INSTRUCTIONS FOR RESPONSE QUALITY:\n"
                "1. When using tools, keep your reasoning and tool call arguments SHORT and PRECISE.\n"
                "2. After receiving tool results, respond directly — do NOT re-explain your reasoning.\n"
                "3. Do NOT output extended internal reasoning or chain-of-thought.\n"
                "4. Keep all responses concise — especially tool call arguments and final answers.\n"
                "5. When you have the answer, respond immediately without extra reasoning steps.\n"
                "6. You have up to 5 tool call attempts per message. Use them wisely — gather context first, then respond.\n"
            )

        # Include reply context so the LM knows what message is being replied to
        if reply_context:
            content = f"[Replying to: {reply_context}]\n\n{content}"
            logger.info(f"Included reply context in new session message")

        # Include image attachment info in content
        if image_attachments:
            attachment_info = "\n\nThe user has attached the following image(s):\n"
            for i, att in enumerate(image_attachments, 1):
                attachment_info += f"- Image {i}: {att.get('filename', 'unknown')} (URL: {att.get('url', 'N/A')})\n"
            attachment_info += "You can respond naturally about these images."
            content = content + attachment_info

        # Initialize conversation history
        if channel_id not in conversation_history:
            conversation_history[channel_id] = []

        if not conversation_history[channel_id]:
            conversation_history[channel_id].append({"role": "system", "content": system_prompt})

        # Add user message with identity attribution
        full_content = UserIdentity.format_new_session(content, author_name, author_nick, author_display)
        conversation_history[channel_id].append({"role": "user", "content": full_content})

        # Process with LM Studio and capture result
        result = await self._processor.process_message(
            message=message,
            channel_id=channel_id,
            conversation_history=conversation_history,
            typing_callback=typing_callback,
            is_active_session=False,
            on_message_callback=on_message_callback,
            call_lm_studio_func=self._call_lm_studio_via_processor,
            user_id=user_id,
            guild_id=getattr(message, 'guild', None) and str(message.guild.id),
            user_message_content=content
        )
        
        return result

    # --- Active Session Message Handling ---

    async def handle_active_session_batch(
        self,
        message: Any,
        content: str,
        channel_id: int,
        author_name: str,
        author_display: str,
        author_nick: Optional[str],
        initial_nick: Optional[str],
        session_user: str,
        pending_messages: List[Dict[str, str]],
        conversation_history: Dict[int, List[Dict[str, str]]],
        typing_callback: Callable,
        on_message_callback: Optional[Callable] = None,
        image_attachments: Optional[List[Dict]] = None,
        nick_changed: bool = False,
        display_changed: bool = False,
        reply_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle batched messages during an active session."""
        if not content or not content.strip():
            logger.info(f"Skipping empty message for channel {channel_id}")
            return {"usage": None, "should_end_session": False}

        # Format message with identity attribution
        formatted_content = UserIdentity.format_active_session(
            content, author_name, author_display, author_nick,
            session_user, initial_nick, nick_changed
        )

        # Include reply context so the LM knows what message is being replied to
        if reply_context:
            formatted_content = f"[Replying to: {reply_context}]\n\n{formatted_content}"
            logger.info(f"Included reply context in active session message")

        # Include image attachment info
        if image_attachments:
            attachment_info = "\n\nThe user has attached the following image(s):\n"
            for i, att in enumerate(image_attachments, 1):
                attachment_info += f"- Image {i}: {att.get('filename', 'unknown')} (URL: {att.get('url', 'N/A')})\n"
            attachment_info += "You can respond naturally about these images."
            formatted_content = formatted_content + attachment_info
            logger.info(f"Included {len(image_attachments)} image attachment(s) in message content")

        # Build batch content
        all_user_messages = [{"formatted_content": formatted_content, "content": content}]
        all_user_messages.extend(pending_messages)
        batch_content = "\n".join([msg["formatted_content"] for msg in all_user_messages])

        # Prepare messages for LM Studio
        history = list(conversation_history.get(channel_id, []))
        messages_for_lm = list(history)
        messages_for_lm.append({"role": "user", "content": batch_content})

        if pending_messages:
            logger.info(f"[{author_display}] in active session: {content[:50]}... (+{len(pending_messages)} queued)")
        else:
            logger.info(f"[{author_display}] in active session: {content[:50]}...")

        # Process via processor
        result = await self._processor.process_active_session(
            message=message,
            channel_id=channel_id,
            messages_for_lm=messages_for_lm,
            history=history,
            formatted_content=batch_content,
            pending_messages=pending_messages,
            typing_callback=typing_callback,
            conversation_history=conversation_history,
            on_message_callback=on_message_callback,
            call_lm_studio_func=self._call_lm_studio_via_processor,
            user_id=getattr(message, 'author', None) and str(message.author.id),
            guild_id=getattr(message, 'guild', None) and str(message.guild.id),
            user_message_content=content
        )

        # Check if processing was interrupted by a pending message
        if result and result.get("interrupted", False):
            pending_msg = result.get("pending_message")
            if pending_msg:
                logger.info(f"Processing interrupted by pending message: {pending_msg.get('author_display', 'unknown')}")
                # Return a special result to signal the caller to process the pending message
                return {
                    "usage": None,
                    "should_end_session": False,
                    "interrupted": True,
                    "pending_message": pending_msg
                }

        return result

    # --- LM Studio Call Wrapper ---

    async def _call_lm_studio_via_processor(
        self,
        messages_for_lm: List[Dict],
        tools: List[Dict],
        temperature: float,
        max_tokens: int,
        channel_id: int,
        use_tool_calling: bool
    ) -> Dict:
        """Wrapper for _call_lm_studio that matches the processor's expected signature.
        
        REASONING-FIX: When tool calling is enabled, uses tool-specific settings
        (tool_temperature, tool_max_tokens) for tool calls and final_max_tokens
        for final responses.
        """
        # Detect if this is a tool call turn (has tool_calls in context) or final response
        # We check the last few messages for tool_call presence to determine context
        has_tool_context = any(
            m.get("role") == "assistant" and "tool_calls" in m 
            for m in messages_for_lm[-5:] if isinstance(m, dict)
        )
        
        # Check if last user message contains a tool result (means we're waiting for final response)
        has_tool_result = any(
            m.get("role") == "tool" 
            for m in messages_for_lm[-3:] if isinstance(m, dict)
        )
        
        if use_tool_calling and tools:
            # Determine which settings to use based on context
            if has_tool_result:
                # This is a final response after tool result - use final settings
                effective_temp = self.temperature
                effective_max_tokens = self._final_max_tokens
                logger.debug(f"[tools-config] Final response after tool result: temp={effective_temp}, max_tokens={effective_max_tokens}")
            else:
                # This is a tool call turn - use tool-specific settings
                effective_temp = self._tool_temperature
                effective_max_tokens = self._tool_max_tokens
                logger.debug(f"[tools-config] Tool call turn: temp={effective_temp}, max_tokens={effective_max_tokens}")
            
            return await self._call_lm_studio(
                self.lm_studio_client.chat_with_tools,
                messages_for_lm, tools, effective_temp, effective_max_tokens,
                channel_id=channel_id
            )
        else:
            return await self._call_lm_studio(
                lambda: self.lm_studio_client.chat(
                    messages=messages_for_lm,
                    temperature=temperature,
                    max_tokens=max_tokens
                ),
                channel_id=channel_id
            )
