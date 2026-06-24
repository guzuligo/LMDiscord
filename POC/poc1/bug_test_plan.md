# Bug Test Plan - LMDiscord

## Overview
This document outlines the bugs identified through code analysis and unit testing, along with their root causes and proposed fixes.

**Test Results:** All 22 tests pass ✅

---

## BUG-001: Empty Response Detection - Whitespace Only (BUG-HANG-003)

**Location:** `src/discord_bot/message_processor.py`, line 1094
**Severity:** Low
**Status:** ✅ FIXED (code already has the fix)

### Description
LM Studio sometimes returns whitespace-only content (`\n\n`) which should be treated as empty. The `_is_empty_response()` method correctly handles this.

### Current Code (Line 1094)
```python
return not text or not text.strip()
```

### Test Result
✅ PASSED - The fix is already in place. `_is_empty_response('\n\n')` correctly returns `True`.

---

## BUG-002: None Response Text Slicing (BUG-HANG-004)

**Location:** `src/discord_bot/message_processor.py`, lines 395, 800
**Severity:** Low
**Status:** ✅ FIXED (code already has the guard)

### Description
When `response_text` is `None`, slicing it (`response_text[:50]`) would cause `TypeError`. The code now guards against this.

### Current Code (Lines 395, 800)
```python
response_text_safe = response_text if response_text is not None else "(None)"
```

### Test Result
✅ PASSED - The fix is already in place. None values are properly handled.

---

## BUG-003: has_link Filter Matches Image Embeds (BUG-SEARCH-001)

**Location:** `src/tools/builtins/channel_search.py`, lines 417-421
**Severity:** High
**Status:** ✅ FIXED (6/11/2026)

### Description
The `has_link` filter incorrectly matched ANY message with `has_embeds=True`, not just messages with link-type embeds. This caused false positives when filtering for link embeds.

### Buggy Code (Lines 417-421)
```python
if has_link_param and not match:
    if content_types and "link" in content_types:
        match = True
    else:
        match = m.get("has_embeds", False)  # BUG: Any embed = link?
```

### Fix Applied (Phase 1 - 6/11/2026)
```python
if has_link_param and not match:
    if content_types and "link" in content_types:
        match = True
    else:
        # Check for actual link embeds: use image_urls as proxy
        # since bot_core.py populates content_types["link"] with
        # embed URLs. If content_types["link"] wasn't set, check
        # image_urls which contains embed URLs stripped of tokens.
        match = bool(m.get("image_urls", []))
```

### Fix Applied (Phase 2 - 6/11/2026, Final)
```python
if has_link_param and not match:
    if content_types and "link" in content_types:
        match = True
    else:
        # Check for actual link embeds: use content_types["link"]
        # which bot_core.py populates with embed URLs.
        # IMPORTANT: Do NOT use image_urls here because
        # image_urls also contains attachment URLs which are
        # not link embeds.
        match = bool(m.get("content_types", {}).get("link", []))
```

### Test Result
✅ FIXED - Test `test_has_link_filter_with_embeds` passes. The fix now correctly uses `content_types["link"]` to check for link embeds instead of `image_urls` (which also contains attachment URLs) or `has_embeds` (which matches any embed type).

**Why the final fix matters:**
- `image_urls` contains BOTH embed URLs AND attachment URLs, so using it as a proxy for link embeds would cause false positives for messages with image attachments
- `content_types["link"]` is populated by `bot_core.py` only when embeds have URLs (link-type embeds), making it the correct source for `has: link` filtering

---

## BUG-004: Cancellation Method Naming (BUG-CANCEL-001)

**Location:** `src/discord_bot/bot_core.py`
**Severity:** High
**Status:** ✅ FIXED (6/11/2026)

### Description
The `bot_core.py` file was using `cancel()` instead of `request_cancel()` for the cancellation manager, causing cancellation requests to not work properly.

### Issue
The `CancellationManager` class uses `request_cancel()` method, but `bot_core.py` called `cancel()` instead, which doesn't exist.

### Fix Applied
Changed `manager.cancel(channel_id)` to `manager.request_cancel(channel_id)` in `bot_core.py` line 422.

