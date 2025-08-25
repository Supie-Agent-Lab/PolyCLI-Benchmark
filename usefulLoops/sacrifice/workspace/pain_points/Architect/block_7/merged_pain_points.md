# Merged Pain Points - Architect Block 7

## Critical Issues (High Priority)

### Issue: Validation Order Logic Error - Schema Before Mode Check
When sending JSON missing required fields like `body`, the system incorrectly shows `[DROP_BY_MODE]` instead of `[DROP_INVALID]` due to whitelist validation happening before structural validation.

**Problem Example:**
```
Input: { "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"bad-002","page":"dialog.chat" }
Expected: [DROP_INVALID] type=ui.render reason=schema-invalid missing=body
Actual: [DROP_BY_MODE] type=ui.render reason=not-allowed-in-mode mode=None detail=None
```

**Solution:**
Reorder validation pipeline in backend:
1. First: Structural validation (check for body.kind field, required fields, data types)
2. Then: Mode-based whitelist filtering
3. Finally: Content sanitization and limits

```python
# Before: whitelist → schema validation  
# After: schema validation → whitelist
if not validate_schema(message):
    log("[DROP_INVALID] type=ui.render reason=schema-invalid missing=body")
    return
if not is_allowed_in_mode(message, current_mode):
    log("[DROP_BY_MODE] ...")
    return
```

---

### Issue: Missing Device State Machine Implementation
The system lacks a comprehensive state machine to track each device's current state, leading to unclear mode transitions and improper command filtering.

**Problem Description:**
Initial design was too simplistic and didn't cover all modes and transitions needed (dialog, meeting, working, coding modes). Backend needs to know each device's exact state for proper whitelist filtering.

**Solution:**
Implement comprehensive device state machine in backend:
- **States:** `boot(local) → connected(idle) → dialog.preparing → dialog.active` and similar paths for meeting, working, coding modes
- **Events:** `mode.start(dialog)`, `listen.start`, `listen.detect`, etc.
- **Whitelist matrix:** Only allow certain commands based on current device state
- **State transitions:** Proper logging for each state change
- **Target device checking:** For direct `to` forwarding, check TARGET device's `currentMode`

---

### Issue: Incomplete Dialog Conversation Pipeline
The system can render and receive ACKs but lacks the complete ASR→LLM→TTS pipeline for actual conversations.

**Problem Description:**
Missing the core conversation capability that makes devices actually "talk" - the most critical missing piece for Stage 2 dialog loop.

**Solution:**
Implement complete dialog conversation chain:
1. **ASR:** Receive audio/text from device → speech recognition → get recognized text
2. **LLM:** Feed recognized text to LLM → generate appropriate text response  
3. **TTS:** Convert LLM response to audio → send audio frames to device for playback
4. **Error handling:** Add fallbacks for each step with ui.render messages like "Sorry, couldn't hear clearly..." or "Please try again later..."

---

## Medium Priority Issues

### Issue: Rate Limiting Shows "Device Offline" Instead of Rate-Limited
When rate limiting triggers (e.g., 3 ui.render commands within 1 second), logs incorrectly show "device offline" instead of proper rate limiting indicators.

**Problem Flow:**
```
rate_limit_exceeded → send_function_returns_false → logged_as_device_offline
```

**Solution:**
Distinguish between rate limiting and actual offline status:
- Make `send_to_device` return `ok`/`limited`/`offline` status instead of boolean
- Log as `[DROP_INVALID reason=rate-limited]` or show `qps=limited` in [SEND] log
- Upstream stops printing "device not online" for rate limiting

```python
def send_to_device():
    if rate_limited:
        return "limited"
    elif device_offline:
        return "offline"
    else:
        return "ok"
```

---

### Issue: Missing ACK Tracking and Device Freeze Mechanism
Current system only does logging without implementing flow control to the freeze level - missing "待确认表 + 3s超时重试1次 + 失败冻结30s" implementation.

**Solution:**
Implement ACK pending confirmation table:
- When sending with id → register in pending table
- 3s no response → retry once
- Second failure → freeze device for 30s (only allow `net.banner`)
- Log `[FREEZE] device=... seconds=30 reason=ack-timeout id=...`

---

