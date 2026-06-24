# Context Management System

## Overview

A set of tools and procedures that enable the Main Bot to manage conversation context efficiently:
1. **Session Start Context Initialization** — brief setup from recent channel activity
2. **Context Compression** — on-demand compression when conversation grows too long
3. **Channel Search** — foundation tool to fetch and filter recent channel messages
4. **Mini-Context Handover** — check for pending messages between tool calls during multi-tool execution
5. **Tool Call Deduplication** — prevent redundant tool executions using hash-based caching
6. **Delay Processing** — configurable timing between message events to avoid rate limits
7. **Message Hash Tracking** — SHA256-based duplicate detection for incoming messages

## Architecture

```
discord_bot/
├── context_management.md          # This file - design documentation
├── tools/
│   └── builtins/
│       ├── channel_search.py      # ChannelSearchTool
└── bot_core.py                    # Session management, processing lock
└── message_handler.py             # Session routing, interruption handling
└── message_processor.py           # Tool call processing, check_pending callback
└── tool_executor.py               # Inter-tool-call queue checking
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

---

## Feature 4: Mini-Context Handover Between Tool Calls

### Problem Statement

When the LM Studio model returns multiple tool calls in a single response, the bot executes them sequentially in a "mini-context" without checking for new user messages between each tool call. This means:

1. User sends "search for recent announcements" → bot starts mini-context
2. Bot executes tool 1 of 3 (e.g., channel_search)
3. User sends "wait, actually search for errors not announcements" while bot is working
4. Bot finishes tool 1, tool 2, tool 3 without noticing the correction
5. Bot posts its (now outdated) response, then processes the queued messages

This creates a poor user experience where the bot seems "deaf" during multi-tool operations and can't respond to corrections.

### Single-Bot Constraint

**Important**: This bot runs on consumer hardware with GPU limitations. Only ONE bot session can run at a time. When the bot is working on a task, new messages from users are queued and processed sequentially after the current task completes.

The mini-context handover feature allows the bot to temporarily pause its current task to check for new messages between tool calls, without starting a second bot session.

### Pending Message Check During Multi-Tool Processing

During multi-tool execution, a pending message check occurs **between each tool call** to detect if the user has sent a new message. This ensures the bot can respond to user corrections or cancellations without completing all queued tool calls.

**Check Flow:**
```
[1] Execute tool 1 (e.g., channel_search)
    ↓
[2] Check pending messages (message hash comparison)
    ├─ Hash unchanged → Continue to tool 2
    └─ Hash changed → Cancel remaining tools, start new processing cycle
```

**Implementation Details:**
- Pending messages tracked via `message_hash` change detection
- `_pending_messages` dict stores hashes of already-processed messages
- If user sends a new message (detected via message hash change), remaining tool calls are cancelled
- A new processing cycle starts with the new message immediately
- This prevents the bot from completing outdated tool calls after the user has changed their request

**Example Scenario:**
```
User: "Search for recent announcements"
  -> Bot starts: [channel_search(announcements), channel_search(results), image_describe]

[1] Execute channel_search(announcements) -> Found 5 results
    ↓
[2] Check pending -> User sent: "Actually search for errors"
    ↓
[3] Cancel remaining tools (channel_search, image_describe)
    ↓
