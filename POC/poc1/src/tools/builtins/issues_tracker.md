# Tools Issues Tracker

> This file tracks known issues, bugs, and enhancement requests specifically related to the built-in tools.
> - `channel_search.py`: Channel message search tool
> - `image_compare.py`: Image compare/describe tool (1-3 images, consolidated from image_describe + image_compare)
> - Other tool-specific issues
> For full issue details, cross-reference with [../issues_tracker.md](../issues_tracker.md).

---

## Image Compare / Describe Tool

### BUG-IMG-001: image_describe Tool Consolidated into image_compare

| Field | Value |
|-------|-------|
| **ID** | BUG-IMG-001 |
| **Date** | 2026-06-05 |
| **Status** | ✅ Resolved |
| **Severity** | High |
| **Description** | The `image_describe` tool claimed to accept URLs in its description but its `execute()` method only handled base64 data. This caused the LM Studio model to get stuck in a loop calling `channel_search` to find images instead of using `image_describe`. |
| **Root Cause** | `image_describe.py` description said: "The image_data parameter accepts either a URL (e.g., Discord CDN link) or Base64-encoded image data." but `execute()` only processed base64. Meanwhile `image_compare.py` had proper async URL downloading via `compare_images_async()`. |
| **Fix Applied** | Consolidated `image_describe` into `image_compare`: (1) Changed `minItems` from 2 to 1 in parameters. (2) Added `is_single_image` detection in `compare_images_async()`. (3) Single image uses description prompt, multiple images use comparison prompt. (4) Removed `ImageDescribeTool` from tool registration. (5) Updated `tool_executor.py` to route `image_describe` calls through `ImageCompareTool.compare_images_async()`. (6) Deleted `image_describe.py`. |
| **Files Modified** | `src/tools/builtins/image_compare.py`, `src/tools/builtins/__init__.py`, `src/discord_bot/tool_executor.py`, `src/tools/builtins/image_describe.py` (deleted) |
| **Follow-up Cleanup (2026-06-05)** | Removed stale `ImageDescribeTool` import and registration from `bot_core.py`. Updated `message_processor.py` status message dictionaries to remove `image_describe` references. Updated `tool_executor.py` docstring to reflect consolidation. |

---

## Known Limitations & Bugs

### BUG-014 (channel_id): channel_search — LM Passes Channel Name Instead of Numeric ID

| Field | Value |
|-------|-------|
| **ID** | BUG-014 (channel_id) |
| **Date** | 2026-06-04 |
| **Status** | 🔴 Confirmed — Root Cause Identified |
| **Severity** | High |
| **Description** | The LM Studio model passes channel names ("this", "general") as `channel_id` parameter instead of actual Discord channel ID numbers. |
| **Root Cause** | 1. The LM model interprets `channel_id` as a human-readable channel name. 2. **IMPORTANT**: `resolve_channel()` in `bot_core.py` already handles channel name resolution — the names ARE being resolved correctly. The real issue is the tool call loop (BUG-013). |
| **Related** | BUG-013 (tool call loop), CHANNEL-001 (result format improvement) |
| **Proposed Fix** | **Primary**: Fix BUG-013 (tool call loop). Add explicit instruction in tool result. After max_tool_calls, force response with gathered data. |
| **Files To Modify** | `src/discord_bot/message_processor.py`, `src/discord_bot/tool_executor.py`, `src/discord_bot/message_handler.py` |

---

### BUG-014 (embeds): channel_search Only Checks Attachments, Not Embeds

| Field | Value |
|-------|-------|
| **ID** | BUG-014 (embeds) |
| **Date** | 2026-05-27 |
| **Status** | 🔴 Confirmed |
| **Severity** | Medium |
| **Description** | The `channel_search` tool only checks `message.attachments` for images, but Discord messages can also contain images via `message.embeds`. |
| **Root Cause** | `_has_image()` function only checks `message.attachments`, not `message.embeds`. |
| **Proposed Fix** | Update `_has_image()` to also check embeds: ```python def _has_image(message): # Check attachments ... # Check embeds for embed in (message.embeds or []): if embed.type == 'image' or (embed.thumbnail and embed.thumbnail.url): return True return False ``` |
| **Files To Modify** | `src/tools/builtins/channel_search.py` → `_has_image()` function |

