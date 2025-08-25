# Backend Block 3 Pain Points - Merged

## Critical Issues (System Breaking)

### Issue: Backend not sending UI updates after ASR/LLM processing
Hardware was receiving and processing voice input, ASR was working, but no UI updates were sent back to device, breaking the entire conversation flow.

**Solution:**
Backend needed to explicitly send render commands at three key points:
1. After wake word detection - send dialog prompt:
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
2. During LLM processing - send "thinking..." placeholder
3. After LLM completion - send final answer

Also required adding missing import in `textHandle.py`:
```python
from core.orchestration.render_sender import send_render, send_control
```

---

### Issue: Hardware display not showing rendered content
Hardware was receiving render commands ([RENDER_RX] → [RENDER_OK] in logs) but screen wasn't updating - either showing nothing or white text on white background.

**Solution:**
Fixed text drawing by switching from `print()` to `drawUTF8()` and explicitly setting colors:
```cpp
// Text rendering fix: change from print() to drawUTF8()
// and explicitly set foreground/background colors
u8g2_->setForegroundColor(ST7306_COLOR_BLACK);
u8g2_->setBackgroundColor(ST7306_COLOR_WHITE);
u8g2_->drawUTF8(x, y, text);  // Instead of u8g2_->print(text)
```

---

### Issue: Top banner text not visible
Red banner was displaying but text was invisible or cut off for long messages.

**Solution:**
Fixed banner text rendering with proper color and adaptive layout:
```cpp
// Set white foreground for red background
u8g2_->setForegroundColor(ST7306_COLOR_WHITE);
u8g2_->drawUTF8(x, y, banner_text);  // Instead of print()

// Support single-line adaptive and two-line layout
// Priority: 16pt bold, fallback to 14pt if too wide
// Split to two lines if still too wide (UTF-8 safe boundary)
// Add ellipsis to last line automatically
```

---

## High Priority Issues (Stability & Performance)

### Issue: WebSocket receive thread stack overflow
JSON parsing and rendering in receive thread caused stack pressure and crashes.

**Solution:**
Moved heavy processing to main loop, receive thread only copies strings:
```cpp
// Receive thread slim-down: only parse 'hello' in-place
// Other JSON copied as string and posted to main loop for parsing
if (type == "hello") {
    ParseServerHello(doc);  // Quick parse, set event bit
} else {
    // Copy JSON string and schedule for main loop processing
    std::string json_copy(buffer);
    Schedule([json_copy]() {
        // Parse and render in main loop with larger stack
        OnIncomingJson(json_copy);
    });
}
```
Combined with increased pthread stack size (8192) for stability.

---

### Issue: Audio loop causing watchdog timer resets
Fixed-rate audio processing was triggering task watchdog and assertions.

**Solution:**
Implemented proper task timing and yielding:
```cpp
// Fixed beat with vTaskDelayUntil (2ms period)
TickType_t xLastWakeTime = xTaskGetTickCount();
const TickType_t xPeriod = pdMS_TO_TICKS(2);

while (running) {
    // Ensure period >= 1 tick to avoid assertion
    if (xPeriod > 0) {
        vTaskDelayUntil(&xLastWakeTime, xPeriod);
    }
    
    // Process audio...
    
    // Yield in no-data/early-exit branches
    if (no_data) {
        vTaskDelay(1);  // Active yield
    }
}
```
Also lowered audio_loop task priority to 4 to prevent CPU hogging.

---

### Issue: WebSocket server port binding failures not exposed early
Server startup errors like port already in use or permission denied were discovered too late in the startup process.

**Solution:**
Added pre-flight binding check in `backend/core/websocket_server.py::start()`:
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

### Issue: Duplicate device connections causing instability
When a device reconnected while still having an active connection, it caused routing conflicts.

