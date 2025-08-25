# Merged Pain Points - Backend Block 4

## Critical Issues (System Stability & Core Functionality)

### Issue: Task Watchdog Triggered and Stack Overflow
Audio loop task causing WDT (watchdog timer) resets, stack overflow, and `xTaskDelayUntil` assertion failures.

**Solution:**
Fixed audio loop timing and added proper task yielding:
```cpp
// AudioLoop 改为固定节拍
vTaskDelayUntil(&xLastWakeTime, pdMS_TO_TICKS(2));  // 周期 2ms
// 在无数据/早退分支处统一让步
if (no_data) {
    vTaskDelay(1);  // 主动让步避免饿死
}
// 降低任务优先级至 4
```
Additional fixes:
- Changed to fixed-beat `vTaskDelayUntil` with 2ms period
- Ensured `period >= 1 tick` to avoid `tasks.c:1476 (( xTimeIncrement > 0U ))` assertion
- Added `vTaskDelay(1ms)` in no-data/early-exit branches for yielding
- Reduced audio_loop task priority to 4 to prevent CPU monopolization

---

### Issue: WebSocket Reception Thread Stack Overflow
Heavy JSON parsing in the WebSocket receive thread was causing stack pressure and potential crashes.

**Solution:**
Implemented a thin receive thread that only copies strings and delegates parsing to the main loop:
```cpp
// 增加线程栈大小
CONFIG_PTHREAD_TASK_STACK_SIZE_DEFAULT=8192

// 接收线程瘦身：仅复制字符串
std::string json_copy = json_str;
Schedule([json_copy]() {
    // 在主循环中解析和处理JSON
    ParseAndHandleJson(json_copy);
});
```
- Reception thread only parses `hello` messages directly
- Other JSON messages are copied as strings and posted to main loop for parsing
- Significantly reduced stack usage in receive thread

---

### Issue: Wake Word Detection Concurrent Access Crash
Concurrent access to wake word detection pointers causing null reference crashes.

**Solution:**
Added null pointer checks and atomic flags for concurrency protection:
```cpp
// GetFeedSize() adds null pointer check
if (!afe_iface_ || !afe_data_) {
    return 512;  // Safe default when uninitialized
}
// Added atomic flag wwd_suspended_ to inhibit OnAudioInput path
// Added vTaskDelay(20ms) after StopDetection() for safe cleanup
```

---

### Issue: Thread Pool Shutdown Blocking on Connection Close
The executor shutdown was blocking the connection close process, causing delays and potential resource leaks.

**Solution:**
Modified the executor shutdown to use non-blocking mode with cancel_futures for Python 3.9+:
```python
# 最后关闭线程池（避免阻塞）
if self.executor:
    try:
        # Python 3.9+ 支持 cancel_futures
        self.executor.shutdown(wait=False, cancel_futures=True)
    except TypeError:
        self.executor.shutdown(wait=False)
    self.executor = None
```

---

## Major Issues (User Experience & Functionality)

### Issue: UI Stuck on "建立连接中，请稍候" During Dialog
After voice recognition and LLM processing, the hardware screen remained stuck displaying "建立连接中，请稍候" (establishing connection, please wait) even though the LLM had generated a response.

**Solution:**
Added proper state transitions and UI updates in chat flow:
```python
# 进入对话活跃态
self.current_mode = "dialog.active"

# 下发"开始对话"提示
payload_active = {
    "type": "ui.render",
    "id": "dlg-active",
    "page": "dialog.chat",
    "header": {},
    "body": {"kind": "text", "text": "开始对话"},
}
asyncio.run_coroutine_threadsafe(send_render(self, payload_active), self.loop)

# LLM回答后渲染最终文本
if len(response_message) > 0:
    final_text = "".join(response_message)
    payload_final = {
        "type": "ui.render",
        "id": f"dlg-final-{self.sentence_id or ''}",
        "page": "dialog.chat",
        "header": {},
        "body": {"kind": "text", "text": final_text},
        "footer": {"hint": "说\"开始聊天\"继续"}
    }
    asyncio.run_coroutine_threadsafe(send_render(self, payload_final), self.loop)
```

---

### Issue: Display Showing White Text on White Background
E-ink display was rendering text but it wasn't visible due to incorrect color settings.

**Solution:**
Fixed text rendering by explicitly setting foreground and background colors:
```cpp
// Changed from u8g2_->print(...) to u8g2_->drawUTF8(...)
// Explicitly set colors:
u8g2_->setForegroundColor(ST7306_COLOR_BLACK);
u8g2_->setBackgroundColor(ST7306_COLOR_WHITE);
u8g2_->drawUTF8(x, y, text);  // 改为 drawUTF8 instead of print
```
Also fixed default font colors in `u8g2_for_st73xx_impl.cpp` to use black foreground on white background.

---

### Issue: Top Banner Text Not Displaying
Red banner was showing but text was invisible or truncated.