[4] Start new processing cycle with "Actually search for errors"
```

### Solution: Mini-Context Handover

After each tool call completes, check the `_pending_messages` queue before proceeding to the next tool call. If a new message exists, temporarily pause (hand over from) the mini-context and process the new message immediately.

### Handover Behavior

When a pending message is detected during mini-context execution:

1. **Mini-context pauses**: The current tool execution sequence stops
2. **Main bot takes over**: Checks the pending message
3. **User intent evaluation**:
   - **Simple reply needed**: Bot replies to user, then resumes mini-context with remaining tools
   - **Behavior change needed**: Bot instructs mini-context to adjust (e.g., "search for errors instead of announcements")
   - **Cancellation needed**: Bot cancels mini-context entirely and handles the new request

### Architecture

```
discord_bot/
├── bot_core.py                    # Handle interruption result (new session)
├── message_handler.py             # Propagate interruption for new session
├── message_processor.py           # Pass check_pending callback (new session)
└── tool_executor.py               # Check queue between tool calls
```

### Implementation Status

#### 1. `ToolCallHandler.process_tool_calls()` (tool_executor.py) ✅ IMPLEMENTED

Has `check_pending` callback parameter. After each tool call completes (except the last), calls this callback:

```python
async def process_tool_calls(
    self,
    tool_calls: List[Dict],
    messages_for_lm: List[Dict],
    channel,
    turn: int,
    safe_downloader: Any = None,
    make_lm_call_func: Optional[Callable] = None,
    get_bot_instance: Optional[Callable] = None,
    check_pending: Optional[Callable] = None
) -> Any:
    for i, tool_call in enumerate(tool_calls):
        # ... execute tool call ...
        
        # Check pending messages before next tool call (except last)
        if check_pending and i < len(tool_calls) - 1:
            pending = await check_pending()
            if pending:
                logger.info(f"Pending message detected during tool {i+1}/{len(tool_calls)}, interrupting")
                return {"interrupted": True, "pending_message": pending}
```

#### 2. `ToolCallHandler.process_tool_calls_active()` (tool_executor.py) ✅ IMPLEMENTED

Same approach for active session tool processing:

```python
async def process_tool_calls_active(
    self,
    tool_calls: List[Dict],
    messages_for_lm: List[Dict],
    turn: int,
    safe_downloader: Any = None,
    make_lm_call_func: Optional[Callable] = None,
    get_bot_instance: Optional[Callable] = None,
    check_pending: Optional[Callable] = None
) -> Optional[Dict]:
    for i, tool_call in enumerate(tool_calls):
        # ... execute tool call ...
        
        # Check pending messages before next tool call (except last)
        if check_pending and i < len(tool_calls) - 1:
            pending = await check_pending()
            if pending:
                logger.info(f"Pending message detected during active session tool {i+1}/{len(tool_calls)}, interrupting")
                return {"interrupted": True, "pending_message": pending}
```

#### 3. `message_processor.py` — Pass the callback

**Active session** (`process_active_session()`): ✅ ALREADY IMPLEMENTED
```python
# Already passes check_pending to process_tool_calls_active:
end_session_result = await self._tool_call_handler.process_tool_calls_active(
    tool_calls, messages_for_lm, turn,
    self._safe_downloader,
    make_lm_call_func=lambda ctx, **kw: self._lm_caller.call(ctx, **kw),
    get_bot_instance=lambda: self._bot_instance,
    check_pending=lambda: self.check_pending_messages(channel_id)
)
```

**New session** (`_process_session()`): ⚠️ NEEDS IMPLEMENTATION
```python
# NEEDS TO ADD check_pending to process_tool_calls call:
response_text = await self._tool_call_handler.process_tool_calls(
    tool_calls, messages_for_lm, channel, turn,
    self._safe_downloader,
    make_lm_call_func=lambda ctx, **kw: self._lm_caller.call(ctx, **kw),
    get_bot_instance=lambda: self._bot_instance,
    check_pending=lambda: self.check_pending_messages(channel_id)  # ← ADD THIS
)
```

#### 4. `bot_core.py` — Handle interruption result

**Active session** (`_process_active_session_batch()`): ✅ ALREADY IMPLEMENTED
```python
# Already handles interruption for active sessions:
if isinstance(result, dict) and result.get("interrupted", False):
    pending_msg = result.get("pending_message")
    if pending_msg:
        logger.info(f"Active session interrupted by pending message")
        self._processing_lock[channel_id] = False
        await self._process_active_session_batch(message, pending_msg["content"], ...)
        return
