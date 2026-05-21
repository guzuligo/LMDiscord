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
└── memorylite.py                # SQLite-based memory lite integration
```

## Planned Evolution

This module will evolve to include:
- Advanced memory recall strategies
- LM Studio tool calling interface for memory operations
- Memory summarization and pruning
- Per-server memory isolation
- User preference learning

## Current Integration Points

| Module | Integration |
|--------|-------------|
| `src/discord_bot/session_manager.py` | Session lifecycle hooks |
| `src/tools/builtins/memory_tool.py` | Memory tool for LM Studio |
| `src/discord_bot/bot_core.py` | Bot core integration |

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

## Data Model (Planned)

### Memory
| Field | Type | Description |
|-------|------|-------------|
| memory_id | TEXT (PK) | Unique memory ID |
| user_id | TEXT (FK) | Associated user |
| channel_id | TEXT | Associated channel |
| guild_id | TEXT | Associated server |
| content | TEXT | Memory content |
| type | TEXT | Memory type (fact, preference, event, etc.) |
| importance | REAL | Importance score (0-1) |
| created_at | TIMESTAMP | Creation timestamp |
| expires_at | TIMESTAMP | Expiration timestamp |

## Memory Types

| Type | Description | Example |
|------|-------------|---------|
| **fact** | Factual information | "User's name is Guzu" |
| **preference** | User preferences | "User prefers Python" |
| **event** | Notable events | "User completed task" |
| **context** | Conversation context | "User was asking about setup" |
| **relationship** | User relationships | "User knows Picatchu" |

## Future Enhancements

- Vector embedding for semantic memory search
- Cross-user memory (group preferences)
- Memory visualization in web UI
- Memory analytics (conversation patterns)
- Export to JSON/CSV for backup