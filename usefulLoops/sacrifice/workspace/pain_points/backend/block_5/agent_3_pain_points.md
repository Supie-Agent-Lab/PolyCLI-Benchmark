# Pain Points from Backend Block 5

## Issue: WebSocket Headers Compatibility
Multiple exception handling was needed to properly extract headers from different websocket library implementations.

**Solution:**
```python
try:
    raw_headers = getattr(ws, "request_headers", {})
    headers_lower = {}
    try:
        # 优先使用 items() 以兼容 websockets 的 Headers 类型
        for k, v in raw_headers.items():
            headers_lower[str(k).lower()] = v
    except Exception:
        try:
            headers_lower = {str(k).lower(): v for k, v in dict(raw_headers).items()}
        except Exception:
            headers_lower = {}
    self.headers = headers_lower
except Exception:
    self.headers = {}
```

---

## Issue: Device ID Extraction Fallback Chain
Device ID couldn't be reliably extracted from a single source, requiring multiple fallback strategies.

**Solution:**
Implemented a three-tier fallback mechanism:
1. Try to extract from query parameters
2. Fall back to header values (with multiple header name variations)
3. Auto-generate ID if all extraction methods fail

```python
# 赋值优先级：Query > Header > 回退
chosen_device_id = device_id_from_query or header_device_id or header_client_id
if not chosen_device_id:
    # 容错：仍未取到则自动分配，保证连接可用
    auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
    self.headers["device-id"] = auto_device_id
```

---

## Issue: LLM Instance Management by Mode
Different modes (chat, meeting, coding) required different LLM configurations but no clean way to manage them.

**Solution:**
Created a cached LLM factory with fallback to default:
```python
def get_llm_for(self, purpose: str):
    if key in self._llm_cache and self._llm_cache[key] is not None:
        return self._llm_cache[key]
    
    # Try to get from mapping configuration
    mapping_val = mapping.get(key, None)
    if mapping_val is None:
        # 用途未配置专用 LLM，回退 default
        self.logger.bind(tag=TAG).warning(
            f"get_llm_for: 未找到用途 {key} 的 llm_by_mode 配置，回退到 default"
        )
        mapping_val = mapping.get("default")
```

---

## Issue: Thread Pool Resource Exhaustion
Default thread pool size was causing context switching issues and memory problems.

**Solution:**
Reduced default thread pool size from system default to 2 workers:
```python
# 缩减线程池，降低上下文切换与内存占用
try:
    meeting_cfg = self.config.get("meeting", {})
    # 固化 W3：线程池默认 2，可被 meeting.threadpool_max_workers 覆盖
    default_workers = 2
    max_workers = int(meeting_cfg.get("threadpool_max_workers", default_workers))
    if max_workers < 1:
        max_workers = default_workers
except Exception:
    max_workers = 2
self.executor = ThreadPoolExecutor(max_workers=max_workers)
```

---

## Issue: Server Restart TTY Inheritance
Server restart was hanging in nohup/background mode due to SIGTTIN signal.

**Solution:**
Redirect all standard streams to /dev/null to avoid TTY inheritance:
```python
# 后台重启：避免继承TTY，全部重定向，保证 nohup/backgroud 模式不被SIGTTIN挂起
with open(os.devnull, "rb", buffering=0) as devnull_in, \
     open(os.devnull, "ab", buffering=0) as devnull_out, \
     open(os.devnull, "ab", buffering=0) as devnull_err:
    subprocess.Popen(
        [sys.executable, "app.py"],
        stdin=devnull_in,
        stdout=devnull_out,
        stderr=devnull_err,
        start_new_session=True,
        close_fds=True,
    )
```

---

## Issue: Memory Save Blocking Connection Close
Saving memory on connection close was blocking and delaying cleanup.

**Solution:**
Made memory saving asynchronous using a daemon thread:
```python
def save_memory_task():
    try:
        # 创建新事件循环（避免与主循环冲突）
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            self.memory.save_memory(self.dialogue.dialogue)
        )
    except Exception as e:
        self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
    finally:
        loop.close()

# 启动线程保存记忆，不等待完成
threading.Thread(target=save_memory_task, daemon=True).start()
# 立即关闭连接，不等待记忆保存完成
await self.close(ws)
```

---

## Issue: Connection Timeout Configuration
Fixed timeout value was too rigid for different deployment scenarios.

