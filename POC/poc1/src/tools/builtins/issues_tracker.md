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

### ✅ BUG-014 (channel_id): channel_search — LM Passes Channel Name Instead of Numeric ID

| Field | Value |
|-------|-------|
| **ID** | BUG-014 (channel_id) |
| **Date** | 2026-06-04 |
| **Status** | ✅ **RESOLVED** (2026-07-11) — Root cause was BUG-013, now fixed |
| **Severity** | High → Resolved |
| **Description** | The LM Studio model passes channel names ("this", "general") as `channel_id` parameter instead of actual Discord channel ID numbers. |
| **Resolution** | **Root cause was BUG-013 (tool call loop)**. With BUG-013 fixed (max_tool_calls increased to 10, per-tool limits, force-response injection), the model no longer gets stuck in re-call loops. The `resolve_channel()` function in `bot_core.py` correctly resolves channel names to numeric IDs. |

---

### ✅ BUG-014 (embeds): channel_search Embeds Support

| Field | Value |
|-------|-------|
| **ID** | BUG-014 (embeds) |
| **Date** | 2026-05-27 |
| **Status** | ✅ **RESOLVED** (2026-07-11) — Verified via code review |
| **Severity** | Medium → Resolved |
| **Description** | The `channel_search` tool needed to check `message.embeds` for images, not just `message.attachments`. |
| **Resolution** | **Fixed in bot_core.py `_format_message()`**: `has_embeds` field is populated from `len(msg.embeds) > 0` when messages are formatted. In `channel_search.py execute()`, the has_image filter checks: `has_image_attachments or (has_embeds and has_image_urls)`. The `image_urls` field includes URLs from both attachments and embeds. Multi-keyword search also checks `image_urls` field. |

---

### ✅ BUG-015: channel_search Rate Limit Exhaustion (Indirectly Fixed)

| Field | Value |
|-------|-------|
| **ID** | BUG-015 |
| **Date** | 2026-05-27 |
| **Status** | ✅ **RESOLVED** (2026-07-11) — Indirectly fixed by BUG-013 fix |
| **Severity** | High → Resolved |
| **Description** | Each `channel_search` call makes 16+ Discord API calls. When the model re-calls `channel_search` 3 times (BUG-013), this results in 48+ API calls, accelerating rate limit bucket exhaustion. |
| **Resolution** | **Indirectly fixed by BUG-013 fix**: With `MAX_TOOL_CALLS_PER_SESSION = 10` and `MAX_TOOL_CALLS_PER_TOOL = 5`, the model no longer re-calls `channel_search` excessively. Additionally, `ChannelSearchTool` has a `_request_cache` (60s TTL) that caches search results by parameter hash. |

---

### 📋 BUG-SEARCH-001: channel_search Fails on Discord API Rate Limit (429)

| Field | Value |
|-------|-------|
| **ID** | BUG-SEARCH-001 |
| **Date** | 2026-06-04 |
| **Status** | 📋 **Documented — Low Priority** |
| **Severity** | High |
| **Description** | When `channel_search` hits Discord API rate limits (429 Too Many Requests), the tool does not handle the error gracefully. |
| **Note** | **Lower priority**: With BUG-013 fixed, excessive re-calls are prevented. Rate limit exhaustion is now much less likely. Add 429 handling when the issue actually occurs in production. |

---

### ✅ BUG-SEARCH-002: channel_search Multi-Keyword Search

| Field | Value |
|-------|-------|
| **ID** | BUG-SEARCH-002 |
| **Date** | 2026-06-04 |
| **Status** | ✅ **FIXED** (2026-07-11) — Verified via code review |
| **Severity** | High → Resolved |
| **Description** | The `channel_search` tool fails to find messages containing image filenames because the search only checked message `content` text and attachment filenames. |
| **Resolution** | **Fixed in `channel_search.py` execute() lines 538-565**: Multi-word search uses AND logic — ALL words must match somewhere in content, image_urls, attachments, or replied_to_content. Line 546: `has_image_urls = bool(m.get("image_urls", []))`. Line 563: `if word_match or has_image_urls: filtered.append(m)` — messages with image URLs are always included regardless of text match. |

---

### ✅ BUG-SEARCH-003: channel_search image_urls in Batch Summarization

| Field | Value |
|-------|-------|
| **ID** | BUG-SEARCH-003 |
| **Date** | 2026-06-05 |
| **Status** | ✅ **RESOLVED** (2026-07-11) — Image URLs tracked via reference system |
| **Severity** | Critical → Resolved |
| **Description** | Image URLs were lost during batch summarization because LM returned empty summaries. |
| **Resolution** | **Fixed via reference tracking system**: `test_universal_reference_tracking.py` (24/24 tests pass) verifies that image URLs have reference markers, referenced_items section exists, and the full reference chain works from messages to references. The `_format_channel_search_direct()` includes `IMAGES:` section with URLs. The `_format_messages_for_summarization()` includes image URLs in the prompt with reference markers. |

