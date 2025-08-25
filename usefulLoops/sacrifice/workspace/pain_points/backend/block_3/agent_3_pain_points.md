# Backend Block 3 Pain Points

## Issue: Variable naming confusion suspected in _normalize_device_id
User reported that `backend/core/utils/last_render_cache.py::_normalize_device_id` appeared to have an undefined variable `v` usage, suggesting a typo that could cause issues.

**Solution:**
After inspection, the variable `v` was properly defined and used within the function scope. No actual bug existed:
```python
def _normalize_device_id(device_id: str | None) -> str | None:
    try:
        if device_id is None:
            return None
        v = str(device_id).strip().strip('"').strip("'")
        return v.lower() if v else None
    except Exception:
        return None
```
The issue was a false alarm - `v` is defined before use. Decision was made to keep the code as-is to maintain stability in phase 1.

---

## Issue: Device auto-redelivery of last render causing confusion
The backend was automatically redelivering the last rendered content when a device reconnected, which was causing unexpected behavior and confusion.

**Solution:**
Removed the automatic last_render redelivery logic from `backend/core/websocket_server.py`:
- Deleted the `deliver_last_render_snapshot` function implementation
- Removed the registration-time redelivery call
- No longer importing or using `get_last` 
- Decision: Let the orchestration layer explicitly decide when to send renders after device connection
This simplified the phase 1 implementation and avoided unwanted side effects.

---

## Issue: Inconsistent logging format making debugging difficult
The backend had no unified logging format for key operations like sending messages, receiving ACKs, and dropping messages, making it hard to trace issues and understand system behavior.

**Solution:**
Implemented unified logging format with five categories:
1. **[SEND]** - Before sending messages
   ```python
   "[SEND] type=ui.render id=d1-002 to=94:a9:90:07:9d:88 mode=testing page=dialog.chat body=list qps=ok"
   ```
2. **[ACK]** - Device acknowledgments with elapsed time calculation
   ```python
   "[ACK] id=d1-002 device=94:a9:90:07:9d:88 elapsedMs=215"
   ```
3. **[DROP_BY_MODE]** - Whitelist rejection
   ```python
   "[DROP_BY_MODE] type=ui.render reason=not-allowed-in-mode mode=testing detail=logs"
   ```
4. **[DROP_INVALID]** - Schema validation/rate limiting failures
   ```python
   "[DROP_INVALID] type=ui.render reason=rate-limited interval=180 device=..."
   ```
5. **[FREEZE]** and **[REDELIVER]** - Reserved for future use

---

## Issue: Backend not sending UI renders after device wakeup
Hardware was successfully waking up and sending ASR data to backend, but backend wasn't sending any UI render commands back to the device, breaking the conversation flow.

**Solution:**
Initially tried to send welcome page on device connection/hello, but this was wrong because hardware has its own boot animation. The correct approach was to only send renders after wakeup/listen events:
```python
# In handle_listen when state == "start":
await send_render(conn, {
    "type": "ui.render",
    "id": "dlg-listen-start",
    "page": "dialog.chat",
    "header": {},
    "body": {"kind": "text", "text": "请说出您的问题…"},
    "footer": {"hint": "我在听"}
})
```

---

## Issue: Hardware executing renders during welcome page inappropriately
External test client (meet001) was able to send render commands that hardware executed even during the welcome page state, which shouldn't happen.

**Solution:**
Added mode tracking to prevent render execution during inappropriate states:
```python
# Track dialog preparation state
conn.current_mode = "dialog.preparing"
```
This ensures renders are only executed when the device is in the appropriate conversational state, not during boot/welcome screens.

---

## Issue: String payload compatibility in send_to_device
The `send_to_device` function wasn't handling string payloads, only dict objects, causing issues with certain message formats.

**Solution:**
Added JSON parsing for string payloads:
```python
# Compatible with string payloads: try parsing as JSON
if isinstance(payload, str):
    try:
        payload = json.loads(payload)
    except Exception:
        self.logger.bind(tag=TAG).warning("send_to_device: string payload not valid JSON, dropped")
        return False
```

---

## Issue: Rate limiting implementation dropping frames silently
Rate limiting was working but wasn't providing clear feedback about dropped frames, making it hard to diagnose throughput issues.

**Solution:**
Enhanced rate limiting with explicit logging:
```python
if now_ms - last_ms < _MIN_INTERVAL_MS:
    _last_send_ms[device_id] = now_ms
    _logger.info(f"[DROP_INVALID] type=ui.render reason=rate-limited interval={now_ms - last_ms} device={device_id}")
    return False, "limited"
```
Returns status tuple `(success, status)` where status can be "ok" or "limited" for upstream logging.

---

## Issue: Port binding failures not detected early
WebSocket server would fail silently or late when port was already in use or permissions were insufficient.

**Solution:**
Added preflight port binding check before starting WebSocket server:
```python
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
except OSError as e:
    self.logger.bind(tag=TAG).error(
        f"WebSocketServer failed to bind preflight {host}:{port}: {e}. \n"
        f"可能原因：端口被占用/权限不足/host非法。请确认无旧进程占用端口或调整 server.port。"
    )
    self.startup_error = e
    self._started_event.set()
    raise
```

---

## Issue: Missing import for render_sender in textHandle
The conversation flow wasn't working because `textHandle.py` wasn't importing the render sender functions needed for UI updates.

**Solution:**
Added missing import:
```python
from core.orchestration.render_sender import send_render, send_control
```
This enabled the handler to send UI renders at appropriate points in the conversation flow.

---

## Issue: Whitelist validation too restrictive
Phase 1 whitelist was only allowing specific render types (text/list) and control actions (net.banner), but the validation logic wasn't clear or properly logged.

**Solution:**
Implemented clear whitelist validation with detailed logging:
```python
allow = False
if msg_type == "ui.render":
    body_kind = (msg_json.get("body") or {}).get("kind", "").strip().lower()
    allow = body_kind in ("text", "list")
elif msg_type == "device.control":
    allow = (msg_json.get("action") == "net.banner")

if not allow:
    mode = getattr(conn, "current_mode", None)
    detail = (msg_json.get("body") or {}).get("kind") if msg_type == "ui.render" else msg_json.get("action")
    conn.logger.bind(tag=TAG).info(
        f"[DROP_BY_MODE] type={msg_type} reason=not-allowed-in-mode mode={mode} detail={detail}"
    )
```