# Memory Module

## Overview

This module provides a comprehensive memory system for the Discord Bot + LM Studio Integration. It enables the bot to remember users, conversations, and context across sessions and servers.

## Current Implementation

| Component | File | Status |
|-----------|------|--------|
| Memory Manager | `memory_manager.py` | ✅ Basic implementation |
| Memory Lite | `memorylite.py` | ✅ SQLite integration |

## Purpose

The memory system transforms the Discord bot from a stateless conversational agent into a system with persistent knowledge about users, their preferences, conversation patterns, and shared context.

## Architecture

```
memory/
├── README.md                    # This file - module description
├── issues_tracker.md            # Issue tracking for memory module
├── progress.md                  # Implementation progress tracking
├── __init__.py                  # Package init
├── memory_manager.py            # Core memory management logic
├── memorybot.py                 # MemoryBot specialist (planned)
└── memorylite.py                # SQLite-based memory lite integration
```

## Database Schema

### `memories` Table

| Column | Type | Description |
|--------|------|-------------|
| `memory_id` | TEXT (PK) | Unique memory ID |
| `content` | TEXT | Memory content |
| `type` | TEXT | `fact` / `preference` / `context` / `relationship` / `deprecated` |
| `status` | TEXT | `active` / `deprecated` / `expired` / `superseded` |
| `importance` | REAL | Importance score (0.0 - 1.0) |
| `update_count` | INTEGER DEFAULT 0 | How many times memory was modified |
| `created_at` | TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | Last modification timestamp |
| `expires_at` | TIMESTAMP | Expiration/validity check timestamp |
| `superseded_by` | TEXT (FK) | Reference to replacement memory_id (NULL if none) |
| `source_session_id` | TEXT (FK) | Originating session |
| `metadata` | TEXT (JSON) | Additional structured data |

**Indexes**: `idx_memories_type`, `idx_memories_status`, `idx_memories_importance`, `idx_memories_update_count`, `idx_memories_expires_at`

### `memory_users` Table (Junction - Many-to-Many)

| Column | Type | Description |
|--------|------|-------------|
| `memory_id` | TEXT (FK) | Reference to memories |
| `user_id` | TEXT (FK) | Associated user |
| `role` | TEXT | `speaker` / `subject` / `observer` |

**Indexes**: `idx_memory_users_user_id`, `idx_memory_users_memory_id`

### `users` Table

| Column | Type | Description |
|--------|------|-------------|
| `user_id` | TEXT (PK) | Immutable Discord user ID |
| `username` | TEXT | Display username |
| `created_at` | TIMESTAMP | First seen |
| `last_active` | TIMESTAMP | Last interaction |

### `sessions` Table

| Column | Type | Description |
|--------|------|-------------|
| `session_id` | TEXT (PK) | Unique session ID |
| `user_id` | TEXT (FK) | Associated user |
| `guild_id` | TEXT | Discord server |
| `channel_id` | TEXT | Discord channel |
| `started_at` | TIMESTAMP | Session start |
| `ended_at` | TIMESTAMP | Session end |
| `topic` | TEXT | Conversation topic |
| `status` | TEXT | `active` / `ended` / `timeout` |

### `wake_up_memory` Table

| Column | Type | Description |
|--------|------|-------------|
| `memory_type` | TEXT (PK) | `'general'` or `'user:<user_id>'` |
| `content` | TEXT | Compact summary (~500 chars max) |
| `last_updated` | TIMESTAMP | Last rewritten |
| `version` | INTEGER | Revision counter |

## Memory Types

| Type | Description | Example |
|------|-------------|---------|
| **`fact`** | Verified factual information about a user or entity | "User's name is Guzu", "User uses Linux" |
| **`preference`** | User's stated or strongly implied preferences | "User prefers Python", "User likes dark mode" |
| **`context`** | Temporary or situational information with limited lifespan | "User is currently working on a Discord bot" |
| **`relationship`** | Connections between users, entities, or groups | "User and Picatchu are collaborators" |
| **`deprecated`** | Previously held but no longer valid information | "User lived in NYC (2020-2023)" |

## Importance Score

The importance score serves **two purposes**:

1. **Pruning** (Low importance = prune first when storage grows)
2. **Search** (High importance = more relevant/stable knowledge, returned first)

### Formula

```
importance = (update_count_normalized * 0.4) + (recency_score * 0.3) + (explicit_weight * 0.3)
```

