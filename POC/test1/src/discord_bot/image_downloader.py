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

    async def _download_with_session(self, url: str, headers: Optional[dict] = None) -> bytes:
        """Download image using a session with optional custom headers.
        
        For Discord CDN URLs, automatically adds a User-Agent header to mimic
        a browser request. This helps bypass CDN restrictions that block
        requests without proper headers.
        
        Args:
            url: URL to download from
            headers: Optional extra headers to include
            
        Returns:
            Raw image bytes
            
        Raises:
            ValueError: If content type is invalid or size limit exceeded
            aiohttp.ClientResponseError: If HTTP request fails
        """
        timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)
        async with aiohttp.ClientSession() as session:
            # Merge User-Agent header if URL is Discord CDN
            merged_headers = dict(headers or {})
            parsed = urlparse(url)
            if parsed.hostname in ("cdn.discordapp.com", "media.discordapp.net"):
                # Add browser-like User-Agent if not already present
                if "User-Agent" not in merged_headers:
                    merged_headers["User-Agent"] = (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
            async with session.get(url, timeout=timeout, headers=merged_headers or None) as response:
                # Validate content type
                content_type = response.content_type.lower()
                if content_type not in ALLOWED_CONTENT_TYPES:
                    raise ValueError(f"Blocked: disallowed content type '{content_type}' (expected one of {ALLOWED_CONTENT_TYPES})")
                logger.info(f"Content type allowed: {content_type}")

                # Download with size limit
                raw_bytes = b""
                async for chunk in response.content.iter_chunked(1024 * 1024):  # 1MB chunks
                    raw_bytes += chunk
                    if len(raw_bytes) > MAX_IMAGE_SIZE:
                        raise ValueError(f"Blocked: image exceeds size limit ({len(raw_bytes)} bytes > {MAX_IMAGE_SIZE} bytes)")
                    logger.debug(f"Downloaded {len(raw_bytes)} bytes so far...")

        return raw_bytes

    async def download_image(self, url: str) -> bytes:
        """Safely download an image from a URL.
        
        Validates hostname against whitelist, checks content type,
        enforces size limits and timeouts.
        
        For Discord CDN URLs (cdn.discordapp.com, media.discordapp.net), if the
        initial download gets a 404, retries with a Referer header pointing to
        discord.com. This works around Discord's CDN behavior where deleted or
        moved images require a valid Referer to resolve redirects.
        
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
        try:
            raw_bytes = await self._download_with_session(url)
            logger.info(f"Successfully downloaded {len(raw_bytes)} bytes from {hostname}")
            return raw_bytes
        except (aiohttp.ClientResponseError, ValueError) as e:
            error_str = str(e).lower()
            # For Discord CDN hosts, retry with Referer header on 404 or content-type errors
            # (Discord sometimes returns HTML error pages that pass initial checks)
            if hostname in ("cdn.discordapp.com", "media.discordapp.net") and ("404" in error_str or "not found" in error_str):
                logger.info(f"Got 404 for {url}, retrying with Referer header (image may have been deleted/moved)")
                try:
                    referer_headers = {"Referer": "https://discord.com"}
                    raw_bytes = await self._download_with_session(url, headers=referer_headers)
                    logger.info(f"Successfully downloaded {len(raw_bytes)} bytes from {hostname} with Referer header")
                    return raw_bytes
                except Exception as retry_error:
                    logger.warning(f"Retry with Referer also failed for {url}: {retry_error}")
                    raise ValueError(f"Image not found (404) even with Referer retry: {url}") from e
            # Additional retry: if content type is text/html, the CDN may have returned
            # an error page. Retry with Referer header as a fallback.
            if hostname in ("cdn.discordapp.com", "media.discordapp.net") and isinstance(e, ValueError) and "content type" in error_str:
                logger.info(f"Got unexpected content type for {url}, retrying with Referer header")
                try:
                    referer_headers = {"Referer": "https://discord.com"}
                    raw_bytes = await self._download_with_session(url, headers=referer_headers)
                    logger.info(f"Successfully downloaded {len(raw_bytes)} bytes from {hostname} with Referer header")
                    return raw_bytes
                except Exception as retry_error:
                    logger.warning(f"Retry with Referer also failed for {url}: {retry_error}")
                    raise ValueError(f"Image not found (404) even with Referer retry: {url}") from e
            raise


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