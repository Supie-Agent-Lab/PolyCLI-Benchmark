# Pain Points from Backend Block 7

## Issue: UI displays wrong dialog header format and bullet points
The hardware screen was showing ">对话中" instead of "> 正在对话中：" (with space and colon), and history items had unwanted bullet points (•) that shouldn't appear on the hardware display.

**Solution:**
Changed the header line from `">对话中："` to `"> 正在对话中："` and removed bullet points from history items:
```python
# Before
header_lines = [">对话中：", "────────────────────────────────"]
# After  
header_lines = ["> 正在对话中：", "────────────────────────────────"]

# Before
for s in summaries:
    history_lines.append(f"• {s}")
# After
for s in summaries:
    history_lines.append(f"{s}")
```

---

## Issue: Dialog display limited to fixed 6 lines instead of dynamic adjustment
The dialog mode was hardcoded to display only 6-10 lines (`max_lines = 10`) instead of dynamically adjusting based on the device's display capabilities.

**Solution:**
Added `get_lines_per_page()` function to dynamically fetch the device's line capacity from configuration:
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

---

## Issue: Dialog refresh happening too fast for users to read
When displaying long conversations, the content was refreshing too quickly (0.55 seconds) between batches, not giving users enough time to read.

**Solution:**
The issue was identified but the exact timing adjustment wasn't shown in this block. The code shows:
```python
# Current implementation - may be too fast
if idx == 0 and len(batches) > 1:
    try:
        asyncio.run_coroutine_threadsafe(asyncio.sleep(0.55), self.loop).result()
    except Exception:
        pass
```

---

## Issue: Memory save failures during connection close
The memory save operation was failing when connections closed, potentially losing conversation history.

**Solution:**
Implemented asynchronous memory saving in a separate thread to avoid blocking connection closure:
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

---

## Issue: Device registration failures not handled properly
Device registration could fail but the connection would still proceed, causing issues later.

**Solution:**
Added explicit registration check and proper error handling:
```python
if self.server and self.device_id:
    ok = await self.server.register_device_handler(self.device_id, self)
    if ok is False:
        self.logger.bind(tag=TAG).error(f"设备注册失败: {self.device_id}")
        await ws.send("设备注册失败")
        await self.close(ws)
        return
```

---

## Issue: Component initialization failures during private config loading
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

## Issue: LLM selection by mode failing with fallback issues
The `get_llm_for()` method was failing to properly select mode-specific LLMs and fallback to default.

**Solution:**
Implemented comprehensive fallback strategy with proper error handling:
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
    
    # Multiple fallback levels:
    # 1. Try to get from llm_by_mode config
    # 2. Fall back to default mapping
    # 3. Fall back to main LLM instance
    try:
        srv = getattr(self, "server", None)
        if srv and hasattr(srv, "get_or_create_llm"):
            instance = srv.get_or_create_llm(alias, overrides)
            if instance is not None:
                self._llm_cache[key] = instance
                return instance
    except Exception as e:
        self.logger.bind(tag=TAG).warning(f"get_llm_for 失败({key}): {e}，回退默认LLM")
    
    # Final fallback
    self._llm_cache[key] = self.llm
    return self.llm
```

---

## Issue: MCP tool call result parsing failures
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

---

## Issue: ASR initialization issues with local vs remote services
ASR (Automatic Speech Recognition) initialization was failing to properly distinguish between local and remote services, causing connection issues.

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

## Issue: Thread pool exhaustion in high-concurrency scenarios
Default thread pool size was causing resource exhaustion under load.

**Solution:**
Made thread pool size configurable with sensible defaults:
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

---

## Issue: Device ID parsing failures from WebSocket handshake
Device IDs weren't being properly extracted from WebSocket handshake headers and query parameters.

**Solution:**
Implemented multi-level parsing with fallback to auto-generated IDs:
```python
# Try server's handshake parser first
device_id_from_query = None
if server_obj and hasattr(server_obj, "parse_ids_from_handshake"):
    d, c, rawp = server_obj.parse_ids_from_handshake(ws, path)
    device_id_from_query = d

# Fallback to header parsing (multiple formats)
header_device_id = _normalize_id(
    self.headers.get("device-id")
    or self.headers.get("device_id")
    or self.headers.get("x-device-id")
    or self.headers.get("x-device_id")
)

# Priority: Query > Header > Auto-generate
chosen_device_id = device_id_from_query or header_device_id or header_client_id
if not chosen_device_id:
    # Auto-generate if all parsing fails
    auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
    self.headers["device-id"] = auto_device_id
    self.logger.bind(tag=TAG).warning(
        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}"
    )
```