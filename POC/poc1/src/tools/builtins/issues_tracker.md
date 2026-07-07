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

### ⚠️ DEPRECATED: Operator-Based Query Syntax (has:, from:, in:)

| Field | Value |
|-------|-------|
| **ID** | DEPRECATED-001 |
| **Date** | 2026-06-05 |
| **Status** | ⚠️ **DEPRECATED** |
| **Severity** | N/A |
| **Description** | **DEPRECATED**: The operator-based query syntax (`has: image from: BotGuzu#3756`) was removed in favor of explicit boolean parameters. The `channel_search` tool now uses dedicated parameters: `has_image` (boolean), `has_link` (boolean), `has_file` (boolean), `has_video` (boolean), `has_audio` (boolean), `username` (string), `after_date` (string), `before_date` (string). See [solved_issues.md#bug-013-dep](../../solved_issues.md#bug-013-dep) for the deprecation details and migration guide. |

---

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

### ✅ BUG-CONTEXT-001: Context Compressor Tool Generates Placeholder Summary Instead of Real AI-Generated Summary

| Field | Value |
|-------|-------|
| **ID** | BUG-CONTEXT-001 |
| **Date** | 2026-06-10 |
| **Status** | ✅ **Resolved — Misreported** |
| **Severity** | Critical (was) |
| **Description** | The `context_compress` tool was documented as generating only placeholder summaries. This has been corrected — the tool DOES perform real AI-based summarization. |
| **Actual Implementation** | `ContextCompressorTool.execute()` in `context_compressor.py` (lines 222-348) accepts `messages_for_lm` parameter (line 227) and performs real LM-based summarization via `_generate_lm_summary()` method (lines 151-220). The placeholder (lines 268-275) is ONLY generated as a fallback when `messages_for_lm is None` (line 265). A secondary fallback summary generator exists (lines 322-329) that counts user/assistant messages when LM call fails. |
| **Tool Definition** | - **Tool Name**: `context_compress` - **Description**: "Compress old conversation messages into a compact summary to free up context window." - **Parameters**: `compress_before_index` (required), `target_summary_length` (default 300), `messages_to_keep_fresh` (default 6) |
| **Compression Flow** | 1. If `messages_for_lm is None` → placeholder summary (fallback). 2. If `messages_for_lm` provided → LM-based summarization via `_generate_lm_summary()`. 3. If LM call fails → fallback summary counting user/assistant messages. 4. Result returned in `[CONTEXT: <summary>]` format. |
| **Resolution** | The tool is fully functional. The placeholder behavior documented in this bug was a misreading of the code — the placeholder is a fallback for when no conversation history is provided, NOT the default behavior. The tool correctly receives messages, formats them, and sends them to LM Studio for summarization. |

### 📋 BUG-SEARCH-005: Channel Search Batch Summaries Return Empty Content — LM Returns Empty Summaries

| Field | Value |
|-------|-------|
| **ID** | BUG-SEARCH-005 |
| **Date** | 2026-06-10 |
| **Status** | 🔴 **Confirmed Active — Terminal Log Evidence (2026-06-10 22:21)** |
| **Severity** | Critical |
| **Description** | The `channel_search` tool uses batched mini-context summarization for large result sets (15+ messages). When the LM model summarizes each batch, it returns **empty content** for all batches. The final combined result contains empty batch summaries with no actual message content. |
| **Root Cause** | `_summarize_channel_search_batched()` in `tool_executor.py` sends messages to LM Studio with a summarization prompt, but the model returns empty content. The prompt may lack sufficient instruction for the model to produce meaningful summaries, or the message formatting may not provide enough context for the model to summarize effectively. |
| **Evidence** | Terminal log (2026-06-10 22:21:14-32): ```Batch 1 summary content: ''``` ```Batch 2 summary content: ''``` ```Final combined result (183 chars): "📋 Channel Search Results (batch-summarized from 15 messages):\n\nSearch query: ''\n\n--- Batch 1 Summary ---\n\n\n--- Batch 2 Summary ---\n\n\nTotal messages searched: 15\n=== END OF RESULTS ==="``` |
| **Flow Analysis** | 1. User sends a Discord message jump link. 2. Bot calls `channel_search` to find the referenced message. 3. 15 messages are fetched from the channel. 4. Messages exceed batch_size (10), so batched summarization is triggered. 5. Batch 1 (messages 1-10) → LM returns empty summary. 6. Batch 2 (messages 11-15) → LM returns empty summary. 7. Final result has empty summaries. 8. Bot has no useful data, reaches max tool calls. 9. Force-response gives "I couldn't find that specific message..." |
| **Impact** | When batched summarization is used, the tool returns completely empty summaries. The LM then has no information to work with, leading to unhelpful responses. This directly causes the "Max tool calls (3) reached" issue because the LM re-calls `channel_search` trying to get better results, but each attempt also returns empty summaries. |
| **Related Issues** | BUG-SEARCH-003, BUG-SEARCH-004, BUG-013, BUG-HANG-003, FEATURE-REQUEST-001 |

---

### 📋 BUG-SEARCH-006: Max Tool Calls (3) Reached Prematurely — Force-Response Has No Useful Data

| Field | Value |
|-------|-------|
| **ID** | BUG-SEARCH-006 |
| **Date** | 2026-06-10 |
| **Status** | 🔴 **Confirmed Active — Terminal Log Evidence (2026-06-10 22:21)** |
| **Severity** | Critical |
| **Description** | `MAX_TOOL_CALLS_PER_SESSION` is set to 3, which is too low for batched summarization workflows. The sequence is: Turn 1: `channel_search` tool call → empty summary. Turn 2: `channel_search` retry → empty summary. Turn 3: Another tool call → max reached → force-response triggered. The force-response prompt adds a user hint but does NOT include the actual (empty) tool results, so the LM has nothing meaningful to respond with. |
| **Root Cause** | Two issues combined: (1) `MAX_TOOL_CALLS_PER_SESSION = 3` is too low for batched summarization which requires 2+ LM calls just for the summarization step. (2) When max is reached, the force-response mechanism adds a hint message but doesn't inject the tool results into the conversation, leaving the LM without data to form a response. |
| **Evidence** | Terminal log (2026-06-10 22:21:32): ```Max tool calls (3) reached for channel 1503498074851508476, forcing response``` ```Making final response call after max tool calls for channel 1503498074851508476``` ```Final response obtained: "I couldn't find that specific message in the channel. It might have been deleted, or I might not have access to it. Could you share what's in that message, or check if the link is correct?"``` |
| **Expected Behavior** | (1) Increase `MAX_TOOL_CALLS_PER_SESSION` to at least 8-10 to accommodate batched summarization. (2) When max is reached, inject the actual tool results (even if empty) into the conversation so the LM can form a meaningful response like "The search found 15 messages but I couldn't extract the specific one you're looking for." |
| **Proposed Fix** | **Option A (Recommended)**: Increase `MAX_TOOL_CALLS_PER_SESSION` from 3 to 10. **Option B**: Keep max at 3 but implement the tool result injection mechanism from BUG-014's proposed fix. **Option C**: Both — increase max AND implement result injection for robustness. |
| **Files To Modify** | `src/discord_bot/message_processor.py` → `MAX_TOOL_CALLS_PER_SESSION` constant, force-response mechanism |

---

### ✅ BUG-IMG-002: Message Links in Content Do Not Trigger Image Extraction — Bot Cannot Describe Images from Jump Links

| Field | Value |
|-------|-------|
| **ID** | BUG-IMG-002 |
| **Date** | 2026-06-10 |
| **Status** | ✅ **Resolved** |
| **Severity** | High |
| **Description** | When a user sends a Discord message jump link (e.g., `https://discordapp.com/channels/1502926835862863944/1503498099081871470/1508736219281096804`) embedded in the message content, the bot fails to extract and describe the image referenced by that message. The bot responds with "I couldn't pull up the actual image from it directly!" instead of analyzing the image. |
| **Root Cause** | `message_router.py` only extracts images from: (1) direct message attachments (`message.attachments`), (2) message embeds (`message.embeds`), and (3) replied-to messages (`message.reference`). There is NO code to parse Discord message jump links from `message.content` text. |
| **Resolution** | Added `extract_images_from_message_links()` method in `message_router.py` that: (1) Parses Discord message URLs from `message.content` using `MESSAGE_LINK_PATTERN` regex. (2) Fetches each referenced message via `channel.fetch_message(message_id)`. (3) Extracts image attachments from the referenced message using `_extract_images_from_message()`. (4) Merges extracted images with existing `image_attachments` in `handle_on_message()`. |
| **Files Modified** | ✅ `src/discord_bot/message_router.py` — Added `extract_images_from_message_links()` method, integrated call in `handle_on_message()` before session processing. |
| **Related Issues** | BUG-IMG-001 (image_describe consolidation), BUG-014 (embeds), BUG-SEARCH-003, BUG-SEARCH-004 |

---

### ✅ BUG-MEMORY-001: Datetime Comparison Error — "can't compare offset-naive and offset-aware datetimes"

| Field | Value |
|-------|-------|
| **ID** | BUG-MEMORY-001 |
| **Date** | 2026-06-10 |
| **Status** | ✅ **Resolved** |
| **Severity** | High |
| **Description** | When `channel_search` attempts to fetch recent messages, it fails with `TypeError: can't compare offset-naive and offset-aware datetimes`. This error occurs in `memory_callbacks.py` when filtering messages by time. The bot falls back to `channel_search` with empty query which searches only the current channel's recent messages, missing the target message from the jump link. |
| **Root Cause** | `memory_callbacks.py` line 154 uses `datetime.utcnow()` which returns an **offset-naive** datetime (no timezone info). Line 161 compares this against `msg.created_at` which is an **offset-aware** datetime (Discord.py message objects include timezone info). Python 3 raises TypeError when comparing naive vs aware datetimes. |
| **Resolution** | Replaced `datetime.utcnow()` with `datetime.now(timezone.utc)` in `memory_callbacks.py` line 154. Added `timezone` import to the datetime import statement. |
| **Files Modified** | ✅ `src/discord_bot/memory_callbacks.py` — Line 154: `datetime.utcnow()` → `datetime.now(timezone.utc)`. Line 149: Added `timezone` to import. |
| **Related Issues** | BUG-IMG-002, BUG-SEARCH-003, BUG-SEARCH-004 |

---

## Known Limitations & Bugs (Continued)

### ⚠️ BUG-COMFY-001: ComfyUI Generate Tool Is a TODO Stub — Not Implemented

| Field | Value |
|-------|-------|
| **ID** | BUG-COMFY-001 |
| **Date** | 2026-06-11 |
| **Status** | ⚠️ **Known — Stub Code** |
| **Severity** | High |
| **Description** | The `comfyui_generate` tool is registered in the tool system but its implementation is a TODO stub. The file `comfyui_generate.py` contains only 28 lines of comments describing what the tool SHOULD do, with no actual class implementation. |
| **Actual Code State** | `comfyui_generate.py` contains only TODO comments (lines 20-28): `# TODO: Implement ComfyUIGenerateTool class (extends BaseTool)`. No class exists. No API client. No workflow submission. No polling. No image download. |
| **What Should Be Implemented** | 1. `ComfyUIGenerateTool` class extending `BaseTool`. 2. `ComfyUIClient` with: `connect(host:port)`, `submit_workflow(prompt, workflow_json)`, `poll_for_completion(timeout)`, `download_image(output_id)`. 3. API endpoints: POST `/api/prompt`, GET `/api/history/{id}`, GET `/api/view/{filename}`. 4. Duplicate prevention (one generation at a time per session). |
| **Reference Files** | `helloworlds/comfyui_api_client.py` — Working reference implementation exists in project root. `helloworlds/comfyui_RefToRef_api.json` — Workflow template. |
| **Related Issues** | BUG-IMG-001 (image_describe consolidation), FEATURE-REQUEST-002 (image generation pipeline) |

---

### ⚠️ BUG-IMG-COMP-001: Image Compare Uses LM Vision, Not Algorithmic Comparison

| Field | Value |
|-------|-------|
| **ID** | BUG-IMG-COMP-001 |
| **Date** | 2026-06-11 |
| **Status** | ⚠️ **Known — Design Choice** |
| **Severity** | Low (by design) |
| **Description** | The `image_compare` tool description claims to "compare up to 3 images side by side" but does NOT perform any algorithmic comparison (SSIM, MSE, structural similarity). Instead, it downloads images, converts them to base64, and sends them to LM Studio's vision model for visual analysis. |
| **Actual Implementation** | `compare_images_async()` in `image_compare.py` (lines 169-301): Downloads images via `safe_downloader`, resizes/compresses via `resize_image_bytes()`, converts to base64 via `image_to_base64()`, builds multi-image `mini_context` with `image_url` content parts, calls `make_lm_call_func()` with the context. The "comparison" is entirely done by the LM vision model. |
| **What This Means** | - No numerical similarity scores are computed. - No pixel-level diff analysis. - Comparison quality depends entirely on the LM model's vision capabilities. - Single image mode = description, not comparison. - Multi-image mode = LM-based visual comparison. |
| **Related Issues** | BUG-IMG-001 (image_describe consolidation), FEATURE-REQUEST-002 (image generation pipeline) |

---

## Feature Requests

### 📋 FEATURE-REQUEST-001: channel_search Incremental Processing with Context Window Protection

| Field | Value |
|-------|-------|
| **ID** | FEATURE-REQUEST-001 |
| **Date** | 2026-06-05 |
| **Status** | 📋 **Feature Request** |
| **Priority** | High |
| **Type** | Enhancement |
| **Description** | The `channel_search` tool currently returns ALL matching results at once, which can rapidly fill the LLM context window when searching channels with many messages. This causes token limit errors and degrades response quality. The tool needs to support **incremental/batched processing** with **external state management** and **two-phase summarization** to prevent context overflow. |
| **Problem Details** | 1. **No incremental processing**: The tool fetches and returns all messages in a single response, filling the context window. 2. **No context window protection**: There is no mechanism to limit the number of tokens sent to the LLM per tool call. 3. **No external state**: Search state (offset, batch index, accumulated results) is not stored externally — it relies entirely on conversation history. 4. **No two-phase processing**: There is no separate "summary context" for processing aggregated results before sending final findings to the main bot. 5. **Token limit exhaustion**: When searching large channels or using wide queries, the context window fills with raw message data, causing the LLM to hit token limits before it can produce a useful response. |
| **Proposed Architecture** | **Phase 1 — Batched Search with External State:** SearchState class to store results per session with window_index, total_windows, accumulated_summary, results, image_urls, needs_more_detail. **Phase 2 — Incremental Processing:** return_summary parameter for compact summary-only mode, offset parameter for pagination, two-phase flow (summary first, detail on demand). **Phase 3 — Context Window Protection:** max_context_tokens parameter, auto-truncate long messages, compress_long by default. |
| **Required Changes** | 1. `channel_search.py`: Add `return_summary` boolean parameter, add `window_size` parameter. 2. `tool_executor.py`: Create SearchState class, manage state lifecycle, extract image URLs separately. 3. `message_handler.py`: Add max_context_tokens limit, auto-truncate long content. |
| **Expected Behavior** | Before: channel_search(query="test") → returns 50 messages → context window full → token limit error. After: channel_search(query="test") → returns summary + image URLs → context preserved → on demand: channel_search(query="test", offset=10) → returns next 10 detailed messages. |
| **Testing Requirements** | Unit tests for batched search, summary mode, offset pagination, external state management, context window protection. Integration tests for two-phase processing flow. |
| **Files To Modify** | `src/tools/builtins/channel_search.py`, `src/discord_bot/tool_executor.py`, `src/discord_bot/bot_core.py`, `src/discord_bot/message_handler.py` |
| **Related Issues** | BUG-SEARCH-003, BUG-SEARCH-004, BUG-013, BUG-015, BUG-HANG-001 |

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

### ✅ FEATURE-CTX-001: Context Compression / Auto-Context-Compressor

| Field | Value |
|-------|-------|
| **ID** | FEATURE-CTX-001 |
| **Date** | 2026-06-09 |
| **Status** | ✅ Implemented (2026-06-09) |
| **Description** | Add automatic context compression to prevent context window overflow errors. When conversation history exceeds configurable thresholds, old messages are compressed into a summary to free up context space. |
| **Implementation Details** | **New Tool**: `context_compressor.py` — `ContextCompressorTool` that allows the LM to manually compress conversation history. **Auto-Trigger**: `MessageProcessor` monitors conversation history size and token estimates, automatically compressing when thresholds are exceeded. **Configuration**: Six new settings in tools config: `context_compression_enabled` (boolean), `context_token_threshold` (int, default 80%), `context_message_threshold` (int, default 20 messages), `context_messages_to_keep_fresh` (int, default 6), `context_summary_length` (int, default 300 chars). |
| **Configuration UI** | New "Context Compression" section in Tools Settings tab with enable/disable toggle, token threshold slider (0-100%), message threshold input, messages to keep fresh input, and summary length input. |
| **System Prompt Integration** | System prompt includes `context_compress` tool description with instructions on when to call it. |
| **Wiring** | Context settings flow: `app.py` → `bot_core.py.apply_tools_config()` → `message_handler.apply_tools_config()` → `message_processor.apply_tools_config()`. |
| **Files Modified** | ✅ `context_compressor.py` (new), ✅ `tool_executor.py`, ✅ `bot_core.py`, ✅ `config.py`, ✅ `message_handler.py`, ✅ `message_processor.py`, ✅ `index.html`, ✅ `script.js`, ✅ `app.py` |
| **Unit Tests** | ✅ `test_context_compressor.py` — 30 tests covering tool definition, execute behavior, parameter validation, and LM Studio integration. All 30 tests pass. |

---

*Last updated: 2026-06-09*
