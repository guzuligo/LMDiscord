"""
Session Manager Module

Manages Discord bot session lifecycle including:
- Active session tracking
- Session timeout cleanup
- Session state queries
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages Discord bot sessions with timeout and cleanup."""

    def __init__(self, timeout_seconds: int = 600):
        """Initialize session manager.

        Args:
            timeout_seconds: Session timeout in seconds (default: 600 = 10 minutes)
        """
        self._active_sessions: Dict[int, datetime] = {}
        self._session_users: Dict[int, str] = {}
        self._session_timeout = timeout_seconds

    # --- Session Lifecycle ---

    def start_session(self, channel_id: int, user_name: str) -> None:
        """Start or update a session for a channel.

        Args:
            channel_id: Discord channel ID
            user_name: User who started the session
        """
        self._active_sessions[channel_id] = datetime.now()
        self._session_users[channel_id] = user_name

    def is_active(self, channel_id: int) -> bool:
        """Check if a session is active for a channel.

        Args:
            channel_id: Discord channel ID

        Returns:
            True if session is active
        """
        return channel_id in self._active_sessions

    def get_user(self, channel_id: int) -> Optional[str]:
        """Get the user who started the session.

        Args:
            channel_id: Discord channel ID

        Returns:
            Username or None if no session
        """
        return self._session_users.get(channel_id)

    def clear(self, channel_id: int) -> None:
        """Clear the session for a specific channel.

        Args:
            channel_id: Discord channel ID
        """
        if channel_id in self._active_sessions:
            del self._active_sessions[channel_id]
        if channel_id in self._session_users:
            del self._session_users[channel_id]
        logger.info(f"Cleared session for channel {channel_id}")

    def update_activity(self, channel_id: int) -> None:
        """Update the last activity timestamp for a channel.

        Args:
            channel_id: Discord channel ID
        """
        if channel_id in self._active_sessions:
            self._active_sessions[channel_id] = datetime.now()

    def get_active_count(self) -> int:
        """Get the number of active sessions.

        Returns:
            Number of active sessions
        """
        return len(self._active_sessions)

    def get_active_channels(self) -> list:
        """Get list of channel IDs with active sessions.

        Returns:
            List of channel IDs
        """
        return list(self._active_sessions.keys())

    def get_all_users(self) -> Dict[int, str]:
        """Get all session users.

        Returns:
            Dict mapping channel_id to username
        """
        return dict(self._session_users)

    # --- Cleanup ---

    async def cleanup_expired(self, check_interval: int = 60) -> None:
        """Periodically clean up expired sessions.

        Args:
            check_interval: Check interval in seconds (default: 60)
        """
        while True:
            await asyncio.sleep(check_interval)
            now = datetime.now()
            expired_channels = []

            for channel_id, last_activity in self._active_sessions.items():
                if (now - last_activity).total_seconds() > self._session_timeout:
                    expired_channels.append(channel_id)

            for channel_id in expired_channels:
                self.clear(channel_id)
                logger.info(f"Session expired for channel {channel_id}")