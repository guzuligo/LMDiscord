"""
Message Handler Module

Handles Discord message processing including:
- New session message handling
- Active session message batching
- LM Studio response generation
- Tool calling and execution (with image support)
- Response posting to Discord
- Token usage tracking
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional, Callable, TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from asyncio import Lock

import aiohttp
import discord

from src.tools.executor import ToolExecutor

logger = logging.getLogger(__name__)

# Image download configuration
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
DOWNLOAD_TIMEOUT = 30  # seconds
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}


class SafeImageDownloader:
    """Safely downloads images with whitelist-based hostname validation."""

    def __init__(self, allowed_hostnames: Optional[List[str]] = None):
        """Initialize with allowed hostnames whitelist.
        
        Args:
            allowed_hostnames: List of allowed hostnames (e.g., ['cdn.discordapp.com'])
        """
        self.allowed_hostnames = allowed_hostnames or []

    def is_hostname_allowed(self, url: str) -> tuple:
        """Check if a URL's hostname is in the allowed list.
        
        Args:
            url: The URL to check
            
        Returns:
            Tuple of (is_allowed: bool, reason: str)
        """
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname or ""
        
        # Check scheme
        if scheme not in ("http", "https"):
            return False, f"Blocked disallowed scheme: {scheme}"
        
        # Check hostname against whitelist
        if not hostname:
            return False, "Blocked: empty hostname"
        
        if hostname in self.allowed_hostnames:
            logger.info(f"ALLOWED: hostname '{hostname}' is in allowed list")
            return True, "Hostname is in allowed whitelist"
        
        logger.warning(f"BLOCKED: hostname '{hostname}' is NOT in allowed list: {self.allowed_hostnames}")
        return False, f"Hostname '{hostname}' not in allowed hostnames"

    async def download_image(self, url: str) -> bytes:
        """Safely download an image from a URL.
        
        Validates hostname against whitelist, checks content type,
        enforces size limits and timeouts.
        
        Args:
            url: URL to download from
            
        Returns:
            Raw image bytes
            
        Raises:
            ValueError: If URL is blocked or validation fails
            asyncio.TimeoutError: If download times out
        """
        # Step 1: Validate hostname
        allowed, reason = self.is_hostname_allowed(url)
        if not allowed:
            raise ValueError(f"URL blocked: {reason} (URL: {url})")

        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        logger.info(f"Downloading image from allowed host: {hostname}")

        # Step 2: Download with timeout and size limit
        timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as response:
                # Step 3: Validate content type
                content_type = response.content_type.lower()
                if content_type not in ALLOWED_CONTENT_TYPES:
                    raise ValueError(f"Blocked: disallowed content type '{content_type}' (expected one of {ALLOWED_CONTENT_TYPES})")
                logger.info(f"Content type allowed: {content_type}")

                # Step 4: Download with size limit
                raw_bytes = b""
                async for chunk in response.content.iter_chunked(1024 * 1024):  # 1MB chunks
                    raw_bytes += chunk
                    if len(raw_bytes) > MAX_IMAGE_SIZE:
                        raise ValueError(f"Blocked: image exceeds size limit ({len(raw_bytes)} bytes > {MAX_IMAGE_SIZE} bytes)")
                    logger.debug(f"Downloaded {len(raw_bytes)} bytes so far...")

        logger.info(f"Successfully downloaded {len(raw_bytes)} bytes from {hostname}")
        return raw_bytes


# Global safe image downloader instance
_safe_downloader = None


def get_safe_downloader(allowed_hostnames: Optional[List[str]] = None) -> SafeImageDownloader:
    """Get or create the global safe image downloader instance.
    
    Args:
        allowed_hostnames: Optional list of allowed hostnames (cached on first call)
        
    Returns:
        SafeImageDownloader instance
    """
    global _safe_downloader
    if _safe_downloader is None:
        _safe_downloader = SafeImageDownloader(allowed_hostnames=allowed_hostnames or [])
    return _safe_downloader


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
        max_tokens: int = 2500,
        use_tool_calling: bool = True,
        tools: Optional[List[Dict[str, Any]]] = None,
        executor: Optional[ThreadPoolExecutor] = None,
        tool_executor_instance: Optional[ToolExecutor] = None,
        allowed_image_hostnames: Optional[List[str]] = None,
        lm_studio_lock: Optional["Lock"] = None
    ):
        """Initialize message handler.

        Args:
            lm_studio_client: LMStudioClient instance
            system_prompt: System prompt for LM Studio
            temperature: Temperature for responses
            max_tokens: Max tokens for responses
            use_tool_calling: Whether to use tool calling
            tools: List of tool definitions
            executor: Thread pool executor for blocking calls
            tool_executor_instance: Optional ToolExecutor instance with registered tools
            allowed_image_hostnames: List of allowed hostnames for image downloads
            lm_studio_lock: Global asyncio.Lock to serialize LM Studio API calls
        """
        self.lm_studio_client = lm_studio_client
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.use_tool_calling = use_tool_calling
        self._tools = tools or [self.END_SESSION_TOOL]
        self._executor = executor or ThreadPoolExecutor(max_workers=2)
        self._lm_studio_lock = lm_studio_lock
        
        # Set up tool executor (for executing tool calls from LM Studio)
        self._tool_executor = tool_executor_instance
        self._tools_dict = {}  # name -> tool instance mapping
        if self._tool_executor is None:
            # Build tools dict from registered tools if no executor provided
            self._tools_dict = {
                "end_session": {"type": "builtin", "definition": self.END_SESSION_TOOL}
            }
        
        # Set up safe image downloader with allowed hostnames
        self._allowed_hostnames = allowed_image_hostnames or []
        self._safe_downloader = get_safe_downloader(allowed_hostnames=self._allowed_hostnames)
        logger.info(f"Safe image downloader initialized with allowed hostnames: {self._allowed_hostnames}")

    @property
    def tools(self) -> List[Dict[str, Any]]:
        """Get the list of tools."""
        return self._tools

    def set_tools(self, tools: List[Dict[str, Any]]) -> None:
        """Set the list of tools."""
        self._tools = tools

    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt."""
        self.system_prompt = prompt

    def set_params(self, temperature: float = 0.7, max_tokens: int = 2500) -> None:
        """Set LM Studio parameters."""
        self.temperature = temperature
        self.max_tokens = max_tokens

    def register_tool(self, tool_name: str, tool_instance: Any) -> None:
        """Register a tool instance for execution.
        
        Args:
            tool_name: Name of the tool
            tool_instance: Tool instance with execute() method
        """
        self._tools_dict[tool_name] = {"type": "tool", "instance": tool_instance}
        # Update tool definitions list
        if hasattr(tool_instance, 'to_dict'):
            tool_def = tool_instance.to_dict()
            if tool_def not in self._tools:
                self._tools.append(tool_def)

    async def _call_lm_studio(self, api_call_func, *args, channel_id: Optional[int] = None) -> Dict:
        """Call LM Studio API with global lock to prevent concurrent requests.
        
        This ensures only one LM Studio API call is in progress at a time,
        preventing OOM errors on the LM Studio server.
        
        Args:
            api_call_func: The synchronous API function to call
            *args: Arguments to pass to the API function
            channel_id: Optional channel ID for logging
            
        Returns:
            LM Studio API response dict
        """
        channel_info = f" (channel {channel_id})" if channel_id else ""
        
        if self._lm_studio_lock is not None:
            # Acquire global lock before making API call
            logger.info(f"Waiting for LM Studio lock{channel_info}")
            async with self._lm_studio_lock:
                logger.info(f"Acquired LM Studio lock{channel_info}, calling API")
                result = await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    api_call_func,
                    *args
                )
                logger.info(f"Released LM Studio lock{channel_info}")
                return result
        else:
            # Fallback: no lock available, call directly
            logger.warning(f"No LM Studio lock available{channel_info}, calling API directly")
            return await asyncio.get_event_loop().run_in_executor(
                self._executor,
                api_call_func,
                *args
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
        image_attachments: Optional[List[Dict]] = None
    ) -> None:
        """Handle a new session message (mention or reply).

        Args:
            message: Discord message object
            content: Message content
            message_type: 'mention' or 'reply'
            channel_id: Discord channel ID
            author_name: Author's Discord username (stable identifier)
            author_display: Author's Discord display name (can be changed)
            author_nick: Author's per-server nickname (can be None, server-specific)
            user_id: Author's Discord user ID (immutable unique identifier)
            conversation_history: Dict of channel_id -> message history
            typing_callback: Async callback to show typing indicator
            on_message_callback: Optional callback for GUI updates
            image_attachments: List of image attachment dicts with url, filename
        """
        channel = message.channel

        # Build system prompt with full user identity context
        # This enables the LLM to know how to address the user and track identity changes
        identity_context = ""
        if user_id or author_name:
            identity_parts = []
            identity_parts.append("\n\nYou are in a Discord server. The person you are talking to has the following Discord identity information:")
            identity_parts.append(f"\n- **Discord username** (stable, global identifier): `{author_name}`")
            
            if author_nick:
                identity_parts.append(f"\n- **Per-server nickname** (server-specific, can be different per server): `{author_nick}`")
                identity_parts.append("\n  → Use this nickname when addressing this user. Nicknames are server-specific — the same person may have different nicknames in different servers.")
            elif author_display and author_display != author_name:
                identity_parts.append(f"\n- **Display name** (global, can be changed by the user): `{author_display}`")
            else:
                identity_parts.append(f"\n- **Display name** (same as username): `{author_display or author_name}`")
            
            if user_id:
                identity_parts.append(f"\n- **Discord user ID** (unique, immutable, cannot change): `{user_id}`")
            
            identity_parts.append("\n**Important guidelines:**")
            identity_parts.append("1. These are Discord identifiers, NOT real-world names.")
            identity_parts.append("2. The user ID is the most stable way to identify this user across time.")
            identity_parts.append("3. The nickname or display name may change — use the current one when addressing them.")
            identity_parts.append("4. If the user shares their real name or personal info, associate it with their Discord username for this session.")
            identity_parts.append("5. The same user may have different nicknames in different servers — treat each server identity as separate.")
            identity_context = "\n".join(identity_parts)

        system_prompt = self.system_prompt + (
            identity_context +
            "\n\nUsers will mention you or reply to you to start conversations.\n"
            "When someone mentions you (e.g., @Bot hello), respond naturally.\n"
            "Only respond when the message appears to be directed at you.\n\n"
            "You have access to tools:\n"
            "- 'image_describe': Call this ONLY when the user explicitly asks for an image to be described, analyzed, or identified (e.g., 'what is in this image', 'describe this picture', 'what does this show').\n"
            "- If the user sends an image but does NOT explicitly ask for it to be described, respond naturally about the image in text (e.g., 'Nice picture!', 'That looks great!'). Do NOT call image_describe automatically.\n"
            "- 'end_session': Call this when the conversation is ending and you want to say goodbye\n\n"
            "IMPORTANT: Do not call image_describe for every image. Only call it when the user clearly wants a detailed description of the image.\n"
        )
        
        # If there are image attachments, include their info in the user message
        if image_attachments:
            attachment_info = "\n\nThe user has attached the following image(s):\n"
            for i, att in enumerate(image_attachments, 1):
                attachment_info += f"- Image {i}: {att.get('filename', 'unknown')} (URL: {att.get('url', 'N/A')})\n"
            attachment_info += "If you need to describe these images, call the image_describe tool with the image URL."
            content = content + attachment_info
        # Initialize conversation history
        if channel_id not in conversation_history:
            conversation_history[channel_id] = []

        # Add system prompt (with user identity)
        if not conversation_history[channel_id]:
            conversation_history[channel_id].append({
                "role": "system",
                "content": system_prompt
            })

        # Add user message with full identity attribution
        # Include all identity info so the LLM sees the complete picture from the start
        full_content = content
        if author_nick and author_nick != author_name:
            # Has per-server nickname — include all identity layers
            full_content = (
                f"[From user '{author_name}' "
                f"(nickname: '{author_nick}', "
                f"display: '{author_display}')]: {content}"
            )
        elif author_display and author_display != author_name:
            # No nickname, but display differs from username
            full_content = (
                f"[From user '{author_name}' "
                f"(display: '{author_display}')]: {content}"
            )
        elif author_name:
            # Minimal attribution
            full_content = f"[From user '{author_name}']: {content}"
        conversation_history[channel_id].append({
            "role": "user",
            "content": full_content
        })

        # Process with LM Studio
        await self._process_message(
            message,
            channel_id,
            conversation_history,
            typing_callback,
            is_active_session=False,
            on_message_callback=on_message_callback
        )

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
        display_changed: bool = False
    ) -> None:
        """Handle batched messages during an active session.

        Args:
            message: Discord message object
            content: Main message content
            channel_id: Discord channel ID
            author_name: Author's Discord username (stable)
            author_display: Author's current Discord display name
            author_nick: Author's current per-server nickname (can be None)
            initial_nick: Nickname at session start (for change detection)
            session_user: User who started the session
            pending_messages: List of queued message dicts
            conversation_history: Dict of channel_id -> message history
            typing_callback: Async callback to show typing indicator
            on_message_callback: Optional callback for GUI updates
            image_attachments: List of image attachment dicts
            nick_changed: Whether the nickname has changed since session start
            display_changed: Whether the display name has changed since session start
        """
        # Skip empty messages
        if not content or not content.strip():
            logger.info(f"Skipping empty message for channel {channel_id}")
            return

        # Format main message with identity attribution
        # Include nickname change info when the user has changed their nickname during the session
        if author_name == session_user:
            # Same user as session starter — include identity context
            if nick_changed and initial_nick:
                # Nickname changed — inform the LLM
                nick_now = author_nick if author_nick else "(none)"
                formatted_content = (
                    f"[{author_name} (was: {initial_nick}, now: {nick_now})]: {content}"
                )
            elif author_nick and author_nick != author_name:
                # Has nickname — include it
                formatted_content = (
                    f"[{author_name} (nickname: {author_nick})]: {content}"
                )
            elif author_display and author_display != author_name:
                # No nickname but display differs
                formatted_content = (
                    f"[{author_name} (display: {author_display})]: {content}"
                )
            else:
                formatted_content = content
        else:
            # Different user in the same channel — include identity
            if author_nick and author_nick != author_name:
                formatted_content = (
                    f"{author_nick} ({author_name}) says: {content}"
                )
            elif author_display and author_display != author_name:
                formatted_content = (
                    f"{author_display} ({author_name}) says: {content}"
                )
            else:
                formatted_content = f"{author_display} says: {content}"
        
        # If there are image attachments, include their info
        if image_attachments:
            attachment_info = "\n\nThe user has attached the following image(s):\n"
            for i, att in enumerate(image_attachments, 1):
                attachment_info += f"- Image {i}: {att.get('filename', 'unknown')} (URL: {att.get('url', 'N/A')})\n"
            attachment_info += "If you need to describe these images, call the image_describe tool with the image URL."
            formatted_content = formatted_content + attachment_info
            logger.info(f"Included {len(image_attachments)} image attachment(s) in message content")

        # Build batch content from main message + all pending messages
        all_user_messages = [{"formatted_content": formatted_content, "content": content}]
        all_user_messages.extend(pending_messages)

        batch_content_parts = [msg["formatted_content"] for msg in all_user_messages]
        batch_content = "\n".join(batch_content_parts)

        # Prepare messages for LM Studio
        history = list(conversation_history.get(channel_id, []))
        messages_for_lm = list(history)
        messages_for_lm.append({
            "role": "user",
            "content": batch_content
        })

        if pending_messages:
            logger.info(f"[{author_display}] in active session: {content[:50]}... (+{len(pending_messages)} queued)")
        else:
            logger.info(f"[{author_display}] in active session: {content[:50]}...")

        # Process with LM Studio
        return await self._process_active_session(
            message,
            channel_id,
            messages_for_lm,
            history,
            formatted_content,
            pending_messages,
            typing_callback,
            conversation_history,
            on_message_callback=on_message_callback
        )

    # --- Core Processing Logic ---

    async def _process_message(
        self,
        message: Any,
        channel_id: int,
        conversation_history: Dict[int, List[Dict[str, str]]],
        typing_callback: Callable,
        is_active_session: bool = False,
        on_message_callback: Optional[Callable] = None
    ) -> None:
        """Core message processing with LM Studio.

        Args:
            message: Discord message object
            channel_id: Discord channel ID
            conversation_history: Conversation history dict
            typing_callback: Async typing indicator callback
            is_active_session: Whether this is an active session
            on_message_callback: Optional GUI callback
        """
        channel = message.channel
        messages_for_lm = list(conversation_history.get(channel_id, []))

        # Show typing indicator
        await typing_callback(channel)

        response_text = None
        discord_response = None
        final_tool_calls = None
        final_usage = None

        try:
            for turn in range(3):  # Max 3 turns
                logger.info(f"{'Active session' if is_active_session else 'New session'} turn {turn + 1} for channel {channel_id}")

                if turn > 0:
                    await typing_callback(channel)

                # Call LM Studio (serialized via global lock)
                if self.use_tool_calling:
                    response = await self._call_lm_studio(
                        self.lm_studio_client.chat_with_tools,
                        messages_for_lm,
                        self.tools,
                        self.temperature,
                        self.max_tokens,
                        channel_id=channel_id
                    )
                else:
                    response = await self._call_lm_studio(
                        lambda: self.lm_studio_client.chat(
                            messages=messages_for_lm,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens
                        ),
                        channel_id=channel_id
                    )

                # Extract usage data
                turn_usage = response.get("usage")
                if turn_usage:
                    final_usage = turn_usage

                choices = response.get("choices", [])
                if not choices:
                    logger.warning(f"No choices in response on turn {turn + 1}")
                    break

                message_data = choices[0].get("message", {})
                response_text = message_data.get("content", "")
                tool_calls = message_data.get("tool_calls", [])

                logger.info(f"Turn {turn + 1}: content={repr(response_text[:100])}, tool_calls={len(tool_calls) if tool_calls else 0}")

                # Build assistant message
                assistant_msg = {"role": "assistant", "content": response_text}
                if tool_calls:
                    assistant_msg["tool_calls"] = tool_calls
                messages_for_lm.append(assistant_msg)

                if not tool_calls:
                    logger.info(f"Got final response on turn {turn + 1}")
                    break

                # Process tool calls
                for tool_call in tool_calls:
                    func = tool_call.get("function", {})
                    func_name = func.get("name", "")
                    tool_call_id = tool_call.get("id", "")
                    func_args = func.get("arguments", "{}")

                    logger.info(f"Turn {turn + 1}: LM Studio called tool: {func_name}")

                    if func_name == "end_session":
                        try:
                            args = json.loads(func_args)
                            farewell = args.get("farewell_message", "Goodbye!")
                            if len(farewell) > 2000:
                                farewell = farewell[:1997] + "..."
                            await channel.send(farewell)
                            logger.info("Farewell message posted")
                        except (json.JSONDecodeError, Exception) as e:
                            logger.error(f"Error processing end_session: {e}")
                        response_text = None
                        break
                    elif func_name == "image_describe":
                        # Execute image_describe tool with safe download
                        # Fix 2c: Use isolated context window for image description to avoid
                        # context overflow from large base64 image data in conversation history.
                        # Process: (1) Get description with mini-context, (2) Store description as text,
                        # (3) Continue conversation without base64 data.
                        image_description = None
                        try:
                            args = json.loads(func_args)
                            image_data = args.get("image_data", "")
                            mime_type = args.get("mime_type", "image/jpeg")
                            
                            logger.info(f"Executing image_describe tool with image_data length: {len(image_data)}")
                            
                            # Check if image_data is a URL (Discord CDN)
                            if image_data.startswith("http"):
                                # Download image safely with hostname validation
                                raw_bytes = await self._safe_downloader.download_image(image_data)
                                
                                logger.info(f"Downloaded {len(raw_bytes)} bytes from URL")
                                
                                # Resize and compress
                                from src.utils import resize_image_bytes, image_to_base64
                                compressed_bytes, output_mime = resize_image_bytes(
                                    raw_bytes,
                                    max_dimension=768,
                                    quality=85
                                )
                                processed_base64 = image_to_base64(compressed_bytes)
                                
                                # Fix 2c: Use an ISOLATED mini-context for image description only.
                                # This prevents the large base64 data from polluting the main conversation.
                                mini_context = [
                                    {"role": "user", "content": [
                                        {"type": "text", "text": "Please describe this image in detail, up to 3-4 sentences."},
                                        {"type": "image_url", "image_url": {"url": f"data:{output_mime};base64,{processed_base64}"}}
                                    ]}
                                ]
                                
                                # Get description using mini-context (no conversation history)
                                logger.info(f"[Fix 2c] Using isolated mini-context for image description")
                                mini_response = await self._call_lm_studio(
                                    self.lm_studio_client.chat,
                                    mini_context,
                                    self.temperature,
                                    self.max_tokens,
                                    channel_id=channel_id
                                )
                                
                                # Extract description from response
                                mini_choices = mini_response.get("choices", [])
                                if mini_choices:
                                    image_description = mini_choices[0].get("message", {}).get("content", "Could not describe the image.")
                                else:
                                    image_description = "Could not describe the image (no response from LM Studio)."
                                
                                logger.info(f"[Fix 2c] Image description obtained: {repr(image_description[:80])}...")
                                
                                # Replace the tool call with the description as plain text in the conversation
                                # Remove the assistant message that called the tool, add tool result with description
                                messages_for_lm.pop()  # Remove assistant message with tool call
                                messages_for_lm.append({
                                    "role": "user",
                                    "content": f"The image has been described. Here's what was in the image: {image_description}. Please continue the conversation naturally, incorporating this information."
                                })
                                # Continue with the main conversation (no base64, no vision messages)
                                break
                                
                        except ValueError as e:
                            # Security violation - URL was blocked
                            logger.warning(f"Image download blocked: {e}")
                            # Fix 2b: User-friendly error instead of raw security message
                            tool_result = (
                                "The image URL could not be processed. "
                                "This may be due to the image being hosted on an unsupported domain, "
                                "or the URL may not be publicly accessible. "
                                "Please try using an image from Discord's CDN instead."
                            )
                            messages_for_lm.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": tool_result
                            })
                        except Exception as e:
                            logger.error(f"Error executing image_describe: {e}", exc_info=True)
                            tool_result = f"Error processing image: {str(e)}"
                            messages_for_lm.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": tool_result
                            })
                    else:
                        tool_result = f"Unknown tool: {func_name}"
                        messages_for_lm.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": tool_result
                        })

                final_tool_calls = tool_calls

            if response_text and len(response_text) > 2000:
                response_text = response_text[:1997] + "..."

        except ConnectionError as e:
            logger.error(f"LM Studio connection error: {e}")
            response_text = "Sorry, I couldn't connect to LM Studio."
            await channel.send(response_text)
        except Exception as e:
            logger.error(f"Error getting LM Studio response: {e}", exc_info=True)
            response_text = "Sorry, I encountered an error processing your message."
            await channel.send(response_text)

        # Post response
        if response_text and response_text.strip():
            try:
                discord_response = await channel.send(response_text)
                logger.info("Response posted to Discord")
            except discord.HTTPException as e:
                logger.error(f"Failed to post response: {e}")
        elif final_tool_calls:
            logger.info("LM Studio used tool call, no text response to post")

        # Update conversation history
        if response_text:
            conversation_history[channel_id].append({
                "role": "assistant",
                "content": response_text
            })

        # Call GUI callback
        if on_message_callback and discord_response:
            actual_response = discord_response.content if hasattr(discord_response, 'content') else response_text
            asyncio.create_task(on_message_callback(actual_response))

        return final_usage

    async def _process_active_session(
        self,
        message: Any,
        channel_id: int,
        messages_for_lm: List[Dict[str, str]],
        history: List[Dict[str, str]],
        formatted_content: str,
        pending_messages: List[Dict[str, str]],
        typing_callback: Callable,
        conversation_history: Dict[int, List[Dict[str, str]]],
        on_message_callback: Optional[Callable] = None
    ) -> Optional[Dict[str, Any]]:
        """Process active session messages.

        Args:
            message: Discord message object
            channel_id: Discord channel ID
            messages_for_lm: Messages for LM Studio API
            history: Conversation history
            formatted_content: Formatted user message
            pending_messages: Queued messages
            typing_callback: Async typing callback
            on_message_callback: Optional GUI callback

        Returns:
            Final usage data or None
        """
        response_text = None
        final_tool_calls = None
        final_usage = None
        should_end_session = False
        farewell_message = None

        try:
            # Truncate conversation history to prevent context overflow.
            # Keep system prompt + last ~10 exchanges (20 messages) to ensure
            # LM Studio always receives a manageable context.
            MAX_HISTORY_MESSAGES = 20  # 10 user/assistant pairs
            if len(messages_for_lm) > MAX_HISTORY_MESSAGES:
                # Keep system prompt (index 0) + last MAX_HISTORY_MESSAGES - 1 messages
                messages_for_lm = [messages_for_lm[0]] + messages_for_lm[-(MAX_HISTORY_MESSAGES - 1):]
                logger.info(f"Truncated conversation history to {len(messages_for_lm)} messages")

            for turn in range(3):
                logger.info(f"Active session turn {turn + 1} for channel {channel_id}")

                if turn > 0:
                    await typing_callback(message.channel)

                # Call LM Studio (serialized via global lock)
                if self.use_tool_calling:
                    response = await self._call_lm_studio(
                        self.lm_studio_client.chat_with_tools,
                        messages_for_lm,
                        self.tools,
                        self.temperature,
                        self.max_tokens,
                        channel_id=channel_id
                    )
                else:
                    response = await self._call_lm_studio(
                        lambda: self.lm_studio_client.chat(
                            messages=messages_for_lm,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens
                        ),
                        channel_id=channel_id
                    )

                turn_usage = response.get("usage")
                if turn_usage:
                    final_usage = turn_usage

                choices = response.get("choices", [])
                if not choices:
                    logger.warning(f"No choices on turn {turn + 1}")
                    break

                message_data = choices[0].get("message", {})
                response_text = message_data.get("content", "")
                tool_calls = message_data.get("tool_calls", [])

                logger.info(f"Turn {turn + 1}: content={repr(response_text[:100])}")

                assistant_msg = {"role": "assistant", "content": response_text}
                if tool_calls:
                    assistant_msg["tool_calls"] = tool_calls
                messages_for_lm.append(assistant_msg)

                if not tool_calls:
                    break

                for tool_call in tool_calls:
                    func = tool_call.get("function", {})
                    func_name = func.get("name", "")
                    tool_call_id = tool_call.get("id", "")
                    func_args = func.get("arguments", "{}")

                    if func_name == "end_session":
                        try:
                            args = json.loads(func_args)
                            farewell_message = args.get("farewell_message", "Goodbye!")
                            should_end_session = True
                        except (json.JSONDecodeError, AttributeError):
                            farewell_message = "Goodbye!"
                            should_end_session = True
                        response_text = None
                        messages_for_lm.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": farewell_message
                        })
                        # For end_session, break immediately - don't send tool result back to LM Studio
                        break
                    elif func_name == "image_describe":
                        # Execute image_describe tool with safe download
                        # Fix 2c: Use isolated context window for image description to avoid
                        # context overflow from large base64 image data in conversation history.
                        try:
                            args = json.loads(func_args)
                            image_data = args.get("image_data", "")
                            mime_type = args.get("mime_type", "image/jpeg")
                            
                            logger.info(f"Executing image_describe tool (active session) with image_data length: {len(image_data)}")
                            
                            # Check if image_data is a URL (Discord CDN)
                            if image_data.startswith("http"):
                                # Download image safely with hostname validation
                                raw_bytes = await self._safe_downloader.download_image(image_data)
                                
                                logger.info(f"Downloaded {len(raw_bytes)} bytes from URL")
                                
                                from src.utils import resize_image_bytes, image_to_base64
                                compressed_bytes, output_mime = resize_image_bytes(
                                    raw_bytes,
                                    max_dimension=768,
                                    quality=85
                                )
                                processed_base64 = image_to_base64(compressed_bytes)
                                
                                # Fix 2c: Use an ISOLATED mini-context for image description only.
                                # This prevents the large base64 data from polluting the main conversation.
                                mini_context = [
                                    {"role": "user", "content": [
                                        {"type": "text", "text": "Please describe this image in detail, up to 3-4 sentences."},
                                        {"type": "image_url", "image_url": {"url": f"data:{output_mime};base64,{processed_base64}"}}
                                    ]}
                                ]
                                
                                # Get description using mini-context (no conversation history)
                                logger.info(f"[Fix 2c] Using isolated mini-context for image description (active session)")
                                mini_response = await self._call_lm_studio(
                                    self.lm_studio_client.chat,
                                    mini_context,
                                    self.temperature,
                                    self.max_tokens,
                                    channel_id=channel_id
                                )
                                
                                # Extract description from response
                                mini_choices = mini_response.get("choices", [])
                                if mini_choices:
                                    image_description = mini_choices[0].get("message", {}).get("content", "Could not describe the image.")
                                else:
                                    image_description = "Could not describe the image (no response from LM Studio)."
                                
                                logger.info(f"[Fix 2c] Image description obtained: {repr(image_description[:80])}...")
                                
                                # Replace the tool call with the description as plain text in the conversation
                                messages_for_lm.pop()  # Remove assistant message with tool call
                                messages_for_lm.append({
                                    "role": "user",
                                    "content": f"The image has been described. Here's what was in the image: {image_description}. Please continue the conversation naturally, incorporating this information."
                                })
                                # Continue with the main conversation (no base64, no vision messages)
                                break
                                
                        except ValueError as e:
                            # Security violation - URL was blocked
                            logger.warning(f"Image download blocked: {e}")
                            # Fix 2b: User-friendly error instead of raw security message
                            tool_result = (
                                "The image URL could not be processed. "
                                "This may be due to the image being hosted on an unsupported domain, "
                                "or the URL may not be publicly accessible. "
                                "Please try using an image from Discord's CDN instead."
                            )
                            messages_for_lm.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": tool_result
                            })
                        except Exception as e:
                            logger.error(f"Error executing image_describe: {e}", exc_info=True)
                            messages_for_lm.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": f"Error processing image: {str(e)}"
                            })
                    else:
                        messages_for_lm.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": f"Unknown tool: {func_name}"
                        })

                final_tool_calls = tool_calls

                # If end_session was called, break out of the turn loop immediately
                if should_end_session:
                    break

            if response_text and len(response_text) > 2000:
                response_text = response_text[:1997] + "..."

        except Exception as e:
            logger.error(f"Error in active session: {e}", exc_info=True)
            response_text = "Sorry, I encountered an error processing your message."

        # Update history
        history.append({"role": "user", "content": formatted_content})
        for pending in pending_messages:
            history.append({"role": "user", "content": pending["formatted_content"]})
        if response_text:
            assistant_msg = {"role": "assistant", "content": response_text}
            if final_tool_calls:
                assistant_msg["tool_calls"] = final_tool_calls
            history.append(assistant_msg)
        conversation_history[channel_id] = history

        # Handle session end
        if should_end_session:
            final_farewell = farewell_message or response_text or "Goodbye!"
            if len(final_farewell) > 2000:
                final_farewell = final_farewell[:1997] + "..."
            try:
                await message.channel.send(final_farewell)
                logger.info("Farewell message posted")
            except Exception as e:
                logger.error(f"Failed to post farewell: {e}")
        else:
            if response_text and response_text.strip():
                try:
                    await message.channel.send(response_text)
                    logger.info("Response posted from active session")
                except discord.HTTPException as e:
                    logger.error(f"Failed to post response: {e}")
            elif final_tool_calls:
                logger.info("LM Studio used tool call, no text response")

        return {
            "usage": final_usage,
            "should_end_session": should_end_session
        }
