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

### BUG-001: Bot Can't See Its Own Messages in channel_search

| Field | Value |
|-------|-------|
| **ID** | BUG-001 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | The `_fetch_channel_messages()` method in `bot_core.py` always filtered out the bot's own messages (`msg.author.id == bot_id`), preventing the LM from seeing the bot's own previous messages when calling `channel_search`. This limited context for conversation flow and reply chains. |
| **Root Cause** | The bot identity check was unconditional — every message from the bot was skipped regardless of whether the LM needed that context. |
| **Fix Applied** | 1. Removed the `msg.author.id == bot_id` check from `_fetch_channel_messages()` 2. Kept the `filter_bots` parameter for filtering OTHER bot messages (optional, default False) 3. Updated docstring to clarify: "bot's own messages are always included" |
| **Files Modified** | `src/discord_bot/bot_core.py` |


---

### FIX-MEMORY-001: memory_tool Not Registered in Tools System

| Field | Value |
|-------|-------|
| **ID** | FIX-MEMORY-001 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | Critical |
| **Description** | memory_tool was not registered in the tools system. `tool_executor.py` had no handlers for memory operations, so LM Studio could not call any memory functions. |
| **Root Cause** | The memory tool existed in `src/tools/builtins/memory_tool.py` but was never wired into the tool execution pipeline. `tool_executor.py` had no `memory_tool` case in its handler, and `bot_core.py` did not import or register it. |
| **Fix Applied** | 1. Added `memory_tool` case handlers in `tool_executor.py` for all operations (save, search, update, delete, list, summarize, clear) 2. Added `pop('operation')` from args before passing **args to `self.executor.execute()` to prevent duplicate kwarg error 3. Added memory_tool import and registration in `bot_core.py` |
| **Files Modified** | `src/discord_bot/tool_executor.py`, `src/discord_bot/bot_core.py`, `src/tools/builtins/__init__.py` |

---

### FIX-MEMORY-002: Default Memory Database Path Inconsistent

| Field | Value |
|-------|-------|
| **ID** | FIX-MEMORY-002 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | Low |
| **Description** | Default memory database path was `data/memory.db` which was inconsistent with the project structure. Changed to `user/data/memory/memory.db` for better organization. |
| **Fix Applied** | 1. Changed default in `memorylite.py` `__init__()` parameter 2. Changed default in `config.py` `memory_db_path` property and `get_memory_config()` 3. Updated `DEFAULT_MEMORY_DB_PATH` in `settings.js` |
| **Files Modified** | `src/memory/memorylite.py`, `src/config.py`, `src/static/lib/settings.js` |

---

### FIX-MEMORY-003: Status Message Now Requires LLM-Generated Text

| Field | Value |
|-------|-------|
| **ID** | FIX-MEMORY-003 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Description** | Removed hardcoded tool status message fallback. Status messages are now only sent when the LLM provides a custom `tell_user_you_are_working` message via tool call arguments. |
| **Fix Applied** | 1. `_should_send_status()` in `message_processor.py` now takes `custom_message` parameter and returns `True` only if non-None 2. System prompt in `message_handler.py` instructs LLM to always include `tell_user_you_are_working` argument with in-character status messages |
| **Files Modified** | `src/discord_bot/message_processor.py`, `src/discord_bot/message_handler.py` |

---

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
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Date Solved** | 2026-05-26 |
| **Description** | Build the central memory engine that coordinates all memory operations. |
| **Requirements** | 1. Memory create, read, update, delete operations 2. Memory recall with multiple strategies 3. Memory summarization triggers 4. Integration with LM Studio tool interface |
| **Implementation** | 1. `memory_manager.py` implements full CRUD operations via MemoryManager class 2. `memory_recall` uses similarity scoring and importance filtering 3. `memory_summarize` generates compact summaries of stored memories 4. `memory_create`, `memory_update`, `memory_delete` all implemented 5. Tool interface via `memory_tool.py` registered in tools system |

