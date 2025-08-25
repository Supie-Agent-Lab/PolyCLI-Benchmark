# Merged Pain Points - Backend Block 5

## Critical Issues (High Priority)

### Issue: UI页面瞬时切换问题 - C1到P1的跳变
唤醒后仍然额外渲染了"过渡页/占位页"，以及标题未统一，导致看起来像"c1 → p1"的瞬时切换。用户体验到明显的页面闪烁，因为底部文字和中间文字都被替换了。

**Solution:**
- 移除对话开始时在 `chat()` 的"dlg-active"占位渲染，避免任何额外页切换
- 统一渲染清洗：`dialog.chat` 的 `header.title` 强制为"对话模式"（在 `render_schema.clean_render_payload` 中实现）
- 准备态直接渲染 p1（`dialog.chat`），不再发送任何 `net.banner` 或"建立连接中"页面
- 改为默认不发送"准备聆听"帧，仅在配置显式开启时才显示（`enable_ready_ui=false`）
- 唤醒后不再推一帧文字占位，避免底部提示与中间文案的瞬时替换
- 阶段2：进入对话活跃态（不再下发额外占位渲染，避免 c1→p1 的瞬时切换）：
```python
try:
    self.current_mode = "dialog.active"
except Exception:
    pass
```

### Issue: 标题重复显示问题 - 两个C1
唤醒后左上角显示的是"c1 c1 对话模式"，有两个c1重复显示。

**Solution:**
调整为渲染页标题仅为"对话模式"，左上角的"C1"应由硬件端固定UI头部渲染：
```python
# 注入标题策略：dialog.chat 标题为"对话模式"（设备端负责加左上角 C1 标识）
if page == "dialog.chat":
    title = "对话模式"
else:
    injected_title = get_display_title(device_id_norm)
```

## Memory and Performance Issues

### Issue: 线程池上下文切换与内存占用过高
线程池默认配置过大，导致上下文切换频繁，内存占用高。

**Solution:**
缩减线程池，降低上下文切换与内存占用：
```python
# 缩减线程池，降低上下文切换与内存占用
try:
    meeting_cfg = self.config.get("meeting", {}) if isinstance(self.config, dict) else {}
    # 固化 W3：线程池默认 2，可被 meeting.threadpool_max_workers 覆盖
    default_workers = 2
    max_workers = int(meeting_cfg.get("threadpool_max_workers", default_workers))
    if max_workers < 1:
        max_workers = default_workers
except Exception:
    max_workers = 2
self.executor = ThreadPoolExecutor(max_workers=max_workers)
```

### Issue: Memory Leak in Connection Cleanup
Memory wasn't being properly freed when connections were closed, especially for saved dialogue history.

**Solution:**
Implemented asynchronous memory saving in a separate thread to avoid blocking connection closure:
```python
async def _save_and_close(self, ws):
    """保存记忆并关闭连接"""
    try:
        if self.memory:
            # 使用线程池异步保存记忆
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
    except Exception as e:
        self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
    finally:
        # 立即关闭连接，不等待记忆保存完成
        await self.close(ws)
```

## ASR/TTS Related Issues

### Issue: ASR变量暴露给公共ASR的问题
实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR。

**Solution:**
涉及到ASR的变量，需要在connection里定义，属于connection的私有变量：
```python
# 因为实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR
# 所以涉及到ASR的变量，需要在这里定义，属于connection的私有变量
self.asr_audio = []
self.asr_audio_queue = queue.Queue()
```

### Issue: 远程ASR实例化问题
远程ASR涉及到websocket连接和接收线程，需要每个连接一个实例。

**Solution:**
区分本地和远程ASR的初始化策略：
```python
if self._asr.interface_type == InterfaceType.LOCAL:
    # 如果公共ASR是本地服务，则直接返回
    # 因为本地一个实例ASR，可以被多个连接共享
    asr = self._asr
else:
    # 如果公共ASR是远程服务，则初始化一个新实例
    # 因为远程ASR，涉及到websocket连接和接收线程，需要每个连接一个实例
    asr = initialize_asr(self.config)
```

