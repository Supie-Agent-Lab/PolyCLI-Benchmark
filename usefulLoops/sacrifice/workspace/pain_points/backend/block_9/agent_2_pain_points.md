# Backend Block 9 - Agent 2 Pain Points

## Issue: NameError in connection.py causing backend crashes
Backend was crashing with NameError due to mistakenly adding synchronous rendering variables to `ConnectionHandler.__init__` that referenced undefined variables like `query`.

**Solution:**
Removed the synchronous rendering variables that were incorrectly placed in the `ConnectionHandler.__init__` method. The variables referenced `query` which was not defined in the constructor scope, causing NameError exceptions during connection initialization.

---

## Issue: Hardware not speaking due to missing TTS start signals
The core issue was that hardware devices were not receiving audio because the backend was not sending proper TTS start signals when STT messages were disabled by default.

**Solution:**
Modified the STT/TTS pathway to ensure that even when STT text is not sent (to avoid echoing wake words), the backend still sends `tts start` signals and continues pushing TTS audio frames:
- Adjusted logic in `send_stt_message()` to force send `tts start` even when `enable_stt_message=false`
- Ensured TTS audio frames are pushed via `sendAudio()` with 60ms frame timing
- Added sentence start/end signals and final stop signal

---

## Issue: AttributeError when websocket lacks send_json method
Some websocket implementations don't have the `send_json()` method, causing AttributeError exceptions when trying to send JSON messages.

**Solution:**
Added fallback logic in multiple places to handle missing `send_json` method:
```python
try:
    await self.websocket.send_json(payload)
except AttributeError:
    import json as _json
    await self.websocket.send(_json.dumps(payload, ensure_ascii=False))
```

---

## Issue: Audio protocol mismatch between backend and hardware
Backend and hardware were not following consistent audio protocol specifications, leading to hardware not receiving audio frames correctly.

**Solution:**
Implemented strict protocol compliance:
- Added proper handshake with `audio_params` in hello response including `format:"opus"`, `sample_rate:16000`, `channels:1`, `frame_duration:60`
- Ensured binary Opus frames are sent directly via WebSocket binary frames (not JSON wrapped)
- Added TTS start signal before sending any audio frames
- Implemented proper frame timing at 60ms intervals

---

## Issue: Connection timeout handling causing premature disconnections
Connections were being closed too aggressively due to timeout mechanisms, interrupting ongoing conversations.

**Solution:**
Improved timeout handling with graduated warnings:
```python
async def _check_timeout(self):
    while not self.stop_event.is_set():
        await asyncio.sleep(self.timeout_seconds)
        # Send warning first
        await self.websocket.send(json.dumps({
            "type": "system", 
            "event": "timeout_warning",
            "message": "连接将因长时间空闲而关闭，如需继续请发送任意消息。"
        }))
        # Give 10 second buffer
        await asyncio.sleep(10)
```

---

## Issue: VAD fallback mechanism not triggering properly
VAD (Voice Activity Detection) fallback was not triggering correctly when devices stopped sending audio boundaries, causing ASR to hang.

**Solution:**
Implemented robust VAD fallback checking:
```python
def check_vad_fallback(self):
    if self.listen_state != "listening":
        return False
    now_ms = int(time.time() * 1000)
    fallback_ms = 2000  # 2 second fallback
    last_event_ms = getattr(self, "_last_listen_event_ms", 0)
    if last_event_ms > 0 and (now_ms - last_event_ms) > fallback_ms:
        self.logger.bind(tag=TAG).debug(f"VAD兜底触发: {now_ms - last_event_ms}ms未见设备边界")
        return True
    return False
```

---

## Issue: JSON parsing errors in function call handling
Function calls with malformed JSON arguments were causing JSONDecodeError exceptions and breaking the function execution flow.

**Solution:**
Added comprehensive error handling for JSON parsing:
```python
if isinstance(function_arguments, str):
    try:
        args_dict = json.loads(function_arguments)
    except json.JSONDecodeError:
        self.logger.bind(tag=TAG).error(
            f"无法解析 function_arguments: {function_arguments}"
        )
        return ActionResponse(action=Action.REQLLM, result="参数解析失败", response="")
```

---

## Issue: Thread pool shutdown causing TypeError on older Python versions
Thread pool shutdown was failing on Python versions < 3.9 due to the `cancel_futures` parameter not being available.

**Solution:**
Added version-compatible thread pool shutdown:
```python
try:
    # Python 3.9+ supports cancel_futures
    self.executor.shutdown(wait=False, cancel_futures=True)
except TypeError:
    self.executor.shutdown(wait=False)
```

---

## Issue: Memory cleanup and queue management during connection close
Connections were not properly cleaning up memory, task queues, and background threads when closing, leading to resource leaks.

**Solution:**
Implemented comprehensive cleanup in the `close()` method:
- Clear all TTS queues (text and audio)
- Cancel timeout tasks
- Stop background threads with poison pill pattern
- Shut down thread pool executor
- Reset VAD states and clear audio buffers
- Close websocket connections properly

---

## Issue: Inconsistent error handling for websocket operations
Different websocket operations had inconsistent error handling, some silently failing while others crashed the connection.

**Solution:**
Standardized error handling patterns:
- Added unified `send_json()` and `send_text()` wrapper methods with consistent error handling
- Differentiated between expected errors (ConnectionClosed) that are logged at debug level vs unexpected errors logged as warnings
- Ensured errors don't interrupt main processing flow