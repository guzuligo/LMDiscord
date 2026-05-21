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
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | Design the SQLite schema for users, memories, sessions, and associations. |
| **Solution** | Finalized schema with 5 tables: `memories`, `memory_users` (junction), `users`, `sessions`, `wake_up_memory`. Supports multi-user memories via junction table, memory lifecycle tracking (active/deprecated/expired/superseded), and importance scoring for both pruning and search. |

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

### CONCEPT-003: MemoryBot Architecture

| Field | Value |
|-------|-------|
| **ID** | CONCEPT-003 |
| **Date** | 2026-05-21 |
| **Status** | 💡 Concept - Documented |
| **Severity** | N/A (Feature concept, not a bug) |
| **Description** | Implement a specialized MemoryBot sub-bot with fresh isolated context that handles memory search operations, protecting the main conversation context from being saturated with irrelevant memory results. |

#### Architecture

```
Main Bot (holds main conversation context)
    ↓ requests memory search for: "User's current project details"
MemoryBot (fresh isolated context, has memory tools)
    ↓ calls memory_recall with broad queries
Memory System (returns many results, most irrelevant)
MemoryBot (filters noise, extracts relevant findings)
    ↓ returns distilled results
Main Bot (receives only relevant info, context preserved)
```

#### MemoryBot Lifecycle

1. **Activation**: Triggered when Main Bot needs memory information
2. **Session**: Fresh context, calls memory tools, gets polluted with irrelevant results
3. **Completion**: MemoryBot signals "job done" when search is complete
4. **Termination**: On new prompt, MemoryBot decides if existing context is relevant
5. **Flush & Restart**: If irrelevant, MemoryBot clears context and starts fresh

#### Communication Protocol (Shared Memory)

```
Main Bot writes: {query, priority, session_id}
MemoryBot reads → searches → writes: {findings, confidence, completed}
Main Bot reads findings → continues conversation
```

#### MemoryBot System Prompt Template

```
You are MemoryBot, a specialized memory search assistant.
Your job: Find relevant memories for the Main Bot's query.
Tools available: memory_recall, memory_create, memory_update

When you have sufficient relevant findings, respond with:
[SEARCH_COMPLETE] <summary of findings>

If no relevant memories exist, respond with:
[NO_RELEVANT_MEMORIES]
```

#### Completion Signal Options

- **Explicit marker**: `[SEARCH_COMPLETE]` or `[SEARCH_DONE]`
- **Confidence threshold**: MemoryBot self-evaluates before returning
- **Main Bot approval**: Main Bot can ask follow-up questions to MemoryBot

#### When to Flush Context

- **Keyword/topic mismatch** between new query and existing findings
- **User changes subject** entirely (e.g., from "project details" to "weather")
- **Time-based**: MemoryBot context expires after N seconds

#### Multi-Turn MemoryBot (Optional)

For complex queries, allow Main Bot to have a brief back-and-forth:

```
Main: "Find info about user's database setup"
MemoryBot: "Found 3 memories about PostgreSQL configuration"
Main: "Also check if there's anything about backup procedures"
MemoryBot: "[SEARCH_COMPLETE] Found 1 memory about daily backups"
Main: "Done, thanks"
MemoryBot: "[SESSION_END]"
```

#### Design Decisions (Final)

| Decision | Choice |
|----------|--------|
| **Name** | MemoryBot (previously considered: memoryLiberian, sub_bot) |
| **Single vs Multiple** | One shared MemoryBot per session |
| **Synchronous vs Async** | Synchronous - Main Bot waits for response |
| **Fallback** | If MemoryBot unavailable, Main Bot calls memory tools directly |
| **MemoryBot memory** | TBD - Should MemoryBot remember search patterns? |

#### Planned Files

| File | Purpose |
|------|---------|
| `src/memory/memorybot.py` | MemoryBot core logic |
| `src/memory/memorybot_prompt.py` | System prompt templates |
| `src/discord_bot/message_handler.py` | Route memory queries to MemoryBot |
| `src/lm_models/api.py` | Support parallel/concurrent LM calls |

---

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

#### Sleep procedure Flow

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
| **Status** | ✅ Implemented in Schema |
| **Severity** | N/A (Feature concept, now part of schema) |
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

#### Importance Scoring Formula (Final)

```
importance = (update_count_normalized * 0.4) + (recency_score * 0.3) + (explicit_weight * 0.3)
```

Where:
- `update_count_normalized` = `min(update_count / max_expected_updates, 1.0)`
- `recency_score` = `max(0, 1 - days_since_update / max_days)`
- `explicit_weight` = user-set weight (defaults to 0.5)

#### Schema Implementation

Already included in `memories` table:
- `update_count` INTEGER DEFAULT 0
- `importance` REAL (0.0 - 1.0)
- `updated_at` TIMESTAMP

#### Benefits

- Frequently updated memories automatically get higher importance
- Helps pruning decisions (keep frequently modified memories)
- Provides signal for memory fusion (similar memories with high update counts)
- Enables search filtering by update frequency

---

## Memory Schema Evolution Notes

### Schema Version: 2.0 (2026-05-21)

**Key Design Decisions**:

1. **Multi-user memories**: `memory_users` junction table enables many-to-many relationship between memories and users, supporting conversations with multiple participants.

2. **Concise memory types** (5 types):
   - `fact` - Verified factual information
   - `preference` - User preferences
   - `context` - Temporary situational information
   - `relationship` - Connections between entities
   - `deprecated` - No longer valid information

3. **Importance dual-purpose**: Score used for both pruning priority and search relevance ranking.

4. **Memory lifecycle tracking**: `status` column tracks memory state transitions (active → deprecated/expired/superseded).

5. **Expiration-based validation**: `expires_at` column enables automatic validity checking of memories.

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
| 💡 Concept | Feature concept, pending refinement |