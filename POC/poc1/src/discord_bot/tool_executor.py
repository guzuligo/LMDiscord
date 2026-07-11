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
            elif func_name == "context_compress":
                result = await self._handle_context_compress(
                    func_args, messages_for_lm, tool_call_id, make_lm_call_func
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
            elif func_name == "context_compress":
                result = await self._handle_context_compress_active(
                    func_args, messages_for_lm, tool_call_id, make_lm_call_func
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
        make_lm_call_func: Optional[Any] = None,
        check_pending: Optional[Any] = None
    ) -> Optional[str]:
        """Handle image_describe tool call with base64 data (legacy variant).
        
        Args:
            check_pending: Optional callable to check for pending messages (FEAT-008)
        """
        image_description = None
        try:
            args = json.loads(func_args)
            image_data = args.get("image_data", "")
            mime_type = args.get("mime_type", "image/jpeg")

            logger.info(f"Executing image_describe tool (legacy base64) with image_data length: {len(image_data)}")

            if image_data.startswith("http"):
                raw_bytes = await safe_downloader.download_image(image_data)
                logger.info(f"Downloaded {len(raw_bytes)} bytes from URL")

                # Check for pending messages before processing (FEAT-008)
                if check_pending:
                    pending = await check_pending()
                    if pending:
                        logger.info("Pending message detected during image download, interrupting")
                        return {"interrupted": True, "pending_message": pending}

                from src.utils import resize_image_bytes, image_to_base64
                compressed_bytes, output_mime = resize_image_bytes(raw_bytes, max_dimension=768, quality=85)
                processed_base64 = image_to_base64(compressed_bytes)

                # Check for pending messages before LM call (FEAT-008)
                if check_pending:
                    pending = await check_pending()
                    if pending:
                        logger.info("Pending message detected before mini-context LM call, interrupting")
                        return {"interrupted": True, "pending_message": pending}

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
            before_message_id = args.get("before_message_id")

            channel_display = channel if channel else "(all channels)"
            extra_info = []
            if user_feedback:
                extra_info.append(f"feedback={user_feedback[:60]}")
            if before_message_id:
                extra_info.append(f"before_message_id={before_message_id}")
            logger.info(f"[channel_search] Searching channel {channel_display} (limit={limit}, query='{search_query}')"
                        f"{f', {', '.join(extra_info)}' if extra_info else ''}")

            if get_bot_instance is None:
                logger.warning("[channel_search] No bot instance provided, returning error")
                messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": "Error: Bot instance not available for channel search"})
                return

            bot = get_bot_instance()
            if bot is None:
                messages_for_lm.append({"role": "tool", "tool_call_id": tool_call_id, "content": "Error: Bot not available"})
                return

            # Extract message_id and channel_id from args (from parsed Discord message link)
            message_id = args.get("message_id")
            link_channel_id = args.get("channel_id")  # Original channel_id from the message link

            # FALLBACK: If LM didn't provide message_id/channel_id but the user shared a link,
            # extract them from conversation history (user messages contain Discord message links)
            if not message_id or not link_channel_id:
                extracted = self._extract_message_link_ids_from_history(messages_for_lm)
                if extracted:
                    mid, cid = extracted
                    if not message_id and mid:
                        message_id = mid
                        logger.info(f"[channel_search] Extracted message_id={message_id} from conversation history (fallback)")
                    if not link_channel_id and cid:
                        link_channel_id = cid
                        logger.info(f"[channel_search] Extracted channel_id={link_channel_id} from conversation history (fallback)")

            # If message_id or before_message_id is provided, pass them to get_channel_messages
            result = await bot.get_channel_messages(
                channel=str(channel),
                limit=int(limit),
                search_query=str(search_query),
                username=str(username),
                compress_long=bool(compress_long),
                offset=int(offset),
                windows=int(windows),
                message_id=int(message_id) if message_id else None,
                link_channel_id=int(link_channel_id) if link_channel_id else None,
                before_message_id=int(before_message_id) if before_message_id else None,
            )

            messages = result.get("messages", [])
            available_channels = result.get("available_channels", {})

            # NEW: Extract message_id references from message content and fetch
            # the referenced messages to get their actual image_urls.
            # This catches cases where the bot says "I found images in message 1524..."
            # but the image URLs are only in the original message's image_urls field.
            if bot and messages:
                existing_ids = {m.get("message_id") for m in messages if m.get("message_id")}
                messages = await self._fetch_referenced_messages(messages, bot, existing_ids)

            # If message_id was provided but get_channel_messages didn't fetch it,
            # try fetching from the original channel_id from the link
            if message_id and not any(m.get("id") == str(message_id) for m in messages):
                try:
                    # Use the original channel_id from the message link, NOT messages[0].get("channel_id")
                    target_channel_id = int(link_channel_id) if link_channel_id else None
                    if target_channel_id:
                        msg_data = await bot.get_message_by_id(target_channel_id, int(message_id))
                        if msg_data and msg_data.get("message"):
                            fetched_msg = msg_data["message"]
                            logger.info(f"[channel_search] Fetched message {message_id}: has_image={fetched_msg.get('has_image', False)}, image_urls={fetched_msg.get('image_urls', [])}")
                            messages.insert(0, fetched_msg)
                    else:
                        # Fallback: try from first matched message's channel (original behavior)
                        target_channel_id = messages[0].get("channel_id") if messages else None
                        if target_channel_id:
                            msg_data = await bot.get_message_by_id(int(target_channel_id), int(message_id))
                            if msg_data and msg_data.get("message"):
                                fetched_msg = msg_data["message"]
                                logger.info(f"[channel_search] Fetched message {message_id} (fallback): has_image={fetched_msg.get('has_image', False)}, image_urls={fetched_msg.get('image_urls', [])}")
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
                # BUG-SEARCH-006 FIX: Conditional batch summarization
                # Only summarize when result text would be too large for direct formatting.
                # Estimate direct format size: ~150 chars per message + headers
                estimated_direct_size = len(messages) * 150 + 500
                # Threshold: only summarize if estimated direct format > 3000 chars
                # This avoids unnecessary LM calls when direct formatting suffices
                USE_BATCH_SUMMARIZATION_THRESHOLD = 3000
                if estimated_direct_size > USE_BATCH_SUMMARIZATION_THRESHOLD:
                    logger.info(f"[channel_search] Result size {estimated_direct_size} > threshold {USE_BATCH_SUMMARIZATION_THRESHOLD}, using batch summarization")
                    tool_content = await self._summarize_channel_search_batched(messages, search_query, user_feedback, make_lm_call_func)
                else:
                    logger.info(f"[channel_search] Result size {estimated_direct_size} <= threshold {USE_BATCH_SUMMARIZATION_THRESHOLD}, using direct formatting")
                    tool_content = self._format_channel_search_direct(messages, search_query, user_feedback, available_channels)
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

    # --- context_compress ---

    async def _handle_context_compress(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        tool_call_id: str,
        make_lm_call_func: Optional[Any] = None
    ) -> Optional[str]:
        """Handle context_compress tool call (new session variant).
        
        Passes messages_for_lm and make_lm_call_func to the compressor for real LM-based summarization.
        Replaces compressed messages in messages_for_lm with the summary.
        """
        try:
            args = json.loads(func_args)
            compress_before_index = args.get("compress_before_index", 0)
            target_summary_length = args.get("target_summary_length", 300)
            messages_to_keep_fresh = args.get("messages_to_keep_fresh", 6)

            logger.info(f"[context_compress] Compressing messages before index {compress_before_index}")
            logger.info(f"[context_compress] Conversation history size: {len(messages_for_lm)} messages")

            from src.tools.builtins.context_compressor import ContextCompressorTool

            compressor = ContextCompressorTool()
            result = await compressor.execute(
                compress_before_index=compress_before_index,
                target_summary_length=target_summary_length,
                messages_to_keep_fresh=messages_to_keep_fresh,
                messages_for_lm=messages_for_lm,
                make_lm_call_func=make_lm_call_func
            )

            if result.success:
                # Replace compressed messages: remove all messages before compress_before_index
                # and insert the summary as a single system message
                summary_msg = {
                    "role": "system",
                    "content": f"[CONTEXT COMPRESSION]\n{result.content}"
                }
                
                # Replace messages: remove old messages, keep fresh ones, add summary
                fresh_messages = messages_for_lm[compress_before_index:]
                new_messages = [summary_msg] + fresh_messages
                
                # Replace the entire messages_for_lm list content
                messages_for_lm.clear()
                messages_for_lm.extend(new_messages)
                
                logger.info(
                    f"[context_compress] Compression successful: "
                    f"{len(messages_for_lm)} messages (was {len(messages_for_lm) + compress_before_index}), "
                    f"summary: {result.content[:100]}..."
                )
                return None
            else:
                messages_for_lm.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result.error or result.message
                })
                return None

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing context_compress args: {e}")
            messages_for_lm.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": f"Error: Invalid arguments for context_compress: {str(e)}"
            })
            return None
        except Exception as e:
            logger.error(f"Error in context_compress: {e}", exc_info=True)
            messages_for_lm.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": f"Error during context compression: {str(e)}"
            })
            return None

    async def _handle_context_compress_active(
        self,
        func_args: str,
        messages_for_lm: List[Dict],
        tool_call_id: str,
        make_lm_call_func: Optional[Any] = None
    ) -> Optional[Dict]:
        """Handle context_compress tool call (active session variant)."""
        await self._handle_context_compress(func_args, messages_for_lm, tool_call_id, make_lm_call_func)
        return None

    # --- Message Reference Extraction ---

    @staticmethod
    def _extract_message_ids_from_content(messages: List[Dict]) -> List[tuple]:
        """Extract message_id and channel_id references from message content.

        Scans message content for patterns like:
        - "message `1524101243654373617`"
        - "message 1524101243654373617"
        - Discord message links: https://discord.com/channels/GUILD/CHANNEL/MESSAGE
        - https://discordapp.com/channels/GUILD/CHANNEL/MESSAGE

        Returns:
            List of tuples (message_id, channel_id, source_message_index).
        """
        references = []

        # Pattern 1: Discord message links
        link_pattern = re.compile(
            r'(?:discord\.com|discordapp\.com)/channels/\d+/(\d+)/(\d+)'
        )

        # Pattern 2: "message `123456...`" or "message 123456..."
        message_pattern = re.compile(
            r'message\s+[`\'"]?(\d{17,20})[`\'"]?'
        )

        for idx, msg in enumerate(messages):
            content = msg.get("content", "")
            if not isinstance(content, str):
                continue

            # Check for Discord message links
            for match in link_pattern.finditer(content):
                channel_id = match.group(1)
                message_id = match.group(2)
                references.append((message_id, channel_id, idx))

            # Check for "message `123456...`" pattern
            for match in message_pattern.finditer(content):
                message_id = match.group(1)
                # Use the message's own channel_id as fallback
                channel_id = msg.get("channel_id", "")
                if channel_id:
                    references.append((message_id, channel_id, idx))

        return references

    async def _fetch_referenced_messages(
        self,
        messages: List[Dict],
        bot: Any,
        existing_ids: set
    ) -> List[Dict]:
        """Fetch messages referenced by message_id in other messages' content.

        After channel search returns results, scan message content for
        message_id references (e.g., "message `1524101243654373617`" or
        Discord message links). Fetch those referenced messages to get
        their actual image_urls.

        Args:
            messages: List of message dicts from channel search.
            bot: The DiscordBot instance.
            existing_ids: Set of already-fetched message IDs to avoid duplicates.

        Returns:
            Updated messages list with referenced messages prepended.
        """
        references = self._extract_message_ids_from_content(messages)
        fetched = []

        for message_id, channel_id, _ in references:
            # Avoid fetching the same message twice
            if message_id in existing_ids:
                continue

            try:
                msg_data = await bot.get_message_by_id(
                    int(channel_id), int(message_id)
                )
                if msg_data and msg_data.get("message"):
                    fetched_msg = msg_data["message"]
                    logger.info(
                        f"[channel_search] Fetched referenced message {message_id}: "
                        f"has_image={fetched_msg.get('has_image', False)}, "
                        f"image_urls count={len(fetched_msg.get('image_urls', []))}"
                    )
                    fetched.append(fetched_msg)
                    existing_ids.add(message_id)
            except Exception as e:
                logger.warning(
                    f"[channel_search] Failed to fetch referenced message {message_id}: {e}"
                )

        # Prepend fetched messages to the beginning
        if fetched:
            messages = fetched + messages
            logger.info(
                f"[channel_search] Fetched {len(fetched)} referenced message(s) "
                f"with {sum(len(m.get('image_urls', [])) for m in fetched)} total image URLs"
            )

        return messages

    # --- Helper Methods ---

    @staticmethod
    def _extract_message_link_ids_from_history(messages_for_lm: List[Dict]) -> Optional[tuple]:
        """Extract message_id and channel_id from Discord message links in conversation history.
        
        Scans recent user messages for Discord message link patterns like:
        - https://discord.com/channels/GUILD_ID/CHANNEL_ID/MESSAGE_ID
        - https://discordapp.com/channels/GUILD_ID/CHANNEL_ID/MESSAGE_ID
        
        Returns:
            Tuple of (message_id, channel_id) as strings, or None if not found.
        """
        # Discord message link pattern: guild_id/channel_id/message_id
        pattern = r'(?:discord\.com|discordapp\.com)/channels/\d+/(\d+)/(\d+)'
        
        # Scan last 10 messages for Discord links
        for msg in reversed(messages_for_lm[-10:]):
            if msg.get("role") != "user":
                continue
            content = msg.get("content", "")
            if not isinstance(content, str):
                continue
            
            match = re.search(pattern, content)
            if match:
                channel_id = match.group(1)
                message_id = match.group(2)
                return (message_id, channel_id)
        
        return None

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
        """Format messages into a text block suitable for mini-context summarization.
        
        Includes universal reference metadata for all content types:
        - Images: URL + message_id + channel_id + guild_id
        - Files/Attachments: filename + URL + message_id + channel_id + guild_id
        - Links/Embeds: URL + message_id + channel_id + guild_id
        - Text Messages: content snippet + message_id + channel_id + guild_id
        - Replies: replied content + author + message_id + channel_id + guild_id
        """
        # Regex pattern to match Discord CDN image URLs and other image URLs
        import re
        image_url_pattern = re.compile(
            r'https?://[^\s<>\"\')\]]*\.(?:png|jpg|jpeg|gif|webp|bmp|svg)'
            r'(?:[^\s<>\"\')]*)?',
            re.IGNORECASE
        )

        lines = []
        # Track references for building the reference section
        image_refs = []  # [ref_idx, url, msg_id, ch_id, guild_id]
        file_refs = []   # [ref_idx, filename, url, msg_id, ch_id, guild_id]
        text_refs = []   # [ref_idx, content_snippet, msg_id, ch_id, guild_id]

        for i, msg in enumerate(messages, 1):
            author = msg.get("display_name", msg.get("author", "Unknown"))
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            is_reply = msg.get("is_reply", False)
            replied_to_author = msg.get("replied_to_author")
            replied_to_content = msg.get("replied_to_content")
            channel_name = msg.get("_channel_name", "")
            has_image = msg.get("has_image", False)
            image_urls = list(msg.get("image_urls", []))  # copy to avoid modifying original
            attachments = msg.get("attachments", [])
            msg_message_id = msg.get("message_id") or msg.get("id", "")
            msg_channel_id = msg.get("channel_id", "")
            guild_id = msg.get("guild_id", "")

            # Extract image URLs from message content text using regex
            content_urls = image_url_pattern.findall(content)
            for url in content_urls:
                while url and url[-1] in '.,;:!?)\'":]':
                    url = url[:-1]
                if url and url not in image_urls:
                    image_urls.append(url)

            # Build reference tag for this message
            ref_tag = ""
            if msg_message_id and msg_channel_id:
                ref_tag = f" [msg:{msg_message_id} ch:{msg_channel_id} guild:{guild_id}]"

            if is_reply and replied_to_author:
                reply_preview = replied_to_content[:80] if replied_to_content else ""
                lines.append(f"[Reply to {replied_to_author}: \"{reply_preview}\"]")
                # Track reply as text reference
                if replied_to_content:
                    text_refs.append([len(text_refs), replied_to_content[:100], msg_message_id, msg_channel_id, guild_id])
            if channel_name:
                lines.append(f"[#{channel_name}]{ref_tag}")
            lines.append(f"--- Message {i} by {author} at {timestamp} ---")
            lines.append(content)

            # Track images with references
            if image_urls:
                for url in image_urls:
                    ref_idx = len(image_refs)
                    image_refs.append([ref_idx, url, msg_message_id, msg_channel_id, guild_id])
                    lines.append(f"  ![image]({url}) [ref:img:{ref_idx}]")
                urls_str = ", ".join(image_urls)
                lines.append(f"[Contains {len(image_urls)} image(s): {urls_str}]")
            elif has_image:
                lines.append("[Contains image]")

            # Track file attachments with references
            if attachments:
                for att in attachments:
                    if isinstance(att, str):
                        ref_idx = len(file_refs)
                        file_refs.append([ref_idx, att, att, msg_message_id, msg_channel_id, guild_id])
                        lines.append(f"  [📎 Attachment: {att}] [ref:file:{ref_idx}]")
                    elif isinstance(att, dict):
                        filename = att.get("filename", "unknown")
                        url = att.get("url", "")
                        ref_idx = len(file_refs)
                        file_refs.append([ref_idx, filename, url, msg_message_id, msg_channel_id, guild_id])
                        lines.append(f"  [📎 Attachment: {filename}] [ref:file:{ref_idx}]")

            # Track main content as text reference for search queries
            if content and len(content.strip()) > 10:
                text_refs.append([len(text_refs), content[:150], msg_message_id, msg_channel_id, guild_id])

        # Add reference section at the end
        all_refs = []
        for r in image_refs:
            all_refs.append(f"[img:{r[0]}] {r[1]} → msg:{r[2]} ch:{r[3]} guild:{r[4]}")
        for r in file_refs:
            all_refs.append(f"[file:{r[0]}] {r[1]} → msg:{r[2]} ch:{r[3]} guild:{r[4]}")
        for r in text_refs:
            all_refs.append(f"[text:{r[0]}] \"{r[1]}\" → msg:{r[2]} ch:{r[3]} guild:{r[4]}")

        if all_refs:
            lines.append("")
            lines.append("=== REFERENCED ITEMS ===")
            lines.extend(all_refs)
            lines.append("=== END REFERENCES ===")

        return "\n".join(lines)

    async def _summarize_channel_search_batched(
        self,
        messages: List[Dict],
        search_query: str,
        user_feedback: str,
        make_lm_call_func: Any,
        batch_size: int = 10,
        max_tokens: int = 12288
    ) -> str:
        """Summarize channel search results using mini-context batched summarization.
        
        BUG-SEARCH-006 FIX (2026-07-11): 
        - Increased default max_tokens from 4096 to 12288 to prevent finish_reason: length.
        - Added token-aware batching: packs messages into batches based on estimated token count
          rather than fixed batch_size=10.
        - Added output length constraints to prompt (max 400 chars per batch summary).
        """
        total = len(messages)
        summaries = []
        
        # BUG-SEARCH-006 FIX: Token-aware batching
        # Estimate tokens per formatted message (~150 chars / 4 = ~38 tokens)
        # Target ~50% of max_tokens per batch to leave headroom for response
        estimated_tokens_per_message = 40
        target_tokens_per_batch = max_tokens // 2  # 50% of max_tokens
        effective_batch_size = max(5, target_tokens_per_batch // estimated_tokens_per_message)
        
        # Cap batch size to prevent exceeding max_tokens
        effective_batch_size = min(effective_batch_size, 20)
        
        logger.info(f"[channel_search] Using token-aware batching: batch_size={effective_batch_size}, "
                    f"max_tokens={max_tokens}, estimated_tokens_per_batch={target_tokens_per_batch}")

        for start_idx in range(0, total, effective_batch_size):
            end_idx = min(start_idx + effective_batch_size, total)
            batch = messages[start_idx:end_idx]

            batch_text = self._format_messages_for_summarization(batch)

            # BUG-SEARCH-006 FIX: Add output length constraints to prompt
            summarization_prompt = (
                f"These are recent Discord messages from a channel search. "
                f"Search query was: '{search_query}'"
                f"{' User context: ' + user_feedback if user_feedback else ''}."
                f"\n\nYour task: Summarize the key points AND list ALL image URLs found.\n\n"
                f"RULES (MUST FOLLOW):\n"
                f"1. If any message contains image URLs (lines like '![image](https://...)'), you MUST list every image URL in the summary.\n"
                f"2. If any message contains file/attachment links, list them.\n"
                f"3. Mention the authors and key content of messages.\n"
                f"4. Keep the summary concise but DO NOT skip image URLs.\n"
                f"5. MAX 400 CHARACTERS per batch summary.\n"
                f"6. List image URLs compactly — one per line, no extra text.\n"
                f"7. List only UNIQUE image URLs (deduplicate).\n\n"
                f"REQUIRED OUTPUT FORMAT:\n"
                f"- First list all unique image URLs found (if any), one per line\n"
                f"- Then summarize key points/topics in 2-3 sentences max\n\n"
                f"DO NOT return an empty or near-empty summary. You must include at least the image URLs and a brief description.\n\n---\n{batch_text}"
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
                    # BUG-SEARCH-005 FIX: LM returned no choices — fall back to direct formatting
                    logger.warning(f"[channel_search] Batch {len(summaries)}: No choices in LM response, using fallback")
                    fallback_summary = self._format_channel_search_direct(batch, search_query, user_feedback)
                    summaries.append(f"--- Batch {len(summaries)+1} Summary (Fallback) ---\n{fallback_summary}")
            except Exception as e:
                logger.error(f"[channel_search] Mini-context summarization failed for batch {len(summaries)+1}: {e}")
                # BUG-SEARCH-005 FIX: Fall back to direct formatting when LM call fails
                logger.info(f"[channel_search] Using fallback direct formatting for batch {len(summaries)+1}")
                fallback_summary = self._format_channel_search_direct(batch, search_query, user_feedback)
                summaries.append(f"--- Batch {len(summaries)+1} Summary (Fallback) ---\n{fallback_summary}")

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
        """Format channel search results directly without mini-context summarization.
        
        Includes universal reference section at the end mapping all content
        (images, files, text) to their source message IDs for constructing
        Discord jump links.
        """
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

        # Track universal references
        image_refs = []  # [ref_idx, url, msg_id, ch_id, guild_id]
        file_refs = []   # [ref_idx, filename, url, msg_id, ch_id, guild_id]
        text_refs = []   # [ref_idx, content_snippet, msg_id, ch_id, guild_id]

        for i, msg in enumerate(messages, 1):
            author = msg.get("display_name", msg.get("author", "Unknown"))
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            is_reply = msg.get("is_reply", False)
            replied_to = msg.get("replied_to_author")
            channel_name = msg.get("_channel_name", "")
            msg_message_id = msg.get("message_id") or msg.get("id", "")
            msg_channel_id = msg.get("channel_id", "")
            guild_id = msg.get("guild_id", "")

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
                # Use Discord-compatible markdown image format ![alt](URL)
                # This renders as a clickable image preview in Discord
                for url in image_urls:
                    ref_idx = len(image_refs)
                    image_refs.append([ref_idx, url, msg_message_id, msg_channel_id, guild_id])
                    result_lines.append(f"  ![image]({url}) [ref:img:{ref_idx}]")
                urls_str = ", ".join(image_urls)
                result_lines.append(f"  [Image URLs for reference: {urls_str}]")

            # Track file attachments
            attachments = msg.get("attachments", [])
            if attachments:
                for att in attachments:
                    if isinstance(att, str):
                        ref_idx = len(file_refs)
                        file_refs.append([ref_idx, att, att, msg_message_id, msg_channel_id, guild_id])
                        result_lines.append(f"  [📎 Attachment: {att}] [ref:file:{ref_idx}]")
                    elif isinstance(att, dict):
                        filename = att.get("filename", "unknown")
                        url = att.get("url", "")
                        ref_idx = len(file_refs)
                        file_refs.append([ref_idx, filename, url, msg_message_id, msg_channel_id, guild_id])
                        result_lines.append(f"  [📎 Attachment: {filename}] [ref:file:{ref_idx}]")

            # Track text references for search queries
            if content and len(content.strip()) > 10:
                ref_idx = len(text_refs)
                text_refs.append([ref_idx, content[:150], msg_message_id, msg_channel_id, guild_id])

            # Add Discord jump link
            if msg_message_id and msg_channel_id and guild_id:
                jump_link = f"https://discord.com/channels/{guild_id}/{msg_channel_id}/{msg_message_id}"
                result_lines.append(f"  [Message link]({jump_link}) [ref:msg:{msg_message_id}]")

        # Add structured reference section for LM to use
        all_refs = []
        for r in image_refs:
            all_refs.append(f"[img:{r[0]}] {r[1]} → msg:{r[2]} ch:{r[3]} guild:{r[4]}")
        for r in file_refs:
            all_refs.append(f"[file:{r[0]}] {r[1]} → msg:{r[2]} ch:{r[3]} guild:{r[4]}")
        for r in text_refs:
            all_refs.append(f"[text:{r[0]}] \"{r[1]}\" → msg:{r[2]} ch:{r[3]} guild:{r[4]}")

        result_lines.append(f"")
        result_lines.append(f"=== REFERENCED ITEMS ===")
        result_lines.append(f"Use these references to construct Discord message links:")
        result_lines.append(f"Format: https://discord.com/channels/{{guild_id}}/{{channel_id}}/{{message_id}}")
        result_lines.append(f"")
        if all_refs:
            result_lines.extend(all_refs)
        else:
            result_lines.append(f"(No referenced items found)")
        result_lines.append(f"=== END REFERENCES ===")

        if user_feedback:
            result_lines.append(f"USER CONTEXT: {user_feedback}")
        result_lines.append(f"INSTRUCTIONS: Read the messages above. If the search query was '{search_query}', identify which messages contain this term and provide a direct answer to the user's original question. When asked for message links, use the REFERENCED ITEMS section to construct Discord jump links.")

        return "\n".join(result_lines)
