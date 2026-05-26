"""
Message Processor Module

Handles core message processing with LM Studio:
- process_message: New session message processing
- process_active_session: Active session message processing
- Delegates LM calls to LMCaller
- Delegates tool calling to ToolCallHandler
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable

from src.discord_bot.tool_executor import ToolCallHandler
from src.discord_bot.lm_caller import LMCaller

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
        max_tool_turns: int = 5
    ):
        """Initialize message processor."""
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

    def set_params(self, temperature: float = 0.7, max_tokens: int = 2500) -> None:
        """Set LM Studio parameters."""
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._lm_caller.update_params(temperature=temperature, max_tokens=max_tokens)

    def set_tools(self, tools: List[Dict[str, Any]]) -> None:
        """Set the list of tools."""
        self._tools = tools
        self._lm_caller.update_params(tools=tools)

    # --- Core Processing Logic ---

    async def process_message(
        self,
        message: Any,
        channel_id: int,
        conversation_history: Dict[int, List[Dict[str, str]]],
        typing_callback: Callable,
        is_active_session: bool = False,
        on_message_callback: Optional[Callable] = None,
        call_lm_studio_func: Optional[Callable] = None
    ) -> Optional[Dict]:
        """Core message processing with LM Studio (new session)."""
        return await self._process_session(
            message, channel_id, conversation_history, typing_callback,
            is_active_session, on_message_callback, call_lm_studio_func,
            is_new_session=True
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
        is_new_session: bool = False
    ) -> Optional[Dict]:
        """Common session processing logic for both new and active sessions."""
        channel = message.channel
        messages_for_lm = list(conversation_history.get(channel_id, []))

        await typing_callback(channel)

        response_text = None
        discord_response = None
        final_tool_calls = None
        final_usage = None

        try:
            # Track failed tool turns for retry logic (failed turns don't count against limit)
            failed_tool_turns: List[int] = []
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

                # Track whether this tool turn succeeded or failed
                tool_turn_failed = False

                # Send a status message only if the LLM provided a custom one
                tool_names = [tc.get("function", {}).get("name", "") for tc in tool_calls]
                custom_status_msg = self._extract_status_message(tool_calls)
                if self._should_send_status(custom_status_msg):
                    await self._send_tool_status_message(channel, tool_names, turn + 1, custom_status_msg)

                response_text = await self._tool_call_handler.process_tool_calls(
                    tool_calls, messages_for_lm, channel, turn,
                    self._safe_downloader,
                    make_lm_call_func=lambda ctx, **kw: self._lm_caller.call(ctx, **kw),
                    get_bot_instance=lambda: self._bot_instance
                )

                # Detect failed tool turns: tool called but result was error (tool role message with error content)
                last_msgs = messages_for_lm[-3:]
                for m in last_msgs:
                    if m.get("role") == "tool" and "Error" in m.get("content", ""):
                        tool_turn_failed = True
                        break

                if tool_turn_failed:
                    failed_tool_turns.append(turn)
                    logger.info(f"Turn {turn + 1} tool call failed, will retry (failed turns: {len(failed_tool_turns)})")

                # Do NOT break here. The loop should continue so LM Studio can process the tool results
                # and generate a final text response. Only break when LM returns no tool calls.
                final_tool_calls = tool_calls

            if response_text and len(response_text) > 2000:
                response_text = response_text[:1997] + "..."

            # Fallback: if max turns exhausted with no text response, send something
            if not response_text and final_tool_calls:
                logger.warning(f"[empty_response] Channel {channel_id}: max turns exhausted with no text response. "
                               f"final_tool_calls=present, failed_tool_turns={len(failed_tool_turns)}")
                response_text = (
                    "I've processed the available information but couldn't generate a complete response. "
                    "This might be because the conversation context is too large. "
                    "Please try starting a new session."
                )
            elif not response_text and final_tool_calls is None:
                # LM returned empty content on turn 0 with no tool calls - pure LM failure
                logger.warning(f"[empty_response] Channel {channel_id}: LM returned empty response on turn 0 "
                               f"with no tool calls (pure LM silence)")
                response_text = (
                    "Sorry, I couldn't generate a response. This might be a temporary issue. "
                    "Please try again or start a new session if the problem persists."
                )

        except ConnectionError as e:
            logger.error(f"LM Studio connection error: {e}")
            response_text = "Sorry, I couldn't connect to LM Studio."
            await channel.send(response_text)
        except Exception as e:
            error_str = str(e)
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

        return final_usage

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
        call_lm_studio_func: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Process active session messages."""
        response_text = None
        final_tool_calls = None
        final_usage = None
        should_end_session = False
        farewell_message = None

        try:
            # Truncate conversation history to prevent context overflow
            MAX_HISTORY_MESSAGES = 20
            if len(messages_for_lm) > MAX_HISTORY_MESSAGES:
                messages_for_lm = [messages_for_lm[0]] + messages_for_lm[-(MAX_HISTORY_MESSAGES - 1):]
                logger.info(f"Truncated conversation history to {len(messages_for_lm)} messages")

            # Track total tool calls to prevent infinite tool-calling loops
            total_tool_calls_in_session = 0
            MAX_TOOL_CALLS_PER_SESSION = 3
            force_response_break = False  # Flag to indicate we broke due to max tool calls
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

                # Process tool calls via ToolCallHandler
                tool_turn_failed = False

                # Send a status message only if the LLM provided a custom one
                tool_names = [tc.get("function", {}).get("name", "") for tc in tool_calls]
                custom_status_msg = self._extract_status_message(tool_calls)
                if self._should_send_status(custom_status_msg):
                    await self._send_tool_status_message(message.channel, tool_names, turn + 1, custom_status_msg)

                end_session_result = await self._tool_call_handler.process_tool_calls_active(
                    tool_calls, messages_for_lm, turn,
                    self._safe_downloader,
                    make_lm_call_func=lambda ctx, **kw: self._lm_caller.call(ctx, **kw),
                    get_bot_instance=lambda: self._bot_instance
                )

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
                if total_tool_calls_in_session >= MAX_TOOL_CALLS_PER_SESSION:
                    logger.warning(f"Max tool calls ({MAX_TOOL_CALLS_PER_SESSION}) reached for channel {channel_id}, forcing response")
                    # Add a hint message to prompt the model to respond
                    messages_for_lm.append({
                        "role": "user",
                        "content": "You have enough information. Please respond to the user now with your answer. Do NOT call any more tools."
                    })
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

            # Fallback: if loop ended with no text response in active session
            if not response_text and final_tool_calls:
                logger.warning(f"[empty_response] Active session channel {channel_id}: "
                               f"loop ended with no text response, final_tool_calls=present, "
                               f"failed_tool_turns={len(failed_tool_turns)}")
                response_text = (
                    "I've processed the available information but couldn't generate a complete response. "
                    "This might be because the conversation context is too large. "
                    "Please try starting a new session."
                )
            elif not response_text and final_tool_calls is None:
                # LM returned empty response with no tool calls - pure LM silence
                logger.warning(f"[empty_response] Active session channel {channel_id}: "
                               f"LM returned empty response with no tool calls (pure LM silence)")
                response_text = (
                    "Sorry, I couldn't generate a response. This might be a temporary issue. "
                    "Please try again or start a new session if the problem persists."
                )

        except Exception as e:
            error_str = str(e)
            if self._is_oom_error(error_str):
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

    def _is_oom_error(self, error_str: str) -> bool:
        """Check if an error indicates OOM (Out of Memory)."""
        oom_indicators = ["out of memory", "oom", "cuda out of memory", "runtime error", "500",
                         "internal server error", "context length", "context exceeded",
                         "max context", "too many tokens"]
        error_lower = error_str.lower()
        return any(indicator in error_lower for indicator in oom_indicators)

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
                "image_describe": "🖼️ Analyzing image",
                "image_compare": "🖼️ Comparing images",
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