### Issue: ASR/TTS Channel Opening Race Condition
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

## Connection Management Issues

### Issue: Device ID Parsing from WebSocket Handshake
Device ID extraction from WebSocket connections was failing due to inconsistent header formats and missing query parameters.

**Solution:**
Implemented a three-tier fallback mechanism with auto-assignment:
```python
# 统一调用服务器封装的握手解析；其次尝试 Header；最后回退自动分配
device_id_from_query = None
client_id_from_query = None
raw_path_from_server = None
try:
    server_obj = getattr(self, "server", None)
    if server_obj and hasattr(server_obj, "parse_ids_from_handshake"):
        d, c, rawp = server_obj.parse_ids_from_handshake(ws, path)
        device_id_from_query = d
        client_id_from_query = c
        raw_path_from_server = rawp
except Exception:
    pass

# 从 Header 兜底解析（包含非规范写法）
header_device_id = _normalize_id(
    self.headers.get("device-id")
    or self.headers.get("device_id")
    or self.headers.get("x-device-id")
    or self.headers.get("x-device_id")
)
header_client_id = _normalize_id(
    self.headers.get("client-id")
    or self.headers.get("client_id")
    or self.headers.get("x-client-id")
    or self.headers.get("x-client_id")
)

# 赋值优先级：Query > Header > 回退
chosen_device_id = device_id_from_query or header_device_id or header_client_id
chosen_client_id = client_id_from_query or header_client_id or chosen_device_id

if chosen_device_id:
    self.headers["device-id"] = chosen_device_id
    if chosen_client_id:
        self.headers["client-id"] = chosen_client_id
else:
    # 容错：仍未取到则自动分配，保证连接可用
    auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
    self.headers["device-id"] = auto_device_id
    self.headers["client-id"] = auto_device_id
```

### Issue: 设备注册失败处理不当
设备注册失败时没有正确关闭连接。

**Solution:**
```python
# 在 server 上注册设备路由（自动断开旧连接）
if self.server and self.device_id:
    ok = await self.server.register_device_handler(self.device_id, self)
    if ok is False:
        self.logger.bind(tag=TAG).error(f"设备注册失败: {self.device_id}")
        await ws.send("设备注册失败")
        await self.close(ws)
        return
```

### Issue: Connection Timeout Handling
Connections were staying open indefinitely when clients became idle, consuming server resources.

**Solution:**
Implemented configurable idle timeout with fallback values:
```python
# 放宽默认空闲阈值：默认 600s + 60s 兜底；允许配置覆盖
try:
    base_idle = int(self.config.get("close_connection_no_voice_time", 600))
except Exception:
    base_idle = 600
self.timeout_seconds = base_idle + 60  # 第一层之外的兜底关闭
```

### Issue: 服务器重启时TTY继承问题
后台重启时，如果继承了TTY，会导致nohup/background模式被SIGTTIN挂起。

**Solution:**
避免继承TTY，全部重定向：
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

## LLM Instance Management

### Issue: LLM Instance Management and Caching
Multiple LLM instances were being created unnecessarily for different purposes, causing memory issues.

**Solution:**
Implemented lazy loading with caching mechanism for LLM instances by purpose:
```python
def get_llm_for(self, purpose: str):
    """按用途/模式返回 LLM 实例，懒加载并缓存。
    purpose 可取："chat" | "meeting" | "coding" | "working" | "intent" | "memory"
    """
    # 缓存命中
    if key in self._llm_cache and self._llm_cache[key] is not None:
        return self._llm_cache[key]
    
    # 用途未配置专用 LLM，回退 default 并记录告警
    mapping_val = mapping.get(key, None)
    if mapping_val is None:
        self.logger.bind(tag=TAG).warning(
            f"get_llm_for: 未找到用途 {key} 的 llm_by_mode 配置，回退到 default"
        )
        mapping_val = mapping.get("default")
    
    # Try to get instance from server
    try:
        srv = getattr(self, "server", None)
        if srv and hasattr(srv, "get_or_create_llm") and callable(getattr(srv, "get_or_create_llm")) and alias:
            instance = srv.get_or_create_llm(alias, overrides)
            if instance is not None:
                self._llm_cache[key] = instance
                return instance
        # 回退默认
        self._llm_cache[key] = self.llm
        return self.llm
    except Exception as e:
        self.logger.bind(tag=TAG).warning(f"get_llm_for 失败({key}): {e}，回退默认LLM")
        self._llm_cache[key] = self.llm
        return self.llm
```