**Solution:**
Enhanced banner rendering with adaptive layout:
```cpp
// 顶部横幅修复
u8g2_->setForegroundColor(ST7306_COLOR_WHITE);  // 白色文字
u8g2_->drawUTF8(x, y, text);  // 使用 drawUTF8
// 添加自适应两行布局，超宽自动降字号或拆分
```
- Fixed text drawing from `print(...)` to `drawUTF8(...)`
- Set foreground color to white for red background visibility
- Implemented auto-sizing: starts with 16pt bold, falls back to 14pt if too wide
- Added UTF-8 safe text splitting for two-line layout when needed
- Auto-adds ellipsis for truncated text

---

### Issue: Infinite Listening State After Wake-up
After hardware wake-up, the server would remain in listening state indefinitely until the user spoke, causing poor user experience.

**Solution:**
Implemented listening timeout mechanism with configurable delays:
```python
# Configuration options
ready_delay_ms = int(getattr(conn, "config", {}).get("listen_ready_delay_ms", 800))
preparing_timeout_ms = int(getattr(conn, "config", {}).get("listen_timeout_ms", 10000))

# Timeout handler
async def _preparing_timeout():
    await asyncio.sleep(max(0, preparing_timeout_ms) / 1000.0)
    if getattr(conn, "current_mode", "") == "dialog.preparing" and not getattr(conn, "client_have_voice", False):
        # Timeout without speech, return to idle
        await send_control(conn, action="play.tone", name="cancel")
        await send_render(conn, {
            "type": "ui.render",
            "id": "dlg-timeout",
            "page": "dialog.chat",
            "header": {},
            "body": {"kind": "text", "text": "长时间未说话，已退出聆听。"},
            "footer": {"hint": "说\"开始聊天\"再次进入"}
        })
        conn.current_mode = "connected.idle"
```

---

### Issue: Clock Updates Overwriting Rendered Pages
Welcome page clock updates were overwriting interactive UI renders.

**Solution:**
Implemented state-based mutual exclusion:
```cpp
// 切换到交互态，阻止时钟覆盖
current_state_ = STATE_INTERACTIVE_UI;
// 时钟更新只在 STATE_WELCOME/STATE_CARD_DISPLAY 下执行
if (current_state_ == STATE_WELCOME || current_state_ == STATE_CARD_DISPLAY) {
    UpdateClock();
}
```
- Clock updates only occur in `STATE_WELCOME/STATE_CARD_DISPLAY` states
- Render pages switch to `STATE_INTERACTIVE_UI` to block clock updates
- Display driver manages state transitions during rendering

---

## Backend Communication Issues

### Issue: JSON Parameter Parsing Failure in MCP Tool Calls
The system was unable to parse function arguments when they were passed as strings instead of dictionaries.

**Solution:**
Added JSON parsing logic to handle both dictionary and string arguments:
```python
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
```

---

### Issue: Device Control Commands Blocked for play.tone
The backend was only allowing `net.banner` action for device control, causing `play.tone` to be rejected with `[DROP_INVALID] type=device.control reason=unsupported-action action=play.tone`.

**Solution:**
Updated `render_sender.py` to allow both `net.banner` and `play.tone` actions:
```python
if action not in ("net.banner", "play.tone"):
    _logger.info(f"[DROP_INVALID] type=device.control reason=unsupported-action action={action} device={device_id}")
    return False, "invalid"
```

---

### Issue: WebSocket Send Method Inconsistency
Different WebSocket implementations have different send methods (send_json vs send with string).

**Solution:**
Created unified send wrappers with fallback mechanism:
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

### Issue: Device Identification and Routing Failures
Backend couldn't properly identify and route messages to specific devices.

**Solution:**
Added device identification in WebSocket connection URL:
```cpp
// 在 URL 追加查询参数
std::string url = base_url + "?device-id=" + mac_lower + "&client-id=" + uuid;
// 同时设置请求头
headers["Device-Id"] = mac_address;
headers["Client-Id"] = client_uuid;
```
- URL追加查询参数: ?device-id=<mac小写>&client-id=<uuid>
- Added corresponding request headers for stable device routing
- Backend parses device-id during handshake for proper routing

---

### Issue: WebSocket Connection Failed with TcpTransport Error -1
Hardware repeatedly disconnecting with "TcpTransport: Receive failed: -1" after wake word detection.

**Solution:**
Fixed by properly sequencing audio and connection handling:
```cpp
// 唤醒回调修复
ResumeAudioLoop();  // 恢复音频输入
StartListening();    // 使用已存在的控制通道
// 避免二次 OpenAudioChannel 导致连接冲突
```

---

## State Management Issues

### Issue: Mode-based Rendering Whitelist Too Restrictive
The rendering system was dropping valid render requests based on device mode, preventing UI updates during certain states.

