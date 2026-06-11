"""
Image Compare / Describe Tool

This module implements a tool for comparing up to 3 images using vision capabilities,
or describing a single image. It downloads all images, sends them together in a single
multi-image mini-context call, and returns the direct comparison or description result.

Tool Definition:
- name: "image_compare"
- description: "Compare up to 3 images side by side, or describe a single image"
- parameters: { image_urls: list, comparison_prompt: str (optional) }

Integration:
- Used by message_handler to build comparison/description messages for LM Studio
- Downloads images safely, sends all in one multi-image mini-context call
- Single image: acts as image description tool
- Multiple images (2-3): acts as image comparison tool
"""

import json
import logging
from typing import Dict, List, Optional, Any

from ..base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Discord CDN often returns redirect pages; adding Referer header helps
DISCORD_CDN_REFERER = "https://discord.com/"


class ImageCompareTool(BaseTool):
    """Tool for comparing up to 3 images using vision capabilities.
    
    This tool accepts multiple image URLs, downloads them, and sends all images
    together in a single multi-image mini-context call for direct comparison.
    
    Security measures:
    - Max images: 3
    - Max image size: 5MB each
    - Max dimension: 768px (auto-resized)
    - In-memory processing only (no disk writes)
    """

    MAX_IMAGES = 3
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_DIMENSION = 768  # pixels
    JPEG_QUALITY = 85

    @property
    def name(self) -> str:
        return "image_compare"

    @property
    def description(self) -> str:
        return (
            "Analyze images - describe a single image or compare up to 3 images side by side. "
            "Use this when the user wants to describe an image, compare multiple images, "
            "identify differences/similarities, or get a combined analysis. "
            "Pass image URLs as a list (1-3). For a single image, it will be described in detail. "
            "For multiple images, they will be compared. Optionally provide a comparison_prompt for "
            "specific comparison focus."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "image_urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 3,
                    "description": "List of 1-3 image URLs to analyze (e.g., Discord CDN links). Single image = description, 2-3 images = comparison."
                },
                "comparison_prompt": {
                    "type": "string",
                    "description": "Optional specific comparison focus (e.g., 'Compare the lighting and composition', 'What are the differences between these?'). Ignored for single image."
                }
            },
            "required": ["image_urls"]
        }

    def execute(self, image_urls: List[str], comparison_prompt: str = "", **kwargs) -> ToolResult:
        """Execute the image compare/describe tool.
        
        Note: This tool's actual execution happens asynchronously in the
        tool_executor via mini-context, as it requires async image downloads.
        This execute method is a placeholder for tool registration.
        
        Args:
            image_urls: List of 1-3 image URLs to analyze
            comparison_prompt: Optional comparison focus
            **kwargs: Additional arguments (ignored)
            
        Returns:
            ToolResult indicating async processing is needed
        """
        # This tool requires async processing (image downloads)
        # The actual execution is handled by ToolCallHandler in tool_executor.py
        return ToolResult(
            status="success",
            message=json.dumps({
                "status": "async_required",
                "message": "Image analysis requires async processing via tool_executor"
            }),
            data=json.dumps({
                "status": "async_required",
                "message": "Image analysis requires async processing via tool_executor"
            }),
            success=True,
            content=json.dumps({
                "status": "async_required",
                "message": "Image analysis requires async processing via tool_executor"
            })
        )

    @staticmethod
    async def _download_image_with_retry(
        url: str,
        safe_downloader: Any
    ) -> Optional[bytes]:
        """Download an image, retrying with Referer header on Discord CDN failures.
        
        Args:
            url: Image URL to download
            safe_downloader: SafeImageDownloader instance
            
        Returns:
            Raw image bytes, or None if download failed
        """
        import aiohttp
        from urllib.parse import urlparse
        
        try:
            # First attempt: use safe_downloader (hostname whitelist check)
            raw_bytes = await safe_downloader.download_image(url)
            return raw_bytes
        except ValueError as e:
            error_msg = str(e)
            # Check if it's a content-type error (likely Discord CDN redirect)
            if "disallowed content type" in error_msg:
                logger.info(f"[image_compare] Content-type error, retrying with Referer header: {url[:80]}...")
                try:
                    parsed = urlparse(url)
                    hostname = parsed.hostname or ""
                    
                    # Manual download with Referer header
                    import aiohttp
                    timeout = aiohttp.ClientTimeout(total=30)
                    headers = {"Referer": DISCORD_CDN_REFERER, "User-Agent": "DiscordBot/1.0"}
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=timeout, headers=headers) as response:
                            content_type = response.content_type.lower()
                            if content_type not in {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}:
                                logger.warning(f"[image_compare] Retry also got non-image content type: {content_type}")
                                return None
                            raw_bytes = await response.read()
                            logger.info(f"[image_compare] Retry succeeded: downloaded {len(raw_bytes)} bytes")
                            return raw_bytes
                except Exception as retry_err:
                    logger.warning(f"[image_compare] Retry also failed: {retry_err}")
            else:
                # Re-raise non-content-type errors
                raise
        return None

    @staticmethod
    async def compare_images_async(
        image_urls: List[str],
        comparison_prompt: str,
        safe_downloader: Any,
        make_lm_call_func: Optional[Any] = None,
        image_instruction: Optional[str] = None,
        mini_context_max_tokens: int = 4096
    ) -> str:
        """Async image comparison using a single multi-image mini-context call.
        
        Downloads all images and sends them together in one mini-context message
        so the model can see all images simultaneously for direct comparison.
        
        Args:
            image_urls: List of 2-3 image URLs
            comparison_prompt: Optional comparison focus
            safe_downloader: SafeImageDownloader instance
            make_lm_call_func: Optional function to make LM calls
            image_instruction: Deprecated - kept for backward compatibility
            mini_context_max_tokens: Max tokens for the mini-context call.
                Increased (default 4096) to accommodate multiple image base64 payloads.
            
        Returns:
            Comparison text from LM Studio
        """
        from src.utils import resize_image_bytes, image_to_base64

        if len(image_urls) > ImageCompareTool.MAX_IMAGES:
            return f"Maximum {ImageCompareTool.MAX_IMAGES} images allowed for analysis."

        is_single_image = len(image_urls) == 1

        # Step 1: Download all images and build base64 payloads
        image_payloads = []  # List of (base64_data, mime_type)
        failed_images = []
        
        for i, url in enumerate(image_urls, 1):
            try:
                logger.info(f"[image_compare] Downloading image {i}/{len(image_urls)}: {url[:80]}...")
                
                raw_bytes = await ImageCompareTool._download_image_with_retry(url, safe_downloader)
                if raw_bytes is None:
                    failed_images.append(i)
                    continue
                    
                logger.info(f"[image_compare] Downloaded {len(raw_bytes)} bytes for image {i}")

                # Resize/compress to reduce token usage
                compressed_bytes, output_mime = resize_image_bytes(
                    raw_bytes, max_dimension=ImageCompareTool.MAX_DIMENSION,
                    quality=ImageCompareTool.JPEG_QUALITY
                )
                processed_base64 = image_to_base64(compressed_bytes)
                image_payloads.append((processed_base64, output_mime))

            except Exception as e:
                logger.error(f"[image_compare] Error processing image {i}: {e}", exc_info=True)
                failed_images.append(i)

        # Build failure note
        failure_note = ""
        if failed_images:
            effective_count = len(image_urls) - len(failed_images)
            if effective_count < 1:
                return f"⚠️ Failed to download images. At least 1 image is required for analysis. Failed images: {', '.join(map(str, failed_images))}."
            if is_single_image:
                failure_note = f"\n\n⚠️ Note: Image {', '.join(map(str, failed_images))} could not be processed (download error). Description is based on the available image only."
            else:
                failure_note = f"\n\n⚠️ Note: Images {', '.join(map(str, failed_images))} could not be processed (download error). Comparison is based on the available images only."
            effective_count = len(image_payloads)
        else:
            effective_count = len(image_payloads)

        # Step 2: Build single multi-image mini-context
        # All images are sent together so the model can see them simultaneously
        content_parts = []
        
        # Build the instruction text based on single vs multi image mode
        if is_single_image:
            # Single image mode: description
            if image_instruction:
                description_instruction = f"The user asked: {image_instruction}. Please describe this image in detail, focusing on visual elements relevant to this question."
            else:
                description_instruction = "Please describe this image in detail, up to 3-4 sentences. Focus on key visual elements, colors, objects, and composition."
            content_parts.append({
                "type": "text",
                "text": description_instruction
            })
        else:
            # Multi-image mode: comparison
            # Priority: 1) comparison_prompt from LM Studio, 2) image_instruction (user's question), 3) generic fallback
            if comparison_prompt:
                comparison_instruction = f"Comparison focus: {comparison_prompt}"
            elif image_instruction:
                # UX-002 Fix: Use the user's actual question to focus the comparison
                comparison_instruction = f"The user asked: {image_instruction}. Compare these images and focus on visual elements relevant to this question."
            else:
                comparison_instruction = "Compare these images side by side. Note similarities, differences, and notable features. Be specific and detailed."
            content_parts.append({
                "type": "text",
                "text": f"Compare these {effective_count} images. {comparison_instruction}"
            })
        
        # Add all images to the content
        for i, (base64_data, mime_type) in enumerate(image_payloads, 1):
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{base64_data}"}
            })
        
        mini_context = [{"role": "user", "content": content_parts}]
        
        logger.info(f"[image_compare] Sending {effective_count} image(s) in single mini-context call ({'description' if is_single_image else 'comparison'})")

        # Step 3: Get response from LM Studio (single call)
        if make_lm_call_func:
            logger.info(f"[image_compare] Calling LM Studio with multi-image mini-context (max_tokens={mini_context_max_tokens})")
            comparison_response = await make_lm_call_func(
                mini_context, channel_id=None, use_tool_calling=False, max_tokens=mini_context_max_tokens
            )
            choices = comparison_response.get("choices", [])
            if choices:
                comparison_text = choices[0].get("message", {}).get("content", "Could not generate response.")
            else:
                comparison_text = "Could not generate response (no response from LM Studio)."
        else:
            comparison_text = "Could not generate response (no LM call function available)."

        logger.info(f"[image_compare] {'Description' if is_single_image else 'Comparison'} complete")
        if failure_note:
            return comparison_text + failure_note
        return comparison_text
