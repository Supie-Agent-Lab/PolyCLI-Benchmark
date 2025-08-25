# Backend Block 8 Technical Pain Points

## Issue: Device Registration Failure
Device registration can fail silently or with generic error messages, making debugging difficult.

**Solution:**
Implemented specific error logging and immediate connection cleanup:
```python
ok = await self.server.register_device_handler(self.device_id, self)
if ok is False:
    self.logger.bind(tag=TAG).error(f"设备注册失败: {self.device_id}")
    await ws.send("设备注册失败")
    await self.close(ws)
```

---

## Issue: Function Call JSON Parsing Errors
Function call arguments from LLM responses may be malformed JSON, causing parsing failures.

**Solution:**
Added comprehensive error handling with fallback strategies:
```python
if function_id is None:
    a = extract_json_from_string(content_arguments)
    if a is not None:
        try:
            function_arguments = json.dumps(a, ensure_ascii=False)
            function_id = str(uuid.uuid4().hex)
        except Exception as e:
            bHasError = True
            response_message.append(a)
    else:
        bHasError = True
        response_message.append(content_arguments)
    if bHasError:
        self.logger.bind(tag=TAG).error(f"function call error: {content_arguments}")
```

---

## Issue: MCP Tool Execution Failures
MCP (Model Context Protocol) tool calls can fail due to various reasons including malformed arguments or tool unavailability.

**Solution:**
Implemented robust error handling with meaningful error messages:
```python
try:
    args_dict = json.loads(function_arguments)
except json.JSONDecodeError:
    self.logger.bind(tag=TAG).error(f"无法解析 function_arguments: {function_arguments}")
    
try:
    tool_result = asyncio.run_coroutine_threadsafe(
        self.mcp_manager.execute_tool(function_name, args_dict), self.loop
    ).result()
except Exception as e:
    self.logger.bind(tag=TAG).error(f"MCP工具调用失败: {e}")
    result = ActionResponse(action=Action.REQLLM, result="MCP工具调用失败", response="")
```

---

## Issue: WebSocket Connection Handling
WebSocket connections can close unexpectedly, leading to failed message sends and resource leaks.

**Solution:**
Added graceful connection handling with proper exception management:
```python
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

## Issue: Memory Saving Thread Safety
Memory saving operations can fail due to threading issues or resource constraints.

**Solution:**
Implemented thread-safe memory saving with proper cleanup:
```python
def save_memory_task():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            self.memory.store_memory(self.session_id, memory_data)
        )
    except Exception as e:
        self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
    finally:
        loop.close()

threading.Thread(target=save_memory_task, daemon=True).start()
```

---

## Issue: Resource Cleanup on Connection Close
Improper resource cleanup can lead to memory leaks and hanging threads.

**Solution:**
Comprehensive resource cleanup with version compatibility handling:
```python
try:
    if self.executor:
        try:
            # Python 3.9+ 支持 cancel_futures
            self.executor.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            self.executor.shutdown(wait=False)
        self.executor = None
        
    # Close ASR/TTS/LLM resources with async compatibility
    for component_name in ['asr', 'tts', 'llm']:
        if hasattr(self, component_name):
            component = getattr(self, component_name)
            if hasattr(component, 'close') and callable(getattr(component, 'close')):
                maybe_close = component.close()
                if asyncio.iscoroutine(maybe_close):
                    await maybe_close
except Exception as e:
    self.logger.bind(tag=TAG).error(f"关闭连接时出错: {e}")
```

---

## Issue: Queue Management and Deadlocks
TTS and audio queues can become blocked or overfilled, causing performance issues.

**Solution:**
Non-blocking queue clearing with size monitoring:
```python
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

---

## Issue: VAD State Management
Voice Activity Detection (VAD) state can get stuck in inconsistent states leading to audio processing issues.

**Solution:**
Implemented comprehensive VAD state reset with timeout fallback:
```python
def reset_vad_states(self):
    """重置VAD状态，恢复到idle状态"""
    self.client_audio_buffer = bytearray()
    self.client_have_voice = False
    self.client_have_voice_last_time = 0
    self.client_voice_stop = False
    self.listen_state = "idle"
    if self._listen_state_timer:
        self._listen_state_timer.cancel()
        self._listen_state_timer = None
    self.logger.bind(tag=TAG).debug("VAD states reset.")

# VAD fallback timeout mechanism
def should_fallback_handle_voice_stop(self, fallback_ms=3000):
    now_ms = int(time.time() * 1000)
    last_event_ms = getattr(self, "_last_listen_event_ms", 0)
    if last_event_ms > 0 and (now_ms - last_event_ms) > fallback_ms:
        self.logger.bind(tag=TAG).debug(f"VAD兜底触发: {now_ms - last_event_ms}ms未见设备边界")
        return True
    return False
```