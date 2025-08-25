# Pain Points from Block 2 - WebSocket Server Implementation

## Issue: Event Loop Binding Error in Connection Handler
The ConnectionHandler was trying to bind to the event loop at initialization time using `asyncio.get_event_loop()`, but this could fail or get the wrong loop when called from within a coroutine context.

**Solution:**
Changed the initialization to set `self.loop = None` initially, then bind the actual running event loop inside the `handle_connection` coroutine:
```python
# Before (line 714)
self.loop = asyncio.get_event_loop()

# After
# In __init__:
self.loop = None

# In handle_connection:
try:
    self.loop = asyncio.get_running_loop()
except Exception:
    self.loop = asyncio.get_event_loop()
```

---

## Issue: Port Binding Detection Failure
The WebSocket server could fail silently when the port was already occupied or there were permission issues, leading to confusion about why the server wasn't starting.

**Solution:**
Added pre-flight port binding check before actually starting the WebSocket server to detect issues early:
```python
# Pre-binding check to expose port/permission issues early
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

## Issue: Inconsistent WebSocket Send Methods
The code had multiple places using different methods to send JSON data (`websocket.send(json.dumps())` vs `websocket.send_json()`), causing potential compatibility issues and code duplication.

**Solution:**
Created unified send wrapper methods that automatically handle the `send_json` AttributeError and fallback to string sending:
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
        # 发送错误不应中断主流程
        pass
```

---

## Issue: Delayed Workflow Snapshot Timing Problem
The workflow snapshot was being sent with a delay using `asyncio.sleep()` in test mode, but the task creation wasn't properly handled with `asyncio.create_task()`.

**Solution:**
Fixed the async task creation for delayed snapshot sending:
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

## Issue: ASR Variable Exposure in Shared Local Service
When using a shared local ASR service, instance variables couldn't be exposed to the public ASR, requiring separate private variables for each connection.

**Solution:**
Defined ASR-related variables as private to the connection instance:
```python
# ASR related variables
# 因为实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR
# 所以涉及到ASR的变量，需要在这里定义，属于connection的私有变量
self.asr_audio = []
self.asr_audio_queue = queue.Queue()
```

---

## Issue: Duplicate Connection Handling
When a device reconnected with the same device-id, the old connection wasn't properly closed, leading to duplicate connections and potential message routing issues.

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

## Issue: Memory Save Blocking Connection Close
Saving memory to storage was blocking the connection close process, causing delays in cleanup.

**Solution:**
Changed memory saving to use a daemon thread that runs asynchronously without blocking the connection close:
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

## Issue: Configuration Update Failure Handling
When fetching new configuration from API failed, the error wasn't properly handled and could leave the system in an inconsistent state.

**Solution:**
Added proper error handling and return values for configuration updates:
```python
new_config = get_config_from_api(self.config)
if new_config is None:
    self.logger.bind(tag=TAG).error("获取新配置失败")
    return False
self.logger.bind(tag=TAG).info(f"获取新配置成功")
```

---

## Issue: LLM Instance Creation and Caching
Multiple LLM instances were being created unnecessarily, and there was no proper caching mechanism for shared instances.

**Solution:**
Implemented an LLM registry with fingerprint-based keys for instance reuse:
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

## Issue: Thread Pool Resource Management
The thread pool wasn't being properly shut down, potentially causing resource leaks.

**Solution:**
Added proper thread pool shutdown with Python 3.9+ cancel_futures support:
```python
if self.executor:
    try:
        # Python 3.9+ supports cancel_futures
        self.executor.shutdown(wait=False, cancel_futures=True)
    except TypeError:
        self.executor.shutdown(wait=False)
    self.executor = None
```

---

## Issue: Device ID Parsing from WebSocket Handshake
Device IDs weren't being properly extracted from URL query parameters in different WebSocket library versions.

**Solution:**
Implemented comprehensive parsing that checks multiple sources and attribute names:
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

## Issue: Meeting Mode Timer Management
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