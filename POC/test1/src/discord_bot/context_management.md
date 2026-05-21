# Context Management System

## Overview

A set of tools and procedures that enable the Main Bot to manage conversation context efficiently:
1. **Session Start Context Initialization** — brief setup from recent channel activity
2. **Context Compression** — on-demand compression when conversation grows too long
3. **Channel Search** — foundation tool to fetch and filter recent channel messages

## Architecture

```
discord_bot/
├── context_management.md          # This file - design documentation
├── tools/
│   └── builtins/
│       ├── channel_search.py      # NEW: ChannelSearchTool
│       └── context_compressor.py  # NEW: ContextCompressor
└── bot_core.py                    # Modified: session start context init
└── message_handler.py             # Modified: context injection
```

---

## Feature 1: Channel Search Tool (Foundation) ✅ IMPLEMENTED

### Purpose
Fetch recent Discord channel messages with optional filtering and compression. Used by both Session Start Context and Context Compression.

### Tool Definition
```python
{
    "type": "function",
    "function": {
        "name": "channel_search",
        "description": "Search recent messages in a Discord channel to gather context for conversation. Returns a list of recent messages with author, content, timestamp, and reply info.",
        "parameters": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "Discord channel ID to search messages from"},
                "limit": {"type": "integer", "description": "Number of recent messages to fetch (default: 15, max: 50)", "default": 15},
                "search_query": {"type": "string", "description": "Optional text filter — only messages containing this text are returned"},
                "username": {"type": "string", "description": "Optional username filter — only messages from this specific user"},
                "compress_long": {"type": "boolean", "description": "If true, truncate messages longer than 200 characters with '...'", "default": true}
            },
            "required": ["channel_id"]
        }
    }
}
```

### Implementation
- **File**: `src/tools/builtins/channel_search.py`
- **Class**: `ChannelSearchTool`
- **Method**: `execute(messages, **kwargs)` — formats pre-fetched message data
- **Data Source**: `bot_core.py` → `get_channel_messages()` and `_fetch_channel_messages()` — async Discord API calls
- **Message Format**: Each message contains `{author, display_name, content, timestamp, is_reply, replied_to_author, replied_to_content, has_image}`

### Integration Path
```
LM Studio calls channel_search
    ↓
tool_executor._handle_channel_search()
    ↓
bot.get_channel_messages(channel_id, limit, search_query, username, compress_long)
    ↓
bot._fetch_channel_messages(channel_id, limit) — Discord API async call
    ↓
ChannelSearchTool.execute() formats result for LM Studio
```

### Key Behavior
- Skips bot's own messages (already in conversation history)
- Skips messages from other bots
- Long messages truncated to 200 chars + "..."
- Reply messages include the FULL referenced message (truncated to 100 chars)
- Image attachments detected and marked
- Optional keyword and username filtering
- Chronological order (oldest first)

---

## Feature 2: Session Start Context Initialization

### Purpose
Before starting a new session, generate a compact summary of recent channel activity. This tells the Main Bot "who is talking to whom and about what" without polluting the conversation context.

### When It Runs
```
@Bot hello (or reply to bot)
    ↓
[Session Start Procedure]
    1. ChannelSearchTool.search(channel_id, limit=15, compress_long=true)
    2. Generate LM-based context summary
    3. Inject summary as first user message in conversation history
    ↓
Normal session start continues
```

### Context Summary Format
```
[CHANNEL CONTEXT: Alice asked about weather earlier (resolved).
Bob and Carol discussed games (ongoing, not involving bot).
No active conversation with bot before this message.]
```

### Implementation
- **File**: `bot_core.py` → `_handle_new_session_message()` (modified)
- **Process**:
  1. Call ChannelSearchTool to fetch recent messages
  2. Send compressed messages to a quick LM call for summarization
  3. Inject summary into conversation history before current message

### LM-Generated Summary
- **System prompt**: "You are a conversation summarizer. Summarize who is talking to whom, what topics are discussed, and what is resolved vs ongoing."
- **Output format**: `[CHANNEL CONTEXT: <summary>]`
- **Max length**: ~300 characters
- **Trigger**: Always at session start (no decision needed)

---

## Feature 3: Context Compression Tool

### Purpose
Compress old conversation messages into a compact summary when the conversation is getting long. This frees up context space while preserving recent messages.

### When It Triggers

**Auto-trigger** (two conditions):
1. **Token consumption** exceeds 80% of `max_tokens`
2. **Message count** exceeds 20 messages in conversation history

**Manual trigger**:
- Main Bot decides when it "feels like it" (via LM judgment)
- Bot calls `context_compress` tool when conversation is getting long but subject doesn't need all the chitchat

### Tool Definition
```python
{
    "type": "function",
    "function": {
        "name": "context_compress",
        "description": "Compress old conversation messages into a compact summary to free context space.",
        "parameters": {
            "type": "object",
            "properties": {
                "compress_before_message_index": {"type": "integer", "description": "Compress messages before this index. Null=auto"},
                "target_summary_length": {"type": "integer", "description": "Max chars for summary. Default: 300"}
            }
        }
    }
}
```