**Solution:**
Implemented graceful dual-channel transition with 1.5-second overlap:
```python
async def register_or_replace_device_route(self, device_id: str, handler: ConnectionHandler) -> None:
    async with self.device_handlers_lock:
        existed = self.device_handlers.get(device_id)
        if existed is not None and existed is not handler:
            self.logger.bind(tag=TAG).warning(
                f"检测到重复连接，启用双通道过渡(≤2s)并接受新连接: device={device_id}"
            )
            # Send notification to old connection
            await existed.send_json({
                "type": "system",
                "message": "检测到新连接，当前通道将于约1.5秒后关闭以切换到新通道"
            })
            # Schedule deferred close
            async def _deferred_close(old_handler):
                await asyncio.sleep(1.5)
                await old_handler.close(old_handler.websocket)
            asyncio.create_task(_deferred_close(existed))
```

---

## Medium Priority Issues (Logic & Flow Control)

### Issue: Device registration last_render auto-redelivery causing confusion
During device registration, the backend was automatically redelivering the last rendered content, which could cause misunderstandings and wasn't necessary for phase 1 minimal loop.

**Solution:**
Removed the auto-redelivery logic completely from `backend/core/websocket_server.py`:
- Deleted the `deliver_last_render_snapshot` function implementation
- Removed the call during device registration
- Let orchestration layer decide when to actively send rendering commands
This was documented as "编辑内容05" - focusing on minimal loop for phase 1.

---

### Issue: Hardware rendering without proper wake-up state
Hardware was executing render commands even when in welcome page state, before wake word detection.

**Solution:**
Backend now tracks device state and only sends rendering after:
1. Wake word detected (handle_listen_detect with wake word)
2. Listen start event received (handle_listen with state="start")

Implemented device mode whitelist:
- Only allow rendering when device is in `dialog.preparing` or `dialog.active` modes
- Added mode tracking: set `current_mode=dialog.preparing` on listen.start
- Block rendering attempts during welcome page phase
- For `ui.render`: only allow `page==dialog.chat` during dialog modes

---

### Issue: Device wakeup creating concurrent sessions
Wake word detection was starting voice sessions while render test was active.

**Solution:**
After wakeup, only switch to render test page without establishing voice session:
```cpp
// After wakeup, enter "render test page (waiting for backend...)"
// Don't establish voice session, don't report audio
wake_word_detect_.StopDetection();
vTaskDelay(20);  // Allow detection to fully stop
wwd_suspended_ = true;  // Atomic flag to suppress OnAudioInput path
// Switch to idle state, show universal UI
```

---

### Issue: Rate limiting dropping frames without proper feedback
When rate limiting was triggered (>2 QPS per device), frames were silently dropped without clear indication.

**Solution:**
Implemented per-device rate limiting with 500ms minimum interval (≤2 QPS) and explicit logging:
```python
# Per-device render rate limiting (QPS ≤ 2), minimum interval 500ms
_MIN_INTERVAL_MS = 500
_last_send_ms: dict[str, int] = {}

# Rate limiting check
now_ms = int(time.time() * 1000)
last_ms = int(_last_send_ms.get(device_id, 0))
if now_ms - last_ms < _MIN_INTERVAL_MS:
    # Drop old frame, update timestamp to allow next send ASAP
    _last_send_ms[device_id] = now_ms
    _logger.info(f"[DROP_INVALID] type=ui.render reason=rate-limited interval={now_ms - last_ms} device={device_id}")
    return False, "limited"
_last_send_ms[device_id] = now_ms
```
The status is propagated up to `send_to_device` which logs qps=limited in the [SEND] log.

---

## Low Priority Issues (Validation & Logging)

### Issue: Inconsistent logging format across different operations
Different parts of the backend were logging with different formats, making it hard to trace issues and monitor system behavior.

**Solution:**
Implemented unified logging format with five categories:
- **[SEND]**: Log before sending with fields: type, id, to, mode, page|action, qps=ok|limited
  ```
  [SEND] type=ui.render id=d1-002 to=94:a9:90:07:9d:88 mode=testing page=dialog.chat body=list qps=ok
  ```
- **[ACK]**: Device acknowledgments with id, device, elapsedMs
  ```
  [ACK] id=d1-002 device=94:a9:90:07:9d:88 elapsedMs=215
  ```  
- **[DROP_BY_MODE]**: Whitelist failures with type, reason, mode, detail
  ```
  [DROP_BY_MODE] type=ui.render reason=not-allowed-in-mode mode=testing detail=logs
  ```
- **[DROP_INVALID]**: Schema/rate-limit failures with type, reason, missing/invalidField
  ```
  [DROP_INVALID] type=ui.render reason=rate-limited interval=180 device=94:a9:90:07:9d:88
  ```
- **[FREEZE]**: Reserved for future rate limiting (not triggered in phase 1)
- **[REDELIVER]**: Only when orchestration explicitly resends

---

### Issue: String payload compatibility in send_to_device
The `send_to_device` function didn't handle string payloads, causing issues when payloads were sent as JSON strings.

**Solution:**
Added automatic JSON parsing for string payloads:
```python
if isinstance(payload, str):
    try:
        payload = json.loads(payload)
    except Exception:
        self.logger.bind(tag=TAG).warning("send_to_device: string payload 不是有效 JSON，已丢弃")
        return False
```

---

### Issue: Invalid render payloads causing failures
Render messages with unsupported body types or missing required fields were causing errors.

**Solution:**
Implemented strict payload validation with whitelisting for body.kind:
```python
# Only allow body.kind: text|list
body_kind = _norm_str(body_in.get("kind"))
cleaned_body: Optional[Dict[str, Any]] = None
if body_kind == "text":
    text = _norm_str(body_in.get("text")) or ""
    cleaned_body = {"kind": "text", "text": text}
elif body_kind == "list":
    items = _ensure_list_of_str(body_in.get("items"), limit=8) or []
    cleaned_body = {"kind": "list", "items": items}
else:
    # Unsupported body type, return None
    _logger.info(f"[DROP_INVALID] type=ui.render reason=unsupported-body-kind kind={body_kind} device={device_id_norm}")
    return None
```

---

### Issue: Control actions beyond net.banner being accepted
Phase 1 should only support net.banner action, but other actions weren't being filtered properly.

**Solution:**
Added whitelist check in `send_control`:
```python
if action != "net.banner":
    _logger.info(f"[DROP_INVALID] type=device.control reason=unsupported-action action={action} device={device_id}")
    return False, "invalid"
```

---

### Issue: Device title injection failing for unregistered devices
When devices weren't registered in devices.yaml, title injection would fail silently.

**Solution:**
Added explicit logging and graceful handling:
```python
injected_title = get_display_title(device_id_norm)
if injected_title is None:
    _logger.info(f"未注册设备，不注入标题 device={device_id_norm}")
    title = _norm_str(header_in.get("title")) or ""
else:
    title = injected_title  # Format: "工牌{badge} · {owner}"
```

---

### Issue: Missing elapsed time calculation in ACK messages
ACK messages from devices weren't showing timing information for debugging performance issues.

**Solution:**
Added elapsed time calculation when device sends timestamp:
```python
if "ts" in msg_json:
    now_ms = int(time.time() * 1000)
    device_ts = int(msg_json.get("ts", 0))
    elapsed = now_ms - device_ts if device_ts > 0 else None
    if elapsed is not None:
        log_fields.append(f"elapsedMs={elapsed}")
```

---

## False Alarms

### Issue: Variable naming suspected typo in last_render_cache.py
User reported: "backend/core/utils/last_render_cache.py::_normalize_device_id 中变量名疑似笔误（使用了未定义的 v），虽不影响当前主链路，但建议尽快修复。"

**Resolution:**
After inspection, the variable `v` was properly defined and used within scope. No actual bug existed:
```python
def _normalize_device_id(device_id: str | None) -> str | None:
    try:
        if device_id is None:
            return None
        v = str(device_id).strip().strip('"').strip("'")  # v is defined here
        return v.lower() if v else None  # v is used here
    except Exception:
        return None
```
The variable was assigned on line 97 before being used on line 98. Decision was made to keep it as-is to avoid unnecessary code churn during phase 1.