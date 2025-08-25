# Pain Points from Backend Block 6 - Merged

## Critical Issues

### Issue: Duplicate send_json and send_text method definitions causing confusion
The code had multiple definitions of `send_json` and `send_text` methods (lines 1123-1170, 1211-1232, 2711-2758, 2799-2819), leading to method overwriting and inconsistent behavior.

**Solution:**
Consolidated to a single implementation with proper error handling:
```python
async def send_json(self, data: dict) -> bool:
    """统一的 JSON 消息发送封装，包含错误处理
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not self.websocket:
        self.logger.bind(tag=TAG).warning("send_json: websocket is None")
        return False
    
    try:
        # 优先使用 send_json 方法
        if hasattr(self.websocket, 'send_json'):
            await self.websocket.send_json(data)
        else:
            # 回退到字符串发送
            await self.websocket.send(json.dumps(data, ensure_ascii=False))
        return True
    except websockets.exceptions.ConnectionClosed:
        # 连接已关闭，静默处理（预期情况）
        self.logger.bind(tag=TAG).debug(f"send_json: connection closed for device {self.device_id}")
        return False
    except Exception as e:
        # 其他异常，记录警告但不中断
        self.logger.bind(tag=TAG).warning(f"send_json failed for device {self.device_id}: {e}")
        return False
```

---

### Issue: Device ID parsing failure from WebSocket handshake
The system couldn't properly extract device-id from various WebSocket path formats and headers, leading to auto-generated fallback IDs. Different clients were sending it in different formats.

**Solution:**
Implemented comprehensive device ID parsing with multiple fallback strategies:
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
        
# 赋值优先级：Query > Header > 回退
chosen_device_id = device_id_from_query or header_device_id or header_client_id
chosen_client_id = client_id_from_query or header_client_id or chosen_device_id

if chosen_device_id:
    self.headers["device-id"] = chosen_device_id
    if chosen_client_id:
        self.headers["client-id"] = chosen_client_id
else:
    # 容错：仍未取到则自动分配，保证连接可用
    auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
    self.headers["device-id"] = auto_device_id
    self.headers["client-id"] = auto_device_id
```

---

### Issue: Memory save blocking connection close
Saving memory to file during connection close was blocking and could delay the connection cleanup process.

**Solution:**
Made memory saving asynchronous using a daemon thread:
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

## Display & UI Issues

### Issue: Text rendering overflow on hardware screen (300x400)
Long text from LLM responses would overflow the hardware screen width (300px) and cause display issues, with content being cut off or screen freezing. ASCII and CJK characters have different display widths, causing layout issues.

**Solution:**
Implemented text wrapping and truncation functions with proper character width detection:
```python
def _char_display_width(ch: str) -> int:
    """中日韩全角/宽字符按2，其他按1"""
    try:
        if unicodedata.east_asian_width(ch) in ("F", "W"):
            return 2
        return 1
    except Exception:
        return 1

def wrap_label_text(label: str, text: str, max_units_per_line: int = 40) -> List[str]:
    """按显示宽度将 label+text 拆分为多行。每行都带相同的 label。"""
    label = str(label or "")
    text = str(text or "")
    # 计算每行可用宽度（扣除label占用）
    label_units = sum(_char_display_width(c) for c in label)
    avail = max(8, max_units_per_line - label_units)
    
    lines: List[str] = []
    current: List[str] = []
    total = 0
    
    for ch in text:
        if ch == "\n":
            flush()
            current, total = [], 0
            continue
        w = _char_display_width(ch)
        if total + w > avail:
            flush()
            current, total = [ch], w
        else:
            current.append(ch)
            total += w
```

---

### Issue: Screen refresh blocking with extremely long responses
Very long LLM responses would cause the hardware screen to freeze or fail to refresh, particularly with weather reports that would get stuck at "未来7天" with remaining content invisible.

**Solution:**
Implemented paginated rendering with batched sending and circular buffer:
```python
# 环形窗口：最多10行，超过则保留末尾10行（模拟"从第一行重新刷新"）
max_lines = 10
if len(items) > max_lines:
    items = items[-max_lines:]