```

**New session** (`_handle_new_session_message()`): ⚠️ NEEDS IMPLEMENTATION
```python
# NEEDS TO HANDLE interruption result from message_handler
```

### Flow Diagram

```
═══════════════════════════════════════════════════════════
  MINI-CONTEXT EXECUTION WITH HANDOVER
═══════════════════════════════════════════════════════════

User: "Search for recent announcements"
  → Bot starts mini-context: [channel_search, channel_search, image_describe]

[1] Execute channel_search (results: announcements found)
    ↓
[2] Check pending messages queue
    ├─ Empty → Continue to next tool (mini-context continues)
    └─ Has message → HANDOVER to main bot

═══════════════════════════════════════════════════════════
  HANDOVER SCENARIOS
═══════════════════════════════════════════════════════════

Scenario A: Simple reply needed
    ↓
[1] Main bot replies: "Found 3 announcements, let me describe one..."
    ↓
[2] Mini-context resumes: Continue with image_describe
    ↓
[3] Bot completes task

Scenario B: Behavior change needed
    ↓
[1] User: "Actually search for errors, not announcements"
    ↓
[2] Main bot: "Updating search criteria..."
    ↓
[3] Mini-context resumes with updated parameters
    ↓
[4] Bot completes task with new criteria

Scenario C: Cancellation needed
    ↓
[1] User: "Stop, I found it myself"
    ↓
[2] Main bot: "Alright, let me know if you need anything!"
    ↓
[3] Mini-context cancelled, remaining tools skipped

═══════════════════════════════════════════════════════════
  NO HANDOVER (No pending messages)
═══════════════════════════════════════════════════════════

[1] Execute channel_search
    ↓
[2] Check pending → Empty
    ↓
[3] Execute channel_search
    ↓
[4] Check pending → Empty
    ↓
[5] Execute image_describe
    ↓
[6] No more tools → Continue to next LM turn
    ↓
[7] Bot responds to user
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Check between tools, not during | Tool execution is atomic; checking mid-execution would require complex state management |
| Single bot session | Only one bot runs at a time due to GPU constraints; handover reuses the same session |
| Use existing `check_pending_messages()` | Reuses existing mechanism; no new queue management needed |
| Only check between tools (not last) | No point checking after the last tool since there's nothing to cancel |
| Mini-context pauses, not restarts | When handover completes, mini-context resumes where it left off |

### Edge Cases Handled

1. **Session expired during tool execution** — `check_pending_messages()` already checks `bot._session_manager.is_active(channel_id)` and clears expired sessions
2. **Multiple messages queued** — First pending message is processed immediately; remaining messages are handled by `_process_queued_pending_messages()`
3. **Bot's own message** — `check_pending_messages()` returns only non-bot messages (filtered at queue time)
4. **Tool call failure** — Failed tool turns are tracked separately; interruption takes priority
5. **Handover with no pending** — If no pending messages, mini-context continues normally (no overhead)

### Testing Checklist

- [ ] Multi-tool call: User sends message during tool execution → bot interrupts and processes new message
- [ ] Multi-tool call: No new messages → bot completes all tools normally (no handover)
- [ ] Active session: Interruption clears lock and processes pending message
- [ ] New session: Interruption handled correctly (NEEDS IMPLEMENTATION)
- [ ] Multiple queued messages: First processed immediately, rest queued
- [ ] Session expired during tool execution: Expired session handled correctly
- [ ] Handover with reply only: Bot replies and resumes mini-context
- [ ] Handover with cancellation: Bot cancels mini-context and handles new request

---

---

## Feature 5: Tool Call Deduplication

### Purpose
Prevent redundant execution of identical tool calls by caching results using content-based hashing. This is especially important for `channel_search` tool calls, where the LM model may return duplicate or near-duplicate search requests.

### Hash-Based Deduplication System

The deduplication system uses SHA256 hashing to uniquely identify tool calls and cache their results.

