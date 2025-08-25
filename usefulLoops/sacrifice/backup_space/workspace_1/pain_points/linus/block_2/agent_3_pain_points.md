# Pain Points from Linus Block 2

## Issue: AttributeError when calling send_json on websocket
The code was encountering AttributeError when trying to call `send_json` method on websocket connections, as the websockets library doesn't have a native `send_json` method.

**Solution:**
Created a unified JSON sending wrapper method that automatically handles compatibility:
```python
async def send_json(self, payload: dict) -> None:
    """统一 JSON 发送包装，自动兼容 send_json 缺失并回退字符串。"""
    try:
        if self.websocket is None:
            return
        try:
            await self.websocket.send_json(payload)
        except AttributeError:
            import json as _json
            await self.websocket.send(_json.dumps(payload, ensure_ascii=False))
    except Exception:
        pass
```
This wrapper tries to use `send_json` first, and if it fails with AttributeError, falls back to sending JSON as a string.

---

## Issue: Event loop binding issues in multi-threaded environment
The code was binding the event loop at initialization time using `asyncio.get_event_loop()`, which could cause issues when the actual connection handler runs in a different thread or context.

**Solution:**
Moved the event loop binding from initialization to the actual connection handling method:
```python
# Before (in __init__):
# self.loop = asyncio.get_event_loop()

# After (in handle_connection):
async def handle_connection(self, ws, path=None):
    try:
        # 绑定当前运行事件循环供跨线程调度使用
        try:
            self.loop = asyncio.get_running_loop()
        except Exception:
            self.loop = asyncio.get_event_loop()
```
This ensures the event loop is bound to the actual running loop when the connection is established.

---

## Issue: Duplicate heartbeat/ping message handling
The code had redundant heartbeat processing logic scattered across multiple places, causing unnecessary processing overhead.

**Solution:**
Consolidated heartbeat handling into a single location and removed duplicate branches. Added early return for ping/keepalive messages to avoid further processing:
```python
if isinstance(obj, dict) and obj.get("type") in ("ping", "keepalive"):
    try:
        # 可选：立即回 pong
        await self.websocket.send(_json.dumps({"type": "pong"}))
    except Exception:
        pass
    return  # Early return to avoid duplicate processing
```

---

## Issue: Delayed snapshot scheduling with asyncio.create_task
When using `asyncio.create_task` for delayed operations, the tasks weren't properly awaited in test mode, potentially causing race conditions.

**Solution:**
Fixed the delayed snapshot scheduling by properly structuring the async functions:
```python
if test_mode and delay_ms > 0:
    async def _delayed_snapshot():
        try:
            await asyncio.sleep(delay_ms/1000.0)
            await _send_snapshot()
        except Exception:
            pass
    asyncio.create_task(_delayed_snapshot())
else:
    await _send_snapshot()
```

---

## Issue: Port binding failures not detected early
The WebSocket server could fail to start due to port conflicts or permission issues, but these failures were only detected late in the startup process.

**Solution:**
Added pre-flight port binding check before actually starting the WebSocket server:
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

## Issue: Duplicate device connections causing conflicts
When a device reconnected with the same ID, it would conflict with the existing connection, potentially causing data loss or confusion.

**Solution:**
Implemented a dual-channel transition mechanism that gracefully handles duplicate connections:
```python
if existed is not None and existed is not handler:
    self.logger.bind(tag=TAG).warning(
        f"检测到重复连接，启用双通道过渡(≤2s)并接受新连接: device={device_id}"
    )
    # 双通道过渡：先提示旧连接，延迟 ~1.5s 再关闭，降低听写中断概率
    try:
        if existed.websocket:
            await existed.websocket.send(json.dumps({
                "type": "system",
                "message": "检测到新连接，当前通道将于约1.5秒后关闭以切换到新通道"
            }, ensure_ascii=False))
            async def _deferred_close(old_handler):
                await asyncio.sleep(1.5)
                await old_handler.close(old_handler.websocket)
            asyncio.create_task(_deferred_close(existed))
    except Exception as e:
        self.logger.bind(tag=TAG).error(f"计划关闭旧连接失败(已忽略): {e}")
```

---

## Issue: Inconsistent JSON sending methods across codebase
The code had multiple different approaches to sending JSON data, some using `send_json`, others using `json.dumps` with `send`, leading to maintenance issues.

**Solution:**
Replaced all major JSON sending call sites with the unified `send_json` method:
```python
# Before:
await self.websocket.send(json.dumps(self.welcome_msg))

# After:
await self.send_json(self.welcome_msg)
```
This standardization makes the code more maintainable and ensures consistent error handling.

---

## Issue: Thread pool sizing not optimized for different workloads
The thread pool was using a fixed size that might not be optimal for different deployment scenarios.

**Solution:**
Made thread pool size configurable with sensible defaults:
```python
try:
    meeting_cfg = self.config.get("meeting", {}) if isinstance(self.config, dict) else {}
    # 固化 W3：线程池默认 2，可被 meeting.threadpool_max_workers 覆盖
    default_workers = 2
    max_workers = int(meeting_cfg.get("threadpool_max_workers", default_workers))
    if max_workers < 1:
        max_workers = default_workers
except Exception:
    max_workers = 2
self.executor = ThreadPoolExecutor(max_workers=max_workers)
```

---

## Issue: Offline message redelivery tracking issues
When devices came online, offline messages were redelivered, but there was no proper tracking of which sender sent how many messages.

**Solution:**
Implemented sender-based aggregation and acknowledgment for offline message redelivery:
```python
# 统计按发起方聚合的补投条数
try:
    from collections import defaultdict
    sender_counts = defaultdict(int)
except Exception:
    sender_counts = {}

# Track messages per sender
for env in pending:
    origin = env.get("from")
    if isinstance(origin, str) and len(origin) > 0:
        key = origin.strip().lower()
        sender_counts[key] += 1

# Send acknowledgments to each sender
for origin_id, cnt in sender_counts.items():
    origin_handler = self.device_handlers.get(origin_id)
    if origin_handler and origin_handler.websocket:
        payload = {
            "type": "peer",
            "event": "redelivered",
            "to": device_id,
            "count": int(cnt),
        }
        await origin_handler.send_json(payload)
```

---

## Issue: Cross-thread coroutine scheduling problems
The code was using `asyncio.run_coroutine_threadsafe` with an event loop that might not be properly initialized.

**Solution:**
Ensured the event loop is properly bound before any cross-thread operations:
```python
# Only schedule after loop is bound in handle_connection
if self.loop:
    asyncio.run_coroutine_threadsafe(self.asr.open_audio_channels(self), self.loop)
```