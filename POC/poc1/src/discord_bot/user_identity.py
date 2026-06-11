"""
User Identity Module

Provides utilities for building Discord user identity context
for LM Studio system prompts and message formatting.
"""

from typing import Optional


class UserIdentity:
    """Utilities for Discord user identity context."""

    @staticmethod
    def build_context(
        author_name: str,
        author_display: str,
        author_nick: Optional[str],
        user_id: str
    ) -> str:
        """Build identity context string for system prompt.

        Args:
            author_name: Discord username
            author_display: Discord display name
            author_nick: Per-server nickname
            user_id: Discord user ID

        Returns:
            Identity context string
        """
        identity_parts = []
        identity_parts.append("\n\nYou are in a Discord server. The person you are talking to has the following Discord identity information:")
        identity_parts.append(f"\n- **Discord username** (stable, global identifier): `{author_name}`")

        if author_nick:
            identity_parts.append(f"\n- **Per-server nickname** (server-specific, can be different per server): `{author_nick}`")
            identity_parts.append("\n  → Use this nickname when addressing this user. Nicknames are server-specific — the same person may have different nicknames in different servers.")
        elif author_display and author_display != author_name:
            identity_parts.append(f"\n- **Display name** (global, can be changed by the user): `{author_display}`")
        else:
            identity_parts.append(f"\n- **Display name** (same as username): `{author_display or author_name}`")

        if user_id:
            identity_parts.append(f"\n- **Discord user ID** (unique, immutable, cannot change): `{user_id}`")

        identity_parts.append("\n**Important guidelines:**")
        identity_parts.append("1. These are Discord identifiers, NOT real-world names.")
        identity_parts.append("2. The user ID is the most stable way to identify this user across time.")
        identity_parts.append("3. The nickname or display name may change — use the current one when addressing them.")
        identity_parts.append("4. If the user shares their real name or personal info, associate it with their Discord username for this session.")
        identity_parts.append("5. The same user may have different nicknames in different servers — treat each server identity as separate.")

        return "\n".join(identity_parts)

    @staticmethod
    def format_new_session(
        content: str,
        author_name: str,
        author_nick: Optional[str],
        author_display: str
    ) -> str:
        """Format user message with identity attribution for new sessions.

        Args:
            content: Message content
            author_name: Discord username
            author_nick: Per-server nickname
            author_display: Discord display name

        Returns:
            Formatted message string
        """
        if author_nick and author_nick != author_name:
            return (
                f"[From user '{author_name}' "
                f"(nickname: '{author_nick}', "
                f"display: '{author_display}')]: {content}"
            )
        elif author_display and author_display != author_name:
            return (
                f"[From user '{author_name}' "
                f"(display: '{author_display}')]: {content}"
            )
        elif author_name:
            return f"[From user '{author_name}']: {content}"
        return content

    @staticmethod
    def format_active_session(
        content: str,
        author_name: str,
        author_display: str,
        author_nick: Optional[str],
        session_user: str,
        initial_nick: Optional[str],
        nick_changed: bool
    ) -> str:
        """Format message with identity attribution for active sessions.

        Args:
            content: Message content
            author_name: Discord username
            author_display: Discord display name
            author_nick: Per-server nickname
            session_user: User who started the session
            initial_nick: Nickname at session start
            nick_changed: Whether nickname has changed

        Returns:
            Formatted message string
        """
        if author_name == session_user:
            if nick_changed and initial_nick:
                nick_now = author_nick if author_nick else "(none)"
                return f"[{author_name} (was: {initial_nick}, now: {nick_now})]: {content}"
            elif author_nick and author_nick != author_name:
                return f"[{author_name} (nickname: {author_nick})]: {content}"
            elif author_display and author_display != author_name:
                return f"[{author_name} (display: {author_display})]: {content}"
            else:
                return content
        else:
            if author_nick and author_nick != author_name:
                return f"{author_nick} ({author_name}) says: {content}"
            elif author_display and author_display != author_name:
                return f"{author_display} ({author_name}) says: {content}"
            else:
                return f"{author_display} says: {content}"