###  _is_duplicate_tool_call() Method

```python
def _is_duplicate_tool_call(self, tool_name, tool_arguments):
    # Create unique key from tool name and arguments
    key_data = json.dumps({"tool": tool_name, "args": tool_arguments}, sort_keys=True)
    tool_hash = hashlib.sha256(key_data.encode()).hexdigest()

    # Check if we have a cached result
    if tool_hash in self._tool_cache:
        return True
    return False
```

**Key Generation:**
- Combines tool name and arguments into a structured dictionary
- Serializes to JSON with sorted keys for consistent hashing
- Generates SHA256 hash of the serialized string
- Same tool name + same arguments = same hash = duplicate detected

#### _cache_tool_result() Method

```python
def _cache_tool_result(self, tool_name, tool_arguments, result, ttl=300):
    key_data = json.dumps({"tool": tool_name, "args": tool_arguments}, sort_keys=True)
    tool_hash = hashlib.sha256(key_data.encode()).hexdigest()

    self._tool_cache[tool_hash] = {
        "result": result,
        "timestamp": time.time(),
        "ttl": ttl,
        "tool_name": tool_name,
        "arguments": tool_arguments
    }
```

**Cache Entry Structure:**
| Field | Type | Description |
|-------|------|-------------|
| result | Dict | The cached tool execution result |
| timestamp | float | Unix timestamp when result was cached |
| ttl | int | Time-to-live in seconds (default: 300 = 5 minutes) |
| tool_name | str | Original tool name for logging |
| arguments | Dict | Original tool arguments for debugging |

**TTL Expiration:**
- Cached results expire after 5 minutes by default
- Expired entries are cleaned up on access
- Cache eviction: _cleanup_expired_cache() removes expired entries

### Application to channel_search Tool

The deduplication system is specifically applied to `channel_search` tool calls:

**Use Case 1: Duplicate Search Requests**
```
User: "Search for announcements in #general"
  -> Bot calls: channel_search(channel_id="123", search_query="announcements", channel="general")
  -> Result cached with hash H1

User: "Search for announcements in #general" (same request)
  -> Bot detects duplicate via hash H1
  -> Returns cached result instead of executing tool again
```

**Use Case 2: LM Model Redundancy**
```
LM returns multiple identical tool calls:
  [channel_search(...), channel_search(...), channel_search(...)]

  [1] First call: Executes tool, caches result
  [2] Second call: Duplicate detected, returns cached result
  [3] Third call: Duplicate detected, returns cached result
```

### Deduplication Flow

```
Tool Call Received
    |
_is_duplicate_tool_call(tool_name, arguments)
    |
SHA256 Hash Generation
    |
Check _tool_cache for existing hash
    |-> Hash exists -> Return cached result (NO tool execution)
    |-> Hash not found -> Execute tool
                            |
                    _cache_tool_result(tool_name, arguments, result)
                            |
                    Return result to caller
```

### Configuration

```json
{
  "tool_call_deduplication": {
    "enabled": true,
    "default_ttl_seconds": 300,
    "max_cache_size": 100,
    "applied_to_tools": ["channel_search"]
  }
}
```

### Benefits
1. **Reduced API calls** - Avoids redundant Discord API requests
2. **Faster response times** - Cached results returned immediately
3. **Consistent responses** - Same query always returns same result within TTL
4. **Lower server load** - Reduces overall system workload

---

## Feature 6: Delay Processing

### Purpose
Manage configurable delays between message events to prevent Discord API rate limiting and create more natural interaction timing. The delay processor coordinates the sequence of sending typing indicators, response messages, and message deletion.

### delay_processor.py Module

The delay processor provides timed sequencing for message lifecycle events.

#### DelayTask Dataclass