### Verification
✅ Test `test_bot_core_uses_request_cancel` passes. All 22 tests pass.

---

## BUG-005: Tool Call Counting Limit Check

**Location:** `src/discord_bot/message_processor.py`, lines 324-329, 672-678
**Severity:** Medium
**Status:** ✅ VERIFIED (code is correct)

### Description
The tool call counting logic tracks per-tool-type call counts and enforces the `MAX_TOOL_CALLS_PER_TOOL` limit (5 calls).

### Current Code (Lines 324-329)
```python
exceeded_tool = None
for tn, count in tool_call_counts.items():
    if count >= MAX_TOOL_CALLS_PER_TOOL:
        exceeded_tool = tn
        logger.warning(f"Tool '{tn}' called {count} times (limit: {MAX_TOOL_CALLS_PER_TOOL}), forcing response")
        break
```

### Test Result
✅ PASSED - Tool call counting logic is correct.

---

## BUG-006: Date Filter Day Addition (BUG-SEARCH-002)

**Location:** `src/tools/builtins/channel_search.py`, lines 479-487
**Severity:** Medium
**Status:** ✅ FIXED (6/11/2026)

### Description
When `after_date` is provided as a date-only string (e.g., "2026-06-03"), the code was adding 1 day to the parsed datetime, so "after 2026-06-03" actually meant "after June 4th". This was counterintuitive and undocumented for the LLM calling the tool.

### Buggy Code (Lines 479-487)
```python
if after_dt.hour == 0 and after_dt.minute == 0 and after_dt.second == 0:
    from datetime import timedelta
    after_dt = after_dt + timedelta(days=1)
```

### Fix Applied
```python
# For date-only inputs (no time component), use as-is.
# `after_date: 2026-06-03` means "after June 3rd 00:00:00"
# (i.e., messages from June 3rd 00:00:01 onwards).
# This matches the LLM's natural expectation from the tool description.
```

### Rationale
The day addition behavior was undocumented and counterintuitive. Since the LLM consumer of this tool relies on the tool description to understand behavior, the fix removes the day addition to make the behavior match what the LLM would naturally expect from reading the tool description.

**Before fix:** `after_date: 2026-06-03` → June 4th 00:00:00 (off by 1 day)
**After fix:** `after_date: 2026-06-03` → June 3rd 00:00:00 (matches description)

### Test Result
✅ FIXED - Test `test_date_filter_behavior` updated to verify the corrected behavior. `after_date: 2026-06-03` now correctly means "after June 3rd 00:00:00".

---

## Summary of Confirmed Bugs

| Bug ID | Description | Severity | Status |
|--------|-------------|----------|--------|
| BUG-003 | has_link filter matches image embeds | High | ✅ FIXED |
| BUG-004 | Cancellation method naming | High | ✅ FIXED |
| BUG-006 | Date filter day addition | Medium | ✅ FIXED |
| BUG-001 | Empty response detection | Low | ✅ VERIFIED |
| BUG-002 | None response text slicing | Low | ✅ VERIFIED |

---

## Test Coverage

### test_message_processor.py
- `TestIsEmptyResponse` - Tests for whitespace-only response detection (7 tests)
- `TestResponseTextSafeSlicing` - Tests for None response text handling (2 tests)
- `TestToolCallDetection` - Tests for tool call loop detection (3 tests)
- `TestForceResponseHintInjection` - Tests for force-response hint injection (1 test)
- `TestEmptyResponseFallback` - Tests for empty response fallback messages (2 tests)
- `TestChannelSearchFiltering` - Tests for channel search filtering logic (2 tests)
- `TestCancellationManager` - Tests for cancellation system (3 tests)
- `TestMiniContextSummarization` - Tests for context summarization (2 tests)

**Total: 22 tests, all passing**

---

## Next Steps

1. ✅ **BUG-003**: Fixed `channel_search.py` to properly check for link-type embeds
2. ✅ **BUG-004**: Fixed `bot_core.py` to use `request_cancel()` method
3. ✅ **BUG-006**: Fixed `channel_search.py` to remove day addition from `after_date` filter
4. All 22 unit tests pass