### Issue: Incorrect Hardware Welcome Page Logic
Initial Stage 2 design incorrectly assumed backend should send welcome page renders immediately upon device connection.

**Problem Description:**
Original design: "onConnect → mode=welcome → send welcome (ui.render:text)" conflicted with hardware's local welcome page implementation.

**Solution:**
Clarify responsibility boundaries:
- **Hardware:** Handles boot animation and welcome page locally (pre-built)
- **Backend:** NO ui.render during "connect/hello" phase
- **Rendering:** Only starts AFTER device is "awakened" (唤醒)
- **State flow:** `boot(local) → connected(idle) → dialog.preparing → dialog.active`

---

### Issue: Direct Message Forwarding Whitelist Logic Unclear
Uncertainty about whether direct `to` message forwarding should check sender's mode or target device's mode.

**Solution:**
Implement "target device mode" checking for direct forwarding:
- When message has `to:["device-id"]`, check TARGET device's `currentMode`
- Only allow `ui.render(page==dialog.chat)` and `device.control(net.banner|play.tone)` if target is in `dialog.preparing` or `dialog.active`
- All other messages should be `[DROP_BY_MODE]`

---

## Low Priority Issues

### Issue: Default Mode Shows as None in Logs
Connected devices show `mode=None` in logs instead of a proper default mode, making debugging less clear.

**Solution:**
Set `currentMode` to `testing` (or `welcome`) after connection, so logs show `mode=testing` instead of `None`.

---

### Issue: Variable Name Typo in last_render_cache.py
Small defect in `backend/core/utils/last_render_cache.py::_normalize_device_id` - suspected typo using undefined variable 'v'.

**Solution:**
Review and fix the variable reference in the `_normalize_device_id` function to use the correct variable name.

---

### Issue: Inconsistent Logging Format Across Components
Unified directional logging needs standardization across all components for easier debugging and monitoring.

**Solution:**
Standardize logging format with key=value structure:
- `[SEND] type=ui.render id=d1-002 to=94:a9:90:07:9d:88 mode=testing page=dialog.chat body=list qps=ok`
- `[ACK] id=d1-002 device=94:a9:90:07:9d:88 elapsedMs=215`
- `[DROP_BY_MODE] type=ui.render body=logs reason=not-allowed-in-mode mode=testing`
- `[DROP_INVALID] type=ui.render reason=schema-invalid missing=header/body`
- `[FREEZE] device=94:a9:90:07:9d:88 seconds=30 reason=ack-timeout id=d1-004`
- `[REDELIVER] device=94:a9:90:07:9d:88 id=wel-001 page=welcome`

---

### Issue: Queue Bounds and Drop Count Statistics Not Unified
Has rate limiting and drop old frames logging, but drop count and queue limits are not presented in unified format.

**Solution:**
Implement unified drop counting per device with cumulative output (by minute or every N entries). Present queue bounds consistently across the system.

---

### Issue: Automatic Re-delivery Strategy Not Implemented
`send_render` writes to last_render, but "auto re-deliver last_render after registration" entry point not found.

**Solution:**
Either implement auto re-delivery on device registration or ensure explicit re-delivery strategy is consistently applied through orchestration component.

---

## Lessons Learned

### Issue: Over-Engineering vs Minimal Implementation
Initial focus included too many non-essential features that weren't critical for minimum viable dialog loop.

**Key Insight:**
Focus on absolute core changes needed for Stage 2:
1. Wake-up triggered rendering (no rendering until awakened)
2. Device state machine implementation  
3. Direct forwarding whitelist based on target device mode
4. Complete ASR→LLM→TTS conversation pipeline

Keep existing features (rendering sanitization, rate limiting, unified logging) as baseline without re-implementing.

---

### Issue: Misunderstanding of Backend Implementation Status
Initial assumptions about missing features when they were already implemented led to wasted effort.

**Key Insight:**
Most Stage 1 features were already implemented:
- Transfer and whitelist functionality in `backend/core/handle/textHandle.py`
- Device routing in `backend/core/websocket_server.py::send_to_device`  
- Cleaning and rate limiting in render pipeline
- Device ACK/ERROR handling
- Unified logging structure

Always examine actual codebase before assuming features are missing.