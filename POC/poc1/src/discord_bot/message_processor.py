"""
Message Processor Module

Handles core message processing with LM Studio:
- process_message: New session message processing
- process_active_session: Active session message processing
- Delegates LM calls to LMCaller
- Delegates tool calling to ToolCallHandler
- Periodic status updates during multi-turn tool execution
- Cancellation support via CancellationManager
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Callable

from src.discord_bot.tool_executor import ToolCallHandler
from src.discord_bot.lm_caller import LMCaller
from src.discord_bot.cancellation import get_cancellation_manager
from src.memory.memory_manager import MemoryManager
from src.lm_studio_client import LMStudioError

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Core message processing with LM Studio."""

    def __init__(
        self,
        lm_studio_client: Any,
        temperature: float = 0.7,
        max_tokens: int = 2500,
        use_tool_calling: bool = True,
        tools: Optional[List[Dict[str, Any]]] = None,
        executor: Any = None,
        lm_studio_lock: Optional[Any] = None,
        safe_downloader: Optional[Any] = None,
        bot_instance: Any = None,
        max_tool_turns: int = 5,
        memory_manager: Optional[MemoryManager] = None,
        memory_recall_limit: int = 5,
        # Context management settings
        context_compression_enabled: bool = True,
        context_token_threshold: int = 80,
        context_message_threshold: int = 20,
        context_messages_to_keep_fresh: int = 6,
        context_summary_length: int = 300,
        context_lm_max_tokens: int = 4096,
    ):
        """Initialize message processor.

        Args:
            memory_manager: MemoryManager instance for recalling relevant memories.
            memory_recall_limit: Max memories to recall per query.
            context_compression_enabled: Whether automatic context compression is enabled.
            context_token_threshold: Token percentage threshold to trigger compression.
            context_message_threshold: Message count threshold to trigger compression.
            context_messages_to_keep_fresh: Number of recent messages to keep uncompressed.
            context_summary_length: Target summary length for compressed messages.
            context_lm_max_tokens: Maximum tokens for context compression LM calls.
        """
        self.lm_studio_client = lm_studio_client
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.use_tool_calling = use_tool_calling
        self._tools = tools or []
        self._safe_downloader = safe_downloader
        self._bot_instance = bot_instance
        self._max_tool_turns = max(1, min(max_tool_turns, 10))  # Clamp between 1-10
        self._tool_call_handler = ToolCallHandler()
        self._lm_caller = LMCaller(
            lm_studio_client=lm_studio_client,
            tools=self._tools,
            temperature=temperature,
            max_tokens=max_tokens,
            executor=executor,
            lm_studio_lock=lm_studio_lock,
            use_tool_calling=use_tool_calling
        )
        # Memory integration
        self._memory_manager = memory_manager
        self._memory_recall_limit = memory_recall_limit

        # Context management settings
        self._context_compression_enabled = context_compression_enabled
        self._context_token_threshold = context_token_threshold
        self._context_message_threshold = context_message_threshold
        self._context_messages_to_keep_fresh = context_messages_to_keep_fresh
        self._context_summary_length = context_summary_length
        self._context_lm_max_tokens = context_lm_max_tokens

    def set_params(self, temperature: float = 0.7, max_tokens: int = 2500) -> None:
        """Set LM Studio parameters."""
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._lm_caller.update_params(temperature=temperature, max_tokens=max_tokens)

    def set_tools(self, tools: List[Dict[str, Any]]) -> None:
        """Set the list of tools."""
        self._tools = tools
        self._lm_caller.update_params(tools=tools)

    def apply_tools_config(
        self,
        context_compression_enabled: bool = True,
        context_token_threshold: int = 80,
        context_message_threshold: int = 20,
        context_messages_to_keep_fresh: int = 6,
        context_summary_length: int = 300,
        context_lm_max_tokens: int = 4096
    ) -> None:
        """Apply context compression configuration changes.
        
        Args:
            context_compression_enabled: Whether automatic context compression is enabled.
            context_token_threshold: Token percentage threshold to trigger compression.
            context_message_threshold: Message count threshold to trigger compression.
            context_messages_to_keep_fresh: Number of recent messages to keep uncompressed.
            context_summary_length: Target summary length for compressed messages.
            context_lm_max_tokens: Maximum tokens for context compression LM calls.
        """
        self._context_compression_enabled = context_compression_enabled
        self._context_token_threshold = context_token_threshold
        self._context_message_threshold = context_message_threshold
        self._context_messages_to_keep_fresh = context_messages_to_keep_fresh
        self._context_summary_length = context_summary_length
        self._context_lm_max_tokens = context_lm_max_tokens
        logger.info(
            f"Context compression config updated: enabled={context_compression_enabled}, "
            f"token_threshold={context_token_threshold}%, message_threshold={context_message_threshold}, "
            f"keep_fresh={context_messages_to_keep_fresh}, summary_length={context_summary_length}, "
            f"lm_max_tokens={context_lm_max_tokens}"
        )

    # --- Core Processing Logic ---

    async def process_message(
        self,
        message: Any,
        channel_id: int,
        conversation_history: Dict[int, List[Dict[str, str]]],
        typing_callback: Callable,
        is_active_session: bool = False,
        on_message_callback: Optional[Callable] = None,
        call_lm_studio_func: Optional[Callable] = None,
        user_id: Optional[str] = None,
        guild_id: Optional[str] = None,
        user_message_content: Optional[str] = None
    ) -> Optional[Dict]:
        """Core message processing with LM Studio (new session).

        Args:
            user_id: Optional Discord user ID for memory recall.
            guild_id: Optional Discord guild/server ID for per-server memory isolation.
            user_message_content: Optional raw user message for memory recall query.
        """
        return await self._process_session(
            message, channel_id, conversation_history, typing_callback,
            is_active_session, on_message_callback, call_lm_studio_func,
            is_new_session=True,
            user_id=user_id,
            guild_id=guild_id,
            user_message_content=user_message_content
        )

    async def _process_session(
        self,
        message: Any,
        channel_id: int,
        conversation_history: Dict[int, List[Dict[str, str]]],
        typing_callback: Callable,
        is_active_session: bool,
        on_message_callback: Optional[Callable],
        call_lm_studio_func: Optional[Callable],
        is_new_session: bool = False,
        user_id: Optional[str] = None,
        guild_id: Optional[str] = None,
        user_message_content: Optional[str] = None
    ) -> Optional[Dict]:
        """Common session processing logic for both new and active sessions.

        Args:
            user_id: Optional Discord user ID for memory recall.
            guild_id: Optional Discord guild/server ID for per-server memory isolation.
            user_message_content: Optional raw user message for memory recall query.
        """
        channel = message.channel
        messages_for_lm = list(conversation_history.get(channel_id, []))

        # --- Memory Recall: Inject relevant memories before LM call ---
        if user_message_content and self._memory_manager:
            memory_context = self._recall_memories(
                query=user_message_content,
                user_id=user_id,
                guild_id=guild_id,
            )
            if memory_context:
                # Insert memory context after the system prompt (index 0)
                messages_for_lm.insert(1, {"role": "user", "content": memory_context})
                logger.info(f"Injected {len(messages_for_lm)} messages (including memory context) for channel {channel_id}")

        # --- Auto-Trigger Context Compression (FEAT-008) ---
        # Check if context compression is needed before making the LM call.
        # This prevents context overload by compressing old messages when
        # both token threshold and message count threshold are exceeded.
        compression_point = self.check_context_compression_needed(messages_for_lm)
        if compression_point is not None:
            logger.info(f"[auto_compress] Context compression needed at index {compression_point} for channel {channel_id}")
            messages_for_lm = await self._auto_compress_context(messages_for_lm, channel, compression_point, call_lm_studio_func)

        await typing_callback(channel)

        response_text = None
        discord_response = None
        final_tool_calls = None
        final_usage = None

        try:
            # Track failed tool turns for retry logic (failed turns don't count against limit)
            failed_tool_turns: List[int] = []
            # Track per-tool-type call counts to prevent specific tool infinite loops
            # Increased from 3 to 5 to allow LM more attempts to find relevant context
            tool_call_counts: Dict[str, int] = {}
            MAX_TOOL_CALLS_PER_TOOL = 5
            for turn in range(self._max_tool_turns):
                logger.info(f"{'Active session' if is_active_session else 'New session'} turn {turn + 1}/{self._max_tool_turns} for channel {channel_id}")
                if turn > 0:
                    await typing_callback(channel)

                # Determine max_tokens for this turn
                max_tokens_override = None
                # After tool processing, if previous response was empty, retry with higher max_tokens
                if turn > 0 and response_text == "" and final_tool_calls is not None:
                    max_tokens_override = min(self.max_tokens * 2, 8192)
                    logger.info(f"[max_tokens retry] Retrying with max_tokens={max_tokens_override} (was {self.max_tokens})")

                response = await self._execute_lm_call(
                    call_lm_studio_func, messages_for_lm, channel_id,
                    max_tokens_override=max_tokens_override
                )

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

                assistant_msg = {"role": "assistant", "content": response_text}
                if tool_calls:
                    assistant_msg["tool_calls"] = tool_calls
                messages_for_lm.append(assistant_msg)

                if not tool_calls:
                    # Check if response is empty after tool processing (max_tokens overflow)
                    if turn > 0 and response_text == "" and final_tool_calls is not None:
                        # Check if we have retry budget (failed turns don't count against limit)
                        effective_turns = turn - len(failed_tool_turns)
                        if max_tokens_override and max_tokens_override > self.max_tokens:
                            # Already retried with higher max_tokens and still empty → OOM or context too large
                            logger.warning(f"[max_tokens] Empty response even with max_tokens={max_tokens_override}. "
                                         f"LM Studio may be OOM. Suggest increasing server max_tokens.")
                            response_text = (
                                "⚠️ I was unable to generate a response. This may be because the conversation "
                                "context is too large or the server is running low on memory. "
                                "Please try starting a new session, or if you have control over the server, "
                                "try increasing the max_tokens setting or reducing the conversation history."
                            )
                        else:
                            # First retry attempt, add warning to context
                            messages_for_lm.append({
                                "role": "user",
                                "content": (
                                    "⚠️ NOTE: The previous response from me was empty. This may be because "
                                    "the response hit a token limit. If you have control over the server, "
                                    "try increasing max_tokens (currently set to " + str(self.max_tokens) + "). "
                                    "For now, please respond naturally using the information above."
                                )
                            })
                        continue
                    logger.info(f"Got final response on turn {turn + 1}")
                    break

                # Check for pending messages between turns (real-time interruption)
                pending_msg = await self.check_pending_messages(channel_id)
                if pending_msg:
                    logger.info(f"Pending message detected during turn {turn + 1}, interrupting tool processing")
                    # Return a special result indicating interruption with pending message
                    # This result will be passed back to message_handler which will process the pending message
                    return {
                        "response_text": None,
                        "tool_calls": None,
                        "usage": None,
                        "interrupted": True,
                        "pending_message": pending_msg
                    }

                # Track whether this tool turn succeeded or failed
                tool_turn_failed = False

                # Extract tool names and track per-tool call counts
                tool_names = [tc.get("function", {}).get("name", "") for tc in tool_calls]
                
                # If we were interrupted, skip tool processing and continue to next iteration
                if turn > 0 and pending_msg:
                    continue
                
                # Track per-tool-type call counts to detect infinite loops
                for tn in tool_names:
                    tool_call_counts[tn] = tool_call_counts.get(tn, 0) + 1
                
                # Check if any single tool exceeded its call limit
                exceeded_tool = None
                for tn, count in tool_call_counts.items():
                    if count >= MAX_TOOL_CALLS_PER_TOOL:
                        exceeded_tool = tn
                        logger.warning(f"Tool '{tn}' called {count} times (limit: {MAX_TOOL_CALLS_PER_TOOL}), forcing response")
                        break
                
                # Send a status message only if the LLM provided a custom one
                custom_status_msg = self._extract_status_message(tool_calls)
                if self._should_send_status(custom_status_msg):
                    await self._send_tool_status_message(channel, tool_names, turn + 1, custom_status_msg)

                response_text = await self._tool_call_handler.process_tool_calls(
                    tool_calls, messages_for_lm, channel, turn,
                    self._safe_downloader,
                    make_lm_call_func=lambda ctx, **kw: self._lm_caller.call(ctx, **kw),
                    get_bot_instance=lambda: self._bot_instance,
                    check_pending=lambda: self.check_pending_messages(channel_id)
                )

                # Check if processing was interrupted by a pending message
                if isinstance(response_text, dict) and response_text.get("interrupted", False):
                    pending_msg = response_text.get("pending_message")
                    if pending_msg:
                        logger.info(f"Processing interrupted by pending message during turn {turn + 1}")
                        return {
                            "response_text": None,
                            "tool_calls": None,
                            "usage": None,
                            "interrupted": True,
                            "pending_message": pending_msg
                        }

                # Detect failed tool turns: tool called but result was error (tool role message with error content)
                last_msgs = messages_for_lm[-3:]
                for m in last_msgs:
                    if m.get("role") == "tool" and "Error" in m.get("content", ""):
                        tool_turn_failed = True
                        break

                if tool_turn_failed:
                    failed_tool_turns.append(turn)
                    logger.info(f"Turn {turn + 1} tool call failed, will retry (failed turns: {len(failed_tool_turns)})")

                # If a tool exceeded its call limit, add a force-response hint and break
                if exceeded_tool:
                    messages_for_lm.append({
                        "role": "user",
                        "content": (
                            f"You have called '{exceeded_tool}' too many times. You MUST now respond to the user "
                            f"with a direct answer based on the information you already have. Do NOT call any more tools."
                        )
                    })
                    # Continue one more turn to let the model generate a response
                    final_tool_calls = tool_calls
                    continue

                # Do NOT break here. The loop should continue so LM Studio can process the tool results
                # and generate a final text response. Only break when LM returns no tool calls.
                final_tool_calls = tool_calls

            if response_text and len(response_text) > 2000:
                response_text = response_text[:1997] + "..."

            # === BUG-HANG-003 FIX: Enhanced empty response detection ===
            # LM Studio sometimes returns whitespace-only content ('\n\n') which should be
            # treated as empty. The old check `not response_text` fails for whitespace strings.
            if self._is_empty_response(response_text):
                if final_tool_calls is not None:
                    # LM made tool calls but returned empty content — inject results and retry
                    # BUG-HANG-004 FIX: Guard against None before slicing response_text
                    response_text_safe = response_text if response_text is not None else "(None)"
                    logger.warning(
                        f"[empty_response] Channel {channel_id}: empty/whitespace response after tool processing. "
                        f"final_tool_calls=present, failed_tool_turns={len(failed_tool_turns)}, "
                        f"response={repr(response_text_safe[:50])}"
                    )
                    # Inject tool results as a hint message and make one more LM call
                    injection_msg = self._build_tool_results_injection(
                        messages_for_lm, final_tool_calls, response_text, channel_id
                    )
                    messages_for_lm.append({"role": "user", "content": injection_msg})
                    
                    try:
                        await typing_callback(channel)
                        retry_response = await self._execute_lm_call(
                            call_lm_studio_func, messages_for_lm, channel_id
                        )
                        retry_choices = retry_response.get("choices", [])
                        if retry_choices:
                            retry_msg = retry_choices[0].get("message", {})
                            retry_text = retry_msg.get("content", "")
                            retry_tool_calls = retry_msg.get("tool_calls", [])
                            
                            if retry_text and retry_text.strip() and not retry_tool_calls:
                                # Successfully got a text response on retry
                                response_text = retry_text
                                final_tool_calls = None
                                logger.info(f"[empty_response] Retry succeeded: got text response for channel {channel_id}")
                            else:
                                # Retry also failed — use fallback message
                                logger.warning(f"[empty_response] Retry also returned empty/tool_calls for channel {channel_id}")
                                response_text = (
                                    "I've processed the available information but couldn't generate a complete response. "
                                    "This might be because the conversation context is too large. "
                                    "Please try starting a new session."
                                )
                        else:
                            response_text = (
                                "I've processed the available information but couldn't generate a complete response. "
                                "This might be because the conversation context is too large. "
                                "Please try starting a new session."
                            )
                    except Exception as retry_err:
                        logger.error(f"[empty_response] Retry failed for channel {channel_id}: {retry_err}")
                        response_text = (
                            "I've processed the available information but couldn't generate a complete response. "
                            "This might be because the conversation context is too large. "
                            "Please try starting a new session."
                        )
                else:
                    # LM returned empty content on turn 0 with no tool calls — pure LM failure
                    logger.warning(f"[empty_response] Channel {channel_id}: LM returned empty response on turn 0 "
                                   f"with no tool calls (pure LM silence)")
                    response_text = (
                        "Sorry, I couldn't generate a response. This might be a temporary issue. "
                        "Please try again or start a new session if the problem persists."
                    )

        except ConnectionError as e:
            logger.error(f"LM Studio connection error: {e}")
            response_text = "Sorry, I couldn't connect to LM Studio."
            try:
                await channel.send(response_text)
            except Exception as send_err:
                logger.error(f"Failed to send connection error message: {send_err}")
        except LMStudioError as e:
            # Handle LM Studio specific errors with detailed response body
            logger.error(f"LM Studio error (status {e.status_code}): {e}. Response: {getattr(e, 'response_body', '')[:500]}")
            response_text = self._format_lm_studio_error_message(e)
            try:
                await channel.send(response_text)
            except Exception as send_err:
                logger.error(f"Failed to send LM Studio error message: {send_err}")
                # Fallback: try sending a simpler message
                try:
                    await channel.send("⚠️ An error occurred while communicating with LM Studio. Please check the server logs.")
                except Exception as fallback_err:
                    logger.error(f"Fallback error message also failed: {fallback_err}")
            return  # Prevent double-send: error message already posted, skip post response section
        except Exception as e:
            error_str = str(e)
            # Check for LM Studio model loading failure (400 error with specific message)
            if self._is_model_load_error(error_str):
                logger.error(f"LM Studio model load failure: {e}")
                response_text = (
                    "⚠️ **MODEL NOT CONNECTED** — I couldn't load my AI model in LM Studio. "
                    "Please make sure LM Studio is running and a model is loaded before chatting."
                )
                try:
                    await channel.send(response_text)
                except Exception as send_err:
                    logger.error(f"Failed to send model load error message: {send_err}")
                return
            if self._is_oom_error(error_str):
                logger.error(f"Possible OOM error: {e}")
                response_text = (
                    "⚠️ I encountered an internal server error. This is likely due to the server "
                    "running out of memory (OOM). If you have control over the server, please check "
                    "the server logs and consider reducing the number of concurrent requests or "
                    "using a model with fewer parameters."
                )
            else:
                logger.error(f"Error getting LM Studio response: {e}", exc_info=True)
                response_text = "Sorry, I encountered an error processing your message."
            await channel.send(response_text)

        # Post response
        if response_text and response_text.strip():
            try:
                discord_response = await channel.send(response_text)
                logger.info("Response posted to Discord")
            except Exception as e:
                logger.error(f"Failed to post response: {e}")
        elif final_tool_calls:
            logger.info("LM Studio used tool call, no text response to post")

        # Update conversation history (new sessions only)
        if is_new_session and response_text:
            conversation_history[channel_id].append({
                "role": "assistant",
                "content": response_text
            })

        # Call GUI callback
        if on_message_callback and discord_response:
            actual_response = discord_response.content if hasattr(discord_response, 'content') else response_text
            asyncio.create_task(on_message_callback(actual_response))

        return {
            "usage": final_usage,
            "response_text": response_text,
            "tool_calls": final_tool_calls,
            "interrupted": False
        }

    async def process_active_session(
        self,
        message: Any,
        channel_id: int,
        messages_for_lm: List[Dict[str, str]],
        history: List[Dict[str, str]],
        formatted_content: str,
        pending_messages: List[Dict[str, str]],
        typing_callback: Callable,
        conversation_history: Dict[int, List[Dict[str, str]]],
        on_message_callback: Optional[Callable] = None,
        call_lm_studio_func: Optional[Callable] = None,
        user_id: Optional[str] = None,
        guild_id: Optional[str] = None,
        user_message_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process active session messages.

        Args:
            user_id: Optional Discord user ID for memory recall.
            guild_id: Optional Discord guild/server ID for per-server memory isolation.
            user_message_content: Optional raw user message for memory recall query.
        """
        response_text = None
        final_tool_calls = None
        final_usage = None
        should_end_session = False
        farewell_message = None

        try:
            # --- Memory Recall: Inject relevant memories before LM call ---
            if user_message_content and self._memory_manager:
                memory_context = self._recall_memories(
                    query=user_message_content,
                    user_id=user_id,
                    guild_id=guild_id,
                )
                if memory_context:
                    # Insert memory context after the system prompt (index 0)
                    messages_for_lm.insert(1, {"role": "user", "content": memory_context})
                    logger.info(f"Injected {len(messages_for_lm)} messages (including memory context) for channel {channel_id}")

            # Truncate conversation history to prevent context overflow
            MAX_HISTORY_MESSAGES = 20
            if len(messages_for_lm) > MAX_HISTORY_MESSAGES:
                messages_for_lm = [messages_for_lm[0]] + messages_for_lm[-(MAX_HISTORY_MESSAGES - 1):]
                logger.info(f"Truncated conversation history to {len(messages_for_lm)} messages")

            # Track total tool calls to prevent infinite tool-calling loops
            total_tool_calls_in_session = 0
            MAX_TOOL_CALLS_PER_SESSION = 10  # Increased to accommodate batched summarization (2+ LM calls per tool execution)
            force_response_break = False  # Flag to indicate we broke due to max tool calls
            # Track per-tool-type call counts to prevent specific tool infinite loops
            # Increased from 3 to 5 to allow LM more attempts to find relevant context
            tool_call_counts: Dict[str, int] = {}
            MAX_TOOL_CALLS_PER_TOOL = 5
            # Track failed tool turns for retry logic (failed turns don't count against limit)
            failed_tool_turns: List[int] = []

            for turn in range(self._max_tool_turns):
                logger.info(f"Active session turn {turn + 1}/{self._max_tool_turns} for channel {channel_id}")
                if turn > 0:
                    await typing_callback(message.channel)

                # Determine max_tokens for this turn
                max_tokens_override = None
                if turn > 0 and response_text == "" and final_tool_calls is not None:
                    max_tokens_override = min(self.max_tokens * 2, 8192)
                    logger.info(f"[max_tokens retry] Retrying with max_tokens={max_tokens_override} (was {self.max_tokens})")

                response = await self._execute_lm_call(
                    call_lm_studio_func, messages_for_lm, channel_id,
                    max_tokens_override=max_tokens_override
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
                    # Check if response is empty after tool processing (max_tokens overflow)
                    if turn > 0 and response_text == "" and final_tool_calls is not None:
                        if max_tokens_override and max_tokens_override > self.max_tokens:
                            logger.warning(f"[max_tokens] Empty response even with max_tokens={max_tokens_override}. "
                                         f"LM Studio may be OOM.")
                            response_text = (
                                "⚠️ I was unable to generate a response. This may be because the conversation "
                                "context is too large or the server is running low on memory. "
                                "Please try starting a new session, or if you have control over the server, "
                                "try increasing the max_tokens setting or reducing the conversation history."
                            )
                        else:
                            messages_for_lm.append({
                                "role": "user",
                                "content": (
                                    "⚠️ NOTE: The previous response from me was empty. This may be because "
                                    "the response hit a token limit. If you have control over the server, "
                                    "try increasing max_tokens (currently set to " + str(self.max_tokens) + "). "
                                    "For now, please respond naturally using the information above."
                                )
                            })
                        continue
                    break

                # Check for pending messages between turns (real-time interruption)
                pending_msg = await self.check_pending_messages(channel_id)
                if pending_msg:
                    logger.info(f"Pending message detected during active session turn {turn + 1}, interrupting")
                    # Return interruption result with pending message
                    return {
                        "usage": None,
                        "should_end_session": False,
                        "interrupted": True,
                        "pending_message": pending_msg
                    }

                # Process tool calls via ToolCallHandler
                tool_turn_failed = False

                # Extract tool names and track per-tool call counts
                tool_names = [tc.get("function", {}).get("name", "") for tc in tool_calls]
                
                # Track per-tool-type call counts to detect infinite loops
                for tn in tool_names:
                    tool_call_counts[tn] = tool_call_counts.get(tn, 0) + 1
                
                # Check if any single tool exceeded its call limit
                exceeded_tool = None
                for tn, count in tool_call_counts.items():
                    if count >= MAX_TOOL_CALLS_PER_TOOL:
                        exceeded_tool = tn
                        logger.warning(f"Tool '{tn}' called {count} times (limit: {MAX_TOOL_CALLS_PER_TOOL}), forcing response")
                        break
                
                # Send a status message only if the LLM provided a custom one
                custom_status_msg = self._extract_status_message(tool_calls)
                if self._should_send_status(custom_status_msg):
                    await self._send_tool_status_message(message.channel, tool_names, turn + 1, custom_status_msg)

                end_session_result = await self._tool_call_handler.process_tool_calls_active(
                    tool_calls, messages_for_lm, turn,
                    self._safe_downloader,
                    make_lm_call_func=lambda ctx, **kw: self._lm_caller.call(ctx, **kw),
                    get_bot_instance=lambda: self._bot_instance,
                    check_pending=lambda: self.check_pending_messages(channel_id)
                )

                # Check if processing was interrupted by a pending message
                if isinstance(end_session_result, dict) and end_session_result.get("interrupted", False):
                    pending_msg = end_session_result.get("pending_message")
                    if pending_msg:
                        logger.info(f"Active session processing interrupted by pending message during turn {turn + 1}")
                        return {
                            "usage": None,
                            "should_end_session": False,
                            "interrupted": True,
                            "pending_message": pending_msg
                        }

                if end_session_result:
                    should_end_session = True
                    farewell_message = end_session_result.get("farewell")
                    response_text = None
                    break

                # Detect failed tool turns: tool called but result was error
                last_msgs = messages_for_lm[-3:]
                for m in last_msgs:
                    if m.get("role") == "tool" and "Error" in m.get("content", ""):
                        tool_turn_failed = True
                        break

                if tool_turn_failed:
                    failed_tool_turns.append(turn)
                    logger.info(f"Active turn {turn + 1} tool call failed, will retry (failed turns: {len(failed_tool_turns)})")

                final_tool_calls = tool_calls

                # Track total tool calls and break if too many (prevents infinite loops)
                total_tool_calls_in_session += len(tool_calls) if tool_calls else 0
                
                # If a tool exceeded its call limit, add a force-response hint and break
                if exceeded_tool:
                    messages_for_lm.append({
                        "role": "user",
                        "content": (
                            f"You have called '{exceeded_tool}' too many times. You MUST now respond to the user "
                            f"with a direct answer based on the information you already have. Do NOT call any more tools."
                        )
                    })
                    force_response_break = True
                    break
                
                if total_tool_calls_in_session >= MAX_TOOL_CALLS_PER_SESSION:
                    logger.warning(f"Max tool calls ({MAX_TOOL_CALLS_PER_SESSION}) reached for channel {channel_id}, forcing response")
                    
                    # BUG-SEARCH-006 FIX: Inject actual tool results into context so LM can form
                    # a meaningful response instead of just a generic hint message.
                    # Extract the most recent tool results from conversation history.
                    tool_results = []
                    for msg in reversed(messages_for_lm[-15:]):
                        if msg.get("role") == "tool" and msg.get("content"):
                            content = msg["content"]
                            if isinstance(content, str) and content.strip():
                                tool_results.append(content.strip())
                    
                    if tool_results:
                        # Inject actual gathered data for the LM to use in its response
                        injection_msg = (
                            "⚠️ You have gathered enough information. You already have tool results "
                            "from your previous calls. Please respond to the user NOW using the "
                            "information you already collected. DO NOT call any more tools.\n\n"
                            "=== PREVIOUSLY GATHERED RESULTS ===\n"
                            + "\n\n".join(tool_results[-5:])  # Last 5 tool results max
                            + "\n\n=== END RESULTS ===\n\n"
                            "Respond with a natural answer based on the results above."
                        )
                        logger.info(f"[force_response] Injected {len(tool_results)} tool results for force-response")
                    else:
                        injection_msg = (
                            "You have enough information. Please respond to the user now with your answer. "
                            "Do NOT call any more tools."
                        )
                    messages_for_lm.append({"role": "user", "content": injection_msg})
                    force_response_break = True
                    break

            # If we broke due to max tool calls, make one final LM call to get a text response
            if force_response_break:
                logger.info(f"Making final response call after max tool calls for channel {channel_id}")
                try:
                    await typing_callback(message.channel)
                    final_response = await self._execute_lm_call(
                        call_lm_studio_func, messages_for_lm, channel_id
                    )
                    final_choices = final_response.get("choices", [])
                    if final_choices:
                        final_message_data = final_choices[0].get("message", {})
                        response_text = final_message_data.get("content", "")
                        final_tool_calls_from_response = final_message_data.get("tool_calls", [])
                        if final_tool_calls_from_response:
                            logger.warning(f"Final response still had tool calls, discarding them")
                        logger.info(f"Final response obtained: {repr(response_text[:100])}")
                except Exception as e:
                    logger.error(f"Failed to get final response after max tool calls: {e}")
                    response_text = None

            if response_text and len(response_text) > 2000:
                response_text = response_text[:1997] + "..."

            # === BUG-HANG-003 FIX: Enhanced empty response detection (active session) ===
            if self._is_empty_response(response_text):
                if final_tool_calls is not None:
                    # BUG-HANG-004 FIX: Guard against None before slicing response_text (active session)
                    response_text_safe = response_text if response_text is not None else "(None)"
                    logger.warning(
                        f"[empty_response] Active session channel {channel_id}: empty/whitespace response after tool processing. "
                        f"final_tool_calls=present, failed_tool_turns={len(failed_tool_turns)}, "
                        f"response={repr(response_text_safe[:50])}"
                    )
                    injection_msg = self._build_tool_results_injection(
                        messages_for_lm, final_tool_calls, response_text, channel_id
                    )
                    messages_for_lm.append({"role": "user", "content": injection_msg})
                    
                    try:
                        await typing_callback(message.channel)
                        retry_response = await self._execute_lm_call(
                            call_lm_studio_func, messages_for_lm, channel_id
                        )
                        retry_choices = retry_response.get("choices", [])
                        if retry_choices:
                            retry_msg = retry_choices[0].get("message", {})
                            retry_text = retry_msg.get("content", "")
                            retry_tool_calls = retry_msg.get("tool_calls", [])
                            
                            if retry_text and retry_text.strip() and not retry_tool_calls:
                                response_text = retry_text
                                final_tool_calls = None
                                logger.info(f"[empty_response] Retry succeeded: got text response for active session channel {channel_id}")
                            else:
                                logger.warning(f"[empty_response] Retry also failed for active session channel {channel_id}")
                                response_text = (
                                    "I've processed the available information but couldn't generate a complete response. "
                                    "This might be because the conversation context is too large. "
                                    "Please try starting a new session."
                                )
                        else:
                            response_text = (
                                "I've processed the available information but couldn't generate a complete response. "
                                "This might be because the conversation context is too large. "
                                "Please try starting a new session."
                            )
                    except Exception as retry_err:
                        logger.error(f"[empty_response] Retry failed for active session channel {channel_id}: {retry_err}")
                        response_text = (
                            "I've processed the available information but couldn't generate a complete response. "
                            "This might be because the conversation context is too large. "
                            "Please try starting a new session."
                        )
                else:
                    logger.warning(f"[empty_response] Active session channel {channel_id}: "
                                   f"LM returned empty response with no tool calls (pure LM silence)")
                    response_text = (
                        "Sorry, I couldn't generate a response. This might be a temporary issue. "
                        "Please try again or start a new session if the problem persists."
                    )

        except LMStudioError as e:
            # Handle LM Studio specific errors with detailed response body
            logger.error(f"LM Studio error in active session (status {e.status_code}): {e}. Response: {getattr(e, 'response_body', '')[:500]}")
            response_text = self._format_lm_studio_error_message(e)
            # Don't return here - in active sessions we still want to update history
            # But we need to prevent the double-send below
            history.append({"role": "user", "content": formatted_content})
            for pending in pending_messages:
                history.append({"role": "user", "content": pending["formatted_content"]})
            if response_text:
                assistant_msg = {"role": "assistant", "content": response_text}
                history.append(assistant_msg)
            conversation_history[channel_id] = history
            try:
                await message.channel.send(response_text)
                logger.info("Error response posted from active session")
            except Exception as send_err:
                logger.error(f"Failed to post error response: {send_err}")
                # Fallback: try sending a simpler message
                try:
                    await message.channel.send("⚠️ An error occurred while communicating with LM Studio.")
                except Exception as fallback_err:
                    logger.error(f"Fallback error message also failed: {fallback_err}")
            return  # Prevent double-send
        except Exception as e:
            error_str = str(e)
            # Check for LM Studio model loading failure (400 error with specific message)
            if self._is_model_load_error(error_str):
                logger.error(f"LM Studio model load failure in active session: {e}")
                response_text = (
                    "⚠️ **MODEL NOT CONNECTED** — I couldn't load my AI model in LM Studio. "
                    "Please make sure LM Studio is running and a model is loaded before chatting."
                )
                try:
                    await message.channel.send(response_text)
                except Exception as send_err:
                    logger.error(f"Failed to send model load error message: {send_err}")
            elif self._is_oom_error(error_str):
                logger.error(f"Possible OOM error in active session: {e}")
                response_text = (
                    "⚠️ I encountered an internal server error. This is likely due to the server "
                    "running out of memory (OOM). If you have control over the server, please check "
                    "the server logs and consider reducing the number of concurrent requests or "
                    "using a model with fewer parameters."
                )
            else:
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
                except Exception as e:
                    logger.error(f"Failed to post response: {e}")
            elif final_tool_calls:
                logger.info("LM Studio used tool call, no text response")

        return {"usage": final_usage, "should_end_session": should_end_session}

    # --- LM Studio Call Helpers ---

    async def _execute_lm_call(
        self,
        call_func: Optional[Callable],
        messages_for_lm: List[Dict],
        channel_id: int,
        max_tokens_override: Optional[int] = None
    ) -> Dict:
        """Execute LM Studio call via provided function or internal method.
        
        Args:
            call_func: Optional callable for the LM API call
            messages_for_lm: Messages to send
            channel_id: Channel ID for logging
            max_tokens_override: Optional override for max_tokens (used for retries)
        """
        effective_max_tokens = max_tokens_override or self.max_tokens
        if call_func:
            return await call_func(
                messages_for_lm, self._tools,
                self.temperature, effective_max_tokens,
                channel_id=channel_id, use_tool_calling=self.use_tool_calling
            )
        return await self._lm_caller.call(messages_for_lm, channel_id, self.use_tool_calling, max_tokens=effective_max_tokens)

    def _should_send_status(self, custom_message: Optional[str]) -> bool:
        """Decide whether to send a status message for this tool turn.

        Only send a status message if the LLM provided a custom
        `tell_user_you_are_working` message in the tool call arguments.
        This ensures status messages are always in-character and natural,
        rather than generic hardcoded text like "⏳ Searching channel history...".

        Args:
            custom_message: Custom status message from the LLM, or None.

        Returns:
            True if a status message should be sent.
        """
        return custom_message is not None

    def _is_model_load_error(self, error_str: str) -> bool:
        """Check if an error indicates LM Studio failed to load the model.

        LM Studio returns HTTP 400 with a JSON body like:
        {"error": "Failed to load model \"qwen3.6-35b-a3b\". Error: ..."}

        Args:
            error_str: The error string from the exception.

        Returns:
            True if this is a model loading error.
        """
        error_lower = error_str.lower()
        model_load_indicators = [
            "failed to load model",
            "failed to load model.",
            "model load failed",
            "unable to load model",
        ]
        return any(indicator in error_lower for indicator in model_load_indicators)

    def _format_lm_studio_error_message(self, error: "LMStudioError") -> str:
        """Format a user-friendly error message from LMStudioError.

        Provides clear, actionable feedback to the user WITHOUT leaking
        internal details like model names or specific error codes.

        Args:
            error: The LMStudioError exception.

        Returns:
            A formatted user-facing error message string.
        """
        status_code = error.status_code

        # Handle 400 Bad Request - model loading failures
        if status_code == 400:
            return (
                "⚠️ **UNABLE TO RESPOND**\n"
                "I couldn't connect to my AI brain. Please make sure LM Studio is "
                "running and a model is loaded before chatting."
            )

        # Handle 500 Internal Server Error - OOM or server issues
        if status_code == 500:
            return (
                "⚠️ **INTERNAL SERVER ERROR**\n"
                "I encountered an error processing your request. "
                "This is likely due to the server running out of memory (OOM) "
                "or the conversation context being too large.\n"
                "Please try starting a new session or reducing the conversation history."
            )

        # Handle 408 Request Timeout
        if status_code == 408:
            return (
                "⚠️ **REQUEST TIMEOUT**\n"
                "LM Studio took too long to respond. The model might be loading "
                "or the conversation is too long. Please try again."
            )

        # Handle connection-related errors
        if status_code in (403, 404):
            return (
                "⚠️ **LM STUDIO NOT AVAILABLE**\n"
                "I couldn't connect to LM Studio. Please make sure:\n"
                "1. LM Studio is running\n"
                "2. The API server is started (Load Model button)\n"
                "3. The hostname and port are correctly configured."
            )

        # Generic LM Studio error
        return (
            "⚠️ **LM STUDIO ERROR**\n"
            "An error occurred while communicating with LM Studio.\n"
            "Please check the server logs for details and try again."
        )

    def _parse_model_load_error(self, response_body: str) -> Optional[str]:
        """Parse LM Studio error response body to extract model name and error details.

        NOTE: This method is kept for logging/debugging purposes only. The user-facing
        message is now handled entirely by _format_lm_studio_error_message() which
        returns a generic message without leaking internal details.

        Args:
            response_body: The JSON response body from LM Studio.

        Returns:
            Always returns None to prevent leaking internal details to the user.
        """
        # Do NOT return a formatted message - this prevents leaking model names
        # and internal error details to the user. The generic message in
        # _format_lm_studio_error_message() is used instead.
        return None

    def _is_oom_error(self, error_str: str) -> bool:
        """Check if an error indicates OOM (Out of Memory)."""
        oom_indicators = ["out of memory", "oom", "cuda out of memory", "runtime error", "500",
                          "internal server error", "context length", "context exceeded",
                          "max context", "too many tokens"]
        error_lower = error_str.lower()
        return any(indicator in error_lower for indicator in oom_indicators)

    def _is_empty_response(self, text: Optional[str]) -> bool:
        """Check if a response is effectively empty (None, empty string, or whitespace-only).

        LM Studio sometimes returns whitespace-only content ('\\n\\n') which should be
        treated as an empty response that needs fallback handling.

        Args:
            text: The response text to check.

        Returns:
            True if the response is empty or whitespace-only.
        """
        return not text or not text.strip()

    def _build_tool_results_injection(
        self,
        messages_for_lm: List[Dict],
        final_tool_calls: Optional[List[Dict]],
        response_text: Optional[str],
        channel_id: int
    ) -> str:
        """Build a system message injecting gathered tool results for the LM to use.

        When the LM returns an empty response after tool processing, this extracts
        the tool results from conversation history and injects them as a new user
        message with explicit instructions to respond using the data.

        Args:
            messages_for_lm: Current conversation messages.
            final_tool_calls: The final tool calls returned by the LM.
            response_text: The empty response text.
            channel_id: Channel ID for logging.

        Returns:
            The injected message content string.
        """
        # Extract tool results from recent messages in conversation history
        tool_results = []
        for msg in reversed(messages_for_lm[-10:]):  # Check last 10 messages
            if msg.get("role") == "tool" and msg.get("content"):
                content = msg["content"]
                if isinstance(content, str) and content.strip():
                    tool_results.append(content.strip())

        if tool_results:
            injected = (
                "⚠️ RESPONSE ERROR: Your previous response was empty. "
                "You have already executed tool calls and received results. "
                "Please respond to the user NOW using the information you gathered.\n\n"
                "=== GATHERED RESULTS ===\n"
                + "\n\n".join(tool_results[-5:])  # Last 5 tool results max
                + "\n\n=== END RESULTS ===\n\n"
                "DO NOT call any more tools. Respond to the user with a natural answer "
                "based on the results above."
            )
            logger.info(f"[empty_response] Injected {len(tool_results)} tool results for channel {channel_id}")
            return injected

        return (
            "⚠️ Your previous response was empty. Please respond to the user "
            "with a direct answer. Do NOT call any tools."
        )

    def _extract_status_message(self, tool_calls: List[Dict]) -> Optional[str]:
        """Extract tell_user_you_are_working message from tool call arguments.

        Iterates over tool calls and returns the first non-empty
        tell_user_you_are_working value found.

        Args:
            tool_calls: List of tool call dicts from LM Studio response.

        Returns:
            Custom status message string, or None if not provided.
        """
        for tc in tool_calls:
            try:
                func = tc.get("function", {})
                args = json.loads(func.get("arguments", "{}"))
                msg = args.get("tell_user_you_are_working", "")
                if msg:
                    return msg.strip()
            except (json.JSONDecodeError, AttributeError):
                pass
        return None

    async def _send_tool_status_message(
        self, channel, tool_names: List[str], turn: int, custom_message: Optional[str] = None
    ) -> None:
        """Send a status message to Discord before executing time-consuming tools.

        Provides user feedback so they know the bot is working instead of going silent.
        If the LM provided a custom message via tell_user_you_are_working, use that
        instead of the generic tool display text.

        Args:
            channel: Discord channel to send the message to
            tool_names: List of tool names being executed
            turn: Current turn number
            custom_message: Optional LM-generated status message
        """
        if custom_message:
            status_text = custom_message
        else:
            # Deduplicate tool names for cleaner display
            unique_tools = list(dict.fromkeys(tool_names))

            # Build a human-readable status message
            tool_display = {
                "channel_search": "🔍 Searching channel history",
                "image_compare": "🖼️ Comparing/describing images",
                "comfyui_generate": "🎨 Generating image",
                "memory_tool": "🧠 Accessing memory",
                "math_calc": "🔢 Calculating",
            }

            status_parts = []
            for tool in unique_tools:
                display = tool_display.get(tool, f"⚙️ Running {tool}")
                status_parts.append(display)

            status_text = " | ".join(status_parts) + "..."

        try:
            await channel.send(f"⏳ {status_text}")
            logger.info(f"Turn {turn}: Sent tool status message: {status_text}")
        except Exception as e:
            logger.warning(f"Failed to send tool status message: {e}")

    def _is_max_tokens_overflow(self, response: Dict) -> bool:
        """Check if response indicates max_tokens overflow (empty content)."""
        choices = response.get("choices", [])
        if not choices:
            return True
        message = choices[0].get("message", {})
        content = message.get("content", "")
        finish_reason = choices[0].get("finish_reason", "")
        # Empty content with length finish_reason = max_tokens overflow
        if content == "" and finish_reason == "length":
            return True
        # Also detect empty content with no tool calls as potential overflow
        if content == "" and not message.get("tool_calls"):
            return True
        return False

    # --- Periodic Status Updates & Cancellation ---

    async def _check_cancellation(self, channel_id: int) -> bool:
        """Check if cancellation was requested for this channel.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if cancellation was requested (and event was reset)
        """
        manager = get_cancellation_manager()
        return await manager.check_and_reset(channel_id)
    
    async def check_pending_messages(self, channel_id: int) -> Optional[Dict]:
        """Check for pending messages that arrived during processing.
        
        This enables real-time message interleaving - if a new message
        arrived while the bot was processing tool calls, it will be
        returned here so the caller can interrupt and process it.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            Dict with pending message data if available, None otherwise.
            The dict contains: author_name, author_display, author_nick,
            content, formatted_content, image_attachments
        """
        # Import here to avoid circular imports
        from src.discord_bot.bot_core import get_bot_instance
        bot = get_bot_instance()
        if bot is None:
            return None
        
        # Check if there are pending messages for this channel
        pending = bot._pending_messages.get(channel_id)
        if not pending:
            return None
        
        # Check if session is still active (only process if session exists)
        if not bot._session_manager.is_active(channel_id):
            # Session expired, clear pending messages
            bot._pending_messages.pop(channel_id, None)
            return None
        
        # Get the first pending message (highest priority - oldest)
        if pending:
            return pending.pop(0)
        
        return None
    
    async def check_pending_messages_and_interrupt(self, channel_id: int, message) -> Optional[Dict]:
        """Check for pending messages and interrupt processing if found.
        
        This is a convenience method that checks for pending messages
        and sends a cancellation message to the channel if one is found.
        
        Args:
            channel_id: Discord channel ID
            message: Discord message object (for channel reference)
            
        Returns:
            Dict with pending message data if interrupted, None otherwise.
        """
        # Check for pending messages
        pending = await self.check_pending_messages(channel_id)
        if pending:
            logger.info(f"Pending message found for channel {channel_id}, interrupting processing")
            # Send a brief notification that we're switching to the new message
            try:
                await message.channel.send("📝 Switching to new message...")
            except Exception:
                pass
            return pending
        
        return None
    
    async def _send_periodic_status(
        self,
        channel,
        turn: int,
        total_turns: int,
        tool_names: List[str],
        elapsed_seconds: float,
        channel_id: int = 0
    ) -> None:
        """Send a periodic status update during long tool execution.
        
        Sends a "still working" message to keep the user engaged
        when tool execution takes longer than 10 seconds.
        
        Args:
            channel: Discord channel to send the message to
            turn: Current turn number
            total_turns: Total max turns
            tool_names: List of tool names being executed
            elapsed_seconds: Seconds elapsed since processing started
            channel_id: Discord channel ID (for status message rotation)
        """
        # Only send periodic status if processing has been going for > 10 seconds
        if elapsed_seconds < 10:
            return
        
        # Avoid spamming - only send if more than 15 seconds since last status
        # Use a simple heuristic: only send on turns that are multiples of 2
        # after the first 10 seconds
        if turn % 2 != 0 and elapsed_seconds < 25:
            return
        
        # Build a friendly "still working" message
        unique_tools = list(dict.fromkeys(tool_names))
        tool_display = {
            "channel_search": "searching channel history",
            "image_compare": "comparing/describing images",
            "comfyui_generate": "generating an image",
            "memory_tool": "accessing memory",
            "math_calc": "calculating",
            "end_session": "ending the session",
        }
        
        active_tools = []
        for tool in unique_tools:
            desc = tool_display.get(tool, tool)
            active_tools.append(desc)
        
        if active_tools:
            tool_desc = " and ".join(active_tools)
        else:
            tool_desc = "processing your request"
        
        # Round elapsed time
        elapsed_rounded = int(elapsed_seconds)
        
        status_messages = [
            f"⏳ Still working on {tool_desc}... ({elapsed_rounded}s)",
            f"⏳ Working on it... ({elapsed_rounded}s elapsed)",
            f"🔧 Almost there, still processing ({elapsed_rounded}s)",
        ]
        
        # Simple rotation based on channel_id, turn, and elapsed time
        import hashlib
        hash_val = int(hashlib.md5(f"{channel_id}_{turn}_{elapsed_rounded}".encode()).hexdigest(), 16)
        status_text = status_messages[hash_val % len(status_messages)]
        
        try:
            await channel.send(status_text)
            logger.info(f"Periodic status [{elapsed_rounded}s]: {status_text}")
        except Exception as e:
            logger.warning(f"Failed to send periodic status: {e}")
    
    async def _process_tool_calls_with_status(
        self,
        tool_calls: List[Dict],
        messages_for_lm: List[Dict],
        channel,
        turn: int,
        channel_id: int,
        start_time: float,
        is_active_session: bool = False
    ) -> Any:
        """Process tool calls with periodic status updates and cancellation checking.
        
        This wraps the tool call processing with:
        - Periodic status messages to Discord
        - Cancellation checks before and after processing
        
        Args:
            tool_calls: Tool call dicts from LM Studio
            messages_for_lm: Conversation messages
            channel: Discord channel
            turn: Current turn number
            channel_id: Discord channel ID
            start_time: Processing start time (time.time())
            is_active_session: Whether this is an active session
            
        Returns:
            For new session: response_text string
            For active session: end_session_result dict or None
        """
        # Check cancellation before processing
        cancelled = await self._check_cancellation(channel_id)
        if cancelled:
            logger.info(f"Cancellation requested before tool processing, channel {channel_id}")
            await channel.send("⚠️ Operation cancelled.")
            return None
        
        # Extract tool names for status display
        tool_names = [tc.get("function", {}).get("name", "") for tc in tool_calls]
        
        # Send initial status message if no custom one was provided
        custom_status_msg = self._extract_status_message(tool_calls)
        if not self._should_send_status(custom_status_msg):
            await self._send_tool_status_message(channel, tool_names, turn, None)
        
        # Process tool calls
        if is_active_session:
            response_text = await self._tool_call_handler.process_tool_calls_active(
                tool_calls, messages_for_lm, turn,
                self._safe_downloader,
                make_lm_call_func=lambda ctx, **kw: self._lm_caller.call(ctx, **kw),
                get_bot_instance=lambda: self._bot_instance
            )
        else:
            response_text = await self._tool_call_handler.process_tool_calls(
                tool_calls, messages_for_lm, channel, turn,
                self._safe_downloader,
                make_lm_call_func=lambda ctx, **kw: self._lm_caller.call(ctx, **kw),
                get_bot_instance=lambda: self._bot_instance
            )
        
        # Send periodic status update if processing took time
        elapsed = time.time() - start_time
        await self._send_periodic_status(channel, turn, self._max_tool_turns, tool_names, elapsed)
        
        return response_text
    
    # --- Memory Recall ---

    def _recall_memories(
        self,
        query: str,
        user_id: Optional[str] = None,
        guild_id: Optional[str] = None,
    ) -> Optional[str]:
        """Recall relevant memories for a query and format them as context text.

        Args:
            query: The search query (typically the user's message content).
            user_id: Optional Discord user ID for filtering.
            guild_id: Optional Discord guild/server ID for per-server isolation.

        Returns:
            Formatted memory context string, or None if no memories found.
        """
        if self._memory_manager is None:
            return None

        if not query or not query.strip():
            return None

        try:
            memories = self._memory_manager.get_relevant_memories(
                query=query,
                user_id=user_id,
                limit=self._memory_recall_limit,
            )

            if not memories:
                return None

            # Format memories as context block
            lines = []
            lines.append(f"🧠 [RECALLED CONTEXT: {len(memories)} relevant memory(ies)]")
            for i, mem in enumerate(memories, 1):
                content = mem.get("content", "")
                mtype = mem.get("memory_type", "fact")
                importance = mem.get("importance", 0.0)
                created = mem.get("created_at", "")
                lines.append(f"  [{i}] type={mtype}, importance={importance:.2f}, date={created}")
                lines.append(f"      {content}")

            result = "\n".join(lines)
            logger.info(f"Memory recall: {len(memories)} memories for query '{query[:50]}...'")
            return result

        except Exception as e:
            logger.warning(f"Failed to recall memories for query '{query[:50]}...': {e}")
            return None

    # --- Context Compression ---

    def _estimate_tokens(self, messages: List[Dict]) -> int:
        """Estimate total token count for a list of messages.
        
        Simple heuristic: ~4 characters per token, plus overhead for structure.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            
        Returns:
            Estimated total token count
        """
        total_chars = 0
        for msg in messages:
            content = msg.get("content", "")
            if content:
                total_chars += len(content)
            # Add overhead for role tags and structure
            total_chars += len(msg.get("role", "")) + 20  # role + structure overhead
        # Rough estimate: 4 characters per token
        return max(1, int(total_chars / 4))

    def check_context_compression_needed(self, messages: List[Dict]) -> Optional[int]:
        """Check if context compression is needed and return compression point.
        
        Evaluates whether conversation history exceeds thresholds that warrant
        automatic context compression.
        
        Args:
            messages: Current conversation messages list
            
        Returns:
            Index to compress before if compression needed, None otherwise.
            Returns the index where compression should start - all messages
            before this index will be compressed into a summary.
        """
        if not self._context_compression_enabled:
            return None

        if not messages or len(messages) <= self._context_message_threshold:
            return None

        # Check token threshold
        estimated_tokens = self._estimate_tokens(messages)
        # Rough estimate of max tokens: assume ~1000 tokens per message on average
        max_estimated_tokens = len(messages) * 100
        token_percentage = (estimated_tokens / max(1, max_estimated_tokens)) * 100

        if token_percentage < self._context_token_threshold:
            return None

        # Calculate compression point: keep recent messages fresh
        num_recent = min(self._context_messages_to_keep_fresh, len(messages))
        compression_point = len(messages) - num_recent

        # Don't compress if there's nothing to compress
        if compression_point <= 1:
            return None

        logger.info(
            f"Context compression triggered: {len(messages)} messages, "
            f"~{estimated_tokens} tokens, compression point: {compression_point}"
        )
        return compression_point

    def compress_context_in_messages(self, messages: List[Dict], compression_point: int,
                                      summary: str) -> List[Dict]:
        """Replace old messages with a compressed summary in the conversation list.
        
        Args:
            messages: Current conversation messages list (modified in place)
            compression_point: Index before which messages should be compressed
            summary: The compressed summary string to insert
            
        Returns:
            Modified messages list with compression marker inserted
        """
        if compression_point <= 0 or compression_point >= len(messages):
            return messages

        # Extract the compressed portion (messages before compression point)
        compressed_messages = messages[:compression_point]
        # Keep recent messages as-is
        recent_messages = messages[compression_point:]

        # Build a brief summary of compressed messages
        user_msgs = [m for m in compressed_messages if m.get("role") == "user"]
        assistant_msgs = [m for m in compressed_messages if m.get("role") == "assistant"]

        summary_parts = []
        if user_msgs:
            summary_parts.append(f"{len(user_msgs)} user messages")
        if assistant_msgs:
            summary_parts.append(f"{len(assistant_msgs)} assistant messages")
        summary_detail = f"Compressed {', '.join(summary_parts)}. " if summary_parts else ""

        full_summary = (
            f"[CONTEXT: {summary_detail}Conversation history from message index 0 to "
            f"{compression_point - 1} has been compressed to save context space. "
            f"The conversation covered multiple topics and turns. "
            f"Recent messages from index {compression_point} onwards are preserved in full. "
            f"Summary length: {len(summary)} characters.]"
        )

        # Truncate to target summary length if needed
        max_summary_len = self._context_summary_length
        if len(full_summary) > max_summary_len:
            full_summary = full_summary[:max_summary_len - 3] + "..."

        # Replace compressed portion with summary as a special system message
        compressed_messages = [{
            "role": "system",
            "content": full_summary
        }]

        # Combine compressed portion + recent messages
        return compressed_messages + recent_messages

    async def _send_cancelled_response(self, channel: Any) -> None:
        """Send a cancellation confirmation message to Discord.
        
        Args:
            channel: Discord channel to send the message to
        """
        try:
            await channel.send("⚠️ Operation cancelled. I'm no longer processing that request.")
        except Exception as e:
            logger.error(f"Failed to send cancellation message: {e}")

    # --- Auto-Compression (FEAT-008) ---

    async def _auto_compress_context(
        self,
        messages: List[Dict],
        channel: Any,
        compression_point: int,
        call_lm_studio_func: Optional[Callable] = None
    ) -> List[Dict]:
        """Automatically compress conversation context using LM-based summarization.
        
        Sends messages before compression_point to LM Studio for summarization,
        then replaces them with a compact summary message.
        
        Args:
            messages: Current conversation messages list
            channel: Discord channel for typing indicator
            compression_point: Index where compression should start
            call_lm_studio_func: Optional callable for LM API call
            
        Returns:
            Modified messages list with compressed summary
        """
        if compression_point <= 0 or compression_point >= len(messages):
            return messages

        # Extract messages to compress (everything before compression_point)
        messages_to_compress = messages[:compression_point]
        recent_messages = messages[compression_point:]

        # Build a summarization prompt for the LM
        summarization_prompt = self._build_context_summarization_prompt(messages_to_compress)

        # Call LM Studio for summarization
        summary = None
        try:
            if call_lm_studio_func:
                summary_response = await call_lm_studio_func(
                    [{"role": "user", "content": summarization_prompt}],
                    tools=[],
                    temperature=0.3,
                    max_tokens=self._context_lm_max_tokens,
                    channel_id=None,
                    use_tool_calling=False
                )
            else:
                summary_response = await self._lm_caller.call(
                    [{"role": "user", "content": summarization_prompt}],
                    channel_id=None,
                    use_tool_calling=False,
                    max_tokens=self._context_lm_max_tokens
                )

            choices = summary_response.get("choices", [])
            if choices:
                summary = choices[0].get("message", {}).get("content", "")
                if summary and summary.strip():
                    logger.info(f"[auto_compress] LM summary generated: {len(summary)} chars")
                else:
                    summary = None

        except Exception as e:
            logger.error(f"[auto_compress] Failed to get LM summary: {e}")

        # Fallback: if LM summarization failed, use a concise placeholder
        if not summary:
            user_msgs = [m for m in messages_to_compress if m.get("role") == "user"]
            assistant_msgs = [m for m in messages_to_compress if m.get("role") == "assistant"]
            summary = (
                f"[CONTEXT: Compressed {len(user_msgs)} user messages and "
                f"{len(assistant_msgs)} assistant messages. "
                f"Conversation covered multiple topics from message index 0 to "
                f"{compression_point - 1}. Recent messages preserved from index {compression_point}.]"
            )
            logger.info(f"[auto_compress] Used fallback summary: {len(summary)} chars")

        # Build compressed message
        compressed_msg = {
            "role": "system",
            "content": f"[CONTEXT SUMMARY]\n{summary}"
        }

        # Replace compressed portion with summary
        new_messages = [compressed_msg] + recent_messages
        logger.info(
            f"[auto_compress] Context compressed: {len(messages)} -> {len(new_messages)} messages "
            f"(compressed {compression_point} messages into 1 summary)"
        )
        return new_messages

    def _build_context_summarization_prompt(self, messages_to_compress: List[Dict]) -> str:
        """Build a prompt for the LM to summarize conversation messages.
        
        Args:
            messages_to_compress: List of message dicts to summarize
            
        Returns:
            A prompt string for the LM to summarize the messages
        """
        # Format messages for summarization
        formatted = []
        for msg in messages_to_compress:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role in ("user", "assistant"):
                formatted.append(f"{role}: {content}")
            elif role == "system":
                formatted.append(f"[SYSTEM]: {content}")

        conversation_text = "\n\n".join(formatted)

        # Truncate if extremely long (safety limit)
        max_text_length = 4000
        if len(conversation_text) > max_text_length:
            conversation_text = conversation_text[:max_text_length] + "\n\n[...truncated...]"

        prompt = (
            "You are a conversation summarizer. Summarize the following conversation excerpt. "
            "Focus on: who is talking to whom, what topics are discussed, what information is shared, "
            "and what is resolved vs ongoing. Keep the summary concise and informative.\n\n"
            f"=== CONVERSATION EXCERPT ===\n{conversation_text}\n=== END EXCERPT ===\n\n"
            "IMPORTANT: If any messages contain image URLs, file references, or important data, "
            "mention them specifically in the summary. Format: 'Images found: [URL1], [URL2]'\n\n"
            "Provide a concise summary (target: 200-300 characters)."
        )
        return prompt
