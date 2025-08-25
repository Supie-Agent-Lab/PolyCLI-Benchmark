# Pain Points - Backend Block 4

## Issue: JSON Parameter Parsing Failure in MCP Tool Calls
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

## Issue: Thread Pool Shutdown Blocking on Connection Close
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

## Issue: WebSocket Reception Thread Stack Overflow
Heavy JSON parsing in the WebSocket receive thread was causing stack pressure and potential crashes.

**Solution:**
Implemented a thin receive thread that only copies strings and delegates parsing to the main loop:
- Reception thread only parses `hello` messages directly
- Other JSON messages are copied as strings and posted to main loop for parsing
- Significantly reduced stack usage in receive thread
- Increased default pthread stack size to 8192: `CONFIG_PTHREAD_TASK_STACK_SIZE_DEFAULT=8192`

---

## Issue: Audio Loop Watchdog Timer (WDT) Triggers
Audio loop was monopolizing CPU and triggering watchdog timer resets due to high priority and tight loops.

**Solution:**
Restructured audio loop with proper task scheduling:
```
- Changed to fixed-beat `vTaskDelayUntil` with 2ms period
- Ensured `period >= 1 tick` to avoid `tasks.c:1476 (( xTimeIncrement > 0U ))` assertion
- Added `vTaskDelay(1ms)` in no-data/early-exit branches for yielding
- Reduced audio_loop task priority to 4 to prevent CPU monopolization
```

---

## Issue: Display Showing White Text on White Background
E-ink display was rendering text but it wasn't visible due to incorrect color settings.

**Solution:**
Fixed text rendering by explicitly setting foreground and background colors:
```cpp
// Changed from u8g2_->print(...) to u8g2_->drawUTF8(...)
// Explicitly set colors:
setForegroundColor(ST7306_COLOR_BLACK)
setBackgroundColor(ST7306_COLOR_WHITE)
```
Also fixed default font colors in `u8g2_for_st73xx_impl.cpp` to use black foreground on white background.

---

## Issue: Device Side VAD Fallback Not Working
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

## Issue: Duplicate Listen Events Causing Multiple Triggers
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

## Issue: Wake Word Detection Concurrent Access Crash
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

## Issue: Top Banner Text Not Displaying
Red banner was showing but text was invisible or truncated.

**Solution:**
Enhanced banner rendering with adaptive layout:
- Fixed text drawing from `print(...)` to `drawUTF8(...)`
- Set foreground color to white for red background visibility
- Implemented auto-sizing: starts with 16pt bold, falls back to 14pt if too wide
- Added UTF-8 safe text splitting for two-line layout when needed
- Auto-adds ellipsis for truncated text

---

## Issue: Clock Updates Overwriting Rendered Pages
Welcome page clock updates were overwriting interactive UI renders.

**Solution:**
Implemented state-based mutual exclusion:
- Clock updates only occur in `STATE_WELCOME/STATE_CARD_DISPLAY` states
- Render pages switch to `STATE_INTERACTIVE_UI` to block clock updates
- Display driver manages state transitions during rendering

---

## Issue: Device Identification and Routing Failures
Backend couldn't properly identify and route messages to specific devices.

**Solution:**
Added device identification in WebSocket connection URL:
```
URL追加查询参数: ?device-id=<mac小写>&client-id=<uuid>
Added corresponding request headers for stable device routing
Backend parses device-id during handshake for proper routing
```

---

## Issue: Non-blocking Queue Clearing Needed
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

## Issue: Meeting Mode State Persistence Lost
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

## Issue: Task Routing and Index Parsing Confusion
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

## Issue: Connection Timeout Without Warning
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