payload_final = {
    "type": "ui.render",
    "id": f"dlg-final-{self.sentence_id or ''}",
    "page": "dialog.chat",
    "header": {},
    "body": {"kind": "list", "items": items},
    "footer": {"hint": build_chat_footer_hint()}
}
```
- Split responses into chunks of 5 lines per frame
- Added minimum 500ms interval between frames to avoid rate limiting
- Enabled "分批渲染" (batch rendering) mode for stable display of long content

---

## Voice & Audio Issues

### Issue: VAD (Voice Activity Detection) state machine getting stuck
The listen state transitions (idle -> listening -> finalizing -> idle) could get stuck, preventing proper voice detection, especially when device boundaries weren't properly detected.

**Solution:**
Implemented proper state machine with timeouts and fallback mechanisms:
```python
async def transition_listen_state(self, new_state: str):
    """状态机转换：idle -> listening -> finalizing -> idle"""
    old_state = self.listen_state
    if old_state == "idle" and new_state == "listening":
        self.listen_state = "listening"
        self._last_listen_event_ms = int(time.time() * 1000)
        self.logger.bind(tag=TAG).debug("Listen state: idle -> listening")
    elif old_state == "listening" and new_state == "finalizing":
        self.listen_state = "finalizing"
        self.logger.bind(tag=TAG).debug("Listen state: listening -> finalizing")
        # 触发一次handle_voice_stop
        if len(self.asr_audio) > 0:
            from core.handle.receiveAudioHandle import handleAudioMessage
            await handleAudioMessage(self, b"")
    elif old_state == "finalizing" and new_state == "idle":
        self.listen_state = "idle"
        self.logger.bind(tag=TAG).debug("Listen state: finalizing -> idle")
        self.reset_vad_states()

def check_vad_fallback(self):
    """检查是否需要VAD兜底（超过fallback_ms未见设备边界）"""
    if self.listen_state != "listening":
        return False
    if self.client_listen_mode != "manual":
        return False
    now_ms = int(time.time() * 1000)
    fallback_ms = 2000  # 默认2秒
    last_event_ms = getattr(self, "_last_listen_event_ms", 0)
    if last_event_ms > 0 and (now_ms - last_event_ms) > fallback_ms:
        self.logger.bind(tag=TAG).debug(f"VAD兜底触发: {now_ms - last_event_ms}ms未见设备边界")
        return True
    return False
```

---

### Issue: Premature Idle Timeout During TTS Playback
System was triggering "长时间未说话，退出聆听" timeout while TTS was still playing or text was still being displayed.

**Solution:**
Modified timeout logic to only start counting after TTS playback completes:
```python
# In tts_text_priority_thread:
if message.sentence_type == SentenceType.FIRST:
    try:
        # 开始播报：标记服务端正在讲话，暂停无语音超时
        self.conn.client_is_speaking = True
    except Exception:
        pass

# In _audio_play_priority_thread:
elif message[0] == SentenceType.LAST:
    self.playing = False
    try:
        # 播放完毕：清除讲话状态，允许无语音计时重新开始
        self.conn.clearSpeakStatus()
    except Exception:
        pass

# In no_voice_close_connect:
try:
    if hasattr(conn, "tts") and hasattr(conn.tts, "tts_audio_queue"):
        if not conn.tts.tts_audio_queue.empty():
            conn.client_no_voice_last_time = 0.0
            return
    # 也可根据服务端讲话状态阻断计时
    if getattr(conn, "client_is_speaking", False):
        conn.client_no_voice_last_time = 0.0
        return
except Exception:
    pass
