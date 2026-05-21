"""
Built-in Tools package for Discord Bot + LM Studio Integration application.

This package contains all built-in tool implementations:
- math_calc.py: Mathematical calculations tool
- image_describe.py: Image description/vision tool
- image_compare.py: Image comparison tool (up to 3 images)
- channel_search.py: Channel message search tool
- memory_tool.py: Memory save/search tool
- comfyui_generate.py: ComfyUI image generation tool
"""

from .image_describe import ImageDescribeTool
from .image_compare import ImageCompareTool
from .channel_search import ChannelSearchTool

__all__ = [
    "ImageDescribeTool",
    "ImageCompareTool",
    "ChannelSearchTool",
]
