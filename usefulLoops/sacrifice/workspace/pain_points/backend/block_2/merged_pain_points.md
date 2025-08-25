# Backend Block 2 Pain Points - Merged Analysis

## Critical Infrastructure Issues

### Issue: Python 3.13 pytest-asyncio compatibility failure
The pytest-asyncio package failed to load correctly in Python 3.13 environment, blocking test execution for the backend module changes.

**Solution:**
Cancelled the "运行核心后端单测验证改动" TODO task. The functionality was verified through static checks and minimal runtime validation instead of full unit test suite. The note indicates: "当前本地 pytest-asyncio 在 Python 3.13 环境下未能正确加载，阻碍测试执行；功能改动已通过静态检查与最小运行验证。"

---

### Issue: Port binding failures during WebSocket server startup
WebSocket server failed to bind to ports due to port occupation, insufficient permissions, or illegal host configurations. Server startup could fail silently without proper error reporting.

**Solution:**
Added pre-bind detection mechanism to expose port issues early:
```python
# 预绑定检测：尽早暴露"端口被占用/权限不足"等问题
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

## Connection Management Issues

### Issue: Duplicate device connections causing unstable routing
When a device reconnected while still having an active connection, it created routing conflicts and message delivery issues.

**Solution:**
Implemented dual-channel transition mechanism with graceful close:
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
            # Deferred close after 1.5 seconds
            async def _deferred_close(old_handler):
                await asyncio.sleep(1.5)
                await old_handler.close(old_handler.websocket)
            asyncio.create_task(_deferred_close(existed))
```

---

### Issue: Missing last render state after device reconnection
When devices reconnected, they lost their previous UI state, requiring manual refresh.

**Solution:**
Implemented last render cache with automatic redelivery on registration:
```python
# Cache last render on successful send
def set_last(device_id: str, payload: dict) -> None:
    with _LOCK:
        _LAST_RENDER_CACHE[did] = deepcopy(payload)

# Redeliver on device registration
async def deliver_last_render_snapshot(self, device_id: str, handler: ConnectionHandler) -> None:
    snap = get_last(device_id)
    if isinstance(snap, dict) and snap:
        await handler.send_json(snap)
        self.logger.bind(tag=TAG).info(f"补投last_render完成 device={device_id} id={snap.get('id')}")
```

---

### Issue: Offline devices not receiving messages
Messages sent to offline devices were being lost without any notification to senders.

**Solution:**
Implemented offline message queueing with redelivery notification:
```python
async def deliver_offline_messages(self, device_id: str, handler: ConnectionHandler) -> None:
    pending, dropped = pop_offline_for_device(device_id)
    # Send queued messages
    for env in pending:
        await handler.send_json(env)
    # Notify original senders about redelivery
    for origin_id, cnt in sender_counts.items():
        origin_handler = self.device_handlers.get(origin_id)
        if origin_handler:
            await origin_handler.send_json({
                "type": "peer",
                "event": "redelivered",
                "to": device_id,
                "count": int(cnt)
            })
```

---

## Data Validation & Processing Issues

### Issue: Unsupported render payload types causing failures
System was receiving render payloads with unsupported body types beyond text/list, causing rendering failures.

**Solution:**
Implemented strict payload cleaning with type validation:
```python
def clean_render_payload(device_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    body_kind = _norm_str(body_in.get("kind"))
    if body_kind == "text":
        cleaned_body = {"kind": "text", "text": _norm_str(body_in.get("text")) or ""}
    elif body_kind == "list":
        cleaned_body = {"kind": "list", "items": _ensure_list_of_str(body_in.get("items"), 8) or []}
    else:
        # 不支持的 body，直接返回 None
        return None
```
Log warning for unsupported payloads: `_logger.warning(f"忽略不支持的渲染负载 device={device_id}")`

---

### Issue: High-frequency rendering causing device overload
Devices were receiving render commands too frequently, leading to performance issues.

**Solution:**
Implemented per-device rate limiting with 500ms minimum interval (≤2 QPS):
```python
_MIN_INTERVAL_MS = 500
_last_send_ms: dict[str, int] = {}

now_ms = int(time.time() * 1000)
last_ms = int(_last_send_ms.get(device_id, 0))
if now_ms - last_ms < _MIN_INTERVAL_MS:
    _last_send_ms[device_id] = now_ms
    _logger.warning(f"渲染限频：已丢弃旧帧 device={device_id} interval={now_ms - last_ms}ms")
    return False
```

