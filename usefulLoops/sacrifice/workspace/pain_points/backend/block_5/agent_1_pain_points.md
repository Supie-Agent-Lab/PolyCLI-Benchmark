# Pain Points Extracted from Backend Block 5

## Issue: UI页面瞬时切换问题 - C1到P1的跳变
唤醒后仍然额外渲染了"过渡页/占位页"，以及标题未统一，导致看起来像"c1 → p1"的瞬时切换。用户体验到明显的页面闪烁，因为底部文字和中间文字都被替换了。

**Solution:**
- 移除对话开始时在 `chat()` 的"dlg-active"占位渲染，避免任何额外页切换
- 统一渲染清洗：`dialog.chat` 的 `header.title` 强制为"对话模式"（在 `render_schema.clean_render_payload` 中实现）
- 准备态直接渲染 p1（`dialog.chat`），不再发送任何 `net.banner` 或"建立连接中"页面
- 改为默认不发送"准备聆听"帧，仅在配置显式开启时才显示（`enable_ready_ui=false`）
- 唤醒后不再推一帧文字占位，避免底部提示与中间文案的瞬时替换

---

## Issue: 标题重复显示问题 - 两个C1
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

---

## Issue: 线程池上下文切换与内存占用过高
线程池默认配置过大，导致上下文切换频繁，内存占用高。

**Solution:**
缩减线程池，降低上下文切换与内存占用：
```python
# 固化 W3：线程池默认 2，可被 meeting.threadpool_max_workers 覆盖
default_workers = 2
max_workers = int(meeting_cfg.get("threadpool_max_workers", default_workers))
if max_workers < 1:
    max_workers = default_workers
self.executor = ThreadPoolExecutor(max_workers=max_workers)
```

---

## Issue: ASR变量暴露给公共ASR的问题
实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR。

**Solution:**
涉及到ASR的变量，需要在connection里定义，属于connection的私有变量：
```python
# 因为实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR
# 所以涉及到ASR的变量，需要在这里定义，属于connection的私有变量
self.asr_audio = []
self.asr_audio_queue = queue.Queue()
```

---

## Issue: 远程ASR实例化问题
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

---

## Issue: 设备注册失败处理不当
设备注册失败时没有正确关闭连接。

**Solution:**
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

## Issue: 记忆保存与事件循环冲突
保存记忆时直接使用主事件循环会导致冲突。

**Solution:**
创建新事件循环避免与主循环冲突：
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
```

---

## Issue: 服务器重启时TTY继承问题
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

---

## Issue: MCP工具调用结果解析失败
MCP工具返回的结果可能不是JSON格式，导致解析失败。

**Solution:**
```python
resultJson = None
if isinstance(result, str):
    try:
        resultJson = json.loads(result)
    except Exception as e:
        self.logger.bind(tag=TAG).error(
            f"解析MCP工具返回结果失败: {e}"
        )
```

---

## Issue: VAD兜底策略 - 设备边界未检测到
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
```

---

## Issue: LLM实例获取失败回退处理
按用途获取LLM实例时可能失败，需要有回退机制。

**Solution:**
```python
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

## Issue: 聆听状态去抖动问题
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

---

## Issue: 设备ID解析复杂性
从Query参数、Header等多个来源解析device-id，优先级混乱。

**Solution:**
统一调用服务器封装的握手解析，建立清晰的优先级：Query > Header > 回退自动分配：
```python
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