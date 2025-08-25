# Pain Points from Backend Block 3

## Issue: Variable naming suspected typo in last_render_cache.py
User reported: "backend/core/utils/last_render_cache.py::_normalize_device_id 中变量名疑似笔误（使用了未定义的 v），虽不影响当前主链路，但建议尽快修复。"

**Solution:**
After inspection, the variable `v` was properly defined and used within scope. No actual bug existed - the variable was assigned on line 97 (`v = str(device_id).strip().strip('"').strip("'")`) before being used on line 98. Decision was made to keep it as-is to avoid unnecessary code churn during phase 1.

---

## Issue: Device registration last_render auto-redelivery causing confusion
During device registration, the backend was automatically redelivering the last rendered content, which could cause misunderstandings and wasn't necessary for phase 1 minimal loop.

**Solution:**
Removed the auto-redelivery logic completely from `backend/core/websocket_server.py`:
- Deleted the `deliver_last_render_snapshot` function implementation
- Removed the call during device registration
- Let orchestration layer decide when to actively send rendering commands
This was documented as "编辑内容05" - focusing on minimal loop for phase 1.

---

## Issue: WebSocket server port binding failures not exposed early
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

## Issue: Inconsistent logging format across different operations
Different parts of the backend were logging with different formats, making it hard to trace issues and monitor system behavior.

**Solution:**
Implemented unified logging format with five categories (编辑内容08):
- **[SEND]**: Log before sending with fields: type, id, to, mode, page|action, qps=ok|limited
- **[ACK]**: Device acknowledgments with id, device, elapsedMs  
- **[DROP_BY_MODE]**: Whitelist failures with type, reason, mode, detail
- **[DROP_INVALID]**: Schema/rate-limit failures with type, reason, missing/invalidField
- **[FREEZE]**: Reserved for future rate limiting (not triggered in phase 1)
- **[REDELIVER]**: Only when orchestration explicitly resends

---

## Issue: Rate limiting dropping frames without proper feedback
When rate limiting was triggered (>2 QPS per device), frames were silently dropped without clear indication.

**Solution:**
Added explicit logging and status returns in `render_sender.py`:
```python
if now_ms - last_ms < _MIN_INTERVAL_MS:
    _last_send_ms[device_id] = now_ms
    _logger.info(f"[DROP_INVALID] type=ui.render reason=rate-limited interval={now_ms - last_ms} device={device_id}")
    return False, "limited"
```
The status is propagated up to `send_to_device` which logs qps=limited in the [SEND] log.

---

## Issue: String payload compatibility in send_to_device
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

## Issue: Rendering allowed in wrong device states
Initially, rendering commands were being accepted and processed even when devices were in welcome/idle states, causing confusion about when rendering should occur.

**Solution:**
Implemented device mode whitelist (编辑内容10):
- Only allow rendering when device is in `dialog.preparing` or `dialog.active` modes
- Added mode tracking: set `current_mode=dialog.preparing` on listen.start
- Block rendering attempts during welcome page phase
- For `ui.render`: only allow `page==dialog.chat` during dialog modes

---

## Issue: Hardware rendering without proper wake-up state
Hardware was executing render commands even when in welcome page state, before wake word detection.

**Solution:**
Backend now tracks device state and only sends rendering after:
1. Wake word detected (handle_listen_detect with wake word)
2. Listen start event received (handle_listen with state="start")
This ensures rendering only happens after device is ready for interaction.

---

## Issue: Missing elapsed time calculation in ACK messages
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

## Issue: Device title injection failing for unregistered devices
When devices weren't registered in devices.yaml, title injection would fail silently.

**Solution:**
Added explicit logging and graceful handling:
```python
injected_title = get_display_title(device_id_norm)
if injected_title is None:
    _logger.info(f"未注册设备，不注入标题 device={device_id_norm}")
    title = _norm_str(header_in.get("title")) or ""
else:
    title = injected_title
```

---

## Issue: Unsupported body types causing silent failures
Render payloads with unsupported body.kind values were failing without clear indication.

**Solution:**
Added explicit validation and logging in `render_schema.py`:
```python
if body_kind not in ["text", "list"]:
    _logger.info(f"[DROP_INVALID] type=ui.render reason=unsupported-body-kind kind={body_kind} device={device_id_norm}")
    return None
```

---

## Issue: Control actions beyond net.banner being accepted
Phase 1 should only support net.banner action, but other actions weren't being filtered properly.

**Solution:**
Added whitelist check in `send_control`:
```python
if action != "net.banner":
    _logger.info(f"[DROP_INVALID] type=device.control reason=unsupported-action action={action} device={device_id}")
    return False, "invalid"
```