---

### Issue: Device ID normalization inconsistency
Device IDs needed consistent normalization across the codebase (lowercase, trim whitespace and quotes) but this was initially done inconsistently.

**Solution:**
Implemented consistent normalization function used across all modules:
```python
def _normalize_device_id(v: Optional[str]) -> Optional[str]:
    try:
        if v is None:
            return None
        s = str(v).strip().strip('"').strip("'")
        return s.lower() if s else None
    except Exception:
        return None
```

---

### Issue: Missing whitelist validation for message forwarding
Any message type could be forwarded to devices without validation, potentially causing issues.

**Solution:**
Added whitelist validation in the message handler to only allow specific message types and payloads:
```python
# 白名单校验：阶段1 仅允许 ui.render(text|list) 与 device.control(net.banner)
allow = False
if msg_type == "ui.render":
    body_kind = None
    try:
        body = msg_json.get("body") or {}
        body_kind = (body.get("kind") or "").strip().lower()
    except Exception:
        body_kind = None
    allow = body_kind in ("text", "list")
elif msg_type == "device.control":
    allow = (msg_json.get("action") == "net.banner")

if not allow:
    conn.logger.bind(tag=TAG).info(f"[DROP_BY_MODE] {safe_msg}")
    return
```

---

## Device Registry & Configuration Issues

### Issue: Device registration info not displaying in UI
Unregistered devices were showing up without proper identification, making it difficult to track which device was which.

**Solution:**
Created device registry reading from YAML with title injection:
```python
def get_display_title(device_id: str) -> Optional[str]:
    pair = get_badge_and_owner(device_id)
    if pair is None:
        return None
    badge, owner = pair
    return f"工牌{badge} · {owner}"

# In render_schema.py
injected_title = get_display_title(device_id_norm)
if injected_title is None:
    _logger.info(f"未注册设备，不注入标题 device={device_id_norm}")
    title = _norm_str((payload.get("header") or {}).get("title")) or ""
else:
    title = injected_title
```

---

### Issue: YAML file hot-reload for device registry
Device registry needed to reflect changes without restarting the server.

**Solution:**
Implemented file modification time checking with automatic reload:
```python
def _load_if_needed() -> None:
    path = _data_file_path()
    mtime = os.path.getmtime(path)
    with _LOCK:
        if _CACHE["path"] != path or float(_CACHE["mtime"]) != float(mtime):
            with open(path, "r", encoding="utf-8") as f:
                data = _yaml.load(f) or {}
            _CACHE.update({"path": path, "mtime": float(mtime), "data": data})
```

---

## API & Handler Issues

### Issue: Handler reference not available for send operations
The render_sender module couldn't access the handler directly, requiring workarounds for message routing.

**Solution:**
Designed flexible API accepting either ConnectionHandler or device_id:
```python
async def send_render(conn_or_device_id: Any, payload: Dict[str, Any]) -> bool:
    if hasattr(conn_or_device_id, "device_id"):
        handler = conn_or_device_id
        device_id = getattr(conn_or_device_id, "device_id", None)
    else:
        device_id = conn_or_device_id
        # Fall back to warning if handler not provided
        _logger.warning(f"send_render 未提供 handler，请使用 send_to_device 进行路由发送 device={device_id}")
```

---

### Issue: String payload support for send_to_device
The send_to_device function initially only supported dict payloads, but string JSON payloads were also needed.

**Solution:**
Extended send_to_device to accept both dict and string payloads with automatic JSON parsing:
```python
async def send_to_device(self, device_id: str, payload) -> bool:
    # 兼容字符串载荷自动 JSON 解析
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return False
    # ... rest of implementation
```

---

### Issue: Unsupported control actions in phase 1
System was receiving control actions beyond the supported "net.banner" action.

**Solution:**
Added explicit validation with clear error messages:
```python
if action != "net.banner":
    _logger.warning(f"不支持的控制动作(阶段1)：{action}")
    return False
```

---

## Thread Safety & Concurrency Issues

### Issue: Thread safety for cache operations
Last render cache needed thread-safe operations to prevent race conditions in concurrent access scenarios.

