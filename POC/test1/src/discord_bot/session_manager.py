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
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages Discord bot sessions with timeout and cleanup.
    
    Each session stores full identity context for memory integration:
    - channel_id -> session data dict with user identity, nickname history, guild info
    """

    def __init__(self, timeout_seconds: int = 600):
        """Initialize session manager.

        Args:
            timeout_seconds: Session timeout in seconds (default: 600 = 10 minutes)
        """
        self._active_sessions: Dict[int, datetime] = {}
        # Legacy: single username (backward compat)
        self._session_users: Dict[int, str] = {}
        # Full session identity data for memory integration
        self._session_data: Dict[int, Dict[str, Any]] = {}
        self._session_timeout = timeout_seconds

    # --- Session Lifecycle ---

    def start_session(
        self,
        channel_id: int,
        user_name: str,
        user_id: str = "",
        author_display: str = "",
        initial_nick: Optional[str] = None,
        guild_id: str = ""
    ) -> None:
        """Start or update a session for a channel.

        Args:
            channel_id: Discord channel ID
            user_name: User who started the session (Discord username, stable)
            user_id: Discord user ID (immutable unique identifier)
            author_display: Discord display name (can be changed by user)
            initial_nick: Per-server nickname at session start (can be None)
            guild_id: Discord guild/server ID (for per-server identity context)
        """
        self._active_sessions[channel_id] = datetime.now()
        self._session_users[channel_id] = user_name
        
        # Store full identity context for memory integration
        self._session_data[channel_id] = {
            "author_name": user_name,
            "user_id": user_id,
            "initial_display": author_display,
            "initial_nick": initial_nick,
            "current_display": author_display,
            "current_nick": initial_nick,
            "guild_id": guild_id,
            "started_at": datetime.now()
        }

    def is_active(self, channel_id: int) -> bool:
        """Check if a session is active for a channel.

        Args:
            channel_id: Discord channel ID

        Returns:
            True if session is active
        """
        return channel_id in self._active_sessions

    def get_user(self, channel_id: int) -> Optional[str]:
        """Get the user who started the session (backward compat).

        Args:
            channel_id: Discord channel ID

        Returns:
            Username or None if no session
        """
        # Check new data store first, fall back to legacy
        if channel_id in self._session_data:
            return self._session_data[channel_id].get("author_name")
        return self._session_users.get(channel_id)

    def get_session(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Get full session data including identity context.

        Args:
            channel_id: Discord channel ID

        Returns:
            Dict with session identity data, or None if no session.
            Keys: author_name, user_id, initial_display, initial_nick,
                  current_display, current_nick, guild_id, started_at
        """
        return self._session_data.get(channel_id)

    def clear(self, channel_id: int) -> None:
        """Clear the session for a specific channel.

        Args:
            channel_id: Discord channel ID
        """
        if channel_id in self._active_sessions:
            del self._active_sessions[channel_id]
        if channel_id in self._session_users:
            del self._session_users[channel_id]
        if channel_id in self._session_data:
            del self._session_data[channel_id]
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
        """Get all session users (backward compat).

        Returns:
            Dict mapping channel_id to username
        """
        return dict(self._session_users)

    def get_all_session_data(self) -> Dict[int, Dict[str, Any]]:
        """Get all session identity data.

        Returns:
            Dict mapping channel_id to session data
        """
        return dict(self._session_data)

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