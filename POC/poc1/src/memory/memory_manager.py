"""
Memory Manager Module

High-level memory management for the Discord bot session lifecycle.
Coordinates all memory operations including session memory creation,
keyword extraction, memory type assignment, and relevant memory retrieval.

Key Responsibilities:
- Create memory after session timeout ends
- Extract keywords from conversation summary
- Assign appropriate memory types based on conversation content
- Link to related previous memories
- Retrieve relevant memories for session context
- Integrate with MemoryLite for storage operations
- Thread-safe memory operations

Usage:
    manager = MemoryManager(db_path="data/memory.db")
    # Create memory from session
    memory = manager.create_session_memory(session, conversation)
    # Retrieve relevant memories
    memories = manager.get_relevant_memories("Discord bot project Python")
    manager.close()
"""

import json
import re
import string
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

from .memorylite import MemoryLite


# Simple English stop words for keyword extraction
STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "he", "her", "his", "i", "in", "is", "it", "its", "me",
    "my", "not", "of", "on", "our", "out", "she", "that", "the",
    "their", "them", "then", "there", "they", "this", "to", "us",
    "was", "we", "what", "when", "where", "which", "while", "who",
    "whom", "why", "will", "with", "would", "you", "your", "about",
    "after", "all", "also", "been", "but", "can", "did", "do",
    "each", "get", "got", "how", "just", "let", "may", "might",
    "must", "need", "never", "no", "none", "not", "only", "other",
    "own", "same", "so", "some", "than", "that", "theirs", "them",
    "themselves", "those", "through", "too", "under", "until", "very",
    "was", "we", "were", "will", "won", "within", "you", "your",
    "can", "could", "should", "would", "might", "must", "shall",
    "into", "upon", "per", "via",
})


