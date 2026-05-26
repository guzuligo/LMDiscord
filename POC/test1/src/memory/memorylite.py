"""
Memory Lite Client Module

SQLite-based memory storage for LLM context. Provides save, search, retrieve,
update, and delete operations for managing memories.

Key Responsibilities:
- Store memories in SQLite database with WAL mode for concurrency
- Support memory types: fact, preference, context, relationship, deprecated
- Keyword-based search with importance ranking
- Related ID tracking via memory_users junction table
- Memory CRUD operations
- Automatic expiration checking

Memory Types:
- fact: Verified factual information
- preference: User preferences
- context: Temporary situational information
- relationship: Connections between entities
- deprecated: No longer valid information
"""

import sqlite3
import json
import uuid
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class MemoryLite:
    """SQLite-based memory storage client.

    Thread-safe with WAL mode for concurrent reads.
    Writes are serialized through a threading lock.
    """

    # Memory type constants
    TYPE_FACT = "fact"
    TYPE_PREFERENCE = "preference"
    TYPE_CONTEXT = "context"
    TYPE_RELATIONSHIP = "relationship"
    TYPE_DEPRECATED = "deprecated"

    # Status constants
    STATUS_ACTIVE = "active"
    STATUS_DEPRECATED = "deprecated"
    STATUS_EXPIRED = "expired"
    STATUS_SUPERSEDED = "superseded"

    # Valid types and statuses
    VALID_TYPES = [TYPE_FACT, TYPE_PREFERENCE, TYPE_CONTEXT, TYPE_RELATIONSHIP, TYPE_DEPRECATED]
    VALID_STATUSES = [STATUS_ACTIVE, STATUS_DEPRECATED, STATUS_EXPIRED, STATUS_SUPERSEDED]

    def __init__(self, db_path: str = "user/data/memory/memory.db", max_expected_updates: int = 10, max_days: float = 90.0):
        """Initialize MemoryLite client.

        Args:
            db_path: Path to SQLite database file. Use ':memory:' for in-memory DB,
                     or a file path like 'user/data/memory/memory.db' for persistent storage.
            max_expected_updates: Normalization factor for update_count in importance scoring.
            max_days: Factor for recency score calculation.
        """
        self._lock = threading.Lock()
        self._max_expected_updates = max_expected_updates
        self._max_days = max_days

        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._create_tables()

    def _create_tables(self):
        """Create all memory tables from schema v2.0."""
        self._conn.executescript("""
            -- Users table
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Memories table
            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'fact' CHECK(type IN ('fact', 'preference', 'context', 'relationship', 'deprecated')),
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'deprecated', 'expired', 'superseded')),
                importance REAL NOT NULL DEFAULT 0.5 CHECK(importance >= 0.0 AND importance <= 1.0),
                update_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                superseded_by TEXT,
                source_session_id TEXT,
                metadata TEXT,
                FOREIGN KEY (superseded_by) REFERENCES memories(memory_id)
            );

            -- Memory-users junction table (many-to-many)
            CREATE TABLE IF NOT EXISTS memory_users (
                memory_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'observer' CHECK(role IN ('speaker', 'subject', 'observer')),
                PRIMARY KEY (memory_id, user_id),
                FOREIGN KEY (memory_id) REFERENCES memories(memory_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            -- Sessions table
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                guild_id TEXT,
                channel_id TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                topic TEXT,
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'ended', 'timeout')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            -- Wake-up memory table
            CREATE TABLE IF NOT EXISTS wake_up_memory (
                memory_type TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                version INTEGER NOT NULL DEFAULT 1
            );

            -- Indexes for performance
            CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
            CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status);
            CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC);
            CREATE INDEX IF NOT EXISTS idx_memories_update_count ON memories(update_count DESC);
            CREATE INDEX IF NOT EXISTS idx_memories_expires_at ON memories(expires_at);
            CREATE INDEX IF NOT EXISTS idx_memory_users_user_id ON memory_users(user_id);
            CREATE INDEX IF NOT EXISTS idx_memory_users_memory_id ON memory_users(memory_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_guild_id ON sessions(guild_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_channel_id ON sessions(channel_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
        """)
        self._conn.commit()

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _generate_id(self) -> str:
        """Generate a unique memory ID."""
        return f"mem_{uuid.uuid4().hex[:12]}"

    def _now(self) -> str:
        """Return current UTC timestamp as ISO string."""
        return datetime.utcnow().isoformat()

    def _importance(
        self,
        update_count: int = 0,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        explicit_weight: float = 0.5,
    ) -> float:
        """Calculate importance score using the standard formula.

        importance = (update_count_normalized * 0.4) + (recency_score * 0.3) + (explicit_weight * 0.3)
        """
        # Update count component
        update_count_normalized = min(update_count / max(self._max_expected_updates, 1), 1.0)

        # Recency component
        if updated_at:
            try:
                updated_dt = datetime.fromisoformat(updated_at)
            except (ValueError, TypeError):
                updated_dt = datetime.utcnow()
            days_since = (datetime.utcnow() - updated_dt).total_seconds() / 86400.0
            recency_score = max(0.0, 1.0 - days_since / self._max_days)
        elif created_at:
            try:
                created_dt = datetime.fromisoformat(created_at)
            except (ValueError, TypeError):
                created_dt = datetime.utcnow()
            days_since = (datetime.utcnow() - created_dt).total_seconds() / 86400.0
            recency_score = max(0.0, 1.0 - days_since / self._max_days)
        else:
            recency_score = 0.5  # Neutral default

        importance = (update_count_normalized * 0.4) + (recency_score * 0.3) + (explicit_weight * 0.3)
        return round(min(max(importance, 0.0), 1.0), 4)

    def _row_to_memory(self, row: Optional[sqlite3.Row]) -> Optional[dict]:
        """Convert a database row to a memory dict."""
        if row is None:
            return None
        metadata = row["metadata"]
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = None
        return {
            "memory_id": row["memory_id"],
            "content": row["content"],
            "type": row["type"],
            "status": row["status"],
            "importance": row["importance"],
            "update_count": row["update_count"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "expires_at": row["expires_at"],
            "superseded_by": row["superseded_by"],
            "source_session_id": row["source_session_id"],
            "metadata": metadata,
        }

    def _row_to_user(self, row: Optional[sqlite3.Row]) -> Optional[dict]:
        """Convert a database row to a user dict."""
        if row is None:
            return None
        return {
            "user_id": row["user_id"],
            "username": row["username"],
            "created_at": row["created_at"],
            "last_active": row["last_active"],
        }

    def _row_to_session(self, row: Optional[sqlite3.Row]) -> Optional[dict]:
        """Convert a database row to a session dict."""
        if row is None:
            return None
        return {
            "session_id": row["session_id"],
            "user_id": row["user_id"],
            "guild_id": row["guild_id"],
            "channel_id": row["channel_id"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "topic": row["topic"],
            "status": row["status"],
        }

    def _row_to_wake_up(self, row: Optional[sqlite3.Row]) -> Optional[dict]:
        """Convert a database row to a wake-up memory dict."""
        if row is None:
            return None
        return {
            "memory_type": row["memory_type"],
            "content": row["content"],
            "last_updated": row["last_updated"],
            "version": row["version"],
        }

    def _safe_str(self, row: sqlite3.Row, key: str) -> Optional[str]:
        """Safely get a string value from a row, returning None if NULL."""
        val = row[key]
        return val if val is not None else None

    # ----------------------------------------------------------------
    # Thread-safe wrapper
    # ----------------------------------------------------------------

    def _execute(self, sql: str, params: tuple = (), fetchone=False, fetchall=False):
        """Execute SQL within the write lock."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(sql, params)
            if fetchone:
                result = cursor.fetchone()
            elif fetchall:
                result = cursor.fetchall()
            else:
                result = None
            self._conn.commit()
        return result, cursor

    # ================================================================
    # USER OPERATIONS
    # ================================================================

    def upsert_user(self, user_id: str, username: str = "") -> dict:
        """Create or update a user record.

        Args:
            user_id: Immutable Discord user ID.
            username: Display username (optional).

        Returns:
            User dict.
        """
        sql = """
            INSERT INTO users (user_id, username, created_at, last_active)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                last_active = excluded.last_active
        """
        now = self._now()
        self._execute(sql, (user_id, username, now, now))
        return self.get_user(user_id)

    def get_user(self, user_id: str) -> Optional[dict]:
        """Retrieve a user by ID.

        Args:
            user_id: Discord user ID.

        Returns:
            User dict or None.
        """
        sql = "SELECT * FROM users WHERE user_id = ?"
        row, _ = self._execute(sql, (user_id,), fetchone=True)
        return self._row_to_user(row)

    def list_users(self, limit: int = 100) -> list:
        """List all users.

        Args:
            limit: Maximum number of users to return.

        Returns:
            List of user dicts.
        """
        sql = "SELECT * FROM users ORDER BY last_active DESC LIMIT ?"
        rows, _ = self._execute(sql, (limit,), fetchall=True)
        return [self._row_to_user(r) for r in rows if r]

    # ================================================================
    # SESSION OPERATIONS
    # ================================================================

    def create_session(self, session_id: str, user_id: str, guild_id: str = "", channel_id: str = "", topic: str = "") -> dict:
        """Create a new session.

        Args:
            session_id: Unique session identifier.
            user_id: Associated user ID.
            guild_id: Discord server ID.
            channel_id: Discord channel ID.
            topic: Conversation topic.

        Returns:
            Session dict.
        """
        sql = """
            INSERT INTO sessions (session_id, user_id, guild_id, channel_id, topic, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        """
        self._execute(sql, (session_id, user_id, guild_id, channel_id, topic))
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve a session by ID.

        Args:
            session_id: Session identifier.

        Returns:
            Session dict or None.
        """
        sql = "SELECT * FROM sessions WHERE session_id = ?"
        row, _ = self._execute(sql, (session_id,), fetchone=True)
        return self._row_to_session(row)

    def end_session(self, session_id: str, status: str = "ended") -> Optional[dict]:
        """End a session.

        Args:
            session_id: Session identifier.
            status: End status ('ended' or 'timeout').

        Returns:
            Updated session dict or None.
        """
        sql = """
            UPDATE sessions SET status = ?, ended_at = ? WHERE session_id = ?
        """
        _, _ = self._execute(sql, (status, self._now(), session_id))
        return self.get_session(session_id)

    def get_active_sessions(self, guild_id: str = "", channel_id: str = "") -> list:
        """Get active sessions, optionally filtered by guild or channel.

        Args:
            guild_id: Filter by guild.
            channel_id: Filter by channel.

        Returns:
            List of session dicts.
        """
        conditions = ["status = 'active'"]
        params = []
        if guild_id:
            conditions.append("guild_id = ?")
            params.append(guild_id)
        if channel_id:
            conditions.append("channel_id = ?")
            params.append(channel_id)
        sql = f"SELECT * FROM sessions WHERE {' AND '.join(conditions)} ORDER BY started_at DESC"
        rows, _ = self._execute(sql, tuple(params), fetchall=True)
        return [self._row_to_session(r) for r in rows if r]

    # ================================================================
    # MEMORY OPERATIONS (CRUD)
    # ================================================================

    def create_memory(
        self,
        content: str,
        memory_type: str = "fact",
        user_ids: Optional[list] = None,
        session_id: Optional[str] = None,
        expires_at: Optional[str] = None,
        metadata: Optional[dict] = None,
        explicit_weight: float = 0.5,
    ) -> dict:
        """Create a new memory.

        Args:
            content: Memory content text.
            memory_type: One of fact, preference, context, relationship, deprecated.
            user_ids: List of user IDs associated with this memory.
            session_id: Source session ID.
            expires_at: Expiration timestamp (optional).
            metadata: Arbitrary JSON-serializable data.
            explicit_weight: Weight for importance calculation (0.0-1.0).

        Returns:
            Memory dict.

        Raises:
            ValueError: If memory_type is invalid.
        """
        if memory_type not in self.VALID_TYPES:
            raise ValueError(f"Invalid memory type '{memory_type}'. Must be one of {self.VALID_TYPES}")

        memory_id = self._generate_id()
        now = self._now()
        meta_json = json.dumps(metadata) if metadata else None
        importance = self._importance(explicit_weight=explicit_weight)

        sql = """
            INSERT INTO memories (memory_id, content, type, status, importance, created_at, updated_at, expires_at, source_session_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._execute(sql, (
            memory_id, content, memory_type, self.STATUS_ACTIVE,
            importance, now, now, expires_at, session_id, meta_json,
        ))

        # Link users
        if user_ids:
            for uid in user_ids:
                self._link_user_to_memory(memory_id, uid, "observer")

        return self.get_memory(memory_id)

    def get_memory(self, memory_id: str) -> Optional[dict]:
        """Retrieve a memory by ID.

        Args:
            memory_id: Memory identifier.

        Returns:
            Memory dict or None.
        """
        sql = "SELECT * FROM memories WHERE memory_id = ?"
        row, _ = self._execute(sql, (memory_id,), fetchone=True)
        return self._row_to_memory(row)

    def update_memory(self, memory_id: str, **fields) -> Optional[dict]:
        """Update a memory's fields.

        Supported fields: content, type, status, importance, expires_at, metadata, superseded_by

        Args:
            memory_id: Memory identifier.
            **fields: Fields to update.

        Returns:
            Updated memory dict or None if not found.
        """
        if not fields:
            return self.get_memory(memory_id)

        allowed = {"content", "type", "status", "importance", "expires_at", "metadata", "superseded_by"}
        invalid = set(fields.keys()) - allowed
        if invalid:
            raise ValueError(f"Invalid fields: {invalid}. Allowed: {allowed}")

        set_clauses = []
        params = []
        for key, value in fields.items():
            if key == "metadata":
                value = json.dumps(value) if isinstance(value, dict) else value
            set_clauses.append(f"{key} = ?")
            params.append(value)

        # Increment update_count and updated_at
        set_clauses.append("update_count = update_count + 1")
        set_clauses.append("updated_at = ?")
        params.append(self._now())

        params.append(memory_id)
        sql = f"UPDATE memories SET {' , '.join(set_clauses)} WHERE memory_id = ?"
        self._execute(sql, tuple(params))

        return self.get_memory(memory_id)

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory and its user associations.

        Args:
            memory_id: Memory identifier.

        Returns:
            True if deleted, False if not found.
        """
        # First remove from memory_users junction (FK constraint order)
        self._execute("DELETE FROM memory_users WHERE memory_id = ?", (memory_id,))
        sql = "DELETE FROM memories WHERE memory_id = ?"
        _, cursor = self._execute(sql, (memory_id,))
        return cursor.rowcount > 0

    def list_memories(
        self,
        memory_type: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        guild_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "updated_at",
        order_dir: str = "DESC",
    ) -> list:
        """List memories with optional filters.

        Args:
            memory_type: Filter by type.
            status: Filter by status.
            user_id: Filter by associated user.
            guild_id: Filter by guild (via sessions).
            limit: Max results.
            offset: Pagination offset.
            order_by: Sort field (created_at, updated_at, importance, update_count).
            order_dir: ASC or DESC.

        Returns:
            List of memory dicts.
        """
        conditions = []
        params = []

        if memory_type:
            conditions.append("m.type = ?")
            params.append(memory_type)

        if status:
            conditions.append("m.status = ?")
            params.append(status)

        if user_id:
            conditions.append("mu.user_id = ?")
            params.append(user_id)

        if guild_id:
            conditions.append("s.guild_id = ?")
            params.append(guild_id)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        valid_order = {"created_at", "updated_at", "importance", "update_count", "memory_id"}
        if order_by not in valid_order:
            order_by = "updated_at"
        order_dir = "DESC" if order_dir.upper() == "DESC" else "ASC"

        sql = f"""
            SELECT DISTINCT m.* FROM memories m
            {'JOIN memory_users mu ON m.memory_id = mu.memory_id' if user_id else ''}
            {'JOIN sessions s ON m.source_session_id = s.session_id' if guild_id else ''}
            {where}
            ORDER BY m.{order_by} {order_dir}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows, _ = self._execute(sql, tuple(params), fetchall=True)
        return [self._row_to_memory(r) for r in rows if r]

    def count_memories(self, memory_type: Optional[str] = None, status: Optional[str] = None, user_id: Optional[str] = None) -> int:
        """Count memories with optional filters.

        Args:
            memory_type: Filter by type.
            status: Filter by status.
            user_id: Filter by user.

        Returns:
            Count.
        """
        conditions = []
        params = []

        if memory_type:
            conditions.append("type = ?")
            params.append(memory_type)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if user_id:
            sql = """
                SELECT COUNT(DISTINCT m.memory_id) FROM memories m
                JOIN memory_users mu ON m.memory_id = mu.memory_id
                WHERE mu.user_id = ?
            """
            if conditions:
                sql += " AND " + " AND ".join(conditions)
            params.append(user_id)
        else:
            sql = f"SELECT COUNT(*) FROM memories WHERE {' AND '.join(conditions)}" if conditions else "SELECT COUNT(*) FROM memories"

        row, _ = self._execute(sql, tuple(params), fetchone=True)
        return row[0] if row else 0

    # ================================================================
    # USER-MEMORY LINKING
    # ================================================================

    def _link_user_to_memory(self, memory_id: str, user_id: str, role: str = "observer"):
        """Link a user to a memory (internal, no lock needed — called within _execute)."""
        sql = """
            INSERT OR IGNORE INTO users (user_id, username, created_at, last_active)
            VALUES (?, '', ?, ?)
        """
        now = self._now()
        self._execute(sql, (user_id, now, now))

        sql = """
            INSERT OR IGNORE INTO memory_users (memory_id, user_id, role)
            VALUES (?, ?, ?)
        """
        self._execute(sql, (memory_id, user_id, role))

    def add_user_to_memory(self, memory_id: str, user_id: str, role: str = "observer") -> bool:
        """Add a user association to an existing memory.

        Auto-creates the user if they don't exist.

        Args:
            memory_id: Memory identifier.
            user_id: User identifier.
            role: User role (speaker, subject, observer).

        Returns:
            True if added, False if already linked.
        """
        # Auto-create user if not exists
        self.upsert_user(user_id)
        sql = """
            INSERT OR IGNORE INTO memory_users (memory_id, user_id, role)
            VALUES (?, ?, ?)
        """
        _, cursor = self._execute(sql, (memory_id, user_id, role))
        return cursor.rowcount > 0

    def remove_user_from_memory(self, memory_id: str, user_id: str) -> bool:
        """Remove a user association from a memory.

        Args:
            memory_id: Memory identifier.
            user_id: User identifier.

        Returns:
            True if removed, False if not found.
        """
        sql = "DELETE FROM memory_users WHERE memory_id = ? AND user_id = ?"
        _, cursor = self._execute(sql, (memory_id, user_id))
        return cursor.rowcount > 0

    def get_users_for_memory(self, memory_id: str) -> list:
        """Get all users associated with a memory.

        Args:
            memory_id: Memory identifier.

        Returns:
            List of user dicts with role info.
        """
        sql = """
            SELECT u.*, mu.role FROM users u
            JOIN memory_users mu ON u.user_id = mu.user_id
            WHERE mu.memory_id = ?
        """
        rows, _ = self._execute(sql, (memory_id,), fetchall=True)
        result = []
        for row in rows:
            entry = {
                "user_id": row["user_id"],
                "username": row["username"],
                "created_at": row["created_at"],
                "last_active": row["last_active"],
                "role": row["role"],
            }
            result.append(entry)
        return result

    # ================================================================
    # SEARCH
    # ================================================================

    def search_by_keywords(self, keywords: list, limit: int = 10, memory_type: Optional[str] = None) -> list:
        """Search memories by keyword matching in content.

        Performs a simple LIKE-based search across memory content.
        Results are ranked by importance (higher = more relevant).

        Args:
            keywords: List of keywords to search for.
            limit: Maximum results.
            memory_type: Optional type filter.

        Returns:
            List of matching memory dicts, ranked by importance.
        """
        if not keywords:
            return []

        conditions = ["m.status = 'active'"]
        params = []

        if memory_type:
            conditions.append("m.type = ?")
            params.append(memory_type)

        # Build OR conditions for each keyword
        keyword_conditions = []
        for kw in keywords:
            keyword_conditions.append("m.content LIKE ?")
            params.append(f"%{kw}%")

        conditions.append(f"({' OR '.join(keyword_conditions)})")

        sql = f"""
            SELECT m.*, COUNT(DISTINCT mu.user_id) as user_count
            FROM memories m
            LEFT JOIN memory_users mu ON m.memory_id = mu.memory_id
            WHERE {' AND '.join(conditions)}
            GROUP BY m.memory_id
            ORDER BY m.importance DESC, m.updated_at DESC
            LIMIT ?
        """
        params.append(limit)

        rows, _ = self._execute(sql, tuple(params), fetchall=True)
        return [self._row_to_memory(r) for r in rows if r]

    def search_by_type(self, memory_type: str, limit: int = 50) -> list:
        """Search memories by type.

        Args:
            memory_type: Memory type to filter by.
            limit: Maximum results.

        Returns:
            List of memory dicts.
        """
        sql = """
            SELECT * FROM memories
            WHERE type = ? AND status = 'active'
            ORDER BY importance DESC, updated_at DESC
            LIMIT ?
        """
        rows, _ = self._execute(sql, (memory_type, limit), fetchall=True)
        return [self._row_to_memory(r) for r in rows if r]

    def search_recent(self, limit: int = 20) -> list:
        """Get the most recently updated memories.

        Args:
            limit: Maximum results.

        Returns:
            List of memory dicts.
        """
        sql = """
            SELECT * FROM memories
            WHERE status = 'active'
            ORDER BY updated_at DESC
            LIMIT ?
        """
        rows, _ = self._execute(sql, (limit,), fetchall=True)
        return [self._row_to_memory(r) for r in rows if r]

    def search_by_importance(self, min_importance: float = 0.5, limit: int = 50) -> list:
        """Get memories above a minimum importance threshold.

        Args:
            min_importance: Minimum importance score (0.0-1.0).
            limit: Maximum results.

        Returns:
            List of memory dicts.
        """
        sql = """
            SELECT * FROM memories
            WHERE status = 'active' AND importance >= ?
            ORDER BY importance DESC, updated_at DESC
            LIMIT ?
        """
        rows, _ = self._execute(sql, (min_importance, limit), fetchall=True)
        return [self._row_to_memory(r) for r in rows if r]

    def search_expired(self) -> list:
        """Get all expired memories.

        Returns:
            List of expired memory dicts.
        """
        sql = """
            SELECT * FROM memories
            WHERE expires_at IS NOT NULL AND expires_at <= ? AND status = 'active'
        """
        now = self._now()
        rows, _ = self._execute(sql, (now,), fetchall=True)
        return [self._row_to_memory(r) for r in rows if r]

    # ================================================================
    # WAKE-UP MEMORY
    # ================================================================

    def get_wake_up_memory(self, memory_type: str) -> Optional[dict]:
        """Get a wake-up memory entry.

        Args:
            memory_type: 'general' or 'user:<user_id>'.

        Returns:
            Wake-up memory dict or None.
        """
        sql = "SELECT * FROM wake_up_memory WHERE memory_type = ?"
        row, _ = self._execute(sql, (memory_type,), fetchone=True)
        return self._row_to_wake_up(row)

    def set_wake_up_memory(self, memory_type: str, content: str) -> dict:
        """Create or update a wake-up memory entry.

        Args:
            memory_type: 'general' or 'user:<user_id>'.
            content: Compact summary text (~500 chars max recommended).

        Returns:
            Updated wake-up memory dict.
        """
        now = self._now()
        existing = self.get_wake_up_memory(memory_type)
        version = (existing["version"] + 1) if existing else 1

        if existing:
            sql = """
                UPDATE wake_up_memory SET content = ?, last_updated = ?, version = ?
                WHERE memory_type = ?
            """
            self._execute(sql, (content, now, version, memory_type))
        else:
            sql = """
                INSERT INTO wake_up_memory (memory_type, content, last_updated, version)
                VALUES (?, ?, ?, ?)
            """
            self._execute(sql, (memory_type, content, now, version))

        return self.get_wake_up_memory(memory_type)

    def delete_wake_up_memory(self, memory_type: str) -> bool:
        """Delete a wake-up memory entry.

        Args:
            memory_type: 'general' or 'user:<user_id>'.

        Returns:
            True if deleted, False if not found.
        """
        sql = "DELETE FROM wake_up_memory WHERE memory_type = ?"
        _, cursor = self._execute(sql, (memory_type,))
        return cursor.rowcount > 0

    def list_wake_up_memories(self) -> list:
        """List all wake-up memory entries.

        Returns:
            List of wake-up memory dicts.
        """
        sql = "SELECT * FROM wake_up_memory ORDER BY memory_type"
        rows, _ = self._execute(sql, (), fetchall=True)
        return [self._row_to_wake_up(r) for r in rows if r]

    # ================================================================
    # PRUNING & CLEANUP
    # ================================================================

    def prune_low_importance(self, keep: int = 100, min_importance: float = 0.1) -> int:
        """Deprecate low-importance memories, keeping the top N by importance.

        Args:
            keep: Number of highest-importance memories to preserve.
            min_importance: Memories below this score are candidates for deprecation.

        Returns:
            Number of memories deprecated.
        """
        # First, mark anything below min_importance as deprecated
        sql = """
            UPDATE memories SET status = 'deprecated', updated_at = ?
            WHERE status = 'active' AND importance < ?
              AND memory_id NOT IN (
                  SELECT memory_id FROM memories
                  WHERE status = 'active'
                  ORDER BY importance DESC
                  LIMIT ?
              )
        """
        _, cursor = self._execute(sql, (self._now(), min_importance, keep))
        return cursor.rowcount

    def prune_expired(self) -> int:
        """Mark all expired memories as expired status.

        Returns:
            Number of memories expired.
        """
        now = self._now()
        sql = """
            UPDATE memories SET status = 'expired', updated_at = ?
            WHERE expires_at IS NOT NULL AND expires_at <= ? AND status = 'active'
        """
        _, cursor = self._execute(sql, (now, now))
        return cursor.rowcount

    def cleanup(self) -> dict:
        """Run full cleanup: expire old memories, prune low-importance.

        Returns:
            Dict with counts: {expired: int, deprecated: int}.
        """
        expired = self.prune_expired()
        deprecated = self.prune_low_importance()
        return {"expired": expired, "deprecated": deprecated}

    # ================================================================
    # STATISTICS
    # ================================================================

    def get_statistics(self) -> dict:
        """Get memory storage statistics.

        Returns:
            Dict with storage stats.
        """
        stats = {}

        # Total memories by type
        sql = "SELECT type, COUNT(*) as count FROM memories GROUP BY type"
        rows, _ = self._execute(sql, (), fetchall=True)
        stats["by_type"] = {row["type"]: row["count"] for row in rows} if rows else {}

        # Total memories by status
        sql = "SELECT status, COUNT(*) as count FROM memories GROUP BY status"
        rows, _ = self._execute(sql, (), fetchall=True)
        stats["by_status"] = {row["status"]: row["count"] for row in rows} if rows else {}

        # Total users
        sql = "SELECT COUNT(*) as count FROM users"
        row, _ = self._execute(sql, (), fetchone=True)
        stats["total_users"] = row["count"] if row else 0

        # Total sessions
        sql = "SELECT COUNT(*) as count FROM sessions"
        row, _ = self._execute(sql, (), fetchone=True)
        stats["total_sessions"] = row["count"] if row else 0

        # Active sessions
        sql = "SELECT COUNT(*) as count FROM sessions WHERE status = 'active'"
        row, _ = self._execute(sql, (), fetchone=True)
        stats["active_sessions"] = row["count"] if row else 0

        # Total memories
        sql = "SELECT COUNT(*) as count FROM memories"
        row, _ = self._execute(sql, (), fetchone=True)
        stats["total_memories"] = row["count"] if row else 0

        # Average importance
        sql = "SELECT AVG(importance) as avg_imp, MAX(importance) as max_imp, MIN(importance) as min_imp FROM memories WHERE status = 'active'"
        row, _ = self._execute(sql, (), fetchone=True)
        if row:
            stats["avg_importance"] = row["avg_imp"] or 0.0
            stats["max_importance"] = row["max_imp"] or 0.0
            stats["min_importance"] = row["min_imp"] or 0.0

        return stats

    # ================================================================
    # DATABASE MAINTENANCE
    # ================================================================

    def optimize(self):
        """Run VACUUM and REINDEX for database maintenance."""
        self._execute("VACUUM")
        self._execute("REINDEX")

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass