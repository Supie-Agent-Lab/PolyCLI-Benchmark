# Pain Points from Backend Block 6

## Issue: Device ID parsing from WebSocket handshake
The system had difficulty extracting device-id from various WebSocket paths and headers, with different clients sending it in different formats.

**Solution:**
Implemented a robust multi-source extraction with fallback:
```python
def _normalize_id(v):
    try:
        if v is None:
            return None
        vv = str(v).strip().strip('"').strip("'")
        return vv.lower() if vv else None
    except Exception:
        return None

# Check multiple header variations
header_device_id = _normalize_id(
    self.headers.get("device-id")
    or self.headers.get("device_id")
    or self.headers.get("x-device-id")
    or self.headers.get("x-device_id")
)

# Fallback to auto-generated ID if not found
if not chosen_device_id:
    auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
    self.headers["device-id"] = auto_device_id
```

---

## Issue: Memory save failures during connection close
Saving memory synchronously during connection close was blocking and causing errors.

**Solution:**
Moved memory saving to background thread to avoid blocking:
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

# Start thread without waiting
threading.Thread(target=save_memory_task, daemon=True).start()
```

---

## Issue: WebSocket send failures on closed connections
Sending messages to closed WebSocket connections was causing exceptions and interrupting flow.

**Solution:**
Implemented unified send wrappers with error handling:
```python
async def send_json(self, data: dict) -> bool:
    if not self.websocket:
        self.logger.bind(tag=TAG).warning("send_json: websocket is None")
        return False
    
    try:
        if hasattr(self.websocket, 'send_json'):
            await self.websocket.send_json(data)
        else:
            await self.websocket.send(json.dumps(data, ensure_ascii=False))
        return True
    except websockets.exceptions.ConnectionClosed:
        self.logger.bind(tag=TAG).debug(f"send_json: connection closed for device {self.device_id}")
        return False
    except Exception as e:
        self.logger.bind(tag=TAG).warning(f"send_json failed for device {self.device_id}: {e}")
        return False
```

---

## Issue: VAD state machine getting stuck
Voice Activity Detection (VAD) state transitions were getting stuck in certain states, especially when device boundaries weren't properly detected.

**Solution:**
Implemented VAD fallback mechanism with timeout:
```python
def check_vad_fallback(self):
    if self.listen_state != "listening":
        return False
    if self.client_listen_mode != "manual":
        return False
    now_ms = int(time.time() * 1000)
    fallback_ms = 2000  # Default 2 seconds
    last_event_ms = getattr(self, "_last_listen_event_ms", 0)
    if last_event_ms > 0 and (now_ms - last_event_ms) > fallback_ms:
        self.logger.bind(tag=TAG).debug(f"VAD兜底触发: {now_ms - last_event_ms}ms未见设备边界")
        return True
    return False
```

---

## Issue: Component initialization failures
Components (ASR, TTS, LLM) were failing to initialize properly, especially with differentiated configurations from API.

**Solution:**
Wrapped initialization in try-except blocks with fallback to empty modules:
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

## Issue: Server restart causing TTY issues
Server restart was failing in background/nohup mode due to SIGTTIN signal when trying to access TTY.

**Solution:**
Properly detached subprocess with all I/O redirected to devnull:
```python
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
```

---

## Issue: ThreadPoolExecutor shutdown blocking
Executor shutdown was blocking during connection cleanup, especially with Python version differences.

**Solution:**
Implemented version-compatible shutdown with cancel_futures:
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

## Issue: Function call argument parsing errors
MCP tool calls were failing when function arguments came in different formats (string vs dict).

**Solution:**
Added flexible argument parsing with proper error handling:
```python
args_dict = function_arguments
if isinstance(function_arguments, str):
    try:
        args_dict = json.loads(function_arguments)
    except json.JSONDecodeError:
        self.logger.bind(tag=TAG).error(f"无法解析 function_arguments: {function_arguments}")
        return ActionResponse(
            action=Action.REQLLM, result="参数解析失败", response=""
        )
```

---

## Issue: LLM instance caching and mode switching
Different modes (chat, meeting, coding) needed different LLM configurations but were using the same instance.

**Solution:**
Implemented LLM caching by purpose/mode:
```python
def get_llm_for(self, purpose: str):
    key = str(purpose or "chat").lower()
    
    # Cache hit
    if key in self._llm_cache and self._llm_cache[key] is not None:
        return self._llm_cache[key]
    
    # Create and cache new instance based on configuration
    mapping_val = mapping.get(key)
    if mapping_val is None:
        self.logger.bind(tag=TAG).warning(
            f"get_llm_for: 未找到用途 {key} 的 llm_by_mode 配置，回退到 default"
        )
        self._llm_cache[key] = self.llm
        return self.llm
```

---

## Issue: Connection timeout warnings not being sent
Connections were timing out without warning users, leading to unexpected disconnections.

**Solution:**
Added timeout warning with grace period:
```python
try:
    await self.websocket.send(json.dumps({
        "type": "system",
        "event": "timeout_warning",
        "message": "连接将因长时间空闲而关闭，如需继续请发送任意消息。"
    }))
except Exception:
    pass
# Give 10 second buffer
await asyncio.sleep(10)
```

---

## Issue: Queue clearing during connection cleanup
Task queues (TTS, audio) weren't being properly cleared, causing memory leaks.

**Solution:**
Implemented non-blocking queue clearing:
```python
def clear_queues(self):
    if self.tts:
        for q in [self.tts.tts_text_queue, self.tts.tts_audio_queue, self.report_queue]:
            if not q:
                continue
            while True:
                try:
                    q.get_nowait()
                except queue.Empty:
                    break
```

---

## Issue: Duplicate send_json and send_text methods
The code had duplicate method definitions causing confusion and potential bugs.

**Solution:**
Consolidated into single unified methods with proper error handling and return values to indicate success/failure.

---

## Issue: Authentication errors not properly handled
Authentication failures were causing ungraceful connection terminations.

**Solution:**
Added specific exception handling for authentication:
```python
except AuthenticationError as e:
    self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
    return
```

---

## Issue: Client IP extraction failures
Getting client IP from WebSocket remote_address was failing in some configurations.

**Solution:**
Added robust IP extraction with fallback:
```python
try:
    remote = getattr(ws, "remote_address", None)
    if isinstance(remote, tuple) and len(remote) >= 1:
        self.client_ip = remote[0]
    else:
        self.client_ip = str(remote) if remote is not None else ""
except Exception:
    self.client_ip = ""
```