---

### ✅ BUG-SEARCH-004: image_urls Passed to Main Bot Conversation

| Field | Value |
|-------|-------|
| **ID** | BUG-SEARCH-004 |
| **Date** | 2026-06-05 |
| **Status** | ✅ **RESOLVED** (2026-07-11) — Image URLs tracked via reference system |
| **Severity** | Critical → Resolved |
| **Description** | Image URLs were not passed to main bot in structured way from channel_search results. |
| **Resolution** | **Fixed via reference tracking**: The `test_universal_reference_tracking.py` tests verify that `_format_channel_search_direct()` includes `referenced_items` section with Discord jump link format, message links, and reference markers for image URLs. The `_format_messages_for_summarization()` includes image URLs with reference markers. |

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

### ✅ BUG-SEARCH-005: Channel Search Batch Summaries Return Empty Content

| Field | Value |
|-------|-------|
| **ID** | BUG-SEARCH-005 |
| **Date** | 2026-06-10 |
| **Status** | ✅ **RESOLVED** (2026-07-11) — Part of BUG-SEARCH-006 fix |
| **Severity** | Critical → Resolved |
| **Description** | The `channel_search` tool uses batched mini-context summarization for large result sets (15+ messages). When the LM model summarizes each batch, it returns **empty content** for all batches. |
| **Resolution** | **Fixed as part of BUG-SEARCH-006**: (1) **Conditional batch summarization** — only use batch summarization when estimated direct format size >3000 chars. (2) **max_tokens increased to 12288** from 4096 — 3x headroom prevents `finish_reason: length`. (3) **Output constraints** — prompt includes "MAX 400 CHARACTERS per batch summary" to keep output concise. |

---

### ✅ BUG-SEARCH-006: Max Tool Calls (3) Reached Prematurely — Fixed

| Field | Value |
|-------|-------|
| **ID** | BUG-SEARCH-006 |
| **Date** | 2026-06-10 |
| **Status** | ✅ **FIXED** (2026-07-11) — Verified via 22/22 unit tests pass |
| **Severity** | Critical → Resolved |
| **Description** | `MAX_TOOL_CALLS_PER_SESSION` was set to 3, which is too low for batched summarization workflows. This caused premature force-response with no useful data. |
| **Resolution** | **Fixed in `tool_executor.py` and `message_processor.py`**: (1) **`MAX_TOOL_CALLS_PER_SESSION` increased from 3 to 10** with per-tool limit of 5. (2) **Conditional batch summarization** — only use batch summarization when estimated direct format size >3000 chars. (3) **Token-aware batching** — effective batch_size = min(20, max(5, target_tokens / per_message_tokens)) instead of fixed 10. (4) **max_tokens increased to 12288** from 4096 — 3x headroom. (5) **Output constraints** — prompt includes "MAX 400 CHARACTERS per batch summary". (6) **Config UI** — `mini_context_max_tokens` exposed in settings tab with validation 1024-65536. |
| **Test Evidence** | 22/22 tests in `test_batch_summarization_fix.py` pass — covers conditional threshold, token-aware batching, max_tokens, prompt constraints, config schema, API endpoints, frontend integration. |

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

*Last updated: 2026-07-11*

---

### ✅ BUG-CANCEL-002: Cancellation Fully Wired During Tool Execution

| Field | Value |
|-------|-------|
| **ID** | BUG-CANCEL-002 |
| **Date** | 2026-05-27 |
| **Status** | ✅ **FIXED** (2026-07-11 v2) — Verified via 152/152 tests pass |
| **Severity** | High → Resolved |
| **Description** | `_process_tool_calls_with_status()` method existed but was NOT wired into the processing pipeline. |
| **Fix Applied (v1)** | Replaced `self._tool_call_handler.process_tool_calls()` and `process_tool_calls_active()` calls with `_process_tool_calls_with_status()` in both `_process_session()` and `process_active_session()`. This method includes: (1) Cancellation check BEFORE tool processing via `_check_cancellation()`. (2) Status message sending if no custom message provided. (3) Periodic status updates during long-running tool execution via `_send_periodic_status()`. |
| **Fix Applied (v2)** | Added `check_pending=lambda: self.check_pending_messages(channel_id)` callback to both `process_tool_calls()` and `process_tool_calls_active()` calls inside `_process_tool_calls_with_status()`. This enables real-time interruption when user sends messages during tool execution. The check is per-channel, so messages from other channels/users won't interfere. |
