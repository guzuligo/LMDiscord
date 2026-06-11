"""
Safe Image Downloader Module

Provides SafeImageDownloader class for securely downloading images
with whitelist-based hostname validation.
"""

import logging
from typing import Optional, List, Tuple

import aiohttp
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)

# Image download configuration
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
DOWNLOAD_TIMEOUT = 30  # seconds
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}


class ExpiredTokenError(Exception):
    """Raised when an image URL's authentication token has expired."""
    pass


DISCORD_CDN_HOSTS = ("cdn.discordapp.com", "media.discordapp.net")

# Query params that Discord adds for CDN expiration/processing — safe to strip
DISCORD_CDN_EXPIRY_PARAMS = {
    "ex", "is", "hm", "format", "quality", "width", "height",
    "t", "token", "age", "nonce",
}


def strip_expired_cdn_params(url: str) -> str:
    """Strip expiration and processing query params from Discord CDN URLs.
    
    Discord attachment URLs contain time-limited tokens like:
    https://media.discordapp.net/attachments/.../image.png?ex=6a167da7&is=6a152c27&hm=...
    
    This function removes the expiration-related query params so the base CDN URL
    is used instead. The base URL sometimes works for publicly accessible resources.
    
    Args:
        url: The URL to sanitize
        
    Returns:
        Sanitized URL with expiration params removed
    """
    parsed = urlparse(url)
    if parsed.hostname not in DISCORD_CDN_HOSTS:
        return url
    
    # Filter out expiration-related query params
    if parsed.query:
        from urllib.parse import parse_qs, urlencode
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        filtered_params = {
            k: v for k, v in query_params.items()
            if k not in DISCORD_CDN_EXPIRY_PARAMS
        }
        if filtered_params:
            new_query = urlencode(filtered_params, doseq=True)
        else:
            new_query = ""
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    
    return url


class SafeImageDownloader:
    """Safely downloads images with whitelist-based hostname validation.
    
    Handles expired CDN token scenarios by:
    1. Stripping query parameters (expiration tokens) from Discord CDN URLs before download
    2. Retrying with Referer headers on 403/401/content-type errors
    3. Raising ExpiredTokenError for user-friendly handling upstream
    """

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
        
        For Discord CDN URLs, strips expiration query parameters (ex=, is=, hm=)
        before download to work around stale token issues from old message embeds.
        If the stripped URL fails, falls back to the original URL.
        
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

        # Step 1.5: For Discord CDN URLs, try stripping expiration params first
        original_url = url
        if hostname in DISCORD_CDN_HOSTS and parsed.query:
            # Check if URL has expiration-related params
            has_expiry_params = any(p in parsed.query for p in ["ex=", "is=", "hm=", "&ex=", "&is=", "&hm="])
            if has_expiry_params:
                sanitized_url = strip_expired_cdn_params(url)
                logger.info(f"Discord CDN URL has expired params, trying sanitized URL: {sanitized_url[:80]}...")
                url = sanitized_url

        # Step 2: Download with timeout and size limit
        try:
            raw_bytes = await self._download_with_session(url)
            logger.info(f"Successfully downloaded {len(raw_bytes)} bytes from {hostname}")
            return raw_bytes
        except (aiohttp.ClientResponseError, ValueError) as e:
            error_str = str(e).lower()

            # If we already tried the sanitized URL, fall back to the original URL with expiry params
            if url != original_url and hostname in DISCORD_CDN_HOSTS:
                logger.info(f"Sanitized URL failed, falling back to original URL with expiry params: {original_url[:80]}...")
                url = original_url
                try:
                    raw_bytes = await self._download_with_session(url)
                    logger.info(f"Successfully downloaded {len(raw_bytes)} bytes from {hostname} using original URL")
                    return raw_bytes
                except Exception as fallback_error:
                    logger.warning(f"Original URL also failed: {fallback_error}")
                    # Continue to error handling below

            # Handle 403 Forbidden — expired authentication token
            # This is the primary symptom of stale CDN URLs from old message embeds.
            # Strip query params and retry once, as the base URL may still be accessible.
            if hostname in ("cdn.discordapp.com", "media.discordapp.net") and ("403" in error_str or "forbidden" in error_str):
                logger.warning(f"Got 403 Forbidden for {url} — token likely expired")
                # Try with Referer header first
                try:
                    referer_headers = {"Referer": "https://discord.com", "Origin": "https://discord.com"}
                    raw_bytes = await self._download_with_session(url, headers=referer_headers)
                    logger.info(f"Successfully downloaded {len(raw_bytes)} bytes from {hostname} with Referer+Origin headers after 403")
                    return raw_bytes
                except Exception as retry_error:
                    logger.warning(f"Retry with Referer+Origin also failed for {url}: {retry_error}")
                    # Raise ExpiredTokenError for user-friendly handling upstream
                    raise ExpiredTokenError(
                        f"Image URL has expired (403 Forbidden). Discord attachment URLs are time-limited. "
                        f"Please re-share the image: {url}"
                    ) from e
            
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