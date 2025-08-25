# Backend Block 9 - Merged Pain Points

## Critical Issues (System Breaking)

### Issue: Hardware Not Speaking - Complete Audio Pipeline Failure
**Severity: CRITICAL**
The most critical issue was that hardware devices were completely silent despite successful ASR and LLM processing. Users reported: "硬件不会说话!!!!! 后端没有给硬件传输消息!!!!"

**Root Causes:**
1. TTS start signals not being sent before audio frames
2. Audio protocol mismatch between backend and hardware
3. TTS audio channels not properly initialized

**Solution:**
- Fixed TTS audio transmission path with proper sequence: `start` → binary opus frames → `sentence_start/sentence_end` → `stop`
- Modified `sendAudioHandle.py` to guarantee TTS start signal is sent even when STT text is disabled
- Restored `tts.open_audio_channels()` initialization during connection setup
- Ensured TTS audio frames are pushed via `sendAudio()` with 60ms frame timing

Code changes in `core/handle/sendAudioHandle.py`:
```python
# Send TTS start signal before audio frames
await send_tts_message(conn, "start")
# Continue with audio frame transmission
```

### Issue: NameError Crash in ConnectionHandler.__init__
**Severity: CRITICAL**
Backend was crashing immediately on startup with NameError due to undefined variable `query` being referenced in ConnectionHandler initialization.

**Solution:**
Removed synchronous rendering variables that were incorrectly added to `ConnectionHandler.__init__` method:
```python
# Removed problematic code that referenced undefined 'query' variable
# from ConnectionHandler.__init__ that was causing NameError crashes
```

---

## High Impact Issues (Core Functionality)

### Issue: Audio Protocol Mismatch Between Backend and Hardware
**Severity: HIGH**
Backend and hardware were not following consistent audio protocol specifications, leading to hardware not receiving audio frames correctly.

**Solution:**
Implemented strict protocol compliance:
1. **Handshake protocol**: Added complete `audio_params` to hello response:
```python
"audio_params": {
    "format": "opus",
    "sample_rate": 16000, 
    "channels": 1,
    "frame_duration": 60
},
"transport": "websocket"
```

2. **TTS control flow**: Proper sequence of:
   - `{"type":"tts","state":"start","session_id":"..."}`
   - Multiple binary Opus frames (60ms/frame)
   - `{"type":"tts","state":"sentence_end"}` (optional)
   - `{"type":"tts","state":"stop"}`

3. **Frame transmission**: Keep binary Opus frames as direct WebSocket binary transmission, not JSON-wrapped

Updated files:
- `backend/core/handle/helloHandle.py`: Added complete audio_params to handshake
- `backend/core/handle/sendAudioHandle.py`: Fixed TTS control flow and frame transmission

### Issue: WebSocket Connection Error Handling
**Severity: HIGH**
Various WebSocket connection errors (ConnectionClosed, AttributeError) were not properly handled, causing audio transmission failures.

**Solution:**
Implemented robust WebSocket error handling with proper fallback mechanisms:

```python
async def send_json(self, data: dict) -> bool:
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

Added fallback for WebSocket libraries without `send_json()` support:
```python
try:
    await self.websocket.send_json(payload)
except AttributeError:
    import json as _json
    await self.websocket.send(_json.dumps(payload, ensure_ascii=False))
```

---

## Medium Impact Issues (Reliability & Performance)

### Issue: Connection Timeout Handling Causing Premature Disconnections
**Severity: MEDIUM**
Connection timeout mechanisms were triggering inappropriately and causing premature connection closures, interrupting ongoing conversations.

**Solution:**
Implemented proper timeout reset mechanism and graceful timeout handling:
```python
async def _check_timeout(self):
    try:
        while not self.stop_event.is_set():
            await asyncio.sleep(self.timeout_seconds)
            # Send warning before closing
            try:
                await self.websocket.send(json.dumps({
                    "type": "system",
                    "event": "timeout_warning", 
                    "message": "连接将因长时间空闲而关闭，如需继续请发送任意消息。"
                }))
            except Exception:
                pass
            # Grace period before actual timeout
            await asyncio.sleep(10)
            # ... timeout handling
    except Exception as e:
        self.logger.bind(tag=TAG).error(f"超时检查任务出错: {e}")
```

Added `reset_timeout()` method to cancel and restart timeout tasks properly.

### Issue: VAD Fallback Mechanism Not Working Properly
**Severity: MEDIUM**
Voice Activity Detection fallback was not triggering correctly when devices failed to send proper voice boundaries, causing ASR to hang.

**Solution:**
Implemented robust VAD fallback checking:
```python
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

### Issue: Function Call Parsing Errors
**Severity: MEDIUM**
JSON parsing errors occurred when processing LLM function calls and MCP tool execution, leading to function call failures.

**Solution:**
Added comprehensive error handling for function argument parsing:
```python
if isinstance(function_arguments, str):
    try:
        args_dict = json.loads(function_arguments)
    except json.JSONDecodeError:
        self.logger.bind(tag=TAG).error(f"无法解析 function_arguments: {function_arguments}")
        return ActionResponse(action=Action.REQLLM, result="参数解析失败", response="")
```

For MCP tool execution:
```python
try:
    tool_result = asyncio.run_coroutine_threadsafe(
        self.mcp_manager.execute_tool(function_name, args_dict), self.loop
    ).result()
    # Process tool result...
except Exception as e:
    self.logger.bind(tag=TAG).error(f"MCP工具调用错误: {e}")
    return ActionResponse(action=Action.REQLLM, result="工具调用出错", response="")
```

---

## Low Impact Issues (Maintenance & Debugging)

### Issue: Lack of Debugging Visibility in Audio Transmission
**Severity: LOW**
There was no visibility into whether audio frames were actually being sent from backend to hardware, making debugging extremely difficult.

**Solution:**
Added comprehensive logging for audio pipeline debugging:
- `[TTS] state=start/stop session_id=...` for TTS control events
- `[SEND_AUDIO] prebuffer frames=N` for initial buffering
- `[SEND_AUDIO] frames=N bytes_total=...` for frame transmission (logged every 10 frames)

### Issue: Memory Cleanup and Queue Management Problems
**Severity: LOW**
TTS and audio queues were not being properly cleared, causing memory issues and potentially stale audio playback.

**Solution:**
Implemented comprehensive cleanup in the `close()` method:
```python
def clear_queues(self):
    """清空所有任务队列"""
    if self.tts:
        self.logger.bind(tag=TAG).debug(
            f"开始清理: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
        )
        for q in [self.tts.tts_text_queue, self.tts.tts_audio_queue, self.report_queue]:
            if not q:
                continue
            while True:
                try:
                    q.get_nowait()
                except queue.Empty:
                    break
```

### Issue: Thread Pool Shutdown Compatibility
**Severity: LOW**
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

### Issue: TTS Audio Channels Initialization
**Severity: LOW**
TTS audio channels might not be opened correctly during connection initialization, preventing audio output.

**Solution:**
Ensured `tts.open_audio_channels(self)` is properly executed during connection initialization:
```python
disable_tts = bool(meeting_cfg.get("disable_tts", False))
if not disable_tts:
    asyncio.run_coroutine_threadsafe(self.tts.open_audio_channels(self), self.loop)
```

---

## Summary

The most critical issues were related to the audio pipeline - hardware not speaking due to missing TTS signals and protocol mismatches. The NameError crash was also critical as it prevented the backend from starting. Most issues have been resolved through proper error handling, protocol compliance, and comprehensive logging. The fixes ensure robust audio transmission, graceful error recovery, and better debugging capabilities.