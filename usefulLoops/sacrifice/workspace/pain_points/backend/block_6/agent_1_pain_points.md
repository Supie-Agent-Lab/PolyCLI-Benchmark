# Pain Points from Backend Block 6

## Issue: Duplicate send_json and send_text method definitions causing confusion
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

## Issue: Text rendering overflow on hardware screen (300x400)
Long text from LLM responses would overflow the hardware screen width (300px) and cause display issues, with content being cut off or screen freezing.

**Solution:**
Implemented text wrapping and truncation functions to ensure proper display:
```python
def _wrap_text_to_width(text):
    """将文本按硬件屏幕宽度换行"""
    # 实现文本包装逻辑，确保单行不超过屏幕宽度
    text = _wrap_text_to_width(text)
    
def _truncate_to_width(text):
    """截断文本以适应屏幕宽度"""
    # 对列表项进行截断处理
    items = [_truncate_to_width(it) for it in items]
```

---

## Issue: Screen refresh blocking with extremely long responses
Very long LLM responses would cause the hardware screen to freeze or fail to refresh, particularly with weather reports that would get stuck at "未来7天" with remaining content invisible.

**Solution:**
Implemented paginated rendering with batched sending:
- Split responses into chunks of 5 lines per frame
- Added minimum 500ms interval between frames to avoid rate limiting
- Enabled "分批渲染" (batch rendering) mode for stable display of long content

---

## Issue: Device ID parsing failure from WebSocket handshake
The system couldn't properly extract device-id from various WebSocket path formats and headers, leading to auto-generated fallback IDs.

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
        
# 赋值优先级：Query > Header > 回退
chosen_device_id = device_id_from_query or header_device_id or header_client_id
```

---

## Issue: Memory save blocking connection close
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

## Issue: Chat history being saved multiple times during session
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

## Issue: Thread pool resource exhaustion with high connection count
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

## Issue: WebSocket attribute compatibility issues
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

## Issue: MCP tool call error handling incomplete
MCP (Model Context Protocol) tool calls could fail silently or return unhelpful error messages.

**Solution:**
Added comprehensive error handling for MCP tool calls:
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

## Issue: Dialog UI format inconsistency 
The dialog UI would instantly change format after refresh, showing multiple "喵喵同学:" prefixes instead of maintaining consistent format.

**Solution:**
Ensured consistent dialog formatting throughout the session by maintaining proper message structure in the dialog builder and avoiding duplicate assistant name prefixes in the rendering logic.

---

## Issue: VAD (Voice Activity Detection) state machine getting stuck
The listen state transitions (idle -> listening -> finalizing -> idle) could get stuck, preventing proper voice detection.

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
    # ... check timeout and trigger fallback
```