---

### REQ-003: LM Studio Tool Interface

| Field | Value |
|-------|-------|
| **ID** | REQ-003 |
| **Date** | 2026-05-21 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Date Solved** | 2026-05-26 |
| **Description** | Expose memory operations as LM Studio tools for the model to call. |
| **Requirements** | 1. `memory_recall` tool - search and retrieve memories 2. `memory_create` tool - store new memories 3. `memory_update` tool - modify existing memories 4. Tool definitions compatible with existing tools system |
| **Integration** | `src/discord_bot/bot_core.py` (tool registration) |
| **Implementation** | 1. `memory_tool.py` implements all memory operations as LM-callable tools 2. Registered in `bot_core.py` via `from src.tools.builtins.memory_tool import MemoryTool` 3. Tool definitions compatible with existing tools system 4. All operations wired through `tool_executor.py` |

---

### REQ-004: Discord Bot Integration

| Field | Value |
|-------|-------|
| **ID** | REQ-004 |
| **Date** | 2026-05-21 |
| **Status** | ✅ Solved |
| **Severity** | High |
| **Date Solved** | 2026-05-26 |
| **Description** | Integrate memory module with existing Discord bot modules. |
| **Requirements** | 1. Session lifecycle hooks (start, update, end) 2. Memory creation from conversation content 3. Memory recall before LM Studio calls 4. Per-server memory isolation |
| **Implementation** | 1. Added MemoryManager to bot_core.py with shared DB path 2. `_on_session_started()`: Injects wake-up memory into system prompt on new session 3. `_on_session_ended()`: Saves conversation summary to memory, updates wake-up memory 4. `_on_session_cleanup()`: Prunes low-importance memories on session cleanup 5. Wired hooks into `_handle_new_session_message()` and `clear_session()` 6. Memory save and pruning run as background tasks (non-blocking) |
| **Files Modified** | `src/discord_bot/bot_core.py` |

---

### REQ-005: Memory Summarization and Pruning

| Field | Value |
|-------|-------|
| **ID** | REQ-005 |
| **Date** | 2026-05-21 |
| **Status** | ✅ Solved |
| **Severity** | Medium |
| **Date Solved** | 2026-05-26 |
| **Description** | Implement memory summarization to prevent storage bloat and improve recall quality. |
| **Requirements** | 1. Importance scoring for memories 2. Automatic pruning of low-importance old memories 3. Memory fusion (combining related memories) 4. Configurable memory lifespan |
| **Implementation** | 1. `generate_sleep_summary()` called on session end to update wake-up memory 2. `prune()` method called on session cleanup to remove low-importance memories 3. Both run as background tasks (non-blocking) |
| **Files Modified** | `src/discord_bot/bot_core.py` |

---

## Feature Concepts (Pending Refinement)

### CONCEPT-003: MemoryBot Architecture

| Field | Value |
|-------|-------|
| **ID** | CONCEPT-003 |
| **Date** | 2026-05-21 |
| **Status** | ✅ Completed |
| **Severity** | Medium |
| **Date Completed** | 2026-05-26 |
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

#### Implementation Plan

**Phase 1: Core MemoryBot Class**

| Step | Task | File |
|------|------|------|
| 1 | Create `MemoryBot` class with isolated session management | `src/memory/memorybot.py` |
| 2 | Implement `search_memories(query, limit)` method | `src/memory/memorybot.py` |
| 3 | Implement `filter_results(results, query)` method | `src/memory/memorybot.py` |
| 4 | Implement `distill_results(findings)` method | `src/memory/memorybot.py` |
| 5 | Add `is_complete()` detection (confidence threshold) | `src/memory/memorybot.py` |

**Phase 2: System Prompt**

| Step | Task | File |
|------|------|------|
| 6 | Create memory bot system prompt template | `src/memory/memorybot_prompt.py` |
| 7 | Add completion signal detection (`[SEARCH_COMPLETE]`) | `src/memory/memorybot_prompt.py` |
| 8 | Add context flush logic (topic mismatch detection) | `src/memory/memorybot_prompt.py` |

