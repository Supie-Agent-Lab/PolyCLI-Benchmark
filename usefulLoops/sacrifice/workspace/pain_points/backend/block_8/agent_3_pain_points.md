# Backend Block 8 Pain Points - Agent 3

## Issue: Thread Pool Configuration Error Handling
The system needed robust error handling for thread pool configuration to prevent startup failures.

**Solution:**
Added proper exception handling with fallback values:
```python
try:
    meeting_cfg = self.config.get("meeting", {}) if isinstance(self.config, dict) else {}
    default_workers = 2
    max_workers = int(meeting_cfg.get("threadpool_max_workers", default_workers))
    if max_workers < 1:
        max_workers = default_workers
except Exception:
    max_workers = 2
```

---

## Issue: Device Registration Failure
Device registration could fail silently or with unclear error messages.

**Solution:**
Added explicit error logging and connection termination on registration failure:
```python
if self.server and self.device_id:
    ok = await self.server.register_device_handler(self.device_id, self)
    if ok is False:
        self.logger.bind(tag=TAG).error(f"设备注册失败: {self.device_id}")
        await ws.send("设备注册失败")
        await self.close(ws)
        return
```

---

## Issue: Authentication Error Handling
Authentication failures needed proper exception handling and logging.

**Solution:**
Implemented specific exception handling for authentication:
```python
except AuthenticationError as e:
    self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
    return
```

---

## Issue: Memory Saving Failures
Memory saving operations could fail and block connection cleanup.

**Solution:**
Implemented asynchronous memory saving with proper error handling:
```python
def save_memory_task():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            self.memory.save_memory(self.dialogue.dialogue)
        )
    except Exception as e:
        self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
    finally:
        loop.close()
```

---

## Issue: Function Call JSON Parsing Errors
Function arguments from LLM could contain malformed JSON causing parsing failures.

**Solution:**
Added comprehensive JSON parsing error handling:
```python
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

## Issue: MCP Tool Call Failures
MCP (Model Context Protocol) tool calls could fail with unclear error messages.

**Solution:**
Added detailed error logging and graceful degradation:
```python
try:
    result = asyncio.run_coroutine_threadsafe(
        self.mcp_manager.execute_tool(function_name, function_arguments),
        self.loop,
    ).result()
    self.logger.bind(tag=TAG).debug(f"MCP工具调用结果: {result}")
except Exception as e:
    self.logger.bind(tag=TAG).error(f"MCP工具调用失败: {e}")
    result = ActionResponse(
        action=Action.REQLLM, result="MCP工具调用失败", response=""
    )
```

---

## Issue: Connection State Management Issues
WebSocket connections could get into inconsistent states during cleanup.

**Solution:**
Implemented comprehensive connection cleanup with proper state management:
```python
async def close(self, ws=None):
    """资源清理方法"""
    try:
        if self.timeout_task:
            self.timeout_task.cancel()
            self.timeout_task = None
        # ... more cleanup code
    except Exception as e:
        self.logger.bind(tag=TAG).error(f"关闭连接时出错: {e}")
```

---

## Issue: STT Message Triggering Unwanted Voice Output
When entering C1 conversation mode, the system would trigger TTS playback for STT messages like "你好小智/喵喵同学", causing unwanted voice output.

**Solution:**
Modified the STT message handling to prevent automatic TTS triggering:
```python
# 根因：在进入 C1 对话模式后，服务端会将识别文本通过 `send_stt_message` 下发到设备，
# 并且这里默认会触发 `send_tts_message("start")`，导致设备端"发声/播报提示"

# 修复：关闭默认 STT→TTS 的链路
# 若未显式开启 `enable_stt_message=true`，则不向设备发送 STT，也不触发 TTS start
```

---

## Issue: ASR Variable Exposure in Public Deployments
ASR-related variables could be exposed to public ASR services, causing security and state management issues.

**Solution:**
Encapsulated ASR variables within connection-private scope:
```python
# 因为实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR
# 所以涉及到ASR的变量，需要在这里定义，属于connection的私有变量
self.asr_audio = []
self.asr_audio_queue = queue.Queue()
```

---

## Issue: Exception Handling in Thread Pool Operations
Thread pool operations could fail during shutdown causing resource leaks.

**Solution:**
Added version-compatible shutdown handling:
```python
try:
    # Python 3.9+ 支持 cancel_futures
    self.executor.shutdown(wait=False, cancel_futures=True)
except TypeError:
    self.executor.shutdown(wait=False)
```

---

## Issue: WebSocket Send Operations Reliability
WebSocket send operations could fail silently, leading to communication issues.

**Solution:**
Implemented robust send methods with proper error handling:
```python
async def send_json(self, data: dict) -> bool:
    try:
        await self.websocket.send(json.dumps(data, ensure_ascii=False))
        return True
    except websockets.exceptions.ConnectionClosed:
        self.logger.bind(tag=TAG).debug(f"send_json: connection closed for device {self.device_id}")
        return False
    except Exception as e:
        self.logger.bind(tag=TAG).warning(f"send_json failed for device {self.device_id}: {e}")
        return False
```