### Implementation
- **File**: `src/tools/builtins/context_compressor.py`
- **Class**: `ContextCompressor`
- **Method**: `compress(messages, target_length=300)`
- **Returns**: `(summary_string, cutoff_index, recent_messages)`

### Compression Logic
```
Before: [msg1, msg2, msg3, ..., msg25]  (25 messages, ~8000 tokens)
    ↓
Keep last 6 messages fresh, compress the rest
    ↓
After: ["[CONTEXT: Alice and Bob discussed weather and games (resolved). Topic: general chat.]", msg20, msg21, msg22, msg23, msg24, msg25]
       (7 items, ~500 tokens)
```

### LM-Generated Summary
- **System prompt**: "You are a conversation summarizer. Output ONLY the summary, nothing else."
- **Input**: Old conversation messages (all except last 6)
- **Output format**: `[CONTEXT: <summary>]`
- **Max length**: Configurable (default 300 chars)

---

## Full Flow: Session Start to Compression

```
═══════════════════════════════════════════════════════
  PHASE 1: SESSION START
═══════════════════════════════════════════════════════

@Bot hello
    ↓
[1] ChannelSearchTool.search(channel_id, limit=15, compress_long=true)
    → Returns: [compressed recent messages from last 15 user messages]
    ↓
[2] LM generates context summary:
    Input: compressed messages
    Output: "[CHANNEL CONTEXT: Alice asked about weather (resolved). Bob and Carol discussed games (ongoing).]"
    ↓
[3] Build conversation history:
    [
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": "[CHANNEL CONTEXT: ...]"},       ← injected context
      {"role": "user", "content": "Alice says: hello"}            ← current message
    ]
    ↓
[4] Normal LM processing → Bot responds

═══════════════════════════════════════════════════════
  PHASE 2: ACTIVE SESSION (conversation grows)
═══════════════════════════════════════════════════════

User messages continue...
Conversation history grows: 5, 10, 15, 20, 25 messages...
    ↓
[Auto-trigger check after each response]
    Condition 1: Token count > 80% of max_tokens?
    Condition 2: Message count > 20?
    ↓
If triggered → Auto-compress

OR

Main Bot decides (via LM judgment): "conversation getting long"
    → Calls context_compress tool manually

═══════════════════════════════════════════════════════
  PHASE 3: CONTEXT COMPRESSION
═══════════════════════════════════════════════════════

[1] ContextCompressor.compress(messages, target_length=300)
    → Splits: old_messages (all except last 6) + recent_messages (last 6)
    → LM generates: "[CONTEXT: Alice and Bob discussed weather, games, and weekend plans. All topics resolved.]"
    → Returns: (summary, cutoff_index, recent_messages)
    ↓
[2] Rebuild conversation history:
    [
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": "[CONTEXT: ...]"},              ← compressed summary
      ... recent_messages (last 6) ...
    ]
    ↓
[3] Continue conversation with fresh context

═══════════════════════════════════════════════════════
  PHASE 4: SESSION END
═══════════════════════════════════════════════════════

end_session tool called OR timeout (600s)
    ↓
Session cleared, all context discarded
    ↓
Next session will repeat PHASE 1
```

---

## Open Questions — Resolved

| Question | Decision | Rationale |
|----------|----------|-----------|
| 1. Channel Search: sync or async? | To be determined during implementation | Discord.py's `history()` is async, but current architecture uses `run_in_executor`. Will evaluate during coding. |
| 2. Context Compression trigger? | **Token monitoring (>80%) + message count (>20) + bot judgment** | Three complementary signals: token threshold for efficiency, message count as simple heuristic, LM judgment for nuance |
| 3. Auto-trigger or bot-decided? | **Both** — auto-trigger on token/message thresholds, bot can also decide | Auto ensures reliability, bot judgment handles cases where thresholds aren't met but compression is still useful |
| 4. LM-generated or rule-based summary? | **LM-generated** | Too complex to make rule-based effectively. LM provides richer, more accurate summaries. |

---

## Configuration

```json
{
  "context_management": {
    "session_start": {
      "recent_messages_limit": 15,
      "message_truncate_length": 200,
      "summary_max_length": 300
    },
    "compression": {
      "token_threshold_percent": 80,
      "message_count_threshold": 20,
      "messages_to_keep_fresh": 6,
      "default_summary_length": 300
    }
  }
}
```

---

## Related Components

| Component | Relationship |
|-----------|-------------|
| `ChannelSearchTool` | Foundation — used by both Session Start and Compression |
| `ContextCompressor` | Depends on LM client for summarization |
| `SessionManager` | Provides session state (active/inactive) |
| `MessageHandler` | Orchestrates session start context injection |
| `MemoryBot` (future) | Will use similar patterns for memory search |

---

## Future Enhancements

1. **MemoryBot integration** — MemoryBot uses same search patterns for memory retrieval
2. **Per-channel compression thresholds** — Some channels may need different settings
3. **Compressed context export** — Save compressed summaries for analytics
4. **Smart message retention** — Keep important messages (images, tool results) uncompressed