# Agent_3 Pain Points - Architect Block 7

## Issue: Misunderstanding of Backend Implementation Status
The user assumed backend features were missing when they were already implemented.

**Problem Description:**
The user requested checking code implementation but initially focused only on logs rather than examining the actual codebase. This led to incorrect assumptions about what was missing from the backend implementation.

**Solution:**
Agent_3 conducted a thorough code review and discovered that most Stage 1 features were already implemented:
- Transfer and whitelist functionality in `backend/core/handle/textHandle.py`
- Device routing in `backend/core/websocket_server.py::send_to_device`
- Cleaning and rate limiting in render pipeline
- Device ACK/ERROR handling
- Unified logging structure

---

## Issue: Incorrect Logic for Hardware Welcome Page Rendering
Initial Stage 2 design incorrectly assumed backend should send welcome page renders on device connection.

**Problem Description:**
The original Stage 2 design stated: "onConnect → mode=welcome → send welcome (ui.render:text)" which conflicted with the hardware's local welcome page implementation.

**Solution:**
Agent_3 corrected the logic after user feedback:
- Hardware handles boot animation and welcome page locally
- Backend only starts rendering after "wake-up" event
- Updated state machine: `boot(local) → connected(idle) → dialog.preparing → dialog.active`
- Connection/hello phase sends no ui.render to avoid overriding hardware welcome

---

## Issue: Confusion Around Log Message Classification
Testing revealed incorrect log message categorization for validation failures.

**Problem Description:**
When sending JSON without required fields, the system logged `[DROP_BY_MODE]` instead of the expected `[DROP_INVALID]`. The backend was doing whitelist checking before structural validation.

**User Feedback:**
```
发送 { "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"bad-002","page":"dialog.chat" } 
显示[DROP_BY_MODE] type=ui.render reason=not-allowed-in-mode mode=None detail=None
```

**Solution:**
Agent_3 identified the issue was in validation order and suggested:
- Perform structural validation first (check for body.kind)
- Then apply mode-based whitelist filtering
- This ensures proper categorization: structural failures → DROP_INVALID, permission failures → DROP_BY_MODE

---

## Issue: Rate Limiting Confusion with "Device Offline" Messages
Rate limiting was working but displayed misleading "device offline" messages.

**Problem Description:**
When testing rapid message sending (3 messages in 1 second), the system showed "device offline" messages instead of proper rate limiting indicators.

**Solution:**
Agent_3 identified this was a display/logging issue rather than functional:
- Rate limiting was actually working correctly
- The issue was in how the sending function returned status
- Suggested separating rate limiting from offline/failure status in logs
- Recommended using `qps=limited` or `rate-limited` indicators instead

---

## Issue: Over-Engineering vs Minimal Implementation Conflict
User questioned why certain features were emphasized when they were already implemented.

**Problem Description:**
Agent_3 repeatedly mentioned features like "rendering sanitization," "rate limiting," and "unified logging" as needed improvements, but these were already functional in the codebase.

**User Feedback:**
"我认为渲染净化与限幅 限频与丢弃 统一日志已经做到了 我不知道为什么还要在这里强调一次?"

**Solution:**
Agent_3 adjusted approach to focus only on truly missing core features:
1. Device state machine implementation (most critical)
2. Dialog mode conversation pipeline (ASR→LLM→TTS)
3. Wake-up triggered rendering logic
4. Target device mode-based whitelist filtering

---

## Issue: Incomplete State Machine Design Initially
First attempt at state machine was oversimplified for implementation needs.

**Problem Description:**
Initial state table was too basic and didn't provide sufficient implementation guidance.

**User Feedback:**
"为什么给我 对话模式状态表的简版? 我需要详细全面的表格"

**Solution:**
Agent_3 created comprehensive state tables including:
- Detailed state transition matrix with entry conditions, allowed operations, exit conditions
- Event→transition rules with specific actions
- Direct message whitelist matrix by target device currentMode
- Error handling and fallback strategies
- Specific log patterns for each state

---

## Issue: Misalignment on Core Priorities for Stage 2
Initial task breakdown didn't focus on the most critical missing pieces.

**Problem Description:**
Agent_3 initially listed many peripheral improvements alongside core missing features, diluting focus from what truly needed implementation.

**User Insight:**
"你认为为了实现阶段2 的目标（对话最小闭环） 最核心的改动有哪些?"

**Solution:**
Agent_3 refocused on the two most critical missing pieces:
1. **Backend device state machine** - knowing each device's exact state
2. **Dialog conversation pipeline** - making devices actually "talk" (ASR→LLM→TTS)

Everything else was repositioned as "already implemented" or "secondary priority."

---

## Issue: Protocol vs Implementation Logic Confusion  
Confusion between "direct message forwarding" and "target device mode checking" concepts.

**Problem Description:**
The user needed clarification on what "wake-up triggered rendering" and "direct forward whitelist by target device mode" actually meant in practical terms.

**Solution:**
Agent_3 provided elementary explanations:
- "Wake-up triggered rendering": Like a school bell - no homework assignments until bell rings
- "Direct forward whitelist": Like subject-specific assignments - only math homework allowed during math class

This helped clarify the security and flow control concepts in simple terms.

---

## Issue: Documentation Structure Inconsistency
Multiple revisions of build.md created confusion about what was current vs outdated.

**Problem Description:**
As requirements evolved, the documentation was updated multiple times but didn't maintain clear version control of what changed and why.

**Solution:**
Agent_3 created final consolidated documentation with:
- Clear separation of Stage 1 (completed) vs Stage 2 (target)
- Detailed state tables as implementation reference
- Specific backend task assignments
- Comprehensive validation criteria

---

## Issue: Validation Order Logic Error
The backend was checking mode-based permissions before validating message structure.

**Problem Description:**
When a malformed message (missing `body` field) was sent, it was categorized as `[DROP_BY_MODE]` instead of `[DROP_INVALID]` because the whitelist check happened first.

**Technical Details:**
```
Input: { "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"bad-002","page":"dialog.chat" }
Expected: [DROP_INVALID] type=ui.render reason=schema-invalid missing=body
Actual: [DROP_BY_MODE] type=ui.render reason=not-allowed-in-mode mode=None detail=None
```

**Solution:**
Reorder validation pipeline:
1. First: Structural validation (required fields, data types)
2. Then: Mode-based whitelist checking
3. Finally: Content sanitization and limits

This ensures proper error categorization and clearer debugging.
