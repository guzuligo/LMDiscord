"""
Tool Executor Module

Handles tool call processing for LM Studio responses:
- Tool call dispatch and deduplication
- end_session tool handling
- image_describe / image_compare tool handling (consolidated via ImageCompareTool)
- channel_search tool handling with mini-context summarization
- memory_tool handling
- Generic tool result handling

Refactored to separate concerns:
- ToolCallHandler: Core tool dispatch and deduplication
- _handle_image_describe / _handle_image_describe_active: Image analysis (delegates to ImageCompareTool)
- _handle_image_compare / _handle_image_compare_active: Image comparison (delegates to ImageCompareTool)
- _handle_channel_search / _handle_channel_search_active: Channel search
- _handle_memory_tool / _handle_memory_tool_active: Memory operations
- _handle_end_session: Session termination
"""

import asyncio
import base64
import json
import logging
import re
import time
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class ToolCallHandler:
    """Handles processing of LM Studio tool calls."""

    def __init__(self):
        """Initialize the tool call handler."""
        self._dedup_cache: Dict[str, tuple] = {}
        self._dedup_cache_ttl: float = 300.0  # 5 minutes TTL

    # --- Deduplication ---

    def _is_duplicate_tool_call(self, tool_name: str, func_args: str) -> bool:
        """Check if this tool call is a duplicate of a recent one."""
        cache_key = f"{tool_name}:{func_args}"
        if cache_key in self._dedup_cache:
            timestamp, result = self._dedup_cache[cache_key]
            if time.time() - timestamp < self._dedup_cache_ttl:
                logger.info(f"[tool_dedup] Duplicate tool call: {tool_name} with args {func_args[:100]}")
                return True
        return False

    def _cache_tool_result(self, tool_name: str, func_args: str, result: str) -> None:
        """Cache a tool call result for deduplication."""
        cache_key = f"{tool_name}:{func_args}"
        self._dedup_cache[cache_key] = (time.time(), result)
        if len(self._dedup_cache) > 100:
            now = time.time()
            expired = [k for k, (ts, _) in self._dedup_cache.items() if now - ts > self._dedup_cache_ttl]
            for k in expired:
                del self._dedup_cache[k]

    # --- Main Entry Points ---

    async def process_tool_calls(
        self,
        tool_calls: List[Dict],
        messages_for_lm: List[Dict],
        channel: Any,
        turn: int,
        safe_downloader: Any,
        make_lm_call_func: Optional[Any] = None,
        get_bot_instance: Optional[Any] = None,
        check_pending: Optional[Any] = None
    ) -> Optional[str]:
        """Process tool calls from LM Studio (new session variant).

        Returns:
            Response text, or None if end_session was called.
            Or dict {"interrupted": True, "pending_message": {...}} if interrupted.
        """
        image_describe_results: List[str] = []
        image_compare_results: List[str] = []
        had_end_session = False

        for i, tool_call in enumerate(tool_calls):
            func = tool_call.get("function", {})
            func_name = func.get("name", "")
            tool_call_id = tool_call.get("id", "")
            func_args = func.get("arguments", "{}")

            logger.info(f"Turn {turn + 1}: LM Studio called tool: {func_name}")

            # Check pending messages before next tool call (except after last)
            if check_pending and i < len(tool_calls) - 1:
                pending = await check_pending()
                if pending:
                    logger.info(f"Pending message detected during tool {i+1}/{len(tool_calls)}, interrupting")
                    return {"interrupted": True, "pending_message": pending}

            if func_name == "end_session":
                had_end_session = True
                await self._handle_end_session(func_args, messages_for_lm, channel)
                break
            elif func_name == "image_describe":
                result = await self._handle_image_describe(
                    func_args, messages_for_lm, tool_call_id, safe_downloader, make_lm_call_func
                )
                if result:
                    image_describe_results.append(result)
            elif func_name == "image_compare":
                result = await self._handle_image_compare(
                    func_args, messages_for_lm, tool_call_id, safe_downloader, make_lm_call_func
                )
                if result:
                    image_compare_results.append(result)
            elif func_name == "channel_search":
                if self._is_duplicate_tool_call(func_name, func_args):
                    _, cached_result = self._dedup_cache.get(func_name + ":" + func_args, (0, "No results"))
                    messages_for_lm.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": cached_result
                    })
                    logger.info(f"[tool_dedup] Using cached result for channel_search")
                else:
                    await self._handle_channel_search(
                        func_args, messages_for_lm, tool_call_id, get_bot_instance, make_lm_call_func
                    )
            elif func_name == "memory_tool":
                result = await self._handle_memory_tool(
                    func_args, messages_for_lm, tool_call_id, get_bot_instance
                )
                if result:
                    return result
            else:
                tool_result = f"Unknown tool: {func_name}"
                messages_for_lm.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": tool_result
                })

        if had_end_session:
            return None
        if image_describe_results:
            return "\n\n".join(image_describe_results)
        if image_compare_results:
            return "\n\n".join(image_compare_results)
        return None

    async def process_tool_calls_active(
        self,
        tool_calls: List[Dict],
        messages_for_lm: List[Dict],
        turn: int,
        safe_downloader: Any,
        make_lm_call_func: Optional[Any] = None,
        get_bot_instance: Optional[Any] = None,
        check_pending: Optional[Any] = None
    ) -> Optional[Dict]:
        """Process tool calls from LM Studio (active session variant).

        Returns:
            Dict with 'farewell' key if end_session was called, None to continue.
        """
        farewell_msg = None

        for i, tool_call in enumerate(tool_calls):
            func = tool_call.get("function", {})
            func_name = func.get("name", "")
            tool_call_id = tool_call.get("id", "")
            func_args = func.get("arguments", "{}")

            if func_name == "end_session":
                if check_pending and i < len(tool_calls) - 1:
                    pending = await check_pending()
                    if pending:
                        logger.info(f"Pending message detected during active session tool {i+1}/{len(tool_calls)}, interrupting")
                        return {"interrupted": True, "pending_message": pending}
                try:
                    args = json.loads(func_args)
                    farewell_msg = args.get("farewell_message", "Goodbye!")
                except (json.JSONDecodeError, AttributeError):
                    farewell_msg = "Goodbye!"
                break

            if check_pending and i < len(tool_calls) - 1:
                pending = await check_pending()
                if pending:
                    logger.info(f"Pending message detected during active session tool {i+1}/{len(tool_calls)}, interrupting")
                    return {"interrupted": True, "pending_message": pending}

            if func_name == "image_describe":
                await self._handle_image_describe_active(
                    func_args, messages_for_lm, tool_call_id, safe_downloader, make_lm_call_func
                )
            elif func_name == "image_compare":
                await self._handle_image_compare_active(
                    func_args, messages_for_lm, tool_call_id, safe_downloader, make_lm_call_func
                )
            elif func_name == "channel_search":
                if self._is_duplicate_tool_call(func_name, func_args):
                    _, cached_result = self._dedup_cache.get(func_name + ":" + func_args, (0, "No results"))
                    messages_for_lm.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": cached_result
                    })
                    logger.info(f"[tool_dedup] Using cached result for channel_search (active)")
                else:
                    await self._handle_channel_search_active(
                        func_args, messages_for_lm, tool_call_id, get_bot_instance, make_lm_call_func
                    )
            elif func_name == "memory_tool":
                result = await self._handle_memory_tool_active(
                    func_args, messages_for_lm, tool_call_id, get_bot_instance
                )
                if result:
                    return result
            else:
                messages_for_lm.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": f"Unknown tool: {func_name}"
                })

        if farewell_msg is not None:
            return {"farewell": farewell_msg}
        return None

    # --- end_session ---

    async def _handle_end_session(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        channel: Any
    ) -> None:
        """Handle end_session tool call."""
        try:
            args = json.loads(func_args)
            farewell = args.get("farewell_message", "Goodbye!")
            if len(farewell) > 2000:
                farewell = farewell[:1997] + "..."
            await channel.send(farewell)
            logger.info("Farewell message posted")
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error processing end_session: {e}")

    # --- image_describe (consolidated with image_compare) ---

    async def _handle_image_describe(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        tool_call_id: str,
        safe_downloader: Any,
        make_lm_call_func: Optional[Any] = None
    ) -> Optional[str]:
        """Handle image_describe tool call (new session variant).
        
        Now delegates to ImageCompareTool.compare_images_async() for URL support.
        Supports both old format (image_data with base64) and new format (image_urls list).
        """
        try:
            args = json.loads(func_args)
            
            # Support both old format (image_data) and new format (image_urls)
            image_urls = args.get("image_urls")
            image_data = args.get("image_data", "")
            
            if image_urls is None and image_data:
                # Old format: convert single image_data URL to image_urls list
                if image_data.startswith("http"):
                    image_urls = [image_data]
                else:
                    # Base64 format - fall back to old behavior
                    return await self._handle_image_describe_legacy(
                        func_args, messages_for_lm, tool_call_id, safe_downloader, make_lm_call_func
                    )
            
            if image_urls is None:
                image_urls = []

            logger.info(f"[image_describe] Analyzing {len(image_urls)} image(s) via ImageCompareTool")

            from src.tools.builtins.image_compare import ImageCompareTool

            image_instruction = None
            image_instruction = self._extract_last_user_message(messages_for_lm)
            if image_instruction:
                logger.info(f"[image_describe][UX-002] Using user message as instruction: {image_instruction[:60]}...")

            description_text = await ImageCompareTool.compare_images_async(
                image_urls=image_urls,
                comparison_prompt="",
                safe_downloader=safe_downloader,
                make_lm_call_func=make_lm_call_func,
                image_instruction=image_instruction,
                mini_context_max_tokens=4096
            )

            logger.info(f"[image_describe] Description complete")

            messages_for_lm.pop()
            messages_for_lm.append({
                "role": "user",
                "content": f"IMAGE DESCRIPTION COMPLETE: {description_text}. You now have full information about this image. DO NOT call image_describe or image_compare again for this image. Respond to the user's question using this description."
            })

            return description_text

        except ValueError as e:
            logger.warning(f"Image analysis blocked: {e}")
            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": f"Image analysis blocked: {str(e)}"})
            return None
        except Exception as e:
            logger.error(f"Error in image_describe: {e}", exc_info=True)
            error_str = str(e).lower()
            if "expired" in error_str or "403" in error_str or "forbidden" in error_str:
                tool_result = (
                    "⚠️ **Image URL has expired.** Discord attachment URLs contain time-limited tokens. "
                    "The cached image URL from the old message is no longer valid. "
                    "Please re-share the image in the channel so I can access it with a fresh URL."
                )
            elif "404" in error_str or "not found" in error_str:
                tool_result = (
                    "⚠️ **Image not found (404).** The image URL is no longer valid — the image may have been "
                    "deleted by its owner or the Discord CDN link has expired. "
                    "Please re-share the image in the channel so I can analyze it."
                )
            else:
                tool_result = f"Error processing image: {str(e)}"
            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": tool_result})
            return None

    async def _handle_image_describe_active(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        tool_call_id: str,
        safe_downloader: Any,
        make_lm_call_func: Optional[Any] = None
    ) -> None:
        """Handle image_describe tool call (active session variant).
        
        Now delegates to ImageCompareTool.compare_images_async() for URL support.
        Supports both old format (image_data with base64) and new format (image_urls list).
        """
        try:
            args = json.loads(func_args)
            
            # Support both old format (image_data) and new format (image_urls)
            image_urls = args.get("image_urls")
            image_data = args.get("image_data", "")
            
            if image_urls is None and image_data:
                # Old format: convert single image_data URL to image_urls list
                if image_data.startswith("http"):
                    image_urls = [image_data]
                else:
                    # Base64 format - fall back to old behavior
                    await self._handle_image_describe_legacy_active(
                        func_args, messages_for_lm, tool_call_id, safe_downloader, make_lm_call_func
                    )
                    return
            
            if image_urls is None:
                image_urls = []

            logger.info(f"[image_describe] Analyzing {len(image_urls)} image(s) via ImageCompareTool (active session)")

            from src.tools.builtins.image_compare import ImageCompareTool

            image_instruction = self._extract_last_user_message(messages_for_lm)
            if image_instruction:
                logger.info(f"[image_describe][UX-002] Using user message as instruction (active): {image_instruction[:60]}...")

            description_text = await ImageCompareTool.compare_images_async(
                image_urls=image_urls,
                comparison_prompt="",
                safe_downloader=safe_downloader,
                make_lm_call_func=make_lm_call_func,
                image_instruction=image_instruction,
                mini_context_max_tokens=4096
            )

            logger.info(f"[image_describe] Description complete (active session)")

            messages_for_lm.pop()
            messages_for_lm.append({
                "role": "user",
                "content": f"IMAGE DESCRIPTION COMPLETE: {description_text}. You now have full information about this image. DO NOT call image_describe or image_compare again for this image. Respond to the user's question using this description."
            })

        except ValueError as e:
            logger.warning(f"Image analysis blocked: {e}")
            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": f"Image analysis blocked: {str(e)}"})
        except Exception as e:
            logger.error(f"Error in image_describe (active): {e}", exc_info=True)
            error_str = str(e).lower()
            if "expired" in error_str or "403" in error_str or "forbidden" in error_str:
                tool_result = (
                    "⚠️ **Image URL has expired.** Discord attachment URLs contain time-limited tokens. "
                    "The cached image URL from the old message is no longer valid. "
                    "Please re-share the image in the channel so I can access it with a fresh URL."
                )
            elif "404" in error_str or "not found" in error_str:
                tool_result = (
                    "⚠️ **Image not found (404).** The image URL is no longer valid — the image may have been "
                    "deleted by its owner or the Discord CDN link has expired. "
                    "Please re-share the image in the channel so I can analyze it."
                )
            else:
                tool_result = f"Error processing image: {str(e)}"
            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": tool_result})

    async def _handle_image_describe_legacy(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        tool_call_id: str,
        safe_downloader: Any,
        make_lm_call_func: Optional[Any] = None
    ) -> Optional[str]:
        """Handle image_describe tool call with base64 data (legacy variant)."""
        image_description = None
        try:
            args = json.loads(func_args)
            image_data = args.get("image_data", "")
            mime_type = args.get("mime_type", "image/jpeg")

            logger.info(f"Executing image_describe tool (legacy base64) with image_data length: {len(image_data)}")

            if image_data.startswith("http"):
                raw_bytes = await safe_downloader.download_image(image_data)
                logger.info(f"Downloaded {len(raw_bytes)} bytes from URL")

                from src.utils import resize_image_bytes, image_to_base64
                compressed_bytes, output_mime = resize_image_bytes(raw_bytes, max_dimension=768, quality=85)
                processed_base64 = image_to_base64(compressed_bytes)

                image_instruction = self._extract_last_user_message(messages_for_lm)
                mini_context = self._build_mini_context(processed_base64, output_mime, image_instruction=image_instruction)

                logger.info(f"[Fix 2c] Using isolated mini-context for image description (legacy)"
                           f"{f' (instruction: {image_instruction[:40]}...)' if image_instruction else ''}")
                mini_response = await self._get_mini_context_response(mini_context, make_lm_call_func)

                image_description = self._extract_description(mini_response)
                logger.info(f"[Fix 2c] Image description obtained: {repr(image_description[:80])}...")

                messages_for_lm.pop()
                messages_for_lm.append({
                    "role": "user",
                    "content": f"IMAGE DESCRIPTION COMPLETE: {image_description}. You now have full information about this image. DO NOT call image_describe again for this image. Respond to the user's question using this description."
                })

        except ValueError as e:
            logger.warning(f"Image download blocked: {e}")
            tool_result = self._build_blocked_url_error()
            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": tool_result})
        except Exception as e:
            logger.error(f"Error executing image_describe: {e}", exc_info=True)
            error_str = str(e).lower()
            if "expired" in error_str or "403" in error_str or "forbidden" in error_str:
                tool_result = (
                    "⚠️ **Image URL has expired.** Discord attachment URLs contain time-limited tokens. "
                    "The cached image URL from the old message is no longer valid. "
                    "Please re-share the image in the channel so I can access it with a fresh URL."
                )
            elif "404" in error_str or "not found" in error_str:
                tool_result = (
                    "⚠️ **Image not found (404).** The image URL is no longer valid — the image may have been "
                    "deleted by its owner or the Discord CDN link has expired. "
                    "Please re-share the image in the channel so I can analyze it."
                )
            else:
                tool_result = f"Error processing image: {str(e)}"
            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": tool_result})

        return image_description

    async def _handle_image_describe_legacy_active(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        tool_call_id: str,
        safe_downloader: Any,
        make_lm_call_func: Optional[Any] = None
    ) -> None:
        """Handle image_describe tool call with base64 data (legacy active session variant)."""
        try:
            args = json.loads(func_args)
            image_data = args.get("image_data", "")
            mime_type = args.get("mime_type", "image/jpeg")

            logger.info(f"Executing image_describe tool (legacy base64, active) with image_data length: {len(image_data)}")

            if image_data.startswith("http"):
                raw_bytes = await safe_downloader.download_image(image_data)
                logger.info(f"Downloaded {len(raw_bytes)} bytes from URL")

                from src.utils import resize_image_bytes, image_to_base64
                compressed_bytes, output_mime = resize_image_bytes(raw_bytes, max_dimension=768, quality=85)
                processed_base64 = image_to_base64(compressed_bytes)

                image_instruction = self._extract_last_user_message(messages_for_lm)
                mini_context = self._build_mini_context(processed_base64, output_mime, image_instruction=image_instruction)

                logger.info(f"[Fix 2c] Using isolated mini-context for image description (active session, legacy)"
                           f"{f' (instruction: {image_instruction[:40]}...)' if image_instruction else ''}")
                mini_response = await self._get_mini_context_response(mini_context, make_lm_call_func)

                image_description = self._extract_description(mini_response)
                logger.info(f"[Fix 2c] Image description obtained: {repr(image_description[:80])}...")

                messages_for_lm.pop()
                messages_for_lm.append({
                    "role": "user",
                    "content": f"IMAGE DESCRIPTION COMPLETE: {image_description}. You now have full information about this image. DO NOT call image_describe again for this image. Respond to the user's question using this description."
                })

        except ValueError as e:
            logger.warning(f"Image download blocked: {e}")
            tool_result = self._build_blocked_url_error()
            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": tool_result})
        except Exception as e:
            logger.error(f"Error executing image_describe: {e}", exc_info=True)
            error_str = str(e).lower()
            if "expired" in error_str or "403" in error_str or "forbidden" in error_str:
                tool_result = (
                    "⚠️ **Image URL has expired.** Discord attachment URLs contain time-limited tokens. "
                    "The cached image URL from the old message is no longer valid. "
                    "Please re-share the image in the channel so I can access it with a fresh URL."
                )
            elif "404" in error_str or "not found" in error_str:
                tool_result = (
                    "⚠️ **Image not found (404).** The image URL is no longer valid — the image may have been "
                    "deleted by its owner or the Discord CDN link has expired. "
                    "Please re-share the image in the channel so I can analyze it."
                )
            else:
                tool_result = f"Error processing image: {str(e)}"
            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": tool_result})

    # --- image_compare ---

    async def _handle_image_compare(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        tool_call_id: str,
        safe_downloader: Any,
        make_lm_call_func: Optional[Any] = None
    ) -> Optional[str]:
        """Handle image_compare tool call (new session variant)."""
        try:
            args = json.loads(func_args)
            image_urls = args.get("image_urls", [])
            comparison_prompt = args.get("comparison_prompt", "")

            logger.info(f"[image_compare] Comparing {len(image_urls)} images")

            from src.tools.builtins.image_compare import ImageCompareTool

            image_instruction = None
            if not comparison_prompt:
                image_instruction = self._extract_last_user_message(messages_for_lm)
                if image_instruction:
                    logger.info(f"[image_compare][UX-002] Using user message as instruction: {image_instruction[:60]}...")

            comparison_text = await ImageCompareTool.compare_images_async(
                image_urls=image_urls,
                comparison_prompt=comparison_prompt,
                safe_downloader=safe_downloader,
                make_lm_call_func=make_lm_call_func,
                image_instruction=image_instruction,
                mini_context_max_tokens=4096
            )

            logger.info(f"[image_compare] Comparison complete")

            messages_for_lm.pop()
            messages_for_lm.append({
                "role": "user",
                "content": f"IMAGE COMPARISON COMPLETE: {comparison_text}. You now have a full comparison of all images. Respond to the user's question using this comparison."
            })

        except ValueError as e:
            logger.warning(f"Image compare blocked: {e}")
            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": f"Image comparison blocked: {str(e)}"})
        except Exception as e:
            logger.error(f"Error in image_compare: {e}", exc_info=True)
            # Check if this is an expired token error (stale CDN URL from old message embed)
            error_str = str(e).lower()
            if "expired" in error_str or "403" in error_str or "forbidden" in error_str:
                tool_result = (
                    "⚠️ **Image URL has expired.** Discord attachment URLs contain time-limited tokens. "
                    "The cached image URL from the old message is no longer valid. "
                    "Please re-share the image in the channel so I can access it with a fresh URL."
                )
            elif "404" in error_str or "not found" in error_str:
                tool_result = (
                    "⚠️ **Image not found (404).** The image URL is no longer valid — the image may have been "
                    "deleted by its owner or the Discord CDN link has expired. "
                    "Please re-share the image in the channel so I can analyze it."
                )
            else:
                tool_result = f"Error during image comparison: {str(e)}"
            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": tool_result})

    async def _handle_image_compare_active(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        tool_call_id: str,
        safe_downloader: Any,
        make_lm_call_func: Optional[Any] = None
    ) -> None:
        """Handle image_compare tool call (active session variant)."""
        try:
            args = json.loads(func_args)
            image_urls = args.get("image_urls", [])
            comparison_prompt = args.get("comparison_prompt", "")

            logger.info(f"[image_compare] Comparing {len(image_urls)} images (active session)")

            from src.tools.builtins.image_compare import ImageCompareTool

            image_instruction = None
            if not comparison_prompt:
                image_instruction = self._extract_last_user_message(messages_for_lm)
                if image_instruction:
                    logger.info(f"[image_compare][UX-002] Using user message as instruction (active): {image_instruction[:60]}...")

            comparison_text = await ImageCompareTool.compare_images_async(
                image_urls=image_urls,
                comparison_prompt=comparison_prompt,
                safe_downloader=safe_downloader,
                make_lm_call_func=make_lm_call_func,
                image_instruction=image_instruction,
                mini_context_max_tokens=4096
            )

            logger.info(f"[image_compare] Comparison complete (active session)")

            messages_for_lm.pop()
            messages_for_lm.append({
                "role": "user",
                "content": f"IMAGE COMPARISON COMPLETE: {comparison_text}. You now have a full comparison of all images. Respond to the user's question using this comparison."
            })

        except ValueError as e:
            logger.warning(f"Image compare blocked: {e}")
            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": f"Image comparison blocked: {str(e)}"})
        except Exception as e:
            logger.error(f"Error in image_compare (active): {e}", exc_info=True)
            # Check if this is an expired token error (stale CDN URL from old message embed)
            error_str = str(e).lower()
            if "expired" in error_str or "403" in error_str or "forbidden" in error_str:
                tool_result = (
                    "⚠️ **Image URL has expired.** Discord attachment URLs contain time-limited tokens. "
                    "The cached image URL from the old message is no longer valid. "
                    "Please re-share the image in the channel so I can access it with a fresh URL."
                )
            elif "404" in error_str or "not found" in error_str:
                tool_result = (
                    "⚠️ **Image not found (404).** The image URL is no longer valid — the image may have been "
                    "deleted by its owner or the Discord CDN link has expired. "
                    "Please re-share the image in the channel so I can analyze it."
                )
            else:
                tool_result = f"Error during image comparison: {str(e)}"
            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": tool_result})

    # --- channel_search ---

    async def _handle_channel_search(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        tool_call_id: str,
        get_bot_instance: Optional[Any] = None,
        make_lm_call_func: Optional[Any] = None
    ) -> None:
        """Handle channel_search tool call (new session variant)."""
        try:
            args = json.loads(func_args)
            channel = args.get("channel", "")
            limit = args.get("limit", 15)
            search_query = args.get("search_query", "")
            username = args.get("username", "")
            compress_long = args.get("compress_long", True)
            user_feedback = args.get("user_feedback", "")
            offset = args.get("offset", 0)
            windows = args.get("windows", 1)

            channel_display = channel if channel else "(all channels)"
            logger.info(f"[channel_search] Searching channel {channel_display} (limit={limit}, query='{search_query}')"
                       f"{f', feedback={user_feedback[:60]}' if user_feedback else ''}")

            if get_bot_instance is None:
                logger.warning("[channel_search] No bot instance provided, returning error")
                messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": "Error: Bot instance not available for channel search"})
                return

            bot = get_bot_instance()
            if bot is None:
                messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": "Error: Bot not available"})
                return

            message_id = args.get("message_id")

            result = await bot.get_channel_messages(
                channel=str(channel),
                limit=int(limit),
                search_query=str(search_query),
                username=str(username),
                compress_long=bool(compress_long),
                offset=int(offset),
                windows=int(windows),
            )

            messages = result.get("messages", [])
            available_channels = result.get("available_channels", {})

            if message_id and messages:
                try:
                    target_channel_id = messages[0].get("channel_id") if messages else None
                    if target_channel_id:
                        msg_data = await bot.get_message_by_id(int(target_channel_id), int(message_id))
                        if msg_data and msg_data.get("message"):
                            fetched_msg = msg_data["message"]
                            logger.info(f"[channel_search] Fetched message {message_id}: has_image={fetched_msg.get('has_image', False)}, image_urls={fetched_msg.get('image_urls', [])}")
                            messages.insert(0, fetched_msg)
                except Exception as e:
                    logger.warning(f"Failed to fetch message {message_id} for image URLs: {e}")

            if not messages:
                error_msg = result.get("error", "No messages found matching the specified criteria.")
                if available_channels:
                    channels_list = ", ".join([f"{name} (ID: {id})" for name, id in list(available_channels.items())[:10]])
                    tool_content = f"{error_msg}\n\nAvailable channels: {channels_list}"
                else:
                    tool_content = error_msg
            elif make_lm_call_func and len(messages) > 5:
                tool_content = await self._summarize_channel_search_batched(messages, search_query, user_feedback, make_lm_call_func)
            else:
                tool_content = self._format_channel_search_direct(messages, search_query, user_feedback, available_channels)

            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": tool_content})
            self._cache_tool_result("channel_search", func_args, tool_content)
            logger.info(f"[channel_search] Returned {len(messages)} messages" if not (make_lm_call_func and len(messages) > 5) else f"[channel_search] Returned {len(messages)} messages (summarized via mini-context)")

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing channel_search args: {e}")
            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": f"Error: Invalid arguments for channel_search: {str(e)}"})
        except Exception as e:
            logger.error(f"Error in channel_search: {e}", exc_info=True)
            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": f"Error during channel search: {str(e)}"})

    async def _handle_channel_search_active(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        tool_call_id: str,
        get_bot_instance: Optional[Any] = None,
        make_lm_call_func: Optional[Any] = None
    ) -> None:
        """Handle channel_search tool call (active session variant)."""
        await self._handle_channel_search(func_args, messages_for_lm, tool_call_id, get_bot_instance, make_lm_call_func)

    # --- memory_tool ---

    async def _handle_memory_tool(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        tool_call_id: str,
        get_bot_instance: Optional[Any] = None
    ) -> Optional[str]:
        """Handle memory_tool call (new session variant)."""
        try:
            args = json.loads(func_args)
            operation = args.pop("operation", "")

            if get_bot_instance is None:
                logger.warning("[memory_tool] No bot instance provided")
                messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": "Error: Bot instance not available for memory_tool"})
                return None

            bot = get_bot_instance()
            if bot is None:
                messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": "Error: Bot not available for memory_tool"})
                return None

            memory_tool = bot._memory_tool
            if memory_tool is None:
                messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": "Error: Memory tool not initialized"})
                return None

            result = memory_tool.execute(operation, **args)

            if result.success:
                tool_content = result.content
            else:
                tool_content = f"Error: {result.error}"

            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": tool_content})
            logger.info(f"[memory_tool] Executed operation '{operation}' successfully")
            return None

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing memory_tool args: {e}")
            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": f"Error: Invalid arguments for memory_tool: {str(e)}"})
            return None
        except Exception as e:
            logger.error(f"Error in memory_tool: {e}", exc_info=True)
            messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": f"Error during memory operation: {str(e)}"})
            return None

    async def _handle_memory_tool_active(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        tool_call_id: str,
        get_bot_instance: Optional[Any] = None
    ) -> Optional[Dict]:
        """Handle memory_tool call (active session variant)."""
        await self._handle_memory_tool(func_args, messages_for_lm, tool_call_id, get_bot_instance)
        return None

    # --- Helper Methods ---

    def _build_mini_context(self, base64_data: str, mime_type: str, image_instruction: Optional[str] = None) -> List[Dict]:
        """Build mini-context for image description."""
        if image_instruction is None:
            image_instruction = "Please describe this image in detail, up to 3-4 sentences. Focus on key visual elements, colors, objects, and composition."
        return [
            {"role": "user", "content": [
                {"type": "text", "text": image_instruction},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_data}"}}
            ]}
        ]

    def _extract_last_user_message(self, messages_for_lm: List[Dict]) -> Optional[str]:
        """Extract the last user message text from conversation history."""
        for msg in reversed(messages_for_lm):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    text = content.strip()
                    text = re.sub(r'[A-Za-z0-9+/]{50,}={0,2}', '', text)
                    text = re.sub(r'https?://\S+', '', text)
                    text = re.sub(r'data:image/[a-z]+;base64,[A-Za-z0-9+/=]+', '', text)
                    text = re.sub(r'cdn\.discordapp\.com\S+', '', text)
                    text = re.sub(r'cdn\.discordix\.com\S+', '', text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    if text:
                        return text
        return None

    async def _get_mini_context_response(self, mini_context: List[Dict], make_lm_call_func: Optional[Any] = None, max_tokens: Optional[int] = None) -> Dict:
        """Get response from LM Studio using mini-context."""
        if make_lm_call_func:
            return await make_lm_call_func(mini_context, channel_id=None, use_tool_calling=False, max_tokens=max_tokens)
        logger.warning("No make_lm_call_func provided for mini-context")
        return {"choices": []}

    def _extract_description(self, mini_response: Dict) -> str:
        """Extract image description from mini-context response."""
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

    # --- Channel Search Summarization ---

    def _format_messages_for_summarization(self, messages: List[Dict]) -> str:
        """Format messages into a text block suitable for mini-context summarization."""
        lines = []
        for i, msg in enumerate(messages, 1):
            author = msg.get("display_name", msg.get("author", "Unknown"))
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            is_reply = msg.get("is_reply", False)
            replied_to_author = msg.get("replied_to_author")
            replied_to_content = msg.get("replied_to_content")
            channel_name = msg.get("_channel_name", "")
            has_image = msg.get("has_image", False)
            image_urls = msg.get("image_urls", [])

            if is_reply and replied_to_author:
                reply_preview = replied_to_content[:80] if replied_to_content else ""
                lines.append(f"[Reply to {replied_to_author}: \"{reply_preview}\"]")
            if channel_name:
                lines.append(f"[#{channel_name}]")
            lines.append(f"--- Message {i} by {author} at {timestamp} ---")
            lines.append(content)
            if has_image and image_urls:
                urls_str = ", ".join(image_urls)
                lines.append(f"[Contains {len(image_urls)} image(s): {urls_str}]")
            elif has_image:
                lines.append("[Contains image]")
        return "\n".join(lines)

    async def _summarize_channel_search_batched(
        self,
        messages: List[Dict],
        search_query: str,
        user_feedback: str,
        make_lm_call_func: Any,
        batch_size: int = 10,
        max_tokens: int = 1024
    ) -> str:
        """Summarize channel search results using mini-context batched summarization."""
        total = len(messages)
        summaries = []

        for start_idx in range(0, total, batch_size):
            end_idx = min(start_idx + batch_size, total)
            batch = messages[start_idx:end_idx]

            batch_text = self._format_messages_for_summarization(batch)

            summarization_prompt = (
                f"These are recent Discord messages from a channel search. "
                f"Search query was: '{search_query}'"
                f"{' User context: ' + user_feedback if user_feedback else ''}."
                f"\n\nPlease provide a concise summary of the key points, "
                f"topics discussed, and any relevant information. "
                f"Focus on facts, decisions, and actionable items. "
                f"Keep the summary under 150 words.\n\n---\n{batch_text}"
            )

            mini_context = [{"role": "user", "content": summarization_prompt}]

            logger.info(f"[channel_search] Summarizing batch {len(summaries)+1} (messages {start_idx+1}-{end_idx}/{total})")

            try:
                response = await make_lm_call_func(mini_context, channel_id=None, use_tool_calling=False, max_tokens=max_tokens)
                choices = response.get("choices", [])
                if choices:
                    summary = choices[0].get("message", {}).get("content", "")
                    summary_stripped = summary.strip() if summary else ""
                    summaries.append(f"--- Batch {len(summaries)+1} Summary ---\n{summary_stripped}")
                    logger.info(f"[channel_search] Batch {len(summaries)} summary content: {repr(summary_stripped[:300])}")
                else:
                    summaries.append(f"--- Batch {len(summaries)+1} Summary ---\n[No summary generated]")
                    logger.warning(f"[channel_search] Batch {len(summaries)}: No choices in LM response")
            except Exception as e:
                logger.error(f"[channel_search] Mini-context summarization failed for batch {len(summaries)+1}: {e}")
                summaries.append(f"--- Batch {len(summaries)+1} Summary ---\n[Summarization error: {str(e)[:100]}]")

        combined = "\n\n".join(summaries)
        final_result = (
            f"📋 Channel Search Results (batch-summarized from {total} messages):\n\n"
            f"Search query: '{search_query}'\n\n"
            f"{combined}\n\n"
            f"Total messages searched: {total}\n"
            f"=== END OF RESULTS ==="
        )

        logger.info(f"[channel_search] Batch summarization complete: {total} messages -> {len(summaries)} summaries")
        logger.info(f"[channel_search] Final combined result ({len(final_result)} chars): {repr(final_result[:500])}")
        return final_result

    def _format_channel_search_direct(
        self,
        messages: List[Dict],
        search_query: str,
        user_feedback: str,
        available_channels: Optional[Dict] = None
    ) -> str:
        """Format channel search results directly without mini-context summarization."""
        if not messages:
            error_msg = "No messages found matching the specified criteria."
            if available_channels:
                channels_list = ", ".join([f"{name} (ID: {id})" for name, id in list(available_channels.items())[:10]])
                return f"{error_msg}\n\nAvailable channels: {channels_list}"
            return error_msg

        result_lines = [f"=== Channel Search Results ==="]
        result_lines.append(f"Search query: '{search_query}'")
        result_lines.append(f"Total matches: {len(messages)} messages")
        result_lines.append(f"")

        for i, msg in enumerate(messages, 1):
            author = msg.get("display_name", msg.get("author", "Unknown"))
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            is_reply = msg.get("is_reply", False)
            replied_to = msg.get("replied_to_author")
            channel_name = msg.get("_channel_name", "")
            msg_message_id = msg.get("message_id")
            msg_channel_id = msg.get("channel_id")
            guild_id = msg.get("guild_id")

            entry_parts = []
            if channel_name:
                entry_parts.append(f"[#{channel_name}]")
            entry_parts.append(f"{i}. **{author}** at {timestamp}")
            if is_reply and replied_to:
                entry_parts.append(f"(Reply to {replied_to})")
            entry_line = " ".join(entry_parts) + ":"

            result_lines.append(entry_line)
            result_lines.append(f"  CONTENT: {content}")

            image_urls = msg.get("image_urls", [])
            if image_urls:
                urls_str = ", ".join(image_urls)
                result_lines.append(f"  IMAGES: {urls_str}")

            if msg_message_id and msg_channel_id and guild_id:
                jump_link = f"https://discord.com/channels/{guild_id}/{msg_channel_id}/{msg_message_id}"
                result_lines.append(f"  REF: {jump_link}")

        result_lines.append(f"")
        result_lines.append(f"=== END OF RESULTS ===")
        if user_feedback:
            result_lines.append(f"USER CONTEXT: {user_feedback}")
        result_lines.append(f"INSTRUCTIONS: Read the messages above. If the search query was '{search_query}', identify which messages contain this term and provide a direct answer to the user's original question.")

        return "\n".join(result_lines)