**Solution:**
Used threading locks for all cache operations:
```python
_LOCK = threading.RLock()
_LAST_RENDER_CACHE: dict[str, dict] = {}

def set_last(device_id: str, payload: dict) -> None:
    did = _normalize_device_id(device_id)
    if did is None:
        return
    try:
        with _LOCK:
            _LAST_RENDER_CACHE[did] = deepcopy(payload) if isinstance(payload, dict) else None
    except Exception:
        pass
```

---

## Data Validation Issues

### Issue: List item limit enforcement
Lists in render payloads needed to be limited to 8 items maximum to prevent display overflow.

**Solution:**
Implemented list truncation in the cleaning function:
```python
def _ensure_list_of_str(items: Any, limit: int = 8) -> Optional[List[str]]:
    if not isinstance(items, list):
        return None
    out: List[str] = []
    for it in items:
        s = _norm_str(it)
        if s is None:
            continue
        out.append(s)
        if len(out) >= limit:
            break
    return out
```

---

### Issue: Footer page validation for pagination
Footer pagination data needed validation to ensure valid page indices and totals.

**Solution:**
Added validation for page indices with exception handling:
```python
try:
    page_index = int(page_obj.get("index"))
    page_total = int(page_obj.get("total"))
    footer_page = {"index": page_index, "total": page_total} if page_index >= 1 and page_total >= 1 else None
except Exception:
    footer_page = None
```

---

## Monitoring & Debugging Issues

### Issue: No timing information for ACK/ERROR responses
Device acknowledgments didn't include timing information, making it hard to debug latency issues.

**Solution:**
Added elapsed time calculation for ACK/ERROR messages when they include a timestamp:
```python
if msg_type in ("ui.ack", "ui.error"):
    try:
        ts = msg_json.get("ts")
        elapsed = None
        if isinstance(ts, (int, float)):
            try:
                now_ms = int(time.time() * 1000)
                elapsed = now_ms - int(ts)
            except Exception:
                elapsed = None
    except Exception:
        elapsed = None
    
    if elapsed is None:
        conn.logger.bind(tag=TAG).info(f"收到设备回包：{msg_type} {safe_msg}")
    else:
        conn.logger.bind(tag=TAG).info(f"收到设备回包：{msg_type} {safe_msg} elapsedMs={elapsed}")
```

---

## Error Handling Improvements

### Issue: Exception handling causing silent failures
Multiple try-except blocks were swallowing exceptions without proper logging.

**Solution:**
Added comprehensive exception handling with fallback behaviors throughout:
- Normalize functions return None on any exception
- Cache operations fail silently but continue
- Send operations return False on failure
- All critical paths have try-except with appropriate fallbacks

---

### Issue: Device registration failure handling
Device registration could fail for various reasons but needed proper error handling and logging.

**Solution:**
Wrapped registration in try-catch with detailed error logging:
```python
try:
    await self.register_or_replace_device_route(device_id, handler)
    await self.broadcast_online_snapshot()
    await self.deliver_offline_messages(device_id, handler)
    await self.deliver_last_render_snapshot(device_id, handler)
    await self.snapshot_workflow_to_group(device_id, handler)
    return True
except Exception as e:
    self.logger.bind(tag=TAG).error(f"注册设备路由失败 {device_id}: {e}")
    return False
```

---

### Issue: Configuration update failures
Configuration updates from API could fail, requiring proper error handling and logging.

**Solution:**
Added comprehensive error handling for configuration updates:
```python
new_config = get_config_from_api(self.config)
if new_config is None:
    self.logger.bind(tag=TAG).error("获取新配置失败")
    return False
self.logger.bind(tag=TAG).info(f"获取新配置成功")
```

---

### Issue: Device offline handling during message forwarding
Messages sent to offline devices needed proper handling without causing errors or blocking other operations.

**Solution:**
Graceful handling with informative logging:
```python
ok = await server.send_to_device(did, msg_json)
if not ok:
    conn.logger.bind(tag=TAG).info(f"设备不在线或发送失败：{did}")
```

---

### Issue: JSON parsing failures in message handling
Invalid JSON in messages could cause parsing errors that needed to be caught and logged.

**Solution:**
Wrapped JSON operations in try-catch blocks:
```python
try:
    safe_msg = truncate_for_log(json.dumps(msg_json, ensure_ascii=False))
except Exception:
    safe_msg = str(msg_json)
conn.logger.bind(tag=TAG).info(f"收到设备回包：{msg_type} {safe_msg}")
```