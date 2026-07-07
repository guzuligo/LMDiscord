"""
Token Tracker Module

Tracks token usage data for Discord channels and provides
methods to retrieve usage statistics for web UI sync.
"""

import threading
from typing import Dict, Any, Optional
from datetime import datetime


class TokenTracker:
    """Tracks token usage per Discord channel for web UI sync."""

    def __init__(self):
        """Initialize token tracker."""
        self._channel_token_usage: Dict[int, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def store_token_usage(self, channel_id: int, usage: Dict[str, Any]) -> None:
        """Store token usage data for a Discord channel.

        Args:
            channel_id: Discord channel ID
            usage: Usage dict with prompt_tokens, completion_tokens, total_tokens, etc.
        """
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        total_time = usage.get("total_time", 0)
        tokens_per_second = usage.get("tokens_per_second", 0)

        # Calculate tokens_per_second if not provided
        if tokens_per_second == 0 and total_time > 0:
            tokens_per_second = round(completion_tokens / total_time, 1)

        with self._lock:
            self._channel_token_usage[channel_id] = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "tokens_per_second": tokens_per_second,
                "total_time": round(total_time, 2),
                "timestamp": datetime.now().isoformat()
            }

        logger = __import__('logging').getLogger(__name__)
        logger.info(
            f"Token usage stored for channel {channel_id}: "
            f"{total_tokens} tokens ({prompt_tokens}p + {completion_tokens}c) "
            f"@ {tokens_per_second} tok/s"
        )

    def get_channel_token_usage(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Get token usage data for a Discord channel.

        Args:
            channel_id: Discord channel ID

        Returns:
            Usage dict or None if no data
        """
        with self._lock:
            return self._channel_token_usage.get(channel_id)

    def get_last_discord_token_usage(self) -> Optional[Dict[str, Any]]:
        """Get the most recent Discord token usage across all channels.

        Returns:
            Usage dict with channel_id and usage data, or None
        """
        with self._lock:
            if not self._channel_token_usage:
                return None

            # Find the channel with the most recent timestamp
            latest_channel = None
            latest_time = ""
            for ch_id, usage in self._channel_token_usage.items():
                ts = usage.get("timestamp", "")
                if ts > latest_time:
                    latest_time = ts
                    latest_channel = ch_id

            if latest_channel:
                usage = self._channel_token_usage[latest_channel]
                return {
                    "channel_id": latest_channel,
                    **usage
                }
            return None

    def clear_channel_usage(self, channel_id: int) -> None:
        """Clear token usage data for a specific channel.

        Args:
            channel_id: Discord channel ID
        """
        with self._lock:
            self._channel_token_usage.pop(channel_id, None)

    def clear_all_usage(self) -> None:
        """Clear all token usage data."""
        with self._lock:
            self._channel_token_usage.clear()