---

### BUG-015: channel_search Rate Limit Exhaustion

| Field | Value |
|-------|-------|
| **ID** | BUG-015 |
| **Date** | 2026-05-27 |
| **Status** | 🔴 Confirmed |
| **Severity** | High |
| **Description** | Each `channel_search` call makes 16+ Discord API calls. When the model re-calls `channel_search` 3 times (BUG-013), this results in 48+ API calls, accelerating rate limit bucket exhaustion. |
| **Root Cause** | 1. Each channel_search fetches message bodies individually. 2. The model re-calls channel_search instead of using results (BUG-013). 3. No caching of channel_search results. |
| **Proposed Fix** | 1. Fix BUG-013 (tool call loop). 2. Add result caching for channel_search with TTL. 3. Consider batching message fetches. |
| **Files To Modify** | `src/tools/builtins/channel_search.py`, `src/discord_bot/message_processor.py` |

---

### BUG-SEARCH-001: channel_search Fails on Discord API Rate Limit (429)

| Field | Value |
|-------|-------|
| **ID** | BUG-SEARCH-001 |
| **Date** | 2026-06-04 |
| **Status** | 📋 Documented |
| **Severity** | High |
| **Description** | When `channel_search` hits Discord API rate limits (429 Too Many Requests), the tool does not handle the error gracefully. |
| **Proposed Fix** | Catch 429 errors and return partial results with a warning. |
| **Files To Modify** | `src/tools/builtins/channel_search.py`, `src/discord_bot/bot_core.py` |

---

### BUG-SEARCH-002: channel_search Multi-Keyword Search Doesn't Check Image URLs or Embeds

| Field | Value |
|-------|-------|
| **ID** | BUG-SEARCH-002 |
| **Date** | 2026-06-04 |
| **Status** | 🔴 Confirmed |
| **Severity** | High |
| **Description** | The `channel_search` tool fails to find messages containing image filenames because the search only checks message `content` text and attachment filenames. |
| **Root Cause** | Two filtering layers both incomplete: (1) `bot_core.py get_channel_messages()`: Only checks `content` field. (2) `channel_search.py execute()`: Checks `content` + `attachments` filenames, but NOT `image_urls`. |
| **Proposed Fix** | **Two-tier search with internal keyword splitting**: First word = primary (sent to Discord API), remaining words = secondary (client-side AND filtering). Secondary filter checks ALL fields: content, image_urls, attachments, replied_to_content. |
| **Files To Modify** | `src/discord_bot/bot_core.py`, `src/tools/builtins/channel_search.py` |

---

### BUG-SEARCH-003: channel_search image_urls Not Communicated to Main Bot After Mini-Context Summarization

