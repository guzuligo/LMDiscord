"""
Tool Executor Module

Handles tool call processing for LM Studio responses:
- end_session tool handling
- image_describe tool handling with safe image download
- Generic tool result handling
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class ToolCallHandler:
    """Handles processing of LM Studio tool calls."""

    async def process_tool_calls(
        self,
        tool_calls: List[Dict],
        messages_for_lm: List[Dict],
        channel: Any,
        turn: int,
        safe_downloader: Any,
        make_lm_call_func: Optional[Any] = None
    ) -> Optional[str]:
        """Process tool calls from LM Studio (new session variant).

        Args:
            tool_calls: List of tool call dicts
            messages_for_lm: Messages list to append to
            channel: Discord channel object
            turn: Current turn number
            safe_downloader: SafeImageDownloader instance
            make_lm_call_func: Optional function to make LM calls (for mini-context)

        Returns:
            Response text, or None if end_session was called
        """
        for tool_call in tool_calls:
            func = tool_call.get("function", {})
            func_name = func.get("name", "")
            tool_call_id = tool_call.get("id", "")
            func_args = func.get("arguments", "{}")

            logger.info(f"Turn {turn + 1}: LM Studio called tool: {func_name}")

            if func_name == "end_session":
                return await self._handle_end_session(func_args, messages_for_lm, channel)
            elif func_name == "image_describe":
                result = await self._handle_image_describe(
                    func_args, messages_for_lm, tool_call_id, safe_downloader, make_lm_call_func
                )
                return result
            elif func_name == "image_compare":
                result = await self._handle_image_compare(
                    func_args, messages_for_lm, tool_call_id, safe_downloader, make_lm_call_func
                )
                return result
            else:
                tool_result = f"Unknown tool: {func_name}"
                messages_for_lm.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": tool_result
                })

        return None  # Continue the loop for multi-turn

    async def process_tool_calls_active(
        self,
        tool_calls: List[Dict],
        messages_for_lm: List[Dict],
        turn: int,
        safe_downloader: Any,
        make_lm_call_func: Optional[Any] = None
    ) -> Optional[Dict]:
        """Process tool calls from LM Studio (active session variant).

        Args:
            tool_calls: List of tool call dicts
            messages_for_lm: Messages list to append to
            turn: Current turn number
            safe_downloader: SafeImageDownloader instance
            make_lm_call_func: Optional function to make LM calls (for mini-context)

        Returns:
            Dict with 'farewell' key if end_session was called, None otherwise
        """
        for tool_call in tool_calls:
            func = tool_call.get("function", {})
            func_name = func.get("name", "")
            tool_call_id = tool_call.get("id", "")
            func_args = func.get("arguments", "{}")

            if func_name == "end_session":
                try:
                    args = json.loads(func_args)
                    farewell = args.get("farewell_message", "Goodbye!")
                    return {"farewell": farewell}
                except (json.JSONDecodeError, AttributeError):
                    return {"farewell": "Goodbye!"}

            elif func_name == "image_describe":
                await self._handle_image_describe_active(
                    func_args, messages_for_lm, tool_call_id, safe_downloader, make_lm_call_func
                )
            elif func_name == "image_compare":
                await self._handle_image_compare_active(
                    func_args, messages_for_lm, tool_call_id, safe_downloader, make_lm_call_func
                )
            else:
                messages_for_lm.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": f"Unknown tool: {func_name}"
                })

        return None  # Continue the loop

    async def _handle_end_session(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        channel: Any
    ) -> Optional[str]:
        """Handle end_session tool call.

        Args:
            func_args: Function arguments JSON string
            messages_for_lm: Messages list
            channel: Discord channel

        Returns:
            None (indicating no response to post)
        """
        try:
            args = json.loads(func_args)
            farewell = args.get("farewell_message", "Goodbye!")
            if len(farewell) > 2000:
                farewell = farewell[:1997] + "..."
            await channel.send(farewell)
            logger.info("Farewell message posted")
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error processing end_session: {e}")
        return None

    async def _handle_image_describe(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        tool_call_id: str,
        safe_downloader: Any,
        make_lm_call_func: Optional[Any] = None
    ) -> Optional[str]:
        """Handle image_describe tool call (new session variant).

        Uses isolated context window for image description to avoid
        context overflow from large base64 image data.

        Args:
            func_args: Function arguments JSON string
            messages_for_lm: Messages list to modify
            tool_call_id: Tool call ID
            safe_downloader: SafeImageDownloader instance
            make_lm_call_func: Optional function to make LM calls

        Returns:
            Response text to continue with, or None for errors
        """
        image_description = None
        try:
            args = json.loads(func_args)
            image_data = args.get("image_data", "")
            mime_type = args.get("mime_type", "image/jpeg")

            logger.info(f"Executing image_describe tool with image_data length: {len(image_data)}")

            # Check if image_data is a URL (Discord CDN)
            if image_data.startswith("http"):
                raw_bytes = await safe_downloader.download_image(image_data)
                logger.info(f"Downloaded {len(raw_bytes)} bytes from URL")

                from src.utils import resize_image_bytes, image_to_base64
                compressed_bytes, output_mime = resize_image_bytes(
                    raw_bytes, max_dimension=768, quality=85
                )
                processed_base64 = image_to_base64(compressed_bytes)

                # Use the user's last message as instruction for focused description
                image_instruction = self._extract_last_user_message(messages_for_lm)
                mini_context = self._build_mini_context(
                    processed_base64, output_mime, image_instruction=image_instruction
                )

                logger.info(f"[Fix 2c] Using isolated mini-context for image description"
                            f"{f' (instruction: {image_instruction[:40]}...)' if image_instruction else ''}")
                mini_response = await self._get_mini_context_response(
                    mini_context, make_lm_call_func
                )

                image_description = self._extract_description(mini_response)
                logger.info(f"[Fix 2c] Image description obtained: {repr(image_description[:80])}...")

                messages_for_lm.pop()  # Remove assistant message with tool call
                messages_for_lm.append({
                    "role": "user",
                    "content": f"IMAGE DESCRIPTION COMPLETE: {image_description}. You now have full information about this image. DO NOT call image_describe again for this image. Respond to the user's question using this description."
                })

        except ValueError as e:
            logger.warning(f"Image download blocked: {e}")
            tool_result = self._build_blocked_url_error()
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

        return image_description

    async def _handle_image_describe_active(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        tool_call_id: str,
        safe_downloader: Any,
        make_lm_call_func: Optional[Any] = None
    ) -> None:
        """Handle image_describe tool call (active session variant).

        Args:
            func_args: Function arguments JSON string
            messages_for_lm: Messages list to modify
            tool_call_id: Tool call ID
            safe_downloader: SafeImageDownloader instance
            make_lm_call_func: Optional function to make LM calls
        """
        try:
            args = json.loads(func_args)
            image_data = args.get("image_data", "")
            mime_type = args.get("mime_type", "image/jpeg")

            logger.info(f"Executing image_describe tool (active session) with image_data length: {len(image_data)}")

            if image_data.startswith("http"):
                raw_bytes = await safe_downloader.download_image(image_data)
                logger.info(f"Downloaded {len(raw_bytes)} bytes from URL")

                from src.utils import resize_image_bytes, image_to_base64
                compressed_bytes, output_mime = resize_image_bytes(
                    raw_bytes, max_dimension=768, quality=85
                )
                processed_base64 = image_to_base64(compressed_bytes)

                # Use the user's last message as instruction for focused description
                image_instruction = self._extract_last_user_message(messages_for_lm)
                mini_context = self._build_mini_context(
                    processed_base64, output_mime, image_instruction=image_instruction
                )

                logger.info(f"[Fix 2c] Using isolated mini-context for image description (active session)"
                            f"{f' (instruction: {image_instruction[:40]}...)' if image_instruction else ''}")
                mini_response = await self._get_mini_context_response(
                    mini_context, make_lm_call_func
                )

                image_description = self._extract_description(mini_response)
                logger.info(f"[Fix 2c] Image description obtained: {repr(image_description[:80])}...")

                messages_for_lm.pop()  # Remove assistant message with tool call
                messages_for_lm.append({
                    "role": "user",
                    "content": f"IMAGE DESCRIPTION COMPLETE: {image_description}. You now have full information about this image. DO NOT call image_describe again for this image. Respond to the user's question using this description."
                })

        except ValueError as e:
            logger.warning(f"Image download blocked: {e}")
            tool_result = self._build_blocked_url_error()
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

    async def _handle_image_data(self, image_data: str, safe_downloader: Any) -> tuple:
        """Process image_data which may be either a URL string or base64 data.

        If image_data is a URL (starts with http), downloads it, validates,
        resizes, and converts to base64. If it's already base64 data, processes it directly.

        Args:
            image_data: URL string or base64-encoded image data
            safe_downloader: SafeImageDownloader instance

        Returns:
            Tuple of (base64_data: str, mime_type: str)
        """
        from src.utils import resize_image_bytes, image_to_base64

        # Check if image_data is a URL
        if image_data.startswith("http"):
            # Download from URL
            raw_bytes = await safe_downloader.download_image(image_data)
            logger.info(f"Downloaded {len(raw_bytes)} bytes from URL")

            # Detect MIME type from content
            content_type = None
            if len(raw_bytes) >= 4:
                sig = raw_bytes[:4]
                if sig[:2] == b'\xff\xd8':
                    content_type = "image/jpeg"
                elif sig[:4] == b'\x89PNG':
                    content_type = "image/png"
                elif sig[:4] == b'GIF8':
                    content_type = "image/gif"
                elif sig[:4] == b'RIFF' and raw_bytes[8:12] == b'WEBP':
                    content_type = "image/webp"

            compressed_bytes, output_mime = resize_image_bytes(
                raw_bytes, max_dimension=768, quality=85
            )
            processed_base64 = image_to_base64(compressed_bytes)
            return processed_base64, output_mime
        else:
            # Already base64 data - decode, resize, re-encode
            import base64
            raw_bytes = base64.b64decode(image_data)
            compressed_bytes, output_mime = resize_image_bytes(
                raw_bytes, max_dimension=768, quality=85
            )
            processed_base64 = image_to_base64(compressed_bytes)
            return processed_base64, output_mime

    # --- Helper Methods ---

    def _build_mini_context(
        self,
        base64_data: str,
        mime_type: str,
        image_instruction: Optional[str] = None
    ) -> List[Dict]:
        """Build mini-context for image description.

        Args:
            base64_data: Base64 encoded image data
            mime_type: MIME type of the image
            image_instruction: Instruction for the vision model.
                Defaults to a generic detailed description request.

        Returns:
            Mini-context list
        """
        if image_instruction is None:
            image_instruction = (
                "Please describe this image in detail, up to 3-4 sentences. "
                "Focus on key visual elements, colors, objects, and composition."
            )
        return [
            {"role": "user", "content": [
                {"type": "text", "text": image_instruction},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_data}"}}
            ]}
        ]

    def _extract_last_user_message(self, messages_for_lm: List[Dict]) -> Optional[str]:
        """Extract the last user message text from conversation history.

        Walks backwards through messages and returns the first non-empty
        user message content found.

        Args:
            messages_for_lm: Conversation history

        Returns:
            User message text, or None if not found
        """
        for msg in reversed(messages_for_lm):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    return content.strip()
        return None

    async def _get_mini_context_response(
        self,
        mini_context: List[Dict],
        make_lm_call_func: Optional[Any] = None
    ) -> Dict:
        """Get response from LM Studio using mini-context.

        Args:
            mini_context: Mini-context for image description
            make_lm_call_func: Optional function to make LM calls

        Returns:
            LM Studio response dict
        """
        if make_lm_call_func:
            return await make_lm_call_func(mini_context, channel_id=None, use_tool_calling=False)
        # Fallback: direct call (should not happen in normal operation)
        logger.warning("No make_lm_call_func provided for mini-context")
        return {"choices": []}

    def _extract_description(self, mini_response: Dict) -> str:
        """Extract image description from mini-context response.

        Args:
            mini_response: LM Studio response dict

        Returns:
            Image description string
        """
        mini_choices = mini_response.get("choices", [])
        if mini_choices:
            return mini_choices[0].get("message", {}).get("content", "Could not describe the image.")
        return "Could not describe the image (no response from LM Studio)."

    def _build_blocked_url_error(self) -> str:
        """Build user-friendly error message for blocked URLs."""
        return (
            "The image URL could not be processed. "
            "This may be due to the image being hosted on an unsupported domain, "
            "or the URL may not be publicly accessible. "
            "Please try using an image from Discord's CDN instead."
        )

    async def _handle_image_compare(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        tool_call_id: str,
        safe_downloader: Any,
        make_lm_call_func: Optional[Any] = None
    ) -> Optional[str]:
        """Handle image_compare tool call (new session variant).

        Downloads multiple images, describes each via mini-context, then generates
        a structured comparison.

        Args:
            func_args: Function arguments JSON string
            messages_for_lm: Messages list to modify
            tool_call_id: Tool call ID
            safe_downloader: SafeImageDownloader instance
            make_lm_call_func: Optional function to make LM calls

        Returns:
            Comparison text to continue with
        """
        try:
            args = json.loads(func_args)
            image_urls = args.get("image_urls", [])
            comparison_prompt = args.get("comparison_prompt", "")

            logger.info(f"[image_compare] Comparing {len(image_urls)} images")

            from src.tools.builtins.image_compare import ImageCompareTool

            # Use the user's last message as instruction for focused descriptions
            image_instruction = self._extract_last_user_message(messages_for_lm)
            comparison_text = await ImageCompareTool.compare_images_async(
                image_urls=image_urls,
                comparison_prompt=comparison_prompt,
                safe_downloader=safe_downloader,
                make_lm_call_func=make_lm_call_func,
                image_instruction=image_instruction
            )

            logger.info(f"[image_compare] Comparison complete"
                        f"{f' (instruction: {image_instruction[:40]}...)' if image_instruction else ''}")

            messages_for_lm.pop()  # Remove assistant message with tool call
            messages_for_lm.append({
                "role": "user",
                "content": f"IMAGE COMPARISON COMPLETE: {comparison_text}. You now have a full comparison of all images. Respond to the user's question using this comparison."
            })

        except ValueError as e:
            logger.warning(f"Image compare blocked: {e}")
            messages_for_lm.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": f"Image comparison blocked: {str(e)}"
            })
        except Exception as e:
            logger.error(f"Error in image_compare: {e}", exc_info=True)
            messages_for_lm.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": f"Error during image comparison: {str(e)}"
            })

        return comparison_text

    async def _handle_image_compare_active(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        tool_call_id: str,
        safe_downloader: Any,
        make_lm_call_func: Optional[Any] = None
    ) -> None:
        """Handle image_compare tool call (active session variant).

        Args:
            func_args: Function arguments JSON string
            messages_for_lm: Messages list to modify
            tool_call_id: Tool call ID
            safe_downloader: SafeImageDownloader instance
            make_lm_call_func: Optional function to make LM calls
        """
        try:
            args = json.loads(func_args)
            image_urls = args.get("image_urls", [])
            comparison_prompt = args.get("comparison_prompt", "")

            logger.info(f"[image_compare] Comparing {len(image_urls)} images (active session)")

            from src.tools.builtins.image_compare import ImageCompareTool

            # Use the user's last message as instruction for focused descriptions
            image_instruction = self._extract_last_user_message(messages_for_lm)
            comparison_text = await ImageCompareTool.compare_images_async(
                image_urls=image_urls,
                comparison_prompt=comparison_prompt,
                safe_downloader=safe_downloader,
                make_lm_call_func=make_lm_call_func,
                image_instruction=image_instruction
            )

            logger.info(f"[image_compare] Comparison complete (active session)"
                        f"{f' (instruction: {image_instruction[:40]}...)' if image_instruction else ''}")

            messages_for_lm.pop()  # Remove assistant message with tool call
            messages_for_lm.append({
                "role": "user",
                "content": f"IMAGE COMPARISON COMPLETE: {comparison_text}. You now have a full comparison of all images. Respond to the user's question using this comparison."
            })

        except ValueError as e:
            logger.warning(f"Image compare blocked: {e}")
            messages_for_lm.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": f"Image comparison blocked: {str(e)}"
            })
        except Exception as e:
            logger.error(f"Error in image_compare: {e}", exc_info=True)
            messages_for_lm.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": f"Error during image comparison: {str(e)}"
            })
