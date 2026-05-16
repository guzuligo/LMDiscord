"""
Safe Image Downloader Module

Provides SafeImageDownloader class for securely downloading images
with whitelist-based hostname validation.
"""

import logging
from typing import Optional, List, Tuple

import aiohttp
from urllib.parse import urlparse

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

    def is_hostname_allowed(self, url: str) -> Tuple[bool, str]:
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