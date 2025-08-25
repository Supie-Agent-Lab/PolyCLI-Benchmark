# Pain Points from Backend Block 7

## Issue: UI Display Formatting Issues - Wrong Header and Unwanted Bullet Points
The hardware screen was displaying ">对话中" instead of "> 正在对话中：" (missing space and text), and showing unwanted bullet points (•) in history items.

**Solution:**
Fixed by updating the header_lines and history_lines formatting in the chat rendering code:
```python
# Before:
header_lines = [">对话中：", "────────────────────────────────"]
history_lines.append(f"• {s}")

# After:
header_lines = ["> 正在对话中：", "────────────────────────────────"]
history_lines.append(f"{s}")  # Removed bullet point
```

---

## Issue: LLM Instance Management - Missing Fallback and Configuration Issues
The system wasn't properly handling cases where LLM configuration for specific purposes (chat, meeting, coding, etc.) was missing, leading to errors.

**Solution:**
Implemented comprehensive fallback logic with multiple layers:
```python
def get_llm_for(self, purpose: str):
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
        instance = srv.get_or_create_llm(alias, overrides)
    except Exception as e:
        # Final fallback to default LLM
        self.logger.bind(tag=TAG).warning(f"get_llm_for 失败({key}): {e}，回退默认LLM")
        self._llm_cache[key] = self.llm
        return self.llm
```

---

## Issue: WebSocket Connection Header Parsing Failures
The system was failing to parse device-id from WebSocket handshake headers due to various header formats and naming inconsistencies.

**Solution:**
Implemented multi-layer parsing with automatic fallback:
```python
# 1. Try server's unified handshake parser
if server_obj and hasattr(server_obj, "parse_ids_from_handshake"):
    d, c, rawp = server_obj.parse_ids_from_handshake(ws, path)

# 2. Fallback to Header parsing with multiple variations
header_device_id = _normalize_id(
    self.headers.get("device-id")
    or self.headers.get("device_id")  
    or self.headers.get("x-device-id")
    or self.headers.get("x-device_id")
)

# 3. Auto-assign if still missing
if not chosen_device_id:
    auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
    self.headers["device-id"] = auto_device_id
    self.logger.bind(tag=TAG).warning(
        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}"
    )
```

---

## Issue: Event Loop Conflicts in Memory Saving
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

# Start thread without waiting
threading.Thread(target=save_memory_task, daemon=True).start()
```

---

## Issue: WebSocket Send Failures Breaking Main Flow
WebSocket send operations were throwing exceptions that interrupted the main message flow.

**Solution:**
Implemented unified send wrappers with error handling:
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

## Issue: VAD (Voice Activity Detection) State Machine Stuck
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

---

## Issue: Queue Clearing Blocking Operations
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

## Issue: Thread Pool Resource Exhaustion
Default thread pool size was too large, causing context switching overhead and memory issues.

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

---

## Issue: Server Restart Hanging Due to TTY Inheritance
Server restart subprocess was hanging when inheriting TTY in nohup/background mode.

**Solution:**
Properly detached subprocess with all I/O redirected:
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
```

---

## Issue: Device Registration Failures Not Handled
Device registration failures were not properly handled, leading to undefined behavior.

**Solution:**
Added explicit registration failure handling:
```python
if self.server and self.device_id:
    ok = await self.server.register_device_handler(self.device_id, self)
    if ok is False:
        self.logger.bind(tag=TAG).error(f"设备注册失败: {self.device_id}")
        await ws.send("设备注册失败")
        await self.close(ws)
        return  # Stop processing
```

---

## Issue: Duplicate Send Method Definitions
The code had duplicate definitions of `send_json` and `send_text` methods causing confusion.

**Solution:**
Consolidated to single unified implementations with proper error handling and removed duplicates.

---

## Issue: Connection Timeout Warning Not Giving Users Chance to Continue
Connections were timing out without warning users or giving them a chance to keep the connection alive.

**Solution:**
Added timeout warning with buffer period:
```python
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
```