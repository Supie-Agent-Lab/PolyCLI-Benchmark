# Backend Block 4 Pain Points Analysis

## Issue: JSON Parsing Error in MCP Tool Call Handler
Function arguments received as string but expected as dict, causing JSON decode failures.

**Solution:**
Added proper type checking and JSON parsing with error handling:
```python
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
```

---

## Issue: Thread Pool Shutdown Compatibility Error
Python 3.9+ requires `cancel_futures` parameter in executor.shutdown(), but older versions don't support it.

**Solution:**
Added version compatibility check with try-except fallback:
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

## Issue: WebSocket Send Method Inconsistency
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

## Issue: Display Not Rendering Despite Successful Logs
Hardware logs showed `[RENDER_RX]` → `[RENDER_OK]` but screen didn't update. Text was being drawn with white foreground on white background.

**Solution:**
Fixed text rendering by switching from `print()` to `drawUTF8()` and explicitly setting colors:
```cpp
// 文本绘制修复
u8g2_->setForegroundColor(ST7306_COLOR_BLACK);
u8g2_->setBackgroundColor(ST7306_COLOR_WHITE);
u8g2_->drawUTF8(x, y, text);  // 改为 drawUTF8 instead of print
```

---

## Issue: Top Banner Text Not Visible on Red Background
Banner showed red bar but text was invisible or missing on long strings.

**Solution:**
Fixed banner text rendering with proper color settings and multi-line support:
```cpp
// 顶部横幅修复
u8g2_->setForegroundColor(ST7306_COLOR_WHITE);  // 白色文字
u8g2_->drawUTF8(x, y, text);  // 使用 drawUTF8
// 添加自适应两行布局，超宽自动降字号或拆分
```

---

## Issue: Task Watchdog Triggered and Stack Overflow
Audio loop task causing WDT (watchdog timer) resets and `xTaskDelayUntil` assertion failures.

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

---

## Issue: WebSocket Connection Failed with TcpTransport Error -1
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

## Issue: UI Stuck on "建立连接中，请稍候" During Dialog
LLM responses generated but not displayed on device screen, stuck on connection message.

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
    "body": {"kind": "text", "text": "开始对话"},
}
asyncio.run_coroutine_threadsafe(send_render(self, payload_active), self.loop)

# LLM回答后渲染最终文本
if len(response_message) > 0:
    final_text = "".join(response_message)
    payload_final = {
        "type": "ui.render",
        "page": "dialog.chat",
        "body": {"kind": "text", "text": final_text},
    }
    asyncio.run_coroutine_threadsafe(send_render(self, payload_final), self.loop)
```

---

## Issue: Device Control Commands Blocked for play.tone
Backend dropping `play.tone` commands with "unsupported-action" error.

**Solution:**
Extended allowed actions whitelist in render_sender:
```python
# 允许阶段2：net.banner | play.tone
if action not in ("net.banner", "play.tone"):
    _logger.info(f"[DROP_INVALID] type=device.control reason=unsupported-action action={action}")
    return False, "invalid"
```

---

## Issue: Render Commands Dropped in Welcome State
UI render commands being rejected when device in welcome/idle state.

**Solution:**
Implemented state-based whitelist filtering:
```python
# 仅当目标设备 mode ∈ {dialog.preparing, dialog.active} 才放行
def _allowed_by_target_mode(target_mode: str | None, payload: dict) -> bool:
    if target_mode not in ("dialog.preparing", "dialog.active"):
        return False
    t = payload.get("type", "").strip().lower()
    if t == "ui.render":
        page = payload.get("page", "").strip()
        return page == "dialog.chat"
    if t == "device.control":
        act = payload.get("action", "").strip()
        return act in ("net.banner", "play.tone")
    return False
```

---

## Issue: Rate Limiting Not Working Properly
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

## Issue: Clock Display Overwriting Rendered Content
Welcome page clock updates overwriting UI render results.

**Solution:**
Added state management to prevent clock updates in interactive mode:
```cpp
// 切换到交互态，阻止时钟覆盖
current_state_ = STATE_INTERACTIVE_UI;
// 时钟更新只在 STATE_WELCOME/STATE_CARD_DISPLAY 下执行
if (current_state_ == STATE_WELCOME || current_state_ == STATE_CARD_DISPLAY) {
    UpdateClock();
}
```

---

## Issue: Thread Stack Size Insufficient for WebSocket Processing
WebSocket receive thread running out of stack space during JSON parsing.

**Solution:**
Increased default thread stack size and moved heavy processing to main loop:
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

---

## Issue: Missing Device Identification in WebSocket Connection
Backend couldn't route messages to specific devices without proper identification.

**Solution:**
Added device ID and client ID to WebSocket connection URL:
```cpp
// 在 URL 追加查询参数
std::string url = base_url + "?device-id=" + mac_lower + "&client-id=" + uuid;
// 同时设置请求头
headers["Device-Id"] = mac_address;
headers["Client-Id"] = client_uuid;
```