Where each component is clamped to 0-1 range:
- `update_count_normalized` = `min(update_count / max_expected_updates, 1.0)` — how often memory was refined
- `recency_score` = `max(0, 1 - days_since_update / max_days)` — freshness factor
- `explicit_weight` = User-set weight (defaults to 0.5)

### Search Usage

Filter high-frequency memories:
```sql
WHERE update_count >= (SELECT MAX(update_count) FROM memories) - 3
```

## Memory Lifecycle

```
active → deprecated (when content is corrected)
active → expired (when expires_at is reached and re-validation fails)
active → superseded (when replaced by a better memory)
```

## Configuration

```json
{
  "memory": {
    "enabled": true,
    "storage_type": "sqlite",
    "max_memories_per_user": 1000,
    "memory_lifespan_days": 30
  }
}
```

## Current Integration Points

| Module | Integration |
|--------|-------------|
| `src/discord_bot/session_manager.py` | Session lifecycle hooks |
| `src/tools/builtins/memory_tool.py` | Memory tool for LM Studio |
| `src/discord_bot/bot_core.py` | Bot core integration |

## MemoryBot Architecture (Planned)

### Concept

MemoryBot is a specialized sub-bot with a fresh isolated context that handles memory search operations, protecting the main conversation context from being saturated with irrelevant memory results.

### Architecture Diagram

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

### MemoryBot Lifecycle

1. **Activation**: Triggered when Main Bot needs memory information
2. **Session**: Fresh context, calls memory tools, gets polluted with irrelevant results
3. **Completion**: MemoryBot signals "job done" when search is complete
4. **Termination**: On new prompt, MemoryBot decides if existing context is relevant
5. **Flush & Restart**: If irrelevant, MemoryBot clears context and starts fresh

### Communication Protocol (Shared Memory)

```
Main Bot writes: {query, priority, session_id}
MemoryBot reads → searches → writes: {findings, confidence, completed}
Main Bot reads findings → continues conversation
```

### MemoryBot System Prompt Template

```
You are MemoryBot, a specialized memory search assistant.
Your job: Find relevant memories for the Main Bot's query.
Tools available: memory_recall, memory_create, memory_update

When you have sufficient relevant findings, respond with:
[SEARCH_COMPLETE] <summary of findings>

If no relevant memories exist, respond with:
[NO_RELEVANT_MEMORIES]
```

### Completion Signal Options

- **Explicit marker**: `[SEARCH_COMPLETE]` or `[SEARCH_DONE]`
- **Confidence threshold**: MemoryBot self-evaluates before returning
- **Main Bot approval**: Main Bot can ask follow-up questions to MemoryBot

### When to Flush Context

- **Keyword/topic mismatch** between new query and existing findings
- **User changes subject** entirely (e.g., from "project details" to "weather")
- **Time-based**: MemoryBot context expires after N seconds

### Multi-Turn MemoryBot (Optional)

For complex queries, allow Main Bot to have a brief back-and-forth:

```
Main: "Find info about user's database setup"
MemoryBot: "Found 3 memories about PostgreSQL configuration"
Main: "Also check if there's anything about backup procedures"
MemoryBot: "[SEARCH_COMPLETE] Found 1 memory about daily backups"
Main: "Done, thanks"
MemoryBot: "[SESSION_END]"
```

### Design Decisions

- **Name**: "MemoryBot" (concise, previously considered: memoryLiberian, sub_bot)
- **Single vs Multiple**: One shared MemoryBot per session
- **Synchronous**: Main Bot waits for MemoryBot response
- **Fallback**: If MemoryBot unavailable, Main Bot calls memory tools directly
- **MemoryBot memory**: Should MemoryBot remember its own search patterns?

### Planned Files

| File | Purpose |
|------|---------|
| `src/memory/memorybot.py` | MemoryBot core logic |
| `src/memory/memorybot_prompt.py` | System prompt templates |
| `src/discord_bot/message_handler.py` | Route memory queries to MemoryBot |
| `src/lm_models/api.py` | Support parallel/concurrent LM calls |

## Planned Evolution

This module will evolve to include:
- Advanced memory recall strategies
- LM Studio tool calling interface for memory operations
- Memory summarization and pruning
- Per-server memory isolation
- User preference learning
- **MemoryBot specialist architecture**

## Future Enhancements

- Vector embedding for semantic memory search
- Cross-user memory (group preferences)
- Memory visualization in web UI
- Memory analytics (conversation patterns)
- Export to JSON/CSV for backup