# Architect Block 7 - Agent 2 Pain Points

## Issue: ACK Tracking and Device Freeze Mechanism Not Implemented
Missing "待确认表 + 3s超时重试1次 + 失败冻结30s" implementation. Current system only does logging without implementing flow control to the freeze level.

**Solution:**
Need to implement ACK pending confirmation table: when sending with id→register; 3s no response→retry once; second failure→freeze device for 30s (only allow `net.banner`), log `[FREEZE] device=... seconds=30`.

---

## Issue: Inconsistent Logging Format Across Components
Unified directional logging for SEND/ACK/DROP/FREEZE formats need completion. Currently has partial logging but inconsistent format and statistical metrics.

**Solution:**
Standardize logging format:
- `[SEND] type=.. id=.. to=.. mode=..`
- `[ACK] id=.. elapsedMs=..` 
- `[DROP_BY_MODE] ...`
- `[DROP_INVALID] ...`
- `[FREEZE] ...`

---

## Issue: Variable Name Typo in last_render_cache.py
Small defect in `backend/core/utils/last_render_cache.py::_normalize_device_id` - suspected typo using undefined variable 'v'. Though it doesn't affect current main chain, should be fixed promptly.

**Solution:**
Review and fix the variable reference in the `_normalize_device_id` function to use the correct variable name.

---

## Issue: Schema Validation Order Causes Wrong Error Classification
Backend currently does "whitelist first, then structure validation". When body.kind is missing, whitelist judgment gets None and incorrectly logs DROP_BY_MODE instead of DROP_INVALID.

**Solution:**
Reorder validation: forwarding entry should first do "structure/cleaning (body.kind must be text|list)", if fails → DROP_INVALID; only then proceed to "mode whitelist" judgment.

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

## Issue: Rate Limiting Confusion with Device Offline Status
When rate limiting triggers, send function returns False, causing forwarding entry to log "device not online" - misleading since device is actually online but rate-limited.

**Solution:**
Distinguish "rate limiting" from "offline/failure". Either:
1. Make send_to_device return ok/limited/offline status
2. Have sender directly print DROP_INVALID:rate-limited and upstream stops printing "device not online"

```python
# Current problematic flow:
rate_limit_exceeded → send_function_returns_false → logged_as_device_offline

# Fixed approach:
def send_to_device():
    if rate_limited:
        return "limited"
    elif device_offline:
        return "offline"
    else:
        return "ok"
```

---

## Issue: Default Mode Shows as None in Logs
Connected devices show `mode=None` in logs instead of a proper default mode, making debugging less clear.

**Solution:**
Set `currentMode` to testing (or welcome) after connection, so logs show `mode=testing` instead of None.

---

## Issue: Queue Bounds and Drop Count Statistics Not Unified
Has "time interval rate limiting + drop old frames" logging, but "drop count" and "queue limits" are not presented in unified format.

**Solution:**
Implement unified drop counting per device with cumulative output (by minute or every N entries). Present queue bounds consistently across the system.

---

## Issue: Automatic Re-delivery Strategy Not Implemented
`send_render` writes to last_render, but "auto re-deliver last_render after registration" entry point not found. Stage 1 chose "orchestration explicit delivery" approach.

**Solution:**
Either implement auto re-delivery on device registration or ensure explicit re-delivery strategy is consistently applied. If keeping explicit approach, ensure orchestration component handles re-delivery on reconnection.

---