**Solution:**
Made timeout configurable with multiple layers of fallback:
```python
# 放宽默认空闲阈值：默认 600s + 60s 兜底；允许配置覆盖
try:
    base_idle = int(self.config.get("close_connection_no_voice_time", 600))
except Exception:
    base_idle = 600
self.timeout_seconds = base_idle + 60  # 第一层之外的兜底关闭
```

---

## Issue: VAD Fallback for Missing Device Boundaries
Device wasn't sending proper voice activity boundaries, causing ASR to hang.

**Solution:**
Implemented VAD fallback timer to trigger after no device boundaries for a period:
```python
def check_vad_fallback(self):
    """检查是否需要VAD兜底（超过fallback_ms未见设备边界）"""
    if self.listen_state != "listening":
        return False
    
    last_event_ms = getattr(self, "_last_listen_event_ms", 0)
    if last_event_ms > 0 and (now_ms - last_event_ms) > fallback_ms:
        self.logger.bind(tag=TAG).debug(f"VAD兜底触发: {now_ms - last_event_ms}ms未见设备边界")
        return True
    return False
```

---

## Issue: JSON Send Method Compatibility
Different WebSocket implementations had different methods for sending JSON.

**Solution:**
Created unified send wrapper with automatic fallback:
```python
async def send_json(self, payload: dict) -> None:
    """统一 JSON 发送包装，自动兼容 send_json 缺失并回退字符串。"""
    try:
        if hasattr(self.websocket, 'send_json'):
            await self.websocket.send_json(data)
        else:
            # 回退到字符串发送
            await self.websocket.send(json.dumps(data, ensure_ascii=False))
        return True
    except websockets.exceptions.ConnectionClosed:
        return False
```

---

## Issue: MCP Tool Call Error Handling
MCP tool calls could fail with unparseable results, breaking the conversation flow.

**Solution:**
Added multiple layers of error handling for MCP tool results:
```python
try:
    result = asyncio.run_coroutine_threadsafe(
        call_mcp_tool(self.mcp_client, function_name, function_arguments),
        self.loop,
    ).result()
    
    resultJson = None
    if isinstance(result, str):
        try:
            resultJson = json.loads(result)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"解析MCP工具返回结果失败: {e}")
    
    # Fallback for vision models
    if resultJson is not None and resultJson.get("action") == "show_result":
        result = ActionResponse(action=Action.REQLLM, result=result, response="")
except Exception as e:
    self.logger.bind(tag=TAG).error(f"MCP工具调用失败: {e}")
    result = ActionResponse(
        action=Action.REQLLM, result="MCP工具调用失败", response=""
    )
```

---

## Issue: Device Registration Failure
Device registration could fail silently, leaving connection in undefined state.

**Solution:**
Added explicit registration check and error handling:
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

## Issue: Render State Transitions Causing UI Flickers
Mode transitions were causing unwanted UI renders (c1→p1 transitions).

**Solution:**
Implemented proper state management to avoid redundant renders:
```python
# 阶段2：进入对话活跃态（不再下发额外占位渲染，避免 c1→p1 的瞬时切换）
try:
    self.current_mode = "dialog.active"
except Exception:
    pass
```

---

## Issue: Configuration Update Compatibility
Old configuration update format was incompatible with new system.

**Solution:**
Created compatibility handler that acknowledges but ignores old format:
```python
async def handle_config_update(conn, msg_json: Dict[str, Any]) -> None:
    """处理配置更新消息（兼容旧版）"""
    try:
        cfg_keys = list((msg_json.get("config") or {}).keys())
        conn.logger.bind(tag=TAG).info(f"收到兼容 config_update（忽略实际更新）：keys={cfg_keys}")
    except Exception:
        conn.logger.bind(tag=TAG).info("收到兼容 config_update（忽略实际更新）")
    
    await conn.send_json({"type": "config_update", "status": "ok", "noop": True})
```

---

## Issue: Thread Pool Shutdown Compatibility
Python 3.9+ has different shutdown API than earlier versions.

**Solution:**
Handled both API versions gracefully:
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

## Issue: ASR/TTS Channel Opening Race Condition
TTS channels were being opened unnecessarily in meeting mode.

**Solution:**
Made TTS channel opening conditional based on mode:
```python
# 会议模式可禁用 TTS 通道（懒启动）
disable_tts = False
try:
    meeting_cfg2 = base_cfg.get("meeting", {})
    disable_tts = bool(meeting_cfg2.get("disable_tts", False))
except Exception:
    disable_tts = False
if not disable_tts:
    asyncio.run_coroutine_threadsafe(self.tts.open_audio_channels(self), self.loop)
```