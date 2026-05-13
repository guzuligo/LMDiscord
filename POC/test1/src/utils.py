"""
General Helper Functions Module

This module provides utility functions used across the application.

Key Responsibilities:
- Image processing utilities (resize, format conversion, base64 encoding)
- String manipulation (truncation, formatting)
- File path utilities
- MIME type detection
"""

import base64
import io
from pathlib import Path
from PIL import Image


# MIME type mapping for image file extensions
IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".bmp": "image/bmp",
}


def detect_mime_type(file_path: str) -> str:
    """Detect the MIME type of a file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MIME type string (e.g., "image/png", "image/jpeg")
    """
    ext = Path(file_path).suffix.lower()
    return IMAGE_MIME_TYPES.get(ext, "application/octet-stream")


def resize_image_bytes(image_bytes: bytes, max_dimension: int = 768, quality: int = 85) -> tuple:
    """Resize and compress image bytes in memory.
    
    Loads an image from bytes, converts RGBA to RGB if needed,
    resizes to fit within max_dimension, and compresses as JPEG.
    
    Args:
        image_bytes: Raw image bytes
        max_dimension: Maximum width or height in pixels (default: 768)
        quality: JPEG quality 1-100 (default: 85)
        
    Returns:
        Tuple of (compressed_bytes, mime_type)
    """
    # Load image from bytes
    img = Image.open(io.BytesIO(image_bytes))
    
    # Convert RGBA to RGB if needed (JPEG doesn't support alpha)
    if img.mode == "RGBA":
        # Create white background
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    
    # Resize if image is larger than max_dimension
    orig_width, orig_height = img.size
    if max(orig_width, orig_height) > max_dimension:
        ratio = max_dimension / max(orig_width, orig_height)
        new_width = max(320, int(orig_width * ratio))
        new_height = max(200, int(orig_height * ratio))
        img = img.resize((new_width, new_height), Image.LANCZOS)
    
    # Save as JPEG to compressed bytes
    output_buf = io.BytesIO()
    img.save(output_buf, format="JPEG", quality=quality, optimize=True)
    compressed_bytes = output_buf.getvalue()
    
    return compressed_bytes, "image/jpeg"


def image_to_base64(image_bytes: bytes) -> str:
    """Encode image bytes to base64 string.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        Base64-encoded string
    """
    return base64.b64encode(image_bytes).decode("utf-8")


def resize_image(image_path: str, max_width: int = 768, max_height: int = 768) -> Path:
    """Resize an image file and save to a new location.
    
    Note: This saves to disk, not memory. For in-memory processing,
    use resize_image_bytes() instead.
    
    Args:
        image_path: Path to the source image
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        
    Returns:
        Path to the resized image (saved to temp location)
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    img = Image.open(path)
    
    # Convert RGBA to RGB if needed
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    
    # Resize
    orig_width, orig_height = img.size
    scale_w = min(max_width / orig_width, 1.0)
    scale_h = min(max_height / orig_height, 1.0)
    scale = min(scale_w, scale_h)
    
    if scale < 1.0:
        new_width = max(320, int(orig_width * scale))
        new_height = max(200, int(orig_height * scale))
        img = img.resize((new_width, new_height), Image.LANCZOS)
    
    # Save to temp location
    output_path = path.parent / f"resized_{path.name}"
    img.save(output_path, format="JPEG", quality=85, optimize=True)
    
    return output_path


def truncate_string(s: str, max_length: int = 2000, suffix: str = "...") -> str:
    """Truncate a string to a maximum length.
    
    Args:
        s: The string to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to append when truncated (default: "...")
        
    Returns:
        Truncated string
    """
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def format_timestamp(dt) -> str:
    """Format a datetime object as ISO 8601 string.
    
    Args:
        dt: datetime object
        
    Returns:
        ISO 8601 formatted string
    """
    return dt.isoformat()


def is_valid_port(port: int) -> bool:
    """Check if a port number is valid.
    
    Args:
        port: Port number to validate
        
    Returns:
        True if port is valid (1-65535), False otherwise
    """
    return isinstance(port, int) and 1 <= port <= 65535