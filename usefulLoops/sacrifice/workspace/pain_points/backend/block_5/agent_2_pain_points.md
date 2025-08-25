# Pain Points Analysis - Backend Block 5

## Issue: Thread Pool Size Optimization for Memory and Context Switching
The default thread pool size was causing excessive memory usage and context switching overhead.

**Solution:**
Reduced thread pool size from system default to fixed size of 2 workers with configurable override:
```python
# 缩减线程池，降低上下文切换与内存占用
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

## Issue: Device ID Parsing from WebSocket Handshake
Device ID extraction from WebSocket connections was failing due to inconsistent header formats and missing query parameters.

**Solution:**
Implemented a three-tier fallback mechanism with auto-assignment:
1. First try parsing from query parameters via server method
2. Fallback to headers (supporting multiple naming conventions)
3. Auto-generate device ID if both fail

```python
# 统一调用服务器封装的握手解析；其次尝试 Header；最后回退自动分配
device_id_from_query = None
client_id_from_query = None
raw_path_from_server = None
try:
    server_obj = getattr(self, "server", None)
    if server_obj and hasattr(server_obj, "parse_ids_from_handshake"):
        d, c, rawp = server_obj.parse_ids_from_handshake(ws, path)
        device_id_from_query = d
        client_id_from_query = c
        raw_path_from_server = rawp
except Exception:
    pass

# 从 Header 兜底解析（包含非规范写法）
header_device_id = _normalize_id(
    self.headers.get("device-id")
    or self.headers.get("device_id")
    or self.headers.get("x-device-id")
    or self.headers.get("x-device_id")
)

# 容错：仍未取到则自动分配，保证连接可用
if not chosen_device_id:
    auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
    self.headers["device-id"] = auto_device_id
    self.headers["client-id"] = auto_device_id
```

---

## Issue: LLM Instance Management and Caching
Multiple LLM instances were being created unnecessarily for different purposes, causing memory issues.

**Solution:**
Implemented lazy loading with caching mechanism for LLM instances by purpose:
```python
def get_llm_for(self, purpose: str):
    """按用途/模式返回 LLM 实例，懒加载并缓存。
    purpose 可取："chat" | "meeting" | "coding" | "working" | "intent" | "memory"
    """
    # 缓存命中
    if key in self._llm_cache and self._llm_cache[key] is not None:
        return self._llm_cache[key]
    
    # 用途未配置专用 LLM，回退 default 并记录告警
    if mapping_val is None:
        self.logger.bind(tag=TAG).warning(
            f"get_llm_for: 未找到用途 {key} 的 llm_by_mode 配置，回退到 default"
        )
        mapping_val = mapping.get("default")
```

---

## Issue: Connection Timeout Handling
Connections were staying open indefinitely when clients became idle, consuming server resources.

**Solution:**
Implemented configurable idle timeout with fallback values:
```python
# 放宽默认空闲阈值：默认 600s + 60s 兜底；允许配置覆盖
try:
    base_idle = int(self.config.get("close_connection_no_voice_time", 600))
except Exception:
    base_idle = 600
self.timeout_seconds = base_idle + 60  # 第一层之外的兜底关闭
```

---

## Issue: Meeting Mode Throttling and Deduplication
Meeting mode was sending duplicate text segments and overwhelming the system with rapid updates.

**Solution:**
Added throttling and deduplication state management:
```python
# 会议模式相关缓存
self.meeting_segments = []  # [{"ts": int(ms), "text": str}]
self.meeting_start_ts = 0.0
self.meeting_last_snippet_ts = 0.0
self.meeting_last_snippet_index = 0
# 会议片段节流与幂等状态
self.meeting_recent_texts = {}
self.meeting_pending_texts = []
self.meeting_last_emit_ms = 0.0
self.meeting_finalized = False
```

---

## Issue: Header Parsing Compatibility with Different WebSocket Libraries
Headers were not being parsed correctly due to different attribute naming conventions in websocket libraries.

**Solution:**
Implemented robust header parsing with multiple fallback attempts:
```python
try:
    raw_headers = getattr(ws, "request_headers", {})
    # 统一小写键，便于后续从 headers 获取 authorization/device-id
    headers_lower = {}
    try:
        # 优先使用 items() 以兼容 websockets 的 Headers 类型
        for k, v in raw_headers.items():
            headers_lower[str(k).lower()] = v
    except Exception:
        try:
            headers_lower = {str(k).lower(): v for k, v in dict(raw_headers).items()}
        except Exception:
            headers_lower = {}
    self.headers = headers_lower
except Exception:
    self.headers = {}
```

---

## Issue: Memory Leak in Connection Cleanup
Memory wasn't being properly freed when connections were closed, especially for saved dialogue history.

**Solution:**
Implemented asynchronous memory saving in a separate thread to avoid blocking connection closure:
```python
async def _save_and_close(self, ws):
    """保存记忆并关闭连接"""
    try:
        if self.memory:
            # 使用线程池异步保存记忆
            def save_memory_task():
                try:
                    # 创建新事件循环（避免与主循环冲突）
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        self.memory.save_memory(self.dialogue.dialogue)
                    )
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
                finally:
                    loop.close()
            
            # 启动线程保存记忆，不等待完成
            threading.Thread(target=save_memory_task, daemon=True).start()
    except Exception as e:
        self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
    finally:
        # 立即关闭连接，不等待记忆保存完成
        await self.close(ws)
```

---

## Issue: Device Registration Failure Handling
Device registration could fail silently, leaving connections in an inconsistent state.

**Solution:**
Added explicit registration check with error handling and user notification:
```python
# 在 server 上注册设备路由（自动断开旧连接）
if self.server and self.device_id:
    ok = await self.server.register_device_handler(self.device_id, self)
    if ok is False:
        self.logger.bind(tag=TAG).error(f"设备注册失败: {self.device_id}")
        await ws.send("设备注册失败")
        await self.close(ws)
        return
```

---

## Issue: Exception Information Leakage in Logs
Stack traces and error messages could contain sensitive information when logged.

**Solution:**
Implemented safe truncation for error logging:
```python
except Exception as e:
    stack_trace = traceback.format_exc()
    try:
        safe_e = truncate_for_log(str(e))
        safe_tb = truncate_for_log(stack_trace)
    except Exception:
        safe_e = str(e)
        safe_tb = stack_trace
    self.logger.bind(tag=TAG).error(f"Connection error: {safe_e}-{safe_tb}")
```

---

## Issue: Configuration Defaults and Type Safety
Configuration values could be missing or wrong type, causing runtime errors.

**Solution:**
Added defensive programming with type checking and defaults:
```python
def _get_base_config(self) -> Dict[str, Any]:
    try:
        srv = getattr(self, "server", None)
        base_cfg = getattr(srv, "config", None) if srv else None
        if isinstance(base_cfg, dict):
            return base_cfg
    except Exception:
        pass
    return self.config if isinstance(self.config, dict) else {}
```