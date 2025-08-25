# Pain Points from Backend Block 4

## Issue: play.tone action being dropped as unsupported
The backend was only allowing `net.banner` action for device control, causing `play.tone` to be rejected with `[DROP_INVALID] type=device.control reason=unsupported-action action=play.tone`.

**Solution:**
Updated `render_sender.py` to allow both `net.banner` and `play.tone` actions:
```python
if action not in ("net.banner", "play.tone"):
    _logger.info(f"[DROP_INVALID] type=device.control reason=unsupported-action action={action} device={device_id}")
    return False, "invalid"
```

---

## Issue: UI stuck on "建立连接中，请稍候" during conversation
After voice recognition and LLM processing, the hardware screen remained stuck displaying "建立连接中，请稍候" (establishing connection, please wait) even though the LLM had generated a response.

**Solution:**
Added UI render updates in `ConnectionHandler.chat()` method to:
1. Switch to "dialog.active" mode and send "开始对话" (start conversation) render when chat begins
2. Send the final LLM response as a UI render after generation completes
```python
# Enter active dialog mode
self.current_mode = "dialog.active"
payload_active = {
    "type": "ui.render",
    "id": "dlg-active",
    "page": "dialog.chat",
    "header": {},
    "body": {"kind": "text", "text": "开始对话"},
}
asyncio.run_coroutine_threadsafe(send_render(self, payload_active), self.loop)

# After LLM response generation
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

## Issue: Infinite listening state after wake-up
After hardware wake-up, the server would remain in listening state indefinitely until the user spoke, causing poor user experience.

**Solution:**
Implemented listening timeout mechanism with configurable delays:
1. Added ready delay (800ms default) to switch from "connecting" to "ready to listen"
2. Added listening timeout (10s default) to exit listening mode if no speech detected
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

## Issue: Incorrect voice state initialization on listen.start
When `listen.start` was received, `client_have_voice` was being set to `True` immediately, which could cause incorrect state handling.

**Solution:**
Initialize voice state correctly when starting to listen:
```python
# Initialize voice state: no voice detected yet
conn.client_have_voice = False
conn.client_voice_stop = False
```

---

## Issue: Duplicate send_json and send_text method definitions
The ConnectionHandler class had duplicate definitions of `send_json` and `send_text` methods causing potential confusion.

**Solution:**
Consolidated to single implementations with proper error handling:
```python
async def send_json(self, data: dict) -> bool:
    """Unified JSON message sending with error handling"""
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

## Issue: Mode-based rendering whitelist too restrictive
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

## Issue: Task cancellation not handled properly
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

## Issue: Missing render feedback during LLM processing
Users had no visual feedback while LLM was processing their request, leading to uncertainty about system state.

**Solution:**
Added immediate "开始对话" (starting conversation) render when entering chat, before LLM processing begins, providing immediate visual feedback to users.