class MemoryManager:
    """High-level memory management API.

    Provides session memory creation, keyword extraction, memory type
    assignment, relevant memory retrieval, and related memory linking.

    Args:
        db_path: Path to SQLite database file. Use ':memory:' for in-memory.
        max_expected_updates: Normalization factor for importance scoring.
        max_days: Factor for recency score calculation.
        keyword_count: Default number of keywords to extract.
        recall_limit: Default number of memories to recall.
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        max_expected_updates: int = 10,
        max_days: float = 90.0,
        keyword_count: int = 5,
        recall_limit: int = 10,
    ):
        self._memory = MemoryLite(
            db_path=db_path,
            max_expected_updates=max_expected_updates,
            max_days=max_days,
        )
        self._keyword_count = keyword_count
        self._recall_limit = recall_limit

    @property
    def storage(self) -> MemoryLite:
        """Access the underlying MemoryLite storage directly."""
        return self._memory

    # ================================================================
    # SESSION MEMORY CREATION
    # ================================================================

    def create_session_memory(
        self,
        session_id: str,
        conversation: str,
        user_id: str,
        guild_id: str = "",
        channel_id: str = "",
        topic: str = "",
        memory_type: str = "context",
        expires_in_days: Optional[int] = None,
        explicit_weight: float = 0.5,
    ) -> Dict[str, Any]:
        """Create a memory entry from a completed session conversation.

        Extracts keywords, assigns memory type, and stores in the database.

        Args:
            session_id: The session that generated this memory.
            conversation: Full conversation text to analyze.
            user_id: Primary user involved.
            guild_id: Discord server ID.
            channel_id: Discord channel ID.
            topic: Conversation topic.
            memory_type: Override memory type (default: 'context').
            expires_in_days: Days until expiration (None = no expiration).
            explicit_weight: Importance weight (0.0-1.0).

        Returns:
            Dict with 'memory_id' and 'keywords' extracted.
        """
        # Extract keywords from conversation
        keywords = self.extract_keywords(conversation, count=self._keyword_count)

        # Determine memory type if not explicitly set
        if memory_type == "context":
            memory_type = self.assign_memory_type(conversation)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat()

        # Create the memory
        memory = self._memory.create_memory(
            content=conversation,
            memory_type=memory_type,
            user_ids=[user_id],
            session_id=session_id,
            expires_at=expires_at,
            metadata={
                "topic": topic,
                "guild_id": guild_id,
                "channel_id": channel_id,
                "keywords": keywords,
            },
            explicit_weight=explicit_weight,
        )

        return {
            "memory_id": memory["memory_id"],
            "keywords": keywords,
            "type": memory["type"],
            "importance": memory["importance"],
        }

    def create_summary_memory(
        self,
        session_id: str,
        summaries: List[str],
        user_id: str,
        guild_id: str = "",
        channel_id: str = "",
        topic: str = "",
        expires_in_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a consolidated memory from multiple conversation summaries.

        Useful for merging multiple short sessions into a single memory.

        Args:
            session_id: Primary session ID to link.
            summaries: List of conversation summaries to merge.
            user_id: Primary user.
            guild_id: Discord server ID.
            channel_id: Discord channel ID.
            topic: Overall topic.
            expires_in_days: Days until expiration.

        Returns:
            Dict with memory details.
        """
        combined = "\n\n".join(summaries)
        return self.create_session_memory(
            session_id=session_id,
            conversation=combined,
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            topic=topic,
            expires_in_days=expires_in_days,
            explicit_weight=0.6,  # Slightly higher for consolidated memories
        )

    # ================================================================
    # KEYWORD EXTRACTION
    # ================================================================

    def extract_keywords(self, text: str, count: int = 5) -> List[str]:
        """Extract meaningful keywords from text.

        Removes stop words, punctuation, and short words. Returns the
        most significant remaining terms.

        Args:
            text: Input text to extract keywords from.
            count: Maximum number of keywords to return.

        Returns:
            List of keyword strings, ordered by significance.
        """
        if not text or not text.strip():
            return []

        # Lowercase and split
        words = text.lower().split()

        # Remove punctuation and short words
        cleaned = []
        for word in words:
            word = word.strip(string.punctuation + string.whitespace)
            if len(word) >= 3 and word not in STOP_WORDS:
                cleaned.append(word)

        # Count frequency
        freq: Dict[str, int] = {}
        for word in cleaned:
            freq[word] = freq.get(word, 0) + 1

        if not freq:
            return []

        # Sort by frequency (descending), then alphabetically for ties
        sorted_keywords = sorted(freq.keys(), key=lambda w: (-freq[w], w))

        return sorted_keywords[:count]

    def extract_keywords_from_conversation(self, messages: List[Dict[str, str]], count: int = 10) -> List[str]:
        """Extract keywords from a list of conversation messages.

        Args:
            messages: List of dicts with 'author', 'content', 'timestamp' keys.
            count: Maximum keywords to return.

        Returns:
            List of keyword strings.
        """
        # Combine all message content
        combined = " ".join(msg.get("content", "") for msg in messages if msg.get("content"))
        return self.extract_keywords(combined, count=count)

    # ================================================================
    # MEMORY TYPE ASSIGNMENT
    # ================================================================

    def assign_memory_type(self, text: str) -> str:
        """Assign an appropriate memory type based on text content analysis.

        Analyzes the text for patterns indicating the type of information:
        - 'preference': Contains preference indicators (prefer, like, dislike, etc.)
        - 'fact': Contains factual statements (is, are, was, etc.)
        - 'context': Temporary or situational information
        - 'relationship': Connections between entities
        - 'deprecated': Information marked as outdated

        Args:
            text: Text to analyze.

        Returns:
            One of: 'fact', 'preference', 'context', 'relationship', 'deprecated'.
        """
        text_lower = text.lower()

        # Check for deprecated markers
        deprecated_markers = ["no longer", "used to", "formerly", "previously", "was",
                              "old", "outdated", "deprecated", "changed", "updated", "moved"]
        if any(marker in text_lower for marker in deprecated_markers):
            # Only if it's clearly about something that changed
            change_markers = ["changed", "updated", "moved", "no longer", "used to", "formerly"]
            if any(marker in text_lower for marker in change_markers):
                return "deprecated"

        # Check for preference indicators
        preference_markers = [
            "prefer", "likes", "dislikes", "love", "hate", "enjoy", "avoid",
            "favorite", "favourite", "best", "worst", "always use", "never use",
            "i like", "i prefer", "i enjoy", "i avoid", "rather", "would rather",
            "chooses", "chosen", "setting", "configuration", "config", "theme",
            "dark mode", "light mode", "language", "locale",
        ]
        if any(marker in text_lower for marker in preference_markers):
            return "preference"

        # Check for relationship indicators
        relationship_markers = [
            "collaborator", "colleague", "works with", "team", "partner",
            "friend", "associated", "connected to", "related to", "works for",
            "reports to", "manages", "managed by", "together", "both",
            "and", "between", "among",
        ]
        if any(marker in text_lower for marker in relationship_markers):
            return "relationship"

        # Check for context indicators (temporary/situational)
        context_markers = [
            "currently", "temporary", "right now", "at the moment",
            "working on", "in progress", "ongoing", "project",
            "session", "meeting", "interview", "testing",
        ]
        if any(marker in text_lower for marker in context_markers):
            return "context"

        # Default to fact for definitive statements
        return "fact"

    # ================================================================
    # RELEVANT MEMORY RETRIEVAL
    # ================================================================

    def get_relevant_memories(
        self,
        query: str,
        user_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: Optional[int] = None,
        min_importance: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Retrieve memories relevant to a query.

        Uses keyword extraction from the query to search memories.
        Results are ranked by importance and filtered by optional criteria.

        Args:
            query: Search query text.
            user_id: Filter by user (optional).
            memory_type: Filter by memory type (optional).
            limit: Maximum results (default: self._recall_limit).
            min_importance: Minimum importance score (0.0-1.0).

        Returns:
            List of memory dicts, ranked by relevance.
        """
        if limit is None:
            limit = self._recall_limit

        # Extract keywords from query
        keywords = self.extract_keywords(query, count=max(self._keyword_count, 3))

        if not keywords:
            return []

        # Search by keywords
        memories = self._memory.search_by_keywords(
            keywords=keywords,
            limit=limit * 2,  # Get extra for filtering
            memory_type=memory_type,
        )

        # Filter by min_importance
        if min_importance > 0:
            memories = [m for m in memories if m["importance"] >= min_importance]

        # If user_id specified, verify user association
        if user_id:
            filtered = []
            for m in memories:
                users = self._memory.get_users_for_memory(m["memory_id"])
                if any(u["user_id"] == user_id for u in users):
                    m["associated_users"] = users
                    filtered.append(m)
                else:
                    m["associated_users"] = users
            memories = filtered

        # Limit results
        return memories[:limit]

    def get_recent_memories(
        self,
        limit: int = 10,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get recently updated memories.

        Args:
            limit: Maximum results.
            user_id: Filter by user (optional).

        Returns:
            List of recent memory dicts.
        """
        memories = self._memory.search_recent(limit=limit * 2)

        if user_id:
            filtered = []
            for m in memories:
                users = self._memory.get_users_for_memory(m["memory_id"])
                if any(u["user_id"] == user_id for u in users):
                    m["associated_users"] = users
                    filtered.append(m)
                else:
                    m["associated_users"] = users
            memories = filtered

        return memories[:limit]

    def get_high_importance_memories(
        self,
        min_importance: float = 0.5,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get high-importance memories.

        Args:
            min_importance: Minimum importance score.
            limit: Maximum results.

        Returns:
            List of high-importance memory dicts.
        """
        return self._memory.search_by_importance(
            min_importance=min_importance,
            limit=limit,
        )

    def get_memories_by_type(
        self,
        memory_type: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get memories of a specific type.

        Args:
            memory_type: One of fact, preference, context, relationship, deprecated.
            limit: Maximum results.

        Returns:
            List of memory dicts.
        """
        return self._memory.search_by_type(
            memory_type=memory_type,
            limit=limit,
        )

    # ================================================================
    # RELATED MEMORY LINKING

    def find_related_memories(
        self,
        memory_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find memories related to a given memory by keyword overlap.

        Args:
            memory_id: Reference memory ID.
            limit: Maximum results.

        Returns:
            List of related memory dicts.
        """
        memory = self._memory.get_memory(memory_id)
        if not memory:
            return []

        # Extract keywords from the memory content
        keywords = self.extract_keywords(memory["content"], count=5)
        if not keywords:
            return []

        # Search for memories with overlapping keywords
        candidates = self._memory.search_by_keywords(keywords, limit=limit * 3)

        # Exclude the reference memory itself
        candidates = [m for m in candidates if m["memory_id"] != memory_id]

        # Score by keyword overlap
        candidate_keywords = {}
        for m in candidates:
            kw = self.extract_keywords(m["content"], count=10)
            overlap = len(set(keywords) & set(kw))
            candidate_keywords[m["memory_id"]] = {
                "memory": m,
                "overlap_score": overlap,
                "importance_score": m["importance"],
            }

        # Sort by combined score
        scored = sorted(
            candidate_keywords.items(),
            key=lambda x: (x[1]["overlap_score"] * 0.6 + x[1]["importance_score"] * 0.4),
            reverse=True,
        )

        return [item[1]["memory"] for item in scored[:limit]]

    def link_related_memories(self, memory_id: str, related_ids: List[str]) -> bool:
        """Store related memory IDs in metadata.

        Args:
            memory_id: Memory to link.
            related_ids: List of related memory IDs.

        Returns:
            True if updated successfully.
        """
        memory = self._memory.get_memory(memory_id)
        if not memory:
            return False

        metadata = memory.get("metadata") or {}
        metadata["related_memory_ids"] = related_ids

        self._memory.update_memory(memory_id, metadata=json.dumps(metadata))
        return True

    # ================================================================
    # USER MANAGEMENT
    # ================================================================

    def ensure_user(self, user_id: str, username: str = "") -> Dict[str, Any]:
        """Ensure a user exists in the memory system.

        Args:
            user_id: Discord user ID.
            username: Display username.

        Returns:
            User dict.
        """
        return self._memory.upsert_user(user_id, username)

    def get_user_memories(
        self,
        user_id: str,
        limit: int = 100,
        memory_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get all memories associated with a user.

        Args:
            user_id: Discord user ID.
            limit: Maximum results.
            memory_type: Optional type filter.

        Returns:
            List of memory dicts.
        """
        memories = self._memory.list_memories(
            user_id=user_id,
            memory_type=memory_type,
            limit=limit,
            order_by="importance",
            order_dir="DESC",
        )

        # Add user info to each memory
        for m in memories:
            m["associated_users"] = self._memory.get_users_for_memory(m["memory_id"])

        return memories

    def get_user_count(self, user_id: str) -> int:
        """Get total memory count for a user.

        Args:
            user_id: Discord user ID.

        Returns:
            Count of memories.
        """
        return self._memory.count_memories(user_id=user_id)

    # ================================================================
    # SESSION MANAGEMENT
    # ================================================================

    def create_session(
        self,
        session_id: str,
        user_id: str,
        guild_id: str = "",
        channel_id: str = "",
        topic: str = "",
    ) -> Dict[str, Any]:
        """Create a new session record.

        Args:
            session_id: Unique session identifier.
            user_id: Associated user.
            guild_id: Discord server ID.
            channel_id: Discord channel ID.
            topic: Conversation topic.

        Returns:
            Session dict.
        """
        return self._memory.create_session(
            session_id=session_id,
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            topic=topic,
        )

    def end_session(self, session_id: str, status: str = "ended") -> Optional[Dict[str, Any]]:
        """End a session.

        Args:
            session_id: Session identifier.
            status: End status ('ended' or 'timeout').

        Returns:
            Updated session dict or None.
        """
        return self._memory.end_session(session_id, status)

    def get_active_sessions(self, guild_id: str = "", channel_id: str = "") -> List[Dict[str, Any]]:
        """Get active sessions.

        Args:
            guild_id: Filter by guild.
            channel_id: Filter by channel.

        Returns:
            List of active session dicts.
        """
        return self._memory.get_active_sessions(guild_id, channel_id)

    # ================================================================
    # WAKE-UP MEMORY
    # ================================================================

    def get_wake_up_prompt(
        self,
        user_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        max_keywords: int = 10,
    ) -> Optional[str]:
        """Get a formatted wake-up prompt from recent/relevant memories.

        This method retrieves wake-up memory and formats it into a concise
        prompt that can be injected into the bot's system prompt at session start.

        Args:
            user_id: Discord user ID for per-user wake-up memory.
            channel_id: Discord channel ID for channel-specific context.
            max_keywords: Maximum number of keywords to include.

        Returns:
            Formatted wake-up prompt string, or None if no memory found.
        """
        # Get wake-up memory
        wake_up = self.get_wake_up_memory(user_id=user_id)
        if not wake_up:
            # Try general wake-up memory as fallback
            wake_up = self.get_wake_up_memory(user_id=None)

        if not wake_up:
            return None

        # Build prompt from wake-up memory content
        content = wake_up.get("content", "")
        keywords = wake_up.get("metadata", {}).get("keywords", [])

        # Build the prompt
        parts = []
        if content:
            parts.append(f"Recent context: {content}")

        if keywords:
            parts.append(f"Key topics: {', '.join(keywords[:max_keywords])}")

        if channel_id:
            parts.append(f"Active channel: {channel_id}")

        if not parts:
            return None

        return "\n".join(parts)

    def get_wake_up_memory(self, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get wake-up memory for a user or general.

        Args:
            user_id: If provided, get per-user wake-up memory.
                    If None, get general wake-up memory.

        Returns:
            Wake-up memory dict or None.
        """
        if user_id:
            memory_type = f"user:{user_id}"
        else:
            memory_type = "general"

        return self._memory.get_wake_up_memory(memory_type)

    def set_wake_up_memory(
        self,
        content: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Set wake-up memory.

        Args:
            content: Compact summary text.
            user_id: If provided, set per-user wake-up memory.

        Returns:
            Updated wake-up memory dict.
        """
        if user_id:
            memory_type = f"user:{user_id}"
        else:
            memory_type = "general"

        return self._memory.set_wake_up_memory(memory_type, content)

    def generate_sleep_summary(
        self,
        session_id: str,
        conversation: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Generate a compact sleep summary for wake-up memory.

        This is a rule-based summary generator. In the future, this can
        be replaced with an LM-generated summary.

        Args:
            session_id: Session that ended.
            conversation: Full conversation text.
            user_id: User ID.

        Returns:
            Wake-up memory dict or None if nothing meaningful to save.
        """
        # Extract key topics
        keywords = self.extract_keywords(conversation, count=8)

        # Get existing wake-up memory to merge with
        existing = self.get_wake_up_memory(user_id)

        # Build summary
        if existing:
            # Merge: keep existing content + new keywords
            combined = f"{existing['content']}. Recent topics: {', '.join(keywords[:5])}."
        else:
            combined = f"Recent topics: {', '.join(keywords[:5])}."

        # Truncate to ~500 chars
        if len(combined) > 500:
            combined = combined[:497] + "..."

        return self.set_wake_up_memory(combined, user_id)

    # ================================================================
    # MEMORY UPDATE & LIFECYCLE
    # ================================================================

    def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        memory_type: Optional[str] = None,
        status: Optional[str] = None,
        expires_in_days: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update a memory's fields.

        Args:
            memory_id: Memory to update.
            content: New content.
            memory_type: New memory type.
            status: New status.
            expires_in_days: New expiration in days from now.

        Returns:
            Updated memory dict or None.
        """
        fields = {}
        if content is not None:
            fields["content"] = content
        if memory_type is not None:
            fields["type"] = memory_type
        if status is not None:
            fields["status"] = status
        if expires_in_days is not None:
            fields["expires_at"] = (
                datetime.utcnow() + timedelta(days=expires_in_days)
            ).isoformat()

        if not fields:
            return self._memory.get_memory(memory_id)

        return self._memory.update_memory(memory_id, **fields)

    def supersede_memory(self, memory_id: str, replacement_memory_id: str) -> bool:
        """Mark a memory as superseded by another memory.

        Args:
            memory_id: Memory to deprecate.
            replacement_memory_id: The memory that replaces it.

        Returns:
            True if successful.
        """
        return self._memory.update_memory(
            memory_id,
            status="superseded",
            superseded_by=replacement_memory_id,
        )

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory.

        Args:
            memory_id: Memory to delete.

        Returns:
            True if deleted.
        """
        return self._memory.delete_memory(memory_id)

    # ================================================================
    # PRUNING & CLEANUP
    # ================================================================

    def prune(
        self,
        keep: int = 100,
        min_importance: float = 0.1,
    ) -> Dict[str, int]:
        """Run pruning: expire old memories and deprecate low-importance ones.

        Args:
            keep: Number of highest-importance memories to preserve.
            min_importance: Memories below this score are deprecated.

        Returns:
            Dict with counts: {'expired': int, 'deprecated': int}.
        """
        return self._memory.cleanup()

    def cleanup_expired(self) -> int:
        """Mark expired memories as expired status.

        Returns:
            Number of memories expired.
        """
        return self._memory.prune_expired()

    # ================================================================
    # STATISTICS
    # ================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics.

        Returns:
            Dict with storage stats.
        """
        return self._memory.get_statistics()

    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get statistics for a specific user.

        Args:
            user_id: Discord user ID.

        Returns:
            Dict with user memory stats.
        """
        total = self._memory.count_memories(user_id=user_id)
        by_type = {}
        for mt in MemoryLite.VALID_TYPES:
            count = self._memory.count_memories(memory_type=mt, user_id=user_id)
            if count > 0:
                by_type[mt] = count

        return {
            "user_id": user_id,
            "total_memories": total,
            "by_type": by_type,
        }

    # ================================================================
    # DATABASE MAINTENANCE
    # ================================================================

    def optimize(self):
        """Run database maintenance (VACUUM + REINDEX)."""
        self._memory.optimize()

    def close(self):
        """Close the database connection."""
        self._memory.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass