# Backend Block 3 Pain Points

## Issue: Variable naming confusion suspected in last_render_cache
User suspected a typo in `backend/core/utils/last_render_cache.py::_normalize_device_id` where variable `v` was allegedly undefined.

**Solution:**
After review, the variable `v` was properly defined and used within scope. No actual bug existed:
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
The issue was a false alarm - the code was correct as written.

---

## Issue: Port binding failures and permission errors
WebSocket server failed to start due to port already in use or insufficient permissions.

**Solution:**
Added pre-flight bind check to detect port issues early and provide clear error messages:
```python
# Pre-bind check to expose "port in use/permission denied" issues early
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

## Issue: Duplicate device connections causing instability
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

## Issue: Rate limiting not working properly for render messages
Messages were being sent too frequently to devices, potentially overwhelming them.

**Solution:**
Implemented per-device rate limiting with 500ms minimum interval (≤2 QPS):
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

---

## Issue: Invalid render payloads causing failures
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

## Issue: Device title not showing for unregistered devices
Unregistered devices didn't display proper identification in UI.

**Solution:**
Inject device title only for registered devices, log but don't fail for unregistered:
```python
# Inject title: override if device is registered; otherwise don't inject, just log
injected_title = get_display_title(device_id_norm)
if injected_title is None:
    _logger.info(f"未注册设备，不注入标题 device={device_id_norm}")
    title = _norm_str(header_in.get("title")) or ""
else:
    title = injected_title  # Format: "工牌{badge} · {owner}"
```

---

## Issue: Hardware display not showing rendered content
Hardware was receiving render commands ([RENDER_RX] → [RENDER_OK] in logs) but screen wasn't updating.

**Solution:**
Fixed text drawing by switching from `print()` to `drawUTF8()` and explicitly setting colors:
```cpp
// Text rendering fix: change from print() to drawUTF8()
// and explicitly set foreground/background colors
u8g2_->setForegroundColor(ST7306_COLOR_BLACK);
u8g2_->setBackgroundColor(ST7306_COLOR_WHITE);
u8g2_->drawUTF8(x, y, text);  // Instead of u8g2_->print(text)
```
This fixed the "log shows OK but screen shows nothing/white text on white background" issue.

---

## Issue: Top banner text not visible
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

## Issue: WebSocket receive thread stack overflow
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

## Issue: Audio loop causing watchdog timer resets
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

## Issue: Device wakeup creating concurrent sessions
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

## Issue: Inconsistent logging making debugging difficult
Different log formats across components made it hard to trace message flow.

**Solution:**
Implemented unified logging with five categories:
- **[SEND]**: Before sending, includes type/id/to/mode/page|action/qps
- **[ACK]**: Device acknowledgment with id/device/elapsedMs/code
- **[DROP_BY_MODE]**: Whitelist rejection with reason/mode/detail
- **[DROP_INVALID]**: Schema/rate-limit failures with specific reasons
- **[FREEZE]**: Reserved for future rate-limiting (stage 1: log only)
- **[REDELIVER]**: Explicit redelivery tracking

Example logs:
```
[SEND] type=ui.render id=d1-002 to=94:a9:90:07:9d:88 mode=testing page=dialog.chat body=list qps=ok
[ACK] id=d1-002 device=94:a9:90:07:9d:88 elapsedMs=215
[DROP_BY_MODE] type=ui.render reason=not-allowed-in-mode mode=testing detail=logs
[DROP_INVALID] type=ui.render reason=rate-limited interval=180 device=94:a9:90:07:9d:88
```

---

## Issue: Backend not sending UI updates after ASR/LLM processing
Hardware was receiving and processing voice input, ASR was working, but no UI updates were sent back to device.

**Solution:**
Identified that backend needed to explicitly send render commands at three key points:
1. After wake word detection - send dialog prompt
2. During LLM processing - send "thinking..." placeholder
3. After LLM completion - send final answer

The issue was that the backend wasn't calling the render functions despite having all the infrastructure ready. Required adding explicit `send_render()` calls in the message handling flow.