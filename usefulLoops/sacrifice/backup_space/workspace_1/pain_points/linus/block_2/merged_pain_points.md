# Merged Pain Points from Block 2 - Linus WebSocket Server Implementation

## Critical Issues (System Stability)

### 1. Event Loop Binding in Multi-threaded Context
The connection handler was incorrectly binding to the event loop at initialization time using `asyncio.get_event_loop()`, which could fail or get the wrong loop when called from different thread contexts or within coroutines.

**Solution:**
Changed initialization to defer event loop binding until the actual connection handling:
```python
# Before (in __init__):
self.loop = asyncio.get_event_loop()

# After:
# In __init__:
self.loop = None

# In handle_connection:
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

### 2. Port Binding Failures Not Detected Early
The WebSocket server could fail silently when the port was already occupied or there were permission issues, only detecting failures late in the startup process, leading to confusion about why the server wasn't starting.

**Solution:**
Added pre-flight port binding check before actually starting the WebSocket server to detect issues early:
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

### 3. AttributeError with websocket.send_json() Method
The code was inconsistently handling different websocket library versions where `send_json()` might not be available, causing AttributeError exceptions throughout the codebase.

**Solution:**
Created a unified JSON sending wrapper method that automatically handles compatibility:
```python
async def send_json(self, payload: dict) -> None:
    """统一发送 JSON 消息的封装，兼容不同 websocket 库版本。"""
    try:
        if self.websocket is None:
            return
        try:
            await self.websocket.send_json(payload)
        except AttributeError:
            import json as _json
            await self.websocket.send(_json.dumps(payload, ensure_ascii=False))
    except Exception:
        # 发送错误不应中断主流程
        pass
```
This wrapper tries `send_json` first, and if it fails with AttributeError, falls back to sending JSON as a string.

---

## High Priority Issues (Performance & Resource Management)

### 4. Memory Leak with LLM Instance Caching
When configuration was updated, old LLM instances remained in cache, potentially using outdated configurations. Additionally, there was no proper caching mechanism for shared instances, causing unnecessary instance creation.

**Solution:**
Implemented two-part solution:
1. Cache clearing on configuration updates:
```python
# 通知现有连接：清理用途LLM缓存，避免使用旧配置实例
try:
    for handler in list(self.active_connections):
        try:
            if hasattr(handler, "_llm_cache") and isinstance(handler._llm_cache, dict):
                handler._llm_cache.clear()
                # 同时清理 meeting 推送周期，使热更后的间隔在下一周期生效
                if hasattr(handler, "meeting_push_interval_ms_current"):
                    try:
                        delattr(handler, "meeting_push_interval_ms_current")
                    except Exception:
                        pass
        except Exception:
            continue
except Exception:
    pass
```

2. LLM registry with fingerprint-based keys:
```python
def get_or_create_llm(self, alias: str, overrides: dict | None = None):
    """按别名与可选覆盖创建/复用共享 LLM 实例。"""
    key = f"{alias}::{_json.dumps(ov, ensure_ascii=False, sort_keys=True)}"
    # Check cache
    if key in self.llm_registry:
        return self.llm_registry[key]
    # Create new instance and cache
    instance = llm_utils.create_instance(llm_type, base_conf)
    self.llm_registry[key] = instance
    return instance
```

---

### 5. Thread Pool Shutdown Compatibility
When shutting down the executor thread pool, newer Python versions (3.9+) support `cancel_futures` parameter, but older versions don't, causing TypeError. Additionally, thread pool wasn't being properly shut down, potentially causing resource leaks.

**Solution:**
Added version-compatible shutdown handling with proper configuration:
```python
# Thread pool configuration with sensible defaults
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

# Shutdown with compatibility
if self.executor:
    try:
        # Python 3.9+ 支持 cancel_futures
        self.executor.shutdown(wait=False, cancel_futures=True)
    except TypeError:
        self.executor.shutdown(wait=False)
    self.executor = None
```

---

### 6. Restart Operation Blocking Event Loop
Server restart was being executed directly, which could block the event loop and cause issues with background/nohup modes.

**Solution:**
Moved restart operation to a separate thread to avoid blocking:
```python
# 使用线程执行重启避免阻塞事件循环
def restart_server():
    """实际执行重启的方法"""
    time.sleep(1)
    self.logger.bind(tag=TAG).info("执行服务器重启...")
    # 后台重启：避免继承TTY，全部重定向，保证 nohup/background 模式不被SIGTTIN挂起
    with open(os.devnull, "rb", buffering=0) as devnull_in, \
         open(os.devnull, "ab", buffering=0) as devnull_out, \
         open(os.devnull, "ab", buffering=0) as devnull_err:
        subprocess.Popen(
            [sys.executable, "app.py"],
            stdin=devnull_in,
            stdout=devnull_out,
            stderr=devnull_err,
            start_new_session=True,
            close_fds=True,
        )
    os._exit(0)

threading.Thread(target=restart_server, daemon=True).start()
```

---

## Medium Priority Issues (Connection Management)

### 7. Duplicate Device Connections Causing Conflicts
When a device reconnected with the same device-id, the old connection wasn't properly closed, leading to duplicate connections and potential message routing issues or data loss.

**Solution:**
Implemented a dual-channel transition strategy with a 1.5-second delay before closing the old connection:
```python
if existed is not None and existed is not handler:
    self.logger.bind(tag=TAG).warning(
        f"检测到重复连接，启用双通道过渡(≤2s)并接受新连接: device={device_id}"
    )
    # 双通道过渡：先提示旧连接，延迟 ~1.5s 再关闭，降低听写中断概率
    try:
        if existed.websocket:
            try:
                await existed.send_json({
                    "type": "system",
                    "message": "检测到新连接，当前通道将于约1.5秒后关闭以切换到新通道"
                })
            except Exception:
                pass
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

