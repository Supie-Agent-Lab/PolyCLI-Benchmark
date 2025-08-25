# Pain Points from Backend Block 7 - Merged Insights

## Critical: WebSocket Connection & Device Registration Issues

### Device ID Parsing Failures from Multiple Sources
Device IDs weren't being properly extracted from WebSocket handshake headers and query parameters, leading to connection failures.

**Solution:**
Implemented multi-level parsing with automatic fallback to auto-generated IDs:
```python
# 1. Try server's unified handshake parser
device_id_from_query = None
if server_obj and hasattr(server_obj, "parse_ids_from_handshake"):
    d, c, rawp = server_obj.parse_ids_from_handshake(ws, path)
    device_id_from_query = d

# 2. Fallback to Header parsing with multiple variations
header_device_id = _normalize_id(
    self.headers.get("device-id")
    or self.headers.get("device_id")  
    or self.headers.get("x-device-id")
    or self.headers.get("x-device_id")
)

# 3. Priority: Query > Header > Auto-generate
chosen_device_id = device_id_from_query or header_device_id or header_client_id
if not chosen_device_id:
    # Auto-generate if all parsing fails
    auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
    self.headers["device-id"] = auto_device_id
    self.logger.bind(tag=TAG).warning(
        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}; "
        f"rawPaths={truncate_for_log(str(raw_paths_snapshot))}, "
        f"headerKeys={truncate_for_log(str(header_keys))}"
    )
```

### Device Registration Failures Not Handled
Device registration with the server could fail, but errors weren't properly handled, leading to zombie connections.

**Solution:**
Added explicit registration failure handling with connection cleanup:
```python
if self.server and self.device_id:
    ok = await self.server.register_device_handler(self.device_id, self)
    if ok is False:
        self.logger.bind(tag=TAG).error(f"设备注册失败: {self.device_id}")
        await ws.send("设备注册失败")
        await self.close(ws)
        return  # Stop processing
```

### WebSocket Headers Compatibility with Different Libraries
The system needed to handle headers from different WebSocket library implementations with varying attribute naming conventions.

**Solution:**
Implemented robust header parsing that tries multiple methods:
```python
# 获取并验证headers（兼容 websockets 库的属性命名）
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
```

### WebSocket Send Failures Breaking Main Flow
WebSocket send operations were throwing exceptions that interrupted the main message flow.

**Solution:**
Implemented unified send wrappers with comprehensive error handling:
```python
async def send_json(self, data: dict) -> bool:
    if not self.websocket:
        self.logger.bind(tag=TAG).warning("send_json: websocket is None")
        return False
    
    try:
        # Try send_json method first
        if hasattr(self.websocket, 'send_json'):
            await self.websocket.send_json(data)
        else:
            # Fallback to string send
            await self.websocket.send(json.dumps(data, ensure_ascii=False))
        return True
    except websockets.exceptions.ConnectionClosed:
        # Silent handling for expected case
        self.logger.bind(tag=TAG).debug(f"send_json: connection closed")
        return False
    except Exception as e:
        # Log but don't interrupt flow
        self.logger.bind(tag=TAG).warning(f"send_json failed: {e}")
        return False
```

---

## Critical: LLM Instance Management Issues

### LLM Selection by Mode Failing with Fallback Issues
The `get_llm_for()` method was failing to properly select mode-specific LLMs and fallback to default, causing errors when specific purpose configurations were missing.

**Solution:**
Implemented comprehensive fallback strategy with proper error handling and caching:
```python
def get_llm_for(self, purpose: str):
    """Get LLM instance by purpose/mode with lazy loading and caching"""
    try:
        key = str(purpose or "chat").lower()
    except Exception:
        key = "chat"
    
    # Check cache first
    if key in self._llm_cache and self._llm_cache[key] is not None:
        return self._llm_cache[key]
    
    # Try to get mapping configuration
    mapping_val = mapping.get(key, None)
    if mapping_val is None:
        # Fallback to default and log warning
        self.logger.bind(tag=TAG).warning(
            f"get_llm_for: 未找到用途 {key} 的 llm_by_mode 配置，回退到 default"
        )
        mapping_val = mapping.get("default")
    
    # Multiple fallback layers for failures
    try:
        # Try server factory
        srv = getattr(self, "server", None)
        if srv and hasattr(srv, "get_or_create_llm"):
            instance = srv.get_or_create_llm(alias, overrides)
            if instance is not None:
                self._llm_cache[key] = instance
                return instance
    except Exception as e:
        # Final fallback to default LLM
        self.logger.bind(tag=TAG).warning(f"get_llm_for 失败({key}): {e}，回退默认LLM")
    
    self._llm_cache[key] = self.llm
    return self.llm
```