**Phase 3: Integration**

| Step | Task | File |
|------|------|------|
| 9 | Add `MemoryBot` instance to `bot_core.py` | `src/discord_bot/bot_core.py` |
| 10 | Detect when LM needs memory search → route to MemoryBot | `src/discord_bot/message_handler.py` |
| 11 | Add `memory_search` tool that triggers MemoryBot | `src/tools/builtins/memory_tool.py` |
| 12 | Wire MemoryBot response parsing back to main conversation | `src/discord_bot/bot_core.py` |

**Phase 4: Optimization**

| Step | Task | File |
|------|------|------|
| 13 | Add topic tracking for context flush decisions | `src/memory/memorybot.py` |
| 14 | Implement multi-turn MemoryBot for complex queries | `src/memory/memorybot.py` |
| 15 | Add timeout-based context expiration | `src/memory/memorybot.py` |

#### System Prompt Template (Draft)

```
You are MemoryBot, a specialized memory search assistant.

YOUR JOB:
- Search the memory system for information relevant to the Main Bot's query
- Filter out irrelevant results
- Return only distilled, relevant findings

TOOLS AVAILABLE:
- memory_recall(query, limit): Search memories
- memory_search(channel, limit): Search channel messages

COMPLETION SIGNALS:
When you have sufficient findings, respond with:
  [SEARCH_COMPLETE] <2-3 sentence summary of relevant findings>

If no relevant memories exist:
  [NO_RELEVANT_MEMORIES]

CONTEXT FLUSH RULES:
- If the new query is about a completely different topic, flush your context
- If the user changes subject entirely, start fresh
- If more than 60 seconds have passed, flush context
```

#### Trigger Detection Strategy

| Scenario | Detection Method | Action |
|----------|-----------------|--------|
| LM calls `channel_search` with broad query | Tool call analysis | Route to MemoryBot |
| LM says "let me check my memory" | Intent detection in response | Route to MemoryBot |
| User asks "what do you remember about X" | Keyword detection | Route to MemoryBot |
| LM calls `memory_recall` directly | Tool call analysis | Route to MemoryBot |

#### Open Questions (Updated)

1. ~~Should MemoryBot be synchronous or asynchronous?~~ **Answer: Synchronous** (Main Bot waits)
2. Should MemoryBot have its own LM instance or share the main one? **Recommend: Share main LM instance** (simpler, avoids OOM)
3. What's the max search depth for MemoryBot? **Suggest: 3 tool calls max**
4. Should MemoryBot results be cached? **Recommend: Yes, for repeated queries**

#### Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| MemoryBot pollutes main context with noise | Medium | Strict completion signals, context flush |
| Extra LM calls increase latency | Medium | Cache results, limit search depth |
| Complex implementation adds bugs | Low | Start with simple version, iterate |
| MemoryBot competes with main bot for tokens | Low | Budget tokens separately |

---

### CONCEPT-001: Wake-Up Memory System

| Field | Value |
|-------|-------|
| **ID** | CONCEPT-001 |
| **Date** | 2026-05-21 |
| **Status** | ✅ Implemented |
| **Severity** | N/A (Feature concept) |
| **Date Solved** | 2026-05-26 |
| **Description** | Implement a "wake-up memory" system that persists context across sessions. After each session end, a "sleep procedure" updates the wake-up memory. This memory contains a compact summary of what should be remembered for the next sessions. |
| **Implementation** | 1. `MemoryManager.get_wake_up_memory(user_id)` retrieves per-user wake-up memory 2. `MemoryManager.generate_sleep_summary()` updates wake-up memory on session end 3. Content injected into system prompt before conversation starts 4. Truncated to ~500 chars for compactness 5. Wired into `_on_session_started()` and `_on_session_ended()` in bot_core.py |
| **Files Modified** | `src/discord_bot/bot_core.py` |

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