```python
@dataclass
class DelayTask:
    channel_id: str
    message_id: Optional[str]
    event_type: str
    timestamp: float
```

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| channel_id | str | Target Discord channel |
| message_id | Optional[str] | Associated message ID (None for typing events) |
| event_type | str | Event type: typing, response, delete |
| timestamp | float | Execution timestamp (time.time() + delay) |

#### Configurable Delay Durations

Default delay durations between message events:

| Event | Default Duration | Description |
|-------|-----------------|-------------|
| typing | 1 second | Delay before sending typing indicator |
| response | 2 seconds | Delay before sending response message |
| delete | 3 seconds | Delay before deleting the response message |

**Configuration Example:**
```json
{
  "delay_processing": {
    "durations": {
      "typing": 1,
      "response": 2,
      "delete": 3
    },
    "enabled": true
  }
}
```

**Customization:** Durations are configurable via configuration file or environment variables.

#### DelayProcessor Class

```python
class DelayProcessor:
    def __init__(self, bot_instance):
        self._bot = bot_instance
        self._pending_tasks = defaultdict(list)
        self._channel_rate_limits = defaultdict(float)

    async def schedule_event(self, channel_id, event_type, message_id=None, delay=None):
        ...

    async def _process_queue(self, channel_id):
        ...
```

#### Per-Channel Rate Limiting

Discord API enforces rate limits per channel. The delay processor tracks rate limits per channel to avoid exceeding these limits.

**Rate Limit Behavior:**
- Each channel has independent rate limit tracking
- Minimum interval between events enforced automatically
- Tasks queued if rate limit would be exceeded
- Automatic retry when rate limit window expires

#### Message Lifecycle with Delays

```
Bot decides to respond
    |
[1] Schedule typing event (delay: 1s)
    |
[2] Send typing indicator
    |
[3] Schedule response event (delay: 2s)
    |
[4] Send response message
    |
[5] Schedule delete event (delay: 3s)
    |
[6] Delete response message
    |
Complete
```

**Total Timeline Example:**
```
T+0s: Bot decides to respond
T+1s: Typing indicator sent
T+3s: Response message sent (1s + 2s)
T+6s: Response message deleted (1s + 2s + 3s)
```

### Integration with Message Handler

The delay processor integrates with the message handler to coordinate bot responses.

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Per-channel rate limiting | Discord API limits are per-channel; isolating tracking prevents false positives |
| Configurable delays | Different use cases may need different timing |
| DelayTask dataclass | Clean, type-safe representation of delayed events |
| Async processing | Non-blocking delay execution does not interfere with message processing |

---

## Feature 7: Message Hash Tracking

### Purpose
Prevent duplicate processing of the same message using SHA256 content hashing. This ensures each Discord message is processed exactly once, even if received multiple times due to network retries or gateway events.

### SHA256 Hash-Based Duplicate Detection

Every incoming message content is hashed using SHA256 to create a unique identifier for duplicate detection.

#### Message Hash Generation

```python
import hashlib

def generate_message_hash(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
```

**Properties:**
- Same content -> Same hash (deterministic)
- Different content -> Different hash (collision-resistant)
- Fixed-length output (64 hex characters)
- Content-agnostic (works for any message type)

#### Pending Messages Tracking

The `_pending_messages` dictionary tracks message hashes to prevent duplicate processing:

```python
self._pending_messages = {}

class MessageMetadata:
    def __init__(self, message_id, content_hash, timestamp):
        self.message_id = message_id
        self.content_hash = content_hash
        self.timestamp = timestamp
        self.processed = False
```

**Tracking Structure:**
| Field | Type | Description |
|-------|------|-------------|
| message_id | str | Discord message ID |
| content_hash | str | SHA256 hash of message content |
| timestamp | float | When message was first received |
| processed | bool | Whether message has been fully processed |

#### Duplicate Detection Flow