### Configuration Alias Resolution Complexity
LLM configuration could use various keys (alias, name, module, llm) and needed robust parsing to handle all cases.

**Solution:**
Implemented flexible alias resolution with multiple fallback options:
```python
if isinstance(mapping_val, dict):
    # 支持 { alias: xxx, overrides: { model_name: '...' } } 或直接平铺覆盖字段
    alias = mapping_val.get("alias") or mapping_val.get("name") or \
            mapping_val.get("module") or mapping_val.get("llm")
    overrides = mapping_val.get("overrides")
    if overrides is None:
        # 将除别名键外的其余键视为覆盖
        tmp = dict(mapping_val)
        for k in ["alias", "name", "module", "llm", "overrides"]:
            tmp.pop(k, None)
        overrides = tmp if len(tmp) > 0 else None
```

---

## Critical: System Resource & Process Management

### Server Restart Hanging Due to TTY Inheritance
Server restart subprocess was hanging when inheriting TTY in nohup/background mode, getting suspended by SIGTTIN signal.

**Solution:**
Properly detached subprocess with all I/O redirected to /dev/null:
```python
def restart_server():
    # Avoid TTY inheritance, redirect all I/O
    with open(os.devnull, "rb", buffering=0) as devnull_in, \
         open(os.devnull, "ab", buffering=0) as devnull_out, \
         open(os.devnull, "ab", buffering=0) as devnull_err:
        subprocess.Popen(
            [sys.executable, "app.py"],
            stdin=devnull_in,
            stdout=devnull_out,
            stderr=devnull_err,
            start_new_session=True,  # New session to detach
            close_fds=True,  # Close all file descriptors
        )
    os._exit(0)

# Execute in daemon thread to avoid blocking event loop
threading.Thread(target=restart_server, daemon=True).start()
```

### Thread Pool Resource Exhaustion
Default thread pool size was too large, causing context switching overhead and memory issues in high-concurrency scenarios.

**Solution:**
Reduced default thread pool size with configurable override:
```python
try:
    meeting_cfg = self.config.get("meeting", {})
    # Default to 2 workers, configurable via meeting.threadpool_max_workers
    default_workers = 2
    max_workers = int(meeting_cfg.get("threadpool_max_workers", default_workers))
    if max_workers < 1:
        max_workers = default_workers
except Exception:
    max_workers = 2
self.executor = ThreadPoolExecutor(max_workers=max_workers)
```

### Event Loop Conflicts in Memory Saving
Memory saving was failing due to event loop conflicts when running async operations in threads.

**Solution:**
Created a new event loop for thread-based async operations:
```python
def save_memory_task():
    try:
        # Create new event loop to avoid conflicts with main loop
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

### Queue Clearing Blocking Operations
Queue clearing operations were using blocking `get()` calls which could hang the system.

**Solution:**
Changed to non-blocking queue clearing:
```python
def clear_queues(self):
    """Clear all task queues"""
    for q in [self.tts.tts_text_queue, self.tts.tts_audio_queue, self.report_queue]:
        if not q:
            continue
        while True:
            try:
                q.get_nowait()  # Non-blocking get
            except queue.Empty:
                break  # Queue is empty, done
```

---

## Important: UI/UX Issues

### UI Display Formatting Issues - Wrong Header and Unwanted Bullet Points
The hardware screen was displaying ">对话中" instead of "> 正在对话中：" (missing space and text), and showing unwanted bullet points (•) in history items.

**Solution:**
Fixed by updating the header_lines and history_lines formatting:
```python
# Before:
header_lines = [">对话中：", "────────────────────────────────"]
history_lines.append(f"• {s}")

# After:
header_lines = ["> 正在对话中：", "────────────────────────────────"]
history_lines.append(f"{s}")  # Removed bullet point
```

### Dialog Display Limited to Fixed Lines Instead of Dynamic Adjustment
The dialog mode was hardcoded to display only 6-10 lines instead of dynamically adjusting based on device capabilities.

**Solution:**
Added `get_lines_per_page()` function to dynamically fetch device's line capacity:
```python
from core.utils.device_registry import get_badge_and_owner, get_lines_per_page

# Dynamic line calculation based on device
max_lines = get_lines_per_page(getattr(self, "device_id", ""), default_value=10)

# Function implementation
def get_lines_per_page(device_id: str, default_value: int = 8) -> int:
    """Returns max displayable lines per page for device"""
    _load_if_needed()
    did = _normalize_device_id(device_id)
    if did is None:
        return int(default_value)
    try:
        devices = (_CACHE.get("data") or {}).get("devices") or {}
        meta = devices.get(did) or {}
        v = int(meta.get("lines_per_page", default_value))
        return v if v > 0 else int(default_value)
    except Exception:
        return int(default_value)