### 8. ASR Connection State Persistence Across Sessions
ASR WebSocket connections were not being properly closed/reset when exiting meeting mode, causing stale connections to persist. Additionally, ASR variables couldn't be exposed to the public ASR in shared local service scenarios.

**Solution:**
1. Explicit ASR connection cleanup:
```python
# 关闭/重置 ASR 流式连接，避免下次会议复用陈旧状态
try:
    if getattr(conn, "asr", None) is not None:
        if hasattr(conn.asr, "stop_ws_connection"):
            conn.asr.stop_ws_connection()
        # 如实现了异步 close，则后台触发
        import inspect
        if hasattr(conn.asr, "close") and inspect.iscoroutinefunction(conn.asr.close):
            asyncio.create_task(conn.asr.close())
except Exception:
    pass
```

2. Private ASR variables per connection:
```python
# ASR related variables
# 因为实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR
# 所以涉及到ASR的变量，需要在这里定义，属于connection的私有变量
self.asr_audio = []
self.asr_audio_queue = queue.Queue()
```

---

### 9. Memory Save Blocking Connection Close
Saving memory to storage was blocking the connection close process, causing delays in cleanup.

**Solution:**
Changed memory saving to use a daemon thread that runs asynchronously:
```python
def save_memory_task():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            self.memory.save_memory(self.dialogue.dialogue)
        )
    except Exception as e:
        self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
    finally:
        loop.close()

# Start thread to save memory without waiting for completion
threading.Thread(target=save_memory_task, daemon=True).start()
```

---

## Low Priority Issues (Code Quality & Maintainability)

### 10. Delayed Snapshot Task Creation Without Event Loop Reference
When creating delayed snapshot tasks using `asyncio.create_task()` for workflow updates, the task creation could fail if the event loop context wasn't properly established or tasks weren't properly awaited in test mode.

**Solution:**
Fixed the delayed snapshot scheduling with proper async task creation:
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

### 11. Duplicate Workflow Snapshot Sending & Heartbeat Processing
Workflow snapshots could be sent multiple times in quick succession due to multiple triggers (registration, hello, mode change). Additionally, heartbeat processing logic was scattered across multiple places.

**Solution:**
1. Added debouncing mechanism with timestamp tracking:
```python
# 去抖：避免与注册/hello触发的快照在极短时间内重复
import time as _t
now_ms = int(_t.time() * 1000)
last_ms = int(getattr(conn, "_last_workflow_snapshot_ms", 0) or 0)
if now_ms - last_ms >= 1500:
    # ... send snapshot ...
    conn._last_workflow_snapshot_ms = now_ms
```

2. Consolidated heartbeat handling:
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

### 12. Device ID Parsing from WebSocket Handshake
Device IDs weren't being properly extracted from URL query parameters in different WebSocket library versions.

**Solution:**
Implemented comprehensive parsing that checks multiple sources:
```python
# Try multiple attribute names for compatibility
for attr in ("path", "request_uri", "raw_request_uri", "request_path", "raw_path"):
    try:
        val = getattr(conn_obj, attr, None)
        if isinstance(val, str) and val:
            raw_path_str = val
            break
    except Exception:
        continue

# Parse query parameters
parsed = urlparse(raw_path_str)
qs = parse_qs(parsed.query or "")
device_vals = qs.get("device-id") or qs.get("device_id")
```

---

### 13. Offline Message Redelivery Tracking
When devices came online, offline messages were redelivered, but there was no proper tracking of which sender sent how many messages.

**Solution:**
Implemented sender-based aggregation and acknowledgment:
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

### 14. Meeting Mode Timer Management
Meeting mode timers weren't being properly stopped when finalizing, causing continued updates after the meeting ended.

**Solution:**
Added explicit timer stopping with proper logging:
```python
try:
    setattr(conn, "meeting_finalizing", True)
except Exception:
    pass
try:
    from core.handle.meeting_handle import stop_meeting_timers
    stop_meeting_timers(conn)
    conn.logger.bind(tag=TAG).info("stop timers done")
except Exception:
    conn.logger.bind(tag=TAG).warning("stop timers encountered error (ignored)")
```

---

### 15. Configuration Update Failure Handling
When fetching new configuration from API failed, the error wasn't properly handled and could leave the system in an inconsistent state.

**Solution:**
Added proper error handling and return values:
```python
new_config = get_config_from_api(self.config)
if new_config is None:
    self.logger.bind(tag=TAG).error("获取新配置失败")
    return False
self.logger.bind(tag=TAG).info(f"获取新配置成功")
```

---

### 16. Cross-thread Coroutine Scheduling Problems
The code was using `asyncio.run_coroutine_threadsafe` with an event loop that might not be properly initialized.

**Solution:**
Ensured the event loop is properly bound before any cross-thread operations:
```python
# Only schedule after loop is bound in handle_connection
if self.loop:
    asyncio.run_coroutine_threadsafe(self.asr.open_audio_channels(self), self.loop)
```

---

## Summary
These pain points represent a comprehensive set of issues encountered in the WebSocket server implementation, ranging from critical system stability problems to minor code quality improvements. The solutions demonstrate a systematic approach to handling asynchronous programming challenges, resource management, and cross-version compatibility in a production WebSocket server environment.