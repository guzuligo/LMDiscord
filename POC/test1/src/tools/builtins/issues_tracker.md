# Channel Search Issues Tracker

## Known Limitations & Planned Enhancements

### BUG-015: Channel Search 50-Message Limit is Restrictive (Planned Enhancement)

| Field | Value |
|-------|-------|
| **ID** | BUG-015 |
| **Date** | 2026-05-26 |
| **Status** | 📋 Documented, Enhancement Planned |
| **Severity** | Medium |
| **Description** | The `channel_search` tool currently fetches at most 50 messages per channel. If the content the LM is looking for is older than the 50 most recent messages, it gets nothing. The LM has no way to "look further back" in the channel history. |
| **Current Behavior** | `limit` parameter capped at 50. If the search target is beyond the 50 most recent messages, no results are returned. |
| **Desired Behavior** | Implement a sliding window approach that allows the LM to skip past recent messages and fetch older ones. |

---

### CONCEPT-004: Channel Search Sliding Window (Planned Enhancement)

| Field | Value |
|-------|-------|
| **ID** | CONCEPT-004 |
| **Date** | 2026-05-26 |
| **Status** | 📋 Documented, Enhancement Planned |
| **Severity** | Low |
| **Description** | Add sliding window support to `channel_search` so the LM can fetch non-contiguous message windows from different points in channel history. This allows the LM to efficiently search through older messages without being limited to the 50 most recent. |
| **Proposed Parameters** | **`offset`** (integer, default 0): Number of most recent messages to skip before fetching. **`windows`** (integer, default 1, max 5): Number of non-contiguous windows to fetch. Each window is `limit` messages, separated by `limit` skipped messages. |
| **Example Usage** | `channel_search(channel="this", offset=50, limit=50)` → Skips messages 1-50, fetches 51-100. `channel_search(channel="this", offset=0, limit=20, windows=3)` → Window 1: messages 1-20, Window 2: messages 71-90, Window 3: messages 141-160. |
| **Result Format** | Results grouped by window with headers: `[Window 1: Messages 1-20]`, `[Window 2: Messages 71-90]`, etc. |
| **Design Decisions** | 1. **Max windows = 5**: Prevents excessive API calls (5 × 50 = 250 messages max per channel). 2. **Non-contiguous windows**: Each window is separated by `limit` skipped messages, creating a "skip pattern" that lets the LM jump through history efficiently. 3. **Backward compatibility**: `offset=0, windows=1` (defaults) preserves current behavior. 4. **Discord.py compatibility**: Uses `after` parameter with message objects to skip N messages from history. |
| **Files To Modify** | `src/tools/builtins/channel_search.py` (tool schema + description), `src/discord_bot/bot_core.py` (message fetching with offset/windows), `src/discord_bot/tool_executor.py` (pass new parameters through) |
| **Implementation Notes** | Discord.py's `channel.history()` supports `after` parameter with a message object. To skip N messages, fetch N messages and use the last one as the `after` cursor. For multiple windows, repeat this process N times. |

---