# Memory Module - Issues Tracker

## How to Use
- Add any issues, errors, or problems encountered during memory module implementation
- Include the status (Open, In Progress, Solved, Won't Fix)
- Document workarounds or solutions

---

## Open Issues

_No open issues._

---

## Solved Issues

_No issues solved yet._

---

## Known Limitations

### LIM-001: SQLite Concurrency Constraints

| Field | Value |
|-------|-------|
| **ID** | LIM-001 |
| **Date** | 2026-05-21 |
| **Status** | 🔄 Known |
| **Severity** | Low |
| **Description** | SQLite has limitations on concurrent write operations. When multiple Discord channels trigger memory operations simultaneously, write conflicts may occur. |
| **Impact** | Potential `database is locked` errors during high-concurrency scenarios |
| **Workaround** | Use WAL (Write-Ahead Logging) mode, implement retry logic for database operations, serialize writes through a queue |
| **Planned Fix** | Implement connection pooling with write serialization in `storage.py` |

---

### LIM-002: Memory Storage Size Growth

| Field | Value |
|-------|-------|
| **ID** | LIM-002 |
| **Date** | 2026-05-21 |
| **Status** | 🔄 Known |
| **Severity** | Low |
| **Description** | Without proper pruning, memory storage can grow indefinitely as the bot interacts with more users over time. |
| **Impact** | Database file size increases, potential performance degradation on memory recall |
| **Workaround** | Configurable memory lifespan with automatic expiration, manual cleanup API endpoint |
| **Planned Fix** | Implement memory summarization with automatic pruning and memory fusion |

---

## Planning Phase Issues

### REQ-001: Define Memory Schema

| Field | Value |
|-------|-------|
| **ID** | REQ-001 |
| **Date** | 2026-05-21 |
| **Status** | ⏳ Planned |
| **Severity** | Medium |
| **Description** | Design the SQLite schema for users, memories, sessions, and associations. |
| **Requirements** | 1. Users table with immutable user_id 2. Memories table with type, importance, expiration 3. Sessions table with topic tracking 4. Indexes for efficient recall queries |

---

### REQ-002: Implement Core Memory Engine

| Field | Value |
|-------|-------|
| **ID** | REQ-002 |
| **Date** | 2026-05-21 |
| **Status** | ⏳ Planned |
| **Severity** | Medium |
| **Description** | Build the central memory engine that coordinates all memory operations. |
| **Requirements** | 1. Memory create, read, update, delete operations 2. Memory recall with multiple strategies 3. Memory summarization triggers 4. Integration with LM Studio tool interface |

---

### REQ-003: LM Studio Tool Interface

| Field | Value |
|-------|-------|
| **ID** | REQ-003 |
| **Date** | 2026-05-21 |
| **Status** | ⏳ Planned |
| **Severity** | High |
| **Description** | Expose memory operations as LM Studio tools for the model to call. |
| **Requirements** | 1. `memory_recall` tool - search and retrieve memories 2. `memory_create` tool - store new memories 3. `memory_update` tool - modify existing memories 4. Tool definitions compatible with existing tools system |
| **Integration** | `src/discord_bot/bot_core.py` (tool registration) |

---

### REQ-004: Discord Bot Integration

| Field | Value |
|-------|-------|
| **ID** | REQ-004 |
| **Date** | 2026-05-21 |
| **Status** | ⏳ Planned |
| **Severity** | High |
| **Description** | Integrate memory module with existing Discord bot modules. |
| **Requirements** | 1. Session lifecycle hooks (start, update, end) 2. Memory creation from conversation content 3. Memory recall before LM Studio calls 4. Per-server memory isolation |
| **Files To Modify** | `src/discord_bot/session_manager.py`, `src/discord_bot/bot_core.py`, `src/discord_bot/message_handler.py` |

---

### REQ-005: Memory Summarization and Pruning

| Field | Value |
|-------|-------|
| **ID** | REQ-005 |
| **Date** | 2026-05-21 |
| **Status** | ⏳ Planned |
| **Severity** | Medium |
| **Description** | Implement memory summarization to prevent storage bloat and improve recall quality. |
| **Requirements** | 1. Importance scoring for memories 2. Automatic pruning of low-importance old memories 3. Memory fusion (combining related memories) 4. Configurable memory lifespan |

---

## Feature Concepts (Pending Refinement)

### CONCEPT-001: Wake-Up Memory System

| Field | Value |
|-------|-------|
| **ID** | CONCEPT-001 |
| **Date** | 2026-05-21 |
| **Status** | 💡 Concept - Pending Refinement |
| **Severity** | N/A (Feature concept, not a bug) |
| **Description** | Implement a "wake-up memory" system that persists context across sessions. After each session end, a "sleep procedure" updates the wake-up memory. This memory contains a compact summary of what should be remembered for the next sessions. |

#### Wake-Up Memory Types

| Type | Scope | Description |
|------|-------|-------------|
| **General Wake-Up Memory** | Bot-wide | High-level summary of what the bot should remember across ALL users/servers |
| **Per-User Wake-Up Memory** | Per user | Personalized context about a specific user's ongoing topics, preferences, recent activities |

#### Sleep Procedure Flow

```
Session End (end_session tool or timeout)
    ↓
1. Extract key topics from last conversation
2. Load current wake-up memory (general + per-user)
3. Merge: new topics + existing context
4. Summarize and rewrite (compact, no growth)
5. Store back to SQLite
    ↓
Wake-up memory updated, ready for next session
```

#### Wake-Up Memory Sources

1. **Previous wake-up memory** - Continuity across sessions
2. **Last conversation** - Recent topics, unresolved questions, user state
3. **Explicit references** - When user says "remember X" or "for later, check Y"

#### Proposed Schema: `wake_up_memory` Table

| Field | Type | Description |
|-------|------|-------------|
| memory_type | TEXT (PK) | 'general' or 'user:<user_id>' |
| content | TEXT | The summarized wake-up memory (compact, ~500 chars max) |
| last_updated | TIMESTAMP | When last rewritten |
| version | INTEGER | Revision counter |

#### Integration Points

- **Trigger**: LM Studio `end_session` tool, session timeout, or manual `trigger_sleep()` tool
- **Generation**: LM Studio summarizes conversation during sleep procedure
- **Recall**: Loaded at session start and injected into system prompt
- **Query**: Users can ask "What do you remember about me?" to view their wake-up memory

#### Open Questions

1. Should wake-up memory be LM-generated or rule-based? (Recommend: LM-generated)
2. Should there be per-channel wake-up memory too? (Currently: general + per-user)
3. What's the max size for wake-up memory? (Suggest: ~500 chars)
4. Should users be able to query/modify wake-up memory?

---

### CONCEPT-002: Memory Update Counter for Importance Scoring

| Field | Value |
|-------|-------|
| **ID** | CONCEPT-002 |
| **Date** | 2026-05-21 |
| **Status** | 💡 Concept - Pending Refinement |
| **Severity** | N/A (Feature concept, not a bug) |
| **Description** | Add an update counter to each memory. Frequently updated memories are likely more important (actively relevant, being refined, high priority for retention). |

#### Implementation

```python
class Memory:
    memory_id: str
    content: str
    update_count: int  # Incremented on each update
    last_updated: TIMESTAMP
    importance: float  # Derived from update_count, recency, etc.
```

#### Importance Scoring Formula (Initial)

```
importance = (update_count * 0.4) + (recency_score * 0.3) + (explicit_weight * 0.3)
```

Where:
- `update_count` = how many times memory was modified
- `recency_score` = 1.0 for today, decays over time
- `explicit_weight` = user-set weight (e.g., "this is important")

#### Schema Updates for `memories` Table

Add columns:
- `update_count` INTEGER DEFAULT 0
- `last_updated` TIMESTAMP (separate from created_at)

#### Benefits

- Frequently updated memories automatically get higher importance
- Helps pruning decisions (keep frequently modified memories)
- Provides signal for memory fusion (similar memories with high update counts)

---

## Related Issues from Main Project

| Parent Issue | Description | Status |
|--------------|-------------|--------|
| FEAT-005 (main) | Memory Integration with memorylite | ⏳ Planned - Now implemented as this module |
| BUG-003 (main) | Bot Cannot Identify Discord Users | ✅ Solved - Identity tracking provides foundation for memory |
| ISS-018 (main) | Active Session Context Loss | ✅ Solved - Context persistence within sessions |

---

## Bug Templates

When reporting bugs, use this format:

```markdown
### BUG-XXX: [Brief Description]

| Field | Value |
|-------|-------|
| **ID** | BUG-XXX |
| **Date** | YYYY-MM-DD |
| **Status** | 🔄 Open / In Progress / ✅ Solved |
| **Severity** | Critical / High / Medium / Low |
| **Description** | [Detailed description] |
| **Root Cause** | [If known] |
| **Fix Applied** | [If solved] |
| **Files Modified** | [List of files] |
```

---

## Issue Status Legend

| Status | Meaning |
|--------|---------|
| ⏳ Planned | Issue identified, not yet started |
| 🔄 Open | Issue being worked on |
| ✅ Solved | Issue resolved and verified |
| ❌ Won't Fix | Issue acknowledged but not actionable |