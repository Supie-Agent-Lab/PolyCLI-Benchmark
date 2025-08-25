# Pain Points from Backend Block 6

## Issue: Duplicate send_json and send_text Methods
The ConnectionHandler class has duplicate `send_json` and `send_text` methods defined, causing confusion and potential errors.

**Solution:**
Removed duplicate method definitions and kept only one implementation with proper error handling:
```python
async def send_json(self, data: dict) -> bool:
    """统一的 JSON 消息发送封装，包含错误处理"""
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
```

---

## Issue: History Storage During Active Session
Chat history was being saved during an active conversation session, but requirements specified history should only be saved when the session ends.

**Solution:**
Modified to only save history summary on connection close:
```python
async def close(self, ws=None):
    """资源清理方法"""
    try:
        # 在会话关闭前，生成一次本轮"完整对话摘要"，加入历史（仅在存在有效轮次时）
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
                summary_text = f"{owner_name or '用户'}: {latest_user or ''} / 喵喵同学: {latest_assistant or ''}"
                append_chat_summary(getattr(self, "device_id", ""), summary_text, max_items=2)
        except Exception:
            pass
```

---

## Issue: Text Overflow on Hardware Display
Long text from user input and LLM output was being truncated with ellipsis, making content unreadable on 300x400 pixel hardware screen.

**Solution:**
Implemented text wrapping to automatically split long text into multiple lines:
```python
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

## Issue: Premature Idle Timeout During TTS Playback
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

## Issue: Screen Refresh Stuck with Long Content
When displaying long content like weather forecasts, the screen would get stuck at line 6 ("未来7天") and remaining content wouldn't be visible.

**Solution:**
Implemented circular buffer limiting display to 10 lines maximum:
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

---

## Issue: Backend Restart Using os._exit(0) Too Abruptly
Server restart was using `os._exit(0)` which terminates immediately without cleanup.

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

## Issue: Character Width Calculation for CJK Characters
ASCII and CJK characters have different display widths, causing layout issues.

**Solution:**
Implemented proper character width detection using Unicode properties:
```python
def _char_display_width(ch: str) -> int:
    """中日韩全角/宽字符按2，其他按1"""
    try:
        if unicodedata.east_asian_width(ch) in ("F", "W"):
            return 2
        return 1
    except Exception:
        return 1
```

---

## Issue: Thread Pool Shutdown Not Handling Python Version Differences
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

## Issue: Device ID Parsing from WebSocket Handshake
Complex device ID extraction from various sources (query params, headers) with multiple fallback options was error-prone.

**Solution:**
Centralized device ID parsing with clear priority order:
```python
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

## Issue: Memory Save Task Blocking Connection Close
Memory saving was potentially blocking the connection close process.

**Solution:**
Made memory saving asynchronous using daemon thread:
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
    finally:
        # 立即关闭连接，不等待记忆保存完成
        await self.close(ws)
```