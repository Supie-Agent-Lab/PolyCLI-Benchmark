# Pain Points from Block 2 - Linus Conversation

## Issue: Event Loop Binding in Thread Context
The connection handler was trying to get the event loop during initialization (`self.loop = asyncio.get_event_loop()`), but this could fail or get the wrong loop when called from different thread contexts.

**Solution:**
Moved the event loop binding to inside the `handle_connection` method where the coroutine is actually running, ensuring we get the correct running loop:
```python
# Before (in __init__):
self.loop = asyncio.get_event_loop()

# After (in handle_connection):
async def handle_connection(self, ws, path=None):
    try:
        # 绑定当前运行事件循环供跨线程调度使用
        try:
            self.loop = asyncio.get_running_loop()
        except Exception:
            self.loop = asyncio.get_event_loop()
```

---

## Issue: AttributeError with websocket.send_json() Method
The code was inconsistently handling different websocket library versions where `send_json()` might not be available, causing AttributeError exceptions.

**Solution:**
Added fallback handling throughout the codebase to use `json.dumps()` with `send()` when `send_json()` is not available:
```python
try:
    await handler.websocket.send_json(envelope)
except AttributeError:
    import json
    await handler.websocket.send(json.dumps(envelope, ensure_ascii=False))
```

---

## Issue: Delayed Snapshot Task Creation Without Event Loop Reference
When creating delayed snapshot tasks using `asyncio.create_task()` for workflow updates, the task creation could fail if the event loop context wasn't properly established.

**Solution:**
Fixed the delayed snapshot scheduling in the WebSocket server's device registration to ensure proper async task creation:
```python
if test_mode and delay_ms > 0:
    async def _delayed_snapshot():
        try:
            await asyncio.sleep(delay_ms/1000.0)
            await _send_snapshot()
        except Exception:
            pass
    asyncio.create_task(_delayed_snapshot())
```

---

## Issue: Inconsistent WebSocket Send Implementation
The codebase had multiple places sending messages through websockets with different approaches, leading to maintenance issues and potential bugs.

**Solution:**
Added a unified `send_json()` wrapper method to centralize the sending logic and handle compatibility:
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

---

## Issue: Thread Pool Shutdown Compatibility
When shutting down the executor thread pool, newer Python versions (3.9+) support `cancel_futures` parameter, but older versions don't, causing TypeError.

**Solution:**
Added version-compatible shutdown handling:
```python
if self.executor:
    try:
        # Python 3.9+ 支持 cancel_futures
        self.executor.shutdown(wait=False, cancel_futures=True)
    except TypeError:
        self.executor.shutdown(wait=False)
    self.executor = None
```

---

## Issue: Port Binding Failures Not Detected Early
The WebSocket server could fail to start due to port already in use or permission issues, but this wasn't detected until the actual serve() call.

**Solution:**
Added preflight port binding check to detect issues early and provide clear error messages:
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

## Issue: Memory Leak with LLM Instance Caching
When configuration was updated, old LLM instances remained in cache, potentially using outdated configurations.

**Solution:**
Added cache clearing logic when configuration updates occur:
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

---

## Issue: Restart Operation Blocking Event Loop
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

## Issue: ASR Connection State Persistence Across Sessions
ASR WebSocket connections were not being properly closed/reset when exiting meeting mode, causing stale connections to persist.

**Solution:**
Added explicit ASR connection cleanup when exiting meeting mode:
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

---

## Issue: Duplicate Workflow Snapshot Sending
When entering work mode, workflow snapshots could be sent multiple times in quick succession due to multiple triggers (registration, hello, mode change).

**Solution:**
Added debouncing mechanism with timestamp tracking:
```python
# 去抖：避免与注册/hello触发的快照在极短时间内重复
import time as _t
now_ms = int(_t.time() * 1000)
last_ms = int(getattr(conn, "_last_workflow_snapshot_ms", 0) or 0)
if now_ms - last_ms >= 1500:
    # ... send snapshot ...
    conn._last_workflow_snapshot_ms = now_ms
```