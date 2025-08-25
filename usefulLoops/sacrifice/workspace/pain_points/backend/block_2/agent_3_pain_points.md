# Pain Points from Backend Block 2

## Issue: Port binding failure detection
Early in the implementation, the WebSocket server would fail silently if the port was already in use or there were permission issues.

**Solution:**
Added a preflight port binding check before actually starting the WebSocket server to detect issues early:
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

## Issue: Device ID normalization inconsistency
Device IDs needed consistent normalization across the codebase (lowercase, trim whitespace and quotes) but this was initially done inconsistently.

**Solution:**
Created a centralized normalization function used throughout:
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

---

## Issue: Render rate limiting per device
Without rate limiting, devices could be overwhelmed with rapid render updates causing display issues.

**Solution:**
Implemented per-device rate limiting (≤2 QPS) with minimum 500ms interval:
```python
# 每设备渲染限频（QPS ≤ 2），实现为最小间隔 500ms
_MIN_INTERVAL_MS = 500
_last_send_ms: dict[str, int] = {}

# 限频（每设备 ≥500ms）
now_ms = int(time.time() * 1000)
last_ms = int(_last_send_ms.get(device_id, 0))
if now_ms - last_ms < _MIN_INTERVAL_MS:
    _last_send_ms[device_id] = now_ms
    _logger.warning(f"渲染限频：已丢弃旧帧 device={device_id} interval={now_ms - last_ms}ms")
    return False
_last_send_ms[device_id] = now_ms
```

---

## Issue: Missing last render cache for device reconnection
When devices reconnected, they would lose their display state and show a blank screen.

**Solution:**
Implemented a last render cache that stores the most recent render payload per device and automatically resends it on reconnection:
```python
async def deliver_last_render_snapshot(self, device_id: str, handler: ConnectionHandler) -> None:
    try:
        snap = get_last(device_id)
        if not isinstance(snap, dict) or not snap:
            return
        await handler.send_json(snap)
        self.logger.bind(tag=TAG).info(f"[REDELIVER] device={device_id} id={snap.get('id')}")
    except Exception:
        pass
```

---

## Issue: Unsafe render payload with unknown fields
Raw render payloads could contain unsupported fields or invalid data that could cause rendering issues.

**Solution:**
Created a render payload cleaner that only allows specific body kinds (text/list) and strips unknown fields:
```python
def clean_render_payload(device_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # 轻量清洗渲染负载。仅允许 body.kind: text|list，并注入设备标题
    body_kind = _norm_str(body_in.get("kind"))
    cleaned_body: Optional[Dict[str, Any]] = None
    if body_kind == "text":
        text = _norm_str(body_in.get("text")) or ""
        cleaned_body = {"kind": "text", "text": text}
    elif body_kind == "list":
        items = _ensure_list_of_str(body_in.get("items"), limit=8) or []
        cleaned_body = {"kind": "list", "items": items}
    else:
        # 不支持的 body，直接返回 None
        return None
```

---

## Issue: Device registry file hot reload
The devices.yaml file needed to be reloaded when modified without restarting the server.

**Solution:**
Implemented file modification time checking to reload the registry when the file changes:
```python
def _load_if_needed() -> None:
    path = _data_file_path()
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = 0.0
    with _LOCK:
        if _CACHE["path"] != path or float(_CACHE["mtime"]) != float(mtime):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = _yaml.load(f) or {}
            except Exception:
                data = {}
            _CACHE["path"] = path
            _CACHE["mtime"] = float(mtime)
            _CACHE["data"] = data
```

---

## Issue: Missing whitelist validation for message forwarding
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

## Issue: No timing information for ACK/ERROR responses
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

## Issue: Thread safety for shared caches
Multiple connections could access and modify the render cache simultaneously, causing race conditions.

**Solution:**
Added thread locks for all cache operations:
```python
import threading
_LOCK = threading.RLock()

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

## Issue: pytest-asyncio compatibility with Python 3.13
Testing infrastructure failed with Python 3.13 due to pytest-asyncio incompatibility.

**Solution:**
Acknowledged the limitation and performed static checking and minimal runtime verification instead of full test suite execution. This was noted as a temporary workaround:
```
取消"运行核心后端单测验证改动"这一 TODO，原因：当前本地 pytest-asyncio 在 Python 3.13 环境下未能正确加载，阻碍测试执行；功能改动已通过静态检查与最小运行验证。
```

---

## Issue: Dual-channel transition for device reconnection
When a device reconnected with the same ID, the old connection needed graceful shutdown to avoid conflicts.

**Solution:**
Implemented a graceful dual-channel transition with a 1.5-second delay before closing the old connection:
```python
if existed is not None and existed is not handler:
    self.logger.bind(tag=TAG).warning(
        f"检测到重复连接，启用双通道过渡(≤2s)并接受新连接: device={device_id}"
    )
    try:
        if existed.websocket:
            await existed.send_json({
                "type": "system",
                "message": "检测到新连接，当前通道将于约1.5秒后关闭以切换到新通道"
            })
            async def _deferred_close(old_handler):
                try:
                    await asyncio.sleep(1.5)
                    await old_handler.close(old_handler.websocket)
                except Exception:
                    pass
            asyncio.create_task(_deferred_close(existed))
    except Exception as e:
        self.logger.bind(tag=TAG).error(f"计划关闭旧连接失败(已忽略): {e}")
```

---

## Issue: String payload support for send_to_device
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