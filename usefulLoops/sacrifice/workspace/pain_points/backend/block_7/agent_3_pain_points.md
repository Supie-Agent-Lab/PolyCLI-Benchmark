# Pain Points from Backend Block 7

## Issue: WebSocket Headers Compatibility with Different Libraries
The system needed to handle headers from different WebSocket library implementations that may have different attribute naming conventions and data structures.

**Solution:**
Implemented a robust header parsing approach that tries multiple methods to extract headers:
```python
# 获取并验证headers（兼容 websockets 库的属性命名）
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
```

---

## Issue: Device ID Parsing from Multiple Sources
Device IDs could come from query parameters, headers with various naming conventions, or might be missing entirely, requiring a fallback mechanism.

**Solution:**
Implemented a multi-level parsing strategy with clear priority: Query > Header > Auto-generation
```python
# 从 Header 兜底解析（包含非规范写法）
header_device_id = _normalize_id(
    self.headers.get("device-id")
    or self.headers.get("device_id")
    or self.headers.get("x-device-id")
    or self.headers.get("x-device_id")
)
# 赋值优先级：Query > Header > 回退
chosen_device_id = device_id_from_query or header_device_id or header_client_id

if not chosen_device_id:
    # 容错：仍未取到则自动分配，保证连接可用
    auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
    self.headers["device-id"] = auto_device_id
```

---

## Issue: SIGTTIN Signal Blocking in Background Mode
When restarting the server in background/nohup mode, the process could get suspended by SIGTTIN signal if it tried to read from TTY.

**Solution:**
Redirect all standard streams to /dev/null to prevent TTY interaction:
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

## Issue: Event Loop Conflicts When Saving Memory
Attempting to save memory asynchronously could conflict with the main event loop, causing errors or blocking.

**Solution:**
Create a new event loop in a separate thread for memory saving operations:
```python
def save_memory_task():
    try:
        # 创建新事件循环（避免与主循环冲突）
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            self.memory.save_memory(self.dialogue.dialogue)
        )
    finally:
        loop.close()

# 启动线程保存记忆，不等待完成
threading.Thread(target=save_memory_task, daemon=True).start()
```

---

## Issue: LLM Instance Management and Caching
Multiple LLM instances needed to be managed for different purposes with proper fallback mechanisms when specific configurations weren't available.

**Solution:**
Implemented a caching system with fallback strategy:
```python
def get_llm_for(self, key):
    # 检查缓存
    if key in self._llm_cache:
        return self._llm_cache[key]
    
    mapping_val = mapping.get(key, None)
    if mapping_val is None:
        # 用途未配置专用 LLM，回退 default 并记录告警
        self.logger.bind(tag=TAG).warning(
            f"get_llm_for: 未找到用途 {key} 的 llm_by_mode 配置，回退到 default"
        )
        mapping_val = mapping.get("default")
    
    # 统一委托 server 级共享工厂；失败回退默认 LLM
    try:
        srv = getattr(self, "server", None)
        if srv and hasattr(srv, "get_or_create_llm"):
            instance = srv.get_or_create_llm(alias, overrides)
            if instance is not None:
                self._llm_cache[key] = instance
                return instance
    except Exception as e:
        self.logger.bind(tag=TAG).warning(f"get_llm_for 失败({key}): {e}，回退默认LLM")
    
    # 回退默认
    self._llm_cache[key] = self.llm
    return self.llm
```

---

## Issue: Timeout Management for WebSocket Connections
Connections needed proper timeout handling with the ability to reset timers when activity occurred.

**Solution:**
Implemented a cancellable timeout task system that resets on each message:
```python
def reset_timeout(self):
    """重置超时计时器"""
    if self.timeout_task and not self.timeout_task.done():
        self.timeout_task.cancel()
    self.timeout_task = asyncio.create_task(self._check_timeout())

async def _route_message(self, message):
    """消息路由"""
    # 重置超时计时器
    self.reset_timeout()
    
    # 轻量 ping/keepalive：收到后仅重置计时器并忽略
    if isinstance(obj, dict) and obj.get("type") in ("ping", "keepalive"):
        await self.websocket.send(json.dumps({"type": "pong"}))
        return
```

---

## Issue: Device Registration Failures
Device registration with the server could fail, but the error wasn't properly handled, leading to zombie connections.

**Solution:**
Added explicit registration failure handling with connection cleanup:
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

## Issue: Blocking Server Restart Operations
Server restart operations could block the event loop, preventing proper cleanup and response handling.

**Solution:**
Execute restart in a daemon thread to avoid blocking:
```python
def restart_server():
    """实际执行重启的方法"""
    time.sleep(1)
    self.logger.bind(tag=TAG).info("执行服务器重启...")
    # ... subprocess launch code ...
    os._exit(0)

# 使用线程执行重启避免阻塞事件循环
threading.Thread(target=restart_server, daemon=True).start()
```

---

## Issue: Diagnostic Information for Connection Failures
When device ID parsing failed, it was difficult to diagnose why without sufficient context about the connection attempt.

**Solution:**
Added comprehensive diagnostic snapshots including raw paths and header keys:
```python
try:
    raw_paths_snapshot = []
    if isinstance(raw_path_from_server, str) and raw_path_from_server:
        raw_paths_snapshot.append(raw_path_from_server[:256])
    # ... collect more path info ...
    header_keys = list(self.headers.keys())
    self.logger.bind(tag=TAG).warning(
        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}; "
        f"rawPaths={truncate_for_log(str(raw_paths_snapshot))}, "
        f"headerKeys={truncate_for_log(str(header_keys))}"
    )
```

---

## Issue: Configuration Alias Resolution Complexity
LLM configuration could use various keys (alias, name, module, llm) and needed robust parsing to handle all cases.

**Solution:**
Implemented flexible alias resolution with multiple fallback options:
```python
if isinstance(mapping_val, dict):
    # 支持 { alias: xxx, overrides: { model_name: '...' } } 或直接平铺覆盖字段
    alias = mapping_val.get("alias") or mapping_val.get("name") or \
            mapping_val.get("module") or mapping_val.get("llm")
    overrides = mapping_val.get("overrides")
    if overrides is None:
        # 将除别名键外的其余键视为覆盖
        tmp = dict(mapping_val)
        for k in ["alias", "name", "module", "llm", "overrides"]:
            tmp.pop(k, None)
        overrides = tmp if len(tmp) > 0 else None
```