## Voice Activity Detection Issues

### Issue: VAD兜底策略 - 设备边界未检测到
超过fallback_ms未见设备边界时需要VAD兜底。

**Solution:**
```python
def check_vad_fallback(self):
    """检查是否需要VAD兜底（超过fallback_ms未见设备边界）"""
    if self.listen_state != "listening":
        return False
    if self.client_listen_mode != "manual":
        return False
    now_ms = int(time.time() * 1000)
    fallback_ms = int(meeting_cfg.get("vad_fallback_ms", 2000))
    last_event_ms = getattr(self, "_last_listen_event_ms", 0)
    if last_event_ms > 0 and (now_ms - last_event_ms) > fallback_ms:
        self.logger.bind(tag=TAG).debug(f"VAD兜底触发: {now_ms - last_event_ms}ms未见设备边界")
        return True
    return False
```

### Issue: 聆听状态去抖动问题
频繁的listen start/stop事件需要去抖动处理。

**Solution:**
最小去抖：忽略距上次同类事件 <300ms 的重复事件：
```python
# 最小去抖：忽略距上次同类事件 <300ms 的重复 start
now_ms = int(time.time() * 1000)
last_ms = int(getattr(conn, "_last_listen_start_ms", 0) or 0)
if now_ms - last_ms < 300:
    return
conn._last_listen_start_ms = now_ms
```

## Meeting Mode Issues

### Issue: Meeting Mode Throttling and Deduplication
Meeting mode was sending duplicate text segments and overwhelming the system with rapid updates.

**Solution:**
Added throttling and deduplication state management:
```python
# 会议模式相关缓存
self.meeting_segments = []  # [{"ts": int(ms), "text": str}]
self.meeting_start_ts = 0.0
self.meeting_last_snippet_ts = 0.0
self.meeting_last_snippet_index = 0
# 会议片段节流与幂等状态
self.meeting_recent_texts = {}
self.meeting_pending_texts = []
self.meeting_last_emit_ms = 0.0
self.meeting_finalized = False
```

## Compatibility Issues

### Issue: WebSocket Headers Compatibility with Different Libraries
Headers were not being parsed correctly due to different attribute naming conventions in websocket libraries.

**Solution:**
Implemented robust header parsing with multiple fallback attempts:
```python
try:
    raw_headers = getattr(ws, "request_headers", {})
    # 统一小写键，便于后续从 headers 获取 authorization/device-id
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

### Issue: JSON Send Method Compatibility
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

### Issue: Thread Pool Shutdown Compatibility
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

### Issue: Configuration Update Compatibility
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

## Error Handling and Security

### Issue: MCP工具调用结果解析失败
MCP工具返回的结果可能不是JSON格式，导致解析失败。

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

### Issue: Exception Information Leakage in Logs
Stack traces and error messages could contain sensitive information when logged.

**Solution:**
Implemented safe truncation for error logging:
```python
except Exception as e:
    stack_trace = traceback.format_exc()
    try:
        safe_e = truncate_for_log(str(e))
        safe_tb = truncate_for_log(stack_trace)
    except Exception:
        safe_e = str(e)
        safe_tb = stack_trace
    self.logger.bind(tag=TAG).error(f"Connection error: {safe_e}-{safe_tb}")
```

### Issue: Configuration Defaults and Type Safety
Configuration values could be missing or wrong type, causing runtime errors.

**Solution:**
Added defensive programming with type checking and defaults:
```python
def _get_base_config(self) -> Dict[str, Any]:
    try:
        srv = getattr(self, "server", None)
        base_cfg = getattr(srv, "config", None) if srv else None
        if isinstance(base_cfg, dict):
            return base_cfg
    except Exception:
        pass
    return self.config if isinstance(self.config, dict) else {}
```