# Backend Block 9 Pain Points - Agent 1

## Issue: NameError due to undefined variable in ConnectionHandler.__init__
The backend crashed with NameError because synchronous rendering variables were mistakenly added to `ConnectionHandler.__init__` that referenced an undefined `query` variable.

**Solution:**
Removed the synchronous rendering variables from `ConnectionHandler.__init__` that referenced undefined variables. The backend no longer reports NameError crashes.

---

## Issue: Hardware not speaking despite backend processing working
The core problem was hardware devices were not receiving audio despite ASR/LLM processing working correctly. Users could see rendering information but heard no audio output from devices.

**Solution:**
Fixed the TTS audio pipeline by ensuring:
1. Even when STT messages are disabled (to avoid echo of wake words), still send `tts start` signal to hardware
2. Continue pushing TTS audio frames to ensure device audio output
3. Restored proper TTS start/stop signaling while maintaining audio frame transmission

Code changes in `core/handle/sendAudioHandle.py`:
```python
# Send TTS start signal before audio frames
await send_tts_message(conn, "start")
# Continue with audio frame transmission
```

---

## Issue: Audio protocol mismatch between backend and hardware
Backend was not following the proper audio protocol expected by hardware devices. Hardware only received rendering messages but no audio frames or TTS control messages.

**Solution:**
Implemented proper audio protocol alignment:
1. **Handshake protocol**: Added complete `audio_params` to hello response including:
   - `format: "opus"`
   - `sample_rate: 16000` 
   - `channels: 1`
   - `frame_duration: 60`
   - `transport: "websocket"`

2. **TTS control flow**: Proper sequence of:
   - `{"type":"tts","state":"start","session_id":"..."}`
   - Multiple binary Opus frames (60ms/frame)
   - `{"type":"tts","state":"sentence_end"}` (optional)
   - `{"type":"tts","state":"stop"}`

3. **Frame transmission**: Keep binary Opus frames as direct WebSocket binary transmission, not JSON-wrapped

Updated files:
- `backend/core/handle/helloHandle.py`: Added complete audio_params to handshake
- `backend/core/handle/sendAudioHandle.py`: Fixed TTS control flow and frame transmission

---

## Issue: Lack of debugging visibility in audio transmission
There was no visibility into whether audio frames were actually being sent from backend to hardware, making debugging extremely difficult.

**Solution:**
Added comprehensive logging for audio pipeline debugging:
- `[TTS] state=start/stop session_id=...` for TTS control events
- `[SEND_AUDIO] prebuffer frames=N` for initial buffering
- `[SEND_AUDIO] frames=N bytes_total=...` for frame transmission (logged every 10 frames)

This allows verification that audio frames are reaching the transmission layer and helps identify where the pipeline breaks.

---

## Issue: TTS channels not properly initialized
TTS audio channels might not be opened correctly during connection initialization, preventing audio output.

**Solution:**
Ensured `tts.open_audio_channels(self)` is properly executed during connection initialization in `ConnectionHandler._initialize_components()`. Added checks for meeting mode TTS disable flags:
```python
disable_tts = bool(meeting_cfg.get("disable_tts", False))
if not disable_tts:
    asyncio.run_coroutine_threadsafe(self.tts.open_audio_channels(self), self.loop)
```

---

## Issue: WebSocket connection error handling affecting audio transmission
Various WebSocket connection errors (ConnectionClosed, AttributeError) were not properly handled, potentially causing audio transmission failures.

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

Similar error handling added for `send_text()` method to ensure graceful degradation.

---

## Issue: TTS audio queue management problems
TTS audio queues could become stuck or not properly cleared, preventing new audio from being processed and transmitted.

**Solution:**
Implemented proper queue management in `clear_queues()`:
```python
def clear_queues(self):
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

Added proper queue size logging for debugging and non-blocking queue clearing.

---

## Issue: Function call parsing errors in LLM responses
JSON parsing errors occurred when processing LLM function calls, leading to function call failures.

**Solution:**
Added proper error handling for function argument parsing:
```python
if isinstance(function_arguments, str):
    try:
        args_dict = json.loads(function_arguments)
    except json.JSONDecodeError:
        self.logger.bind(tag=TAG).error(f"无法解析 function_arguments: {function_arguments}")
        return ActionResponse(action=Action.REQLLM, result="参数解析失败", response="")
```

Added fallback mechanisms and proper error responses when function argument parsing fails.

---

## Issue: MCP tool execution failures
MCP (Model Context Protocol) tool calls were failing with various exceptions, breaking the function calling pipeline.

**Solution:**
Implemented comprehensive error handling for MCP tool execution:
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

Added proper exception catching and meaningful error responses for tool execution failures.

---

## Issue: Connection timeout handling interfering with normal operation
Connection timeout mechanisms were triggering inappropriately and causing premature connection closures.

**Solution:**
Implemented proper timeout reset mechanism and graceful timeout handling:
```python
def reset_timeout(self):
    if self.timeout_task and not self.timeout_task.done():
        self.timeout_task.cancel()
    self.timeout_task = asyncio.create_task(self._check_timeout())

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