```

### Dialog Refresh Too Fast for Users to Read
When displaying long conversations, content was refreshing too quickly (0.55 seconds) between batches.

**Note:** Issue identified but specific timing adjustment solution not shown in the block.
```python
# Current implementation - may be too fast
if idx == 0 and len(batches) > 1:
    try:
        asyncio.run_coroutine_threadsafe(asyncio.sleep(0.55), self.loop).result()
    except Exception:
        pass
```

### Connection Timeout Warning Not Giving Users Chance to Continue
Connections were timing out without warning users or giving them a chance to keep the connection alive.

**Solution:**
Added timeout warning with buffer period and reset mechanism:
```python
def reset_timeout(self):
    """重置超时计时器"""
    if self.timeout_task and not self.timeout_task.done():
        self.timeout_task.cancel()
    self.timeout_task = asyncio.create_task(self._check_timeout())

async def _check_timeout(self):
    while not self.stop_event.is_set():
        await asyncio.sleep(self.timeout_seconds)
        if not self.stop_event.is_set():
            # Send warning first
            await self.websocket.send(json.dumps({
                "type": "system",
                "event": "timeout_warning",
                "message": "连接将因长时间空闲而关闭，如需继续请发送任意消息。"
            }))
            # Give 10 second buffer for user to respond
            await asyncio.sleep(10)
            if self.stop_event.is_set():
                break
            # Now close if still idle
            await self.close(self.websocket)

async def _route_message(self, message):
    """消息路由"""
    # 重置超时计时器
    self.reset_timeout()
    
    # 轻量 ping/keepalive：收到后仅重置计时器并忽略
    if isinstance(obj, dict) and obj.get("type") in ("ping", "keepalive"):
        await self.websocket.send(json.dumps({"type": "pong"}))
        return
```

---

## Important: Voice & Audio Processing

### VAD (Voice Activity Detection) State Machine Stuck
VAD state machine was getting stuck in "listening" state when device didn't send proper boundaries.

**Solution:**
Added fallback timeout mechanism for VAD:
```python
def check_vad_fallback(self):
    """Check if VAD fallback needed (no device boundary after fallback_ms)"""
    if self.listen_state != "listening":
        return False
    
    now_ms = int(time.time() * 1000)
    fallback_ms = int(meeting_cfg.get("vad_fallback_ms", 2000))
    last_event_ms = getattr(self, "_last_listen_event_ms", 0)
    
    if last_event_ms > 0 and (now_ms - last_event_ms) > fallback_ms:
        self.logger.bind(tag=TAG).debug(
            f"VAD兜底触发: {now_ms - last_event_ms}ms未见设备边界"
        )
        return True
    return False
```

### ASR Initialization Issues with Local vs Remote Services
ASR initialization was failing to properly distinguish between local and remote services, causing connection issues.

**Solution:**
Implemented service type detection and appropriate initialization:
```python
def _initialize_asr(self):
    """Initialize ASR"""
    if self._asr.interface_type == InterfaceType.LOCAL:
        # Local ASR service can be shared across connections
        asr = self._asr
    else:
        # Remote ASR needs separate instance per connection
        # Due to websocket connections and receive threads
        asr = initialize_asr(self.config)
    return asr
```

---

## Important: Data Processing & Integration

### MCP Tool Call Result Parsing Failures
MCP (Model Context Protocol) tool calls were returning results that couldn't be parsed properly.

**Solution:**
Added robust JSON parsing with error handling:
```python
resultJson = None
if isinstance(result, str):
    try:
        resultJson = json.loads(result)
    except Exception as e:
        self.logger.bind(tag=TAG).error(f"解析MCP工具返回结果失败: {e}")

# Handle visual model responses differently
if (resultJson is not None 
    and isinstance(resultJson, dict) 
    and "action" in resultJson):
    result = ActionResponse(
        action=Action[resultJson["action"]],
        result=None,
        response=resultJson.get("response", ""),
    )
else:
    result = ActionResponse(
        action=Action.REQLLM, 
        result=result, 
        response=""
    )
```

### Component Initialization Failures During Private Config Loading
Multiple initialization failures were occurring when loading private device configurations from API.

**Solution:**
Added comprehensive error handling and fallback logic:
```python
try:
    modules = initialize_modules(
        self.logger,
        private_config,
        init_vad,
        init_asr,
        init_llm,
        init_tts,
        init_memory,
        init_intent,
    )
except Exception as e:
    self.logger.bind(tag=TAG).error(f"初始化组件失败: {e}")
    modules = {}
```

---

## Code Quality Issues

### Duplicate Send Method Definitions
The code had duplicate definitions of `send_json` and `send_text` methods causing confusion.

**Solution:**
Consolidated to single unified implementations with proper error handling and removed duplicates.