```

---

## Session Management Issues

### Issue: Chat history being saved multiple times during session
The system was incorrectly saving chat summaries after each round of conversation instead of only when the session ends.

**Solution:**
Modified to only save chat summary on connection close:
```python
# In close() method - save summary only when disconnecting
try:
    latest_user = None
    latest_assistant = None
    for m in reversed(self.dialogue.dialogue if isinstance(self.dialogue, Dialogue) else []):
        if m.role == "assistant" and latest_assistant is None:
            latest_assistant = m.content
        elif m.role == "user" and latest_user is None:
            latest_user = m.content
        if latest_user and latest_assistant:
            break
    if latest_user or latest_assistant:
        try:
            _, owner_name = get_badge_and_owner(getattr(self, "device_id", "")) or ("", "")
        except Exception:
            owner_name = ""
        summary_text = f"{owner_name or '用户'}: {latest_user or ''} / 喵喵同学: {latest_assistant or ''}"
        append_chat_summary(getattr(self, "device_id", ""), summary_text, max_items=2)
except Exception:
    pass
```

---

## System & Infrastructure Issues

### Issue: Thread pool resource exhaustion with high connection count
Default thread pool size was too large, causing excessive context switching and memory usage.

**Solution:**
Reduced thread pool size with configurable override:
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

### Issue: Backend Restart Using os._exit(0) Too Abruptly
Server restart was using `os._exit(0)` which terminates immediately without cleanup. Also failing in background/nohup mode due to SIGTTIN signal when trying to access TTY.

**Solution:**
Implemented proper subprocess handling with detached process:
```python
def restart_server():
    """实际执行重启的方法"""
    time.sleep(1)
    self.logger.bind(tag=TAG).info("执行服务器重启...")
    # 后台重启：避免继承TTY，全部重定向，保证 nohup/backgroud 模式不被SIGTTIN挂起
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
```

---

### Issue: Thread Pool Shutdown Not Handling Python Version Differences
Thread pool shutdown was failing on Python versions < 3.9 due to missing `cancel_futures` parameter.

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

### Issue: WebSocket attribute compatibility issues
Different WebSocket libraries have different attribute names (request_headers vs headers, etc.), causing failures.

**Solution:**
Added comprehensive attribute checking with fallbacks:
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

## Tool & Integration Issues

### Issue: MCP tool call error handling incomplete
MCP (Model Context Protocol) tool calls could fail silently or return unhelpful error messages. Function arguments came in different formats (string vs dict).

**Solution:**
Added comprehensive error handling for MCP tool calls with flexible argument parsing:
```python
def _handle_mcp_tool_call(self, function_call_data):
    function_arguments = function_call_data["arguments"]
    function_name = function_call_data["name"]
    try:
        args_dict = function_arguments
        if isinstance(function_arguments, str):
            try:
                args_dict = json.loads(function_arguments)
            except json.JSONDecodeError:
                self.logger.bind(tag=TAG).error(
                    f"无法解析 function_arguments: {function_arguments}"
                )
                return ActionResponse(
                    action=Action.REQLLM, result="参数解析失败", response=""
                )
        # ... execute tool
    except Exception as e:
        self.logger.bind(tag=TAG).error(f"MCP工具调用错误: {e}")
        return ActionResponse(
            action=Action.REQLLM, result="工具调用出错", response=""
        )
```

---

### Issue: LLM instance caching and mode switching
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

## Minor Issues

### Issue: Dialog UI format inconsistency 
The dialog UI would instantly change format after refresh, showing multiple "喵喵同学:" prefixes instead of maintaining consistent format.

**Solution:**
Ensured consistent dialog formatting throughout the session by maintaining proper message structure in the dialog builder and avoiding duplicate assistant name prefixes in the rendering logic.

---

### Issue: Component initialization failures
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

### Issue: Connection timeout warnings not being sent
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

### Issue: Queue clearing during connection cleanup
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

### Issue: Authentication errors not properly handled
Authentication failures were causing ungraceful connection terminations.

**Solution:**
Added specific exception handling for authentication:
```python
except AuthenticationError as e:
    self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
    return
```

---

### Issue: Client IP extraction failures
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