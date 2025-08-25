# Backend Block 8 - Agent 1 Pain Points

## Issue: Device ID parsing from WebSocket handshake fails
The system struggled with reliable device-id extraction from WebSocket connections, causing connection failures.

**Solution:**
Implemented a multi-tier fallback system for device-id parsing:
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

# 容错：仍未取到则自动分配，保证连接可用
if not chosen_device_id:
    auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
    self.headers["device-id"] = auto_device_id
```

---

## Issue: WebSocket header processing inconsistencies
Different WebSocket libraries have varying header attribute naming conventions, causing parsing errors.

**Solution:**
Added comprehensive header normalization with multiple fallback strategies:
```python
try:
    # 优先使用 items() 以兼容 websockets 的 Headers 类型
    for k, v in raw_headers.items():
        headers_lower[str(k).lower()] = v
except Exception:
    try:
        headers_lower = {str(k).lower(): v for k, v in dict(raw_headers).items()}
    except Exception:
        headers_lower = {}
```

---

## Issue: LLM instance management and caching problems
Multiple modes (chat, meeting, coding, working) required different LLM configurations, leading to resource waste and configuration conflicts.

**Solution:**
Implemented per-purpose LLM caching with fallback mechanism:
```python
def get_llm_for(self, purpose: str):
    """按用途/模式返回 LLM 实例，懒加载并缓存。
    
    purpose 可取："chat" | "meeting" | "coding" | "working" | "intent" | "memory"
    """
    try:
        key = str(purpose or "chat").lower()
    except Exception:
        key = "chat"
    
    # 缓存命中
    if key in self._llm_cache and self._llm_cache[key] is not None:
        return self._llm_cache[key]
    
    # 统一委托 server 级共享工厂；失败回退默认 LLM
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

---

## Issue: Thread pool resource management and memory optimization
Initial thread pool configuration was too aggressive, causing high context switching and memory usage.

**Solution:**
Implemented configurable thread pool with conservative defaults:
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

---

## Issue: Function call parsing and error handling failures
LLM function calls sometimes returned malformed JSON or unexpected formats, causing parsing failures.

**Solution:**
Added robust function call parsing with multiple fallback strategies:
```python
if tool_call_flag:
    bHasError = False
    if function_id is None:
        a = extract_json_from_string(content_arguments)
        if a is not None:
            try:
                content_arguments_json = json.loads(a)
                function_name = content_arguments_json["name"]
                function_arguments = json.dumps(
                    content_arguments_json["arguments"], ensure_ascii=False
                )
                function_id = str(uuid.uuid4().hex)
            except Exception as e:
                bHasError = True
                response_message.append(a)
        else:
            bHasError = True
            response_message.append(content_arguments)
        if bHasError:
            self.logger.bind(tag=TAG).error(
                f"function call error: {content_arguments}"
            )
```

---

## Issue: Connection timeout management with insufficient grace period
Original timeout implementation was too abrupt, cutting off connections without warning users.

**Solution:**
Implemented graduated timeout with warning system:
```python
# 放宽默认空闲阈值：默认 600s + 60s 兜底；允许配置覆盖
try:
    base_idle = int(self.config.get("close_connection_no_voice_time", 600))
except Exception:
    base_idle = 600
self.timeout_seconds = base_idle + 60  # 第一层之外的兜底关闭

# In timeout check:
# 在关闭前先发送提示并提供缓冲期（与无声层策略一致）
try:
    await self.websocket.send(json.dumps({
        "type": "system",
        "event": "timeout_warning", 
        "message": "连接将因长时间空闲而关闭，如需继续请发送任意消息。"
    }))
except Exception:
    pass
# 给予 10 秒缓冲，若期间收到任何消息，reset_timeout 会取消下一轮关闭
try:
    await asyncio.sleep(10)
except Exception:
    pass
```

---

## Issue: Memory saving race conditions during connection closure
Memory saving operations were blocking connection cleanup, leading to hanging connections.

**Solution:**
Implemented non-blocking memory save with dedicated thread:
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

---

## Issue: MCP tool argument parsing JSON decode errors
MCP tool calls failed when function arguments weren't properly JSON encoded strings.

**Solution:**
Added argument type detection and parsing logic:
```python
def _handle_mcp_tool_call(self, function_call_data):
    function_arguments = function_call_data["arguments"]
    function_name = function_call_data["name"]
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

## Issue: WebSocket send method compatibility problems
Different WebSocket implementations have varying send method signatures, causing send failures.

**Solution:**
Created unified send wrappers with method detection and fallbacks:
```python
async def send_json(self, data: dict) -> bool:
    """统一的 JSON 消息发送封装，包含错误处理"""
    if not self.websocket:
        self.logger.bind(tag=TAG).warning("send_json: websocket is None")
        return False
    
    try:
        # 优先使用 send_json 方法
        if hasattr(self.websocket, 'send_json'):
            await self.websocket.send_json(data)
        else:
            # 回退到字符串发送
            await self.websocket.send(json.dumps(data, ensure_ascii=False))
        return True
    except websockets.exceptions.ConnectionClosed:
        # 连接已关闭，静默处理（预期情况）
        self.logger.bind(tag=TAG).debug(f"send_json: connection closed for device {self.device_id}")
        return False
    except Exception as e:
        # 其他异常，记录警告但不中断
        self.logger.bind(tag=TAG).warning(f"send_json failed for device {self.device_id}: {e}")
        return False
```

---

## Issue: Python version compatibility for ThreadPoolExecutor shutdown
Older Python versions don't support the `cancel_futures` parameter in executor shutdown.

**Solution:**
Added version-aware shutdown with try-except fallback:
```python
# 最后关闭线程池（避免阻塞）
if self.executor:
    try:
        # Python 3.9+ 支持 cancel_futures
        self.executor.shutdown(wait=False, cancel_futures=True)
    except TypeError:
        self.executor.shutdown(wait=False)
    self.executor = None
```

---

## Issue: ASR variable exposure in shared local ASR instances
Public local ASR instances couldn't have connection-specific variables, causing state conflicts.

**Solution:**
Segregated ASR variables to connection-private scope:
```python
# asr相关变量
# 因为实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR
# 所以涉及到ASR的变量，需要在这里定义，属于connection的私有变量
self.asr_audio = []
self.asr_audio_queue = queue.Queue()

def _initialize_asr(self):
    """初始化ASR"""
    if self._asr.interface_type == InterfaceType.LOCAL:
        # 如果公共ASR是本地服务，则直接返回
        # 因为本地一个实例ASR，可以被多个连接共享
        asr = self._asr
    else:
        # 如果公共ASR是远程服务，则初始化一个新实例
        # 因为远程ASR，涉及到websocket连接和接收线程，需要每个连接一个实例
        asr = initialize_asr(self.config)
    
    return asr
```