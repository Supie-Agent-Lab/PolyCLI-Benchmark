# Agent 3 Pain Points - Backend Block 9

## Issue: Critical Hardware Audio Failure - No Speech Output
The most critical issue was that hardware devices were not speaking despite successful ASR and LLM processing. The user reported: "硬件不会说话!!!!! 后端没有给硬件传输消息!!!!"

**Solution:**
- Fixed the TTS audio transmission path by ensuring `tts start` messages are sent before any binary audio frames
- Added proper TTS state management with sequence: `start` → binary opus frames → `sentence_start/sentence_end` → `stop`
- Restored `tts.open_audio_channels()` initialization during connection setup
- Modified `sendAudioHandle.py` to guarantee TTS start signal is sent even when STT text is disabled

---

## Issue: NameError Crash in ConnectionHandler.__init__
Backend started crashing after code modifications with NameError due to undefined variable `query` being referenced in the ConnectionHandler initialization.

**Solution:**
```python
# Removed problematic code that referenced undefined 'query' variable
# from ConnectionHandler.__init__ that was causing NameError crashes
```
- Identified and removed synchronous rendering variables that were incorrectly added to `ConnectionHandler.__init__`
- Fixed reference to undefined `query` variable that was causing immediate crashes
- Backend now initializes without NameError exceptions

---

## Issue: Missing Audio Parameters in WebSocket Handshake
Hardware devices were not receiving proper audio configuration during the initial WebSocket handshake, causing audio protocol mismatches.

**Solution:**
```python
# Updated helloHandle.py to include complete audio_params
"audio_params": {
    "format": "opus",
    "sample_rate": 16000, 
    "channels": 1,
    "frame_duration": 60
},
"transport": "websocket"
```
- Added comprehensive `audio_params` to the hello handshake response
- Specified explicit audio format, sample rate, channels, and frame duration
- Ensured transport type is clearly communicated to hardware

---

## Issue: AttributeError with WebSocket send_json Method
WebSocket connections were failing when trying to use `send_json()` method which doesn't exist on all WebSocket implementations.

**Solution:**
```python
try:
    await self.websocket.send_json(payload)
except AttributeError:
    import json as _json
    await self.websocket.send(_json.dumps(payload, ensure_ascii=False))
```
- Implemented fallback mechanism for WebSocket libraries without `send_json()` support
- Added graceful handling with manual JSON serialization when needed
- Wrapped in exception handling to prevent connection failures

---

## Issue: Insufficient Audio Transmission Logging
Difficult to debug audio transmission issues due to lack of detailed logging in the audio pipeline.

**Solution:**
- Added `[TTS] state=... session_id=...` logging for all TTS state changes
- Implemented `[SEND_AUDIO] prebuffer frames=N` logging for audio prebuffering
- Added aggregated logging `[SEND_AUDIO] frames=N bytes_total=...` every 10 frames
- Enhanced debugging capability for audio transmission pipeline

---

## Issue: Connection Timeout Management Problems
Connections were being closed prematurely or timeout handling was not working correctly, causing session interruptions.

**Solution:**
```python
async def _check_timeout(self):
    """检查连接超时"""
    try:
        while not self.stop_event.is_set():
            await asyncio.sleep(self.timeout_seconds)
            # 在关闭前先发送提示并提供缓冲期
            await self.websocket.send(json.dumps({
                "type": "system",
                "event": "timeout_warning", 
                "message": "连接将因长时间空闲而关闭，如需继续请发送任意消息。"
            }))
            # 给予 10 秒缓冲
            await asyncio.sleep(10)
```
- Implemented proper timeout warning system with 10-second buffer
- Added `reset_timeout()` method to cancel and restart timeout tasks
- Extended default idle threshold to 600s + 60s fallback for better user experience

---

## Issue: VAD Fallback Mechanism Not Working Properly
Voice Activity Detection fallback was not triggering correctly when devices failed to send proper voice boundaries.

**Solution:**
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
- Implemented configurable VAD fallback timeout (default 2000ms)
- Added proper state machine transitions: `idle -> listening -> finalizing -> idle`
- Enhanced debugging with detailed VAD trigger logging

---

## Issue: Queue Management and Resource Cleanup Problems
TTS and audio queues were not being properly cleared, causing memory issues and stale audio playback.

**Solution:**
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
- Added comprehensive queue clearing during connection cleanup
- Implemented non-blocking queue draining to prevent deadlocks
- Added detailed logging of queue sizes before and after cleanup

---

## Issue: ThreadPool Resource Management Issues
Thread pool executor was not being properly shut down, leading to resource leaks.

**Solution:**
```python
try:
    # Python 3.9+ 支持 cancel_futures
    self.executor.shutdown(wait=False, cancel_futures=True)
except TypeError:
    self.executor.shutdown(wait=False)
```
- Added graceful thread pool shutdown with future cancellation when supported
- Implemented fallback for older Python versions without `cancel_futures`
- Reduced default thread pool size from unlimited to 2 workers to minimize context switching

---

## Issue: Function Call Error Handling Inadequacy
Function call errors were not properly handled, causing cascading failures in tool execution.

**Solution:**
```python
if function_id is None:
    a = extract_json_from_string(content_arguments)
    if a is not None:
        # Proper JSON extraction handling
    else:
        bHasError = True
        response_message.append(content_arguments)
        
if bHasError:
    self.logger.bind(tag=TAG).error(f"function call error: {content_arguments}")
```
- Added comprehensive error checking for function call extraction
- Implemented proper fallback handling for malformed function calls
- Enhanced error logging for debugging tool execution failures