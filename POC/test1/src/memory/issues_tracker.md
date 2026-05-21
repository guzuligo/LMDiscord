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