```
Incoming Message Received
    |
Generate content_hash = SHA256(message_content)
    |
Check _pending_messages for content_hash
    |-> Hash exists + Not processed -> Queue for reprocessing
    |-> Hash exists + Processed -> Skip (duplicate detected)
    |-> Hash not found -> Process normally
                            |
                    Add to _pending_messages with content_hash
                            |
                    Mark processed = True when complete
```

#### Implementation Example

```python
async def handle_message(self, message):
    content_hash = generate_message_hash(message.content)

    if content_hash in self._pending_messages:
        existing = self._pending_messages[content_hash]
        if existing.processed:
            return  # Skip duplicate
        self._queue_message(message, content_hash)
        return

    self._pending_messages[content_hash] = MessageMetadata(
        message_id=message.id,
        content_hash=content_hash,
        timestamp=time.time()
    )

    await self._process_message(message, content_hash)
```

### Integration with Pending Message Check

Message hash tracking works in conjunction with the pending message check feature:

```
Multi-Tool Processing
    |
After each tool call: check_pending_messages()
    |
Compare current message_hash with _pending_messages
    |-> Hash changed -> User sent new message, interrupt
    |-> Hash unchanged -> Continue processing
```

### Cache Cleanup

Expired message hashes are periodically cleaned up to prevent memory leaks:

```python
def cleanup_old_hashes(self, max_age=3600):
    now = time.time()
    to_remove = [
        h for h, meta in self._pending_messages.items()
        if now - meta.timestamp > max_age
    ]
    for h in to_remove:
        del self._pending_messages[h]
```

### Key Benefits

1. **Network retry resilience** - Duplicate messages from retries are ignored
2. **Gateway event deduplication** - Discord gateway may send same message twice
3. **Memory efficient** - Old hashes cleaned up automatically
4. **Content-based** - Works regardless of message source or channel

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
  },
  "tool_call_deduplication": {
    "enabled": true,
    "default_ttl_seconds": 300,
    "max_cache_size": 100,
    "applied_to_tools": ["channel_search"]
  },
  "delay_processing": {
    "durations": {
      "typing": 1,
      "response": 2,
      "delete": 3
    },
    "enabled": true
  }
}
```

---

## Known Issues

### BUG-014 (channel_id): LM Passes Channel Name Instead of Numeric ID
| Field | Value |
|-------|-------|
| **ID** | BUG-014 (channel_id) |
| **Status** | 📋 Confirmed — Root Cause Identified |
| **Severity** | High |
| **Description** | The LM Studio model passes channel names ("this", "general") as `channel_id` parameter instead of actual Discord channel ID numbers. Discord API requires numeric channel IDs. |
| **Log Evidence** | ```channel_search called with channel_id='this' → Channel not found: 'this' (expected numeric channel ID)``` |
| **Proposed Fix** | 1. Update tool schema description to explicitly state "channel_id must be a numeric Discord channel ID (e.g., 123456789012345678), NOT a channel name". 2. Add a `channel_name` parameter that accepts channel names and resolves them to IDs internally. |
| **Files To Modify** | `channel_search.py` (tool schema + description) |

---

## Related Components

| Component | Relationship |
|-----------|-------------|
| `ChannelSearchTool` | Foundation — used by both Session Start and Compression |
| `ContextCompressor` | Depends on LM client for summarization |
| `SessionManager` | Provides session state (active/inactive) |
| `MessageHandler` | Orchestrates session start context injection |
| `ToolCallHandler` | Inter-tool-call queue checking for mini-context handover |
| `DelayProcessor` | Manages timed message events with per-channel rate limiting |
| `MessageHashTracker` | SHA256-based duplicate detection for incoming messages |

---

## Future Enhancements

1. **MemoryBot integration** — MemoryBot uses same search patterns for memory retrieval
2. **Per-channel compression thresholds** — Some channels may need different settings
3. **Compressed context export** — Save compressed summaries for analytics
4. **Smart message retention** — Keep important messages (images, tool results) uncompressed
5. **Multi-bot support** — Allow multiple concurrent bot sessions on high-end GPUs