**Solution:**
Implemented mode-based whitelist allowing rendering only during appropriate dialog states:
```python
def _allowed_by_target_mode(target_mode: str | None, payload: dict) -> bool:
    if target_mode not in ("dialog.preparing", "dialog.active"):
        return False
    t = (payload.get("type") or "").strip().lower()
    if t == "ui.render":
        page = (payload.get("page") or "").strip()
        return page == "dialog.chat"
    if t == "device.control":
        act = (payload.get("action") or "").strip()
        return act in ("net.banner", "play.tone")
    return False
```

---

### Issue: Meeting Mode State Persistence Lost
Meeting state wasn't being properly preserved across reconnections.

**Solution:**
Added state loading and timer management:
```python
# 尝试加载活跃会中状态
from core.handle.meeting_handle import load_active_state_if_any, start_meeting_timers
await load_active_state_if_any(conn)
start_meeting_timers(conn)
```

---

### Issue: Device Side VAD Fallback Not Working
Manual listening mode needed a fallback mechanism when device boundaries weren't detected within expected time.

**Solution:**
Implemented VAD fallback mechanism with configurable timeout:
```python
def check_vad_fallback(self):
    """检查是否需要VAD兜底（超过fallback_ms未见设备边界）"""
    if self.listen_state != "listening":
        return False
    if self.client_listen_mode != "manual":
        return False
    fallback_ms = meeting_cfg.get("vad_fallback_ms", 2000)  # Default 2s
    if last_event_ms > 0 and (now_ms - last_event_ms) > fallback_ms:
        self.logger.bind(tag=TAG).debug(f"VAD兜底触发: {now_ms - last_event_ms}ms未见设备边界")
        return True
```

---

## Performance & Resource Management

### Issue: Rate Limiting Not Working Properly
Multiple rapid render requests causing display issues, needed QPS control.

**Solution:**
Implemented per-device rate limiting with 500ms minimum interval:
```python
# 限频（每设备 ≥500ms）
now_ms = int(time.time() * 1000)
last_ms = int(_last_send_ms.get(device_id, 0))
if now_ms - last_ms < _MIN_INTERVAL_MS:
    _last_send_ms[device_id] = now_ms
    _logger.info(f"[DROP_INVALID] type=ui.render reason=rate-limited interval={now_ms - last_ms}")
    return False, "limited"
```

---

### Issue: Duplicate Listen Events Causing Multiple Triggers
Rapid consecutive listen start/stop events were causing duplicate processing.

**Solution:**
Added debouncing logic with 300ms minimum interval:
```python
# 最小去抖：忽略距上次同类事件 <300ms 的重复 start
now_ms = int(time.time() * 1000)
last_ms = int(getattr(conn, "_last_listen_start_ms", 0) or 0)
if now_ms - last_ms < 300:
    return
conn._last_listen_start_ms = now_ms
```

---

### Issue: Task Cancellation Not Handled Properly
Previous listening tasks were not being cancelled when new listen events arrived, potentially causing race conditions.

**Solution:**
Added proper task cancellation before creating new async tasks:
```python
# Cancel any existing tasks first
try:
    for attr in ("_listen_ready_task", "_listen_timeout_task"):
        old_task = getattr(conn, attr, None)
        if old_task is not None and not old_task.done():
            old_task.cancel()
        setattr(conn, attr, None)
except Exception:
    pass
```

---

### Issue: Non-blocking Queue Clearing Needed
Queue clearing operations were blocking during connection cleanup.

**Solution:**
Implemented non-blocking queue draining:
```python
# 使用非阻塞方式清空队列
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

## User Experience Enhancements

### Issue: Connection Timeout Without Warning
Connections were closing abruptly after timeout without user notification.

**Solution:**
Added timeout warning with grace period:
```python
# 在关闭前先发送提示并提供缓冲期
await self.websocket.send(json.dumps({
    "type": "system",
    "event": "timeout_warning",
    "message": "连接将因长时间空闲而关闭，如需继续请发送任意消息。"
}))
# 给予 10 秒缓冲
await asyncio.sleep(10)
```

---

### Issue: Task Routing and Index Parsing Confusion
Voice commands for task operations had inconsistent index parsing across different formats.

**Solution:**
Unified index parsing supporting multiple formats:
```python
def _parse_target_index(text: str):
    """解析序号：第N个/第N条/任务一/工作一/数字/task N/first/second/third"""
    # Supports English ordinals (first, second, third...)
    # Chinese ordinals (一, 二, 三...)
    # Patterns like "task N", "第N个", "第N条"
    # Raw numbers
```

---

### Issue: Incorrect Voice State Initialization on listen.start
When `listen.start` was received, `client_have_voice` was being set to `True` immediately, which could cause incorrect state handling.

**Solution:**
Initialize voice state correctly when starting to listen:
```python
# Initialize voice state: no voice detected yet
conn.client_have_voice = False
conn.client_voice_stop = False
```

---

### Issue: Missing Render Feedback During LLM Processing
Users had no visual feedback while LLM was processing their request, leading to uncertainty about system state.

**Solution:**
Added immediate "开始对话" (starting conversation) render when entering chat, before LLM processing begins, providing immediate visual feedback to users.