| Field | Value |
|-------|-------|
| **ID** | BUG-SEARCH-003 |
| **Date** | 2026-06-05 |
| **Status** | 🔴 Confirmed Active — Terminal Log Evidence (2026-06-05) |
| **Severity** | Critical |
| **Description** | The `channel_search` tool correctly extracts `image_urls` from Discord messages and includes them in the raw message data. However, when the tool uses the **mini-context batched summarization** approach (for large result sets), the LM summarizer receives the messages with image URLs but returns **empty summaries** (`Batch 1 summary content: ''`). This means the final combined result contains NO information about image URLs found during the search. |
| **Root Cause** | The batch summarization flow in `tool_executor.py` `_summarize_channel_search_batched()` formats messages via `_format_messages_for_summarization()` which includes image URLs in the prompt text. However, the LM Studio model returns empty content for the summarization prompt. |
| **Evidence** | Terminal log shows: ```01:03:02 [INFO] [src.discord_bot.tool_executor] [channel_search] Batch 1 summary content: ''``` All batch summaries are empty strings. |
| **Flow Analysis** | 1. `channel_search` tool is called with a search query. 2. Messages are fetched from Discord channel (including `image_urls` field). 3. If messages > batch_size (10), the tool uses `_summarize_channel_search_batched()`. 4. `_format_messages_for_summarization()` formats messages with image URLs included. 5. LM is called with summarization prompt. 6. LM returns empty content. 7. Final result has no image URL information. |
| **Why This Matters** | When a user searches for "image.png" and the search finds messages containing that image, the empty summary means the main bot never learns about the image URLs. The main bot then cannot use `image_compare` or respond with image-related information. |
| **Related Issues** | BUG-013 (tool call loop), BUG-014 (embeds), BUG-HANG-001 (context overload), BUG-HANG-003 (empty response handling) |
| **Proposed Fix** | **Option A (Recommended)**: Add explicit instruction to summarization prompt: "IMPORTANT: If any messages contain image URLs, list them in your summary. Format: 'Images found: [URL1], [URL2]'." **Option B**: Use direct formatting (`_format_channel_search_direct()`) instead of mini-context summarization when image URLs are present. **Option C**: Extract image URLs separately before summarization and append them to the final result regardless of what the LM summarizes. |
| **Files To Modify** | `src/discord_bot/tool_executor.py` → `_summarize_channel_search_batched()`, `_format_messages_for_summarization()` |

---

### BUG-SEARCH-004: image_urls Present in channel_search Results But Not Passed to Main Bot Conversation

| Field | Value |
|-------|-------|
| **ID** | BUG-SEARCH-004 |
| **Date** | 2026-06-05 |
| **Status** | 🔴 Confirmed — Root Cause Identified |
| **Severity** | Critical |
| **Description** | Even when `channel_search` correctly finds messages with `image_urls`, the image URLs are NOT communicated to the main bot for follow-up actions (like `image_compare`). The issue is in the **result format**: the mini-context summarization output does not preserve image URLs in a structured way that the LM can use. |
| **Root Cause** | The `_summarize_channel_search_batched()` method returns a text summary that focuses on "key points, topics discussed" but does not explicitly include image URLs. The `_format_channel_search_direct()` method DOES include image URLs (`IMAGES: [URL1], [URL2]`), but this format is only used when `use_mini_context=False`. |
| **Evidence** | Terminal log shows direct format result includes image URLs: ```IMAGES: https://cdn.discordapp.com/attachments/...``` but mini-context result has: ```--- Batch 1 Summary ---\n\n\n``` (empty). |
| **Related Issues** | BUG-SEARCH-003, BUG-014 (embeds), BUG-IMG-001 (image_describe consolidation) |
| **Proposed Fix** | **Short-term**: In `_summarize_channel_search_batched()`, after getting the LM summary, extract and append any image URLs found in the original messages. **Long-term**: Create a structured result format that always includes image URLs regardless of summarization approach. |
| **Files To Modify** | `src/discord_bot/tool_executor.py` → `_summarize_channel_search_batched()` |

---

## Implemented Enhancements

### ✅ CONCEPT-004: Channel Search Sliding Window

| Field | Value |
|-------|-------|
| **ID** | CONCEPT-004 |
| **Date** | 2026-05-26 |
| **Status** | ✅ Implemented (2026-06-04) |
| **Description** | Add sliding window support to `channel_search` so the LM can fetch non-contiguous message windows from different points in channel history. |
| **Implemented Parameters** | **`offset`** (integer, default 0): Number of most recent messages to skip. **`windows`** (integer, default 1, max 5): Number of non-contiguous windows to fetch. |
| **Files Modified** | ✅ `channel_search.py`, ✅ `bot_core.py`, ✅ `tool_executor.py` |

---

*Last updated: 2026-06-04*