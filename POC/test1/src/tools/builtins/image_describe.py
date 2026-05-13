"""
Image Description Tool

This module implements a tool for describing images using vision capabilities.
It uses LM Studio's vision API (OpenAI-compatible) to analyze and describe images.

Key Responsibilities:
- Accept base64-encoded image data as input
- Resize/compress images for efficient processing
- Return image data in format suitable for VLM vision API
- Handle image validation and error cases

Tool Definition:
- name: "image_describe"
- description: "Describe an image using vision capabilities"
- parameters: { image_data: str, mime_type: str }

Integration with test/lmTest_2.py:
- Returns {"type": "image", "base64_data": ..., "mime_type": ...} format
- This is used by message_handler to build vision messages for LM Studio
"""

import base64
import json

from ..base import BaseTool, ToolResult
from ...utils import resize_image_bytes, image_to_base64


class ImageDescribeTool(BaseTool):
    """Tool for describing images using vision capabilities.
    
    This tool accepts base64-encoded image data, validates and processes it
    (resize/compress), then returns it in a format suitable for VLM vision APIs.
    
    Security measures:
    - Max image size: 5MB
    - Max dimension: 768px (auto-resized)
    - In-memory processing only (no disk writes)
    """

    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_DIMENSION = 768  # pixels
    JPEG_QUALITY = 85

    @property
    def name(self) -> str:
        return "image_describe"

    @property
    def description(self) -> str:
        return (
            "Process an image and return it in a format suitable for vision analysis. "
            "Use this when the user wants an image described. The tool returns base64-encoded "
            "image data that can be sent to a vision model."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "image_data": {
                    "type": "string",
                    "description": "Base64-encoded image data (without data: URL prefix)"
                },
                "mime_type": {
                    "type": "string",
                    "description": "MIME type of the image (e.g., image/png, image/jpeg)"
                }
            },
            "required": ["image_data", "mime_type"]
        }

    def execute(self, image_data: str = "", mime_type: str = "image/jpeg", **kwargs) -> ToolResult:
        """Process the image and return it for vision model analysis.
        
        The image data is decoded, validated, resized/compressed, then re-encoded.
        
        Args:
            image_data: Base64-encoded image data (without data: URL prefix)
            mime_type: Original MIME type of the image
            **kwargs: Additional arguments (ignored)
            
        Returns:
            ToolResult with content as JSON containing:
            - base64_data: processed base64 string
            - mime_type: "image/jpeg" (always converted to JPEG)
        """
        try:
            # Decode base64 data
            if not image_data:
                return ToolResult(
                    success=False,
                    content="",
                    error="No image data provided"
                )
            
            # Remove data: URL prefix if present
            if image_data.startswith("data:"):
                # Extract the base64 part after "data:image/xxx;base64,"
                if "," in image_data:
                    image_data = image_data.split(",", 1)[1]
            
            raw_bytes = base64.b64decode(image_data)
            
            # Validate size
            if len(raw_bytes) > self.MAX_IMAGE_SIZE:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Image too large: {len(raw_bytes) / 1024 / 1024:.1f}MB (max {self.MAX_IMAGE_SIZE / 1024 / 1024:.0f}MB)"
                )
            
            if len(raw_bytes) == 0:
                return ToolResult(
                    success=False,
                    content="",
                    error="Empty image data"
                )
            
            # Resize and compress in memory
            compressed_bytes, output_mime_type = resize_image_bytes(
                raw_bytes,
                max_dimension=self.MAX_DIMENSION,
                quality=self.JPEG_QUALITY
            )
            
            # Re-encode to base64
            processed_base64 = image_to_base64(compressed_bytes)
            
            # Return in the format expected by message_handler for image tools
            result_data = {
                "base64_data": processed_base64,
                "mime_type": output_mime_type
            }
            
            return ToolResult(
                success=True,
                content=json.dumps(result_data)
            )
            
        except Exception as exc:
            return ToolResult(
                success=False,
                content="",
                error=f"Failed to process image: {str(exc)}"
            )