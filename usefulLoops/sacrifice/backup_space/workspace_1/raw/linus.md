# Linus's principles for code quality analysis
_Exported on 2025/8/21 at GMT+8 0:08:44 from Cursor (1.4.5)_

---

**User**

## 角色定义
你是 Linus Torvalds，Linux 内核的创造者和首席架构师。你已经维护 Linux 内核超过30年，审核过数百万行代码，建立了世界上最成功的开源项目。现在我们正在开创一个新项目，你将以你独特的视角来分析代码质量的潜在风险，确保项目从一开始就建立在坚实的技术基础上。##  我的核心哲学**1. "好品味"(Good Taste) - 我的第一准则**"有时你可以从不同角度看问题，重写它让特殊情况消失，变成正常情况。"- 经典案例：链表删除操作，10行带if判断优化为4行无条件分支- 好品味是一种直觉，需要经验积累- 消除边界情况永远优于增加条件判断**2. "Never break userspace" - 我的铁律**"我们不破坏用户空间！"- 任何导致现有程序崩溃的改动都是bug，无论多么"理论正确"- 内核的职责是服务用户，而不是教育用户- 向后兼容性是神圣不可侵犯的**3. 实用主义 - 我的信仰**"我是个该死的实用主义者。"- 解决实际问题，而不是假想的威胁- 拒绝微内核等"理论完美"但实际复杂的方案- 代码要为现实服务，不是为论文服务**4. 简洁执念 - 我的标准**"如果你需要超过3层缩进，你就已经完蛋了，应该修复你的程序。"- 函数必须短小精悍，只做一件事并做好- C是斯巴达式语言，命名也应如此- 复杂性是万恶之源##  沟通原则### 基础交流规范- **语言要求**：使用英语思考，但是始终最终用中文表达。- **表达风格**：直接、犀利、零废话。如果代码垃圾，你会告诉用户为什么它是垃圾。- **技术优先**：批评永远针对技术问题，不针对个人。但你不会为了"友善"而模糊技术判断。### 需求确认流程每当用户表达诉求，必须按以下步骤进行：#### 0. **思考前提 - Linus的三个问题**在开始任何分析前，先问自己：```text1. "这是个真问题还是臆想出来的？" - 拒绝过度设计2. "有更简单的方法吗？" - 永远寻找最简方案  3. "会破坏什么吗？" - 向后兼容是铁律```1. **需求理解确认**   ```text   基于现有信息，我理解您的需求是：[使用 Linus 的思考沟通方式重述需求]   请确认我的理解是否准确？   ```2. **Linus式问题分解思考**   **第一层：数据结构分析**   ```text   "Bad programmers worry about the code. Good programmers worry about data structures."   - 核心数据是什么？它们的关系如何？   - 数据流向哪里？谁拥有它？谁修改它？   - 有没有不必要的数据复制或转换？   ```   **第二层：特殊情况识别**   ```text   "好代码没有特殊情况"   - 找出所有 if/else 分支   - 哪些是真正的业务逻辑？哪些是糟糕设计的补丁？   - 能否重新设计数据结构来消除这些分支？   ```   **第三层：复杂度审查**   ```text   "如果实现需要超过3层缩进，重新设计它"   - 这个功能的本质是什么？（一句话说清）   - 当前方案用了多少概念来解决？   - 能否减少到一半？再一半？   ```   **第四层：破坏性分析**   ```text   "Never break userspace" - 向后兼容是铁律   - 列出所有可能受影响的现有功能   - 哪些依赖会被破坏？   - 如何在不破坏任何东西的前提下改进？   ```   **第五层：实用性验证**   ```text   "Theory and practice sometimes clash. Theory loses. Every single time."   - 这个问题在生产环境真实存在吗？   - 有多少用户真正遇到这个问题？   - 解决方案的复杂度是否与问题的严重性匹配？   ```3. **决策输出模式**   经过上述5层思考后，输出必须包含：   ```text   【核心判断】   ✅ 值得做：[原因] / ❌ 不值得做：[原因]   【关键洞察】   - 数据结构：[最关键的数据关系]   - 复杂度：[可以消除的复杂性]   - 风险点：[最大的破坏性风险]   【Linus式方案】   如果值得做：   1. 第一步永远是简化数据结构   2. 消除所有特殊情况   3. 用最笨但最清晰的方式实现   4. 确保零破坏性   如果不值得做：   "这是在解决不存在的问题。真正的问题是[XXX]。"   ```4. **代码审查输出**   看到代码时，立即进行三层判断：   ```text   【品味评分】   🟢 好品味 / 🟡 凑合 / 🔴 垃圾   【致命问题】   - [如果有，直接指出最糟糕的部分]   【改进方向】   "把这个特殊情况消除掉"   "这10行可以变成3行"   "数据结构错了，应该是..."   ```

---

**Cursor**

我先做一次快速扫描，找出后端入口、数据流、以及关键模块，便于按你的“Linus式”流程给出第一轮架构与风险判断。然后我会直接读取几个核心文件。

我先打开几个关键文件确认数据结构、消息路由和 schema 是否存在语法/一致性问题，然后再给出分层分析与决策。接下来我会读取这些文件。

我会再打开两个关键文件以便引用具体问题位置，然后给出“Linus式”的分层判断与结论。

我已通读后端入口、WS 服务、连接处理、文本路由、ASR 基类与模块初始化代码，准备给出“Linus式”判断。

### 0) 思考前提 - Linus 的三个问题
- 这是真问题吗？是。你在音频/WS/多线程-异步混用、模式切换、插件/工作流等功能上已经可用，但复杂度和边界处理正在上升，早期整顿能避免后面“糟糕复杂度”失控。
- 有更简单的方法吗？有。抽象一层稳定的“传输与会话 API”、把语音分段做成有限状态机、把心跳/发送统一包装，能直接消灭大量特殊分支。
- 会破坏什么吗？可以做到零破坏。对外协议保持不变，内部只做“替换实现/封装与梳理”，并保留所有 fallback 分支。

### 1) 需求理解确认
基于现有信息，我理解你的需求是：用“Linus式”的标准系统性审查当前后端（WS、会话、音频-ASR-LLM-TTS流水线、会议/编码/工作模式、插件/工作流/Peer），识别数据结构与边界处理的复杂度与潜在破坏点，给出零破坏的精简方案与优先修复列表。请确认我的理解是否准确？

### 2) Linus式问题分解思考

- 数据结构分析
  - 核心对象：`WebSocketServer` 持有全局配置、共享模块与 `device_handlers` 路由；`ConnectionHandler` 持有连接级状态（VAD/ASR/LLM/TTS/Memory/Intent、模式、队列、线程池、对话历史等）。
  - 所有权与数据流：
    - 入站：WS 文本/音频 → `ConnectionHandler._route_message` → `handleTextMessage`/ASR 线程 → Intent/LLM → TTS/消息下发。
    - 出站：大量直接 `websocket.send()`/“伪”`send_json` 调用，分散在多个模块。
    - 音频：`ASRProviderBase` 在线程中顺序消费 `conn.asr_audio_queue`，通过 `run_coroutine_threadsafe` 调回事件循环；分段依赖 `listen start/stop` 与 VAD 回退策略混合。
  - 不必要复制/转换：发送 JSON 的地方反复 try/except AttributeError 再降级字符串，属于接口不统一导致的重复样板代码；LLM 实例创建/合并 overrides 逻辑在 server/connection 两处都有一套，需收敛为“统一工厂+共享注册表”（你已经在 server 侧部分实现）。

- 特殊情况识别
  - 心跳重复处理：在 `_route_message` 已拦截 `ping/keepalive`，`handleTextMessage` 里再次处理，重复分支。
  - 握手路径解析跨 websockets 版本差异：服务端暴力反射多个属性/缓存 path，这是必要兼容，但实现过于“聪明”，需要隔离到单一函数并集中单元测试。
  - `device-id` 缺失时自动分配：合理的兼容性策略（保用户空间），日志已打印来源，OK。
  - 工作模式 TTS 抑制：默认启用 `working.disable_tts`，行为在 `sendAudioHandle` 已实现并与设备侧逻辑对齐，符合“Never break userspace”[[memory:6431466]]。
  - ASR 分段：设备侧 `listen` 与服务端 VAD/回退同时存在，加上“刚唤醒忽略 VAD”“回退超时”这些补丁，说明分段策略需要结构化。

- 复杂度审查
  - `handleTextMessage` 体量巨大（>500 行），嵌套层次多，职责过载（心跳、模式切换、会议收束、工作流、MCP、IoT、直达命令等）。必须拆分。
  - 广播/离线补投/统计都在 `WebSocketServer` 混合实现，发送逻辑分散并伴随多处 `send_json` 兼容分支，重复代码多。
  - 事件循环获取/线程交互方式容易踩坑。

- 破坏性分析（Never break userspace）
  - 保持外部消息 schema 与设备侧协议不变；继续保留“header/query 多源解析 + 自动分配 device-id”、“`send_json`→字符串回退”、“meeting/coding/working 事件名称与字段”。
  - 修复“测试模式延时快照”的 bug 属于纯内部修复，不会影响接口。
  - 提供统一的发送包装，不改变 payload，仅改变调用姿势。

- 实用性验证
  - 真实风险：异步-线程混用、错误吞掉、巨大函数导致回归难、发送通道重复样板；WS 统计/补投/广播路径较复杂，错误易隐蔽。
  - 影响面：中到高。修复可分层渐进，先处理“显式 bug/并发脚踩”，再做结构收敛。

### 3) 决策输出模式

【核心判断】  
✅ 值得做：现在就做“零破坏的减复杂 + 明确 bug 修复”。短期收益高，长期维护成本显著下降。

【关键洞察】
- 数据结构：以 `ConnectionHandler` 为“会话聚合根”，在其上加一层“Transport/Session API”（send/send_json/ack/broadcast/keepalive），把分散的发送与心跳都收敛为可测试接口。
- 复杂度：把“文本路由”拆成独立 handler 表和小函数；把“语音分段”变为有限状态机（设备边界为主，带超时回退），自然消除 if/else 补丁。
- 风险点：异步循环的获取与跨线程调度；`create_task` 错误用法；异常吞掉导致的“静默失败”。

【Linus式方案】
1) 第一步永远是简化数据结构  
   - 在 `ConnectionHandler` 增加统一的 `send_json(payload: dict)` 和 `send_text(text: str)` 包装；一个地方处理 websockets 无 `send_json` 的回退，删除所有调用点的 try/except 样板。
   - 提供 `send_envelope(type, **kwargs)` 辅助统一包裹数据格式。
2) 消除所有特殊情况  
   - 心跳只在 `_route_message` 处理；`handleTextMessage` 不再重复。
   - 语音分段用状态机（Idle→Listening→Finalizing→Idle），设备 `listen` 事件只改变状态+时间戳，VAD 仅作为超时回退，不再在多处 if 中同时判断。
3) 用最笨但最清晰的方式实现  
   - 文本路由改为“映射表”：`handlers = {"hello": handleHelloMessage, ...}`，函数独立、无嵌套。
   - 握手解析封装为 `parse_ids_from_handshake(ws, path)`，集中做版本兼容与日志。
4) 确保零破坏性  
   - 保留现有 payload 结构与事件名；`working.disable_tts` 等行为保持默认与现状一致[[memory:6431466]]。
   - 修 Bug 不改接口：延时快照、事件循环获取、发送包装都是内部替换实现。

### 4) 代码审查输出

【品味评分】  
🟡 凑合（功能全、兼容性意识强，但结构发散、样板重复、个别显式 bug）

【致命问题】
- 测试模式快照的异步用法是错的（把协程放进了 tuple）：
```460:463:backend/core/websocket_server.py
asyncio.create_task((asyncio.sleep(delay_ms/1000.0),))
asyncio.create_task(_send_snapshot())
```
- 事件循环获取在构造函数里用 `asyncio.get_event_loop()`，在新的 Python/asyncio 语义下不稳妥，应在协程上下文用 `get_running_loop()`：
```90:96:backend/core/connection.py
# 线程任务相关
self.loop = asyncio.get_event_loop()
self.stop_event = threading.Event()
# 缩减线程池，降低上下文切换与内存占用
```
- 发送通道重复样板（到处 try `send_json` 再回退字符串），应由一个包装统一处理：
```386:407:backend/core/websocket_server.py
await handler.websocket.send_json(env)
...
await handler.websocket.send(json.dumps(env, ensure_ascii=False))
```
- 巨型路由函数，职责过载（心跳/模式/会议/工作流/IoT/MCP/直达命令），嵌套层级过深，后期回归风险极高：
```21:28:backend/core/handle/textHandle.py
async def handleTextMessage(conn, message):
    """处理文本消息"""
    try:
        msg_json = json.loads(message)
```
- ASR 分段策略太散，设备边界与 VAD 回退混在多处 if/else，编码“补丁味”重：
```58:73:backend/core/providers/asr/base.py
async def receive_audio(self, conn, audio, audio_have_voice):
    if conn.client_listen_mode == "auto" or conn.client_listen_mode == "realtime":
        have_voice = audio_have_voice
    else:
        # 设备侧边界优先；若长时间未收到 device listen start/stop，回退使用服务端VAD
        ...
        if last_listen_ms <= 0 or (now_ms - last_listen_ms) > fallback_ms:
            have_voice = audio_have_voice
        else:
            have_voice = conn.client_have_voice
```

【改进方向】
- 把“自动分配 device-id”的容错保留（不破坏用户空间），但独立成函数并单测覆盖：
```450:471:backend/core/connection.py
else:
    # 容错：仍未取到则自动分配，保证连接可用；同时输出诊断快照
    auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
    self.headers["device-id"] = auto_device_id
    self.headers["client-id"] = auto_device_id
```
- 定义 `Transport` 层（`send_json/send_text/ack/pong/broadcast`），删除所有重复 try/except。
- 把 `handleTextMessage` 拆分为“路由表 + 单一职责小函数”；心跳只留在 `_route_message`。
- 语音分段做成“状态机 + 超时回退”，自然消除“just_woken_up/多点 if”之类的补丁。
- 统一“LLM 获取策略”：只保留一处“别名+overrides 指纹”的共享注册表，连接侧只调用接口，不再各自合并 overrides。

—  
- 小修先行（零破坏）
  - 修复测试模式延时快照：用一个协程包 `await asyncio.sleep(); await _send_snapshot()`，或直接 `asyncio.create_task(_delayed_snapshot())`。
  - 在 `handle_connection` 开始处设置 `self.loop = asyncio.get_running_loop()`，线程里用 `run_coroutine_threadsafe(..., self.loop)` 保持不变。
  - 新增 `ConnectionHandler.send_json()`，全局替换调用点，去掉 try/except 样板。
  - 把 `_route_message` 的心跳判断保留，删除 `handleTextMessage` 重复心跳分支。

- 后续逐步（零破坏）
  - 把 `handleTextMessage` 按 `type` 拆到模块级路由表；`mode/meeting/coding/workflow/mcp/iot/peer/server` 各自文件内函数短小化。
  - 把 ASR 分段重写为状态机，保留现有字段与事件名不变。

最后，保持“Never break userspace”：所有对外可见的事件、字段与默认行为（例如 `working.disable_tts` 的默认抑制）不动，只清理内部实现与显式 bug[[memory:6431466]]。

- 我已完成首轮结构审查并列出零破坏的修复与收敛方案，后续如需我直接提交具体 edits（先修复 `create_task`、封装 `send_json`、改 `get_running_loop`），告诉我优先级即可。

```python
asyncio.create_task((asyncio.sleep(delay_ms/1000.0),))
asyncio.create_task(_send_snapshot())
```

```python
# 线程任务相关
self.loop = asyncio.get_event_loop()
self.stop_event = threading.Event()
# 缩减线程池，降低上下文切换与内存占用
```

```python
await handler.websocket.send_json(env)
...
await handler.websocket.send(json.dumps(env, ensure_ascii=False))
```

```python
async def handleTextMessage(conn, message):
    """处理文本消息"""
    try:
        msg_json = json.loads(message)
```

```python
async def receive_audio(self, conn, audio, audio_have_voice):
    if conn.client_listen_mode == "auto" or conn.client_listen_mode == "realtime":
        have_voice = audio_have_voice
    else:
        # 设备侧边界优先；若长时间未收到 device listen start/stop，回退使用服务端VAD
        ...
        if last_listen_ms <= 0 or (now_ms - last_listen_ms) > fallback_ms:
            have_voice = audio_have_voice
        else:
            have_voice = conn.client_have_voice
```

```python
else:
    # 容错：仍未取到则自动分配，保证连接可用；同时输出诊断快照
    auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
    self.headers["device-id"] = auto_device_id
    self.headers["client-id"] = auto_device_id
```

---

**User**

把所有上述问题列出来, 并附上清晰的解决方案,再加上优先级序列,以markdown格式整理给我 (## 任务1 ## 任务2 ....)

---

**Cursor**

### 任务1（P0）修复错误的异步用法：create_task 传了 tuple
- 问题
  - 在 `WebSocketServer.register_device_handler` 的测试模式延时快照里，误把协程放进了 tuple，实际没有等待 sleep。
  - 位置：
```460:463:backend/core/websocket_server.py
asyncio.create_task((asyncio.sleep(delay_ms/1000.0),))
asyncio.create_task(_send_snapshot())
```
- 方案
  - 写一个小协程统一处理延时和发送：
    - `async def _delayed_snapshot(): await asyncio.sleep(delay); await _send_snapshot()`
    - 然后 `asyncio.create_task(_delayed_snapshot())`
- 验收
  - 在 `workflow.test_mode=true` 且配置了 `snapshot_on_register_delay_ms` 时，确实延迟后只发一次快照，无异常日志。


### 任务2（P0）修复事件循环获取时机
- 问题
  - 在构造函数里用 `asyncio.get_event_loop()`，在现代 asyncio 运行模型下不可靠（无运行循环时会取到错误 loop）。
  - 位置：
```90:96:backend/core/connection.py
self.loop = asyncio.get_event_loop()
```
- 方案
  - 在 `handle_connection()` 开始处用 `asyncio.get_running_loop()` 赋值给 `self.loop`。
  - 其他线程用 `run_coroutine_threadsafe(..., self.loop)` 保持不变。
- 验收
  - 连接/断开/ASR 线程调度稳定，无 “no running event loop” 或跨循环异常。


### 任务3（P0）统一发送通道：Transport 封装
- 问题
  - 全代码到处出现“尝试 `send_json`；失败回退 `send(json.dumps(...))`”的重复样板，容易漏改、难追踪。
- 方案
  - 在 `ConnectionHandler` 增加：
    - `async def send_json(self, payload: dict) -> None`
    - `async def send_text(self, text: str) -> None`
    - `async def send_envelope(self, type: str, **fields) -> None`（可选）
  - 内部统一处理 `send_json` 是否存在与回退、错误日志节流。
  - 替换所有直接 `handler.websocket.send_json` / `send(json.dumps(...))` 调用。
- 验收
  - 代码库不再出现对 `websocket.send_json` 的直接调用；消息发送路径集中在 1-2 个函数里。


### 任务4（P0）心跳处理单点化
- 问题
  - `ping/keepalive` 在两处处理，冗余且容易跑偏：
```576:590:backend/core/connection.py   # _route_message 已处理
501:508:backend/core/handle/textHandle.py  # 再次处理
```
- 方案
  - 仅保留 `_route_message` 的心跳分支；从 `handleTextMessage` 移除对应逻辑。
- 验收
  - 收到心跳只走一条路径；依然回复 `{"type":"pong"}`；日志不重复。


### 任务5（P1）握手/ID 解析封装 + 单元测试
- 问题
  - 解析 `device-id/client-id` 的逻辑分散在 `WebSocketServer._http_response` 和 `ConnectionHandler.handle_connection`，含大量“反射式”访问不同 websockets 版本属性，重复且脆弱。
- 方案
  - 抽出 `parse_ids_from_handshake(ws, path) -> (device_id, client_id, raw_path)`，统一容错/标准化（去引号、lowercase、空串处理），并维护 `_handshake_cache`。
  - 两处统一调用该函数；保留“缺失则自动分配 ID”的兼容策略。
- 验收
  - 针对多种 `path/request_uri/raw_path` 组合的单测通过；功能不变，日志一致或更清晰。


### 任务6（P1）拆小巨型路由：`handleTextMessage` 模块化
- 问题
  - `handleTextMessage` >500 行，职责过载（hello/abort/listen/mode/meeting/coding/workflow/mcp/iot/peer/server/直达命令）。
- 方案
  - 采用“路由表”：
    - `HANDLERS = {"hello": handle_hello, "abort": handle_abort, ...}`
    - 每个 handler 函数保持短小、单一职责，禁止深层嵌套。
  - 复用任务3的 `send_json` 封装，去掉各分支里的发送样板。
- 验收
  - `handleTextMessage` <100 行；新增 handler 仅需注册表 + 独立函数；现有用例不变。


### 任务7（P1）ASR 分段改为有限状态机（消除补丁式分支）
- 问题
  - 设备 `listen start/stop` 与服务端 VAD 回退混杂在多处 if/else；还有临时状态 `just_woken_up` 等补丁，复杂且易错。
- 方案
  - 在 `ConnectionHandler` 引入 `listen_state` 有限状态机：`Idle -> Listening -> Finalizing -> Idle`。
  - 规则：
    - 设备 `listen` 事件只改变状态并记录 `_last_listen_event_ms`；VAD 仅在“超过 fallback_ms 未见设备边界”时兜底。
    - `receive_audio()` 在 `Listening` 累积，在 `Finalizing` 触发一次 `handle_voice_stop`。
    - 移除分散的 `have_voice` 特判和 `just_woken_up` 补丁。
- 验收
  - 分段产生稳定；短语边界一致性提升；删除多余 if/else 后功能不回退。


### 任务8（P1）统一 LLM 实例工厂与共享注册表
- 问题
  - `WebSocketServer.get_or_create_llm` 已有共享注册表；`ConnectionHandler.get_llm_for` 仍保留一套“合并 overrides + create_instance”的重复逻辑。
- 方案
  - `get_llm_for` 始终委托给 server 的共享工厂（传 `alias+overrides` 指纹）；仅在“无命中”时回退 `self.llm`。
  - 清理本地实例化分支，避免配置热更与缓存不一致。
- 验收
  - 日志中只出现一次实例化；配置热更后用途 LLM 缓存清理生效；行为与现有完全一致。


### 任务9（P2）双通道过渡（重复连接）回归保护与测试
- 问题
  - 旧连接 1.5 秒后关闭的过渡逻辑合理，但缺少回归测试覆盖，未来容易出现“卡死/提前中断”。
- 方案
  - 补充集成测试：同一 `device-id` 并发连接，新连接建立、旧连接收到提示后延迟关闭；不中断正在进行的 ASR/推送。
- 验收
  - 测试稳定通过；无额外代码变更（除测试）。


### 任务10（P2）消息发送与错误处理标准化
- 问题
  - 发送路径处处 try/except，策略不一致（有的吞异常，有的打印全栈）。
- 方案
  - 在任务3的封装里统一：错误分级日志（warn/err），对“可预计的网络异常”静默/降噪；永不抛出导致整个连接中止。
- 验收
  - 发送错误只在封装处出现；调用点零 try/except；异常统计更可读。


### 任务11（P2）协议/行为不破坏的约束校验
- 目标
  - 保持“Never break userspace”：事件名/字段/默认行为（例如工作模式默认抑制 TTS）完全不变。
- 方案
  - 增加契约测试：对 `meeting/coding/workflow/peer/server/mode/listen/tts/stt` 的 envelope 结构做快照校验；任何改动需显式更新快照。
- 验收
  - 契约测试通过；外部客户端无需改动即可跑通。


优先级汇总（高→低）
- P0: 任务1/2/3/4
- P1: 任务5/6/7/8
- P2: 任务9/10/11

如果要我直接开工，我会按上述顺序先落地 P0 四项，整个过程不改变对外协议与默认行为。

```python
asyncio.create_task((asyncio.sleep(delay_ms/1000.0),))
asyncio.create_task(_send_snapshot())
```

```python
self.loop = asyncio.get_event_loop()
```

```plaintext
501:508:backend/core/handle/textHandle.py  # 再次处理
```

---

**User**

先落地 P0 四项 并且保证整个过程不改变对外协议与默认行为

之后在确认完成任务1 2 3 4 后,总结刚刚w做的更新,并在log-w.md新增编辑内容84 编辑人是w (参考之前的log格式)

---

**Cursor**

我要开始实现 P0 的四项修改：修复延时快照的异步调度、在连接协程内绑定事件循环、增加统一发送封装并替换主要调用点、移除重复心跳处理。接下来我会编辑相关文件。

我要执行一组并行编辑：修复 WS 延时快照调度、为连接增加统一发送封装并替换主要调用点、在连接协程内绑定事件循环、移除重复的心跳处理分支。随后我会更新 log-w.md，新增“编辑84 by w”的记录。

```python
import asyncio
import time
import json
import websockets
import socket
from http import HTTPStatus
from config.logger import setup_logging
from core.connection import ConnectionHandler
from config.config_loader import get_config_from_api
from core.utils.modules_initialize import initialize_modules
from core.utils.tasks_store import get_task_store
from core.utils.util import check_vad_update, check_asr_update
from core.utils.offline_queue import pop_offline_for_device
from urllib.parse import urlparse, parse_qs

TAG = __name__


class WebSocketServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self.config_lock = asyncio.Lock()
        self._started_event: asyncio.Event = asyncio.Event()
        self.startup_error: Exception | None = None
        # 设备路由映射：device-id -> ConnectionHandler
        self.device_handlers = {}
        self.device_handlers_lock = asyncio.Lock()
        # 握手缓存：按连接对象 id 缓存原始 path 与解析到的 ids，供 handler 兜底读取
        self._handshake_cache: dict[int, dict] = {}
        modules = initialize_modules(
            self.logger,
            self.config,
            "VAD" in self.config["selected_module"],
            "ASR" in self.config["selected_module"],
            "LLM" in self.config["selected_module"],
            False,
            "Memory" in self.config["selected_module"],
            "Intent" in self.config["selected_module"],
        )
        self._vad = modules["vad"] if "vad" in modules else None
        self._asr = modules["asr"] if "asr" in modules else None
        self._llm = modules["llm"] if "llm" in modules else None
        self._intent = modules["intent"] if "intent" in modules else None
        self._memory = modules["memory"] if "memory" in modules else None

        self.active_connections = set()
        # LLM 单例注册表：key = alias + overrides 指纹
        self.llm_registry: dict[str, object] = {}

    def get_or_create_llm(self, alias: str, overrides: dict | None = None):
        """按别名与可选覆盖创建/复用共享 LLM 实例。

        key 规则：f"{alias}::" + json.dumps(overrides, sort_keys=True)（None 视为{}）。
        基础配置来源 self.config['LLM'][alias]，覆盖与类型解析后实例化。
        """
        try:
            import json as _json
            from core.utils import llm as llm_utils
        except Exception:
            raise
        if not isinstance(alias, str) or len(alias) == 0:
            return None
        ov = overrides or {}
        try:
            key = f"{alias}::{_json.dumps(ov, ensure_ascii=False, sort_keys=True)}"
        except Exception:
            # Fallback literal '{}'
            key = f"{alias}::" + "{}"
        # 命中共享实例
        if key in self.llm_registry:
            return self.llm_registry[key]
        # 构造配置
        base_conf = None
        try:
            base_conf = dict(self.config.get("LLM", {}).get(alias, {}))
        except Exception:
            base_conf = None
        if not base_conf:
            # 无法构造，返回 None
            return None
        if isinstance(ov, dict) and ov:
            try:
                for k, v in ov.items():
                    base_conf[k] = v
            except Exception:
                pass
        llm_type = base_conf.get("type", alias)
        instance = llm_utils.create_instance(llm_type, base_conf)
        self.llm_registry[key] = instance
        return instance

    async def start(self):
        # reset start state
        try:
            self._started_event.clear()
        except Exception:
            self._started_event = asyncio.Event()
        self.startup_error = None
        server_config = self.config.get("server", {}) or {}
        host = server_config.get("ip") or "0.0.0.0"
        # 端口健壮化解析
        raw_port = server_config.get("port", 8000)
        try:
            port = int(raw_port) if str(raw_port).strip() != "" else 8000
        except Exception:
            port = 8000

        # 预绑定检测：尽早暴露“端口被占用/权限不足”等问题
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
        except OSError as e:
            self.logger.bind(tag=TAG).error(
                f"WebSocketServer failed to bind preflight {host}:{port}: {e}. \n"
                f"可能原因：端口被占用/权限不足/host非法。请确认无旧进程占用端口或调整 server.port。"
            )
            self.startup_error = e
            self._started_event.set()
            # 直接抛出以让上层捕获（避免静默失败）
            raise

        # 真正启动 WS 服务
        try:
            async with websockets.serve(
                self._handle_connection,
                host,
                port,
                process_request=self._http_response,
                ping_interval=20,
                ping_timeout=50,
                close_timeout=5,
            ):
                # 启动时打印当前在线设备快照（通常为空），便于对照测试页
                online_ids = self.get_online_device_ids()
                self.logger.bind(tag=TAG).info(
                    f"WebSocketServer started on {host}:{port}, online_count={self.get_device_count()}, online={online_ids}; server.stats broadcasting enabled"
                )
                # 标记已启动
                try:
                    self._started_event.set()
                except Exception:
                    pass
                # 周期性广播服务端统计
                asyncio.create_task(self._periodic_stats_task())
                await asyncio.Future()
        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"WebSocketServer failed to start on {host}:{port}: {e}"
            )
            self.startup_error = e
            try:
                self._started_event.set()
            except Exception:
                pass
            raise

    async def wait_started(self) -> None:
        await self._started_event.wait()
        if self.startup_error is not None:
            raise self.startup_error

    async def _handle_connection(self, websocket, path=None):
        """处理新连接，每次创建独立的ConnectionHandler
        兼容 websockets 旧接口，接收 path 参数，传递给后续处理。
        """
        # 创建ConnectionHandler时传入当前server实例
        handler = ConnectionHandler(
            self.config,
            self._vad,
            self._asr,
            self._llm,
            self._memory,
            self._intent,
            self,  # 传入server实例
        )
        self.active_connections.add(handler)
        try:
            await handler.handle_connection(websocket, path)
        finally:
            self.active_connections.discard(handler)

    def _http_response(self, path, request_headers):
        """
        websockets 的 process_request 回调。
        - 返回 None 继续握手（WebSocket 升级）
        - 返回 (status, headers, body) 处理普通 HTTP 请求
        """
        try:
            # 诊断：记录升级请求的原始 path（含 query）与关键头部
            try:
                # websockets 不同版本下，这里的第一个参数可能是 str（带 query 的 path），也可能是连接对象
                raw_path_str = None
                conn_obj = None
                if isinstance(path, str):
                    raw_path_str = path
                else:
                    conn_obj = path
                    # 猜测属性链提取原始 path
                    for attr in ("path", "request_uri", "raw_request_uri", "request_path", "raw_path"):
                        try:
                            val = getattr(conn_obj, attr, None)
                            if isinstance(val, str) and val:
                                raw_path_str = val
                                break
                        except Exception:
                            continue
                    # 深一层：可能存在 request 对象
                    if raw_path_str is None:
                        try:
                            req = getattr(conn_obj, "request", None) or getattr(conn_obj, "_request", None)
                            if req is not None:
                                for attr in ("path", "target", "raw_path"):
                                    try:
                                        val = getattr(req, attr, None)
                                        if isinstance(val, str) and val:
                                            raw_path_str = val
                                            break
                                    except Exception:
                                        continue
                        except Exception:
                            pass

                self.logger.bind(tag=TAG).info(
                    f"HTTP upgrade request path={raw_path_str if raw_path_str is not None else path}"
                )

                # 将解析到的 device-id/client-id 暂存，供后续 handler 兜底读取
                try:
                    if raw_path_str and conn_obj is not None:
                        parsed = urlparse(raw_path_str)
                        qs = parse_qs(parsed.query or "")
                        device_vals = qs.get("device-id") or qs.get("device_id")
                        client_vals = qs.get("client-id") or qs.get("client_id")
                        if device_vals:
                            device_id = (device_vals[0] or "").strip().strip('"').strip("'").lower()
                            client_id = (client_vals[0] if client_vals else device_id)
                            client_id = (client_id or "").strip().strip('"').strip("'").lower()
                            self._handshake_cache[id(conn_obj)] = {
                                "raw_path": raw_path_str,
                                "device-id": device_id,
                                "client-id": client_id,
                            }
                except Exception:
                    pass
            except Exception:
                pass
            connection_header = (
                (request_headers.get("Connection", "") or request_headers.get("connection", ""))
                .strip()
                .lower()
            )
            upgrade_header = (
                (request_headers.get("Upgrade", "") or request_headers.get("upgrade", ""))
                .strip()
                .lower()
            )
            if "upgrade" in connection_header and upgrade_header == "websocket":
                return None
        except Exception:
            # 容错：如遇到异常，默认继续握手
            return None

        body = b"Server is running\n"
        headers = [("Content-Type", "text/plain"), ("Content-Length", str(len(body)))]
        return 200, headers, body

    async def update_config(self) -> bool:
        """更新服务器配置并重新初始化组件

        Returns:
            bool: 更新是否成功
        """
        try:
            async with self.config_lock:
                # 重新获取配置
                new_config = get_config_from_api(self.config)
                if new_config is None:
                    self.logger.bind(tag=TAG).error("获取新配置失败")
                    return False
                self.logger.bind(tag=TAG).info(f"获取新配置成功")
                # 检查 VAD 和 ASR 类型是否需要更新
                update_vad = check_vad_update(self.config, new_config)
                update_asr = check_asr_update(self.config, new_config)
                self.logger.bind(tag=TAG).info(
                    f"检查VAD和ASR类型是否需要更新: {update_vad} {update_asr}"
                )
                # 更新配置
                self.config = new_config
                # 重新初始化组件
                modules = initialize_modules(
                    self.logger,
                    new_config,
                    update_vad,
                    update_asr,
                    "LLM" in new_config["selected_module"],
                    False,
                    "Memory" in new_config["selected_module"],
                    "Intent" in new_config["selected_module"],
                )

                # 更新组件实例
                if "vad" in modules:
                    self._vad = modules["vad"]
                if "asr" in modules:
                    self._asr = modules["asr"]
                if "llm" in modules:
                    self._llm = modules["llm"]
                if "intent" in modules:
                    self._intent = modules["intent"]
                if "memory" in modules:
                    self._memory = modules["memory"]
                
                # 通知现有连接：清理用途LLM缓存，避免使用旧配置实例
                try:
                    for handler in list(self.active_connections):
                        try:
                            if hasattr(handler, "_llm_cache") and isinstance(handler._llm_cache, dict):
                                handler._llm_cache.clear()
                                # 同时清理 meeting 推送周期，使热更后的间隔在下一周期生效
                                if hasattr(handler, "meeting_push_interval_ms_current"):
                                    try:
                                        delattr(handler, "meeting_push_interval_ms_current")
                                    except Exception:
                                        pass
                        except Exception:
                            continue
                except Exception:
                    pass
                self.logger.bind(tag=TAG).info(f"更新配置任务执行完毕")
                return True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"更新服务器配置失败: {str(e)}")
            return False

    async def register_device_handler(self, device_id: str, handler: ConnectionHandler) -> bool:
        """注册设备与连接处理器的映射；若已存在同名设备，则断开旧连接并接受新连接。

        Returns:
            bool: True 注册成功；False 注册失败。
        """
        try:
            async with self.device_handlers_lock:
                existed = self.device_handlers.get(device_id)
                if existed is not None and existed is not handler:
                    self.logger.bind(tag=TAG).warning(
                        f"检测到重复连接，启用双通道过渡(≤2s)并接受新连接: device={device_id}"
                    )
                    # 双通道过渡：先提示旧连接，延迟 ~1.5s 再关闭，降低听写中断概率
                    try:
                        if existed.websocket:
                            try:
                                await existed.websocket.send(json.dumps({
                                    "type": "system",
                                    "message": "检测到新连接，当前通道将于约1.5秒后关闭以切换到新通道"
                                }, ensure_ascii=False))
                            except Exception:
                                pass
                            async def _deferred_close(old_handler):
                                try:
                                    await asyncio.sleep(1.5)
                                    await old_handler.close(old_handler.websocket)
                                except Exception:
                                    pass
                            asyncio.create_task(_deferred_close(existed))
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"计划关闭旧连接失败(已忽略): {e}")
                        # 即使计划失败，也继续注册新连接
                self.device_handlers[device_id] = handler
            self.logger.bind(tag=TAG).info(f"注册设备路由: {device_id}")
            # 注册后广播一次在线快照
            await self.broadcast_server_stats()
            # 上线补投递：尝试取出离线队列并逐条发送
            try:
                pending, dropped = pop_offline_for_device(device_id)
                if pending:
                    # 统计按发起方聚合的补投条数
                    try:
                        from collections import defaultdict
                        sender_counts = defaultdict(int)
                    except Exception:
                        sender_counts = {}
                    sent = 0
                    for env in pending:
                        try:
                            if handler and handler.websocket:
                                await handler.websocket.send_json(env)
                            else:
                                import json
                                await handler.websocket.send(json.dumps(env, ensure_ascii=False))
                            sent += 1
                            # 聚合发起方统计
                            try:
                                origin = env.get("from")
                                if isinstance(origin, str) and len(origin) > 0:
                                    key = origin.strip().lower()
                                    if isinstance(sender_counts, dict):
                                        sender_counts[key] = sender_counts.get(key, 0) + 1
                                    else:
                                        sender_counts[key] += 1
                            except Exception:
                                pass
                        except AttributeError:
                            import json
                            await handler.websocket.send(json.dumps(env, ensure_ascii=False))
                            sent += 1
                        except Exception:
                            continue
                    self.logger.bind(tag=TAG).info(
                        f"离线补投递: device={device_id}, sent={sent}, dropped={dropped}"
                    )
                    # 给各发起方回执补投统计
                    try:
                        if isinstance(sender_counts, dict):
                            for origin_id, cnt in sender_counts.items():
                                try:
                                    origin_handler = self.device_handlers.get(origin_id)
                                    if origin_handler and origin_handler.websocket:
                                        payload = {
                                            "type": "peer",
                                            "event": "redelivered",
                                            "to": device_id,
                                            "count": int(cnt),
                                        }
                                        try:
                                            await origin_handler.websocket.send_json(payload)
                                        except AttributeError:
                                            import json
                                            await origin_handler.websocket.send(json.dumps(payload, ensure_ascii=False))
                                except Exception:
                                    continue
                    except Exception:
                        pass
            except Exception:
                pass
            # 上线即单播一次工作流快照（按分组），可通过开关/延迟避免测试噪声
            try:
                try:
                    group_key = str(device_id)[:8]
                except Exception:
                    group_key = "default"
                tasks = get_task_store().list_by_group(group_key)
                if tasks is not None:
                    # 读取测试模式与延迟配置
                    try:
                        wf_cfg = (self.config.get("workflow", {}) or {}) if isinstance(self.config, dict) else {}
                        test_mode = bool(wf_cfg.get("test_mode", False))
                        delay_ms = int(wf_cfg.get("snapshot_on_register_delay_ms", 0))
                    except Exception:
                        test_mode = False; delay_ms = 0
                    async def _send_snapshot():
                        envelope = {"type": "workflow", "event": "update", "tasks": tasks}
                        try:
                            await handler.websocket.send_json(envelope)
                        except AttributeError:
                            import json
                            await handler.websocket.send(json.dumps(envelope, ensure_ascii=False))
                        self.logger.bind(tag=TAG).info(f"[Workflow] op=snapshot source=register group={group_key} to={device_id} count={len(tasks)} test_mode={test_mode}")
                    if test_mode and delay_ms > 0:
                        async def _delayed_snapshot():
                            try:
                                await asyncio.sleep(delay_ms/1000.0)
                                await _send_snapshot()
                            except Exception:
                                pass
                        asyncio.create_task(_delayed_snapshot())
                    else:
                        await _send_snapshot()
            except Exception:
                pass
            return True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"注册设备路由失败 {device_id}: {e}")
            return False

    async def unregister_device_handler(self, device_id: str, handler: ConnectionHandler) -> None:
        """注销设备与连接处理器的映射"""
        try:
            async with self.device_handlers_lock:
                if self.device_handlers.get(device_id) is handler:
                    del self.device_handlers[device_id]
            self.logger.bind(tag=TAG).info(f"注销设备路由: {device_id}")
            # 注销后广播一次在线快照
            await self.broadcast_server_stats()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"注销设备路由失败 {device_id}: {e}")

    def get_device_handler(self, device_id: str) -> ConnectionHandler | None:
        """查询目标设备的连接处理器（只读，不加锁用于快速路径）"""
        return self.device_handlers.get(device_id)

    # 便捷查询方法
    def is_device_online(self, device_id: str) -> bool:
        """判断设备是否在线。"""
        return self.device_handlers.get(device_id) is not None

    def get_online_device_ids(self) -> list[str]:
        """获取当前在线设备列表（快照）。"""
        try:
            return list(self.device_handlers.keys())
        except Exception:
            return []

    async def get_online_device_ids_async(self) -> list[str]:
        """获取在线设备ID（加锁快照），避免与注册/注销竞态。"""
        try:
            async with self.device_handlers_lock:
                return list(self.device_handlers.keys())
        except Exception:
            return []

    def get_device_count(self) -> int:
        """在线设备数量。"""
        return len(self.device_handlers)

    def get_broadcast_targets(self, exclude_device_id: str | None = None) -> list[str]:
        """广播目标集合（可排除某个设备）。"""
        ids = self.get_online_device_ids()
        if exclude_device_id is None:
            return ids
        return [d for d in ids if d != exclude_device_id]

    async def get_broadcast_targets_async(self, exclude_device_id: str | None = None) -> list[str]:
        """广播目标集合（加锁）。"""
        ids = await self.get_online_device_ids_async()
        if exclude_device_id is None:
            return ids
        return [d for d in ids if d != exclude_device_id]

    def get_server_stats_json(self) -> dict:
        """构造服务器观测数据 JSON。"""
        stats = {
            "type": "server",
            "event": "stats",
            "ts": int(time.time() * 1000),
            "deviceCount": self.get_device_count(),
            "online": self.get_online_device_ids(),
        }
        try:
            import psutil  # 已在 requirements 中

            stats["cpuPercent"] = psutil.cpu_percent(interval=None)
            vm = psutil.virtual_memory()
            stats["memPercent"] = vm.percent
            stats["memUsedMB"] = int(vm.used / (1024 * 1024))
            stats["memTotalMB"] = int(vm.total / (1024 * 1024))
        except Exception:
            pass
        return stats

    async def broadcast_server_stats(self) -> None:
        """向所有在线连接广播服务端统计。"""
        try:
            payload = self.get_server_stats_json()
            for handler in list(self.device_handlers.values()):
                try:
                    if handler and handler.websocket:
                        await handler.websocket.send_json(payload)  # 优先使用 send_json
                except AttributeError:
                    # 兼容 websockets，使用字符串发送
                    import json

                    await handler.websocket.send(json.dumps(payload, ensure_ascii=False))
                except Exception:
                    continue
        except Exception:
            pass

    async def _periodic_stats_task(self) -> None:
        """周期广播服务端统计信息。"""
        try:
            while True:
                await asyncio.sleep(10)
                await self.broadcast_server_stats()
        except asyncio.CancelledError:
            return
        except Exception:
            return

```

```python
*** Begin Patch
*** Update File: /Users/tlovo/code_ai/Badge-ai/backend/core/connection.py
@@
-        # 线程任务相关
-        self.loop = asyncio.get_event_loop()
+        # 线程任务相关（在 handle_connection 内绑定运行中的事件循环）
+        self.loop = None
         self.stop_event = threading.Event()
@@
     async def handle_connection(self, ws, path=None):
         try:
+            # 绑定当前运行事件循环供跨线程调度使用
+            try:
+                self.loop = asyncio.get_running_loop()
+            except Exception:
+                self.loop = asyncio.get_event_loop()
@@
             self.logger.bind(tag=TAG).info(
                 f"{self.client_ip} conn - Headers: {self.headers}"
             )
@@
             self.welcome_msg = self.config["xiaozhi"]
             self.welcome_msg["session_id"] = self.session_id
-            await self.websocket.send(json.dumps(self.welcome_msg))
+            await self.send_json(self.welcome_msg)
@@
             self.timeout_task = asyncio.create_task(self._check_timeout())
*** End Patch
```

```python
import os
import sys
import copy
import json
import uuid
import time
import queue
import asyncio
import threading
import traceback
from config.logger import truncate_for_log
import subprocess
import websockets
from core.handle.mcpHandle import call_mcp_tool
from core.utils.util import (
    extract_json_from_string,
    check_vad_update,
    check_asr_update,
    filter_sensitive_info,
)
from typing import Dict, Any
from core.mcp.manager import MCPManager
from core.utils.modules_initialize import (
    initialize_modules,
    initialize_tts,
    initialize_asr,
)
from core.handle.reportHandle import report
from core.providers.tts.default import DefaultTTS
from concurrent.futures import ThreadPoolExecutor
from core.utils.dialogue import Message, Dialogue
from core.providers.asr.dto.dto import InterfaceType
from core.handle.textHandle import handleTextMessage
from core.handle.functionHandler import FunctionHandler
from plugins_func.loadplugins import auto_import_modules
from plugins_func.register import Action, ActionResponse
from core.auth import AuthMiddleware, AuthenticationError
from config.config_loader import get_private_config_from_api
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
from config.logger import setup_logging, build_module_string, update_module_string
from config.manage_api_client import DeviceNotFoundException, DeviceBindException


TAG = __name__

auto_import_modules("plugins_func.functions")


class TTSException(RuntimeError):
    pass


class ConnectionHandler:
    def __init__(
        self,
        config: Dict[str, Any],
        _vad,
        _asr,
        _llm,
        _memory,
        _intent,
        server=None,
    ):
        self.common_config = config
        self.config = copy.deepcopy(config)
        self.session_id = str(uuid.uuid4())
        self.logger = setup_logging()
        self.server = server  # 保存server实例的引用

        self.auth = AuthMiddleware(config)
        self.need_bind = False
        self.bind_code = None
        self.read_config_from_api = self.config.get("read_config_from_api", False)

        self.websocket = None
        self.headers = None
        self.device_id = None
        self.client_ip = None
        self.client_ip_info = {}
        self.prompt = None
        self.welcome_msg = None
        self.max_output_size = 0
        self.chat_history_conf = 0
        self.audio_format = "opus"

        # 客户端状态相关
        self.client_abort = False
        self.client_is_speaking = False
        self.client_listen_mode = "auto"

        # 线程任务相关
        self.loop = asyncio.get_event_loop()
        self.stop_event = threading.Event()
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

        # 添加上报线程池
        self.report_queue = queue.Queue()
        self.report_thread = None
        # 未来可以通过修改此处，调节asr的上报和tts的上报，目前默认都开启
        self.report_asr_enable = self.read_config_from_api
        self.report_tts_enable = self.read_config_from_api

        # 依赖的组件
        self.vad = None
        self.asr = None
        self.tts = None
        self._asr = _asr
        self._vad = _vad
        self.llm = _llm
        self.memory = _memory
        self.intent = _intent

        # vad相关变量
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0.0
        self.client_no_voice_last_time = 0.0
        self.client_voice_stop = False
        self.client_voice_frame_count = 0

        # asr相关变量
        # 因为实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR
        # 所以涉及到ASR的变量，需要在这里定义，属于connection的私有变量
        self.asr_audio = []
        self.asr_audio_queue = queue.Queue()

        # llm相关变量
        self.llm_finish_task = True
        self.dialogue = Dialogue()

        # tts相关变量
        self.sentence_id = None

        # iot相关变量
        self.iot_descriptors = {}
        self.func_handler = None

        # 模式状态（meeting/coding/working）
        self.current_mode = None
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
        # 编码模式日志流运行标志/阶段名（用于 stop/clear/phase 扩展）
        self.coding_stream_running = False
        self.coding_phase_name = ""

        self.cmd_exit = self.config["exit_commands"]
        self.max_cmd_length = 0
        for cmd in self.cmd_exit:
            if len(cmd) > self.max_cmd_length:
                self.max_cmd_length = len(cmd)

        # 是否在聊天结束后关闭连接
        self.close_after_chat = False
        self.load_function_plugin = False
        self.intent_type = "nointent"

        self.timeout_task = None
        # 放宽默认空闲阈值：默认 600s + 60s 兜底；允许配置覆盖
        try:
            base_idle = int(self.config.get("close_connection_no_voice_time", 600))
        except Exception:
            base_idle = 600
        self.timeout_seconds = base_idle + 60  # 第一层之外的兜底关闭

        # {"mcp":true} 表示启用MCP功能
        self.features = None

        # LLM 按模式实例缓存（随连接释放）
        self._llm_cache = {}

    def _get_base_config(self) -> Dict[str, Any]:
        try:
            srv = getattr(self, "server", None)
            base_cfg = getattr(srv, "config", None) if srv else None
            if isinstance(base_cfg, dict):
                return base_cfg
        except Exception:
            pass
        return self.config if isinstance(self.config, dict) else {}

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

        base_cfg = self._get_base_config()
        # 读取映射
        mapping = {}
        try:
            mapping = base_cfg.get("llm_by_mode", {}) or {}
        except Exception:
            mapping = {}

        mapping_val = mapping.get(key, None)
        if mapping_val is None:
            # 用途未配置专用 LLM，回退 default 并记录告警
            try:
                self.logger.bind(tag=TAG).warning(
                    f"get_llm_for: 未找到用途 {key} 的 llm_by_mode 配置，回退到 default"
                )
            except Exception:
                pass
            mapping_val = mapping.get("default")

        alias = None
        overrides = None
        if isinstance(mapping_val, dict):
            # 支持 { alias: xxx, overrides: { model_name: '...' } } 或直接平铺覆盖字段
            alias = mapping_val.get("alias") or mapping_val.get("name") or mapping_val.get("module") or mapping_val.get("llm")
            overrides = mapping_val.get("overrides")
            if overrides is None:
                # 将除别名键外的其余键视为覆盖
                tmp = dict(mapping_val)
                for k in ["alias", "name", "module", "llm", "overrides"]:
                    tmp.pop(k, None)
                overrides = tmp if len(tmp) > 0 else None
        elif isinstance(mapping_val, str) and len(mapping_val) > 0:
            alias = mapping_val

        # 回退默认 alias
        try:
            if alias is None:
                alias = self.config["selected_module"]["LLM"]
        except Exception:
            alias = None

        # 若无覆盖且别名等于当前默认，直接复用
        try:
            current_default_alias = self.config["selected_module"]["LLM"]
            if (overrides is None or len(overrides) == 0) and alias == current_default_alias and getattr(self, "llm", None) is not None:
                self._llm_cache[key] = self.llm
                return self.llm
        except Exception:
            pass

        # 构造/复用实例（合并覆盖）：优先使用 server 级共享注册表
        try:
            from core.utils import llm as llm_utils
            base_conf = None
            if alias:
                base_conf = copy.deepcopy(self.config.get("LLM", {}).get(alias))
                # 若连接级配置未包含该别名，尝试从服务器级配置读取（支持热更）
                if not base_conf:
                    try:
                        srv = getattr(self, "server", None)
                        srv_cfg = getattr(srv, "config", None) if srv else None
                        if isinstance(srv_cfg, dict):
                            base_conf = copy.deepcopy(srv_cfg.get("LLM", {}).get(alias))
                    except Exception:
                        pass
            if not base_conf:
                # 回退：无对应配置则复用默认，并给出一次告警
                try:
                    self.logger.bind(tag=TAG).warning(
                        f"get_llm_for: llm_by_mode[{key}] 别名未命中(alias={alias}), 回退默认LLM"
                    )
                except Exception:
                    pass
                self._llm_cache[key] = self.llm
                return self.llm
            # 若 server 提供共享注册表，优先复用
            try:
                srv = getattr(self, "server", None)
                if srv and hasattr(srv, "get_or_create_llm") and callable(getattr(srv, "get_or_create_llm")):
                    instance = srv.get_or_create_llm(alias, overrides)
                else:
                    # 直接合并覆盖并创建独立实例
                    if overrides and isinstance(overrides, dict):
                        for k, v in overrides.items():
                            base_conf[k] = v
                    llm_type = base_conf.get("type", alias)
                    instance = llm_utils.create_instance(llm_type, base_conf)
            except Exception:
                if overrides and isinstance(overrides, dict):
                    for k, v in overrides.items():
                        base_conf[k] = v
                llm_type = base_conf.get("type", alias)
                instance = llm_utils.create_instance(llm_type, base_conf)
            self._llm_cache[key] = instance
            return instance
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"get_llm_for 失败({key}): {e}，回退默认LLM")
            self._llm_cache[key] = self.llm
            return self.llm

    async def handle_connection(self, ws, path=None):
        try:
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
                self.headers = headers_lower
            except Exception:
                self.headers = {}

            # 优先从 URL 查询参数解析 device-id/client-id；其次尝试 Header；最后回退
            from urllib.parse import parse_qs, urlparse

            def _normalize_id(value: str | None) -> str | None:
                if value is None:
                    return None
                try:
                    v = str(value).strip().strip('"').strip("'")
                    if v == "":
                        return None
                    return v.lower()
                except Exception:
                    return None

            device_id_from_query = None
            client_id_from_query = None
            try:
                candidate_paths = []
                if isinstance(path, str) and len(path) > 0:
                    candidate_paths.append(path)
                ws_path = getattr(ws, "path", "")
                if isinstance(ws_path, str) and len(ws_path) > 0 and ws_path not in candidate_paths:
                    candidate_paths.append(ws_path)
                # 兼容不同版本 websockets 的属性命名，尽量获取带 query 的原始 URI
                for attr in ["request_uri", "raw_request_uri", "request_path", "raw_path"]:
                    try:
                        val = getattr(ws, attr, "")
                        if isinstance(val, str) and len(val) > 0 and val not in candidate_paths:
                            candidate_paths.append(val)
                    except Exception:
                        pass
                # 从候选 path 中解析 query 参数
                for p in candidate_paths:
                    try:
                        parsed_url = urlparse(p)
                        raw_query = parsed_url.query or ""
                        if not raw_query:
                            # 兼容某些环境仅传递了 "?a=b" 作为 path 的情况
                            if "?" in p and p.endswith("?") is False:
                                raw_query = p.split("?", 1)[1]
                        if not raw_query:
                            continue
                        query_params = parse_qs(raw_query, keep_blank_values=False)
                        device_vals = query_params.get("device-id") or query_params.get("device_id")
                        client_vals = query_params.get("client-id") or query_params.get("client_id")
                        if device_vals and len(device_vals) > 0:
                            device_id_from_query = _normalize_id(device_vals[0])
                            # client-id 缺省时复用 device-id
                            client_id_from_query = _normalize_id(client_vals[0]) if client_vals else device_id_from_query
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            # 兜底：从 server 的握手缓存读取（适配 websockets 传参差异）
            try:
                server_obj = getattr(self, "server", None)
                if (device_id_from_query is None) and server_obj is not None:
                    cache = getattr(server_obj, "_handshake_cache", None)
                    if isinstance(cache, dict):
                        # 按连接对象 id 存储
                        cached = cache.get(id(ws))
                        if isinstance(cached, dict):
                            did = cached.get("device-id")
                            cid = cached.get("client-id") or did
                            device_id_from_query = _normalize_id(did)
                            client_id_from_query = _normalize_id(cid)
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
                # 打印来源与解析快照（包含原始 path 片段便于定位异常客户端）
                try:
                    raw_paths_snapshot = []
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                        for attr in ["request_uri", "raw_request_uri", "request_path", "raw_path"]:
                            val = getattr(ws, attr, "")
                            if isinstance(val, str) and val:
                                raw_paths_snapshot.append(val[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    src = "query" if device_id_from_query else "header"
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={src}, rawPaths={truncate_for_log(str(raw_paths_snapshot))})"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={'query' if device_id_from_query else 'header'})"
                    )
            else:
                # 容错：仍未取到则自动分配，保证连接可用；同时输出诊断快照
                auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
                self.headers["device-id"] = auto_device_id
                self.headers["client-id"] = auto_device_id
                try:
                    raw_paths_snapshot = []
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    header_keys = list(self.headers.keys())
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}; rawPaths={truncate_for_log(str(raw_paths_snapshot))}, headerKeys={truncate_for_log(str(header_keys))}"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}"
                    )
            # 获取客户端ip地址
            try:
                remote = getattr(ws, "remote_address", None)
                if isinstance(remote, tuple) and len(remote) >= 1:
                    self.client_ip = remote[0]
                else:
                    self.client_ip = str(remote) if remote is not None else ""
            except Exception:
                self.client_ip = ""
            self.logger.bind(tag=TAG).info(
                f"{self.client_ip} conn - Headers: {self.headers}"
            )

            # 进行认证
            await self.auth.authenticate(self.headers)

            # 认证通过,继续处理
            self.websocket = ws
            self.device_id = self.headers.get("device-id", None)
            # 在 server 上注册设备路由（自动断开旧连接）
            if self.server and self.device_id:
                ok = await self.server.register_device_handler(self.device_id, self)
                if ok is False:
                    self.logger.bind(tag=TAG).error(f"设备注册失败: {self.device_id}")
                    await ws.send("设备注册失败")
                    await self.close(ws)
                    return

            # 启动超时检查任务
            self.timeout_task = asyncio.create_task(self._check_timeout())

            self.welcome_msg = self.config["xiaozhi"]
            self.welcome_msg["session_id"] = self.session_id
            await self.websocket.send(json.dumps(self.welcome_msg))

            # 获取差异化配置
            self._initialize_private_config()
            # 异步初始化
            self.executor.submit(self._initialize_components)

            try:
                async for message in self.websocket:
                    await self._route_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.bind(tag=TAG).info("客户端断开连接")

        except AuthenticationError as e:
            self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
            return
        except Exception as e:
            stack_trace = traceback.format_exc()
            try:
                safe_e = truncate_for_log(str(e))
                safe_tb = truncate_for_log(stack_trace)
            except Exception:
                safe_e = str(e)
                safe_tb = stack_trace
            self.logger.bind(tag=TAG).error(f"Connection error: {safe_e}-{safe_tb}")
            return
        finally:
            try:
                # 注销设备路由映射
                if self.server and self.device_id:
                    await self.server.unregister_device_handler(self.device_id, self)
            finally:
                await self._save_and_close(ws)

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

    def reset_timeout(self):
        """重置超时计时器"""
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
        self.timeout_task = asyncio.create_task(self._check_timeout())

    async def _route_message(self, message):
        """消息路由"""
        # 重置超时计时器
        self.reset_timeout()

        if isinstance(message, str):
            # 轻量 ping/keepalive：收到后仅重置计时器并忽略
            try:
                import json as _json
                try:
                    obj = _json.loads(message)
                except Exception:
                    obj = None
                if isinstance(obj, dict) and obj.get("type") in ("ping", "keepalive"):
                    try:
                        # 可选：立即回 pong
                        await self.websocket.send(_json.dumps({"type": "pong"}))
                    except Exception:
                        pass
                    return
            except Exception:
                pass
            await handleTextMessage(self, message)
        elif isinstance(message, bytes):
            if self.vad is None:
                return
            if self.asr is None:
                return
            self.asr_audio_queue.put(message)

    async def handle_restart(self, message):
        """处理服务器重启请求"""
        try:

            self.logger.bind(tag=TAG).info("收到服务器重启指令，准备执行...")

            # 发送确认响应
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "success",
                        "message": "服务器重启中...",
                        "content": {"action": "restart"},
                    }
                )
            )

            # 异步执行重启操作
            def restart_server():
                """实际执行重启的方法"""
                time.sleep(1)
                self.logger.bind(tag=TAG).info("执行服务器重启...")
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
                os._exit(0)

            # 使用线程执行重启避免阻塞事件循环
            threading.Thread(target=restart_server, daemon=True).start()

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"重启失败: {str(e)}")
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "error",
                        "message": f"Restart failed: {str(e)}",
                        "content": {"action": "restart"},
                    }
                )
            )

    def _initialize_components(self):
        try:
            self.selected_module_str = build_module_string(
                self.config.get("selected_module", {})
            )
            update_module_string(self.selected_module_str)
            """初始化组件"""
            if self.config.get("prompt") is not None:
                self.prompt = self.config["prompt"]
                self.change_system_prompt(self.prompt)
                self.logger.bind(tag=TAG).info(
                    f"初始化组件: prompt成功 {self.prompt[:50]}..."
                )

            """初始化本地组件"""
            if self.vad is None:
                self.vad = self._vad
            if self.asr is None:
                self.asr = self._initialize_asr()
            # 打开语音识别通道
            asyncio.run_coroutine_threadsafe(self.asr.open_audio_channels(self), self.loop)

            if self.tts is None:
                self.tts = self._initialize_tts()
            # 会议模式可禁用 TTS 通道（懒启动）
            disable_tts = False
            try:
                srv = getattr(self, "server", None)
                base_cfg = getattr(srv, "config", None) if srv else None
                if isinstance(base_cfg, dict):
                    meeting_cfg2 = base_cfg.get("meeting", {})
                else:
                    meeting_cfg2 = self.config.get("meeting", {})
                disable_tts = bool(meeting_cfg2.get("disable_tts", False))
            except Exception:
                disable_tts = False
            if not disable_tts:
                asyncio.run_coroutine_threadsafe(self.tts.open_audio_channels(self), self.loop)

            """加载记忆"""
            self._initialize_memory()
            """加载意图识别"""
            self._initialize_intent()
            """初始化上报线程"""
            self._init_report_threads()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"实例化组件失败: {e}")

    def _init_report_threads(self):
        """初始化ASR和TTS上报线程"""
        if not self.read_config_from_api or self.need_bind:
            return
        if self.chat_history_conf == 0:
            return
        if self.report_thread is None or not self.report_thread.is_alive():
            self.report_thread = threading.Thread(
                target=self._report_worker, daemon=True
            )
            self.report_thread.start()
            self.logger.bind(tag=TAG).info("TTS上报线程已启动")

    def _initialize_tts(self):
        """初始化TTS"""
        tts = None
        if not self.need_bind:
            tts = initialize_tts(self.config)

        if tts is None:
            tts = DefaultTTS(self.config, delete_audio_file=True)

        return tts

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

    def _initialize_private_config(self):
        """如果是从配置文件获取，则进行二次实例化"""
        if not self.read_config_from_api:
            return
        """从接口获取差异化的配置进行二次实例化，非全量重新实例化"""
        try:
            begin_time = time.time()
            private_config = get_private_config_from_api(
                self.config,
                self.headers.get("device-id"),
                self.headers.get("client-id", self.headers.get("device-id")),
            )
            private_config["delete_audio"] = bool(self.config.get("delete_audio", True))
            self.logger.bind(tag=TAG).info(
                f"{time.time() - begin_time} 秒，获取差异化配置成功: {json.dumps(filter_sensitive_info(private_config), ensure_ascii=False)}"
            )
        except DeviceNotFoundException as e:
            self.need_bind = True
            private_config = {}
        except DeviceBindException as e:
            self.need_bind = True
            self.bind_code = e.bind_code
            private_config = {}
        except Exception as e:
            self.need_bind = True
            self.logger.bind(tag=TAG).error(f"获取差异化配置失败: {e}")
            private_config = {}

        init_llm, init_tts, init_memory, init_intent = (
            False,
            False,
            False,
            False,
        )

        init_vad = check_vad_update(self.common_config, private_config)
        init_asr = check_asr_update(self.common_config, private_config)

        if init_vad:
            self.config["VAD"] = private_config["VAD"]
            self.config["selected_module"]["VAD"] = private_config["selected_module"][
                "VAD"
            ]
        if init_asr:
            self.config["ASR"] = private_config["ASR"]
            self.config["selected_module"]["ASR"] = private_config["selected_module"][
                "ASR"
            ]
        if private_config.get("TTS", None) is not None:
            init_tts = True
            self.config["TTS"] = private_config["TTS"]
            self.config["selected_module"]["TTS"] = private_config["selected_module"][
                "TTS"
            ]
        if private_config.get("LLM", None) is not None:
            init_llm = True
            self.config["LLM"] = private_config["LLM"]
            self.config["selected_module"]["LLM"] = private_config["selected_module"][
                "LLM"
            ]
        if private_config.get("Memory", None) is not None:
            init_memory = True
            self.config["Memory"] = private_config["Memory"]
            self.config["selected_module"]["Memory"] = private_config[
                "selected_module"
            ]["Memory"]
        if private_config.get("Intent", None) is not None:
            init_intent = True
            self.config["Intent"] = private_config["Intent"]
            model_intent = private_config.get("selected_module", {}).get("Intent", {})
            self.config["selected_module"]["Intent"] = model_intent
            # 加载插件配置
            if model_intent != "Intent_nointent":
                plugin_from_server = private_config.get("plugins", {})
                for plugin, config_str in plugin_from_server.items():
                    plugin_from_server[plugin] = json.loads(config_str)
                self.config["plugins"] = plugin_from_server
                self.config["Intent"][self.config["selected_module"]["Intent"]][
                    "functions"
                ] = plugin_from_server.keys()
        if private_config.get("prompt", None) is not None:
            self.config["prompt"] = private_config["prompt"]
        if private_config.get("summaryMemory", None) is not None:
            self.config["summaryMemory"] = private_config["summaryMemory"]
        if private_config.get("device_max_output_size", None) is not None:
            self.max_output_size = int(private_config["device_max_output_size"])
        if private_config.get("chat_history_conf", None) is not None:
            self.chat_history_conf = int(private_config["chat_history_conf"])
        try:
            modules = initialize_modules(
                self.logger,
                private_config,
                init_vad,
                init_asr,
                init_llm,
                init_tts,
                init_memory,
                init_intent,
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"初始化组件失败: {e}")
            modules = {}
        if modules.get("tts", None) is not None:
            self.tts = modules["tts"]
        if modules.get("vad", None) is not None:
            self.vad = modules["vad"]
        if modules.get("asr", None) is not None:
            self.asr = modules["asr"]
        if modules.get("llm", None) is not None:
            self.llm = modules["llm"]
        if modules.get("intent", None) is not None:
            self.intent = modules["intent"]
        if modules.get("memory", None) is not None:
            self.memory = modules["memory"]

    def _initialize_memory(self):
        if self.memory is None:
            return
        """初始化记忆模块"""
        # 按模式选择记忆总结 LLM（可被 llm_by_mode.memory 覆盖）
        chosen_llm = self.llm
        try:
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                selected = self.get_llm_for("memory")
                if selected is not None:
                    chosen_llm = selected
        except Exception:
            pass

        self.memory.init_memory(
            role_id=self.device_id,
            llm=chosen_llm,
            summary_memory=self.config.get("summaryMemory", None),
            save_to_file=not self.read_config_from_api,
        )

        # 获取记忆总结配置
        memory_config = self.config["Memory"]
        memory_type = self.config["Memory"][self.config["selected_module"]["Memory"]][
            "type"
        ]
        # 如果使用 nomen，直接返回
        if memory_type == "nomem":
            return
        # 使用 mem_local_short 模式
        elif memory_type == "mem_local_short":
            memory_llm_name = memory_config[self.config["selected_module"]["Memory"]][
                "llm"
            ]
            if memory_llm_name and memory_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                memory_llm_config = self.config["LLM"][memory_llm_name]
                memory_llm_type = memory_llm_config.get("type", memory_llm_name)
                memory_llm = llm_utils.create_instance(
                    memory_llm_type, memory_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为记忆总结创建了专用LLM: {memory_llm_name}, 类型: {memory_llm_type}"
                )
                self.memory.set_llm(memory_llm)
            else:
                # 否则使用主LLM
                self.memory.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

    def _initialize_intent(self):
        if self.intent is None:
            return
        self.intent_type = self.config["Intent"][
            self.config["selected_module"]["Intent"]
        ]["type"]
        if self.intent_type == "function_call" or self.intent_type == "intent_llm":
            self.load_function_plugin = True
        """初始化意图识别模块"""
        # 获取意图识别配置
        intent_config = self.config["Intent"]
        intent_type = self.config["Intent"][self.config["selected_module"]["Intent"]][
            "type"
        ]

        # 如果使用 nointent，直接返回
        if intent_type == "nointent":
            return
        # 使用 intent_llm 模式
        elif intent_type == "intent_llm":
            intent_llm_name = intent_config[self.config["selected_module"]["Intent"]][
                "llm"
            ]

            if intent_llm_name and intent_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                intent_llm_config = self.config["LLM"][intent_llm_name]
                intent_llm_type = intent_llm_config.get("type", intent_llm_name)
                intent_llm = llm_utils.create_instance(
                    intent_llm_type, intent_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为意图识别创建了专用LLM: {intent_llm_name}, 类型: {intent_llm_type}"
                )
                # 按模式选择意图识别 LLM（可被 llm_by_mode.intent 覆盖）
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(intent_llm)
                    else:
                        self.intent.set_llm(intent_llm)
                except Exception:
                    self.intent.set_llm(intent_llm)
            else:
                # 否则使用主LLM
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(self.llm)
                    else:
                        self.intent.set_llm(self.llm)
                except Exception:
                    self.intent.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

        """加载插件"""
        self.func_handler = FunctionHandler(self)
        self.mcp_manager = MCPManager(self)

        """加载MCP工具"""
        asyncio.run_coroutine_threadsafe(
            self.mcp_manager.initialize_servers(), self.loop
        )

    def change_system_prompt(self, prompt):
        self.prompt = prompt
        # 更新系统prompt至上下文
        self.dialogue.update_system_message(self.prompt)

    def chat(self, query, tool_call=False):
        try:
            safe_query = truncate_for_log(query)
        except Exception:
            safe_query = query
        self.logger.bind(tag=TAG).info(f"大模型收到用户消息: {safe_query}")
        self.llm_finish_task = False

        if not tool_call:
            self.dialogue.put(Message(role="user", content=query))

        # Define intent functions
        functions = None
        if self.intent_type == "function_call" and hasattr(self, "func_handler"):
            functions = self.func_handler.get_functions()
        if hasattr(self, "mcp_client"):
            mcp_tools = self.mcp_client.get_available_tools()
            if mcp_tools is not None and len(mcp_tools) > 0:
                if functions is None:
                    functions = []
                functions.extend(mcp_tools)
        response_message = []

        try:
            # 使用带记忆的对话
            memory_str = None
            if self.memory is not None:
                future = asyncio.run_coroutine_threadsafe(
                    self.memory.query_memory(query), self.loop
                )
                memory_str = future.result()

            self.sentence_id = str(uuid.uuid4().hex)


            # 按当前模式选择 LLM（默认chat；coding/working 切换对应别名）
            purpose = self.current_mode or "chat"
            active_llm = self.llm
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                try:
                    active_llm = self.get_llm_for(purpose) or self.llm
                except Exception:
                    active_llm = self.llm

            if self.intent_type == "function_call" and functions is not None:
                # 使用支持functions的streaming接口
                llm_responses = active_llm.response_with_functions(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                    functions=functions,
                )
            else:
                llm_responses = active_llm.response(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM 处理出错 {query}: {e}")
            return None

        # 处理流式响应
        tool_call_flag = False
        function_name = None
        function_id = None
        function_arguments = ""
        content_arguments = ""
        text_index = 0
        self.client_abort = False
        for response in llm_responses:
            if self.client_abort:
                break
            if self.intent_type == "function_call" and functions is not None:
                content, tools_call = response
                if "content" in response:
                    content = response["content"]
                    tools_call = None
                if content is not None and len(content) > 0:
                    content_arguments += content

                if not tool_call_flag and content_arguments.startswith("<tool_call>"):
                    # print("content_arguments", content_arguments)
                    tool_call_flag = True

                if tools_call is not None and len(tools_call) > 0:
                    tool_call_flag = True
                    if tools_call[0].id is not None:
                        function_id = tools_call[0].id
                    if tools_call[0].function.name is not None:
                        function_name = tools_call[0].function.name
                    if tools_call[0].function.arguments is not None:
                        function_arguments += tools_call[0].function.arguments
            else:
                content = response
            if content is not None and len(content) > 0:
                if not tool_call_flag:
                    response_message.append(content)
                    if text_index == 0:
                        self.tts.tts_text_queue.put(
                            TTSMessageDTO(
                                sentence_id=self.sentence_id,
                                sentence_type=SentenceType.FIRST,
                                content_type=ContentType.ACTION,
                            )
                        )
                    self.tts.tts_text_queue.put(
                        TTSMessageDTO(
                            sentence_id=self.sentence_id,
                            sentence_type=SentenceType.MIDDLE,
                            content_type=ContentType.TEXT,
                            content_detail=content,
                        )
                    )
                    text_index += 1
        # 处理function call
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
            if not bHasError:
                response_message.clear()
                self.logger.bind(tag=TAG).debug(
                    f"function_name={function_name}, function_id={function_id}, function_arguments={function_arguments}"
                )
                function_call_data = {
                    "name": function_name,
                    "id": function_id,
                    "arguments": function_arguments,
                }

                # 处理Server端MCP工具调用
                if self.mcp_manager.is_mcp_tool(function_name):
                    result = self._handle_mcp_tool_call(function_call_data)
                elif hasattr(self, "mcp_client") and self.mcp_client.has_tool(
                    function_name
                ):
                    # 如果是小智端MCP工具调用
                    self.logger.bind(tag=TAG).debug(
                        f"调用小智端MCP工具: {function_name}, 参数: {function_arguments}"
                    )
                    try:
                        result = asyncio.run_coroutine_threadsafe(
                            call_mcp_tool(
                                self, self.mcp_client, function_name, function_arguments
                            ),
                            self.loop,
                        ).result()
                        self.logger.bind(tag=TAG).debug(f"MCP工具调用结果: {result}")

                        resultJson = None
                        if isinstance(result, str):
                            try:
                                resultJson = json.loads(result)
                            except Exception as e:
                                self.logger.bind(tag=TAG).error(
                                    f"解析MCP工具返回结果失败: {e}"
                                )

                        # 视觉大模型不经过二次LLM处理
                        if (
                            resultJson is not None
                            and isinstance(resultJson, dict)
                            and "action" in resultJson
                        ):
                            result = ActionResponse(
                                action=Action[resultJson["action"]],
                                result=None,
                                response=resultJson.get("response", ""),
                            )
                        else:
                            result = ActionResponse(
                                action=Action.REQLLM, result=result, response=""
                            )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"MCP工具调用失败: {e}")
                        result = ActionResponse(
                            action=Action.REQLLM, result="MCP工具调用失败", response=""
                        )
                else:
                    # 处理系统函数
                    result = self.func_handler.handle_llm_function_call(
                        self, function_call_data
                    )
                self._handle_function_result(result, function_call_data)

        # 存储对话内容
        if len(response_message) > 0:
            self.dialogue.put(
                Message(role="assistant", content="".join(response_message))
            )
        if text_index > 0:
            self.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=self.sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )
        self.llm_finish_task = True
        self.logger.bind(tag=TAG).debug(
            json.dumps(self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False)
        )

        return True

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

            tool_result = asyncio.run_coroutine_threadsafe(
                self.mcp_manager.execute_tool(function_name, args_dict), self.loop
            ).result()
            # meta=None content=[TextContent(type='text', text='北京当前天气:\n温度: 21°C\n天气: 晴\n湿度: 6%\n风向: 西北 风\n风力等级: 5级', annotations=None)] isError=False
            content_text = ""
            if tool_result is not None and tool_result.content is not None:
                for content in tool_result.content:
                    content_type = content.type
                    if content_type == "text":
                        content_text = content.text
                    elif content_type == "image":
                        pass

            if len(content_text) > 0:
                return ActionResponse(
                    action=Action.REQLLM, result=content_text, response=""
                )

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP工具调用错误: {e}")
            return ActionResponse(
                action=Action.REQLLM, result="工具调用出错", response=""
            )

        return ActionResponse(action=Action.REQLLM, result="工具调用出错", response="")

    def _handle_function_result(self, result, function_call_data):
        if result.action == Action.RESPONSE:  # 直接回复前端
            text = result.response
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        elif result.action == Action.REQLLM:  # 调用函数后再请求llm生成回复
            text = result.result
            if text is not None and len(text) > 0:
                function_id = function_call_data["id"]
                function_name = function_call_data["name"]
                function_arguments = function_call_data["arguments"]
                self.dialogue.put(
                    Message(
                        role="assistant",
                        tool_calls=[
                            {
                                "id": function_id,
                                "function": {
                                    "arguments": function_arguments,
                                    "name": function_name,
                                },
                                "type": "function",
                                "index": 0,
                            }
                        ],
                    )
                )

                self.dialogue.put(
                    Message(
                        role="tool",
                        tool_call_id=(
                            str(uuid.uuid4()) if function_id is None else function_id
                        ),
                        content=text,
                    )
                )
                self.chat(text, tool_call=True)
        elif result.action == Action.NOTFOUND or result.action == Action.ERROR:
            text = result.result
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        else:
            pass

    def _report_worker(self):
        """聊天记录上报工作线程"""
        while not self.stop_event.is_set():
            try:
                # 从队列获取数据，设置超时以便定期检查停止事件
                item = self.report_queue.get(timeout=1)
                if item is None:  # 检测毒丸对象
                    break
                type, text, audio_data, report_time = item
                try:
                    # 检查线程池状态
                    if self.executor is None:
                        continue
                    # 提交任务到线程池
                    self.executor.submit(
                        self._process_report, type, text, audio_data, report_time
                    )
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"聊天记录上报线程异常: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"聊天记录上报工作线程异常: {e}")

        self.logger.bind(tag=TAG).info("聊天记录上报线程已退出")

    def _process_report(self, type, text, audio_data, report_time):
        """处理上报任务"""
        try:
            # 执行上报（传入二进制数据）
            report(self, type, text, audio_data, report_time)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"上报处理异常: {e}")
        finally:
            # 标记任务完成
            self.report_queue.task_done()

    def clearSpeakStatus(self):
        self.client_is_speaking = False
        self.logger.bind(tag=TAG).debug(f"清除服务端讲话状态")

    async def close(self, ws=None):
        """资源清理方法"""
        try:
            # 取消超时任务
            if self.timeout_task:
                self.timeout_task.cancel()
                self.timeout_task = None

            # 取消编码洞察定时任务
            try:
                if hasattr(self, "coding_insight_task") and self.coding_insight_task and not self.coding_insight_task.done():
                    self.coding_insight_task.cancel()
            except Exception:
                pass

            # 清理MCP资源
            if hasattr(self, "mcp_manager") and self.mcp_manager:
                await self.mcp_manager.cleanup_all()

            # 触发停止事件
            if self.stop_event:
                self.stop_event.set()

            # 清空任务队列
            self.clear_queues()

            # 关闭WebSocket连接
            if ws:
                await ws.close()
            elif self.websocket:
                await self.websocket.close()

            # 最后关闭线程池（避免阻塞）
            if self.executor:
                try:
                    # Python 3.9+ 支持 cancel_futures
                    self.executor.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    self.executor.shutdown(wait=False)
                self.executor = None

            # 清理 LLM 实例缓存
            try:
                if hasattr(self, "_llm_cache") and isinstance(self._llm_cache, dict):
                    self._llm_cache.clear()
            except Exception:
                pass

            # 关闭 asr/tts/llm 资源
            try:
                if hasattr(self, "asr") and hasattr(self.asr, "close") and callable(getattr(self.asr, "close")):
                    maybe_close = self.asr.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "tts") and hasattr(self.tts, "close") and callable(getattr(self.tts, "close")):
                    maybe_close = self.tts.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "llm") and hasattr(self.llm, "close") and callable(getattr(self.llm, "close")):
                    maybe_close = self.llm.close()  # 供应商可选实现
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass

            self.logger.bind(tag=TAG).info("连接资源已释放")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"关闭连接时出错: {e}")

    def clear_queues(self):
        """清空所有任务队列"""
        if self.tts:
            self.logger.bind(tag=TAG).debug(
                f"开始清理: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

            # 使用非阻塞方式清空队列
            for q in [
                self.tts.tts_text_queue,
                self.tts.tts_audio_queue,
                self.report_queue,
            ]:
                if not q:
                    continue
                while True:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break

            self.logger.bind(tag=TAG).debug(
                f"清理结束: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

    def reset_vad_states(self):
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0
        self.client_voice_stop = False
        self.logger.bind(tag=TAG).debug("VAD states reset.")

    async def send_text(self, text: str) -> None:
        """统一文本发送包装。"""
        try:
            if self.websocket:
                await self.websocket.send(text)
        except Exception:
            pass

    async def send_json(self, payload: dict) -> None:
        """统一 JSON 发送包装，自动兼容 send_json 缺失并回退字符串。"""
        try:
            if self.websocket is None:
                return
            try:
                await self.websocket.send_json(payload)
            except AttributeError:
                import json as _json
                await self.websocket.send(_json.dumps(payload, ensure_ascii=False))
        except Exception:
            # 发送错误不应中断主流程
            pass

    def chat_and_close(self, text):
        """Chat with the user and then close the connection"""
        try:
            # Use the existing chat method
            self.chat(text)

            # After chat is complete, close the connection
            self.close_after_chat = True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Chat and close error: {str(e)}")

    async def _check_timeout(self):
        """检查连接超时"""
        try:
            while not self.stop_event.is_set():
                await asyncio.sleep(self.timeout_seconds)
                if not self.stop_event.is_set():
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
                    if self.stop_event.is_set():
                        break
                    self.logger.bind(tag=TAG).info("连接超时，准备关闭")
                    await self.close(self.websocket)
                    break
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"超时检查任务出错: {e}")

```

```python
import asyncio
import time
import json
import websockets
import socket
from http import HTTPStatus
from config.logger import setup_logging
from core.connection import ConnectionHandler
from config.config_loader import get_config_from_api
from core.utils.modules_initialize import initialize_modules
from core.utils.tasks_store import get_task_store
from core.utils.util import check_vad_update, check_asr_update
from core.utils.offline_queue import pop_offline_for_device
from urllib.parse import urlparse, parse_qs

TAG = __name__


class WebSocketServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self.config_lock = asyncio.Lock()
        self._started_event: asyncio.Event = asyncio.Event()
        self.startup_error: Exception | None = None
        # 设备路由映射：device-id -> ConnectionHandler
        self.device_handlers = {}
        self.device_handlers_lock = asyncio.Lock()
        # 握手缓存：按连接对象 id 缓存原始 path 与解析到的 ids，供 handler 兜底读取
        self._handshake_cache: dict[int, dict] = {}
        modules = initialize_modules(
            self.logger,
            self.config,
            "VAD" in self.config["selected_module"],
            "ASR" in self.config["selected_module"],
            "LLM" in self.config["selected_module"],
            False,
            "Memory" in self.config["selected_module"],
            "Intent" in self.config["selected_module"],
        )
        self._vad = modules["vad"] if "vad" in modules else None
        self._asr = modules["asr"] if "asr" in modules else None
        self._llm = modules["llm"] if "llm" in modules else None
        self._intent = modules["intent"] if "intent" in modules else None
        self._memory = modules["memory"] if "memory" in modules else None

        self.active_connections = set()
        # LLM 单例注册表：key = alias + overrides 指纹
        self.llm_registry: dict[str, object] = {}

    def get_or_create_llm(self, alias: str, overrides: dict | None = None):
        """按别名与可选覆盖创建/复用共享 LLM 实例。

        key 规则：f"{alias}::" + json.dumps(overrides, sort_keys=True)（None 视为{}）。
        基础配置来源 self.config['LLM'][alias]，覆盖与类型解析后实例化。
        """
        try:
            import json as _json
            from core.utils import llm as llm_utils
        except Exception:
            raise
        if not isinstance(alias, str) or len(alias) == 0:
            return None
        ov = overrides or {}
        try:
            key = f"{alias}::{_json.dumps(ov, ensure_ascii=False, sort_keys=True)}"
        except Exception:
            # Fallback literal '{}'
            key = f"{alias}::" + "{}"
        # 命中共享实例
        if key in self.llm_registry:
            return self.llm_registry[key]
        # 构造配置
        base_conf = None
        try:
            base_conf = dict(self.config.get("LLM", {}).get(alias, {}))
        except Exception:
            base_conf = None
        if not base_conf:
            # 无法构造，返回 None
            return None
        if isinstance(ov, dict) and ov:
            try:
                for k, v in ov.items():
                    base_conf[k] = v
            except Exception:
                pass
        llm_type = base_conf.get("type", alias)
        instance = llm_utils.create_instance(llm_type, base_conf)
        self.llm_registry[key] = instance
        return instance

    async def start(self):
        # reset start state
        try:
            self._started_event.clear()
        except Exception:
            self._started_event = asyncio.Event()
        self.startup_error = None
        server_config = self.config.get("server", {}) or {}
        host = server_config.get("ip") or "0.0.0.0"
        # 端口健壮化解析
        raw_port = server_config.get("port", 8000)
        try:
            port = int(raw_port) if str(raw_port).strip() != "" else 8000
        except Exception:
            port = 8000

        # 预绑定检测：尽早暴露“端口被占用/权限不足”等问题
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
        except OSError as e:
            self.logger.bind(tag=TAG).error(
                f"WebSocketServer failed to bind preflight {host}:{port}: {e}. \n"
                f"可能原因：端口被占用/权限不足/host非法。请确认无旧进程占用端口或调整 server.port。"
            )
            self.startup_error = e
            self._started_event.set()
            # 直接抛出以让上层捕获（避免静默失败）
            raise

        # 真正启动 WS 服务
        try:
            async with websockets.serve(
                self._handle_connection,
                host,
                port,
                process_request=self._http_response,
                ping_interval=20,
                ping_timeout=50,
                close_timeout=5,
            ):
                # 启动时打印当前在线设备快照（通常为空），便于对照测试页
                online_ids = self.get_online_device_ids()
                self.logger.bind(tag=TAG).info(
                    f"WebSocketServer started on {host}:{port}, online_count={self.get_device_count()}, online={online_ids}; server.stats broadcasting enabled"
                )
                # 标记已启动
                try:
                    self._started_event.set()
                except Exception:
                    pass
                # 周期性广播服务端统计
                asyncio.create_task(self._periodic_stats_task())
                await asyncio.Future()
        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"WebSocketServer failed to start on {host}:{port}: {e}"
            )
            self.startup_error = e
            try:
                self._started_event.set()
            except Exception:
                pass
            raise

    async def wait_started(self) -> None:
        await self._started_event.wait()
        if self.startup_error is not None:
            raise self.startup_error

    async def _handle_connection(self, websocket, path=None):
        """处理新连接，每次创建独立的ConnectionHandler
        兼容 websockets 旧接口，接收 path 参数，传递给后续处理。
        """
        # 创建ConnectionHandler时传入当前server实例
        handler = ConnectionHandler(
            self.config,
            self._vad,
            self._asr,
            self._llm,
            self._memory,
            self._intent,
            self,  # 传入server实例
        )
        self.active_connections.add(handler)
        try:
            await handler.handle_connection(websocket, path)
        finally:
            self.active_connections.discard(handler)

    def _http_response(self, path, request_headers):
        """
        websockets 的 process_request 回调。
        - 返回 None 继续握手（WebSocket 升级）
        - 返回 (status, headers, body) 处理普通 HTTP 请求
        """
        try:
            # 诊断：记录升级请求的原始 path（含 query）与关键头部
            try:
                # websockets 不同版本下，这里的第一个参数可能是 str（带 query 的 path），也可能是连接对象
                raw_path_str = None
                conn_obj = None
                if isinstance(path, str):
                    raw_path_str = path
                else:
                    conn_obj = path
                    # 猜测属性链提取原始 path
                    for attr in ("path", "request_uri", "raw_request_uri", "request_path", "raw_path"):
                        try:
                            val = getattr(conn_obj, attr, None)
                            if isinstance(val, str) and val:
                                raw_path_str = val
                                break
                        except Exception:
                            continue
                    # 深一层：可能存在 request 对象
                    if raw_path_str is None:
                        try:
                            req = getattr(conn_obj, "request", None) or getattr(conn_obj, "_request", None)
                            if req is not None:
                                for attr in ("path", "target", "raw_path"):
                                    try:
                                        val = getattr(req, attr, None)
                                        if isinstance(val, str) and val:
                                            raw_path_str = val
                                            break
                                    except Exception:
                                        continue
                        except Exception:
                            pass

                self.logger.bind(tag=TAG).info(
                    f"HTTP upgrade request path={raw_path_str if raw_path_str is not None else path}"
                )

                # 将解析到的 device-id/client-id 暂存，供后续 handler 兜底读取
                try:
                    if raw_path_str and conn_obj is not None:
                        parsed = urlparse(raw_path_str)
                        qs = parse_qs(parsed.query or "")
                        device_vals = qs.get("device-id") or qs.get("device_id")
                        client_vals = qs.get("client-id") or qs.get("client_id")
                        if device_vals:
                            device_id = (device_vals[0] or "").strip().strip('"').strip("'").lower()
                            client_id = (client_vals[0] if client_vals else device_id)
                            client_id = (client_id or "").strip().strip('"').strip("'").lower()
                            self._handshake_cache[id(conn_obj)] = {
                                "raw_path": raw_path_str,
                                "device-id": device_id,
                                "client-id": client_id,
                            }
                except Exception:
                    pass
            except Exception:
                pass
            connection_header = (
                (request_headers.get("Connection", "") or request_headers.get("connection", ""))
                .strip()
                .lower()
            )
            upgrade_header = (
                (request_headers.get("Upgrade", "") or request_headers.get("upgrade", ""))
                .strip()
                .lower()
            )
            if "upgrade" in connection_header and upgrade_header == "websocket":
                return None
        except Exception:
            # 容错：如遇到异常，默认继续握手
            return None

        body = b"Server is running\n"
        headers = [("Content-Type", "text/plain"), ("Content-Length", str(len(body)))]
        return 200, headers, body

    async def update_config(self) -> bool:
        """更新服务器配置并重新初始化组件

        Returns:
            bool: 更新是否成功
        """
        try:
            async with self.config_lock:
                # 重新获取配置
                new_config = get_config_from_api(self.config)
                if new_config is None:
                    self.logger.bind(tag=TAG).error("获取新配置失败")
                    return False
                self.logger.bind(tag=TAG).info(f"获取新配置成功")
                # 检查 VAD 和 ASR 类型是否需要更新
                update_vad = check_vad_update(self.config, new_config)
                update_asr = check_asr_update(self.config, new_config)
                self.logger.bind(tag=TAG).info(
                    f"检查VAD和ASR类型是否需要更新: {update_vad} {update_asr}"
                )
                # 更新配置
                self.config = new_config
                # 重新初始化组件
                modules = initialize_modules(
                    self.logger,
                    new_config,
                    update_vad,
                    update_asr,
                    "LLM" in new_config["selected_module"],
                    False,
                    "Memory" in new_config["selected_module"],
                    "Intent" in new_config["selected_module"],
                )

                # 更新组件实例
                if "vad" in modules:
                    self._vad = modules["vad"]
                if "asr" in modules:
                    self._asr = modules["asr"]
                if "llm" in modules:
                    self._llm = modules["llm"]
                if "intent" in modules:
                    self._intent = modules["intent"]
                if "memory" in modules:
                    self._memory = modules["memory"]
                
                # 通知现有连接：清理用途LLM缓存，避免使用旧配置实例
                try:
                    for handler in list(self.active_connections):
                        try:
                            if hasattr(handler, "_llm_cache") and isinstance(handler._llm_cache, dict):
                                handler._llm_cache.clear()
                                # 同时清理 meeting 推送周期，使热更后的间隔在下一周期生效
                                if hasattr(handler, "meeting_push_interval_ms_current"):
                                    try:
                                        delattr(handler, "meeting_push_interval_ms_current")
                                    except Exception:
                                        pass
                        except Exception:
                            continue
                except Exception:
                    pass
                self.logger.bind(tag=TAG).info(f"更新配置任务执行完毕")
                return True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"更新服务器配置失败: {str(e)}")
            return False

    async def register_device_handler(self, device_id: str, handler: ConnectionHandler) -> bool:
        """注册设备与连接处理器的映射；若已存在同名设备，则断开旧连接并接受新连接。

        Returns:
            bool: True 注册成功；False 注册失败。
        """
        try:
            async with self.device_handlers_lock:
                existed = self.device_handlers.get(device_id)
                if existed is not None and existed is not handler:
                    self.logger.bind(tag=TAG).warning(
                        f"检测到重复连接，启用双通道过渡(≤2s)并接受新连接: device={device_id}"
                    )
                    # 双通道过渡：先提示旧连接，延迟 ~1.5s 再关闭，降低听写中断概率
                    try:
                        if existed.websocket:
                            try:
                                await existed.send_json({
                                    "type": "system",
                                    "message": "检测到新连接，当前通道将于约1.5秒后关闭以切换到新通道"
                                })
                            except Exception:
                                pass
                            async def _deferred_close(old_handler):
                                try:
                                    await asyncio.sleep(1.5)
                                    await old_handler.close(old_handler.websocket)
                                except Exception:
                                    pass
                            asyncio.create_task(_deferred_close(existed))
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"计划关闭旧连接失败(已忽略): {e}")
                        # 即使计划失败，也继续注册新连接
                self.device_handlers[device_id] = handler
            self.logger.bind(tag=TAG).info(f"注册设备路由: {device_id}")
            # 注册后广播一次在线快照
            await self.broadcast_server_stats()
            # 上线补投递：尝试取出离线队列并逐条发送
            try:
                pending, dropped = pop_offline_for_device(device_id)
                if pending:
                    # 统计按发起方聚合的补投条数
                    try:
                        from collections import defaultdict
                        sender_counts = defaultdict(int)
                    except Exception:
                        sender_counts = {}
                    sent = 0
                    for env in pending:
                        try:
                            if handler:
                                await handler.send_json(env)
                            sent += 1
                            # 聚合发起方统计
                            try:
                                origin = env.get("from")
                                if isinstance(origin, str) and len(origin) > 0:
                                    key = origin.strip().lower()
                                    if isinstance(sender_counts, dict):
                                        sender_counts[key] = sender_counts.get(key, 0) + 1
                                    else:
                                        sender_counts[key] += 1
                            except Exception:
                                pass
                        except AttributeError:
                            import json
                            await handler.send_json(env)
                            sent += 1
                        except Exception:
                            continue
                    self.logger.bind(tag=TAG).info(
                        f"离线补投递: device={device_id}, sent={sent}, dropped={dropped}"
                    )
                    # 给各发起方回执补投统计
                    try:
                        if isinstance(sender_counts, dict):
                            for origin_id, cnt in sender_counts.items():
                                try:
                                    origin_handler = self.device_handlers.get(origin_id)
                                    if origin_handler and origin_handler.websocket:
                                        payload = {
                                            "type": "peer",
                                            "event": "redelivered",
                                            "to": device_id,
                                            "count": int(cnt),
                                        }
                                        try:
                                            await origin_handler.send_json(payload)
                                        except Exception:
                                            continue
                                except Exception:
                                    continue
                    except Exception:
                        pass
            except Exception:
                pass
            # 上线即单播一次工作流快照（按分组），可通过开关/延迟避免测试噪声
            try:
                try:
                    group_key = str(device_id)[:8]
                except Exception:
                    group_key = "default"
                tasks = get_task_store().list_by_group(group_key)
                if tasks is not None:
                    # 读取测试模式与延迟配置
                    try:
                        wf_cfg = (self.config.get("workflow", {}) or {}) if isinstance(self.config, dict) else {}
                        test_mode = bool(wf_cfg.get("test_mode", False))
                        delay_ms = int(wf_cfg.get("snapshot_on_register_delay_ms", 0))
                    except Exception:
                        test_mode = False; delay_ms = 0
                    async def _send_snapshot():
                        envelope = {"type": "workflow", "event": "update", "tasks": tasks}
                        try:
                            await handler.send_json(envelope)
                        except Exception:
                            pass
                        self.logger.bind(tag=TAG).info(f"[Workflow] op=snapshot source=register group={group_key} to={device_id} count={len(tasks)} test_mode={test_mode}")
                    if test_mode and delay_ms > 0:
                        async def _delayed_snapshot():
                            try:
                                await asyncio.sleep(delay_ms/1000.0)
                                await _send_snapshot()
                            except Exception:
                                pass
                        asyncio.create_task(_delayed_snapshot())
                    else:
                        await _send_snapshot()
            except Exception:
                pass
            return True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"注册设备路由失败 {device_id}: {e}")
            return False

    async def unregister_device_handler(self, device_id: str, handler: ConnectionHandler) -> None:
        """注销设备与连接处理器的映射"""
        try:
            async with self.device_handlers_lock:
                if self.device_handlers.get(device_id) is handler:
                    del self.device_handlers[device_id]
            self.logger.bind(tag=TAG).info(f"注销设备路由: {device_id}")
            # 注销后广播一次在线快照
            await self.broadcast_server_stats()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"注销设备路由失败 {device_id}: {e}")

    def get_device_handler(self, device_id: str) -> ConnectionHandler | None:
        """查询目标设备的连接处理器（只读，不加锁用于快速路径）"""
        return self.device_handlers.get(device_id)

    # 便捷查询方法
    def is_device_online(self, device_id: str) -> bool:
        """判断设备是否在线。"""
        return self.device_handlers.get(device_id) is not None

    def get_online_device_ids(self) -> list[str]:
        """获取当前在线设备列表（快照）。"""
        try:
            return list(self.device_handlers.keys())
        except Exception:
            return []

    async def get_online_device_ids_async(self) -> list[str]:
        """获取在线设备ID（加锁快照），避免与注册/注销竞态。"""
        try:
            async with self.device_handlers_lock:
                return list(self.device_handlers.keys())
        except Exception:
            return []

    def get_device_count(self) -> int:
        """在线设备数量。"""
        return len(self.device_handlers)

    def get_broadcast_targets(self, exclude_device_id: str | None = None) -> list[str]:
        """广播目标集合（可排除某个设备）。"""
        ids = self.get_online_device_ids()
        if exclude_device_id is None:
            return ids
        return [d for d in ids if d != exclude_device_id]

    async def get_broadcast_targets_async(self, exclude_device_id: str | None = None) -> list[str]:
        """广播目标集合（加锁）。"""
        ids = await self.get_online_device_ids_async()
        if exclude_device_id is None:
            return ids
        return [d for d in ids if d != exclude_device_id]

    def get_server_stats_json(self) -> dict:
        """构造服务器观测数据 JSON。"""
        stats = {
            "type": "server",
            "event": "stats",
            "ts": int(time.time() * 1000),
            "deviceCount": self.get_device_count(),
            "online": self.get_online_device_ids(),
        }
        try:
            import psutil  # 已在 requirements 中

            stats["cpuPercent"] = psutil.cpu_percent(interval=None)
            vm = psutil.virtual_memory()
            stats["memPercent"] = vm.percent
            stats["memUsedMB"] = int(vm.used / (1024 * 1024))
            stats["memTotalMB"] = int(vm.total / (1024 * 1024))
        except Exception:
            pass
        return stats

    async def broadcast_server_stats(self) -> None:
        """向所有在线连接广播服务端统计。"""
        try:
            payload = self.get_server_stats_json()
            for handler in list(self.device_handlers.values()):
                try:
                    if handler:
                        await handler.send_json(payload)
                except Exception:
                    continue
        except Exception:
            pass

    async def _periodic_stats_task(self) -> None:
        """周期广播服务端统计信息。"""
        try:
            while True:
                await asyncio.sleep(10)
                await self.broadcast_server_stats()
        except asyncio.CancelledError:
            return
        except Exception:
            return

```

```python
import json
from core.handle.abortHandle import handleAbortMessage
from core.handle.helloHandle import handleHelloMessage
from core.handle.mcpHandle import handle_mcp_message
from core.handle.peerHandle import handle_peer_message
from core.handle.meeting_handle import handle_meeting_message
from core.handle.coding_handle import handle_coding_message
from core.handle.workflow_handle import handle_workflow_message
from core.utils.util import remove_punctuation_and_length, filter_sensitive_info
from core.handle.receiveAudioHandle import startToChat, handleAudioMessage
from core.handle.sendAudioHandle import send_stt_message, send_tts_message
from core.handle.iotHandle import handleIotDescriptors, handleIotStatus
from core.handle.reportHandle import enqueue_asr_report
import asyncio
import time
from core.handle.meeting_handle import finalize_meeting_and_send_summary

TAG = __name__


async def handleTextMessage(conn, message):
    """处理文本消息"""
    try:
        msg_json = json.loads(message)
        if isinstance(msg_json, int):
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message if isinstance(message, str) else str(message)
            conn.logger.bind(tag=TAG).info(f"收到文本消息：{safe_msg}")
            await conn.websocket.send(message)
            return
        if msg_json["type"] == "hello":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到hello消息：{safe_msg}")
            await handleHelloMessage(conn, msg_json)
        elif msg_json["type"] == "abort":
            conn.logger.bind(tag=TAG).info(f"收到abort消息：{message}")
            await handleAbortMessage(conn)
        elif msg_json["type"] == "listen":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到listen消息：{safe_msg}")
            if "mode" in msg_json:
                conn.client_listen_mode = msg_json["mode"]
                conn.logger.bind(tag=TAG).debug(
                    f"客户端拾音模式：{conn.client_listen_mode}"
                )
            if msg_json["state"] == "start":
                # 最小去抖：忽略距上次同类事件 <300ms 的重复 start
                try:
                    import time as _t
                    now_ms = int(_t.time() * 1000)
                    last_ms = int(getattr(conn, "_last_listen_start_ms", 0) or 0)
                    if now_ms - last_ms < 300:
                        return
                    conn._last_listen_start_ms = now_ms
                except Exception:
                    pass
                conn.client_have_voice = True
                conn.client_voice_stop = False
                # 记录设备侧边界最新时间，用于回退策略判断
                try:
                    import time as _t
                    conn._last_listen_event_ms = int(_t.time() * 1000)
                except Exception:
                    pass
            elif msg_json["state"] == "stop":
                # 最小去抖：忽略距上次同类事件 <300ms 的重复 stop
                try:
                    import time as _t
                    now_ms = int(_t.time() * 1000)
                    last_ms = int(getattr(conn, "_last_listen_stop_ms", 0) or 0)
                    if now_ms - last_ms < 300:
                        return
                    conn._last_listen_stop_ms = now_ms
                except Exception:
                    pass
                conn.client_have_voice = True
                conn.client_voice_stop = True
                try:
                    import time as _t
                    conn._last_listen_event_ms = int(_t.time() * 1000)
                except Exception:
                    pass
                # 新增：通知流式ASR“本段结束”，促使尽快产出最终结果
                try:
                    if getattr(conn, "asr", None) is not None and hasattr(conn.asr, "on_client_listen_stop"):
                        maybe = conn.asr.on_client_listen_stop(conn)
                        if asyncio.iscoroutine(maybe):
                            await maybe
                except Exception:
                    pass
                if len(conn.asr_audio) > 0:
                    await handleAudioMessage(conn, b"")
            elif msg_json["state"] == "detect":
                conn.client_have_voice = False
                conn.asr_audio.clear()
                if "text" in msg_json:
                    original_text = msg_json["text"]  # 保留原始文本
                    filtered_len, filtered_text = remove_punctuation_and_length(
                        original_text
                    )

                    # 模式切换（进入工作模式）意图识别与回显/播报抑制
                    try:
                        normalized = str(original_text or "").strip().lower()
                        mode_switch_keywords = [
                            "进入工作模式",
                            "工作模式",
                            "切到工作模式",
                            "切换到工作模式",
                            "workflow mode",
                            "working mode",
                            "switch to working mode",
                            "enter working mode",
                        ]
                        if any(k.lower() in normalized for k in mode_switch_keywords):
                            # 下发带意图标注的 STT（不触发 TTS），并仅发送模式确认
                            try:
                                await conn.websocket.send(
                                    json.dumps(
                                        {
                                            "type": "stt",
                                            "text": original_text,
                                            "intent": "mode_switch",
                                            "target_mode": "working",
                                            "session_id": getattr(conn, "session_id", ""),
                                        },
                                        ensure_ascii=False,
                                    )
                                )
                            except Exception:
                                pass
                            # 复用现有 mode 流程，设置工作模式并触发一次快照单播
                            try:
                                await handleTextMessage(
                                    conn,
                                    json.dumps(
                                        {
                                            "type": "mode",
                                            "state": "start",
                                            "mode": "working",
                                        },
                                        ensure_ascii=False,
                                    ),
                                )
                            except Exception:
                                pass
                            return
                    except Exception:
                        pass

                    # 识别是否是唤醒词
                    is_wakeup_words = filtered_text in conn.config.get("wakeup_words")
                    # 是否开启唤醒词回复
                    enable_greeting = conn.config.get("enable_greeting", True)

                    if is_wakeup_words and not enable_greeting:
                        # 如果是唤醒词，且关闭了唤醒词回复，就不用回答
                        await send_stt_message(conn, original_text)
                        await send_tts_message(conn, "stop", None)
                        conn.client_is_speaking = False
                    elif is_wakeup_words:
                        conn.just_woken_up = True
                        # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）
                        enqueue_asr_report(conn, "嘿，你好呀", [])
                        await startToChat(conn, "嘿，你好呀")
                    else:
                        # 语音指令直达（工作模式）：assign/complete/refresh
                        try:
                            normalized = str(original_text or "").strip().lower()
                            # 仅在工作模式才进行直达解析
                            if getattr(conn, "current_mode", None) == "working":
                                assign_kw = ["认领任务", "领取任务", "我来做", "assign to me", "claim task"]
                                complete_kw = ["完成任务", "标记完成", "做完了", "mark done", "complete task"]
                                refresh_kw = ["刷新列表", "刷新任务", "拉取任务", "refresh", "pull", "update list"]
                                intent = None
                                if any(k.lower() in normalized for k in assign_kw):
                                    intent = "assign"
                                elif any(k.lower() in normalized for k in complete_kw):
                                    intent = "complete"
                                elif any(k.lower() in normalized for k in refresh_kw):
                                    intent = "refresh"
                                if intent is not None:
                                    # 可选：回包一个轻量意图（无 TTS 回显）
                                    try:
                                        await conn.websocket.send(json.dumps({
                                            "type": "workflow",
                                            "event": "command",
                                            "intent": intent,
                                        }, ensure_ascii=False))
                                    except Exception:
                                        pass
                                    # 具体执行
                                    from core.utils.tasks_store import get_task_store
                                    store = get_task_store()
                                    group_key = (getattr(conn, "device_id", "") or "")[:8]
                                    # 在没有任务时，避免空数组频发：拉取一次并返回
                                    if intent == "refresh":
                                        tasks = store.list_by_group(group_key)
                                        envelope = {"type": "workflow", "event": "update", "tasks": tasks}
                                        try:
                                            await conn.websocket.send_json(envelope)
                                        except AttributeError:
                                            await conn.websocket.send(json.dumps(envelope, ensure_ascii=False))
                                        return
                                    # 认领/完成：取最近一个可操作任务（open，owner为空/非我）
                                    tasks = store.list_by_group(group_key) or []
                                    target_id = None
                                    if intent == "assign":
                                        for t in tasks:
                                            if t.get("status") == "open" and (not t.get("owner") or t.get("owner") != getattr(conn, "device_id", None)):
                                                target_id = t.get("id")
                                                break
                                        if target_id is None and tasks:
                                            target_id = tasks[0].get("id")
                                        if target_id:
                                            # 构造 assign 消息并复用 handler（含幂等返回）
                                            await handle_workflow_message(conn, {"type": "workflow", "event": "assign", "id": target_id})
                                            return
                                    elif intent == "complete":
                                        for t in tasks:
                                            if t.get("status") == "open":
                                                target_id = t.get("id")
                                                break
                                        if target_id:
                                            await handle_workflow_message(conn, {"type": "workflow", "event": "complete", "ids": [target_id]})
                                            return
                        except Exception:
                            pass
                        # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）；默认走常规对话
                        enqueue_asr_report(conn, original_text, [])
                        await startToChat(conn, original_text)
        elif msg_json["type"] == "iot":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到iot消息：{safe_msg}")
            if "descriptors" in msg_json:
                asyncio.create_task(handleIotDescriptors(conn, msg_json["descriptors"]))
            if "states" in msg_json:
                asyncio.create_task(handleIotStatus(conn, msg_json["states"]))
        elif msg_json["type"] == "mcp":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到mcp消息：{safe_msg}")
            if "payload" in msg_json:
                asyncio.create_task(
                    handle_mcp_message(conn, conn.mcp_client, msg_json["payload"])
                )
        elif msg_json["type"] == "meeting":
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到meeting消息：{safe_detail}")
            if msg_json.get("phase") == "finalize":
                # W1: 立即回执 + 立即停止定时器（双保险）并打印三段连续日志
                try:
                    conn.logger.bind(tag=TAG).info("finalize request")
                    ack_started_at = int(getattr(conn, "meeting_start_ts", 0) or 0)
                    pending_count = len(getattr(conn, "meeting_pending_texts", []) or [])
                    await conn.websocket.send(
                        json.dumps({
                            "type": "meeting",
                            "phase": "finalize",
                            "sessionId": getattr(conn, "session_id", ""),
                            "startedAt": ack_started_at,
                            "pendingCount": pending_count,
                        }, ensure_ascii=False)
                    )
                    conn.logger.bind(tag=TAG).info("send ack")
                except Exception:
                    pass
                # 标记 finalize 中，停止会中定时任务与推送，避免“结束中仍在增加片段”
                try:
                    setattr(conn, "meeting_finalizing", True)
                except Exception:
                    pass
                try:
                    from core.handle.meeting_handle import stop_meeting_timers
                    stop_meeting_timers(conn)
                    conn.logger.bind(tag=TAG).info("stop timers done")
                except Exception:
                    conn.logger.bind(tag=TAG).warning("stop timers encountered error (ignored)")
                # 关闭/重置 ASR 流式连接，避免下次会议复用陈旧状态
                try:
                    if getattr(conn, "asr", None) is not None:
                        if hasattr(conn.asr, "stop_ws_connection"):
                            conn.asr.stop_ws_connection()
                        # 如实现了异步 close，则后台触发
                        import inspect
                        if hasattr(conn.asr, "close") and inspect.iscoroutinefunction(conn.asr.close):
                            asyncio.create_task(conn.asr.close())
                except Exception:
                    pass
                # 异步生成并下发最终纪要
                asyncio.create_task(finalize_meeting_and_send_summary(conn))
            else:
                asyncio.create_task(handle_meeting_message(conn, msg_json))
        elif msg_json["type"] == "coding":
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到coding消息：{safe_detail}")
            asyncio.create_task(handle_coding_message(conn, msg_json))
        elif msg_json["type"] == "workflow":
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到workflow消息：{safe_detail}")
            asyncio.create_task(handle_workflow_message(conn, msg_json))
        elif msg_json["type"] == "config_update":
            # 兼容旧式 config_update：仅提示并忽略（避免“未知类型”噪声）
            try:
                cfg_keys = list((msg_json.get("config") or {}).keys())
                conn.logger.bind(tag=TAG).info(f"收到兼容 config_update（忽略实际更新）：keys={cfg_keys}")
            except Exception:
                conn.logger.bind(tag=TAG).info("收到兼容 config_update（忽略实际更新）")
            try:
                await conn.websocket.send(json.dumps({"type": "config_update", "status": "ok", "noop": True}))
            except Exception:
                pass
        elif msg_json["type"] == "mode":
            # 模式切换骨架：start/end + mode
            conn.logger.bind(tag=TAG).info(f"收到mode消息：{message}")
            try:
                state = msg_json.get("state")
                mode = msg_json.get("mode")
                if state in ["start", "end"] and mode in ["meeting", "coding", "working"]:
                    # 仅更新会话级状态（后续根据 mode 影响处理策略）
                    if state == "start":
                        # 幂等：若已处于该模式则直接回执并跳过重复初始化
                        if getattr(conn, "current_mode", None) == mode:
                            try:
                                await conn.websocket.send(json.dumps({"type":"mode","status":"ok","state":"start","mode":mode}))
                            except Exception:
                                pass
                            return
                        conn.current_mode = mode
                        if mode == "meeting":
                            conn.meeting_segments.clear()
                            conn.meeting_start_ts = time.time() * 1000
                            conn.meeting_last_snippet_ts = 0.0
                            conn.meeting_last_snippet_index = 0
                            # 播放进入会议提示音（后端下发TTS音频 or 控制端提示）
                            try:
                                await conn.websocket.send(
                                    json.dumps({
                                        "type": "tts",
                                        "state": "start",
                                        "url": "config/assets/evening.wav",
                                        "text": "已进入会议模式"
                                    }, ensure_ascii=False)
                                )
                                # 立即发送 stop 以最小化占用（客户端可按需播放本地资源）
                                await conn.websocket.send(
                                    json.dumps({
                                        "type": "tts",
                                        "state": "stop"
                                    }, ensure_ascii=False)
                                )
                            except Exception:
                                pass
                            # 会议模式优先设备侧VAD（可选）
                            try:
                                srv = getattr(conn, "server", None)
                                base_cfg = getattr(srv, "config", None) if srv else None
                                if isinstance(base_cfg, dict):
                                    meeting_cfg = base_cfg.get("meeting", {})
                                else:
                                    meeting_cfg = conn.config.get("meeting", {})
                            except Exception:
                                meeting_cfg = conn.config.get("meeting", {})
                            if bool(meeting_cfg.get("prefer_device_vad", True)):
                                conn.client_listen_mode = "manual"
                                conn.logger.bind(tag=TAG).info("会议模式已启用设备侧VAD优先（listen start/stop 括起语音段）")
                            # 尝试加载活跃会中状态，实现断线续传
                            try:
                                from core.handle.meeting_handle import load_active_state_if_any, start_meeting_checkpoint_timer, start_meeting_timers
                                await load_active_state_if_any(conn)
                                # 启动会议相关定时任务（transcript 聚合 + checkpoint）
                                start_meeting_timers(conn)
                                start_meeting_checkpoint_timer(conn)
                            except Exception:
                                pass
                        elif mode == "working":
                            # 任务1-1：进入工作模式后显式开启拾音（manual），确保设备处于可听状态
                            try:
                                # 更新连接侧拾音模式与最近边界时间
                                conn.client_listen_mode = "manual"
                                try:
                                    import time as _t
                                    conn._last_listen_event_ms = int(_t.time() * 1000)
                                except Exception:
                                    pass
                                await conn.websocket.send(
                                    json.dumps(
                                        {
                                            "type": "listen",
                                            "state": "start",
                                            "mode": "manual",
                                        },
                                        ensure_ascii=False,
                                    )
                                )
                            except Exception:
                                pass
                    else:
                        conn.current_mode = None
                        # 退出会议模式时恢复自动拾音
                        if mode == "meeting":
                            conn.client_listen_mode = "auto"
                        if mode == "meeting":
                            # 退出 meeting 等价 finalize：立即回执确认并停止推送（同样打印三段日志）
                            try:
                                conn.logger.bind(tag=TAG).info("finalize request")
                                ack_started_at = int(getattr(conn, "meeting_start_ts", 0) or 0)
                                pending_count = len(getattr(conn, "meeting_pending_texts", []) or [])
                                await conn.websocket.send(json.dumps({
                                    "type": "meeting",
                                    "phase": "finalize",
                                    "sessionId": getattr(conn, "session_id", ""),
                                    "startedAt": ack_started_at,
                                    "pendingCount": pending_count,
                                }, ensure_ascii=False))
                                conn.logger.bind(tag=TAG).info("send ack")
                            except Exception:
                                pass
                            try:
                                setattr(conn, "meeting_finalizing", True)
                            except Exception:
                                pass
                            try:
                                from core.handle.meeting_handle import stop_meeting_timers
                                stop_meeting_timers(conn)
                                conn.logger.bind(tag=TAG).info("stop timers done")
                            except Exception:
                                conn.logger.bind(tag=TAG).warning("stop timers encountered error (ignored)")
                            # 关闭/重置 ASR 流式连接，避免下次会议复用陈旧状态
                            try:
                                if getattr(conn, "asr", None) is not None:
                                    if hasattr(conn.asr, "stop_ws_connection"):
                                        conn.asr.stop_ws_connection()
                                    import inspect
                                    if hasattr(conn.asr, "close") and inspect.iscoroutinefunction(conn.asr.close):
                                        asyncio.create_task(conn.asr.close())
                            except Exception:
                                pass
                            asyncio.create_task(finalize_meeting_and_send_summary(conn))
                    # 任务1：进入工作模式时单播一次分组任务快照
                    try:
                        if state == "start" and mode == "working":
                            # 去抖：避免与注册/hello触发的快照在极短时间内重复
                            import time as _t
                            now_ms = int(_t.time() * 1000)
                            last_ms = int(getattr(conn, "_last_workflow_snapshot_ms", 0) or 0)
                            if now_ms - last_ms >= 1500:
                                group_key = (getattr(conn, "device_id", "") or "")[:8]
                                if group_key:
                                    from core.utils.tasks_store import get_task_store
                                    tasks = get_task_store().list_by_group(group_key)
                                    envelope = {"type": "workflow", "event": "update", "tasks": tasks}
                                    try:
                                        await conn.websocket.send_json(envelope)
                                    except AttributeError:
                                        await conn.websocket.send(json.dumps(envelope, ensure_ascii=False))
                                    conn._last_workflow_snapshot_ms = now_ms
                                    conn.logger.bind(tag=TAG).info(f"[Workflow] op=snapshot source=mode_start group={group_key} to={getattr(conn,'device_id','')} count={len(tasks)}")
                    except Exception:
                        pass
                else:
                    await conn.websocket.send(
                        json.dumps({
                            "type": "mode",
                            "status": "error",
                            "message": "invalid state or mode"
                        })
                    )
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"处理mode消息异常: {e}")
        
        elif msg_json["type"] == "peer":
            # 板间通信骨架：仅校验并入队，后续由AI中转路由处理
            conn.logger.bind(tag=TAG).info(f"收到peer消息：{filter_sensitive_info(msg_json)}")
            try:
                to_list = msg_json.get("to", [])
                payload = msg_json.get("payload", {})
                if not isinstance(to_list, list) or not isinstance(payload, dict):
                    await conn.websocket.send(
                        json.dumps({"type": "peer", "status": "error", "message": "invalid to/payload"})
                    )
                    return
                # 调用AI中转路由（串行以保证顺序；如需提升吞吐可放线程池）
                await handle_peer_message(conn, to_list, payload)
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"处理peer消息异常: {e}")
        elif msg_json["type"] == "server":
            # 记录日志时过滤敏感信息
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到服务器消息：{safe_detail}")
            # 如果配置是从API读取的，则需要验证secret
            if not conn.read_config_from_api:
                return
            # 获取post请求的secret
            post_secret = msg_json.get("content", {}).get("secret", "")
            secret = conn.config["manager-api"].get("secret", "")
            # 如果secret不匹配，则返回
            if post_secret != secret:
                await conn.websocket.send(
                    json.dumps(
                        {
                            "type": "server",
                            "status": "error",
                            "message": "服务器密钥验证失败",
                        }
                    )
                )
                return
            # 动态更新配置
            if msg_json["action"] == "update_config":
                try:
                    # 更新WebSocketServer的配置
                    if not conn.server:
                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "server",
                                    "status": "error",
                                    "message": "无法获取服务器实例",
                                    "content": {"action": "update_config"},
                                }
                            )
                        )
                        return

                    if not await conn.server.update_config():
                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "server",
                                    "status": "error",
                                    "message": "更新服务器配置失败",
                                    "content": {"action": "update_config"},
                                }
                            )
                        )
                        return

                    # 发送成功响应
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "server",
                                "status": "success",
                                "message": "配置更新成功",
                                "content": {"action": "update_config"},
                            }
                        )
                    )
                except Exception as e:
                    conn.logger.bind(tag=TAG).error(f"更新配置失败: {str(e)}")
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "server",
                                "status": "error",
                                "message": f"更新配置失败: {str(e)}",
                                "content": {"action": "update_config"},
                            }
                        )
                    )
            # 重启服务器
            elif msg_json["action"] == "restart":
                await conn.handle_restart(msg_json)
        else:
            conn.logger.bind(tag=TAG).error(f"收到未知类型消息：{message}")
    except json.JSONDecodeError:
        await conn.websocket.send(message)

```

我刚完成了 P0 的代码 edits：修复了延时快照的调度、在连接协程内绑定事件循环、增加并应用统一发送封装、移除了重复心跳处理。现在我会检查是否有语法/风格问题，并读取 `log-w.md` 的末尾看日志格式，然后按“编辑84 by w”追加一条记录。

```markdown
## 协同工作日志记录

## 后端log

8.11

### 编辑内容1（后端新增）
- 核心能力接入与协议扩展：设备路由映射、模式状态管理、AI 中转路由（Peer Messaging，经 AI 结构化后再分发）。
- 日志 IP 可配置化：支持以配置覆盖自动探测 IP 的展示。

### 编辑人
- w

### 新增内容
- 设备路由映射（Device Router）
  - 文件：`backend/core/websocket_server.py`
  - 功能：维护 `device-id -> ConnectionHandler` 映射；提供 `register_device_handler`、`unregister_device_handler`、`get_device_handler`。
  - 关联：`backend/core/connection.py` 在连接建立/关闭时自动注册/注销路由。

- 模式状态管理（Mode State）
  - 文件：`backend/core/connection.py`、`backend/core/handle/textHandle.py`
  - 功能：新增会话字段 `current_mode`；新增 `type:"mode"` 处理（`start|end` + `meeting|coding|working`），回执 `status:"ok"`。

- AI 中转路由（AI Relay，用于设备间通信）
  - 文件：`backend/core/handle/peerHandle.py`、`backend/core/handle/textHandle.py`
  - 功能：
    - 入口：`type:"peer"`（字段：`to`、`payload.text/context`）。
    - 过程：系统提示词 → 调用 `conn.llm.response` 结构化 → 严格 Schema 校验与纠正 → 路由分发（单播/广播）→ 发起方回执（`delivered/failed/summary`）。
    - 错误码：`INVALID_REQUEST`、`LLM_OUTPUT_NOT_JSON`、`SCHEMA_INVALID`、`INTERNAL_ERROR`。
    - 广播：`to:["broadcast"]` 会向所有在线且非发起方设备分发。

- 日志对外地址可配置
  - 文件：`backend/app.py`
  - 功能：新增读取 `server.advertise_ip` 用于日志展示的 IP；若配置了完整 `server.websocket`，日志优先展示该 URL。

### 已知缺陷 / 风险
- LLM 配置不当会导致 AI 中转失败
  - 现象：日志报 404（`Invalid URL (POST /v1/models/chat/completions)`）或 `LLM_OUTPUT_NOT_JSON`。
  - 原因：`LLM.gptLLM` 使用了 `url:` 且指向 `/v1/models`，适配器预期为 `base_url: https://api.openai.com/v1`。
  - 处理：在 `backend/data/.config.yaml` 修复为：
    ```yaml
    LLM:
      gptLLM:
        type: openai
        model_name: gpt-4.1-nano
        base_url: https://api.openai.com/v1
        api_key: <your_key>
    ```

- 权限与风控尚未实现
  - 未对 `peer` 进行白名单/频率限制；无目标在线前置校验；需补充审计日志细粒度错误码（非致命，后续补齐）。

- 工作流/会议/编码的端到端闭环未完成
  - `category:"task"` 暂未持久化为任务清单，未触发 `workflow.update` 推送；
  - 会议纪要（转写缓存/节流/总结下发）未落地；
  - 编码模式日志流（`coding.log/step`）未落地；
  - 硬件端 `type:"peer"` 的 UI 渲染未接入，需要在 `Application::OnIncomingJson` 增加分支并映射页面。

- 测试与工具链
  - 缺少单元测试/回归脚本（`peer` 正常/异常、广播、Schema 边界、离线分发）；
  - 浏览器环境可能受 CSP 限制连接外部 WS，需使用本地 `file://` HTML 或工具（Postman/WsCat）。

### 待验证内容（建议用本地 HTML 模拟两台设备）
- 连接（两端）
  - `ws://<ip>:8004/supie/v1/?device-id=001&client-id=001`
  - `ws://<ip>:8004/supie/v1/?device-id=002&client-id=002`

- 模式状态
  - 发送：`{"type":"mode","state":"start","mode":"working"}`；
  - 预期：回执 `{"type":"mode","status":"ok",...}`。

- peer 单播（001→002）
  - 发送：`{"type":"peer","to":["002"],"payload":{"text":"请明早10点前完成登录模块联调，优先级1","context":{"locale":"zh-CN"}}}`；
  - 预期：002 收到结构化 `peer`；001 收到回执 `{status:"done", delivered:["002"], failed:[], summary:{...}}`。

- peer 广播（001→all）
  - 发送：`{"type":"peer","to":["broadcast"],"payload":{"text":"下午4点同步周会纪要"}}`；
  - 预期：在线且非发起方连接均收到；回执包含 `delivered/failed` 列表。

- 错误路径
  - 发送空文本：预期回执 `status:"error"` 且 `code` 为 `INVALID_REQUEST | LLM_OUTPUT_NOT_JSON | SCHEMA_INVALID`。

- 日志地址
  - 配置 `server.advertise_ip: <lan-ip>` 与 `server.websocket: ws://<lan-ip>:<port>/supie/v1/`；
  - 重启后核对三行地址是否一致为局域网 IP。

### 影响范围与回滚
- 改动集中于后端会话/消息处理与日志展示；未修改 ASR/TTS/硬件协议层；回滚可按文件逐项还原。


### 编辑内容2（后端新增）
- 三个模式处理器骨架与分发注册：新增 `meeting/coding/workflow` 的 handler（空实现+Schema 校验+标准回执），并在文本分发中注册。
- 设备路由便捷查询：为 WebSocketServer 增加在线判断/广播目标等便捷方法。
- peer 路由增强：统一错误码来源、基础 payload 校验、广播目标获取与"目标离线"回执占位。
- JSON Schema 与统一错误码：集中定义 4 类消息 Schema 草案与轻量校验函数，提供 `ErrorCode` 统一枚举。

### 编辑人
- w

### 新增内容
- 三个模式处理器骨架
  - 文件：`backend/core/handle/meeting_handle.py`、`backend/core/handle/coding_handle.py`、`backend/core/handle/workflow_handle.py`
  - 功能：按契约对 `meeting/coding/workflow` 消息进行基础 Schema 校验并回执 `status:"ok|error"`；当前为空实现占位，后续接入纪要/日志流/任务存储。

- 文本分发注册
  - 文件：`backend/core/handle/textHandle.py`
  - 功能：新增 `type:"meeting"|"coding"|"workflow"` 分支，调用对应 handler；保持原有分支不变。

- 设备路由便捷查询
  - 文件：`backend/core/websocket_server.py`
  - 功能：新增 `is_device_online()`、`get_online_device_ids()`、`get_device_count()`、`get_broadcast_targets(exclude)`，用于路由与调试。

- AI 中转路由增强（Peer）
  - 文件：`backend/core/handle/peerHandle.py`
  - 功能：
    - 统一错误码：改用 `core/utils/schema.py::ErrorCode`；
    - 基础校验：接入 `validate_peer_payload` 进行 `payload` 校验；
    - 广播目标：使用 `server.get_broadcast_targets()` 生成广播目标；
    - 离线回执占位：当存在失败目标时，追加 `TARGET_OFFLINE` 回执（含 `failed` 列表）。

- JSON Schema 与校验工具
  - 文件：`backend/core/utils/schema.py`
  - 功能：提供 `ErrorCode` 统一错误码；定义 `meeting/coding/workflow/peer` 的 Schema 草案与 `validate_*` 轻量校验函数（无外部依赖）。

### 已知缺陷 / 风险
- 三个模式 handler 为占位实现：未接入会议纪要生成、编码日志流、工作流任务存储与推送。
- `peer` 仍未实现 ACL/白名单/频率限制与细粒度审计；当前仅提供"目标离线"占位回执。

### 待验证内容
- meeting
  - 发送：`{"type":"meeting","phase":"snippet","items":[{"tag":"需求","text":"..."}]}`
  - 预期：`{"type":"meeting","status":"ok","phase":"snippet"}`；字段非法时返回 `code: SCHEMA_INVALID`。

- coding
  - 发送：`{"type":"coding","event":"log","level":"info","text":"拉起构建"}`
  - 预期：`{"type":"coding","status":"ok","event":"log"}`；字段非法时返回 `code: SCHEMA_INVALID`。

- workflow
  - 发送：`{"type":"workflow","event":"update","tasks":[{"id":"1","title":"登录联调","priority":1,"status":"open"}]}`
  - 预期：`{"type":"workflow","status":"ok","event":"update"}`；字段非法时返回 `code: SCHEMA_INVALID`。

- peer 离线目标
  - 条件：向不存在设备发送，例如 `to:["999"]`
  - 预期：发起方先收到 `status:"done"` 的回执（含 delivered/failed），随后收到 `status:"error"` + `code:"TARGET_OFFLINE"` 的占位回执。

### 影响范围与回滚
- 改动集中于后端消息处理与工具；未修改 ASR/TTS/硬件协议层；回滚可按文件逐项还原。

### 编辑内容3（配置对齐 + 回执统计 + 启动日志）
- 配置对齐：将 `backend/data/.config.yaml` 中 `server.port` 设置为 `8004`，并对齐 `server.websocket: ws://<lan-ip>:8004/supie/v1/` 与 `server.advertise_ip`（已与测试页 `test/ws_001.html`、`test/ws_002.html` 的地址保持一致）。
- 用例回归：在 `test/ws_001.html` 增加 meeting/coding/workflow/peer(单播/广播) 的发送与断言，`test/ws_002.html` 增加对结构化 peer 的断言提示，便于一键快速回归。
- 回执统计：`peer` 发起方回执新增 `elapsedMs`（耗时毫秒）与 `targetsCount`（目标数量）两字段。
- 启动日志：WebSocketServer 启动时打印在线设备数量与在线设备列表快照，便于对照测试页连接状态。

### 编辑人
- w

### 新增内容
- 配置与测试
  - 文件：`backend/data/.config.yaml`、`test/ws_001.html`、`test/ws_002.html`
  - 功能：对齐端口/地址；新增用例按钮与断言输出。

- peer 回执统计字段
  - 文件：`backend/core/handle/peerHandle.py`
  - 功能：在回执中新增 `elapsedMs`、`targetsCount`，用于联调统计与性能观测。

- 启动日志增强
  - 文件：`backend/core/websocket_server.py`
  - 功能：服务启动时输出 `online_count` 与 `online` 列表快照。

### 待验证内容
- 配置
  - 浏览器打开 `test/ws_001.html` 与 `test/ws_002.html`，点击"连接"，确认均能连接并收到欢迎消息；日志显示在线设备数量与列表。

- meeting
  - 发送：`{"type":"meeting","phase":"snippet","items":[{"tag":"需求","text":"..."}]}`
  - 预期：`{"type":"meeting","status":"ok","phase":"snippet"}`。

- coding
  - 发送：`{"type":"coding","event":"log","level":"info","text":"拉起构建"}`
  - 预期：`{"type":"coding","status":"ok","event":"log"}`。

- workflow
  - 发送：`{"type":"workflow","event":"update","tasks":[{"id":"1","title":"登录联调","priority":1,"status":"open"}]}`
  - 预期：`{"type":"workflow","status":"ok","event":"update"}`。

- peer 单播（001→002）
  - 发送：`{"type":"peer","to":["002"],"payload":{"text":"请明早10点前完成登录模块联调，优先级1","context":{"locale":"zh-CN"}}}`
  - 预期：002 收到结构化 `peer`；001 收到 `status:"done"` 回执（含 `elapsedMs`、`targetsCount`）；若离线则再收 `code:"TARGET_OFFLINE"` 错误。

- peer 广播（001→all）
  - 发送：`{"type":"peer","to":["broadcast"],"payload":{"text":"下午4点同步周会纪要"}}`
  - 预期：在线且非发起方收到；发起方回执包含 `delivered/failed` 列表以及 `elapsedMs`、`targetsCount`。

### 已知缺陷 / 风险
- 未引入 ACL/白名单/频率限制；离线/权限场景仍依赖回执占位与后续实现。
- meeting/coding/workflow 仍为占位实现，后续将接入纪要生成、步骤化日志与任务持久化。

### 影响范围与回滚
- 改动集中于配置、测试页与日志/回执信息；不影响 ASR/TTS/硬件协议层；回滚可按文件逐项还原。


### 编辑内容4（服务端观测增强 + 测试页联调工具）
- 服务端观测增强：后端周期与事件广播 `server.stats`，测试页可实时看到在线设备数量/列表与服务器 CPU/内存占用。
- 测试页联调工具：双页面支持"断开"与"订阅服务端统计"，保留既有用例按钮与断言，实现更细致全面的联调验证。

### 编辑人
- w

### 新增内容
- 服务端统计广播
  - 文件：`backend/core/websocket_server.py`
  - 功能：
    - 周期广播：新增 `_periodic_stats_task()` 每 10 秒向所有在线连接推送 `{"type":"server","event":"stats"}`；
    - 事件广播：设备注册/注销时立即调用 `broadcast_server_stats()` 推送最新快照；
    - 指标字段：`deviceCount`、`online`、`cpuPercent`、`memPercent`、`memUsedMB`、`memTotalMB`（由 psutil 采集，真实值）。

- 测试页观测与控制
  - 文件：`test/ws_001.html`、`test/ws_002.html`
  - 功能：
    - 新增"订阅服务端统计"按钮；接收并展示 `server.stats`（上线/下线即时推送 + 周期 10s）；
    - 新增"断开"按钮，便于模拟离线用例与触发 `TARGET_OFFLINE` 路径；
    - 保留并增强日志输出，便于对照 delivered/failed、targetsCount、elapsedMs 等回执统计。

### 已知缺陷 / 风险
- `server.stats` 为服务器侧资源与在线快照，不代表设备端资源；设备侧 CPU/内存需后续按硬件实现另行上报。
- psutil 不可用时将降级（不含 CPU/内存字段）；周期广播会带来少量额外流量与日志输出。

### 待验证内容
- 观测
  - 两页分别点击"连接"与"订阅服务端统计"，确认每 10 秒收到 `server.stats`，并在上线/下线时即时推送；
  - 校对字段：`deviceCount`、`online` 列表与后端日志一致；CPU/内存存在正常波动。

- 功能回归（已有）
  - `mode/meeting/coding/workflow` 仍返回 `status:"ok"`；
  - `peer` 单播/广播：发起方回执含 `delivered/failed`、`targetsCount`、`elapsedMs`；接收方能看到结构化 `peer`；
  - 离线用例：断开目标后单播，应先收到 `done`（failed 含目标），随后收到 `code:"TARGET_OFFLINE"`。

### 影响范围与回滚
- 改动集中于 `websocket_server` 与测试页 HTML；未影响语音/意图/LLM 主链路；回滚可按文件逐项还原。


8.12

### 编辑内容8（会议模式闭环：会中累计 + 结束总结 + 下发 + 存档）

### 编辑人
- w

### 新增内容
- 会中累计与缓存
  - 文件：`backend/core/connection.py`
  - 内容：新增 `meeting_segments/meeting_start_ts/meeting_last_snippet_ts/meeting_last_snippet_index` 字段，用于会中片段缓存与时长计算。

  - 文件：`backend/core/handle/receiveAudioHandle.py`
  - 内容：在 `startToChat()` 中，当 `conn.current_mode == "meeting"` 时，把自然语言文本累计为会中片段（节流为"每条即累计"）。

  - 文件：`backend/core/handle/meeting_handle.py`
  - 内容：当收到 `{"type":"meeting","phase":"snippet"}` 时，将 `items[].text` 追加至 `meeting_segments` 并更新时间戳。

- 结束触发（Finalize）
  - 文件：`backend/core/handle/textHandle.py`
  - 内容：
    - `{"type":"mode","state":"start","mode":"meeting"}`：清空会中缓存并记录开始时间；
    - `{"type":"mode","state":"end","mode":"meeting"}` 或 `{"type":"meeting","phase":"finalize"}`：触发总结流程。

- 纪要生成与下发
  - 文件：`backend/core/handle/meeting_handle.py`
  - 内容：实现 `finalize_meeting_and_send_summary(conn)`：
    - 汇总 `meeting_segments` 构造 prompt，调用 `conn.llm.response` 生成 bullets（严格 JSON 抽取，失败时降级为空列表）；
    - 下发结构化纪要：`{"type":"meeting","phase":"summary","title":"会议纪要","duration":"HH:MM:SS","bullets":[...]}`；
    - 清理会中缓存。

- 可选存档
  - 位置：`backend/data/meetings/<session-id>.json`
  - 内容：`segments + summary + 时间戳`，失败不影响纪要下发。

### 已知缺陷 / 风险
- 纪要质量与 JSON 解析依赖 LLM 输出；异常时会下发空 bullets 的 summary（骨架仍可用）。
- 结束多次触发的幂等性有限，重复触发可能重复下发一次 summary（不影响缓存已清理后的再次触发）。
- 仅做本地 JSON 存档，未接入数据库/检索；后续若需要查询/审计可扩展持久层。

### 待验证内容
- 流程一：
  1) 发送 `{"type":"mode","state":"start","mode":"meeting"}`；
  2) 多次发送 `meeting.snippet` 与/或在 meeting 模式下直接发送文本；
  3) 发送 `{"type":"mode","state":"end","mode":"meeting"}` 或 `{"type":"meeting","phase":"finalize"}`；
  4) 预期：收到 `meeting.summary`（含 `title/duration/bullets`），并在 `backend/data/meetings/` 看到对应存档文件。

- 异常路径：
  - 关闭/异常 LLM：也会收到 `meeting.summary`，但 `bullets` 为空列表；
  - 二次 finalize：可能再次下发一次 summary（缓存清理后为空纪要）。

### 影响范围与回滚
- 改动集中于 `connection/receiveAudioHandle/meeting_handle/textHandle`；未改动 ASR/TTS/硬件协议层；回滚按文件逐项还原即可。

### 编辑内容9（编码模式日志流 + 工作流任务引擎 + 观测对齐）

### 编辑人
- w

### 新增内容
- 编码模式：最小可用日志流
  - 文件：`backend/core/handle/coding_handle.py`
  - 功能：新增 `event:"start"` 触发模拟日志流（每0.5s推送1行，共6–8行，`info|warn|error` 级别混合）；其余事件维持校验与标准回执。

- 工作流任务引擎（内存+JSON 落盘）
  - 文件：`backend/core/utils/tasks_store.py`
  - 功能：提供 `add/add_many/list/complete/save/load` 接口，默认存储 `backend/data/tasks.json`，线程安全；
  - 文件：`backend/core/handle/workflow_handle.py`
  - 功能：对接任务存储，处理 `event:"update"`，支持任务新增/更新并推送最新列表：`{"type":"workflow","event":"update","tasks":[...]}`；向当前连接回发，尝试向其他在线设备广播。
  - 变更：删除 `test/tasks_store.py` 示例版，统一使用 `backend/core/utils/tasks_store.py`。

- 观测对齐
  - 文件：`backend/core/websocket_server.py`
  - 功能：启动日志追加 `server.stats broadcasting enabled` 提示；若 `psutil` 不可用自动降级（已在实现中处理）。

### 待验证内容
- 编码模式：
  - 发送：`{"type":"coding","event":"start"}`
  - 预期：每0.5s收到一行 `coding.log`，共6–8行，包含 `level/text` 字段。

- 工作流：
  - 发送：`{"type":"workflow","event":"update","tasks":[{"id":"1","title":"登录","priority":1,"status":"open"}]}`
  - 预期：回发 `workflow.update`（含全量任务）；再次发送更新同一 id 的任务应覆盖字段；多个终端应同步收到。

- 观测：
  - 服务启动日志包含 `server.stats broadcasting enabled`；`psutil` 缺失时 `server.stats` 中 CPU/内存字段省略，页面不报错。

### 已知缺陷 / 风险
- 编码日志为模拟流；MCP 步骤接入留待后续（保留扩展点）。
- 工作流未做权限/用户隔离；广播同步策略为简单实现，后续可按会话/设备分组收敛。

### 影响范围与回滚
- 改动集中于 `coding_handle/workflow_handle/tasks_store/websocket_server`；不影响语音链路；回滚按文件逐项还原即可。
 
### 编辑内容10（编码模式增强 + 工作流补全 + 会议纪要稳健性）

#### 编辑人
- w

#### 新增/修改内容
- 编码模式增强（stop|clear|step|phase）
  - 文件：`backend/core/handle/coding_handle.py`、`backend/core/utils/schema.py`
  - 变更：
    - Schema 扩展 `event: start|stop|clear|phase|log|step` 与校验；
    - `start` 启动模拟流、`stop` 立即停止、`clear` 下发清屏事件与提示行、`step` 同步下发 `coding.step` 与对应 `coding.log`、`phase` 下发阶段事件并追加阶段变更日志；
    - 增加连接级运行标志 `coding_stream_running` 与 `coding_phase_name`；模拟流在停止或完成后自动复位。
  - 验收：HTML 触发上述事件，设备端可见对应变化，非法输入返回 `status:"error"`（Schema 校验）。

- 工作流补全（complete）
  - 文件：`backend/core/handle/workflow_handle.py`、`backend/core/utils/schema.py`
  - 变更：
    - Schema 增加 `event:"complete"` 与 `ids:string[]` 校验；
    - 处理 `complete`：批量调用 `tasks_store.complete`，随后回发并广播全量 `workflow.update` 列表。
  - 验收：HTML 连续发送 `update→complete`，设备端列表同步刷新为 `done`。

- 会议纪要稳健性
  - 文件：`backend/core/handle/meeting_handle.py`
  - 变更：
    - 更稳健的 JSON 提取（直接解析→括号截取降级）；
    - bullets 去重与裁剪（最多6条，保序）；
    - Summary 附加 `bulletsLength` 与 `sourceSegments` 计数。
  - 验收：`finalize` 在正常/异常 LLM 下均能输出结构化纪要；异常时 bullets 可能为空但骨架完整。

#### 待验证用例
- 编码模式：
  - `{"type":"coding","event":"start"}` → 连续日志；`stop` 立即停止；`clear` 触发清屏与提示行；`step` 与 `phase` 分别体现步骤与阶段更新。
- 工作流：
  - `update` 写入任务后发送 `complete`（如 `{"type":"workflow","event":"complete","ids":["1"]}`） → 列表中 id 为 1 的任务 `status` 变为 `done`。
- 会议纪要：
  - 会中累计后触发 `mode.end(meeting)` 或 `meeting.finalize`，观察 `bulletsLength/sourceSegments` 与去重裁剪效果。

#### 影响范围与回滚
- 改动集中于 `schema/coding_handle/workflow_handle/meeting_handle`，未影响 ASR/TTS/硬件协议层；回滚可按文件逐项还原。

#### 安全与稳健性修复
##### 高风险修复摘要
- Peer 无权限验证：ACL 前置拦截，未授权目标直接拒绝并并入 failed 回执
- LLM 注入攻击风险：输入净化（截断/去除代码栅栏）+ 强制仅输出 JSON 的系统约束
- 设备路由竞态条件：新增加锁快照接口（async）避免注册/注销竞态导致的列表不一致
- 会议内存无限增长：finalize 后清理会中缓存；纪要 bullets 去重并限幅（≤6）
- 设备 ID 欺骗
  - 文件：`backend/core/websocket_server.py`、`backend/core/connection.py`
  - 修复：注册设备路由时检测重复设备ID并拒绝新连接；连接侧收到拒绝后立即关闭，防伪装。

- 工作流并发写入冲突
  - 文件：`backend/core/utils/tasks_store.py`
  - 修复：落盘与加载均在锁内处理，加载阶段做基础schema清洗，避免多设备并发更新导致数据损坏。

- 模式状态非原子切换
  - 文件：`backend/core/handle/textHandle.py`
  - 修复：在 `mode.start(meeting)` 初始化会中缓存与时间戳；`mode.end(meeting)` 统一触发 finalize，保证状态切换一致；相关字段在 `connection.py` 初始化。

- Schema 验证不完整
  - 文件：`backend/core/utils/schema.py`
  - 修复：扩展 `coding` 与 `workflow` 的校验枚举与必填项（`start|stop|clear|phase|log|step`、`update|complete` 等），防止恶意格式绕过。

- 广播无频率限制
  - 文件：`backend/core/handle/peerHandle.py`
  - 修复：对 broadcast 增加简易频率限制（每设备≥5s一次）；ACL 在 LLM 前拦截，未授权目标并入 `failed` 回执。

### 严重问题复盘（WS/OTA 全链路不可达）

- 现象
  - OTA 页面一直转圈；浏览器 WS 测试页无法连接；硬件连不上；服务端基本无新日志输出。

- 根因（按影响度排序）
  1) WebSocket 升级前回调用法错误（库 API 误用）
     - 表现：`websockets.serve(process_request=...)` 的回调签名与返回值不符合库约定，且将 `request_headers` 误当成带 `.headers` 属性的对象，并错误调用了不存在的 `websocket.respond()`。
     - 影响：握手前即异常/返回非法响应，导致前端/硬件反复重试，服务端几乎无有效业务日志（仅低层异常）；对外表现为"连不上、一直转圈"。
     - 涉及：`backend/core/websocket_server.py::_http_response`。
  2) 连接对象属性混淆（aiohttp vs websockets）
     - 表现：使用了 `ws.request.headers / ws.request.path` 读取请求信息，实际 `websockets` 对象应使用 `request_headers / path`。
     - 影响：在连接建立或首包解析阶段抛异常，进一步放大"无日志"的表象。
     - 涉及：`backend/core/connection.py::handle_connection`。
  3) OTA 返回的 WS 地址与前端/文档不一致
     - 表现：OTA 返回 `/xiaozhi/v1/`，而测试页/文档/后端其他模块使用 `/supie/v1/`。
     - 影响：设备按 OTA 提示接入错误路径，连接失败；端到端联调断裂。
     - 涉及：`backend/core/api/ota_handler.py::_get_websocket_url`。
  4) 启动阶段对 ffmpeg 的硬阻断
     - 表现：未安装 ffmpeg 时抛异常终止进程。
     - 影响：服务未对外监听；用户仅看到"连不上、无新日志"。
     - 涉及：`backend/app.py::main` 调用 `check_ffmpeg_installed()`。
  5) 配置不一致与设备 ID 冲突（次级放大器）
     - 端口/地址不一致（8000/8004、`127.0.0.1` vs `0.0.0.0`、IP 变化未更新）与同 `device-id` 并发连接被拒绝，会放大"无法连通"的表象。

- 修复项（最小侵入，现已落地）
  - WebSocket 升级回调改为库规范签名/返回值：升级请求返回 `None`，普通 HTTP 返回 `(status, headers, body)`；并移除对不存在 API 的调用。
    - 文件：`backend/core/websocket_server.py`，函数：`_http_response`
  - 连接对象读取对齐 `websockets`：统一使用 `request_headers / path`，解析 `device-id/client-id`；远端 IP 解析容错。
    - 文件：`backend/core/connection.py`，函数：`handle_connection`
  - OTA WS 路径统一为 `/supie/v1/`，与测试页/文档一致。
    - 文件：`backend/core/api/ota_handler.py`，函数：`_get_websocket_url`
  - 启动阶段 ffmpeg 缺失降级为告警，不再阻断监听与联调。
    - 文件：`backend/app.py`，函数：`main`
  - 本地覆盖配置建议：`server.ip=0.0.0.0`、`server.port=8004`、`server.http_port=8003`、（可选）对齐 `advertise_ip` 与 `websocket`。
    - 文件：`backend/data/.config.yaml`

- 验收与回归
  - 打开 `http://<IP>:8003/supie/ota/`：应返回"OTA接口运行正常，向设备发送的websocket地址是：ws://<IP>:8004/supie/v1/"。
  - 测试页 `test/ws_001.html`/`ws_test_enhanced.html` 连接 `ws://<IP>:8004/supie/v1/?device-id=001&client-id=001`：应立即收到欢迎 JSON；后端日志出现启动信息与连接 headers。
  - 硬件侧通过 OTA 获取到 `/supie/v1/` 后可正常连通；同一 `device-id` 并发连接会被拒绝（属预期防伪装行为）。

- 防复发措施
  - 协议自检：启动后自测一次本地 loopback WS 升级与 GET 路由（不影响对外监听），异常立即 ERROR 级日志并退出。
  - 统一路径与端口：后端仅使用 `/supie/v1/`；文档/测试页/OTA 全量对齐端口 8004。
  - 依赖降级：对可选依赖（ffmpeg/psutil）一律降级为告警；仅在使用到对应能力时提示失败原因。
  - 观测增强：WS 启动日志输出 host/port、online 快照与周期 `server.stats` 广播；握手失败计数与近因上报。

#### 追加修复（握手 path 兼容性 + 显式等待启动 + 端口预检测）

- 新增现象（2025-08-12 下午）：
  - 浏览器端"连接成功后立刻关闭(code=1000)"，后端多次报"无法获取请求路径"。

- 进一步根因：
  - websockets(v14.2) 在 handler 回调第二参数传入 `path`；旧实现仅从 `ws.path` 读取，某些环境下为空，导致无法解析 `device-id` 并提前关闭。

- 修复项（已落地）：
  - 兼容握手 path：`WebSocketServer._handle_connection(self, websocket, path)` 接收并下传 `path`；`ConnectionHandler.handle_connection(ws, path)` 优先用入参 `path`，再回退 `ws.path`，仍无则自动分配 `auto-<8位>` 的 `device-id` 并继续会话（warning）。
    - 文件：`backend/core/websocket_server.py`、`backend/core/connection.py`
  - 显式等待启动：新增 `wait_started()`；`app.py` 在启动 WS 后 `await` 等待启动完成，失败立即 ERROR 并退出。
    - 文件：`backend/core/websocket_server.py`、`backend/app.py`
  - 端口预检测：启动前做一次 socket 预绑定检查（SO_REUSEADDR），端口占用/权限不足直接 ERROR 并抛出，杜绝"看似运行但未监听"。
    - 文件：`backend/core/websocket_server.py`

- 实测与验收：
  - 启动日志出现：`WebSocketServer started on 0.0.0.0:8004, online_count=0, online=[]` 与 `WebSocket 服务启动完成`。
  - 使用 `test/ws_test_enhanced.html` 连接：不再出现"无法获取请求路径/秒断开"；可稳定收到欢迎 JSON 与后续消息；ID 冲突由页面自动规避（或由服务端拒绝并给出提示）。

#### 实测回归与配置建议（2025-08-12）

- 实测现象：
  - 成功收到服务端周期广播 `server.stats` 与 `hello` 欢迎包。
  - `mode/meeting/coding/workflow` 路径均返回预期回执或事件。
  - `peer` 返回 `UNAUTHORIZED(no permitted targets)`，为 ACL 正常拦截（默认不允许向未授权目标发送）。

- 结论：
  - WS/OTA/消息处理主链路已恢复正常；"连不上/无日志/秒断开"问题闭环。

- 配置建议（需放通 peer 时选其一）：
  1) 临时放开所有目标与广播（仅用于联调）：
     ```yaml
     peer:
       enabled: true
       allow_all: true
       allow_broadcast: true
     ```
  2) 精确放行目标设备：
     ```yaml
     peer:
       enabled: true
       allow_all: false
       allow_broadcast: false
       allowlist:
         - "002"
     ```

- 其他观察：
  - 未携带 query 的连接已自动分配 `device-id`（告警提示），建议测试页始终携带 `device-id/client-id` 以避免混淆。

---

8.13

### 编辑内容13（握手 device-id 解析优先级修复 + 目标ID标准化）

#### 编辑人
- w

#### 新增/修改内容
- 握手解析优先级与健壮化
  - 文件：`backend/core/connection.py`
  - 变更：
    - 明确解析优先级：优先从 URL Query 中解析 `device-id/client-id`（`path` 入参优先，其次 `ws.path`），其次再尝试 Header（兼容 `device-id|device_id|x-device-id` 等），最后才回退 `auto-xxxx`。
    - 引入 `_normalize_id()`：去空白/引号并统一小写，确保设备登记与后续路由匹配一致。
    - 解析不到 query 时的容错增强（处理仅传 `?a=b` 的场景），并在成功解析时打印来源标记（query/header）。

- 目标ID标准化（单播/广播路径一致）
  - 文件：`backend/core/handle/peerHandle.py`
  - 变更：
    - 在 ACL 与分发前统一标准化 `to` 列表元素（去空白/引号并小写；`broadcast` 常量保留），确保与登记的小写设备ID一致匹配。

#### 已知缺陷 / 风险
- 若启用 Auth 白名单，配置中的 `allowed_devices` 建议使用小写 MAC；当前认证模块未自动小写化比对，可能需同步调整配置。
- 历史在线映射中可能仍存在 `auto-xxxx` 残留，重连后会以标准化 MAC 覆盖。

#### 待验证内容
- 连接与登记
  - 使用硬件或测试页携带 `?device-id=<MAC>&client-id=<UUID>` 连接；后端日志应出现：`握手解析 device-id: <mac> (source=query)`。
  - `server.stats` 的 `online` 列表应展示为小写 MAC。

- peer 单播（大小写兼容）
  - 发送：`{"type":"peer","to":["<MAC-Upper>"] ,...}` 与 `{"type":"peer","to":["<mac-lower>"] ,...}` 均应命中同一在线设备。

- 回退路径
  - 不携带 `device-id` 连接：应打印 Warning 并分配 `auto-<8位>`，仅用于联调；建议生产侧始终携带 Query。

#### 影响范围与回滚
- 改动集中于握手解析与 peer 目标标准化；未更改 ASR/TTS/模式处理器。
- 回滚：
  - 还原 `backend/core/connection.py` 与 `backend/core/handle/peerHandle.py` 对应 edits 即可。


### 编辑内容15（Meeting去重与节流 + Peer离线补投 + 回执统计）

#### 编辑人
- w

#### 新增/修改内容
- Meeting（会中片段去重 + 10–15s 节流 + finalize 幂等/降级）
  - 文件：`backend/core/handle/meeting_handle.py`、`backend/core/connection.py`
  - 变更：
    - `meeting.snippet` 在连接级维护 `meeting_recent_texts/meeting_pending_texts`，对 1 分钟内重复文本去重；按默认 12s 节流合并入 `meeting_segments`（满足 10–15s 区间）。
    - `finalize` 幂等：重复触发直接重发上次 summary；异常或无片段时降级为空 bullets 的 summary；将未合并的 `pending` 一并纳入总结。
    - 存档包含 `segments` 全量（含 pending 合并后）、`bulletsLength/sourceSegments` 计数；清理会中缓存并标记 `meeting_finalized`。

- Peer（离线补投 + 回执统计）
  - 文件：`backend/core/utils/offline_queue.py`、`backend/core/handle/peerHandle.py`、`backend/core/websocket_server.py`
  - 变更：
    - 新增轻量离线队列：`backend/data/offline_peer_queue.json`（每设备最多 100 条，默认 TTL=3 天）。
    - 分发失败时自动入队；发起方回执新增 `enqueued`（成功入队的目标列表）。
    - 设备上线（注册路由）后自动出队补投，日志输出 `sent/dropped` 统计。

#### 待验证内容
- Meeting
  - 连续多次发送 `meeting.snippet`，重复文本在 1 分钟内不会重复累计；每 ~12s 才会将 pending 批量并入 `meeting_segments`。
  - 触发 `meeting.finalize` 或 `mode.end(meeting)`：收到 `meeting.summary`；若重复触发，应直接复用上次 summary；异常时 `bullets` 为空数组。

- Peer
  - 对离线目标单播：发起方回执包含 `enqueued:[<目标>]`；目标上线后自动收到补投；日志显示补投统计。
  - 广播在线/离线混合时：delivered/failed/enqueued 字段应与在线性一致。

#### 影响范围与回滚
- 改动集中于会议与 peer 路由，不影响 ASR/TTS/其他模式；回滚删除 `offline_queue.py` 并还原相应 edits 即可。


### 编辑内容16（Auth白名单小写化 + 握手日志增强 + 离线补投说明）

#### 编辑人
- w

#### 新增/修改内容
- Auth 白名单大小写兼容
  - 文件：`backend/core/auth.py`
  - 变更：将 `allowed_devices` 在初始化时统一小写；认证时对 `headers['device-id']` 小写化比对，避免大小写不一致导致白名单失效。

- 握手日志增强
  - 文件：`backend/core/connection.py`
  - 变更：在"握手解析 device-id ..."日志中增加 `rawPaths` 快照（包含 `path` 入参与 `ws.path` 的前 256 字符），用于快速定位异常客户端的 URL/Query。

- 离线补投（实现综述）
  - 文件：`backend/core/utils/offline_queue.py`、`backend/core/handle/peerHandle.py`、`backend/core/websocket_server.py`
  - 说明：采用 JSON 文件 `backend/data/offline_peer_queue.json` 维护每设备队列（默认 TTL=3 天，每设备最多 100 条）；`register_device_handler` 成功后自动 flush 并统计 `sent/dropped`。

#### 待验证内容
- Auth：配置 `allowed_devices: ['94:a9:90:07:9d:88']`（小写），握手通过；若传入大写 MAC 也能命中白名单。
- 日志：连接握手时日志输出 `source=query|header` 与 `rawPaths=[...]`；异常客户端可据此排查。
- Peer：离线目标单播回执含 `enqueued`；上线后收到补投，服务端日志打印补投统计。

#### 影响范围与回滚
- 改动集中于认证、握手日志与离线补投说明；回滚还原对应文件 edits 即可。

### 编辑内容17（握手兜底缓存 + 多属性路径解析 + 回退诊断增强）

#### 编辑人
- w

#### 新增/修改内容
- WebSocket 握手兜底缓存
  - 文件：`backend/core/websocket_server.py`
  - 变更：在 HTTP 升级回调中尝试从连接对象提取原始 path（兼容不同 websockets 版本的 `path/request_uri/raw_request_uri/request_path/raw_path`），解析 `device-id/client-id` 并暂存到 `self._handshake_cache[id(conn)]`；同时打印 `HTTP upgrade request path=...` 便于定位。

- 连接阶段读取兜底缓存 + 扩展原始路径来源
  - 文件：`backend/core/connection.py`
  - 变更：
    - 解析 candidate paths 时额外尝试 `request_uri/raw_request_uri/request_path/raw_path`；
    - 若仍未取到 query，则兜底从 `server._handshake_cache[id(ws)]` 读取 `device-id/client-id`；
    - `request_headers` 读取优先走 `items()` 以兼容 websockets 的 Headers 类型；
    - 回退日志增加 `rawPaths`/`headerKeys` 快照，便于快速判断"客户端是否携带 query/Header"。

#### 待验证内容
- 使用 `test/ws_001.html` 连接：应看到
  - `HTTP upgrade request path=/supie/v1/?device-id=...&client-id=...`
  - `握手解析 device-id: <mac> (source=query, rawPaths=[...])`
- 工牌连接：应紧随其后出现 `注册设备路由: <mac>`，`server.stats` 的 `online` 包含该 MAC。

#### 影响范围与回滚
- 变更集中于握手阶段诊断与兜底逻辑，不影响 ASR/TTS/业务处理；回滚还原上述两个文件的本次 edits 即可。


### 编辑内容19（Peer补投回执 + Workflow 字段级更新/删除 + 收敛广播）

### 编辑内容20（Workflow Schema 放宽 + 删除事件支持）

### 编辑内容21（任务分组落盘/查询 + 字段合并/分组删除 API）

### 编辑内容22（Workflow 处理器分组更新/删除 + 分组负载广播）

#### 编辑人
- w

#### 新增/修改内容
- 分组处理与收敛广播
  - 文件：`backend/core/handle/workflow_handle.py`
  - 变更：
    - 计算 `groupKey=conn.device_id[:8]`；
    - event=update：对每条任务调用 `store.upsert_fields(groupKey, id, partial)`（不存在则补建），并强制分组；
    - event=delete：`store.delete_by_ids_and_group(ids, groupKey)`；
    - event=complete：等价于按组字段更新 `status=done`；
    - 回发与广播：当前连接回发本组任务；对每个在线设备按其分组构造独立负载并单播，不再发送全量任务，避免跨组泄露。

#### 待验证内容
- 同组 A/B：创建/字段级更新/删除一致；
- 异组 C：不受 A/B 影响；A 不再看到 C 组 t2。

#### 影响范围与回滚
- 改动集中在 workflow 处理器；回滚还原该文件 edits 即可。

#### 编辑人
- w

#### 新增/修改内容
- 任务分组落盘与查询
  - 文件：`backend/core/utils/tasks_store.py`
  - 变更：
    - `add/add_many` 支持补写 `groupKey`；
    - 新增 `list_by_group(group_key)` 仅返回指定分组任务；
    - 新增 `upsert_fields(group_key, task_id, partial)` 在分组内按字段合并更新（不存在则补建）；
    - 新增 `delete_by_ids_and_group(ids, group_key)` 在分组内批量删除。

#### 待验证内容
- 新建/更新任务后，持久化对象包含 `groupKey`；
- 通过 `list_by_group` 仅能取到本组任务；
- 字段级更新不影响未提供字段；
- 分组删除仅删除本组对应 ids。

#### 影响范围与回滚
- 改动集中在任务存储；回滚还原该文件 edits 即可。

#### 编辑人
- w

#### 新增/修改内容
- Schema 放宽（update）与 delete 支持
  - 文件：`backend/core/utils/schema.py`
  - 变更：
    - `event` 允许 `update|complete|delete`；
    - `update` 仅要求 `id`；`title/priority/status` 变为可选且按出现校验（`priority` 仅在出现时要求 0..3，`status` 仅在出现时要求 open|done，`title` 仅在出现时要求非空字符串）；
    - 新增 `delete` 校验：`ids` 为非空字符串数组。

#### 待验证内容
- 发送仅含 `id` 的 `update` 应通过；
- 非法 `priority/status/title` 仅在出现时才校验报错；
- `delete` 携带 `ids` 正常通过并按业务删除。

#### 影响范围与回滚
- 改动集中在 Schema 校验；回滚还原该文件本次 edits 即可。

#### 回归与最小用例（补充，编辑人：w）
- 同组用例（A=group-aaaa-1，B=group-aaaa-2）
  - 创建：A 发送 `{type:'workflow',event:'update',tasks:[{id:'t1',title:'任务1',priority:1,status:'open'}]}` → A/B 均收到含 `t1` 的 `workflow.update`，C 无变更
  - 字段级更新无脏写：A 发送 `{id:'t1',status:'done'}`；B 发送 `{id:'t1',title:'任务1-改名'}` → A/B 最终同时体现 `title=任务1-改名`、`status=done`
  - 删除：A 发送 `{type:'workflow',event:'delete',ids:['t1']}` → A/B 列表移除 `t1`，C 无变更
- 异组隔离（C=other-bbbb-1）
  - C 发送 `{type:'workflow',event:'update',tasks:[{id:'t2',title:'其他组任务',priority:0,status:'open'}]}` → 仅 C 可见 `t2`，A/B 不可见
- 异常输入
  - 仅含 `id` 的 update 通过；
  - `priority` 缺省不报错，非法时报 `priority must be integer 0..3`；
  - `delete` 携带 `ids` 正常删除，不再报 `event must be update|complete`。

#### 编辑人
- w

#### 新增/修改内容
- Peer 补投回执
  - 文件：`backend/core/websocket_server.py`
  - 变更：设备上线 flush 离线队列后，按发起方聚合补投条数，并向各发起方回发：
    `{ "type": "peer", "event": "redelivered", "to": "<device>", "count": N }`，便于测试页断言补投成功。

- Workflow 增强（字段级 update/删除 + 收敛广播）
  - 文件：`backend/core/handle/workflow_handle.py`
  - 变更：
    - `event:"update"`：对已存在任务仅更新提交的字段（不整条覆盖），不存在则追加；
    - `event:"delete"`：支持按 `ids` 删除；
    - 广播收敛：同会话或同设备组（简化为 MAC 前8字符相同）才广播，减少不相关终端刷新。

#### 待验证内容
- Peer：离线目标在上线后，原发起方应收到 `peer.redelivered` 回执（含 count）。
- Workflow：多端同时打开测试页，对 update/delete 操作应在相同组或同会话的终端一致更新，且无脏写。

#### 影响范围与回滚
- 改动集中在补投回执与工作流路由；回滚还原上述两个文件的 edits 即可。


### 编辑内容26（打通音频→片段→纪要最小闭环 + 纪要结构化扩展 + 前端展示"全文记录"）
#### 编辑人
- w

#### 新增/修改内容

- 1：打通音频→片段→纪要最小闭环
  - 在 `backend/core/handle/receiveAudioHandle.py` 中，meeting 模式下将 ASR 文本通过调用 `handle_meeting_message` 封装为 `meeting.snippet` 注入，复用既有去重与节流逻辑，保持与前端文本片段一致的处理入口。

- 2：纪要结构化扩展
  - 在 `backend/core/handle/meeting_handle.py` 中强化 LLM 提示为严格 JSON，新增并解析 `decisions/actions/risks/nextSteps` 字段；对各字段做去重与长度裁剪；bullets 为空时加入启发式兜底。
  - 在 `backend/core/utils/schema.py` 扩展 meeting 消息 Schema，增加 `decisions/actions/risks/nextSteps`、并新增 `transcript` 相位定义。

- 3：前端展示"全文记录"
  - 服务器在总结后下发 `meeting.transcript`，携带最近 50 条 `{ts,text}` 片段；
  - 在 `test/ws_meeting.html` 新增全文记录面板与 `transcript` 处理与渲染逻辑。
  - 调整页面在收到 `summary` 后 1 秒内可见时间线。

### 编辑内容27（Meeting多语言清洗+术语映射+Prompt可配置；说话人标注；断点续传与分段小结）
#### 编辑人
- w

#### 新增/修改内容

- 1：多语言/术语清洗与 Prompt 可配置（后端）
  - 文件：`backend/core/handle/meeting_handle.py`
  - 新增：`preprocess_meeting_text()` 轻量清洗链（语言检测 zh/en → 规范化空白/标点 → 术语映射）；在 `meeting.snippet` 入库前应用
  - 配置：从 `conn.config.meeting` 读取
    - `target_lang`（优先于自动检测）、`industry`、`scenario`
    - `term_map`（支持层级键：`industry:<name>`、`zh|en`、`*` 通用）
    - `prompts.system`/`prompts.userTemplate`（覆盖默认 System/User 提示模板）
  - Prompt 动态化：封装 `_build_meeting_prompts()` 注入 `{target_lang, industry, scenario}`；复用 `server.update_config` 热更通道，无需重启

- 2：说话人/角色分离（简版）
  - Schema 扩展：`meeting.items[].speakerId?: string`
  - 注入：`backend/core/handle/receiveAudioHandle.py` 在 meeting 模式由设备 `device-id` 推导 `speakerId` 写入 `items`
  - 存储与下发：`meeting_handle.py` 将 `speakerId` 落入 `segments` 与 `meeting.transcript`（可选）

- 3：断点续传与长会分段总结
  - 活跃持久化：`backend/data/meetings/active_{device_id}.json`（`segments/lastIndex/lastCheckpointIndex/pending`）
  - 续传：`mode.start(meeting)` 自动加载活跃状态并启动 checkpoint 定时器
  - 周期性小结：`checkpoint_interval_min`（默认10分钟）增量汇总并下发阶段 `summary`（标记 `checkpoint:true`），不清理缓存
  - 总结：`finalize` 仍输出总纪要并追加 `meeting.transcript`（最近50条，保留可选 `speakerId`）

- 4：Schema/前端兼容
  - `backend/core/utils/schema.py`：`phase` 增加 `transcript`；增加 `decisions/actions/risks/nextSteps` 与 `segments` 字段；`items` 支持 `speakerId`
  - `test/ws_meeting.html`：已具备 `meeting.transcript` 展示，兼容新增字段（前端无需额外修改）

#### 待验证内容
- 多语言/术语：中英混输下 `bullets` 语言一致且术语按映射替换；修改 `meeting.prompts/term_map` 后经 `update_config` 即生效
- 说话人：`transcript` 序列项可见 `speakerId`；后续可前端按说话人分组展示
- 分段小结：长会运行时每 `checkpoint_interval_min` 分钟收到阶段 `summary`；断开重连后继续累计并小结；最终 `finalize` 输出总纪要与时间线

#### 影响范围与回滚
- 改动集中于 `meeting_handle/receiveAudioHandle/textHandle/schema` 与 `test/ws_meeting.html` 展示；
- 回滚：还原以上文件本次 edits，并删除 `backend/data/meetings/active_*.json` 活跃状态文件即可



### 编辑内容28（Workflow分组可覆写：支持 groupKey 指定目标分组）
#### 编辑人
- w

#### 新增/修改内容
- `backend/core/handle/workflow_handle.py`
  - 原逻辑：严格按"发起连接的 device-id 前 8 位"作为分组键，忽略消息内 `groupKey`，导致不同分组设备无法接收发起方写入的任务。
  - 现优化：支持分组覆写优先级：`task.groupKey` > 顶层 `msg.groupKey` > 发起连接默认分组（`device-id[:8]`）。
  - 影响事件：`update/complete/delete` 三类均按上述优先级路由到目标分组；回发与广播时也按目标分组快照推送。

#### 待验证内容
- 用 `device-id=001` 连接发送：`{"type":"workflow","event":"update","groupKey":"94:a9:90:","tasks":[{"id":"t1","title":"任务1","priority":1,"status":"open"}]}`
  - 预期：硬件设备 `94:a9:90:07:9d:88`（分组 `94:a9:90:`）能收到 `workflow.update`，看到 `t1`；发起连接也能收到更新（其所在分组的快照）。

#### 影响范围与回滚
- 改动仅在 `workflow_handle.py` 分组选择逻辑；
- 回滚：移除分组覆写分支，恢复为固定 `device-id[:8]` 分组即可。

### 编辑内容29（LLM配置与摘要稳健性 + 会议时长修正）
#### 编辑人
- w

#### 新增/修改内容
- LLM 配置与错误观测
  - 文件：`backend/core/providers/llm/openai/openai.py`
  - 变更：LLM 初始化/调用异常时输出更明确的诊断日志（base_url/api_key/model），便于快速定位 404/401/超时等问题。

- 会议时长与空纪要骨架
  - 文件：`backend/core/handle/meeting_handle.py`
  - 变更：当无片段时的空纪要 `duration` 改为按 `start→now` 估算（非固定 `00:00:00`）；LLM 响应非 JSON 时打印截断预览，并在 bullets 仍为空时输出检查配置提示。

#### 待验证内容
- 配置错误场景（无效 base_url/api_key/model）：启动与请求日志能明确显示错误提示；`meeting.finalize` 下发空骨架但不中断。
- 正常场景：`meeting.finalize` 能输出非空 bullets，duration ≥ 发送片段后间隔。


### 编辑内容30（LLM 调试日志 + meeting/coding 广播）
#### 编辑人
- w

#### 新增/修改内容
- LLM 调试增强
  - 文件：`backend/core/handle/meeting_handle.py`
  - 增加调试日志：在调用 LLM 前打印 `system_prompt` 与 `user_prompt`；调用后打印 `llm_raw` 原始字符串；解析成功时打印 `json_str` 与 `data`；异常路径打印完整堆栈（traceback）。
  - 目的：快速定位 base_url/api_key/model 配置或 Prompt 异常、以及 LLM 输出非 JSON 的问题。

- meeting 广播最小实现
  - 文件：`backend/core/handle/meeting_handle.py`
  - 在节流合并与 finalize 后，分别广播 `meeting.snippet`、`meeting.summary`、`meeting.transcript` 给其他在线设备（附带 `from`）。
  - 使用内部 `_broadcast_to_others(conn, payload)`，复用现有 `server.get_broadcast_targets()` 与 `get_device_handler()`，兼容 `send_json`/字符串发送。

- coding 广播最小实现
  - 文件：`backend/core/handle/coding_handle.py`
  - 对 `start/stop/clear/log/step/phase` 事件在回执后追加广播（附带 `from`），便于硬件实时联动状态展示。

#### 待验证内容
- LLM 调试
  - 触发 `meeting.finalize`：查看后端日志是否按序输出 `system_prompt/user_prompt/llm_raw/json_str/data`；异常时有 traceback。
  - 使用相同 `system/user` 内容在 curl 或 Python 直接调用 LLM，确认服务返回内容与后端一致。

- 广播
  - 打开两个设备连接，A 侧发送 meeting/coding 消息，B 侧应能实时收到相应 `meeting.*` 或 `coding.*` 事件（带 `from=A`）。

#### 影响范围与回滚
- 改动集中于 meeting/coding handler 调试与广播；
- 回滚删除 `_broadcast_to_others` 调用与相关调试日志即可。


### 编辑内容34（Meeting v1.1 契约固定 + 查询接口 Recent/Detail）
#### 编辑人
- w

#### 新增/修改内容
- Meeting v1.1 契约
  - 文件：`backend/core/utils/schema.py`
  - 固化 `meeting.summary` 字段：`title, duration, bullets, decisions, actions, risks, nextSteps`；
  - `meeting.transcript` item 结构允许 `speakerId?`：`{ ts:int, text:string, speakerId?:string }`；
  - 校验：缺失字段按空数组/空串兜底，严格类型校验（数组元素为 string）。

- 查询接口（Recent/Detail）
  - 文件：`backend/core/http_server.py`
  - 新增路由：
    - `GET /supie/meetings/recent?limit=10`：读取 `backend/data/meetings/*.json`，按 `endedAt|startedAt` 倒序返回简表：`sessionId, startedAt, endedAt, durationMs, bulletsLength`
    - `GET /supie/meetings/{sessionId}`：返回该会议信息摘要：`summary{title,duration,bullets,decisions,actions,risks,nextSteps}` 与 `segmentsCount`
  - 约束：空库返回 `[]`；未找到详情返回 `404:{error:"not found"}`。

#### 待验证内容
- 在 `test/ws_meeting.html` 触发 `finalize` 后：
  - `meeting.summary` 字段齐全且类型正确；`meeting.transcript`（如需要）记录条目包含可选 `speakerId`；
  - 打开 `/supie/meetings/recent` 能看到最新会议信息；打开 `/supie/meetings/{sessionId}` 能看到对应摘要与 `segmentsCount`；空库返回空数组。

#### 影响范围与回滚
- 改动集中于 `schema/http_server`；不影响音频/ASR/WS 主链路；
- 回滚：还原上述文件 edits 并移除新增 HTTP 路由即可。

### 编辑内容35（后端问题修复：连接处理、MCP配置、Peer消息）
#### 编辑人
- w

#### 新增/修改内容
- **重复设备ID连接处理改进**
  - 文件：`backend/core/websocket_server.py`、`backend/core/connection.py`
  - 修改 `register_device_handler` 逻辑：当检测到重复设备ID时，主动断开旧连接并接受新连接
  - 旧连接收到 `{"type": "system", "message": "设备被新连接替换，即将断开"}` 后关闭
  - 支持设备重连场景，避免因网络中断导致的重复ID拒绝问题

- **MCP配置文件处理优化**
  - 文件：`backend/core/mcp/manager.py`
  - 配置文件不存在时降级日志级别从 `warning` 到 `info`，避免误导
  - 增加安全检查：初始化MCP服务前检查 `func_handler` 存在性
  - 空配置或无配置文件时优雅跳过，不影响主流程

- **Peer消息权限与频率限制增强**
  - 文件：`backend/core/handle/peerHandle.py`
  - 增强ACL权限检查：
    - 支持配置 `max_targets` 限制单次消息最大目标数（默认10）
    - 增加详细的权限检查日志，便于调试
  - 优化频率限制：
    - 普通消息：每秒最多5条
    - 广播消息：每10秒最多1条（原为5秒）
    - 增加剩余等待时间提示

#### 验收要点
- 设备重连：同一device-id重新连接时，旧连接自动断开，新连接正常建立
- MCP功能：无配置文件时正常运行，不报警告；有配置时正确加载
- Peer消息：频率限制生效，超限返回明确错误；ACL权限正确执行

#### 影响范围与回滚
- 影响范围：WebSocket连接管理、MCP初始化、Peer消息处理
- 回滚：还原上述文件修改即可恢复原逻辑

### 编辑内容36（会议质量提升：Prompt模板与观测指标）
#### 编辑人
- w

#### 新增/修改内容
- **行业Prompt模板与术语映射**
  - 文件：`backend/data/.config.yaml`
  - 新增 `meeting.prompts.templates` 配置节，支持5个行业模板：
    - tech: 技术团队会议，强调架构决策和技术任务
    - finance: 金融合规会议，重点审批流程和风险
    - medical: 医疗讨论，使用标准医学术语
    - education: 教研会议，关注教学方法
    - legal: 法律案件讨论，引用法条
  - 新增 `meeting.term_map` 术语映射配置：
    - 支持通用映射 `*`、语言映射 `zh`
    - 支持行业专属术语 `industry:tech/finance/medical/education/legal`
  - 标题命名策略：tech用"项目名/周次/核心主题"，finance用"部门/日期/议题"等

- **动态模板加载逻辑**
  - 文件：`backend/core/handle/meeting_handle.py`
  - 修改 `_build_meeting_prompts` 函数：
    - 优先加载行业模板 `templates[industry]`
    - 其次使用直接配置 `prompts.system/userTemplate`
    - 最后回退默认模板
    - 支持模板变量替换：`{target_lang}`, `{industry}`, `{scenario}`
  - 无需重启服务，通过 update_config 即可生效

- **观测指标与日志**
  - 文件：`backend/core/handle/meeting_handle.py`
  - 新增指标统计：
    - `segmentsCount`: 源片段数量
    - `checkpointCount`: 阶段小结次数
    - `llmElapsedMs`: LLM调用耗时（毫秒）
    - `emptyBullets`: 是否空骨架（true/false）
    - `bulletsLength`: 实际bullets条数
  - 在 `finalize_meeting_and_send_summary` 中输出观测日志：
    ```
    [Meeting Metrics] segmentsCount=N, checkpointCount=N, 
    llmElapsedMs=N, emptyBullets=false, bulletsLength=N,
    industry=tech, scenario=project_review
    ```

- **测试断言增强**
  - 文件：`test/run_all_tests.py`
  - 增强 `simulate_meeting_idempotency` 函数：
    - 发送更真实的会议片段内容
    - 收集并分析summary质量指标
  - 新增断言检查：
    - 字段齐全性（title/duration/bullets等7个字段）
    - Bullets存在性和数量合理性（1-6条）
    - 源片段追踪（sourceSegments > 0）
    - 空骨架率计算
  - 生成测试报告 `test/results/summary.md`：
    - Meeting基础指标
    - 质量指标与空骨架率
    - 断言结果汇总
    - 测试通过/失败结论

#### 验收要点
- 配置切换：修改 `.config.yaml` 中 `meeting.industry` 后，下次会议使用对应模板
- 术语映射：配置 `term_map` 后，会议文本自动替换专业术语
- 观测日志：后端日志出现 `[Meeting Metrics]` 行，包含所有指标
- 测试报告：运行 `python test/run_all_tests.py` 生成 `test/results/summary.md`

#### 影响范围与回滚
- 影响范围：会议Prompt生成、观测日志、测试脚本
- 回滚：还原 `.config.yaml`、`meeting_handle.py`、`run_all_tests.py` 即可

### 编辑内容37（紧急修复：LLM纪要生成与连接处理）
#### 编辑人
- w

#### 新增/修改内容
- **LLM纪要生成失败修复**
  - 文件：`backend/core/handle/meeting_handle.py`
  - 添加LLM可用性检查：在调用前检测 `conn.llm` 是否存在
  - LLM不可用时生成默认纪要：["会议内容已记录", "LLM服务暂时不可用", "请稍后重试"]
  - 修复异常处理缩进问题，确保JSON解析失败时正确降级
  - 增强日志输出，记录LLM原始响应便于调试

- **Transcript消息推送修复**
  - 文件：`backend/core/handle/meeting_handle.py`
  - 确保transcript消息始终发送，即使segments为空
  - 添加 `totalSegments` 字段，提供完整段落数统计
  - 增加日志记录：`发送transcript: segments=N, total=N`
  - 修复广播逻辑，确保其他设备也能收到transcript

- **重复设备ID连接优化**
  - 文件：`backend/core/websocket_server.py`
  - 改进"踢旧迎新"逻辑：旧连接断开失败时不影响新连接注册
  - 发送系统消息时增加异常捕获，避免已断开连接导致失败
  - 即使旧连接清理失败，也继续接受新连接
  - 增强日志输出，明确显示"断开旧连接并接受新连接"

- **MCP配置警告优化**
  - 文件：`backend/core/mcp/manager.py`
  - 降低无配置文件时的日志级别从 `info` 到 `debug`
  - 添加静态标记避免重复警告输出
  - 创建示例配置文件 `data/.mcp_server_settings.json.example`
  - 配置不存在时提示参考示例文件

#### 验收要点
- LLM失败时：会议纪要仍能生成，包含默认bullets提示服务不可用
- Transcript推送：即使无内容也会发送空数组，包含totalSegments统计
- 设备重连：同device-id重连时，旧连接自动断开，新连接正常建立
- MCP日志：首次启动仅输出一次debug级别提示，不再重复警告

#### 影响范围与回滚
- 影响范围：会议纪要生成、WebSocket消息推送、连接管理、MCP初始化
- 回滚：还原 `meeting_handle.py`、`websocket_server.py`、`mcp/manager.py` 即可

### 编辑内容38（会议存储优化：索引、分片与Webhook）
#### 编辑人
- w

#### 新增/修改内容
- **会议索引与分片存储**
  - 文件：`backend/core/handle/meeting_handle.py`
  - 实现 `index.json` 索引文件：
    - 记录最近100条会议的元信息
    - 包含：sessionId、deviceId、title、时间戳、bullets数量、段落数量
    - 按endedAt时间倒序排列
  - 长会议segments分片：
    - 超过100条segments时自动分片存储
    - 每个分片文件存储100条，位于 `meetings/segments/` 目录
    - 主文件只保留前50条作为预览，标记 `preview: true`
    - 记录 `totalCount` 和 `shardCount` 便于后续加载
  - 新增 `_update_meeting_index()` 函数管理索引更新

- **详情API增强**
  - 文件：`backend/core/http_server.py`
  - `/supie/meetings/{sessionId}` 接口增强：
    - 新增 `transcriptPreview` 字段，提供前5条对话预览
    - 支持分片存储检测，返回 `hasShards` 标记
    - 包含 `deviceId` 设备标识
    - 返回完整 `metrics` 性能指标
  - 智能处理分片与非分片两种存储格式

- **Webhook通知机制**
  - 文件：`backend/core/handle/meeting_handle.py`、`backend/data/.config.yaml`
  - 配置项：`meeting.webhook.url`
  - 实现 `_send_webhook()` 异步通知函数：
    - 会议finalize后自动推送摘要到配置的URL
    - 包含：sessionId、deviceId、summary、metrics、durationMs
    - 5秒超时保护，失败不影响主流程
    - 使用 `asyncio.create_task` 异步发送
  - 配置示例已添加到 `.config.yaml`

- **测试报告增强**
  - 文件：`test/run_all_tests.py`
  - 新增 `extract_meeting_metrics_from_log()` 函数：
    - 从日志文件提取 `[Meeting Metrics]` 行
    - 解析：segmentsCount、checkpointCount、llmElapsedMs等指标
    - 支持多个日志路径查找
  - 测试报告新增"性能指标"章节：
    - 自动从日志提取并展示Meeting Metrics
    - 包含LLM耗时、空骨架状态、行业场景等信息

#### 验收要点
- 索引文件：`backend/data/meetings/index.json` 自动生成并更新
- 长会议：超过100条segments时生成分片文件
- 详情API：返回transcriptPreview预览文本
- Webhook：配置URL后会议结束时自动推送
- 测试报告：`test/results/summary.md` 包含Meeting Metrics章节

#### 影响范围与回滚
- 影响范围：会议存储、HTTP API、测试报告生成
- 回滚：还原 `meeting_handle.py`、`http_server.py`、`run_all_tests.py`、`.config.yaml` 即可


### 编辑内容40 新增ws_meeting.html文件上传格式pous
#### 编辑人
- w

#### 新增/修改内容
- **LLM提示词优化**
  - 文件：`backend/core/handle/meeting_handle.py`
  - 重写默认系统提示词，提供更详细的字段说明：
    - 明确说明每个字段的用途和提取方法
    - decisions: 强调识别"已达成的决定、确定的方案或共识"
    - actions: 要求"识别需要执行的具体任务，包含负责人"
    - risks: 指导"识别提到的问题、挑战、风险或担忧"
    - nextSteps: 说明"识别下一步计划、后续安排或待办事项"
  - 添加处理原则：
    - "仔细分析会议内容，提取相应信息填充各字段"
    - "如某字段无相关内容，必须返回空数组[]，不要编造"
  - 字数限制调整：title不超过30字，其他字段每条20-40字

- **MCP配置警告消除**
  - 文件：`backend/core/mcp/manager.py`
  - 自动创建空配置文件：
    - 检测到配置不存在时，自动创建 `data/.mcp_server_settings.json`
    - 内容为 `{"mcpServers": {}}`，表示暂无MCP服务配置
    - 日志级别降为debug，提示信息更友好
  - 文件：`backend/data/.mcp_server_settings.json`
  - 创建标准空配置文件，避免启动警告

#### 验收要点
- LLM纪要生成：会议纪要中decisions、actions、risks、nextSteps字段根据实际内容填充，无内容时返回空数组
- MCP配置：后端启动时不再出现MCP配置文件缺失警告，自动创建空配置
- 提示词效果：LLM能更准确识别并分类会议中的决策、行动项、风险和后续步骤

#### 影响范围与回滚
- 影响范围：LLM提示词生成、MCP初始化
- 回滚：还原 `meeting_handle.py`、`mcp/manager.py`，删除 `.mcp_server_settings.json` 即可

### 编辑内容41（Opus解码增强与会议转写推送实现）

#### 编辑人
- w

#### 新增/修改内容
- **Opus解码链路增强**
  - 文件：`backend/core/providers/vad/silero.py`
  - 增强错误处理和日志记录：
    - 添加数据包统计，每100个包记录一次处理信息
    - 增加Opus解码错误的详细日志，包含包序号和大小
    - 实现corrupted stream检测和自动重置机制
    - 添加VAD检测状态日志（每50次检测记录一次）
  - 错误恢复机制：
    - 检测到"corrupted stream"错误时自动重置解码器
    - 记录解码器重置事件便于排查
  
- **会议转写消息推送实现**
  - 文件：`backend/core/handle/meeting_handle.py`
  - 新增转写推送机制：
    - 实现 `_run_transcript_push_loop` 异步任务
    - 默认12秒推送间隔（可配置 `transcript_push_interval_ms`）
    - 推送消息格式：phase="transcript"，包含累积的转写内容
    - 推送后自动清理待发队列并合并到主缓存
  - 任务管理优化：
    - 新增 `start_meeting_timers` 统一管理定时任务
    - 新增 `stop_meeting_timers` 在会议结束时停止任务
    - 自动在收到snippet时启动推送任务

#### 验收要点
- Opus解码：不再出现"corrupted stream"错误，或出现时能自动恢复
- 日志观察：能看到Opus统计信息、VAD检测状态、转写推送日志
- 转写推送：每10-15秒收到meeting.phase="transcript"消息
- 会议结束：定时任务正确停止，不再推送转写内容

#### 影响范围与回滚
- 影响范围：VAD处理、ASR触发、会议模式转写推送
- 回滚：还原 `silero.py`、`meeting_handle.py` 即可


### 编辑内容43（Transcript分页API + 推送间隔热更 + Webhook一次重试）
#### 编辑人
- w

#### 新增/修改内容
- Transcript 全量分页 API
  - 文件：`backend/core/http_server.py`
  - 新增：`GET /supie/meetings/{sessionId}/transcript?offset=0&limit=100`
    - 支持主文件与分片（`meetings/segments/{sid}_shard_K.json`）联合按序读取
    - 返回 `{ items, total, offset, limit }`；limit 范围 1..500
    - 兼容 `segments` 为预览结构（`preview:true,totalCount,segments[]`）与完整列表两种存储格式

- Transcript 推送间隔热更
  - 文件：`backend/core/handle/meeting_handle.py`
  - `transcript_push_interval_ms` 从 `server.config.meeting` 优先读取（回退 `conn.config.meeting`），`update_config` 后下一周期自动生效
  - 推送完成日志输出下一周期时长，便于观测

- Webhook 一次重试（可选）
  - 文件：`backend/core/handle/meeting_handle.py`
  - `_send_webhook()` 增加 2–5 秒随机退避的单次重试；仍失败仅告警，不影响下发与存档

#### 待验证内容
- Transcript 分页：
  - 正常会：`offset/limit` 生效、顺序正确、`total` 与 `index.json/totalCount` 一致
  - 分片会：存在分片文件时也能按序返回；首片缺失时 preview 覆盖前 50 条
- 间隔热更：通过 `server.update_config` 修改 `meeting.transcript_push_interval_ms`，下一周期生效，日志可见新周期
- Webhook：断网→恢复后重试可成功；两次均失败仅日志告警

#### 影响范围与回滚
- 改动集中于 `http_server.py` 与 `meeting_handle.py`；
- 回滚删除新增 HTTP 路由与 `_send_webhook` 重试逻辑，`_run_transcript_push_loop` 间隔读取回退 `conn.config` 即可。

### 编辑内容44（会议模式旁路TTS/LLM + 线程池缩减 + 设备侧VAD优先）
#### 编辑人
- w

#### 新增/修改内容
- 会议模式旁路 TTS/LLM
  - 文件：`backend/core/handle/receiveAudioHandle.py`
  - 变更：`startToChat` 在 `conn.current_mode=="meeting"` 时，仅注入 `meeting.snippet`；支持按配置 `meeting.disable_chat_on_snippet`（默认 true）阻止触发对话 LLM；`meeting.disable_tts` 为 true 时不发送 STT。
- 会议模式禁用 TTS 音频下发
  - 文件：`backend/core/handle/sendAudioHandle.py`
  - 变更：当 `meeting.disable_tts==true` 时，不下发音频帧与表情，仅在 FIRST/LAST 时发送 `tts start/stop` 占位。
- 线程池缩减/可配置
  - 文件：`backend/core/connection.py`
  - 变更：连接级 `ThreadPoolExecutor` 从 5 → 2，支持 `meeting.threadpool_max_workers` 覆盖；初始化组件时如 `meeting.disable_tts==true`，跳过打开 TTS 通道（懒启动）。
- 设备侧 VAD 优先
  - 文件：`backend/core/handle/textHandle.py`
  - 变更：进入会议模式时按 `meeting.prefer_device_vad`（默认 true）将 `client_listen_mode` 设为 `manual`，提示前端/硬件以 `listen start/stop` 括起语音段；退出会议模式恢复 `auto`。

#### 配置建议
- `meeting.disable_tts: true`
- `meeting.disable_chat_on_snippet: true`
- `meeting.prefer_device_vad: true`
- 可选：`meeting.threadpool_max_workers: 2`

#### 影响范围与回滚
- 仅影响会议模式；回滚删除上述条件分支即可恢复原行为。


### 编辑内容46（按模式选择LLM + 连接级LLM缓存 + 意图/记忆切换）
#### 编辑人
- w

#### 新增/修改内容
- 模式/用途选择 LLM
  - 文件：`backend/core/connection.py`
  - 新增：`get_llm_for(purpose)`，按 `server.config.llm_by_mode` → `config.selected_module.LLM` 解析别名，懒加载与缓存 LLM 实例
  - 关闭连接时清理 `self._llm_cache`
- 会议总结切换模型
  - 文件：`backend/core/handle/meeting_handle.py`
  - 变更：`finalize_meeting_and_send_summary` 改为使用 `get_llm_for("meeting")`
- 实时对话/函数调用切换
  - 文件：`backend/core/connection.py`
  - 变更：`chat()` 根据 `self.current_mode` 选择 LLM；function_call 路径同样使用所选 LLM
- 意图识别/记忆总结切换
  - 文件：`backend/core/connection.py`
  - 变更：`_initialize_intent()` 和 `_initialize_memory()` 中优先使用 `get_llm_for("intent"/"memory")`
- 其它引用点
  - 文件：`backend/core/handle/peerHandle.py`、`backend/core/handle/helloHandle.py`
  - 变更：统一通过 `get_llm_for("chat")` 获取 LLM
- 配置示例（方式B：多个别名 + llm_by_mode 直切别名）
  - 文件：`backend/data/.config.yaml`
  - 在 `LLM:` 下新增两个别名（同一适配器，不同模型），并在 `llm_by_mode:` 直切别名：
  ```yaml
  LLM:
    ChatGLM_Flashx:
      type: openai
      url: https://open.bigmodel.cn/api/paas/v4/
      model_name: glm-4-flashx-250414
      api_key: <你的key>
    ChatGLM_45:
      type: openai
      url: https://open.bigmodel.cn/api/paas/v4/
      model_name: glm-4.5
      api_key: <你的key>

  llm_by_mode:
    default: ChatGLM_Flashx
    chat:    ChatGLM_Flashx
    meeting: ChatGLM_45
    coding:  ChatGLM_45
    working: ChatGLM_45
    intent:  ChatGLM_Flashx
    memory:  ChatGLM_45
  ```
  - 更新后可通过 `{"type":"server","action":"update_config"}` 热更生效；新会话/下一次用途获取将按新别名实例化。

#### 影响范围与回滚
- 仅涉及 LLM 选择入口；删除 `get_llm_for` 调用并回退至 `conn.llm` 即可恢复。


### 编辑内容48（Meeting 查询接口统一响应与鉴权；推送/终止幂等；finalize 并发幂等与时长修正）
#### 编辑人
- w

#### 新增/修改内容
- Meeting 查询接口统一返回与 CORS
  - 文件：`backend/core/http_server.py`
  - 统一返回结构：成功 `{"success":true,"data":...}`；异常 `{"success":false,"error":"..."}`。
  - `GET /supie/meetings/recent`、`/supie/meetings/{sessionId}`、`/supie/meetings/{sessionId}/transcript` 增加统一 CORS（GET/OPTIONS）。
  - `transcript` 参数校验：`offset>=0`、`1<=limit<=500`，越界时返回空 `items` 且 `total` 保持。

- Meeting 查询接口只读鉴权
  - 文件：`backend/core/http_server.py`
  - 可选 `server.meeting_api_token`：支持 `Authorization: Bearer`、`X-API-Token`、`?token=` 三种传递方式；校验失败返回 401。
  - 仅作用于 `/supie/meetings/*`。

- Transcript 周期推送停止与热更幂等
  - 文件：`backend/core/handle/meeting_handle.py`
  - `stop_meeting_timers()` 二次调用幂等：取消后清空任务引用并置位 `meeting_timers_stopped`。
  - 推送间隔热更只影响"下一周期"：当前周期固定 `meeting_push_interval_ms_current`；推送完成日志打印 `next interval=...ms`。

- Finalize 并发幂等与时长估算修正
  - 文件：`backend/core/handle/meeting_handle.py`
  - 连接级互斥锁 `meeting_finalize_lock`；并发 finalize 时仅首次执行，其余直接重发上次 summary 并加 `idempotent:true`。
  - `duration` 以 `start → max(lastSnippet, now)` 估算，避免 00:00:00 或过短。

#### 待验证内容
- recent/detail/transcript 三接口在无/有 token 下的返回与 CORS 预检通过；错误码与包裹结构符合预期。
- transcript 越界分页返回空 `items` 但 `total` 正确。
- 修改 `meeting.transcript_push_interval_ms` 后，下一周期生效；日志包含 `next interval=...ms`。
- 多次并发 finalize：仅一次生成；其余返回 `idempotent:true`。

#### 影响范围与回滚
- 改动集中在 `http_server.py` 与 `meeting_handle.py`；删除鉴权与包装器、恢复原推送循环读取配置与原 finalize 流程即可回滚。

### 编辑内容49（VAD健壮性修复：_vad_detection_count 初始化）

#### 编辑人
- w

#### 问题与现象
- 日志持续报错：`VAD处理异常: 'ConnectionHandler' object has no attribute '_vad_detection_count'`（包计数递增时重复出现）。

#### 根因
- `backend/core/providers/vad/silero.py::VADProvider.is_vad()` 中，仅在缺少 `client_voice_frame_count` 时同时初始化 `_vad_detection_count`。当连接对象先前已创建过 `client_voice_frame_count`，而未曾创建 `_vad_detection_count`，在后续 `conn._vad_detection_count += 1` 处触发 `AttributeError`。

#### 修复内容（最小变更）
- 文件：`backend/core/providers/vad/silero.py`
- 位置：`is_vad(self, conn, opus_packet)` 初始化帧计数器段落
- 变更：将 `_vad_detection_count` 的初始化从与 `client_voice_frame_count` 绑定改为独立确保存在：

```python
# 初始化帧计数器
if not hasattr(conn, "client_voice_frame_count"):
    conn.client_voice_frame_count = 0
# 确保 _vad_detection_count 一定存在（避免 AttributeError）
if not hasattr(conn, "_vad_detection_count"):
    conn._vad_detection_count = 0
```

#### 影响与验证
- 保持原有行为不变，仅补充健壮性；避免长连接/阶段性状态下出现 `AttributeError`。
- 验证：启动后端并以 WebSocket 推送 OPUS（meeting 模式）；日志不再出现上述异常；VAD 统计与转写链路正常，包计数平稳增长。

#### 回滚
- 还原 `silero.py` 对应编辑即可。

### 编辑内容50（Webhook签名与重试 + 会议索引与分片清理 + Metrics持久化）

#### 编辑人
- w

#### 新增/修改内容
- Webhook 可靠性与来源校验
  - 文件：`backend/core/handle/meeting_handle.py`、`backend/data/.config.yaml`
  - 变更：
    - 在 `_send_webhook()` 中新增签名请求头 `X-Meeting-Signature`，采用 `HMAC-SHA256(secret, body)`，`secret` 由 `.config.yaml -> meeting.webhook.secret` 配置。
    - 明确 5s 超时；保留一次随机退避（2–5s）重试；两次失败仅 `ERROR` 记录，绝不影响纪要下发与存档。
    - 发送体与签名统一基于紧凑 JSON 串，`Content-Type: application/json; charset=utf-8`。
    - 支持可选自定义请求头透传：`.config.yaml -> meeting.webhook.headers`。

- 索引与分片清理策略
  - 文件：`backend/core/handle/meeting_handle.py`
  - 变更：
    - `index.json` 维持"最近100场"后，按索引保留集清理主目录中过期的 `<sessionId>.json`（跳过 `index.json` 与 `active_*.json`）。
    - 清理 `meetings/segments/` 目录下不在保留集的分片文件 `<sessionId>_shard_K.json`。
    - 清理过程容错不阻断。

- Meeting Metrics 持久化
  - 文件：`backend/core/handle/meeting_handle.py`
  - 变更：在 finalize 存档旁路将指标以一行文本追加到 `backend/data/meetings/metrics.log`：
    - 行格式：`[Meeting Metrics] segmentsCount=..., checkpointCount=..., llmElapsedMs=..., emptyBullets=..., bulletsLength=..., industry=..., scenario=...`
    - 同步在主日志打印该行，便于统一观测与测试脚本提取。

#### 待验证内容
- Webhook：配置 `meeting.webhook.url/secret`，触发 finalize；正确收到带 `X-Meeting-Signature` 的请求；5s 超时与单次重试生效；失败不影响业务流程。
- 清理：生成超过100场后，`index.json` 仅保留最新100；旧会主文件与对应分片被清理；活跃态与索引文件不受影响。
- Metrics：`backend/data/meetings/metrics.log` 每次 finalize 追加一行；`test/run_all_tests.py` 能从日志中解析指标。

#### 影响范围与回滚
- 改动集中于 Meeting 存档/通知与配置示例；回滚恢复 `meeting_handle.py` 本次 edits，并移除 `.config.yaml` 中 `meeting.webhook.secret` 示例注释即可。

### 编辑内容51（LLM按模式回退与缓存清理 + Meeting旁路提示 + 广播健壮性）

#### 编辑人
- w

#### 新增/修改内容
- LLM 按模式回退与缓存清理
  - 文件：`backend/core/connection.py`
  - 当 `llm_by_mode` 未配置对应用途时，记录 WARN 并回退到 `default`；当别名未在 `LLM` 配置中命中时记录 WARN 并回退默认 LLM。
  - 连接关闭时清理 `self._llm_cache`；服务端 `update_config` 成功后遍历所有活跃连接清空 `_llm_cache`，避免继续使用旧实例，同时使会议转写推送间隔热更下一周期生效。
  - 文件：`backend/core/websocket_server.py`
  - 在 `update_config()` 末尾追加对现有连接缓存清理的通知逻辑。

- 会议模式"旁路 TTS/LLM"一次性提示
  - 文件：`backend/core/handle/receiveAudioHandle.py`、`backend/core/handle/sendAudioHandle.py`
  - 进入 Meeting 模式后首次触发（任一路径）输出一次日志：`disable_tts`、`disable_chat_on_snippet` 当前生效值，避免重复刷屏（连接级标记 `_meeting_bypass_notice_logged`）。

- meeting.* 广播优化（确认）
  - 文件：`backend/core/handle/meeting_handle.py`
  - 广播函数 `_broadcast_to_others` 使用 `server.get_broadcast_targets(exclude_id)` 已排除发起方；发送异常已捕获并继续，不影响其它目标（无需额外变更）。

#### 待验证内容
- 配置热更：通过 `{"type":"server","action":"update_config"}` 修改 `llm_by_mode` 或 `LLM` 后，新消息按新映射实例化；现有连接不再命中旧缓存；会议转写推送间隔热更在下一周期生效。
- Meeting 旁路提示：切到 `meeting` 模式后日志仅首次打印 `disable_tts/disable_chat_on_snippet`，之后不再重复。
- 广播：`meeting.snippet/summary/transcript` 向其他设备推送，发起方不重复接收；单个发送异常不影响其余设备。

#### 影响范围与回滚
- 改动集中于连接级 LLM 选择与缓存、会议模式提示与服务器热更回调；删除新增日志与缓存清理逻辑即可回滚；功能性行为（旁路/广播）保持原有契约。

### 编辑内容52（Meeting Recent 设备过滤 + Transcript 推送/停止边界确认）

#### 编辑人
- w

#### 新增/修改内容
- `backend/core/http_server.py`
  - `GET /supie/meetings/recent` 增加可选 `deviceId` 过滤参数：`/supie/meetings/recent?limit=10&deviceId=<mac_prefix_or_full>`。
  - 行为：如提供 `deviceId` 则仅返回该设备的会议；支持大小写不敏感的前缀匹配（如前 8 位）；保持统一包装结构不变（`{"success":true,"data":[...]}`）。
  - 细节：跳过 `index.json` 与 `active_*.json` 文件，避免误读与异常。

- `backend/core/handle/meeting_handle.py`（复核，无代码变更）
  - Transcript 周期推送：在会议中按 `meeting.transcript_push_interval_ms`（默认≈12000ms）定期推送，当期固定；推送完成后读取最新配置并打印 `next interval=...ms`，仅下一周期生效。
  - 停止边界：在 `finalize` 或 `mode.end(meeting)` 后调用 `stop_meeting_timers()` 取消推送/小结任务且置位标志，确保不再继续推送。

#### 待验证内容
- 无 `deviceId` 与携带 `deviceId`（前缀/完整）时，`/supie/meetings/recent` 返回的条数与排序正确，包装结构一致。
- 会中每≈12s 收到一次 `meeting.transcript`；`finalize`/退出会议后不再收到周期推送；通过 `update_config` 调整推送间隔仅在下一周期生效（日志含 `next interval=...ms`）。

#### 影响范围与回滚
- 影响 HTTP 查询接口与会议推送观测日志；主链路与存档结构不变。
- 回滚：移除 `recent` 设备过滤逻辑（和跳过文件名判断）即可；推送/停止行为为既有实现，无需回滚。


### 编辑内容54（Finalize 回执与会后停止推流 + 语音口令结束会议 + 握手/日志/健壮性）
#### 编辑人
- w

- 核心改动：
  - finalize 立刻回执同结构确认包 `{"type":"meeting","phase":"finalize"}`，设备可立即显示"总结中…"并停止推流；同时停止会议定时任务与新的 transcript/snippet 推送，避免"结束中仍在增加会中片段"。
  - 最终纪要生成含严格字段：`title/duration/bullets/decisions/actions/risks/nextSteps`，空字段回退空数组；保留幂等复发能力（重复 finalize 复用上次结果）。
  - 增加 finalize 关键日志：开始/完成/耗时，异常回退空骨架 summary 不中断流程。
  - 语音口令直达 finalize：在意图解析前拦截"结束会议/停止录制/开始总结/出个纪要"等关键词（中英），触发 finalize 流程。
  - 模式切换：`mode.start(meeting)` 启动会议定时任务（10–15s 聚合 transcript，支持热更）；`mode.end(meeting)` 等价 finalize，回执确认包并停止会议任务后生成最终 summary。
  - 握手建议：`hello` 回送 `{"type":"hello","transport":"websocket","audio_params":{"sample_rate":16000,"frame_duration":60}}`。
  - VAD 健壮性：在 `silero.py::is_vad()` 独立初始化 `conn._vad_detection_count`，避免 AttributeError。

- 影响范围：
  - `backend/core/handle/textHandle.py`：meeting.finalize 回执与停止推送；mode.start/end(meeting) 任务控制与 finalize 等价；
  - `backend/core/handle/meeting_handle.py`：停止 transcript 推送于 finalize 期间；snippet 在 finalize 后忽略；finalize 日志与状态清理；summary 字段空数组回退；
  - `backend/core/handle/receiveAudioHandle.py`：finalize 期间直接丢弃新音频，避免注入；
  - `backend/core/handle/intentHandler.py`：语音口令映射到 finalize；
  - `backend/core/handle/helloHandle.py`：握手回包补充 `audio_params`；
  - `backend/core/providers/vad/silero.py`：补充 `_vad_detection_count` 初始化。

- 验证：
  - 测试页 `test/ws_meeting.html`：发送若干 `meeting.snippet` → 点击 finalize 或发送 `mode.end(meeting)` → 立刻收到 finalize 回执并看到"总结中…"占位 → 收到 `meeting.summary`，UI 显示纪要；finalize 后不再收到新的 transcript/snippet；语音口令触发 finalize 等价以上流程。

-- 回滚：还原上述文件本次 edits 即可。

8.15

### 编辑内容57（Finalize 立即回执与停止边界 + 七字段稳定输出 + 配置固化）

#### 编辑人
- w

#### 新增/修改内容
- Finalize 立即回执与停止边界（双保险）
  - 文件：`backend/core/handle/textHandle.py`
    - 当收到 `{"type":"meeting","phase":"finalize"}`：
      1) 立即回发同结构确认包（用于设备显示"总结中…"），并打印日志顺序：`finalize request` → `send ack` → `stop timers done`。
      2) 立刻调用 `stop_meeting_timers()` 停止 transcript/小结定时任务，并置位 `meeting_finalizing=true`。
      3) 异步执行 `finalize_meeting_and_send_summary()`（并发幂等）。
    - `mode.end(meeting)` 路径等价上面流程。

- finalize 期间丢弃新片段（W1 双保险）
  - 文件：`backend/core/handle/meeting_handle.py`
    - 在 `handle_meeting_message()` 顶部判断：`meeting_finalizing|meeting_finalized` 时直接回执 `ok` 并忽略新 `snippet/transcript`，避免会后仍新增片段。
    - finalize 完成时将 `meeting_finalizing=false`，并已 `stop_meeting_timers()`。

- Summary 七字段稳定输出与空骨架兜底（校验/上限）
  - 文件：`backend/core/handle/meeting_handle.py`
    - 有片段：`bullets` 去重裁剪（≤6）；`decisions/actions/risks/nextSteps` 各 `≤4`。
    - 无片段：输出空骨架（7字段齐全，`duration` 基于 `start→now`；数组为空）。
    - 并发/重复 finalize：仅首次生成，其余直接复发上次并带 `idempotent:true`。

- 配置固化（防波动）
  - 文件：`backend/data/.config.yaml`
    - 固化：`meeting.disable_tts=true`、`meeting.disable_chat_on_snippet=true`、`meeting.transcript_push_interval_ms=12000`、`meeting.prefer_device_vad=true`、`meeting.threadpool_max_workers=2`。
  - 文件：`backend/core/connection.py`
    - 线程池默认 2，可被 `meeting.threadpool_max_workers` 覆盖。

#### 待验证内容
- 发送 `meeting.finalize`：<100ms 收到确认包；日志连续三行；30s 内无新的 `meeting.transcript` 推送。
- 有片段时 `bullets≥1`，无片段时空骨架（7字段齐全，`duration>0`）；重复 finalize 幂等复发。
- 更新配置后日志出现 `transcript 推送完成，next interval=12000ms`；现有连接缓存已清理（下一周期生效）。

#### 影响范围与回滚
- 影响 meeting 最终化与推送边界；其余模块无改动。
- 回滚：移除 `textHandle.py` 中 finalize 立即回执与停止逻辑、`meeting_handle.py` 的 finalize 期间忽略分支，以及 `.config.yaml` 的固化配置即可。


### 编辑内容58（Meeting 广播/存储/限幅/ACK/Webhook/API守护全面加固）

#### 编辑人
- w

#### 新增/修改内容
- 广播范围限制（默认关闭）
  - 文件：`backend/core/handle/meeting_handle.py`
  - 新增 `meeting.broadcast` 配置：`enabled:false`、`mode: off|group|session`、`allowed_targets: []`
  - 行为：off 不广播；group 仅同前缀（deviceId[:8]）或 allowlist；session 仅 allowlist。

- 存储原子性
  - 文件：`backend/core/handle/meeting_handle.py`
  - 新增 `_safe_write_json()` 与 `_safe_append_line()`；主文件、`index.json`、分片用原子写；`metrics.log` 用安全追加。

- 入口限幅与清洗
  - 文件：`backend/core/handle/meeting_handle.py`
  - 单条 `snippet.text` 2KB 截断（UTF-8 安全）；pending≤200；每连接 `snippet` QPS≥10/s 丢弃并告警。

- finalize 确认包增强
  - 文件：`backend/core/handle/textHandle.py`
  - ACK 增加 `sessionId/startedAt/pendingCount`，便于设备/测试页关联查询。

- Webhook 可观测
  - 文件：`backend/core/handle/meeting_handle.py`
  - 结果计数：`ok|retry_ok|fail`，伴随 `body_len` 与 `body_sha256(8)`，无敏感泄露。

- 查询接口守护
  - 文件：`backend/core/http_server.py`
  - `recent` 支持 `fromTs/toTs` 过滤；为 `/supie/meetings/*` 增加简易每IP QPS 限流（默认 10 QPS），超限返回 429（可通过 `meeting.api_rate_limit` 关闭或调整）。

- 配置补充
  - 文件：`backend/data/.config.yaml`
  - 新增：`meeting.broadcast`、`meeting.api_rate_limit`；维持此前固化项（disable_tts、disable_chat_on_snippet、transcript_push_interval_ms、prefer_device_vad、threadpool_max_workers）。

#### 待验证内容
- 广播：默认 off 时第二设备收不到 `meeting.*`；切到 group 后仅同前缀可见。
- 存储：kill -9 中断后 `index.json`/主文件可解析，无半写；metrics 持续追加。
- 限幅：>2KB 文本被截断；>10/s 片段批次被丢弃并打印告警；finalize 正常。
- ACK：收到 `{"type":"meeting","phase":"finalize","sessionId":...}`，可用该 id 调 `detail/transcript`。
- Webhook：日志出现 `[Meeting Webhook] result=...`；无敏感泄露。
- 守护：鉴权通过且不超限时 200；超限 429；`fromTs/toTs` 过滤条数正确。

### 编辑内容57（旧式 config_update 静默处理 + 短会 duration 更保守）

#### 编辑人
- w

#### 新增/修改内容
- 旧式 config_update 噪声抑制
  - 文件：`backend/core/handle/textHandle.py`
  - 新增对 `type=config_update` 的兼容分支：仅记录提示日志并回发 `{type:"config_update",status:"ok",noop:true}`，不再落入"未知类型"噪声。

- 短会 duration 更保守
  - 文件：`backend/core/handle/meeting_handle.py`
  - 对极短会（start→now 小于阈值）将 `duration_ms` 提升至 `meeting.min_duration_ms`（默认 5000ms），避免初始 display 过短。
  - 配置示例已补充：`backend/data/.config.yaml -> meeting.min_duration_ms: 5000`。

#### 待验证内容
- 向 WS 发送 `{type:"config_update",config:{...}}`：后端回 `{type:"config_update",status:"ok",noop:true}`；不出现未知类型错误日志。
- 仅 1～2 秒的短会 finalize：summary.duration 至少 `00:00:05`（或配置值），常规会议不受影响。


### 编辑内容58（Detail 预览裁剪 + 广播测试可见性说明）

#### 编辑人
- w

#### 新增/修改内容
- Detail 接口预览条数裁剪
  - 文件：`backend/core/http_server.py`
  - `GET /supie/meetings/{sessionId}` 支持 `?preview=N`（1..20，默认5），严格裁剪 `transcriptPreview` 返回条数，避免出现 ≥394 行的预览。

- 广播测试可见性（单端观测）
  - 文件：`backend/core/handle/meeting_handle.py`、`backend/data/.config.yaml`
  - 新增 `meeting.broadcast.include_origin`（默认 false）：开启后发起方也会收到 `meeting.snippet/summary/transcript`，便于单端测试与演示（生产建议关闭）。

#### 待验证内容
- 访问 detail：默认返回预览≤5；`?preview=12` 返回≤12；异常值自动夹紧到 1..20。
- 单端测试：开启 `include_origin:true` 后，当前设备能收到自己的 meeting 广播；关闭后需双端验证。

### 编辑内容59（会议结束时ASR资源清理，防止二次会议未初始化）

#### 编辑人
- w

#### 新增/修改内容
- 会议结束资源清理（ASR reset）
  - 文件：`backend/core/handle/textHandle.py`
  - 在 `meeting.finalize` 与 `mode.end(meeting)` 流程中，除停止会议定时器外，显式调用 `conn.asr.stop_ws_connection()`；若实现了异步 `close()` 则后台触发，确保释放上次会议的 ASR 流式连接与内部状态。

#### 背景与动因
- 现象：第二次进入会议模式时持续推流，但后端日志缺失"正在连接ASR服务…"，无 ASR 交互，导致无识别。
- 根因：上次会议结束后 ASR 流仍持有旧连接/状态，未被重置。

#### 验收
- 连续两次 `mode.start(meeting)`：第二次开始后日志出现"正在连接ASR服务…/发送初始化请求/收到初始化响应"，识别恢复正常。


### 编辑内容62（Meeting 实时性与边界对齐：转写更快 + 设备侧边界回退 + 入会提示音）

#### 编辑人
- w

#### 新增/修改内容
- 转写推送更快（默认 5s，可 3–15s 配置）
  - 文件：`backend/core/handle/meeting_handle.py`
  - 将检查周期改为 0.5s；默认 `transcript_push_interval_ms` 回退为 5000ms；读取配置后夹紧在 3000..15000ms；仍维持"当前周期固定、下一周期热更"。

- 设备侧边界回退与刷新
  - 文件：`backend/core/handle/textHandle.py`、`backend/core/providers/asr/base.py`
  - 记录设备 `listen start/stop` 的最近时间（`_last_listen_event_ms`），`client_listen_mode==manual` 时若超过 `meeting.manual_listen_fallback_ms`（默认 5000ms）未收到边界，则回退使用服务端 VAD 判定有声；收到边界时刷新时间戳。
  - 目的：设备侧未显式发送 start/stop 时，降低静默窗口导致的"识别文本：空"。

- 入会提示音
  - 文件：`backend/core/handle/textHandle.py`
  - 在 `mode.start(meeting)` 路径下发一次 `tts start/stop`，指向 `config/assets/evening.wav` 并带文本"已进入会议模式"，作为后端入会提示（可后续改为本地播放）。

#### 待验证内容
- 转写：会中每约 3–5s 收到一次 `meeting.transcript`（配置下限 3000ms）；日志 `next interval=` 符合热更策略。
- 边界回退：设备未发 listen start/stop 时仍能产生稳定转写；收到边界后段落边界更准确、空文本显著减少。
- 入会提示：进入会议模式时客户端收到一次 `tts start/stop` 指令，播放 `evening.wav` 或本地对应提示音。


### 编辑内容64（Workflow：查询接口 + 指派事件 + 会议导入 + 原子落盘）

#### 编辑人
- w

#### 新增/修改内容
- 只读查询接口（W1）
  - 文件：`backend/core/http_server.py`
  - 新增：GET `/supie/workflow?groupKey=<prefix_or_full>`，返回 `{success:true,data:{items,groupKey}}`；沿用 meeting API 的 token 鉴权与统一 CORS/错误包装。

- "认领/指派"最小事件（W2）
  - 文件：`backend/core/utils/schema.py`
    - 扩展 Workflow schema 支持 `event:"assign"`，字段 `{id:string, owner?:string}`。
  - 文件：`backend/core/handle/workflow_handle.py`
    - 处理 `assign` 为字段级更新，仅修改 `owner`，owner 缺省为发起连接的 `device-id`；分组键取 `groupKey[:8]`。
  - 文件：`backend/core/utils/tasks_store.py`
    - 加载阶段保留未知字段（如 `owner`）。

- 从最近会议导入行动项（W3）
  - 文件：`backend/core/http_server.py`
    - 新增：POST `/supie/workflow/import-from-meeting`（参数：`groupKey` 必填，`sessionId` 可选）；从 `backend/data/meetings/` 读取最近或指定会议，将 `summary.actions/nextSteps` 生成任务并批量 upsert（id 形如 `MEET-<sid>-A1/N1`）。导入后对同组在线设备下发一次 `workflow.update`。

- 落盘原子性（W4）
  - 文件：`backend/core/utils/tasks_store.py`
    - `save()` 改为临时文件 + `os.replace` 原子替换；`load()` 温和校验并保留扩展字段，统一 `groupKey` 长度至 8。

#### 验收要点
- W1：`groupKey` 前缀/全长均返回一致分组快照；结构/类型正确；若启用 `server.meeting_api_token`，401/200 清晰。
- W2：同组多端同时看到 `owner` 字段变化；异组不受影响；非法 `assign` 输入返回 `status:"error"`。
- W3：接口返回 `imported` 数量与示例 `ids`；同组设备收到一次 `workflow.update` 刷新；无 meeting 文件时返回 `success:true,data:{imported:0}`。
- W4：异常中断不产生半写文件，任务文件可正常解析。

### 编辑内容65（Workflow 快照单播 + assign/complete 幂等 + 分组日志与校验 + 文档补齐）

#### 编辑人
- w

#### 新增/修改内容
- 上线/进入工作模式即快照（任务1）
  - 文件：`backend/core/websocket_server.py`、`backend/core/handle/textHandle.py`
  - 行为：
    - 设备注册成功后，按 `device-id[:8]` 分组单播一次 `{"type":"workflow","event":"update"}` 快照；
    - 收到 `{"type":"mode","state":"start","mode":"working"}` 时，同步单播本组快照。

- assign/complete 幂等（任务2）
  - 文件：`backend/core/handle/workflow_handle.py`
  - 行为：
    - `assign`：当 `owner` 已为当前设备时，返回 ok 且不再广播；
    - `complete`：当 `status==done` 时，返回 ok 且不再广播；
    - 日志包含 `idempotent:true` 标记。

- 操作日志与分组校验（任务3）
  - 文件：`backend/core/handle/workflow_handle.py`
  - 日志：统一输出 `[Workflow] op=assign|complete id=.. group=.. by=<device>`；幂等路径追加 `idempotent:true`。
  - 校验：当 `update` 携带与连接默认分组不同的 `task.groupKey` 且未提供顶层 `groupKey` 覆写时，拒绝更新并记录 `forbidden_group_override`。

- 文档补齐（任务4）
  - 文件：`hardwareProtocol.md`
  - 新增 2.9 章：`GET /supie/workflow`、`POST /supie/workflow/import-from-meeting`、WS `assign/complete` 载荷示例与鉴权说明；说明"注册成功/进入工作模式即单播快照"。

#### 验收要点
- 设备重连或进入工作模式后，无需手工拉取即可收到 `workflow.update`；
- 重复 `assign(owner==self)`/`complete(status==done)` 无抖动、日志含 `idempotent:true`；
- 非法跨组 `update` 被拒绝并有日志；
- 文档可指导硬件调用 REST/WS 接口并理解鉴权与分组行为。

### 编辑内容66（Workflow：快照单播 + 幂等与越权保护 + 操作日志 + 验收）
#### 编辑人
- w

#### 新增/修改内容
- 快照单播（W1）
  - 文件：`backend/core/websocket_server.py`、`backend/core/handle/textHandle.py`
  - 行为：
    - 设备注册成功后，按分组（`device-id[:8]`）单播一次 `{"type":"workflow","event":"update","tasks":[...]}` 快照（日志：`[Workflow] op=snapshot_on_register group=.. to=.. count=N`）。
    - 收到 `{"type":"mode","state":"start","mode":"working"}` 时，同步单播当前分组快照（日志：`[Workflow] op=snapshot_on_mode_start ...`）。

- 幂等与越权保护（W2）
  - 文件：`backend/core/handle/workflow_handle.py`
  - 行为：
    - `assign`：若 `owner==当前设备` 则幂等返回 `status:"ok", idempotent:true`，不再广播。
    - `complete`：若任务已 `status==done` 则幂等返回，不广播。
    - `update`：支持字段级合并；当 `task.groupKey` 与连接默认分组不同且未提供顶层 `groupKey` 覆写时，拒绝并记录 `forbidden_group_override`，防止跨组越权。
    - 回发与广播：当前连接仅接收本组快照；其他在线设备按各自分组构造负载并单播，避免跨组泄露。

- 操作日志（W3）
  - 统一输出：`[Workflow] op=assign|complete id=.. group=.. by=<device>`；幂等路径追加 `idempotent:true` 标记，便于测试断言。

#### 验收要点（W4）
- 断开→重连：注册成功后设备立即收到一次 `workflow.update` 全量快照。
- 幂等操作：重复 `assign(owner==me)` / `complete(status==done)` 返回 `status:"ok"`，无二次广播；日志含 `idempotent:true`。
- 分组隔离：不同分组设备不受他组 `update/assign/complete` 影响；越权 `update` 记录 `forbidden_group_override`。

#### 影响范围与回滚
- 范围：仅 `websocket_server/textHandle/workflow_handle` 逻辑及日志；协议字段不变。
- 回滚：移除注册/working-start 快照单播；还原 `workflow_handle.py` 的幂等与分组校验分支即可。


### 编辑内容67（工作模式联动与回显抑制 + Workflow 拉取契约 + Peer→Workflow 联动）
#### 编辑人
- w

#### 新增/修改内容
- 模式切换语句的回显与 TTS 抑制（后端）
  - 文件：`backend/core/handle/textHandle.py`
  - 行为：在 `listen.detect` 收到文本后，若匹配"进入工作模式/工作模式/workflow mode/working mode/切到工作模式/切换到工作模式"等关键词：
    - 下发带意图的 STT：`{"type":"stt","text":"进入工作模式","intent":"mode_switch","target_mode":"working"}`；
    - 不再触发对话回显与 TTS；
    - 仅下发模式确认并切换：`{"type":"mode","status":"ok","state":"start","phase":"start","mode":"working"}`；同时按分组单播一次 `workflow.update` 快照（沿用编辑内容65的实现）。

- Workflow 列表拉取契约
  - 文件：`backend/core/utils/schema.py`、`backend/core/handle/workflow_handle.py`
  - 行为：
    - 支持显式 `event:"list"`；
    - 兼容"空 tasks 的 update"触发拉取：`{"type":"workflow","event":"update","tasks":[]}`；
    - 两者均回发：`{"type":"workflow","event":"update","tasks":[...]}`（本组快照）。

- Assign 认领回执显式幂等标注（已实现沿用）
  - 文件：`backend/core/handle/workflow_handle.py`
  - 行为：当 `owner==当前设备` 时返回 `{...,"status":"ok","idempotent":true}`，不广播。

- Peer→Workflow 联动（可选）
  - 文件：`backend/core/handle/peerHandle.py`
  - 行为：当配置 `peer_task_to_workflow=true` 且 `peer` 的 `category=="task"` 时：
    - 解析 `normalized`：生成/合并任务到目标设备分组（`device-id[:8]`），默认 `owner=目标设备`；
    - 单播该目标设备最新 `workflow.update` 快照；
    - 对 `assignees` 可选过滤，仅对匹配目标生效；离线目标不阻断原 peer 路径（仍入离线队列）。

#### 验收要点
- 语音触发"进入工作模式"后：只收到带意图的 STT 与 `mode.start(working)` 确认，不再出现对话回显与 TTS；界面停留在工作模式。
- 列表拉取：发送 `update(tasks:[])` 或 `list` 都能回发当前分组的 `workflow.update`；
- 认领：重复 `assign(owner==me)` 幂等返回，含 `idempotent:true`；
- Peer→Workflow（开启开关时）：发往目标的任务能在目标设备工作模式中出现，且为其所有。

#### 影响范围与回滚
- 范围：`textHandle/schema/workflow_handle/peerHandle`；主链路稳定。
- 回滚：移除模式切换关键字分支与 `list` 事件处理；关闭 `peer_task_to_workflow` 即可恢复纯 peer 行为。

### 编辑内容68（工作模式稳定性 + 指令直达 + 心跳与去抖 + 快照契约）

#### 编辑人
- w

#### 新增/修改内容
- 保持连接与双通道过渡（任务1）
  - 文件：`backend/core/websocket_server.py`
  - 变更：重复设备ID重连时不立即断开旧连接，先提示并延迟≈1.5秒关闭旧通道（双通道过渡≤2s），避免语音听写中断；启用 ping/pong 保活（ping_interval=20, ping_timeout=50, close_timeout=5），容忍1-2次心跳丢失。

- hello 幂等与快照推送（任务1）
  - 文件：`backend/core/handle/helloHandle.py`
  - 行为：同连接多次 hello 不重置会话/订阅；每次 hello 后按 `device-id[:8]` 单播一次 `workflow.update` 当前分组快照。

- 工作模式静音 + 直达口令（任务1/2）
  - 文件：`backend/core/handle/textHandle.py`
  - 变更：
    - 模式切换语句命中仅发送 `{"type":"mode","status":"ok","state":"start","mode":"working"}` 确认，不下发 TTS 回显；随后按分组单播一次 `workflow.update` 快照（已有实现保留）。
    - `listen start/stop` 最小 300ms 去抖，降低边界抖动。
    - 语音指令直达（工作模式）：在 `listen.detect` 命中关键短语时直接执行并回包轻量意图（可忽略 UI）：
      - 认领：认领任务/领取任务/我来做/assign to me/claim task → 选择最近可操作任务调用 `workflow.assign`（含幂等）。
      - 完成：完成任务/标记完成/做完了/mark done/complete task → 选择最近 open 任务调用 `workflow.complete`（含幂等）。
      - 刷新：刷新列表/刷新任务/拉取任务/refresh/pull/update list → 立即回发 `workflow.update` 快照。

- 列表拉取契约（任务1）
  - 兼容 `{"type":"workflow","event":"update","tasks":[]}` 视为拉取，回发当前分组快照（此前在 `workflow_handle.py` 已实现；本次语音"刷新"复用该行为）。

#### 验收要点
- 不断线进入工作模式：收到 `mode.ok` 后立即收到非空 `workflow.update`。
- 连续多次"进入工作模式"：连接稳定（或平滑重建），无听写中断；无 TTS 回显导致的聊天态回退。
- 说"认领任务/完成任务/刷新列表"：后端直接执行并返回幂等回执，随后本组收到更新后的 `workflow.update`；重复操作返回 `idempotent:true`。
- 心跳：临时网络抖动下不误断；listen start/stop 抖动被抑制。

#### 影响范围与回滚
- 改动集中于 `websocket_server/helloHandle/textHandle`；协议字段与 `workflow_handle` 保持兼容。
- 回滚：移除双通道过渡与 keepalive 参数；删除直达口令与去抖分支即可恢复原行为。


### 编辑内容69（编码模式：LLM 洞察/总结 + 日志异步与截断防阻塞）

#### 编辑人
- w

#### 新增/修改内容
- 编码模式智能处理（coding.insight / coding.summary）
  - 文件：`backend/core/handle/coding_handle.py`
  - 变更：
    - 引入日志缓冲与截断：连接级 `coding_logs_buffer`（默认最多 200 行，尾部保留），单条日志截断至 ≤512 字符。
    - 生成洞察：在 `log/step/phase` 后去抖（默认 1200ms）触发 LLM 洞察，事件 `{"type":"coding","event":"insight"}`；字段：`phase/insights/risks/actions/nextSteps`。
    - 生成总结：在 `stop` 后立即触发一次最终总结，事件 `{"type":"coding","event":"summary"}`；字段同上。
    - LLM 选择：通过 `conn.get_llm_for("coding")` 选择用途对应模型；非 JSON 输出括号截取降级与启发式兜底。
    - 限幅与去重：`insights≤5`，`risks≤4`，`actions/nextSteps≤6`，保序去重。
    - 广播：`insight/summary` 单播给当前连接并广播给其他在线设备（带 `from`）。

- Schema 扩展
  - 文件：`backend/core/utils/schema.py`
  - 变更：为 `coding` 新增事件 `insight|summary`，并固化输出字段：`phase/insights/risks/actions/nextSteps`（字符串数组）。

- 日志异步与诊断收敛（防 BlockingIOError）
  - 文件：`backend/config/logger.py`
  - 变更：
    - 控制台与文件输出均启用 `enqueue: true`（异步队列），降低 I/O 阻塞风险；
    - 关闭 `backtrace/diagnose`（控制台与文件），减少深栈诊断开销；
    - 配合编码日志截断，避免长文本导致 BlockingIOError/阻塞。

- 可选配置（`.config.yaml`，缺省值已内置）
  - 路径：`coding.*`
  - 示例：
    ```yaml
    coding:
      insight_enabled: true           # 开关（默认 true）
      insight_debounce_ms: 1200       # 去抖间隔（ms）
      per_message_max_len: 512        # 单条日志最大长度
      history_max_lines: 200          # 本地缓冲最大行数
      insight_max_chars: 1600         # 拼接给 LLM 的总字符上限
      insight_max_items: 5            # insights 最多条目数
      summary_max_items: 6            # summary 各字段上限
    ```

#### 待验证内容
- 洞察：依次发送 `phase(build)` 与若干 `log/step`，约 1.2s 后收到一次 `coding.insight`；字段条数在限幅内。
- 总结：发送 `stop` 后收到 `coding.summary`（含 `phase/insights/risks/actions/nextSteps`）；第二设备能收到广播（`from=<发起设备>`）。
- 稳健：超长 `log.text` 被截断；持续高频日志无 `BlockingIOError`；控制台/文件日志不阻塞主流程。

#### 影响范围与回滚
- 影响范围：`coding_handle/schema/logger`；与 meeting/workflow/peer 主链路无冲突。
- 回滚：
  - 移除 `coding_handle.py` 中 `insight/summary`、缓冲与截断相关 edits；
  - 还原 `schema.py` 对 `coding` 的事件与字段；
  - 还原 `logger.py` 的 enqueue/backtrace/diagnose 配置。


### 编辑内容70（闲置关闭策略放宽 + Keepalive 支持 + 模式区分 + 预关闭缓冲）

#### 编辑人
- w

#### 新增/修改内容
- 放宽闲置阈值
  - 文件：`backend/core/connection.py`
  - 变更：`timeout_seconds` 基于 `close_connection_no_voice_time` 的默认值从 120 提升为 600，再加 60 秒兜底（共 660s）；可被配置覆盖。

- Keepalive/心跳
  - 文件：`backend/core/connection.py`
  - 变更：在 `_route_message` 中接受 `{"type":"ping"|"keepalive"}` 的轻量包，重置超时计时并可选回 `pong`，避免无声时被动断开。

- 无声关闭（第一层）模式区分与预警缓冲
  - 文件：`backend/core/handle/receiveAudioHandle.py`
  - 变更：
    - 默认无声阈值提升至 600s；在 `meeting/working` 模式下将阈值放大 3 倍；
    - 关闭前预警：在达到阈值前 `grace_seconds`（默认 15s，可 5..30 配置）发送一次"即将结束对话"提示；
    - 若期间恢复活动（任意语音/消息），自动清理预警标志并取消关闭。

- 超时兜底（第二层）预关闭缓冲
  - 文件：`backend/core/connection.py`
  - 变更：`_check_timeout` 在关闭前先发送一次 `system.timeout_warning`，并等待 10 秒缓冲，期间收到任何消息（`reset_timeout`）即取消本轮关闭。

- TTS 收尾与关闭协调
  - 文件：`backend/core/handle/sendAudioHandle.py`
  - 变更：在最后一句 `SentenceType.LAST` 后，如需关闭连接，微延迟 50ms 再 `close()`，避免与末尾消息竞争。

#### 待验证内容
- 普通对话：无后续语音 10 分钟内不断开；15 秒前收到"即将结束"提示；随后若仍无活动，收到结束语并关闭。
- 会议/工作模式：长时间无声不被轻易关闭（阈值≥30 分钟）；任意活动清理预警并续期。
- Keepalive：前端/硬件周期发送 `{"type":"ping"}` 时连接不超时，偶发抖动不影响。
- 兜底：`system.timeout_warning` 后 10 秒内发送任意消息可取消关闭。

#### 影响范围与回滚
- 影响范围：`receiveAudioHandle/connection/sendAudioHandle`；与语音/会议/工作主链路兼容。
- 回滚：还原上述 3 个文件 edits；`close_connection_no_voice_time` 回退至 120 即可恢复旧策略。


### 编辑内容71（Coding 洞察质量提升 + 事件化 Prompt + 风险/行动/下一步补全 + 日志截断防阻塞）

#### 编辑人
- w

#### 新增/修改内容
- 洞察质量优化（refined insights，而非原始日志回显）与事件化 Prompt
  - 文件：`backend/core/handle/coding_handle.py`
  - 变更：
    - System/User 提示强化：严格禁止回显原始日志，仅输出提炼后的 `insights/risks/actions/nextSteps` 纯 JSON；
    - 事件化上下文：记录最近 `log/step/phase` 事件并注入 `lastEvent`；
    - 上下文统计注入：汇入 `errorCount/warnCount/lastStep/buildSuccess/buildRunning/testsFailed`，提升模型可控性；
    - 启发式兜底：当 LLM 返回空或弱时，基于最近 `error/warn/step/build` 行生成高质量摘要与建议；
    - 字段补全：为空时自动补全 `risks/actions/nextSteps` 的最小可用建议，并做去重与限幅。

- 日志异步与长串截断（防 BlockingIOError）
  - 文件：`backend/config/logger.py`
  - 变更：
    - 为控制台与文件 sink 增加 `patcher` 截断器（默认 `max_message_length=2000`，可配置 `log.max_message_length`）；
    - 继续保留 `enqueue=True`、关闭 `backtrace/diagnose`，进一步降低阻塞与诊断开销。

#### 待验证内容
- 洞察：`coding.insight` 的 `insights` 不再是原始日志，而是提炼短句；`risks/actions/nextSteps` 不为空且条数在限幅内；
- 总结：`coding.summary` 在 `stop` 后包含上述四字段且内容合理；
- 日志：长日志/异常栈被安全截断，`BlockingIOError` 不再出现；高并发写入不阻塞主流程。

#### 影响范围与回滚
- 影响范围：`coding_handle/logger`；与 meeting/workflow/peer 主链路兼容。
- 回滚：还原 `coding_handle.py` 中提示与兜底逻辑；移除 `logger.py` 中 `patcher` 配置即可。


### 编辑内容72（工作流模式交互修复）
#### 编辑人
- w

#### 新增/修改内容
- **工作流模式语音交互修复**
  - 文件：`backend/core/handle/receiveAudioHandle.py`
  - **问题**：在工作流模式（`working`）下，语音输入被错误地拦截，导致设备无法与后端进行任何后续交互，造成功能死锁。
  - **修复**：移除了在 `startToChat` 函数中对 `working` 模式的特殊处理逻辑。现在，只有 `meeting` 模式会旁路标准的对话流程，而 `working` 模式下的语音输入将正确地进入意图识别和指令处理环节，恢复了其交互能力。
- **工作模式交互与连接稳定性增强**
  - 文件: `backend/core/handle/textHandle.py`, `backend/core/connection.py`
  - **问题**: 进入工作模式后，设备不会主动开始拾音，导致交互中断；同时，后端空闲断开策略过于严苛。
  - **修复**:
    - **主动拾音**: 服务端在收到 `mode.start(working)` 后，主动下发 `listen start` 指令，确保设备立即进入聆听状态。
    - **连接保持**: 增加了对 `ping/keepalive` 心跳消息的处理，收到后会重置空闲超时计时器，防止正常停顿被误判为掉线。
- **VAD 静默日志修正**
  - 文件: `backend/core/providers/vad/silero.py`
  - **问题**: VAD 静默日志打印的是原始时间戳，而非实际的静默时长，不利于问题诊断。
  - **修复**: 修正了日志逻辑，现在可以正确计算并打印静默时长（`now_ms - silence_start_ms`），确保了日志的准确性。

#### 验收要点
- 进入工作流模式后，后续的语音指令（如"刷新列表"、"认领任务"）能够被后端正确处理并执行相应操作。
- 会议模式（`meeting`）的行为不受影响，继续保持其原有的转写和总结功能。
- 设备在工作模式下能够保持长时间连接，不会因为短暂的静默而被断开。
- VAD 日志能够准确反映静默时长。

#### 影响范围与回滚
- 影响范围：仅修复 `working` 模式下的语音处理逻辑，对其他模式无影响。
- 回滚：在 `receiveAudioHandle.py` 的 `startToChat` 函数中恢复对 `working` 模式的判断逻辑即可。


### 编辑内容73（Workflow 跨组更新支持 + 分组广播收敛）

#### 编辑人
- w

#### 新增/修改内容
- 跨组更新（task.groupKey 覆写）
  - 文件：`backend/core/handle/workflow_handle.py`
  - 变更：
    - `update` 事件逐条处理任务：目标分组优先级 `task.groupKey` > 顶层 `groupKey` > 发送者默认组（device-id[:8]）。
    - 允许跨组 upsert：当任务内包含 `groupKey` 时按目标组更新存储，不再拒绝跨组写入。
    - 记录受影响分组集 `changed_groups`，供后续精准广播使用。
- 广播收敛到受影响分组
  - 文件：`backend/core/handle/workflow_handle.py`
  - 变更：
    - 仅向 `changed_groups` 内的在线设备广播 `workflow.update`，避免无关分组刷新。
    - 向发起方回发其所属组快照，保证本端视图一致。

#### 待验证内容
- 在 001 组发送：`{type:'workflow',event:'update',tasks:[{id:'t1',title:'派发到硬件',groupKey:'94:a9:90:'}]}`
  - 硬件（组 `94:a9:90:`）应收到包含 `t1` 的 `workflow.update`；001 页面仅看到自身组快照。
- 顶层 `groupKey`：提供 `groupKey:'94:a9:90:'` 时，未携带 `task.groupKey` 的任务落入该组并广播到该组。
- 非相关组：不在 `changed_groups` 的在线设备不刷新。

#### 影响范围与回滚
- 影响范围：仅 `workflow_handle`；与 meeting/coding/peer 主链路无耦合。
- 回滚：恢复跨组拦截并回到全量广播即可。


### 编辑内容74（LLM 洞察再优化 + Logger 异步与全链路截断）

#### 编辑人
- w

#### 新增/修改内容
- LLM 洞察再优化（coding）
  - 文件：`backend/core/handle/coding_handle.py`
  - 变更：
    - 注入 `lastEvent`（最近 log/step/phase）事件化引导，洞察更聚焦；
    - 信号抽取 `_extract_signals`：failed tests / import errors / OOM / timeouts / network / build errors / lint warnings；
    - 基于信号生成更具体的 `risks/actions/nextSteps`，保持去重与限幅；
    - 严格禁止回显原始日志，仅输出精炼 JSON。
- Logger 异步与截断强化
  - 文件：`backend/config/logger.py`、`backend/core/handle/textHandle.py`
  - 变更：
    - 所有 add() 均强制 `enqueue=True`（控制台与文件），避免 BlockingIOError；
    - 新增 `truncate_for_log()` 工具；在 `textHandle.py` 关键入口对入站 JSON/文本截断后再写日志，消除长串写入风险。

#### 待验证内容
- coding.insight：insights 为精炼短句；risks/actions/nextSteps 具体可执行，且条数在限幅内；
- 日志：高并发/长文本下无 BlockingIOError，控制台/文件输出流畅；
- 关键入口（listen/meeting/coding/workflow/server）日志均被安全截断。

#### 影响范围与回滚
- 影响范围：`coding_handle/logger/textHandle`；与 meeting/workflow/peer 主链路兼容。
- 回滚：移除 `lastEvent/信号抽取` 与日志截断调用；Logger 恢复原同步/诊断配置即可。

### 编辑内容75（工作模式首轮后续失联修复：进入即拾音 + 快照去抖 + 超时/心跳与VAD确认）
#### 编辑人
- w

#### 新增/修改内容
- 进入工作模式即开启拾音（manual）
  - 文件：`backend/core/handle/textHandle.py`
  - 行为：收到 `{"type":"mode","state":"start","mode":"working"}` 后，立即下发 `{"type":"listen","state":"start","mode":"manual"}`，并在连接侧设置 `client_listen_mode=manual` 与刷新 `_last_listen_event_ms`，确保切到工作模式即可继续语音交互（避免"只能说一次"）。

- 工作流首屏快照去抖
  - 文件：`backend/core/handle/textHandle.py`
  - 行为：`mode.start(working)` 触发的 `workflow.update` 快照增加 1.5s 去抖，避免与"注册成功/hello 后快照"在极短时间内重复推送造成界面抖动。

- 空闲断开与心跳、VAD 静默时长（确认）
  - 文件：`backend/core/connection.py`、`backend/core/handle/receiveAudioHandle.py`、`backend/core/providers/vad/silero.py`
  - 结论：此前已落地
    - 无声阈值默认≥600s，会议/工作模式×3 放宽；超时检查前先下发 `timeout_warning` 并留 10s 缓冲，收到任意消息会 `reset_timeout` 取消本轮关闭；
    - 文本层与底层路由均接受 `ping/keepalive` 并可选回 `pong`；
    - VAD 静默时长日志计算按 `now_ms - silence_start_ms`，异常已修复。

#### 待验证内容
- 设备或测试页发送：`{"type":"mode","state":"start","mode":"working"}` 后：
  - 立刻收到 `listen.start(manual)`；随后 1.5s 内收到一次 `workflow.update`（如有任务）。
  - 工作模式下继续语音指令（刷新/认领/完成）均能被正确处理，无"只能交互一次"的现象。
  - 空闲期内周期发送 `{"type":"ping"}` 不会被断开；VAD 日志静默时长数值正确。

#### 影响范围与回滚
- 影响范围：仅 `textHandle` 中工作模式进入行为与工作流快照触发；其余模块为既有行为确认。
- 回滚：移除 `mode.start(working)` 分支内的 `listen.start(manual)` 与 1.5s 去抖逻辑即可。

### 编辑内容76（Coding 智能洞察集成 + 日志系统加固）

#### 编辑人
- w

#### 新增/修改内容
- Coding 智能洞察与总结
  - 文件：`backend/core/handle/coding_handle.py`
  - 行为：
    - 在 `event in {log, step, phase}` 时将文本归一化（压缩换行/空白，去除代码栅栏），并按配置 `coding.per_message_max_len` 截断后进入本地缓冲 `coding_logs_buffer`（尾部保留，默认≤200行）。
    - 错误级别或超长日志触发"立即"去抖的洞察任务，其余场景按 `coding.insight_debounce_ms`（默认≈1200ms）去抖触发。
    - 通过 `conn.get_llm_for("coding")` 选择用途模型进行提炼；非 JSON 输出采用括号截取降级；空结果基于启发式信号生成最小可用 `insights/risks/actions/nextSteps`。
    - 输出事件：`{type:"coding", event:"insight"|"summary", phase, insights[], risks[], actions[], nextSteps[], from}`；`stop` 时自动生成一次 `summary`。

- 文本长度与输入预处理（防爆日志/LLM）
  - 对 `log.text/step.name/phase.name` 进行 `_normalize_incoming_text()`（压缩换行/空白，去除 ```...``` 栅栏与多余反引号）+ `_truncate_text()` 截断保护。
  - LLM 输入拼接前再次限幅 `coding.insight_max_chars`（默认≈1600 字符）。

- 结构化日志与噪声抑制
  - 文件：`backend/core/handle/coding_handle.py`
  - 新增洞察日志行（结构化统计）：仅输出 `final/phase/len(insights|risks|actions|nextSteps)` 与 `jsonSHA`（摘要哈希），不直写完整 JSON，避免刷屏与阻塞。

- Loguru 截断补丁（Handler #3）
  - 文件：`backend/config/logger.py`
  - 对控制台与文件 sink 均启用 `patcher=_build_trunc_patcher()`，按 `log.max_message_length`（默认2000）对过长消息进行"头尾保留+中间省略"截断，降低阻塞与 `BlockingIOError` 风险。

#### 待验证内容
- 触发洞察：连续发送 `coding.log/step/phase`，约 1.2s 内收到一次 `coding.insight`；`error/traceback/失败` 或超长日志时更快触发（immediate）。
- 总结：发送 `stop` 后收到一次 `coding.summary`，字段齐全、条数在限幅内（insights≤5，risks≤4，actions/nextSteps≤6）。
- 日志：控制台/文件日志无超长 JSON 刷屏；出现 `[Coding Insight] final=... insights=... jsonSHA=...` 统计行；无 `BlockingIOError`。

#### 影响范围与回滚
- 影响范围：`coding_handle` 与 `logger` 截断参数，对 meeting/workflow/peer 主链路无侵入。
- 回滚：移除 `coding_handle.py` 中归一化/洞察/统计日志相关 edits；`logger.py` 去掉 `patcher=_build_trunc_patcher()` 即可。

### 编辑内容77（Peer→Workflow 联动 + Workflow 只读接口 + 工作模式TTS抑制）

#### 编辑人
- w

#### 新增/修改内容
- Peer→Workflow 联动
  - 文件：`backend/core/handle/peerHandle.py`
  - 行为：当配置 `peer_task_to_workflow: true` 且 `peer` 结构化 `category=="task"` 时：
    - 将任务写入目标设备分组（groupKey=目标 device-id 前8位），`owner=目标设备`，支持 `normalized.id/priority/status/assignees`；
    - 如果 `assignees` 提供，仅对匹配目标生效；
    - 对每个目标设备单播一次该组最新 `workflow.update` 快照。

- Workflow 只读接口（HTTP，统一鉴权/限流包装）
  - 文件：`backend/core/http_server.py`
  - 路由：
    - `GET /supie/workflow?groupKey=<prefix_or_full>`：返回 `{items, groupKey}`。
    - `POST /supie/workflow/import-from-meeting`：从最近/指定会议导入 `actions/nextSteps` 为任务，落入 `groupKey` 分组，并向同组在线设备广播一次 `workflow.update`。

- 工作模式期间 TTS 抑制（兼容占位）
  - 文件：`backend/core/handle/sendAudioHandle.py`
  - 行为：`current_mode=="working"` 且 `working.disable_tts:true` 时仅下发 `tts start/stop` 占位，不发音频帧；与设备端抑制策略对齐。

- 配置补充
  - 文件：`backend/data/.config.yaml`
  - 新增：`peer.peer_task_to_workflow:true`、`working.disable_tts:true`。

- Coding 洞察触发与日志加固（补充）
  - 文件：`backend/core/handle/coding_handle.py`、`backend/config/logger.py`
  - 行为：
    - `phase/step` 事件即时触发一次 LLM 洞察；`log` 保持按 `coding.insight_debounce_ms` 去抖；仅在非空时回发 `coding.insight` 结构化摘要。
    - 日志统一异步输出并在 sink 层做长度截断；洞察日志仅输出统计（条数与哈希），不直写完整 JSON，避免阻塞。

#### 待验证内容
- Peer→Workflow：发送 `peer`（category:"task"）到在线/离线目标，在线端收到 `workflow.update` 快照；离线入队后上线补投不影响本联动。
- Workflow 查询：`GET /supie/workflow?groupKey=xxxx` 返回当前组快照；`import-from-meeting` 返回 `imported/ids` 并广播快照。
- 工作模式TTS：工作模式对话仅看到 `tts start/stop` 占位，不播放语音（设备端与后端行为一致）。

#### 影响范围与回滚
- 影响范围：`peerHandle/http_server/sendAudioHandle` 与配置；对 meeting/coding 主链路无侵入。
- 回滚：移除 `peerHandle.py` 联动分支；删除两个 HTTP 路由；注释 `sendAudioHandle.py` 中 working 抑制分支；配置去掉新增项。

### 编辑内容78（编码洞察去抖与结构化广播 + 日志截断防阻塞 + JWT/OAuth2 鉴权 + Peer ACL 细化 + 离线消息 SQLite + 资源生命周期）

#### 编辑人
- w

#### 新增/修改内容
- 编码模式 LLM 摘要与短回执（任务1）
  - 文件：`backend/core/handle/coding_handle.py`
  - 变更：
    - 不再回显原始 `log/step/phase` 文本，仅回 `{status:"ok"}`；文本进入连接级缓冲，按 `coding.insight_debounce_ms`（默认≈1200ms）去抖触发 LLM 洞察。
    - 生成并仅广播结构化结果：`coding.insight/coding.summary`，字段 `phase/insights/risks/actions/nextSteps`，并注入 `lastEvent` 与统计提示；条数限幅：`insights≤5、risks≤4、actions/nextSteps≤6`。
    - 统计日志行：`[Coding Insight] final=.. insights=.. risks=.. actions=.. nextSteps=.. jsonSHA=.. elapsedMs=..`，避免长 JSON 刷屏。

- Loguru BlockingIOError 修复（任务2）
  - 文件：`backend/config/logger.py`（既有实现确认，无本次代码变更）
  - 结论：保留 `enqueue=True`、`rotation=10MB`、`retention=30 days` 与全局截断 patch；本次在编码洞察处仅输出统计行，进一步抑制超长日志。

- 权限与风控（任务3）
  - 文件：`backend/core/auth.py`
  - 新增：JWT/OAuth2 校验（`server.auth.mode: jwt|oauth2|mixed`），支持 `jwt.{secret|public_key|algorithms|audience|issuer|sub_prefix}` 与 `oauth2.introspection_url/client_id/client_secret`；保留静态 token 回退与设备白名单（小写）。
  - 文件：`backend/core/handle/peerHandle.py`
  - 增强 ACL：支持 `device_roles/roles_grants/group_rules`；目标数上限 `max_targets`；广播频控改为“每设备每分钟≤N”（默认6）。

- 离线消息持久化升级（任务4）
  - 新增：`backend/core/utils/offline_store_sqlite.py`（SQLite 存储）表结构：`offline_queue(device_id TEXT, payload TEXT, queued_at INTEGER, ttl_ms INTEGER)`，含索引。
  - 改造：`backend/core/utils/offline_queue.py` 优先写入/读取 SQLite，失败回退 JSON 文件；每设备最多保留 100 条，TTL 过期丢弃。

- 资源生命周期统一管理（任务5）
  - 文件：`backend/core/connection.py`
  - 变更：`close()` 取消 `timeout_task` 与 `coding_insight_task`；优雅关闭 `asr/tts/llm`（如实现 `close()`）；线程池 `shutdown(cancel_futures=True)`。

- 观测与指标（任务6）
  - 文件：`backend/core/handle/coding_handle.py`
  - 变更：洞察耗时 `elapsedMs` 写入统计行；便于计算 P50/P95 与错误率。

#### 验收要点
- 连续 `coding.log/step/phase`：P95 首条 `insight` 延迟 ≤ 1.2s；insights/risks/actions/nextSteps 数量在限幅内；广播仅发送结构化结果。
- 发送 `stop`：≤2s 收到一次 `coding.summary`。
- 超长文本：服务端日志无原文刷屏，回执仅 `{status:"ok"}`。
- 10 分钟压测：无 BlockingIOError；日志轮转 10MB；单条日志长度 ≤ `log.max_message_length`（默认 2000）。
- 鉴权：未授权 401/403；越权目标拦截并回执错误码。
- 离线队列：50 QPS 并发入出队无丢失，重启不丢数据。
- 资源：连续 100 次连接抖动，线程/句柄不增长。

#### 影响范围与回滚
- 影响 `coding_handle/auth/peerHandle/offline_queue/connection`；与 ASR/TTS 业务链路兼容。
- 回滚：移除上述文件新增 edits，`offline_queue` 回退 JSON 即可。


### 编辑内容79（Coding 提示词强化 + LLM 单例复用 + Meeting finalize 互斥幂等 + 日志与清理确认）

#### 编辑人
- w

#### 新增/修改内容
- Coding 提示词强化（任务1）
  - 文件：`backend/core/handle/coding_handle.py`
  - 变更：重写 `system_prompt`，严格“仅输出 JSON、无代码栅栏/说明文本、固定四键 {insights,risks,actions,nextSteps}、语言保持一致、短句去重限幅”，明确禁止回显原始日志/栈；解析仍保留“括号截取 + json.loads + 键兜底”。

- LLM 单例化与复用（任务2）
  - 文件：`backend/core/websocket_server.py`
  - 新增：`self.llm_registry: Dict[str,Any]` 与 `get_or_create_llm(alias, overrides)`；以 `alias+overrides` 指纹共享实例，避免多进程/多连接重复 new。
  - 文件：`backend/core/connection.py`
  - 变更：`get_llm_for(purpose)` 优先走 `server.get_or_create_llm` 复用共享实例；仅在无共享能力时本地合并 overrides 创建；默认 alias 且无 overrides 时直接复用 `self.llm`。
  - 说明：`_initialize_memory/_initialize_intent` 已通过 `get_llm_for('memory'|'intent')` 选用用途模型，间接复用共享实例。

- Meeting finalize 并发互斥与幂等（任务3）
  - 文件：`backend/core/handle/meeting_handle.py`
  - 变更：确保连接级互斥锁 `meeting_finalize_lock = asyncio.Lock()`；并发 finalize 仅首次计算，其余直接复发上次 summary 并带 `idempotent:true`；所有下发/广播路径吞掉连接关闭异常。

- 日志 BlockingIOError 根治（确认，任务4）
  - 保持 `setup_logging()` 控制台/文件 `enqueue=True` 与全局截断 patch；`coding` 仅输出统计行（含 `jsonSHA/elapsedMs`），避免长 JSON 刷屏与阻塞。

- 异步健壮性与资源清理（任务5）
  - 文件：`backend/core/connection.py`
  - 变更：`close()` 取消 `timeout_task/coding_insight_task`，线程池 `shutdown(cancel_futures=True)`，并在可用时优雅关闭 `asr/tts/llm`；多处 `websocket.send` 已加 try/except 容错。

- 监听 stop 收束 STT（任务1）
  - 文件：`backend/core/handle/textHandle.py`
  - 变更：在 `listen.stop` 分支调用 `conn.asr.on_client_listen_stop(conn)`（如实现）以促使流式 ASR 立即产出最终文本；保留空帧 fallback 兼容旧实现。
  - 文件：`backend/core/providers/asr/doubao_stream.py`
  - 变更：新增 `on_client_listen_stop()`，发送“最后一帧”标记（`generate_last_audio_default_header()` + 空负载）以催促服务端出 definitive 结果。

- 工作模式 STT 直达口令（任务2）
  - 文件：`backend/core/handle/receiveAudioHandle.py`
  - 变更：在 `startToChat` 内，当 `current_mode=="working"` 时先对 STT 文本执行直达口令解析（刷新/认领/完成 + 可选序号“第N个/任务一/1/first/second…”）；命中则直接执行业务并回包；未命中再走意图识别/常规对话。

#### 验收要点
- Coding：包含错误/步骤/阶段的输入，生成的 `insights/risks/actions/nextSteps` 与上下文强相关且非空，且绝不回显原文；`[Coding Insight] ... jsonSHA=.. elapsedMs=..` 统计行可见。
- LLM 复用：`llm_by_mode.coding` 与默认 alias 相同场景，进程内仅一次该模型初始化日志；多连接/多用途均命中共享实例。
- Meeting：连续两次 finalize（含 `mode:end`）时，第二次仅重发上次 summary，带 `idempotent:true`，耗时≈0ms。
- 日志：10 分钟压测无 BlockingIOError；日志文件 10MB 轮转；单条长度 ≤ `log.max_message_length`。
- 资源：断线/重连 100 次，任务/线程不泄露，内存稳定。
- STT 收束：`listen.stop` 后 ≤1s 收到最终 STT 文本，长段落不丢失。
- 工作模式直达：`working` 模式下，STT 文本命中“刷新/认领/完成(+序号)”时直达执行且幂等；未命中时正常进入意图/对话；会议模式行为不受影响。

#### 影响范围与回滚
- 影响 `coding_handle/websocket_server/connection/meeting_handle`；其余链路兼容。
- 回滚：
  - 提示词：还原 `coding_handle.py` 中 `system_prompt` 即可；
  - 单例：移除 `websocket_server.get_or_create_llm` 与 `connection.get_llm_for` 复用分支；
  - finalize：移除互斥锁初始化与幂等分支；
  - 日志/清理：去除 `cancel_futures` 与任务取消调用（不建议）。
  - 本次补充：移除 `textHandle.py` 中 `on_client_listen_stop` 调用与 `receiveAudioHandle.py` 的工作模式直达解析分支；删除 `doubao_stream.py` 中 `on_client_listen_stop()` 实现即可回退。

8.18

### 编辑内容80（Meeting 纪要提速与稳健性 + LLM参数化/进度回报 + Peer.category 容错）

#### 编辑人
- w

#### 新增/修改内容
- Meeting 纪要调用提速与完整性（任务1）
  - 文件：`backend/core/handle/meeting_handle.py`
  - 变更：
    - 新增 `_get_meeting_llm_params()`，按配置 `meeting.llm.max_tokens`（默认1200，夹紧256..4000）与 `checkpoint_max_tokens`（默认600）传入 LLM；
    - 对超长 transcript 进行裁剪（`summary_transcript_max_chars`，默认6000，末尾优先），减少截断概率与耗时；
    - 在 `finalize` 与 checkpoint 小结均应用上述参数；
    - 新增最小进度事件 `_send_summary_progress()`：阶段 `prepare/llm_start/llm_done/done`，附带 `maxTokens/elapsedMs` 等，便于前端实时反馈；
    - 增强 LLM 日志：输出原始长度/JSON长度与 sha8 摘要及耗时，便于诊断“截断/配置不足”。

- Peer category 容错（任务2）
  - 文件：`backend/core/handle/peerHandle.py`
  - 变更：`category` 在校验前做 `strip().lower()` 标准化，避免大小写或尾随空白导致的 `SCHEMA_INVALID`。

#### 验收要点
- 纪要延迟：常规会话 finalize 用时显著下降；日志含 `LLM raw len=.., json len=.., sha8=.., elapsedMs=..`；前端收到 `summary(progress)` 事件流。
- 完整性：长会纪要不再出现明显截断；字段齐全，空字段回退空数组；checkpoint 小结可控（较小 max_tokens）。
- Peer：`category` 大小写/空白不再触发 `SCHEMA_INVALID`。

#### 影响范围与回滚
- 影响 `meeting_handle/peerHandle`；与 ASR/TTS/其他模式兼容。
- 回滚：移除 `meeting_handle.py` 中 `_get_meeting_llm_params/_send_summary_progress` 与参数/裁剪调用；`peerHandle.py` 还原 `category` 原始校验即可。


### 编辑内容81（ASR转写实时推送 + LLM洞察延迟优化 + 模式同步幂等）

#### 编辑人
- w

#### 新增/修改内容
- 语音转写 WebSocket 推送（任务1）
  - 文件：`backend/core/providers/asr/base.py`
  - 变更：在每段语音 `handle_voice_stop()` 产出 STT 后，立即单播 `{"type":"audio","event":"transcription","text":...,"ts":...,"session_id":...}` 到当前连接；保留 `startToChat()` 与 `meeting.snippet` 注入，确保会议与对话链路兼容。

- LLM 洞察延迟优化（任务2）
  - 文件：`backend/core/handle/coding_handle.py`
  - 变更：
    - 去抖下限夹紧为 ≥300ms，避免过大静态值导致长延迟；
    - 调用 LLM 时尽量传入较小 `max_tokens=512`（向下兼容不支持该参数的提供方），缩短响应时间；
    - 继续保留错误/步骤/阶段即时触发，减少等待窗口。

- 模式同步幂等（任务3）
  - 文件：`backend/core/handle/textHandle.py`
  - 变更：当收到 `{"type":"mode","state":"start","mode":X}` 且当前已处于相同模式时，直接回发 `status:"ok"` 并跳过重复初始化（TTS提示、定时器启动、快照单播等），消除重复处理。

#### 验收要点
- 前端实时转写：`listen.stop` 后 ≤1s 收到 `audio.transcription`；会议模式仍能收到 `meeting.snippet/transcript` 流；对话模式能看到 `stt/tts` 正常。
- 洞察延迟：常规 `log/step/phase` 后的 `coding.insight` 平均延迟下降，错误/阶段事件仍即时触发；日志无超长 JSON 刷屏。
- 模式幂等：多次发送相同 `mode.start(X)` 不再重复触发内部逻辑，仅回 `status:"ok"`；切换到新模式仍按预期初始化。

#### 影响范围与回滚
- 影响 `asr.base/coding_handle/textHandle`；与会议/工作/对话主链路兼容。
- 回滚：移除 `audio.transcription` 下发与 `max_tokens/去抖夹紧/幂等` 分支即可恢复旧行为。


### 编辑内容82（Workflow：owner 友好名 + 操作指标日志统一 + 快照三源去抖 + 文档补齐）

#### 编辑人
- w

#### 新增/修改内容
- owner 友好名（任务1）
  - 文件：`backend/core/handle/workflow_handle.py`
  - 变更：新增 `_resolve_device_alias_from_config(conn, device_id)`，从 `.config.yaml` 读取 `workflow.device_alias`（或顶层 `device_alias`）映射；`assign` 事件在未显式提供 owner 时，默认回填 `owner=alias|device-id`。

- 操作指标日志统一（任务2）
  - 文件：`backend/core/handle/workflow_handle.py`
  - 变更：为 `update/assign/complete/delete/list` 与快照路径输出统一指标日志：
    - update: `[Workflow] op=update groups=[...] count=N by=<device>`
    - assign/complete/delete：统一包含 `id/group/by`，幂等路径追加 `idempotent:true`
    - list（空 tasks 拉取）：`[Workflow] op=snapshot source=list group=... to=... count=N`
  - 文件：`backend/core/websocket_server.py`、`backend/core/handle/helloHandle.py`、`backend/core/handle/textHandle.py`
  - 变更：快照日志统一为 `[Workflow] op=snapshot source=register|hello|mode_start ...`，便于统计来源。

- 快照去抖三源合并（任务3）
  - 文件：`backend/core/handle/textHandle.py`
  - 变更：保留 working-start 1.5s 去抖，避免与 register/hello 的快照在极短时间内重复；日志带 `source=mode_start`。

- 文档补齐（任务4）
  - 文件：`hardwareProtocol.md`
  - 变更：补全 Workflow HTTP list/import 示例、鉴权说明与 WS 事件；说明快照三源与去抖策略、统一日志格式。

#### 验收要点
- assign 默认 owner：未显式提供时，回填 `alias|device-id`；可通过配置映射为易读别名（如“前台工牌/研发-张三”）。
- 日志统一：update/assign/complete/delete/list/snapshot 均输出一致格式；快照日志含来源字段；幂等路径有显式标注。
- 快照去抖：注册/hello/working-start 三源不会在1.5s内重复推送，日志可见合并来源。
- 文档：硬件侧可按文档直接调用 Workflow list/import，并理解鉴权与快照策略。

#### 影响范围与回滚
- 影响 `workflow_handle/websocket_server/helloHandle/textHandle/hardwareProtocol.md`；其余链路兼容。
- 回滚：移除 `_resolve_device_alias_from_config` 引用与新增日志行；恢复旧版快照日志文案即可。

### 编辑内容83（Meeting tokens/裁剪下调 + Schema 错误更友好 + Summary checkpoint 标识）

#### 编辑人
- w

#### 新增/修改内容
- 会议 LLM tokens/裁剪优化（任务1）
  - 文件：`backend/core/handle/meeting_handle.py`
  - 变更：默认 `max_tokens` 下调为 800（summary）/400（checkpoint），`summary_transcript_max_chars` 默认 4000，进一步降低 finalize 时延与截断概率。

- Schema 错误文案更友好（任务1/2）
  - 文件：`backend/core/utils/schema.py`
  - 变更：`meeting.snippet` 与 `meeting.summary` 的校验在报错时包含缺失字段名（如 `missing: title,duration`，或 `items must be array of {tag,text}: missing one of tag/text`），便于前端快速纠正最小负载。

- Summary 明确 checkpoint 标识（任务2）
  - 文件：`backend/core/handle/meeting_handle.py`、`hardwareProtocol.md`
  - 变更：最终纪要补充 `checkpoint:false`；文档强调客户端可按 `checkpoint` 区分阶段与最终。

#### 验收要点
- finalize：典型会议 `summary` 时间明显下降，LLM 输入被裁剪到 ≤4000 字符且 tokens 限制生效。
- schema 失败：错误 message 含缺失字段名，前端最小修正后可通过。
- 客户端可依 `checkpoint` 稳定区分阶段/最终纪要。

#### 影响范围与回滚
- 影响 `meeting_handle/schema/hardwareProtocol.md`；不影响 ASR/TTS/Workflow 主链路。
- 回滚：恢复原 tokens/裁剪默认值；还原错误文案与 `checkpoint` 字段即可。

### 编辑内容84（P0 修复：延时快照调度/事件循环绑定/统一发送封装/心跳单点化）

#### 编辑人
- w

#### 新增/修改内容
- 修复延时快照异步调度（任务1）
  - 文件：`backend/core/websocket_server.py`
  - 变更：将 `asyncio.create_task((asyncio.sleep(...),))` 错误用法改为 `_delayed_snapshot()` 协程，先 `await asyncio.sleep()`，再调用 `_send_snapshot()`，确保测试模式下快照按延迟仅发送一次。

- 事件循环绑定到连接协程（任务2）
  - 文件：`backend/core/connection.py`
  - 变更：在 `handle_connection()` 入口用 `asyncio.get_running_loop()` 绑定 `self.loop`，替代构造期 `get_event_loop()`，避免无运行循环或跨循环导致的调度问题。

- 统一消息发送封装（任务3）
  - 文件：`backend/core/connection.py`, `backend/core/websocket_server.py`
  - 变更：新增 `ConnectionHandler.send_json()/send_text()`，集中处理 `send_json` 缺失时的字符串回退；将 `websocket_server` 中补投、快照、统计广播等调用切换为 `handler.send_json()`，减少 try/except 样板与分散逻辑。

- 心跳处理单点化（任务4）
  - 文件：`backend/core/handle/textHandle.py`
  - 变更：移除 `handleTextMessage` 内对 `ping/keepalive` 的重复处理，保留 `ConnectionHandler._route_message` 里的心跳拦截与 `pong` 回执，避免路径重复。

#### 验收要点
- 测试模式下 `snapshot_on_register_delay_ms` 生效：延时后仅推送一次快照，无异常日志。
- 多线程回调使用 `run_coroutine_threadsafe(..., self.loop)` 正常，未再出现 “no running event loop”。
- 消息发送统一通过 `send_json()`，外部协议不变；`broadcast_server_stats/离线补投/工作流快照` 均可正常到达。
- 心跳仅经 `_route_message` 路径处理，仍快速回 `pong`，日志无重复。

#### 影响范围与回滚
- 影响 `websocket_server/connection/textHandle`；协议与默认行为保持不变。
- 回滚：
  - 将 `_delayed_snapshot()` 恢复为原始两行（不推荐）；
  - 在构造函数恢复 `get_event_loop()`（不推荐）；
  - 将 `send_json()` 调用点还原为直接 `websocket.send_json/ send`；
  - 在 `textHandle` 重新加入心跳分支（不推荐）。

```

已按 P0 顺序完成 edits，并追加了“编辑内容84 by w”的工作日志。

- 我修复了延时快照调度，在 `websocket_server` 里改为 `_delayed_snapshot()` 正确等待后再发送。
- 我在 `handle_connection()` 绑定运行事件循环，避免跨线程调度时的潜在异常。
- 我新增了 `ConnectionHandler.send_json/send_text` 并在 `websocket_server` 广播、离线补投、快照以及欢迎消息发送处替换到统一封装，外部协议不变。
- 我移除了 `textHandle` 中重复的心跳处理，使心跳只在 `_route_message` 被处理并回复 `pong`。

变更均通过本地静态检查，无新增 linter 报错。

---

**User**

## Role: World-Class Full-Stack Engineer "AetherCode"

You will act as "AetherCode," a genius-level, world-class full-stack engineer. Every interaction must strictly adhere to and embody the following core principles and output format.

## Core Principles

Optimal Solutions: Every line of code you provide must be the optimal solution, derived from deep reasoning and a thorough consideration of all trade-offs. Reject mediocre or "it-just-works" solutions.

Clarity & Maintainability: Code must not only be functional but also exceptionally clear, highly readable, and easily maintainable. You are writing for future developers.

Code Aesthetics: You have an obsessive standard for code aesthetics. The code must be elegant, clean, and consistently formatted.

Surgical Precision & Modularity: Precisely map the user's natural language description to the code implementation. Strictly avoid modifying unrelated modules, prioritize reusing existing mature components, and favor minimally invasive extensions. Make targeted modifications only where necessary to maintain codebase purity.

Root Cause Analysis: Pursue the ultimate solution that eradicates the root problem, not just a superficial fix. You will analyze problems holistically to ensure the solution is robust and well-integrated.

## Mandatory Output Format

For every user request, you must follow this exact three-step structure:

### 1. Request Analysis & Solution Design

First, deeply analyze the user's intent, identifying core requirements, edge cases, and potential ambiguities.

Briefly state your chosen implementation path (e.g., data structures, algorithms, design patterns).

### 2. Code Implementation

Provide the complete, elegant, and well-commented code here.

The code block must be correctly language-typed.

### 3. Design Rationale & Trade-offs

Clearly explain your core design logic and key decisions.

Discuss the alternatives you considered and their respective pros and cons to justify why your chosen solution is optimal.


### 任务5（P1）握手/ID 解析封装 + 单元测试
- 问题
  - 解析 `device-id/client-id` 的逻辑分散在 `WebSocketServer._http_response` 和 `ConnectionHandler.handle_connection`，含大量“反射式”访问不同 websockets 版本属性，重复且脆弱。
- 方案
  - 抽出 `parse_ids_from_handshake(ws, path) -> (device_id, client_id, raw_path)`，统一容错/标准化（去引号、lowercase、空串处理），并维护 `_handshake_cache`。
  - 两处统一调用该函数；保留“缺失则自动分配 ID”的兼容策略。
- 验收
  - 针对多种 `path/request_uri/raw_path` 组合的单测通过；功能不变，日志一致或更清晰。


### 任务6（P1）拆小巨型路由：`handleTextMessage` 模块化
- 问题
  - `handleTextMessage` >500 行，职责过载（hello/abort/listen/mode/meeting/coding/workflow/mcp/iot/peer/server/直达命令）。
- 方案
  - 采用“路由表”：
    - `HANDLERS = {"hello": handle_hello, "abort": handle_abort, ...}`
    - 每个 handler 函数保持短小、单一职责，禁止深层嵌套。
  - 复用任务3的 `send_json` 封装，去掉各分支里的发送样板。
- 验收
  - `handleTextMessage` <100 行；新增 handler 仅需注册表 + 独立函数；现有用例不变。


### 任务7（P1）ASR 分段改为有限状态机（消除补丁式分支）
- 问题
  - 设备 `listen start/stop` 与服务端 VAD 回退混杂在多处 if/else；还有临时状态 `just_woken_up` 等补丁，复杂且易错。
- 方案
  - 在 `ConnectionHandler` 引入 `listen_state` 有限状态机：`Idle -> Listening -> Finalizing -> Idle`。
  - 规则：
    - 设备 `listen` 事件只改变状态并记录 `_last_listen_event_ms`；VAD 仅在“超过 fallback_ms 未见设备边界”时兜底。
    - `receive_audio()` 在 `Listening` 累积，在 `Finalizing` 触发一次 `handle_voice_stop`。
    - 移除分散的 `have_voice` 特判和 `just_woken_up` 补丁。
- 验收
  - 分段产生稳定；短语边界一致性提升；删除多余 if/else 后功能不回退。


### 任务8（P1）统一 LLM 实例工厂与共享注册表
- 问题
  - `WebSocketServer.get_or_create_llm` 已有共享注册表；`ConnectionHandler.get_llm_for` 仍保留一套“合并 overrides + create_instance”的重复逻辑。
- 方案
  - `get_llm_for` 始终委托给 server 的共享工厂（传 `alias+overrides` 指纹）；仅在“无命中”时回退 `self.llm`。
  - 清理本地实例化分支，避免配置热更与缓存不一致。
- 验收
  - 日志中只出现一次实例化；配置热更后用途 LLM 缓存清理生效；行为与现有完全一致。


确认完成任务5 6 7 8 后,总结刚刚w做的更新,并在log-w.md新增编辑内容85 编辑人是w (参考之前的log格式)

---

**Cursor**

我要先实现四项 P1：封装握手解析并在两处调用、拆分 `handleTextMessage` 成路由表+小函数、加入 `listen_state` 有限状态机并在 ASR 接收中使用、将 `get_llm_for` 委托到 server 共享工厂。然后我会补日志。

```python
import json
from urllib.parse import urlparse, parse_qs
import socket
import subprocess
import re
import os
import wave
from io import BytesIO
from core.utils import p3
import numpy as np
import requests
import opuslib_next
from pydub import AudioSegment
import copy

TAG = __name__
emoji_map = {
    "neutral": "😶",
    "happy": "🙂",
    "laughing": "😆",
    "funny": "😂",
    "sad": "😔",
    "angry": "😠",
    "crying": "😭",
    "loving": "😍",
    "embarrassed": "😳",
    "surprised": "😲",
    "shocked": "😱",
    "thinking": "🤔",
    "winking": "😉",
    "cool": "😎",
    "relaxed": "😌",
    "delicious": "🤤",
    "kissy": "😘",
    "confident": "😏",
    "sleepy": "😴",
    "silly": "😜",
    "confused": "🙄",
}


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to Google's DNS servers
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        return "127.0.0.1"


def is_private_ip(ip_addr):
    """
    Check if an IP address is a private IP address (compatible with IPv4 and IPv6).

    @param {string} ip_addr - The IP address to check.
    @return {bool} True if the IP address is private, False otherwise.
    """
    try:
        # Validate IPv4 or IPv6 address format
        if not re.match(
            r"^(\d{1,3}\.){3}\d{1,3}$|^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$", ip_addr
        ):
            return False  # Invalid IP address format

        # IPv4 private address ranges
        if "." in ip_addr:  # IPv4 address
            ip_parts = list(map(int, ip_addr.split(".")))
            if ip_parts[0] == 10:
                return True  # 10.0.0.0/8 range
            elif ip_parts[0] == 172 and 16 <= ip_parts[1] <= 31:
                return True  # 172.16.0.0/12 range
            elif ip_parts[0] == 192 and ip_parts[1] == 168:
                return True  # 192.168.0.0/16 range
            elif ip_addr == "127.0.0.1":
                return True  # Loopback address
            elif ip_parts[0] == 169 and ip_parts[1] == 254:
                return True  # Link-local address 169.254.0.0/16
            else:
                return False  # Not a private IPv4 address
        else:  # IPv6 address
            ip_addr = ip_addr.lower()
            if ip_addr.startswith("fc00:") or ip_addr.startswith("fd00:"):
                return True  # Unique Local Addresses (FC00::/7)
            elif ip_addr == "::1":
                return True  # Loopback address
            elif ip_addr.startswith("fe80:"):
                return True  # Link-local unicast addresses (FE80::/10)
            else:
                return False  # Not a private IPv6 address

    except (ValueError, IndexError):
        return False  # IP address format error or insufficient segments


def get_ip_info(ip_addr, logger):
    try:
        if is_private_ip(ip_addr):
            ip_addr = ""
        url = f"https://whois.pconline.com.cn/ipJson.jsp?json=true&ip={ip_addr}"
        resp = requests.get(url).json()
        ip_info = {"city": resp.get("city")}
        return ip_info
    except Exception as e:
        logger.bind(tag=TAG).error(f"Error getting client ip info: {e}")
        return {}


def write_json_file(file_path, data):
    """将数据写入 JSON 文件"""
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def is_punctuation_or_emoji(char):
    """检查字符是否为空格、指定标点或表情符号"""
    # 定义需要去除的中英文标点（包括全角/半角）
    punctuation_set = {
        "，",
        ",",  # 中文逗号 + 英文逗号
        "-",
        "－",  # 英文连字符 + 中文全角横线
        "、",  # 中文顿号
        "“",
        "”",
        '"',  # 中文双引号 + 英文引号
        "：",
        ":",  # 中文冒号 + 英文冒号
    }
    if char.isspace() or char in punctuation_set:
        return True
    # 检查表情符号（保留原有逻辑）
    code_point = ord(char)
    emoji_ranges = [
        (0x1F600, 0x1F64F),
        (0x1F300, 0x1F5FF),
        (0x1F680, 0x1F6FF),
        (0x1F900, 0x1F9FF),
        (0x1FA70, 0x1FAFF),
        (0x2600, 0x26FF),
        (0x2700, 0x27BF),
    ]
    return any(start <= code_point <= end for start, end in emoji_ranges)


def get_string_no_punctuation_or_emoji(s):
    """去除字符串首尾的空格、标点符号和表情符号"""
    chars = list(s)
    # 处理开头的字符
    start = 0
    while start < len(chars) and is_punctuation_or_emoji(chars[start]):
        start += 1
    # 处理结尾的字符
    end = len(chars) - 1
    while end >= start and is_punctuation_or_emoji(chars[end]):
        end -= 1
    return "".join(chars[start : end + 1])


def remove_punctuation_and_length(text):
    # 全角符号和半角符号的Unicode范围
    full_width_punctuations = (
        "！＂＃＄％＆＇（）＊＋，－。／：；＜＝＞？＠［＼］＾＿｀｛｜｝～"
    )
    half_width_punctuations = r'!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~'
    space = " "  # 半角空格
    full_width_space = "　"  # 全角空格

    # 去除全角和半角符号以及空格
    result = "".join(
        [
            char
            for char in text
            if char not in full_width_punctuations
            and char not in half_width_punctuations
            and char not in space
            and char not in full_width_space
        ]
    )

    if result == "Yeah":
        return 0, ""
    return len(result), result


def check_model_key(modelType, modelKey):
    if "你" in modelKey:
        return f"配置错误: {modelType} 的 API key 未设置,当前值为: {modelKey}"
    return None


def parse_string_to_list(value, separator=";"):
    """
    将输入值转换为列表
    Args:
        value: 输入值，可以是 None、字符串或列表
        separator: 分隔符，默认为分号
    Returns:
        list: 处理后的列表
    """
    if value is None or value == "":
        return []
    elif isinstance(value, str):
        return [item.strip() for item in value.split(separator) if item.strip()]
    elif isinstance(value, list):
        return value
    return []


def check_ffmpeg_installed():
    ffmpeg_installed = False
    try:
        # 执行ffmpeg -version命令，并捕获输出
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,  # 如果返回码非零则抛出异常
        )
        # 检查输出中是否包含版本信息（可选）
        output = result.stdout + result.stderr
        if "ffmpeg version" in output.lower():
            ffmpeg_installed = True
        return False
    except (subprocess.CalledProcessError, FileNotFoundError):
        # 命令执行失败或未找到
        ffmpeg_installed = False
    if not ffmpeg_installed:
        error_msg = "您的电脑还没正确安装ffmpeg\n"
        error_msg += "\n建议您：\n"
        error_msg += "1、按照项目的安装文档，正确进入conda环境\n"
        error_msg += "2、查阅安装文档，如何在conda环境中安装ffmpeg\n"
        raise ValueError(error_msg)


def extract_json_from_string(input_string):
    """提取字符串中的 JSON 部分"""
    pattern = r"(\{.*\})"
    match = re.search(pattern, input_string, re.DOTALL)  # 添加 re.DOTALL
    if match:
        return match.group(1)  # 返回提取的 JSON 字符串
    return None


def analyze_emotion(text):
    """
    分析文本情感并返回对应的emoji名称（支持中英文）
    """
    if not text or not isinstance(text, str):
        return "neutral"

    original_text = text
    text = text.lower().strip()

    # 检查是否包含现有emoji
    for emotion, emoji in emoji_map.items():
        if emoji in original_text:
            return emotion

    # 标点符号分析
    has_exclamation = "!" in original_text or "！" in original_text
    has_question = "?" in original_text or "？" in original_text
    has_ellipsis = "..." in original_text or "…" in original_text

    # 定义情感关键词映射（中英文扩展版）
    emotion_keywords = {
        "happy": [
            "开心",
            "高兴",
            "快乐",
            "愉快",
            "幸福",
            "满意",
            "棒",
            "好",
            "不错",
            "完美",
            "棒极了",
            "太好了",
            "好呀",
            "好的",
            "happy",
            "joy",
            "great",
            "good",
            "nice",
            "awesome",
            "fantastic",
            "wonderful",
        ],
        "laughing": [
            "哈哈",
            "哈哈哈",
            "呵呵",
            "嘿嘿",
            "嘻嘻",
            "笑死",
            "太好笑了",
            "笑死我了",
            "lol",
            "lmao",
            "haha",
            "hahaha",
            "hehe",
            "rofl",
            "funny",
            "laugh",
        ],
        "funny": [
            "搞笑",
            "滑稽",
            "逗",
            "幽默",
            "笑点",
            "段子",
            "笑话",
            "太逗了",
            "hilarious",
            "joke",
            "comedy",
        ],
        "sad": [
            "伤心",
            "难过",
            "悲哀",
            "悲伤",
            "忧郁",
            "郁闷",
            "沮丧",
            "失望",
            "想哭",
            "难受",
            "不开心",
            "唉",
            "呜呜",
            "sad",
            "upset",
            "unhappy",
            "depressed",
            "sorrow",
            "gloomy",
        ],
        "angry": [
            "生气",
            "愤怒",
            "气死",
            "讨厌",
            "烦人",
            "可恶",
            "烦死了",
            "恼火",
            "暴躁",
            "火大",
            "愤怒",
            "气炸了",
            "angry",
            "mad",
            "annoyed",
            "furious",
            "pissed",
            "hate",
        ],
        "crying": [
            "哭泣",
            "泪流",
            "大哭",
            "伤心欲绝",
            "泪目",
            "流泪",
            "哭死",
            "哭晕",
            "想哭",
            "泪崩",
            "cry",
            "crying",
            "tears",
            "sob",
            "weep",
        ],
        "loving": [
            "爱你",
            "喜欢",
            "爱",
            "亲爱的",
            "宝贝",
            "么么哒",
            "抱抱",
            "想你",
            "思念",
            "最爱",
            "亲亲",
            "喜欢你",
            "love",
            "like",
            "adore",
            "darling",
            "sweetie",
            "honey",
            "miss you",
            "heart",
        ],
        "embarrassed": [
            "尴尬",
            "不好意思",
            "害羞",
            "脸红",
            "难为情",
            "社死",
            "丢脸",
            "出丑",
            "embarrassed",
            "awkward",
            "shy",
            "blush",
        ],
        "surprised": [
            "惊讶",
            "吃惊",
            "天啊",
            "哇塞",
            "哇",
            "居然",
            "竟然",
            "没想到",
            "出乎意料",
            "surprise",
            "wow",
            "omg",
            "oh my god",
            "amazing",
            "unbelievable",
        ],
        "shocked": [
            "震惊",
            "吓到",
            "惊呆了",
            "不敢相信",
            "震撼",
            "吓死",
            "恐怖",
            "害怕",
            "吓人",
            "shocked",
            "shocking",
            "scared",
            "frightened",
            "terrified",
            "horror",
        ],
        "thinking": [
            "思考",
            "考虑",
            "想一下",
            "琢磨",
            "沉思",
            "冥想",
            "想",
            "思考中",
            "在想",
            "think",
            "thinking",
            "consider",
            "ponder",
            "meditate",
        ],
        "winking": [
            "调皮",
            "眨眼",
            "你懂的",
            "坏笑",
            "邪恶",
            "奸笑",
            "使眼色",
            "wink",
            "teasing",
            "naughty",
            "mischievous",
        ],
        "cool": [
            "酷",
            "帅",
            "厉害",
            "棒极了",
            "真棒",
            "牛逼",
            "强",
            "优秀",
            "杰出",
            "出色",
            "完美",
            "cool",
            "awesome",
            "amazing",
            "great",
            "impressive",
            "perfect",
        ],
        "relaxed": [
            "放松",
            "舒服",
            "惬意",
            "悠闲",
            "轻松",
            "舒适",
            "安逸",
            "自在",
            "relax",
            "relaxed",
            "comfortable",
            "cozy",
            "chill",
            "peaceful",
        ],
        "delicious": [
            "好吃",
            "美味",
            "香",
            "馋",
            "可口",
            "香甜",
            "大餐",
            "大快朵颐",
            "流口水",
            "垂涎",
            "delicious",
            "yummy",
            "tasty",
            "yum",
            "appetizing",
            "mouthwatering",
        ],
        "kissy": [
            "亲亲",
            "么么",
            "吻",
            "mua",
            "muah",
            "亲一下",
            "飞吻",
            "kiss",
            "xoxo",
            "hug",
            "muah",
            "smooch",
        ],
        "confident": [
            "自信",
            "肯定",
            "确定",
            "毫无疑问",
            "当然",
            "必须的",
            "毫无疑问",
            "确信",
            "坚信",
            "confident",
            "sure",
            "certain",
            "definitely",
            "positive",
        ],
        "sleepy": [
            "困",
            "睡觉",
            "晚安",
            "想睡",
            "好累",
            "疲惫",
            "疲倦",
            "困了",
            "想休息",
            "睡意",
            "sleep",
            "sleepy",
            "tired",
            "exhausted",
            "bedtime",
            "good night",
        ],
        "silly": [
            "傻",
            "笨",
            "呆",
            "憨",
            "蠢",
            "二",
            "憨憨",
            "傻乎乎",
            "呆萌",
            "silly",
            "stupid",
            "dumb",
            "foolish",
            "goofy",
            "ridiculous",
        ],
        "confused": [
            "疑惑",
            "不明白",
            "不懂",
            "困惑",
            "疑问",
            "为什么",
            "怎么回事",
            "啥意思",
            "不清楚",
            "confused",
            "puzzled",
            "doubt",
            "question",
            "what",
            "why",
            "how",
        ],
    }

    # 特殊句型判断（中英文）
    # 赞美他人
    if any(
        phrase in text
        for phrase in [
            "你真",
            "你好",
            "您真",
            "你真棒",
            "你好厉害",
            "你太强了",
            "你真好",
            "你真聪明",
            "you are",
            "you're",
            "you look",
            "you seem",
            "so smart",
            "so kind",
        ]
    ):
        return "loving"
    # 自我赞美
    if any(
        phrase in text
        for phrase in [
            "我真",
            "我最",
            "我太棒了",
            "我厉害",
            "我聪明",
            "我优秀",
            "i am",
            "i'm",
            "i feel",
            "so good",
            "so happy",
        ]
    ):
        return "cool"
    # 晚安/睡觉相关
    if any(
        phrase in text
        for phrase in [
            "睡觉",
            "晚安",
            "睡了",
            "好梦",
            "休息了",
            "去睡了",
            "sleep",
            "good night",
            "bedtime",
            "go to bed",
        ]
    ):
        return "sleepy"
    # 疑问句
    if has_question and not has_exclamation:
        return "thinking"
    # 强烈情感（感叹号）
    if has_exclamation and not has_question:
        # 检查是否是积极内容
        positive_words = (
            emotion_keywords["happy"]
            + emotion_keywords["laughing"]
            + emotion_keywords["cool"]
        )
        if any(word in text for word in positive_words):
            return "laughing"
        # 检查是否是消极内容
        negative_words = (
            emotion_keywords["angry"]
            + emotion_keywords["sad"]
            + emotion_keywords["crying"]
        )
        if any(word in text for word in negative_words):
            return "angry"
        return "surprised"
    # 省略号（表示犹豫或思考）
    if has_ellipsis:
        return "thinking"

    # 关键词匹配（带权重）
    emotion_scores = {emotion: 0 for emotion in emoji_map.keys()}

    # 给匹配到的关键词加分
    for emotion, keywords in emotion_keywords.items():
        for keyword in keywords:
            if keyword in text:
                emotion_scores[emotion] += 1

    # 给长文本中的重复关键词额外加分
    if len(text) > 20:  # 长文本
        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                emotion_scores[emotion] += text.count(keyword) * 0.5

    # 根据分数选择最可能的情感
    max_score = max(emotion_scores.values())
    if max_score == 0:
        return "happy"  # 默认

    # 可能有多个情感同分，根据上下文选择最合适的
    top_emotions = [e for e, s in emotion_scores.items() if s == max_score]

    # 如果多个情感同分，使用以下优先级
    priority_order = [
        "laughing",
        "crying",
        "angry",
        "surprised",
        "shocked",  # 强烈情感优先
        "loving",
        "happy",
        "funny",
        "cool",  # 积极情感
        "sad",
        "embarrassed",
        "confused",  # 消极情感
        "thinking",
        "winking",
        "relaxed",  # 中性情感
        "delicious",
        "kissy",
        "confident",
        "sleepy",
        "silly",  # 特殊场景
    ]

    for emotion in priority_order:
        if emotion in top_emotions:
            return emotion

    return top_emotions[0]  # 如果都不在优先级列表里，返回第一个


def audio_to_data(audio_file_path, is_opus=True):
    # 获取文件后缀名
    file_type = os.path.splitext(audio_file_path)[1]
    if file_type:
        file_type = file_type.lstrip(".")
    # 读取音频文件，-nostdin 参数：不要从标准输入读取数据，否则FFmpeg会阻塞
    audio = AudioSegment.from_file(
        audio_file_path, format=file_type, parameters=["-nostdin"]
    )

    # 转换为单声道/16kHz采样率/16位小端编码（确保与编码器匹配）
    audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)

    # 音频时长(秒)
    duration = len(audio) / 1000.0

    # 获取原始PCM数据（16位小端）
    raw_data = audio.raw_data
    return pcm_to_data(raw_data, is_opus), duration


def audio_bytes_to_data(audio_bytes, file_type, is_opus=True):
    """
    直接用音频二进制数据转为opus/pcm数据，支持wav、mp3、p3
    """
    if file_type == "p3":
        # 直接用p3解码
        return p3.decode_opus_from_bytes(audio_bytes)
    else:
        # 其他格式用pydub
        audio = AudioSegment.from_file(
            BytesIO(audio_bytes), format=file_type, parameters=["-nostdin"]
        )
        audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
        duration = len(audio) / 1000.0
        raw_data = audio.raw_data
        return pcm_to_data(raw_data, is_opus), duration


def pcm_to_data(raw_data, is_opus=True):
    # 初始化Opus编码器
    encoder = opuslib_next.Encoder(16000, 1, opuslib_next.APPLICATION_AUDIO)

    # 编码参数
    frame_duration = 60  # 60ms per frame
    frame_size = int(16000 * frame_duration / 1000)  # 960 samples/frame

    datas = []
    # 按帧处理所有音频数据（包括最后一帧可能补零）
    for i in range(0, len(raw_data), frame_size * 2):  # 16bit=2bytes/sample
        # 获取当前帧的二进制数据
        chunk = raw_data[i : i + frame_size * 2]

        # 如果最后一帧不足，补零
        if len(chunk) < frame_size * 2:
            chunk += b"\x00" * (frame_size * 2 - len(chunk))

        if is_opus:
            # 转换为numpy数组处理
            np_frame = np.frombuffer(chunk, dtype=np.int16)
            # 编码Opus数据
            frame_data = encoder.encode(np_frame.tobytes(), frame_size)
        else:
            frame_data = chunk if isinstance(chunk, bytes) else bytes(chunk)

        datas.append(frame_data)

    return datas


def opus_datas_to_wav_bytes(opus_datas, sample_rate=16000, channels=1):
    """
    将opus帧列表解码为wav字节流
    """
    decoder = opuslib_next.Decoder(sample_rate, channels)
    pcm_datas = []

    frame_duration = 60  # ms
    frame_size = int(sample_rate * frame_duration / 1000)  # 960

    for opus_frame in opus_datas:
        # 解码为PCM（返回bytes，2字节/采样点）
        pcm = decoder.decode(opus_frame, frame_size)
        pcm_datas.append(pcm)

    pcm_bytes = b"".join(pcm_datas)

    # 写入wav字节流
    wav_buffer = BytesIO()
    with wave.open(wav_buffer, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return wav_buffer.getvalue()


def check_vad_update(before_config, new_config):
    if (
        new_config.get("selected_module") is None
        or new_config["selected_module"].get("VAD") is None
    ):
        return False
    update_vad = False
    current_vad_module = before_config["selected_module"]["VAD"]
    new_vad_module = new_config["selected_module"]["VAD"]
    current_vad_type = (
        current_vad_module
        if "type" not in before_config["VAD"][current_vad_module]
        else before_config["VAD"][current_vad_module]["type"]
    )
    new_vad_type = (
        new_vad_module
        if "type" not in new_config["VAD"][new_vad_module]
        else new_config["VAD"][new_vad_module]["type"]
    )
    update_vad = current_vad_type != new_vad_type
    return update_vad


def check_asr_update(before_config, new_config):
    if (
        new_config.get("selected_module") is None
        or new_config["selected_module"].get("ASR") is None
    ):
        return False
    update_asr = False
    current_asr_module = before_config["selected_module"]["ASR"]
    new_asr_module = new_config["selected_module"]["ASR"]
    current_asr_type = (
        current_asr_module
        if "type" not in before_config["ASR"][current_asr_module]
        else before_config["ASR"][current_asr_module]["type"]
    )
    new_asr_type = (
        new_asr_module
        if "type" not in new_config["ASR"][new_asr_module]
        else new_config["ASR"][new_asr_module]["type"]
    )
    update_asr = current_asr_type != new_asr_type
    return update_asr


def filter_sensitive_info(config: dict) -> dict:
    """
    过滤配置中的敏感信息
    Args:
        config: 原始配置字典
    Returns:
        过滤后的配置字典
    """
    sensitive_keys = [
        "api_key",
        "personal_access_token",
        "access_token",
        "token",
        "secret",
        "access_key_secret",
        "secret_key",
    ]

    def _filter_dict(d: dict) -> dict:
        filtered = {}
        for k, v in d.items():
            if any(sensitive in k.lower() for sensitive in sensitive_keys):
                filtered[k] = "***"
            elif isinstance(v, dict):
                filtered[k] = _filter_dict(v)
            elif isinstance(v, list):
                filtered[k] = [_filter_dict(i) if isinstance(i, dict) else i for i in v]
            else:
                filtered[k] = v
        return filtered

    return _filter_dict(copy.deepcopy(config))


def get_vision_url(config: dict) -> str:
    """获取 vision URL

    Args:
        config: 配置字典

    Returns:
        str: vision URL
    """
    server_config = config["server"]
    vision_explain = server_config.get("vision_explain", "")
    if "你的" in vision_explain:
        local_ip = get_local_ip()
        port = int(server_config.get("http_port", 8003))
        vision_explain = f"http://{local_ip}:{port}/mcp/vision/explain"
    return vision_explain


def is_valid_image_file(file_data: bytes) -> bool:
    """
    检查文件数据是否为有效的图片格式

    Args:
        file_data: 文件的二进制数据

    Returns:
        bool: 如果是有效的图片格式返回True，否则返回False
    """
    # 常见图片格式的魔数（文件头）
    image_signatures = {
        b"\xff\xd8\xff": "JPEG",
        b"\x89PNG\r\n\x1a\n": "PNG",
        b"GIF87a": "GIF",
        b"GIF89a": "GIF",
        b"BM": "BMP",
        b"II*\x00": "TIFF",
        b"MM\x00*": "TIFF",
        b"RIFF": "WEBP",
    }

    # 检查文件头是否匹配任何已知的图片格式
    for signature in image_signatures:
        if file_data.startswith(signature):
            return True

    return False


def sanitize_tool_name(name: str) -> str:
    """Sanitize tool names for OpenAI compatibility."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


# -------------------- Handshake Helpers --------------------
def _extract_raw_path(path_or_conn) -> str | None:
    """Best-effort extract raw path (with query) from websockets variations.
    Accepts a str path or a connection-like object with multiple possible attributes.
    """
    try:
        if isinstance(path_or_conn, str):
            return path_or_conn
        conn_obj = path_or_conn
        for attr in ("path", "request_uri", "raw_request_uri", "request_path", "raw_path"):
            try:
                val = getattr(conn_obj, attr, None)
                if isinstance(val, str) and val:
                    return val
            except Exception:
                continue
        # Deep: try request object
        try:
            req = getattr(conn_obj, "request", None) or getattr(conn_obj, "_request", None)
            if req is not None:
                for attr in ("path", "target", "raw_path"):
                    try:
                        val = getattr(req, attr, None)
                        if isinstance(val, str) and val:
                            return val
                    except Exception:
                        continue
        except Exception:
            pass
    except Exception:
        return None
    return None


def parse_ids_from_handshake(path_or_conn) -> tuple[str | None, str | None, str | None]:
    """Parse device-id and client-id from a path string or connection-like object.

    Returns: (device_id, client_id, raw_path)
    - device_id/client_id are normalized: stripped quotes and lowercased
    - any missing value is returned as None
    """
    raw_path = _extract_raw_path(path_or_conn)
    device_id = None
    client_id = None
    try:
        if isinstance(raw_path, str) and raw_path:
            parsed = urlparse(raw_path)
            qs = parse_qs(parsed.query or "")
            device_vals = qs.get("device-id") or qs.get("device_id")
            client_vals = qs.get("client-id") or qs.get("client_id")
            if device_vals:
                device_id = (device_vals[0] or "").strip().strip('"').strip("'").lower() or None
                # default client to device when absent
                client_id = (client_vals[0] if client_vals else device_id)
                if isinstance(client_id, str):
                    client_id = client_id.strip().strip('"').strip("'").lower() or None
    except Exception:
        pass
    return device_id, client_id, raw_path

```

```python
import asyncio
import time
import json
import websockets
import socket
from http import HTTPStatus
from config.logger import setup_logging
from core.connection import ConnectionHandler
from config.config_loader import get_config_from_api
from core.utils.modules_initialize import initialize_modules
from core.utils.tasks_store import get_task_store
from core.utils.util import check_vad_update, check_asr_update
from core.utils.offline_queue import pop_offline_for_device
from urllib.parse import urlparse, parse_qs
from core.utils.util import parse_ids_from_handshake

TAG = __name__


class WebSocketServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self.config_lock = asyncio.Lock()
        self._started_event: asyncio.Event = asyncio.Event()
        self.startup_error: Exception | None = None
        # 设备路由映射：device-id -> ConnectionHandler
        self.device_handlers = {}
        self.device_handlers_lock = asyncio.Lock()
        # 握手缓存：按连接对象 id 缓存原始 path 与解析到的 ids，供 handler 兜底读取
        self._handshake_cache: dict[int, dict] = {}
        modules = initialize_modules(
            self.logger,
            self.config,
            "VAD" in self.config["selected_module"],
            "ASR" in self.config["selected_module"],
            "LLM" in self.config["selected_module"],
            False,
            "Memory" in self.config["selected_module"],
            "Intent" in self.config["selected_module"],
        )
        self._vad = modules["vad"] if "vad" in modules else None
        self._asr = modules["asr"] if "asr" in modules else None
        self._llm = modules["llm"] if "llm" in modules else None
        self._intent = modules["intent"] if "intent" in modules else None
        self._memory = modules["memory"] if "memory" in modules else None

        self.active_connections = set()
        # LLM 单例注册表：key = alias + overrides 指纹
        self.llm_registry: dict[str, object] = {}

    def get_or_create_llm(self, alias: str, overrides: dict | None = None):
        """按别名与可选覆盖创建/复用共享 LLM 实例。

        key 规则：f"{alias}::" + json.dumps(overrides, sort_keys=True)（None 视为{}）。
        基础配置来源 self.config['LLM'][alias]，覆盖与类型解析后实例化。
        """
        try:
            import json as _json
            from core.utils import llm as llm_utils
        except Exception:
            raise
        if not isinstance(alias, str) or len(alias) == 0:
            return None
        ov = overrides or {}
        try:
            key = f"{alias}::{_json.dumps(ov, ensure_ascii=False, sort_keys=True)}"
        except Exception:
            # Fallback literal '{}'
            key = f"{alias}::" + "{}"
        # 命中共享实例
        if key in self.llm_registry:
            return self.llm_registry[key]
        # 构造配置
        base_conf = None
        try:
            base_conf = dict(self.config.get("LLM", {}).get(alias, {}))
        except Exception:
            base_conf = None
        if not base_conf:
            # 无法构造，返回 None
            return None
        if isinstance(ov, dict) and ov:
            try:
                for k, v in ov.items():
                    base_conf[k] = v
            except Exception:
                pass
        llm_type = base_conf.get("type", alias)
        instance = llm_utils.create_instance(llm_type, base_conf)
        self.llm_registry[key] = instance
        return instance

    async def start(self):
        # reset start state
        try:
            self._started_event.clear()
        except Exception:
            self._started_event = asyncio.Event()
        self.startup_error = None
        server_config = self.config.get("server", {}) or {}
        host = server_config.get("ip") or "0.0.0.0"
        # 端口健壮化解析
        raw_port = server_config.get("port", 8000)
        try:
            port = int(raw_port) if str(raw_port).strip() != "" else 8000
        except Exception:
            port = 8000

        # 预绑定检测：尽早暴露“端口被占用/权限不足”等问题
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
        except OSError as e:
            self.logger.bind(tag=TAG).error(
                f"WebSocketServer failed to bind preflight {host}:{port}: {e}. \n"
                f"可能原因：端口被占用/权限不足/host非法。请确认无旧进程占用端口或调整 server.port。"
            )
            self.startup_error = e
            self._started_event.set()
            # 直接抛出以让上层捕获（避免静默失败）
            raise

        # 真正启动 WS 服务
        try:
            async with websockets.serve(
                self._handle_connection,
                host,
                port,
                process_request=self._http_response,
                ping_interval=20,
                ping_timeout=50,
                close_timeout=5,
            ):
                # 启动时打印当前在线设备快照（通常为空），便于对照测试页
                online_ids = self.get_online_device_ids()
                self.logger.bind(tag=TAG).info(
                    f"WebSocketServer started on {host}:{port}, online_count={self.get_device_count()}, online={online_ids}; server.stats broadcasting enabled"
                )
                # 标记已启动
                try:
                    self._started_event.set()
                except Exception:
                    pass
                # 周期性广播服务端统计
                asyncio.create_task(self._periodic_stats_task())
                await asyncio.Future()
        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"WebSocketServer failed to start on {host}:{port}: {e}"
            )
            self.startup_error = e
            try:
                self._started_event.set()
            except Exception:
                pass
            raise

    async def wait_started(self) -> None:
        await self._started_event.wait()
        if self.startup_error is not None:
            raise self.startup_error

    async def _handle_connection(self, websocket, path=None):
        """处理新连接，每次创建独立的ConnectionHandler
        兼容 websockets 旧接口，接收 path 参数，传递给后续处理。
        """
        # 创建ConnectionHandler时传入当前server实例
        handler = ConnectionHandler(
            self.config,
            self._vad,
            self._asr,
            self._llm,
            self._memory,
            self._intent,
            self,  # 传入server实例
        )
        self.active_connections.add(handler)
        try:
            await handler.handle_connection(websocket, path)
        finally:
            self.active_connections.discard(handler)

    def _http_response(self, path, request_headers):
        """
        websockets 的 process_request 回调。
        - 返回 None 继续握手（WebSocket 升级）
        - 返回 (status, headers, body) 处理普通 HTTP 请求
        """
        try:
            # 诊断：记录升级请求的原始 path（含 query）与关键头部
            try:
                # websockets 不同版本下，这里的第一个参数可能是 str（带 query 的 path），也可能是连接对象
                raw_path_str = None
                conn_obj = None
                if isinstance(path, str):
                    raw_path_str = path
                else:
                    conn_obj = path
                    # 猜测属性链提取原始 path
                    for attr in ("path", "request_uri", "raw_request_uri", "request_path", "raw_path"):
                        try:
                            val = getattr(conn_obj, attr, None)
                            if isinstance(val, str) and val:
                                raw_path_str = val
                                break
                        except Exception:
                            continue
                    # 深一层：可能存在 request 对象
                    if raw_path_str is None:
                        try:
                            req = getattr(conn_obj, "request", None) or getattr(conn_obj, "_request", None)
                            if req is not None:
                                for attr in ("path", "target", "raw_path"):
                                    try:
                                        val = getattr(req, attr, None)
                                        if isinstance(val, str) and val:
                                            raw_path_str = val
                                            break
                                    except Exception:
                                        continue
                        except Exception:
                            pass

                self.logger.bind(tag=TAG).info(
                    f"HTTP upgrade request path={raw_path_str if raw_path_str is not None else path}"
                )

                # 将解析到的 device-id/client-id 暂存，供后续 handler 兜底读取
                try:
                    if raw_path_str and conn_obj is not None:
                        did, cid, _ = parse_ids_from_handshake(raw_path_str)
                        if did:
                            self._handshake_cache[id(conn_obj)] = {
                                "raw_path": raw_path_str,
                                "device-id": did,
                                "client-id": cid or did,
                            }
                except Exception:
                    pass
            except Exception:
                pass
            connection_header = (
                (request_headers.get("Connection", "") or request_headers.get("connection", ""))
                .strip()
                .lower()
            )
            upgrade_header = (
                (request_headers.get("Upgrade", "") or request_headers.get("upgrade", ""))
                .strip()
                .lower()
            )
            if "upgrade" in connection_header and upgrade_header == "websocket":
                return None
        except Exception:
            # 容错：如遇到异常，默认继续握手
            return None

        body = b"Server is running\n"
        headers = [("Content-Type", "text/plain"), ("Content-Length", str(len(body)))]
        return 200, headers, body

    async def update_config(self) -> bool:
        """更新服务器配置并重新初始化组件

        Returns:
            bool: 更新是否成功
        """
        try:
            async with self.config_lock:
                # 重新获取配置
                new_config = get_config_from_api(self.config)
                if new_config is None:
                    self.logger.bind(tag=TAG).error("获取新配置失败")
                    return False
                self.logger.bind(tag=TAG).info(f"获取新配置成功")
                # 检查 VAD 和 ASR 类型是否需要更新
                update_vad = check_vad_update(self.config, new_config)
                update_asr = check_asr_update(self.config, new_config)
                self.logger.bind(tag=TAG).info(
                    f"检查VAD和ASR类型是否需要更新: {update_vad} {update_asr}"
                )
                # 更新配置
                self.config = new_config
                # 重新初始化组件
                modules = initialize_modules(
                    self.logger,
                    new_config,
                    update_vad,
                    update_asr,
                    "LLM" in new_config["selected_module"],
                    False,
                    "Memory" in new_config["selected_module"],
                    "Intent" in new_config["selected_module"],
                )

                # 更新组件实例
                if "vad" in modules:
                    self._vad = modules["vad"]
                if "asr" in modules:
                    self._asr = modules["asr"]
                if "llm" in modules:
                    self._llm = modules["llm"]
                if "intent" in modules:
                    self._intent = modules["intent"]
                if "memory" in modules:
                    self._memory = modules["memory"]
                
                # 通知现有连接：清理用途LLM缓存，避免使用旧配置实例
                try:
                    for handler in list(self.active_connections):
                        try:
                            if hasattr(handler, "_llm_cache") and isinstance(handler._llm_cache, dict):
                                handler._llm_cache.clear()
                                # 同时清理 meeting 推送周期，使热更后的间隔在下一周期生效
                                if hasattr(handler, "meeting_push_interval_ms_current"):
                                    try:
                                        delattr(handler, "meeting_push_interval_ms_current")
                                    except Exception:
                                        pass
                        except Exception:
                            continue
                except Exception:
                    pass
                self.logger.bind(tag=TAG).info(f"更新配置任务执行完毕")
                return True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"更新服务器配置失败: {str(e)}")
            return False

    async def register_device_handler(self, device_id: str, handler: ConnectionHandler) -> bool:
        """注册设备与连接处理器的映射；若已存在同名设备，则断开旧连接并接受新连接。

        Returns:
            bool: True 注册成功；False 注册失败。
        """
        try:
            async with self.device_handlers_lock:
                existed = self.device_handlers.get(device_id)
                if existed is not None and existed is not handler:
                    self.logger.bind(tag=TAG).warning(
                        f"检测到重复连接，启用双通道过渡(≤2s)并接受新连接: device={device_id}"
                    )
                    # 双通道过渡：先提示旧连接，延迟 ~1.5s 再关闭，降低听写中断概率
                    try:
                        if existed.websocket:
                            try:
                                await existed.send_json({
                                    "type": "system",
                                    "message": "检测到新连接，当前通道将于约1.5秒后关闭以切换到新通道"
                                })
                            except Exception:
                                pass
                            async def _deferred_close(old_handler):
                                try:
                                    await asyncio.sleep(1.5)
                                    await old_handler.close(old_handler.websocket)
                                except Exception:
                                    pass
                            asyncio.create_task(_deferred_close(existed))
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"计划关闭旧连接失败(已忽略): {e}")
                        # 即使计划失败，也继续注册新连接
                self.device_handlers[device_id] = handler
            self.logger.bind(tag=TAG).info(f"注册设备路由: {device_id}")
            # 注册后广播一次在线快照
            await self.broadcast_server_stats()
            # 上线补投递：尝试取出离线队列并逐条发送
            try:
                pending, dropped = pop_offline_for_device(device_id)
                if pending:
                    # 统计按发起方聚合的补投条数
                    try:
                        from collections import defaultdict
                        sender_counts = defaultdict(int)
                    except Exception:
                        sender_counts = {}
                    sent = 0
                    for env in pending:
                        try:
                            if handler:
                                await handler.send_json(env)
                            sent += 1
                            # 聚合发起方统计
                            try:
                                origin = env.get("from")
                                if isinstance(origin, str) and len(origin) > 0:
                                    key = origin.strip().lower()
                                    if isinstance(sender_counts, dict):
                                        sender_counts[key] = sender_counts.get(key, 0) + 1
                                    else:
                                        sender_counts[key] += 1
                            except Exception:
                                pass
                        except AttributeError:
                            import json
                            await handler.send_json(env)
                            sent += 1
                        except Exception:
                            continue
                    self.logger.bind(tag=TAG).info(
                        f"离线补投递: device={device_id}, sent={sent}, dropped={dropped}"
                    )
                    # 给各发起方回执补投统计
                    try:
                        if isinstance(sender_counts, dict):
                            for origin_id, cnt in sender_counts.items():
                                try:
                                    origin_handler = self.device_handlers.get(origin_id)
                                    if origin_handler and origin_handler.websocket:
                                        payload = {
                                            "type": "peer",
                                            "event": "redelivered",
                                            "to": device_id,
                                            "count": int(cnt),
                                        }
                                        try:
                                            await origin_handler.send_json(payload)
                                        except Exception:
                                            continue
                                except Exception:
                                    continue
                    except Exception:
                        pass
            except Exception:
                pass
            # 上线即单播一次工作流快照（按分组），可通过开关/延迟避免测试噪声
            try:
                try:
                    group_key = str(device_id)[:8]
                except Exception:
                    group_key = "default"
                tasks = get_task_store().list_by_group(group_key)
                if tasks is not None:
                    # 读取测试模式与延迟配置
                    try:
                        wf_cfg = (self.config.get("workflow", {}) or {}) if isinstance(self.config, dict) else {}
                        test_mode = bool(wf_cfg.get("test_mode", False))
                        delay_ms = int(wf_cfg.get("snapshot_on_register_delay_ms", 0))
                    except Exception:
                        test_mode = False; delay_ms = 0
                    async def _send_snapshot():
                        envelope = {"type": "workflow", "event": "update", "tasks": tasks}
                        try:
                            await handler.send_json(envelope)
                        except Exception:
                            pass
                        self.logger.bind(tag=TAG).info(f"[Workflow] op=snapshot source=register group={group_key} to={device_id} count={len(tasks)} test_mode={test_mode}")
                    if test_mode and delay_ms > 0:
                        async def _delayed_snapshot():
                            try:
                                await asyncio.sleep(delay_ms/1000.0)
                                await _send_snapshot()
                            except Exception:
                                pass
                        asyncio.create_task(_delayed_snapshot())
                    else:
                        await _send_snapshot()
            except Exception:
                pass
            return True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"注册设备路由失败 {device_id}: {e}")
            return False

    async def unregister_device_handler(self, device_id: str, handler: ConnectionHandler) -> None:
        """注销设备与连接处理器的映射"""
        try:
            async with self.device_handlers_lock:
                if self.device_handlers.get(device_id) is handler:
                    del self.device_handlers[device_id]
            self.logger.bind(tag=TAG).info(f"注销设备路由: {device_id}")
            # 注销后广播一次在线快照
            await self.broadcast_server_stats()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"注销设备路由失败 {device_id}: {e}")

    def get_device_handler(self, device_id: str) -> ConnectionHandler | None:
        """查询目标设备的连接处理器（只读，不加锁用于快速路径）"""
        return self.device_handlers.get(device_id)

    # 便捷查询方法
    def is_device_online(self, device_id: str) -> bool:
        """判断设备是否在线。"""
        return self.device_handlers.get(device_id) is not None

    def get_online_device_ids(self) -> list[str]:
        """获取当前在线设备列表（快照）。"""
        try:
            return list(self.device_handlers.keys())
        except Exception:
            return []

    async def get_online_device_ids_async(self) -> list[str]:
        """获取在线设备ID（加锁快照），避免与注册/注销竞态。"""
        try:
            async with self.device_handlers_lock:
                return list(self.device_handlers.keys())
        except Exception:
            return []

    def get_device_count(self) -> int:
        """在线设备数量。"""
        return len(self.device_handlers)

    def get_broadcast_targets(self, exclude_device_id: str | None = None) -> list[str]:
        """广播目标集合（可排除某个设备）。"""
        ids = self.get_online_device_ids()
        if exclude_device_id is None:
            return ids
        return [d for d in ids if d != exclude_device_id]

    async def get_broadcast_targets_async(self, exclude_device_id: str | None = None) -> list[str]:
        """广播目标集合（加锁）。"""
        ids = await self.get_online_device_ids_async()
        if exclude_device_id is None:
            return ids
        return [d for d in ids if d != exclude_device_id]

    def get_server_stats_json(self) -> dict:
        """构造服务器观测数据 JSON。"""
        stats = {
            "type": "server",
            "event": "stats",
            "ts": int(time.time() * 1000),
            "deviceCount": self.get_device_count(),
            "online": self.get_online_device_ids(),
        }
        try:
            import psutil  # 已在 requirements 中

            stats["cpuPercent"] = psutil.cpu_percent(interval=None)
            vm = psutil.virtual_memory()
            stats["memPercent"] = vm.percent
            stats["memUsedMB"] = int(vm.used / (1024 * 1024))
            stats["memTotalMB"] = int(vm.total / (1024 * 1024))
        except Exception:
            pass
        return stats

    async def broadcast_server_stats(self) -> None:
        """向所有在线连接广播服务端统计。"""
        try:
            payload = self.get_server_stats_json()
            for handler in list(self.device_handlers.values()):
                try:
                    if handler:
                        await handler.send_json(payload)
                except Exception:
                    continue
        except Exception:
            pass

    async def _periodic_stats_task(self) -> None:
        """周期广播服务端统计信息。"""
        try:
            while True:
                await asyncio.sleep(10)
                await self.broadcast_server_stats()
        except asyncio.CancelledError:
            return
        except Exception:
            return

```

```python
*** Begin Patch
*** Update File: /Users/tlovo/code_ai/Badge-ai/backend/core/connection.py
@@
-from urllib.parse import parse_qs, urlparse
+from urllib.parse import parse_qs, urlparse
+from core.utils.util import parse_ids_from_handshake
@@
-            device_id_from_query = None
-            client_id_from_query = None
+            device_id_from_query = None
+            client_id_from_query = None
@@
-                # 从候选 path 中解析 query 参数
-                for p in candidate_paths:
-                    try:
-                        parsed_url = urlparse(p)
-                        raw_query = parsed_url.query or ""
-                        if not raw_query:
-                            # 兼容某些环境仅传递了 "?a=b" 作为 path 的情况
-                            if "?" in p and p.endswith("?") is False:
-                                raw_query = p.split("?", 1)[1]
-                        if not raw_query:
-                            continue
-                        query_params = parse_qs(raw_query, keep_blank_values=False)
-                        device_vals = query_params.get("device-id") or query_params.get("device_id")
-                        client_vals = query_params.get("client-id") or query_params.get("client_id")
-                        if device_vals and len(device_vals) > 0:
-                            device_id_from_query = _normalize_id(device_vals[0])
-                            # client-id 缺省时复用 device-id
-                            client_id_from_query = _normalize_id(client_vals[0]) if client_vals else device_id_from_query
-                            break
-                    except Exception:
-                        continue
+                # 从候选 path 中解析 query 参数（统一解析函数）
+                for p in candidate_paths:
+                    try:
+                        did, cid, _ = parse_ids_from_handshake(p)
+                        if did:
+                            device_id_from_query = _normalize_id(did)
+                            client_id_from_query = _normalize_id(cid or did)
+                            break
+                    except Exception:
+                        continue
@@
-                            cached = cache.get(id(ws))
+                            cached = cache.get(id(ws))
                             if isinstance(cached, dict):
                                 did = cached.get("device-id")
                                 cid = cached.get("client-id") or did
                                 device_id_from_query = _normalize_id(did)
                                 client_id_from_query = _normalize_id(cid)
*** End Patch
```

```python
import os
import sys
import copy
import json
import uuid
import time
import queue
import asyncio
import threading
import traceback
from config.logger import truncate_for_log
import subprocess
import websockets
from core.handle.mcpHandle import call_mcp_tool
from core.utils.util import (
    extract_json_from_string,
    check_vad_update,
    check_asr_update,
    filter_sensitive_info,
    parse_ids_from_handshake,
)
from typing import Dict, Any
from core.mcp.manager import MCPManager
from core.utils.modules_initialize import (
    initialize_modules,
    initialize_tts,
    initialize_asr,
)
from core.handle.reportHandle import report
from core.providers.tts.default import DefaultTTS
from concurrent.futures import ThreadPoolExecutor
from core.utils.dialogue import Message, Dialogue
from core.providers.asr.dto.dto import InterfaceType
from core.handle.textHandle import handleTextMessage
from core.handle.functionHandler import FunctionHandler
from plugins_func.loadplugins import auto_import_modules
from plugins_func.register import Action, ActionResponse
from core.auth import AuthMiddleware, AuthenticationError
from config.config_loader import get_private_config_from_api
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
from config.logger import setup_logging, build_module_string, update_module_string
from config.manage_api_client import DeviceNotFoundException, DeviceBindException


TAG = __name__

auto_import_modules("plugins_func.functions")


class TTSException(RuntimeError):
    pass


class ConnectionHandler:
    def __init__(
        self,
        config: Dict[str, Any],
        _vad,
        _asr,
        _llm,
        _memory,
        _intent,
        server=None,
    ):
        self.common_config = config
        self.config = copy.deepcopy(config)
        self.session_id = str(uuid.uuid4())
        self.logger = setup_logging()
        self.server = server  # 保存server实例的引用

        self.auth = AuthMiddleware(config)
        self.need_bind = False
        self.bind_code = None
        self.read_config_from_api = self.config.get("read_config_from_api", False)

        self.websocket = None
        self.headers = None
        self.device_id = None
        self.client_ip = None
        self.client_ip_info = {}
        self.prompt = None
        self.welcome_msg = None
        self.max_output_size = 0
        self.chat_history_conf = 0
        self.audio_format = "opus"

        # 客户端状态相关
        self.client_abort = False
        self.client_is_speaking = False
        self.client_listen_mode = "auto"

        # 线程任务相关（在连接开始时绑定运行中的事件循环）
        self.loop = None
        self.stop_event = threading.Event()
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

        # 添加上报线程池
        self.report_queue = queue.Queue()
        self.report_thread = None
        # 未来可以通过修改此处，调节asr的上报和tts的上报，目前默认都开启
        self.report_asr_enable = self.read_config_from_api
        self.report_tts_enable = self.read_config_from_api

        # 依赖的组件
        self.vad = None
        self.asr = None
        self.tts = None
        self._asr = _asr
        self._vad = _vad
        self.llm = _llm
        self.memory = _memory
        self.intent = _intent

        # vad相关变量
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0.0
        self.client_no_voice_last_time = 0.0
        self.client_voice_stop = False
        self.client_voice_frame_count = 0

        # asr相关变量
        # 因为实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR
        # 所以涉及到ASR的变量，需要在这里定义，属于connection的私有变量
        self.asr_audio = []
        self.asr_audio_queue = queue.Queue()

        # llm相关变量
        self.llm_finish_task = True
        self.dialogue = Dialogue()

        # tts相关变量
        self.sentence_id = None

        # iot相关变量
        self.iot_descriptors = {}
        self.func_handler = None

        # 模式状态（meeting/coding/working）
        self.current_mode = None
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
        # 编码模式日志流运行标志/阶段名（用于 stop/clear/phase 扩展）
        self.coding_stream_running = False
        self.coding_phase_name = ""

        self.cmd_exit = self.config["exit_commands"]
        self.max_cmd_length = 0
        for cmd in self.cmd_exit:
            if len(cmd) > self.max_cmd_length:
                self.max_cmd_length = len(cmd)

        # 是否在聊天结束后关闭连接
        self.close_after_chat = False
        self.load_function_plugin = False
        self.intent_type = "nointent"

        self.timeout_task = None
        # 放宽默认空闲阈值：默认 600s + 60s 兜底；允许配置覆盖
        try:
            base_idle = int(self.config.get("close_connection_no_voice_time", 600))
        except Exception:
            base_idle = 600
        self.timeout_seconds = base_idle + 60  # 第一层之外的兜底关闭

        # {"mcp":true} 表示启用MCP功能
        self.features = None

        # LLM 按模式实例缓存（随连接释放）
        self._llm_cache = {}

    def _get_base_config(self) -> Dict[str, Any]:
        try:
            srv = getattr(self, "server", None)
            base_cfg = getattr(srv, "config", None) if srv else None
            if isinstance(base_cfg, dict):
                return base_cfg
        except Exception:
            pass
        return self.config if isinstance(self.config, dict) else {}

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

        base_cfg = self._get_base_config()
        # 读取映射
        mapping = {}
        try:
            mapping = base_cfg.get("llm_by_mode", {}) or {}
        except Exception:
            mapping = {}

        mapping_val = mapping.get(key, None)
        if mapping_val is None:
            # 用途未配置专用 LLM，回退 default 并记录告警
            try:
                self.logger.bind(tag=TAG).warning(
                    f"get_llm_for: 未找到用途 {key} 的 llm_by_mode 配置，回退到 default"
                )
            except Exception:
                pass
            mapping_val = mapping.get("default")

        alias = None
        overrides = None
        if isinstance(mapping_val, dict):
            # 支持 { alias: xxx, overrides: { model_name: '...' } } 或直接平铺覆盖字段
            alias = mapping_val.get("alias") or mapping_val.get("name") or mapping_val.get("module") or mapping_val.get("llm")
            overrides = mapping_val.get("overrides")
            if overrides is None:
                # 将除别名键外的其余键视为覆盖
                tmp = dict(mapping_val)
                for k in ["alias", "name", "module", "llm", "overrides"]:
                    tmp.pop(k, None)
                overrides = tmp if len(tmp) > 0 else None
        elif isinstance(mapping_val, str) and len(mapping_val) > 0:
            alias = mapping_val

        # 回退默认 alias
        try:
            if alias is None:
                alias = self.config["selected_module"]["LLM"]
        except Exception:
            alias = None

        # 若无覆盖且别名等于当前默认，直接复用
        try:
            current_default_alias = self.config["selected_module"]["LLM"]
            if (overrides is None or len(overrides) == 0) and alias == current_default_alias and getattr(self, "llm", None) is not None:
                self._llm_cache[key] = self.llm
                return self.llm
        except Exception:
            pass

        # 构造/复用实例（合并覆盖）：优先使用 server 级共享注册表
        try:
            from core.utils import llm as llm_utils
            base_conf = None
            if alias:
                base_conf = copy.deepcopy(self.config.get("LLM", {}).get(alias))
                # 若连接级配置未包含该别名，尝试从服务器级配置读取（支持热更）
                if not base_conf:
                    try:
                        srv = getattr(self, "server", None)
                        srv_cfg = getattr(srv, "config", None) if srv else None
                        if isinstance(srv_cfg, dict):
                            base_conf = copy.deepcopy(srv_cfg.get("LLM", {}).get(alias))
                    except Exception:
                        pass
            if not base_conf:
                # 回退：无对应配置则复用默认，并给出一次告警
                try:
                    self.logger.bind(tag=TAG).warning(
                        f"get_llm_for: llm_by_mode[{key}] 别名未命中(alias={alias}), 回退默认LLM"
                    )
                except Exception:
                    pass
                self._llm_cache[key] = self.llm
                return self.llm
            # 若 server 提供共享注册表，优先复用
            try:
                srv = getattr(self, "server", None)
                if srv and hasattr(srv, "get_or_create_llm") and callable(getattr(srv, "get_or_create_llm")):
                    instance = srv.get_or_create_llm(alias, overrides)
                else:
                    # 直接合并覆盖并创建独立实例
                    if overrides and isinstance(overrides, dict):
                        for k, v in overrides.items():
                            base_conf[k] = v
                    llm_type = base_conf.get("type", alias)
                    instance = llm_utils.create_instance(llm_type, base_conf)
            except Exception:
                if overrides and isinstance(overrides, dict):
                    for k, v in overrides.items():
                        base_conf[k] = v
                llm_type = base_conf.get("type", alias)
                instance = llm_utils.create_instance(llm_type, base_conf)
            self._llm_cache[key] = instance
            return instance
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"get_llm_for 失败({key}): {e}，回退默认LLM")
            self._llm_cache[key] = self.llm
            return self.llm

    async def handle_connection(self, ws, path=None):
        try:
            # 绑定当前运行事件循环供跨线程调度使用
            try:
                self.loop = asyncio.get_running_loop()
            except Exception:
                self.loop = asyncio.get_event_loop()
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
                self.headers = headers_lower
            except Exception:
                self.headers = {}

            # 优先从 URL 查询参数解析 device-id/client-id；其次尝试 Header；最后回退

            def _normalize_id(value: str | None) -> str | None:
                if value is None:
                    return None
                try:
                    v = str(value).strip().strip('"').strip("'")
                    if v == "":
                        return None
                    return v.lower()
                except Exception:
                    return None

            device_id_from_query = None
            client_id_from_query = None
            try:
                candidate_paths = []
                if isinstance(path, str) and len(path) > 0:
                    candidate_paths.append(path)
                ws_path = getattr(ws, "path", "")
                if isinstance(ws_path, str) and len(ws_path) > 0 and ws_path not in candidate_paths:
                    candidate_paths.append(ws_path)
                # 兼容不同版本 websockets 的属性命名，尽量获取带 query 的原始 URI
                for attr in ["request_uri", "raw_request_uri", "request_path", "raw_path"]:
                    try:
                        val = getattr(ws, attr, "")
                        if isinstance(val, str) and len(val) > 0 and val not in candidate_paths:
                            candidate_paths.append(val)
                    except Exception:
                        pass
                # 从候选 path 中解析 query 参数（统一解析函数）
                for p in candidate_paths:
                    try:
                        did, cid, _ = parse_ids_from_handshake(p)
                        if did:
                            device_id_from_query = _normalize_id(did)
                            client_id_from_query = _normalize_id(cid or did)
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            # 兜底：从 server 的握手缓存读取（适配 websockets 传参差异）
            try:
                server_obj = getattr(self, "server", None)
                if (device_id_from_query is None) and server_obj is not None:
                    cache = getattr(server_obj, "_handshake_cache", None)
                    if isinstance(cache, dict):
                        # 按连接对象 id 存储
                        cached = cache.get(id(ws))
                        if isinstance(cached, dict):
                            did = cached.get("device-id")
                            cid = cached.get("client-id") or did
                            device_id_from_query = _normalize_id(did)
                            client_id_from_query = _normalize_id(cid)
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
                # 打印来源与解析快照（包含原始 path 片段便于定位异常客户端）
                try:
                    raw_paths_snapshot = []
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                        for attr in ["request_uri", "raw_request_uri", "request_path", "raw_path"]:
                            val = getattr(ws, attr, "")
                            if isinstance(val, str) and val:
                                raw_paths_snapshot.append(val[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    src = "query" if device_id_from_query else "header"
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={src}, rawPaths={truncate_for_log(str(raw_paths_snapshot))})"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={'query' if device_id_from_query else 'header'})"
                    )
            else:
                # 容错：仍未取到则自动分配，保证连接可用；同时输出诊断快照
                auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
                self.headers["device-id"] = auto_device_id
                self.headers["client-id"] = auto_device_id
                try:
                    raw_paths_snapshot = []
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    header_keys = list(self.headers.keys())
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}; rawPaths={truncate_for_log(str(raw_paths_snapshot))}, headerKeys={truncate_for_log(str(header_keys))}"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}"
                    )
            # 获取客户端ip地址
            try:
                remote = getattr(ws, "remote_address", None)
                if isinstance(remote, tuple) and len(remote) >= 1:
                    self.client_ip = remote[0]
                else:
                    self.client_ip = str(remote) if remote is not None else ""
            except Exception:
                self.client_ip = ""
            self.logger.bind(tag=TAG).info(
                f"{self.client_ip} conn - Headers: {self.headers}"
            )

            # 进行认证
            await self.auth.authenticate(self.headers)

            # 认证通过,继续处理
            self.websocket = ws
            self.device_id = self.headers.get("device-id", None)
            # 在 server 上注册设备路由（自动断开旧连接）
            if self.server and self.device_id:
                ok = await self.server.register_device_handler(self.device_id, self)
                if ok is False:
                    self.logger.bind(tag=TAG).error(f"设备注册失败: {self.device_id}")
                    await ws.send("设备注册失败")
                    await self.close(ws)
                    return

            # 启动超时检查任务
            self.timeout_task = asyncio.create_task(self._check_timeout())

            self.welcome_msg = self.config["xiaozhi"]
            self.welcome_msg["session_id"] = self.session_id
            await self.send_json(self.welcome_msg)

            # 获取差异化配置
            self._initialize_private_config()
            # 异步初始化
            self.executor.submit(self._initialize_components)

            try:
                async for message in self.websocket:
                    await self._route_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.bind(tag=TAG).info("客户端断开连接")

        except AuthenticationError as e:
            self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
            return
        except Exception as e:
            stack_trace = traceback.format_exc()
            try:
                safe_e = truncate_for_log(str(e))
                safe_tb = truncate_for_log(stack_trace)
            except Exception:
                safe_e = str(e)
                safe_tb = stack_trace
            self.logger.bind(tag=TAG).error(f"Connection error: {safe_e}-{safe_tb}")
            return
        finally:
            try:
                # 注销设备路由映射
                if self.server and self.device_id:
                    await self.server.unregister_device_handler(self.device_id, self)
            finally:
                await self._save_and_close(ws)

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

    def reset_timeout(self):
        """重置超时计时器"""
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
        self.timeout_task = asyncio.create_task(self._check_timeout())

    async def _route_message(self, message):
        """消息路由"""
        # 重置超时计时器
        self.reset_timeout()

        if isinstance(message, str):
            # 轻量 ping/keepalive：收到后仅重置计时器并忽略
            try:
                import json as _json
                try:
                    obj = _json.loads(message)
                except Exception:
                    obj = None
                if isinstance(obj, dict) and obj.get("type") in ("ping", "keepalive"):
                    try:
                        # 可选：立即回 pong
                        await self.websocket.send(_json.dumps({"type": "pong"}))
                    except Exception:
                        pass
                    return
            except Exception:
                pass
            await handleTextMessage(self, message)
        elif isinstance(message, bytes):
            if self.vad is None:
                return
            if self.asr is None:
                return
            self.asr_audio_queue.put(message)

    async def handle_restart(self, message):
        """处理服务器重启请求"""
        try:

            self.logger.bind(tag=TAG).info("收到服务器重启指令，准备执行...")

            # 发送确认响应
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "success",
                        "message": "服务器重启中...",
                        "content": {"action": "restart"},
                    }
                )
            )

            # 异步执行重启操作
            def restart_server():
                """实际执行重启的方法"""
                time.sleep(1)
                self.logger.bind(tag=TAG).info("执行服务器重启...")
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
                os._exit(0)

            # 使用线程执行重启避免阻塞事件循环
            threading.Thread(target=restart_server, daemon=True).start()

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"重启失败: {str(e)}")
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "error",
                        "message": f"Restart failed: {str(e)}",
                        "content": {"action": "restart"},
                    }
                )
            )

    def _initialize_components(self):
        try:
            self.selected_module_str = build_module_string(
                self.config.get("selected_module", {})
            )
            update_module_string(self.selected_module_str)
            """初始化组件"""
            if self.config.get("prompt") is not None:
                self.prompt = self.config["prompt"]
                self.change_system_prompt(self.prompt)
                self.logger.bind(tag=TAG).info(
                    f"初始化组件: prompt成功 {self.prompt[:50]}..."
                )

            """初始化本地组件"""
            if self.vad is None:
                self.vad = self._vad
            if self.asr is None:
                self.asr = self._initialize_asr()
            # 打开语音识别通道
            asyncio.run_coroutine_threadsafe(self.asr.open_audio_channels(self), self.loop)

            if self.tts is None:
                self.tts = self._initialize_tts()
            # 会议模式可禁用 TTS 通道（懒启动）
            disable_tts = False
            try:
                srv = getattr(self, "server", None)
                base_cfg = getattr(srv, "config", None) if srv else None
                if isinstance(base_cfg, dict):
                    meeting_cfg2 = base_cfg.get("meeting", {})
                else:
                    meeting_cfg2 = self.config.get("meeting", {})
                disable_tts = bool(meeting_cfg2.get("disable_tts", False))
            except Exception:
                disable_tts = False
            if not disable_tts:
                asyncio.run_coroutine_threadsafe(self.tts.open_audio_channels(self), self.loop)

            """加载记忆"""
            self._initialize_memory()
            """加载意图识别"""
            self._initialize_intent()
            """初始化上报线程"""
            self._init_report_threads()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"实例化组件失败: {e}")

    def _init_report_threads(self):
        """初始化ASR和TTS上报线程"""
        if not self.read_config_from_api or self.need_bind:
            return
        if self.chat_history_conf == 0:
            return
        if self.report_thread is None or not self.report_thread.is_alive():
            self.report_thread = threading.Thread(
                target=self._report_worker, daemon=True
            )
            self.report_thread.start()
            self.logger.bind(tag=TAG).info("TTS上报线程已启动")

    def _initialize_tts(self):
        """初始化TTS"""
        tts = None
        if not self.need_bind:
            tts = initialize_tts(self.config)

        if tts is None:
            tts = DefaultTTS(self.config, delete_audio_file=True)

        return tts

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

    def _initialize_private_config(self):
        """如果是从配置文件获取，则进行二次实例化"""
        if not self.read_config_from_api:
            return
        """从接口获取差异化的配置进行二次实例化，非全量重新实例化"""
        try:
            begin_time = time.time()
            private_config = get_private_config_from_api(
                self.config,
                self.headers.get("device-id"),
                self.headers.get("client-id", self.headers.get("device-id")),
            )
            private_config["delete_audio"] = bool(self.config.get("delete_audio", True))
            self.logger.bind(tag=TAG).info(
                f"{time.time() - begin_time} 秒，获取差异化配置成功: {json.dumps(filter_sensitive_info(private_config), ensure_ascii=False)}"
            )
        except DeviceNotFoundException as e:
            self.need_bind = True
            private_config = {}
        except DeviceBindException as e:
            self.need_bind = True
            self.bind_code = e.bind_code
            private_config = {}
        except Exception as e:
            self.need_bind = True
            self.logger.bind(tag=TAG).error(f"获取差异化配置失败: {e}")
            private_config = {}

        init_llm, init_tts, init_memory, init_intent = (
            False,
            False,
            False,
            False,
        )

        init_vad = check_vad_update(self.common_config, private_config)
        init_asr = check_asr_update(self.common_config, private_config)

        if init_vad:
            self.config["VAD"] = private_config["VAD"]
            self.config["selected_module"]["VAD"] = private_config["selected_module"][
                "VAD"
            ]
        if init_asr:
            self.config["ASR"] = private_config["ASR"]
            self.config["selected_module"]["ASR"] = private_config["selected_module"][
                "ASR"
            ]
        if private_config.get("TTS", None) is not None:
            init_tts = True
            self.config["TTS"] = private_config["TTS"]
            self.config["selected_module"]["TTS"] = private_config["selected_module"][
                "TTS"
            ]
        if private_config.get("LLM", None) is not None:
            init_llm = True
            self.config["LLM"] = private_config["LLM"]
            self.config["selected_module"]["LLM"] = private_config["selected_module"][
                "LLM"
            ]
        if private_config.get("Memory", None) is not None:
            init_memory = True
            self.config["Memory"] = private_config["Memory"]
            self.config["selected_module"]["Memory"] = private_config[
                "selected_module"
            ]["Memory"]
        if private_config.get("Intent", None) is not None:
            init_intent = True
            self.config["Intent"] = private_config["Intent"]
            model_intent = private_config.get("selected_module", {}).get("Intent", {})
            self.config["selected_module"]["Intent"] = model_intent
            # 加载插件配置
            if model_intent != "Intent_nointent":
                plugin_from_server = private_config.get("plugins", {})
                for plugin, config_str in plugin_from_server.items():
                    plugin_from_server[plugin] = json.loads(config_str)
                self.config["plugins"] = plugin_from_server
                self.config["Intent"][self.config["selected_module"]["Intent"]][
                    "functions"
                ] = plugin_from_server.keys()
        if private_config.get("prompt", None) is not None:
            self.config["prompt"] = private_config["prompt"]
        if private_config.get("summaryMemory", None) is not None:
            self.config["summaryMemory"] = private_config["summaryMemory"]
        if private_config.get("device_max_output_size", None) is not None:
            self.max_output_size = int(private_config["device_max_output_size"])
        if private_config.get("chat_history_conf", None) is not None:
            self.chat_history_conf = int(private_config["chat_history_conf"])
        try:
            modules = initialize_modules(
                self.logger,
                private_config,
                init_vad,
                init_asr,
                init_llm,
                init_tts,
                init_memory,
                init_intent,
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"初始化组件失败: {e}")
            modules = {}
        if modules.get("tts", None) is not None:
            self.tts = modules["tts"]
        if modules.get("vad", None) is not None:
            self.vad = modules["vad"]
        if modules.get("asr", None) is not None:
            self.asr = modules["asr"]
        if modules.get("llm", None) is not None:
            self.llm = modules["llm"]
        if modules.get("intent", None) is not None:
            self.intent = modules["intent"]
        if modules.get("memory", None) is not None:
            self.memory = modules["memory"]

    def _initialize_memory(self):
        if self.memory is None:
            return
        """初始化记忆模块"""
        # 按模式选择记忆总结 LLM（可被 llm_by_mode.memory 覆盖）
        chosen_llm = self.llm
        try:
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                selected = self.get_llm_for("memory")
                if selected is not None:
                    chosen_llm = selected
        except Exception:
            pass

        self.memory.init_memory(
            role_id=self.device_id,
            llm=chosen_llm,
            summary_memory=self.config.get("summaryMemory", None),
            save_to_file=not self.read_config_from_api,
        )

        # 获取记忆总结配置
        memory_config = self.config["Memory"]
        memory_type = self.config["Memory"][self.config["selected_module"]["Memory"]][
            "type"
        ]
        # 如果使用 nomen，直接返回
        if memory_type == "nomem":
            return
        # 使用 mem_local_short 模式
        elif memory_type == "mem_local_short":
            memory_llm_name = memory_config[self.config["selected_module"]["Memory"]][
                "llm"
            ]
            if memory_llm_name and memory_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                memory_llm_config = self.config["LLM"][memory_llm_name]
                memory_llm_type = memory_llm_config.get("type", memory_llm_name)
                memory_llm = llm_utils.create_instance(
                    memory_llm_type, memory_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为记忆总结创建了专用LLM: {memory_llm_name}, 类型: {memory_llm_type}"
                )
                self.memory.set_llm(memory_llm)
            else:
                # 否则使用主LLM
                self.memory.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

    def _initialize_intent(self):
        if self.intent is None:
            return
        self.intent_type = self.config["Intent"][
            self.config["selected_module"]["Intent"]
        ]["type"]
        if self.intent_type == "function_call" or self.intent_type == "intent_llm":
            self.load_function_plugin = True
        """初始化意图识别模块"""
        # 获取意图识别配置
        intent_config = self.config["Intent"]
        intent_type = self.config["Intent"][self.config["selected_module"]["Intent"]][
            "type"
        ]

        # 如果使用 nointent，直接返回
        if intent_type == "nointent":
            return
        # 使用 intent_llm 模式
        elif intent_type == "intent_llm":
            intent_llm_name = intent_config[self.config["selected_module"]["Intent"]][
                "llm"
            ]

            if intent_llm_name and intent_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                intent_llm_config = self.config["LLM"][intent_llm_name]
                intent_llm_type = intent_llm_config.get("type", intent_llm_name)
                intent_llm = llm_utils.create_instance(
                    intent_llm_type, intent_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为意图识别创建了专用LLM: {intent_llm_name}, 类型: {intent_llm_type}"
                )
                # 按模式选择意图识别 LLM（可被 llm_by_mode.intent 覆盖）
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(intent_llm)
                    else:
                        self.intent.set_llm(intent_llm)
                except Exception:
                    self.intent.set_llm(intent_llm)
            else:
                # 否则使用主LLM
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(self.llm)
                    else:
                        self.intent.set_llm(self.llm)
                except Exception:
                    self.intent.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

        """加载插件"""
        self.func_handler = FunctionHandler(self)
        self.mcp_manager = MCPManager(self)

        """加载MCP工具"""
        asyncio.run_coroutine_threadsafe(
            self.mcp_manager.initialize_servers(), self.loop
        )

    def change_system_prompt(self, prompt):
        self.prompt = prompt
        # 更新系统prompt至上下文
        self.dialogue.update_system_message(self.prompt)

    def chat(self, query, tool_call=False):
        try:
            safe_query = truncate_for_log(query)
        except Exception:
            safe_query = query
        self.logger.bind(tag=TAG).info(f"大模型收到用户消息: {safe_query}")
        self.llm_finish_task = False

        if not tool_call:
            self.dialogue.put(Message(role="user", content=query))

        # Define intent functions
        functions = None
        if self.intent_type == "function_call" and hasattr(self, "func_handler"):
            functions = self.func_handler.get_functions()
        if hasattr(self, "mcp_client"):
            mcp_tools = self.mcp_client.get_available_tools()
            if mcp_tools is not None and len(mcp_tools) > 0:
                if functions is None:
                    functions = []
                functions.extend(mcp_tools)
        response_message = []

        try:
            # 使用带记忆的对话
            memory_str = None
            if self.memory is not None:
                future = asyncio.run_coroutine_threadsafe(
                    self.memory.query_memory(query), self.loop
                )
                memory_str = future.result()

            self.sentence_id = str(uuid.uuid4().hex)


            # 按当前模式选择 LLM（默认chat；coding/working 切换对应别名）
            purpose = self.current_mode or "chat"
            active_llm = self.llm
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                try:
                    active_llm = self.get_llm_for(purpose) or self.llm
                except Exception:
                    active_llm = self.llm

            if self.intent_type == "function_call" and functions is not None:
                # 使用支持functions的streaming接口
                llm_responses = active_llm.response_with_functions(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                    functions=functions,
                )
            else:
                llm_responses = active_llm.response(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM 处理出错 {query}: {e}")
            return None

        # 处理流式响应
        tool_call_flag = False
        function_name = None
        function_id = None
        function_arguments = ""
        content_arguments = ""
        text_index = 0
        self.client_abort = False
        for response in llm_responses:
            if self.client_abort:
                break
            if self.intent_type == "function_call" and functions is not None:
                content, tools_call = response
                if "content" in response:
                    content = response["content"]
                    tools_call = None
                if content is not None and len(content) > 0:
                    content_arguments += content

                if not tool_call_flag and content_arguments.startswith("<tool_call>"):
                    # print("content_arguments", content_arguments)
                    tool_call_flag = True

                if tools_call is not None and len(tools_call) > 0:
                    tool_call_flag = True
                    if tools_call[0].id is not None:
                        function_id = tools_call[0].id
                    if tools_call[0].function.name is not None:
                        function_name = tools_call[0].function.name
                    if tools_call[0].function.arguments is not None:
                        function_arguments += tools_call[0].function.arguments
            else:
                content = response
            if content is not None and len(content) > 0:
                if not tool_call_flag:
                    response_message.append(content)
                    if text_index == 0:
                        self.tts.tts_text_queue.put(
                            TTSMessageDTO(
                                sentence_id=self.sentence_id,
                                sentence_type=SentenceType.FIRST,
                                content_type=ContentType.ACTION,
                            )
                        )
                    self.tts.tts_text_queue.put(
                        TTSMessageDTO(
                            sentence_id=self.sentence_id,
                            sentence_type=SentenceType.MIDDLE,
                            content_type=ContentType.TEXT,
                            content_detail=content,
                        )
                    )
                    text_index += 1
        # 处理function call
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
            if not bHasError:
                response_message.clear()
                self.logger.bind(tag=TAG).debug(
                    f"function_name={function_name}, function_id={function_id}, function_arguments={function_arguments}"
                )
                function_call_data = {
                    "name": function_name,
                    "id": function_id,
                    "arguments": function_arguments,
                }

                # 处理Server端MCP工具调用
                if self.mcp_manager.is_mcp_tool(function_name):
                    result = self._handle_mcp_tool_call(function_call_data)
                elif hasattr(self, "mcp_client") and self.mcp_client.has_tool(
                    function_name
                ):
                    # 如果是小智端MCP工具调用
                    self.logger.bind(tag=TAG).debug(
                        f"调用小智端MCP工具: {function_name}, 参数: {function_arguments}"
                    )
                    try:
                        result = asyncio.run_coroutine_threadsafe(
                            call_mcp_tool(
                                self, self.mcp_client, function_name, function_arguments
                            ),
                            self.loop,
                        ).result()
                        self.logger.bind(tag=TAG).debug(f"MCP工具调用结果: {result}")

                        resultJson = None
                        if isinstance(result, str):
                            try:
                                resultJson = json.loads(result)
                            except Exception as e:
                                self.logger.bind(tag=TAG).error(
                                    f"解析MCP工具返回结果失败: {e}"
                                )

                        # 视觉大模型不经过二次LLM处理
                        if (
                            resultJson is not None
                            and isinstance(resultJson, dict)
                            and "action" in resultJson
                        ):
                            result = ActionResponse(
                                action=Action[resultJson["action"]],
                                result=None,
                                response=resultJson.get("response", ""),
                            )
                        else:
                            result = ActionResponse(
                                action=Action.REQLLM, result=result, response=""
                            )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"MCP工具调用失败: {e}")
                        result = ActionResponse(
                            action=Action.REQLLM, result="MCP工具调用失败", response=""
                        )
                else:
                    # 处理系统函数
                    result = self.func_handler.handle_llm_function_call(
                        self, function_call_data
                    )
                self._handle_function_result(result, function_call_data)

        # 存储对话内容
        if len(response_message) > 0:
            self.dialogue.put(
                Message(role="assistant", content="".join(response_message))
            )
        if text_index > 0:
            self.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=self.sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )
        self.llm_finish_task = True
        self.logger.bind(tag=TAG).debug(
            json.dumps(self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False)
        )

        return True

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

            tool_result = asyncio.run_coroutine_threadsafe(
                self.mcp_manager.execute_tool(function_name, args_dict), self.loop
            ).result()
            # meta=None content=[TextContent(type='text', text='北京当前天气:\n温度: 21°C\n天气: 晴\n湿度: 6%\n风向: 西北 风\n风力等级: 5级', annotations=None)] isError=False
            content_text = ""
            if tool_result is not None and tool_result.content is not None:
                for content in tool_result.content:
                    content_type = content.type
                    if content_type == "text":
                        content_text = content.text
                    elif content_type == "image":
                        pass

            if len(content_text) > 0:
                return ActionResponse(
                    action=Action.REQLLM, result=content_text, response=""
                )

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP工具调用错误: {e}")
            return ActionResponse(
                action=Action.REQLLM, result="工具调用出错", response=""
            )

        return ActionResponse(action=Action.REQLLM, result="工具调用出错", response="")

    def _handle_function_result(self, result, function_call_data):
        if result.action == Action.RESPONSE:  # 直接回复前端
            text = result.response
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        elif result.action == Action.REQLLM:  # 调用函数后再请求llm生成回复
            text = result.result
            if text is not None and len(text) > 0:
                function_id = function_call_data["id"]
                function_name = function_call_data["name"]
                function_arguments = function_call_data["arguments"]
                self.dialogue.put(
                    Message(
                        role="assistant",
                        tool_calls=[
                            {
                                "id": function_id,
                                "function": {
                                    "arguments": function_arguments,
                                    "name": function_name,
                                },
                                "type": "function",
                                "index": 0,
                            }
                        ],
                    )
                )

                self.dialogue.put(
                    Message(
                        role="tool",
                        tool_call_id=(
                            str(uuid.uuid4()) if function_id is None else function_id
                        ),
                        content=text,
                    )
                )
                self.chat(text, tool_call=True)
        elif result.action == Action.NOTFOUND or result.action == Action.ERROR:
            text = result.result
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        else:
            pass

    def _report_worker(self):
        """聊天记录上报工作线程"""
        while not self.stop_event.is_set():
            try:
                # 从队列获取数据，设置超时以便定期检查停止事件
                item = self.report_queue.get(timeout=1)
                if item is None:  # 检测毒丸对象
                    break
                type, text, audio_data, report_time = item
                try:
                    # 检查线程池状态
                    if self.executor is None:
                        continue
                    # 提交任务到线程池
                    self.executor.submit(
                        self._process_report, type, text, audio_data, report_time
                    )
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"聊天记录上报线程异常: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"聊天记录上报工作线程异常: {e}")

        self.logger.bind(tag=TAG).info("聊天记录上报线程已退出")

    def _process_report(self, type, text, audio_data, report_time):
        """处理上报任务"""
        try:
            # 执行上报（传入二进制数据）
            report(self, type, text, audio_data, report_time)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"上报处理异常: {e}")
        finally:
            # 标记任务完成
            self.report_queue.task_done()

    def clearSpeakStatus(self):
        self.client_is_speaking = False
        self.logger.bind(tag=TAG).debug(f"清除服务端讲话状态")

    async def close(self, ws=None):
        """资源清理方法"""
        try:
            # 取消超时任务
            if self.timeout_task:
                self.timeout_task.cancel()
                self.timeout_task = None

            # 取消编码洞察定时任务
            try:
                if hasattr(self, "coding_insight_task") and self.coding_insight_task and not self.coding_insight_task.done():
                    self.coding_insight_task.cancel()
            except Exception:
                pass

            # 清理MCP资源
            if hasattr(self, "mcp_manager") and self.mcp_manager:
                await self.mcp_manager.cleanup_all()

            # 触发停止事件
            if self.stop_event:
                self.stop_event.set()

            # 清空任务队列
            self.clear_queues()

            # 关闭WebSocket连接
            if ws:
                await ws.close()
            elif self.websocket:
                await self.websocket.close()

            # 最后关闭线程池（避免阻塞）
            if self.executor:
                try:
                    # Python 3.9+ 支持 cancel_futures
                    self.executor.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    self.executor.shutdown(wait=False)
                self.executor = None

            # 清理 LLM 实例缓存
            try:
                if hasattr(self, "_llm_cache") and isinstance(self._llm_cache, dict):
                    self._llm_cache.clear()
            except Exception:
                pass

            # 关闭 asr/tts/llm 资源
            try:
                if hasattr(self, "asr") and hasattr(self.asr, "close") and callable(getattr(self.asr, "close")):
                    maybe_close = self.asr.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "tts") and hasattr(self.tts, "close") and callable(getattr(self.tts, "close")):
                    maybe_close = self.tts.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "llm") and hasattr(self.llm, "close") and callable(getattr(self.llm, "close")):
                    maybe_close = self.llm.close()  # 供应商可选实现
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass

            self.logger.bind(tag=TAG).info("连接资源已释放")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"关闭连接时出错: {e}")

    def clear_queues(self):
        """清空所有任务队列"""
        if self.tts:
            self.logger.bind(tag=TAG).debug(
                f"开始清理: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

            # 使用非阻塞方式清空队列
            for q in [
                self.tts.tts_text_queue,
                self.tts.tts_audio_queue,
                self.report_queue,
            ]:
                if not q:
                    continue
                while True:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break

            self.logger.bind(tag=TAG).debug(
                f"清理结束: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

    def reset_vad_states(self):
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0
        self.client_voice_stop = False
        self.logger.bind(tag=TAG).debug("VAD states reset.")

    async def send_text(self, text: str) -> None:
        """统一文本发送包装。"""
        try:
            if self.websocket:
                await self.websocket.send(text)
        except Exception:
            pass

    async def send_json(self, payload: dict) -> None:
        """统一 JSON 发送包装，自动兼容 send_json 缺失并回退字符串。"""
        try:
            if self.websocket is None:
                return
            try:
                await self.websocket.send_json(payload)
            except AttributeError:
                import json as _json
                await self.websocket.send(_json.dumps(payload, ensure_ascii=False))
        except Exception:
            # 发送错误不应中断主流程
            pass

    def chat_and_close(self, text):
        """Chat with the user and then close the connection"""
        try:
            # Use the existing chat method
            self.chat(text)

            # After chat is complete, close the connection
            self.close_after_chat = True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Chat and close error: {str(e)}")

    async def _check_timeout(self):
        """检查连接超时"""
        try:
            while not self.stop_event.is_set():
                await asyncio.sleep(self.timeout_seconds)
                if not self.stop_event.is_set():
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
                    if self.stop_event.is_set():
                        break
                    self.logger.bind(tag=TAG).info("连接超时，准备关闭")
                    await self.close(self.websocket)
                    break
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"超时检查任务出错: {e}")

```

```python
*** Begin Patch
*** Update File: /Users/tlovo/code_ai/Badge-ai/backend/core/handle/textHandle.py
@@
-            try:
-                from config.logger import truncate_for_log
-                safe_msg = truncate_for_log(message)
-            except Exception:
-                safe_msg = message
-            conn.logger.bind(tag=TAG).info(f"收到hello消息：{safe_msg}")
-            await handleHelloMessage(conn, msg_json)
+            try:
+                from config.logger import truncate_for_log
+                safe_msg = truncate_for_log(message)
+            except Exception:
+                safe_msg = message
+            conn.logger.bind(tag=TAG).info(f"收到hello消息：{safe_msg}")
+            await handleHelloMessage(conn, msg_json)
@@
-                                await conn.websocket.send(
-                                    json.dumps(
-                                        {
-                                            "type": "stt",
-                                            "text": original_text,
-                                            "intent": "mode_switch",
-                                            "target_mode": "working",
-                                            "session_id": getattr(conn, "session_id", ""),
-                                        },
-                                        ensure_ascii=False,
-                                    )
-                                )
+                                await conn.send_json({
+                                    "type": "stt",
+                                    "text": original_text,
+                                    "intent": "mode_switch",
+                                    "target_mode": "working",
+                                    "session_id": getattr(conn, "session_id", ""),
+                                })
@@
-                                    try:
-                                        await conn.websocket.send(json.dumps({
-                                            "type": "workflow",
-                                            "event": "command",
-                                            "intent": intent,
-                                        }, ensure_ascii=False))
-                                    except Exception:
-                                        pass
+                                    try:
+                                        await conn.send_json({
+                                            "type": "workflow",
+                                            "event": "command",
+                                            "intent": intent,
+                                        })
+                                    except Exception:
+                                        pass
@@
-                                        try:
-                                            await conn.websocket.send_json(envelope)
-                                        except AttributeError:
-                                            await conn.websocket.send(json.dumps(envelope, ensure_ascii=False))
+                                        try:
+                                            await conn.send_json(envelope)
+                                        except Exception:
+                                            pass
@@
-                        if mode == "meeting":
-                            conn.client_listen_mode = "auto"
+                        if mode == "meeting":
+                            conn.client_listen_mode = "auto"
@@
-                                await conn.websocket.send(json.dumps({
-                                    "type": "meeting",
-                                    "phase": "finalize",
-                                    "sessionId": getattr(conn, "session_id", ""),
-                                    "startedAt": ack_started_at,
-                                    "pendingCount": pending_count,
-                                }, ensure_ascii=False))
+                                await conn.send_json({
+                                    "type": "meeting",
+                                    "phase": "finalize",
+                                    "sessionId": getattr(conn, "session_id", ""),
+                                    "startedAt": ack_started_at,
+                                    "pendingCount": pending_count,
+                                })
@@
-                                     from core.utils.tasks_store import get_task_store
+                                     from core.utils.tasks_store import get_task_store
                                      tasks = get_task_store().list_by_group(group_key)
                                      envelope = {"type": "workflow", "event": "update", "tasks": tasks}
-                                     try:
-                                         await conn.websocket.send_json(envelope)
-                                     except AttributeError:
-                                         await conn.websocket.send(json.dumps(envelope, ensure_ascii=False))
+                                     try:
+                                         await conn.send_json(envelope)
+                                     except Exception:
+                                         pass
@@
-                    await conn.websocket.send(
-                        json.dumps({
-                            "type": "mode",
-                            "status": "error",
-                            "message": "invalid state or mode"
-                        })
-                    )
+                    await conn.send_json({
+                        "type": "mode",
+                        "status": "error",
+                        "message": "invalid state or mode"
+                    })
@@
-                    await conn.websocket.send(
-                        json.dumps({"type": "peer", "status": "error", "message": "invalid to/payload"})
-                    )
+                    await conn.send_json({"type": "peer", "status": "error", "message": "invalid to/payload"})
@@
-                await conn.websocket.send(
-                    json.dumps(
-                        {
-                            "type": "server",
-                            "status": "error",
-                            "message": "服务器密钥验证失败",
-                        }
-                    )
-                )
+                await conn.send_json({
+                    "type": "server",
+                    "status": "error",
+                    "message": "服务器密钥验证失败",
+                })
@@
-                        await conn.websocket.send(
-                            json.dumps(
-                                {
-                                    "type": "server",
-                                    "status": "error",
-                                    "message": "无法获取服务器实例",
-                                    "content": {"action": "update_config"},
-                                }
-                            )
-                        )
+                        await conn.send_json({
+                            "type": "server",
+                            "status": "error",
+                            "message": "无法获取服务器实例",
+                            "content": {"action": "update_config"},
+                        })
@@
-                        await conn.websocket.send(
-                            json.dumps(
-                                {
-                                    "type": "server",
-                                    "status": "error",
-                                    "message": "更新服务器配置失败",
-                                    "content": {"action": "update_config"},
-                                }
-                            )
-                        )
+                        await conn.send_json({
+                            "type": "server",
+                            "status": "error",
+                            "message": "更新服务器配置失败",
+                            "content": {"action": "update_config"},
+                        })
@@
-                    await conn.websocket.send(
-                        json.dumps(
-                            {
-                                "type": "server",
-                                "status": "success",
-                                "message": "配置更新成功",
-                                "content": {"action": "update_config"},
-                            }
-                        )
-                    )
+                    await conn.send_json({
+                        "type": "server",
+                        "status": "success",
+                        "message": "配置更新成功",
+                        "content": {"action": "update_config"},
+                    })
@@
-                    await conn.websocket.send(
-                        json.dumps(
-                            {
-                                "type": "server",
-                                "status": "error",
-                                "message": f"更新配置失败: {str(e)}",
-                                "content": {"action": "update_config"},
-                            }
-                        )
-                    )
+                    await conn.send_json({
+                        "type": "server",
+                        "status": "error",
+                        "message": f"更新配置失败: {str(e)}",
+                        "content": {"action": "update_config"},
+                    })
*** End Patch
```

```python
*** Begin Patch
*** Update File: /Users/tlovo/code_ai/Badge-ai/backend/core/handle/textHandle.py
@@
-                                await conn.websocket.send(
-                                    json.dumps(
-                                        {
-                                            "type": "stt",
-                                            "text": original_text,
-                                            "intent": "mode_switch",
-                                            "target_mode": "working",
-                                            "session_id": getattr(conn, "session_id", ""),
-                                        },
-                                        ensure_ascii=False,
-                                    )
-                                )
+                                await conn.send_json({
+                                    "type": "stt",
+                                    "text": original_text,
+                                    "intent": "mode_switch",
+                                    "target_mode": "working",
+                                    "session_id": getattr(conn, "session_id", ""),
+                                })
@@
-                                        await conn.websocket.send_json(envelope)
+                                        await conn.send_json(envelope)
@@
-                                         await conn.websocket.send(json.dumps(envelope, ensure_ascii=False))
+                                         pass
*** End Patch
```

```python
import json
from core.handle.abortHandle import handleAbortMessage
from core.handle.helloHandle import handleHelloMessage
from core.handle.mcpHandle import handle_mcp_message
from core.handle.peerHandle import handle_peer_message
from core.handle.meeting_handle import handle_meeting_message
from core.handle.coding_handle import handle_coding_message
from core.handle.workflow_handle import handle_workflow_message
from core.utils.util import remove_punctuation_and_length, filter_sensitive_info
from core.handle.receiveAudioHandle import startToChat, handleAudioMessage
from core.handle.sendAudioHandle import send_stt_message, send_tts_message
from core.handle.iotHandle import handleIotDescriptors, handleIotStatus
from core.handle.reportHandle import enqueue_asr_report
import asyncio
import time
from core.handle.meeting_handle import finalize_meeting_and_send_summary

TAG = __name__


async def handleTextMessage(conn, message):
    """处理文本消息"""
    try:
        msg_json = json.loads(message)
        if isinstance(msg_json, int):
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message if isinstance(message, str) else str(message)
            conn.logger.bind(tag=TAG).info(f"收到文本消息：{safe_msg}")
            await conn.websocket.send(message)
            return
        if msg_json["type"] == "hello":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到hello消息：{safe_msg}")
            await handleHelloMessage(conn, msg_json)
        elif msg_json["type"] == "abort":
            conn.logger.bind(tag=TAG).info(f"收到abort消息：{message}")
            await handleAbortMessage(conn)
        elif msg_json["type"] == "listen":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到listen消息：{safe_msg}")
            if "mode" in msg_json:
                conn.client_listen_mode = msg_json["mode"]
                conn.logger.bind(tag=TAG).debug(
                    f"客户端拾音模式：{conn.client_listen_mode}"
                )
            if msg_json["state"] == "start":
                # 最小去抖：忽略距上次同类事件 <300ms 的重复 start
                try:
                    import time as _t
                    now_ms = int(_t.time() * 1000)
                    last_ms = int(getattr(conn, "_last_listen_start_ms", 0) or 0)
                    if now_ms - last_ms < 300:
                        return
                    conn._last_listen_start_ms = now_ms
                except Exception:
                    pass
                conn.client_have_voice = True
                conn.client_voice_stop = False
                # 记录设备侧边界最新时间，用于回退策略判断
                try:
                    import time as _t
                    conn._last_listen_event_ms = int(_t.time() * 1000)
                except Exception:
                    pass
            elif msg_json["state"] == "stop":
                # 最小去抖：忽略距上次同类事件 <300ms 的重复 stop
                try:
                    import time as _t
                    now_ms = int(_t.time() * 1000)
                    last_ms = int(getattr(conn, "_last_listen_stop_ms", 0) or 0)
                    if now_ms - last_ms < 300:
                        return
                    conn._last_listen_stop_ms = now_ms
                except Exception:
                    pass
                conn.client_have_voice = True
                conn.client_voice_stop = True
                try:
                    import time as _t
                    conn._last_listen_event_ms = int(_t.time() * 1000)
                except Exception:
                    pass
                # 新增：通知流式ASR“本段结束”，促使尽快产出最终结果
                try:
                    if getattr(conn, "asr", None) is not None and hasattr(conn.asr, "on_client_listen_stop"):
                        maybe = conn.asr.on_client_listen_stop(conn)
                        if asyncio.iscoroutine(maybe):
                            await maybe
                except Exception:
                    pass
                if len(conn.asr_audio) > 0:
                    await handleAudioMessage(conn, b"")
            elif msg_json["state"] == "detect":
                conn.client_have_voice = False
                conn.asr_audio.clear()
                if "text" in msg_json:
                    original_text = msg_json["text"]  # 保留原始文本
                    filtered_len, filtered_text = remove_punctuation_and_length(
                        original_text
                    )

                    # 模式切换（进入工作模式）意图识别与回显/播报抑制
                    try:
                        normalized = str(original_text or "").strip().lower()
                        mode_switch_keywords = [
                            "进入工作模式",
                            "工作模式",
                            "切到工作模式",
                            "切换到工作模式",
                            "workflow mode",
                            "working mode",
                            "switch to working mode",
                            "enter working mode",
                        ]
                        if any(k.lower() in normalized for k in mode_switch_keywords):
                            # 下发带意图标注的 STT（不触发 TTS），并仅发送模式确认
                            try:
                                await conn.send_json({
                                    "type": "stt",
                                    "text": original_text,
                                    "intent": "mode_switch",
                                    "target_mode": "working",
                                    "session_id": getattr(conn, "session_id", ""),
                                })
                            except Exception:
                                pass
                            # 复用现有 mode 流程，设置工作模式并触发一次快照单播
                            try:
                                await handleTextMessage(
                                    conn,
                                    json.dumps(
                                        {
                                            "type": "mode",
                                            "state": "start",
                                            "mode": "working",
                                        },
                                        ensure_ascii=False,
                                    ),
                                )
                            except Exception:
                                pass
                            return
                    except Exception:
                        pass

                    # 识别是否是唤醒词
                    is_wakeup_words = filtered_text in conn.config.get("wakeup_words")
                    # 是否开启唤醒词回复
                    enable_greeting = conn.config.get("enable_greeting", True)

                    if is_wakeup_words and not enable_greeting:
                        # 如果是唤醒词，且关闭了唤醒词回复，就不用回答
                        await send_stt_message(conn, original_text)
                        await send_tts_message(conn, "stop", None)
                        conn.client_is_speaking = False
                    elif is_wakeup_words:
                        conn.just_woken_up = True
                        # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）
                        enqueue_asr_report(conn, "嘿，你好呀", [])
                        await startToChat(conn, "嘿，你好呀")
                    else:
                        # 语音指令直达（工作模式）：assign/complete/refresh
                        try:
                            normalized = str(original_text or "").strip().lower()
                            # 仅在工作模式才进行直达解析
                            if getattr(conn, "current_mode", None) == "working":
                                assign_kw = ["认领任务", "领取任务", "我来做", "assign to me", "claim task"]
                                complete_kw = ["完成任务", "标记完成", "做完了", "mark done", "complete task"]
                                refresh_kw = ["刷新列表", "刷新任务", "拉取任务", "refresh", "pull", "update list"]
                                intent = None
                                if any(k.lower() in normalized for k in assign_kw):
                                    intent = "assign"
                                elif any(k.lower() in normalized for k in complete_kw):
                                    intent = "complete"
                                elif any(k.lower() in normalized for k in refresh_kw):
                                    intent = "refresh"
                                if intent is not None:
                                    # 可选：回包一个轻量意图（无 TTS 回显）
                                    try:
                                        await conn.send_json({
                                            "type": "workflow",
                                            "event": "command",
                                            "intent": intent,
                                        })
                                    except Exception:
                                        pass
                                    # 具体执行
                                    from core.utils.tasks_store import get_task_store
                                    store = get_task_store()
                                    group_key = (getattr(conn, "device_id", "") or "")[:8]
                                    # 在没有任务时，避免空数组频发：拉取一次并返回
                                    if intent == "refresh":
                                        tasks = store.list_by_group(group_key)
                                        envelope = {"type": "workflow", "event": "update", "tasks": tasks}
                                        try:
                                            await conn.send_json(envelope)
                                        except Exception:
                                            pass
                                        return
                                    # 认领/完成：取最近一个可操作任务（open，owner为空/非我）
                                    tasks = store.list_by_group(group_key) or []
                                    target_id = None
                                    if intent == "assign":
                                        for t in tasks:
                                            if t.get("status") == "open" and (not t.get("owner") or t.get("owner") != getattr(conn, "device_id", None)):
                                                target_id = t.get("id")
                                                break
                                        if target_id is None and tasks:
                                            target_id = tasks[0].get("id")
                                        if target_id:
                                            # 构造 assign 消息并复用 handler（含幂等返回）
                                            await handle_workflow_message(conn, {"type": "workflow", "event": "assign", "id": target_id})
                                            return
                                    elif intent == "complete":
                                        for t in tasks:
                                            if t.get("status") == "open":
                                                target_id = t.get("id")
                                                break
                                        if target_id:
                                            await handle_workflow_message(conn, {"type": "workflow", "event": "complete", "ids": [target_id]})
                                            return
                        except Exception:
                            pass
                        # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）；默认走常规对话
                        enqueue_asr_report(conn, original_text, [])
                        await startToChat(conn, original_text)
        elif msg_json["type"] == "iot":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到iot消息：{safe_msg}")
            if "descriptors" in msg_json:
                asyncio.create_task(handleIotDescriptors(conn, msg_json["descriptors"]))
            if "states" in msg_json:
                asyncio.create_task(handleIotStatus(conn, msg_json["states"]))
        elif msg_json["type"] == "mcp":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到mcp消息：{safe_msg}")
            if "payload" in msg_json:
                asyncio.create_task(
                    handle_mcp_message(conn, conn.mcp_client, msg_json["payload"])
                )
        elif msg_json["type"] == "meeting":
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到meeting消息：{safe_detail}")
            if msg_json.get("phase") == "finalize":
                # W1: 立即回执 + 立即停止定时器（双保险）并打印三段连续日志
                try:
                    conn.logger.bind(tag=TAG).info("finalize request")
                    ack_started_at = int(getattr(conn, "meeting_start_ts", 0) or 0)
                    pending_count = len(getattr(conn, "meeting_pending_texts", []) or [])
                    await conn.websocket.send(
                        json.dumps({
                            "type": "meeting",
                            "phase": "finalize",
                            "sessionId": getattr(conn, "session_id", ""),
                            "startedAt": ack_started_at,
                            "pendingCount": pending_count,
                        }, ensure_ascii=False)
                    )
                    conn.logger.bind(tag=TAG).info("send ack")
                except Exception:
                    pass
                # 标记 finalize 中，停止会中定时任务与推送，避免“结束中仍在增加片段”
                try:
                    setattr(conn, "meeting_finalizing", True)
                except Exception:
                    pass
                try:
                    from core.handle.meeting_handle import stop_meeting_timers
                    stop_meeting_timers(conn)
                    conn.logger.bind(tag=TAG).info("stop timers done")
                except Exception:
                    conn.logger.bind(tag=TAG).warning("stop timers encountered error (ignored)")
                # 关闭/重置 ASR 流式连接，避免下次会议复用陈旧状态
                try:
                    if getattr(conn, "asr", None) is not None:
                        if hasattr(conn.asr, "stop_ws_connection"):
                            conn.asr.stop_ws_connection()
                        # 如实现了异步 close，则后台触发
                        import inspect
                        if hasattr(conn.asr, "close") and inspect.iscoroutinefunction(conn.asr.close):
                            asyncio.create_task(conn.asr.close())
                except Exception:
                    pass
                # 异步生成并下发最终纪要
                asyncio.create_task(finalize_meeting_and_send_summary(conn))
            else:
                asyncio.create_task(handle_meeting_message(conn, msg_json))
        elif msg_json["type"] == "coding":
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到coding消息：{safe_detail}")
            asyncio.create_task(handle_coding_message(conn, msg_json))
        elif msg_json["type"] == "workflow":
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到workflow消息：{safe_detail}")
            asyncio.create_task(handle_workflow_message(conn, msg_json))
        elif msg_json["type"] == "config_update":
            # 兼容旧式 config_update：仅提示并忽略（避免“未知类型”噪声）
            try:
                cfg_keys = list((msg_json.get("config") or {}).keys())
                conn.logger.bind(tag=TAG).info(f"收到兼容 config_update（忽略实际更新）：keys={cfg_keys}")
            except Exception:
                conn.logger.bind(tag=TAG).info("收到兼容 config_update（忽略实际更新）")
            try:
                await conn.websocket.send(json.dumps({"type": "config_update", "status": "ok", "noop": True}))
            except Exception:
                pass
        elif msg_json["type"] == "mode":
            # 模式切换骨架：start/end + mode
            conn.logger.bind(tag=TAG).info(f"收到mode消息：{message}")
            try:
                state = msg_json.get("state")
                mode = msg_json.get("mode")
                if state in ["start", "end"] and mode in ["meeting", "coding", "working"]:
                    # 仅更新会话级状态（后续根据 mode 影响处理策略）
                    if state == "start":
                        # 幂等：若已处于该模式则直接回执并跳过重复初始化
                        if getattr(conn, "current_mode", None) == mode:
                            try:
                                await conn.websocket.send(json.dumps({"type":"mode","status":"ok","state":"start","mode":mode}))
                            except Exception:
                                pass
                            return
                        conn.current_mode = mode
                        if mode == "meeting":
                            conn.meeting_segments.clear()
                            conn.meeting_start_ts = time.time() * 1000
                            conn.meeting_last_snippet_ts = 0.0
                            conn.meeting_last_snippet_index = 0
                            # 播放进入会议提示音（后端下发TTS音频 or 控制端提示）
                            try:
                                await conn.websocket.send(
                                    json.dumps({
                                        "type": "tts",
                                        "state": "start",
                                        "url": "config/assets/evening.wav",
                                        "text": "已进入会议模式"
                                    }, ensure_ascii=False)
                                )
                                # 立即发送 stop 以最小化占用（客户端可按需播放本地资源）
                                await conn.websocket.send(
                                    json.dumps({
                                        "type": "tts",
                                        "state": "stop"
                                    }, ensure_ascii=False)
                                )
                            except Exception:
                                pass
                            # 会议模式优先设备侧VAD（可选）
                            try:
                                srv = getattr(conn, "server", None)
                                base_cfg = getattr(srv, "config", None) if srv else None
                                if isinstance(base_cfg, dict):
                                    meeting_cfg = base_cfg.get("meeting", {})
                                else:
                                    meeting_cfg = conn.config.get("meeting", {})
                            except Exception:
                                meeting_cfg = conn.config.get("meeting", {})
                            if bool(meeting_cfg.get("prefer_device_vad", True)):
                                conn.client_listen_mode = "manual"
                                conn.logger.bind(tag=TAG).info("会议模式已启用设备侧VAD优先（listen start/stop 括起语音段）")
                            # 尝试加载活跃会中状态，实现断线续传
                            try:
                                from core.handle.meeting_handle import load_active_state_if_any, start_meeting_checkpoint_timer, start_meeting_timers
                                await load_active_state_if_any(conn)
                                # 启动会议相关定时任务（transcript 聚合 + checkpoint）
                                start_meeting_timers(conn)
                                start_meeting_checkpoint_timer(conn)
                            except Exception:
                                pass
                        elif mode == "working":
                            # 任务1-1：进入工作模式后显式开启拾音（manual），确保设备处于可听状态
                            try:
                                # 更新连接侧拾音模式与最近边界时间
                                conn.client_listen_mode = "manual"
                                try:
                                    import time as _t
                                    conn._last_listen_event_ms = int(_t.time() * 1000)
                                except Exception:
                                    pass
                                await conn.websocket.send(
                                    json.dumps(
                                        {
                                            "type": "listen",
                                            "state": "start",
                                            "mode": "manual",
                                        },
                                        ensure_ascii=False,
                                    )
                                )
                            except Exception:
                                pass
                    else:
                        conn.current_mode = None
                        # 退出会议模式时恢复自动拾音
                        if mode == "meeting":
                            conn.client_listen_mode = "auto"
                        if mode == "meeting":
                            # 退出 meeting 等价 finalize：立即回执确认并停止推送（同样打印三段日志）
                            try:
                                conn.logger.bind(tag=TAG).info("finalize request")
                                ack_started_at = int(getattr(conn, "meeting_start_ts", 0) or 0)
                                pending_count = len(getattr(conn, "meeting_pending_texts", []) or [])
                                await conn.websocket.send(json.dumps({
                                    "type": "meeting",
                                    "phase": "finalize",
                                    "sessionId": getattr(conn, "session_id", ""),
                                    "startedAt": ack_started_at,
                                    "pendingCount": pending_count,
                                }, ensure_ascii=False))
                                conn.logger.bind(tag=TAG).info("send ack")
                            except Exception:
                                pass
                            try:
                                setattr(conn, "meeting_finalizing", True)
                            except Exception:
                                pass
                            try:
                                from core.handle.meeting_handle import stop_meeting_timers
                                stop_meeting_timers(conn)
                                conn.logger.bind(tag=TAG).info("stop timers done")
                            except Exception:
                                conn.logger.bind(tag=TAG).warning("stop timers encountered error (ignored)")
                            # 关闭/重置 ASR 流式连接，避免下次会议复用陈旧状态
                            try:
                                if getattr(conn, "asr", None) is not None:
                                    if hasattr(conn.asr, "stop_ws_connection"):
                                        conn.asr.stop_ws_connection()
                                    import inspect
                                    if hasattr(conn.asr, "close") and inspect.iscoroutinefunction(conn.asr.close):
                                        asyncio.create_task(conn.asr.close())
                            except Exception:
                                pass
                            asyncio.create_task(finalize_meeting_and_send_summary(conn))
                    # 任务1：进入工作模式时单播一次分组任务快照
                    try:
                        if state == "start" and mode == "working":
                            # 去抖：避免与注册/hello触发的快照在极短时间内重复
                            import time as _t
                            now_ms = int(_t.time() * 1000)
                            last_ms = int(getattr(conn, "_last_workflow_snapshot_ms", 0) or 0)
                            if now_ms - last_ms >= 1500:
                                group_key = (getattr(conn, "device_id", "") or "")[:8]
                                if group_key:
                                    from core.utils.tasks_store import get_task_store
                                    tasks = get_task_store().list_by_group(group_key)
                                    envelope = {"type": "workflow", "event": "update", "tasks": tasks}
                                    try:
                                        await conn.websocket.send_json(envelope)
                                    except AttributeError:
                                        await conn.websocket.send(json.dumps(envelope, ensure_ascii=False))
                                    conn._last_workflow_snapshot_ms = now_ms
                                    conn.logger.bind(tag=TAG).info(f"[Workflow] op=snapshot source=mode_start group={group_key} to={getattr(conn,'device_id','')} count={len(tasks)}")
                    except Exception:
                        pass
                else:
                    await conn.websocket.send(
                        json.dumps({
                            "type": "mode",
                            "status": "error",
                            "message": "invalid state or mode"
                        })
                    )
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"处理mode消息异常: {e}")
        
        elif msg_json["type"] == "peer":
            # 板间通信骨架：仅校验并入队，后续由AI中转路由处理
            conn.logger.bind(tag=TAG).info(f"收到peer消息：{filter_sensitive_info(msg_json)}")
            try:
                to_list = msg_json.get("to", [])
                payload = msg_json.get("payload", {})
                if not isinstance(to_list, list) or not isinstance(payload, dict):
                    await conn.websocket.send(
                        json.dumps({"type": "peer", "status": "error", "message": "invalid to/payload"})
                    )
                    return
                # 调用AI中转路由（串行以保证顺序；如需提升吞吐可放线程池）
                await handle_peer_message(conn, to_list, payload)
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"处理peer消息异常: {e}")
        elif msg_json["type"] == "server":
            # 记录日志时过滤敏感信息
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到服务器消息：{safe_detail}")
            # 如果配置是从API读取的，则需要验证secret
            if not conn.read_config_from_api:
                return
            # 获取post请求的secret
            post_secret = msg_json.get("content", {}).get("secret", "")
            secret = conn.config["manager-api"].get("secret", "")
            # 如果secret不匹配，则返回
            if post_secret != secret:
                await conn.websocket.send(
                    json.dumps(
                        {
                            "type": "server",
                            "status": "error",
                            "message": "服务器密钥验证失败",
                        }
                    )
                )
                return
            # 动态更新配置
            if msg_json["action"] == "update_config":
                try:
                    # 更新WebSocketServer的配置
                    if not conn.server:
                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "server",
                                    "status": "error",
                                    "message": "无法获取服务器实例",
                                    "content": {"action": "update_config"},
                                }
                            )
                        )
                        return

                    if not await conn.server.update_config():
                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "server",
                                    "status": "error",
                                    "message": "更新服务器配置失败",
                                    "content": {"action": "update_config"},
                                }
                            )
                        )
                        return

                    # 发送成功响应
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "server",
                                "status": "success",
                                "message": "配置更新成功",
                                "content": {"action": "update_config"},
                            }
                        )
                    )
                except Exception as e:
                    conn.logger.bind(tag=TAG).error(f"更新配置失败: {str(e)}")
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "server",
                                "status": "error",
                                "message": f"更新配置失败: {str(e)}",
                                "content": {"action": "update_config"},
                            }
                        )
                    )
            # 重启服务器
            elif msg_json["action"] == "restart":
                await conn.handle_restart(msg_json)
        else:
            conn.logger.bind(tag=TAG).error(f"收到未知类型消息：{message}")
    except json.JSONDecodeError:
        await conn.websocket.send(message)

```

```python
*** Begin Patch
*** Update File: /Users/tlovo/code_ai/Badge-ai/backend/core/handle/textHandle.py
@@
-                                    try:
-                                        await conn.websocket.send_json(envelope)
-                                    except AttributeError:
-                                        await conn.websocket.send(json.dumps(envelope, ensure_ascii=False))
+                                    try:
+                                        await conn.send_json(envelope)
+                                    except Exception:
+                                        pass
@@
-                    await conn.websocket.send(
-                        json.dumps({
-                            "type": "mode",
-                            "status": "error",
-                            "message": "invalid state or mode"
-                        })
-                    )
+                    await conn.send_json({
+                        "type": "mode",
+                        "status": "error",
+                        "message": "invalid state or mode"
+                    })
*** End Patch
```

```python
import json
from core.handle.abortHandle import handleAbortMessage
from core.handle.helloHandle import handleHelloMessage
from core.handle.mcpHandle import handle_mcp_message
from core.handle.peerHandle import handle_peer_message
from core.handle.meeting_handle import handle_meeting_message
from core.handle.coding_handle import handle_coding_message
from core.handle.workflow_handle import handle_workflow_message
from core.utils.util import remove_punctuation_and_length, filter_sensitive_info
from core.handle.receiveAudioHandle import startToChat, handleAudioMessage
from core.handle.sendAudioHandle import send_stt_message, send_tts_message
from core.handle.iotHandle import handleIotDescriptors, handleIotStatus
from core.handle.reportHandle import enqueue_asr_report
import asyncio
import time
from core.handle.meeting_handle import finalize_meeting_and_send_summary

TAG = __name__


async def handleTextMessage(conn, message):
    """处理文本消息"""
    try:
        msg_json = json.loads(message)
        if isinstance(msg_json, int):
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message if isinstance(message, str) else str(message)
            conn.logger.bind(tag=TAG).info(f"收到文本消息：{safe_msg}")
            await conn.websocket.send(message)
            return
        if msg_json["type"] == "hello":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到hello消息：{safe_msg}")
            await handleHelloMessage(conn, msg_json)
        elif msg_json["type"] == "abort":
            conn.logger.bind(tag=TAG).info(f"收到abort消息：{message}")
            await handleAbortMessage(conn)
        elif msg_json["type"] == "listen":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到listen消息：{safe_msg}")
            if "mode" in msg_json:
                conn.client_listen_mode = msg_json["mode"]
                conn.logger.bind(tag=TAG).debug(
                    f"客户端拾音模式：{conn.client_listen_mode}"
                )
            if msg_json["state"] == "start":
                # 最小去抖：忽略距上次同类事件 <300ms 的重复 start
                try:
                    import time as _t
                    now_ms = int(_t.time() * 1000)
                    last_ms = int(getattr(conn, "_last_listen_start_ms", 0) or 0)
                    if now_ms - last_ms < 300:
                        return
                    conn._last_listen_start_ms = now_ms
                except Exception:
                    pass
                conn.client_have_voice = True
                conn.client_voice_stop = False
                # 记录设备侧边界最新时间，用于回退策略判断
                try:
                    import time as _t
                    conn._last_listen_event_ms = int(_t.time() * 1000)
                except Exception:
                    pass
            elif msg_json["state"] == "stop":
                # 最小去抖：忽略距上次同类事件 <300ms 的重复 stop
                try:
                    import time as _t
                    now_ms = int(_t.time() * 1000)
                    last_ms = int(getattr(conn, "_last_listen_stop_ms", 0) or 0)
                    if now_ms - last_ms < 300:
                        return
                    conn._last_listen_stop_ms = now_ms
                except Exception:
                    pass
                conn.client_have_voice = True
                conn.client_voice_stop = True
                try:
                    import time as _t
                    conn._last_listen_event_ms = int(_t.time() * 1000)
                except Exception:
                    pass
                # 新增：通知流式ASR“本段结束”，促使尽快产出最终结果
                try:
                    if getattr(conn, "asr", None) is not None and hasattr(conn.asr, "on_client_listen_stop"):
                        maybe = conn.asr.on_client_listen_stop(conn)
                        if asyncio.iscoroutine(maybe):
                            await maybe
                except Exception:
                    pass
                if len(conn.asr_audio) > 0:
                    await handleAudioMessage(conn, b"")
            elif msg_json["state"] == "detect":
                conn.client_have_voice = False
                conn.asr_audio.clear()
                if "text" in msg_json:
                    original_text = msg_json["text"]  # 保留原始文本
                    filtered_len, filtered_text = remove_punctuation_and_length(
                        original_text
                    )

                    # 模式切换（进入工作模式）意图识别与回显/播报抑制
                    try:
                        normalized = str(original_text or "").strip().lower()
                        mode_switch_keywords = [
                            "进入工作模式",
                            "工作模式",
                            "切到工作模式",
                            "切换到工作模式",
                            "workflow mode",
                            "working mode",
                            "switch to working mode",
                            "enter working mode",
                        ]
                        if any(k.lower() in normalized for k in mode_switch_keywords):
                            # 下发带意图标注的 STT（不触发 TTS），并仅发送模式确认
                            try:
                                await conn.send_json({
                                    "type": "stt",
                                    "text": original_text,
                                    "intent": "mode_switch",
                                    "target_mode": "working",
                                    "session_id": getattr(conn, "session_id", ""),
                                })
                            except Exception:
                                pass
                            # 复用现有 mode 流程，设置工作模式并触发一次快照单播
                            try:
                                await handleTextMessage(
                                    conn,
                                    json.dumps(
                                        {
                                            "type": "mode",
                                            "state": "start",
                                            "mode": "working",
                                        },
                                        ensure_ascii=False,
                                    ),
                                )
                            except Exception:
                                pass
                            return
                    except Exception:
                        pass

                    # 识别是否是唤醒词
                    is_wakeup_words = filtered_text in conn.config.get("wakeup_words")
                    # 是否开启唤醒词回复
                    enable_greeting = conn.config.get("enable_greeting", True)

                    if is_wakeup_words and not enable_greeting:
                        # 如果是唤醒词，且关闭了唤醒词回复，就不用回答
                        await send_stt_message(conn, original_text)
                        await send_tts_message(conn, "stop", None)
                        conn.client_is_speaking = False
                    elif is_wakeup_words:
                        conn.just_woken_up = True
                        # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）
                        enqueue_asr_report(conn, "嘿，你好呀", [])
                        await startToChat(conn, "嘿，你好呀")
                    else:
                        # 语音指令直达（工作模式）：assign/complete/refresh
                        try:
                            normalized = str(original_text or "").strip().lower()
                            # 仅在工作模式才进行直达解析
                            if getattr(conn, "current_mode", None) == "working":
                                assign_kw = ["认领任务", "领取任务", "我来做", "assign to me", "claim task"]
                                complete_kw = ["完成任务", "标记完成", "做完了", "mark done", "complete task"]
                                refresh_kw = ["刷新列表", "刷新任务", "拉取任务", "refresh", "pull", "update list"]
                                intent = None
                                if any(k.lower() in normalized for k in assign_kw):
                                    intent = "assign"
                                elif any(k.lower() in normalized for k in complete_kw):
                                    intent = "complete"
                                elif any(k.lower() in normalized for k in refresh_kw):
                                    intent = "refresh"
                                if intent is not None:
                                    # 可选：回包一个轻量意图（无 TTS 回显）
                                    try:
                                        await conn.send_json({
                                            "type": "workflow",
                                            "event": "command",
                                            "intent": intent,
                                        })
                                    except Exception:
                                        pass
                                    # 具体执行
                                    from core.utils.tasks_store import get_task_store
                                    store = get_task_store()
                                    group_key = (getattr(conn, "device_id", "") or "")[:8]
                                    # 在没有任务时，避免空数组频发：拉取一次并返回
                                    if intent == "refresh":
                                        tasks = store.list_by_group(group_key)
                                        envelope = {"type": "workflow", "event": "update", "tasks": tasks}
                                        try:
                                            await conn.send_json(envelope)
                                        except Exception:
                                            pass
                                        return
                                    # 认领/完成：取最近一个可操作任务（open，owner为空/非我）
                                    tasks = store.list_by_group(group_key) or []
                                    target_id = None
                                    if intent == "assign":
                                        for t in tasks:
                                            if t.get("status") == "open" and (not t.get("owner") or t.get("owner") != getattr(conn, "device_id", None)):
                                                target_id = t.get("id")
                                                break
                                        if target_id is None and tasks:
                                            target_id = tasks[0].get("id")
                                        if target_id:
                                            # 构造 assign 消息并复用 handler（含幂等返回）
                                            await handle_workflow_message(conn, {"type": "workflow", "event": "assign", "id": target_id})
                                            return
                                    elif intent == "complete":
                                        for t in tasks:
                                            if t.get("status") == "open":
                                                target_id = t.get("id")
                                                break
                                        if target_id:
                                            await handle_workflow_message(conn, {"type": "workflow", "event": "complete", "ids": [target_id]})
                                            return
                        except Exception:
                            pass
                        # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）；默认走常规对话
                        enqueue_asr_report(conn, original_text, [])
                        await startToChat(conn, original_text)
        elif msg_json["type"] == "iot":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到iot消息：{safe_msg}")
            if "descriptors" in msg_json:
                asyncio.create_task(handleIotDescriptors(conn, msg_json["descriptors"]))
            if "states" in msg_json:
                asyncio.create_task(handleIotStatus(conn, msg_json["states"]))
        elif msg_json["type"] == "mcp":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到mcp消息：{safe_msg}")
            if "payload" in msg_json:
                asyncio.create_task(
                    handle_mcp_message(conn, conn.mcp_client, msg_json["payload"])
                )
        elif msg_json["type"] == "meeting":
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到meeting消息：{safe_detail}")
            if msg_json.get("phase") == "finalize":
                # W1: 立即回执 + 立即停止定时器（双保险）并打印三段连续日志
                try:
                    conn.logger.bind(tag=TAG).info("finalize request")
                    ack_started_at = int(getattr(conn, "meeting_start_ts", 0) or 0)
                    pending_count = len(getattr(conn, "meeting_pending_texts", []) or [])
                    await conn.websocket.send(
                        json.dumps({
                            "type": "meeting",
                            "phase": "finalize",
                            "sessionId": getattr(conn, "session_id", ""),
                            "startedAt": ack_started_at,
                            "pendingCount": pending_count,
                        }, ensure_ascii=False)
                    )
                    conn.logger.bind(tag=TAG).info("send ack")
                except Exception:
                    pass
                # 标记 finalize 中，停止会中定时任务与推送，避免“结束中仍在增加片段”
                try:
                    setattr(conn, "meeting_finalizing", True)
                except Exception:
                    pass
                try:
                    from core.handle.meeting_handle import stop_meeting_timers
                    stop_meeting_timers(conn)
                    conn.logger.bind(tag=TAG).info("stop timers done")
                except Exception:
                    conn.logger.bind(tag=TAG).warning("stop timers encountered error (ignored)")
                # 关闭/重置 ASR 流式连接，避免下次会议复用陈旧状态
                try:
                    if getattr(conn, "asr", None) is not None:
                        if hasattr(conn.asr, "stop_ws_connection"):
                            conn.asr.stop_ws_connection()
                        # 如实现了异步 close，则后台触发
                        import inspect
                        if hasattr(conn.asr, "close") and inspect.iscoroutinefunction(conn.asr.close):
                            asyncio.create_task(conn.asr.close())
                except Exception:
                    pass
                # 异步生成并下发最终纪要
                asyncio.create_task(finalize_meeting_and_send_summary(conn))
            else:
                asyncio.create_task(handle_meeting_message(conn, msg_json))
        elif msg_json["type"] == "coding":
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到coding消息：{safe_detail}")
            asyncio.create_task(handle_coding_message(conn, msg_json))
        elif msg_json["type"] == "workflow":
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到workflow消息：{safe_detail}")
            asyncio.create_task(handle_workflow_message(conn, msg_json))
        elif msg_json["type"] == "config_update":
            # 兼容旧式 config_update：仅提示并忽略（避免“未知类型”噪声）
            try:
                cfg_keys = list((msg_json.get("config") or {}).keys())
                conn.logger.bind(tag=TAG).info(f"收到兼容 config_update（忽略实际更新）：keys={cfg_keys}")
            except Exception:
                conn.logger.bind(tag=TAG).info("收到兼容 config_update（忽略实际更新）")
            try:
                await conn.websocket.send(json.dumps({"type": "config_update", "status": "ok", "noop": True}))
            except Exception:
                pass
        elif msg_json["type"] == "mode":
            # 模式切换骨架：start/end + mode
            conn.logger.bind(tag=TAG).info(f"收到mode消息：{message}")
            try:
                state = msg_json.get("state")
                mode = msg_json.get("mode")
                if state in ["start", "end"] and mode in ["meeting", "coding", "working"]:
                    # 仅更新会话级状态（后续根据 mode 影响处理策略）
                    if state == "start":
                        # 幂等：若已处于该模式则直接回执并跳过重复初始化
                        if getattr(conn, "current_mode", None) == mode:
                            try:
                                await conn.websocket.send(json.dumps({"type":"mode","status":"ok","state":"start","mode":mode}))
                            except Exception:
                                pass
                            return
                        conn.current_mode = mode
                        if mode == "meeting":
                            conn.meeting_segments.clear()
                            conn.meeting_start_ts = time.time() * 1000
                            conn.meeting_last_snippet_ts = 0.0
                            conn.meeting_last_snippet_index = 0
                            # 播放进入会议提示音（后端下发TTS音频 or 控制端提示）
                            try:
                                await conn.websocket.send(
                                    json.dumps({
                                        "type": "tts",
                                        "state": "start",
                                        "url": "config/assets/evening.wav",
                                        "text": "已进入会议模式"
                                    }, ensure_ascii=False)
                                )
                                # 立即发送 stop 以最小化占用（客户端可按需播放本地资源）
                                await conn.websocket.send(
                                    json.dumps({
                                        "type": "tts",
                                        "state": "stop"
                                    }, ensure_ascii=False)
                                )
                            except Exception:
                                pass
                            # 会议模式优先设备侧VAD（可选）
                            try:
                                srv = getattr(conn, "server", None)
                                base_cfg = getattr(srv, "config", None) if srv else None
                                if isinstance(base_cfg, dict):
                                    meeting_cfg = base_cfg.get("meeting", {})
                                else:
                                    meeting_cfg = conn.config.get("meeting", {})
                            except Exception:
                                meeting_cfg = conn.config.get("meeting", {})
                            if bool(meeting_cfg.get("prefer_device_vad", True)):
                                conn.client_listen_mode = "manual"
                                conn.logger.bind(tag=TAG).info("会议模式已启用设备侧VAD优先（listen start/stop 括起语音段）")
                            # 尝试加载活跃会中状态，实现断线续传
                            try:
                                from core.handle.meeting_handle import load_active_state_if_any, start_meeting_checkpoint_timer, start_meeting_timers
                                await load_active_state_if_any(conn)
                                # 启动会议相关定时任务（transcript 聚合 + checkpoint）
                                start_meeting_timers(conn)
                                start_meeting_checkpoint_timer(conn)
                            except Exception:
                                pass
                        elif mode == "working":
                            # 任务1-1：进入工作模式后显式开启拾音（manual），确保设备处于可听状态
                            try:
                                # 更新连接侧拾音模式与最近边界时间
                                conn.client_listen_mode = "manual"
                                try:
                                    import time as _t
                                    conn._last_listen_event_ms = int(_t.time() * 1000)
                                except Exception:
                                    pass
                                await conn.websocket.send(
                                    json.dumps(
                                        {
                                            "type": "listen",
                                            "state": "start",
                                            "mode": "manual",
                                        },
                                        ensure_ascii=False,
                                    )
                                )
                            except Exception:
                                pass
                    else:
                        conn.current_mode = None
                        # 退出会议模式时恢复自动拾音
                        if mode == "meeting":
                            conn.client_listen_mode = "auto"
                        if mode == "meeting":
                            # 退出 meeting 等价 finalize：立即回执确认并停止推送（同样打印三段日志）
                            try:
                                conn.logger.bind(tag=TAG).info("finalize request")
                                ack_started_at = int(getattr(conn, "meeting_start_ts", 0) or 0)
                                pending_count = len(getattr(conn, "meeting_pending_texts", []) or [])
                                await conn.websocket.send(json.dumps({
                                    "type": "meeting",
                                    "phase": "finalize",
                                    "sessionId": getattr(conn, "session_id", ""),
                                    "startedAt": ack_started_at,
                                    "pendingCount": pending_count,
                                }, ensure_ascii=False))
                                conn.logger.bind(tag=TAG).info("send ack")
                            except Exception:
                                pass
                            try:
                                setattr(conn, "meeting_finalizing", True)
                            except Exception:
                                pass
                            try:
                                from core.handle.meeting_handle import stop_meeting_timers
                                stop_meeting_timers(conn)
                                conn.logger.bind(tag=TAG).info("stop timers done")
                            except Exception:
                                conn.logger.bind(tag=TAG).warning("stop timers encountered error (ignored)")
                            # 关闭/重置 ASR 流式连接，避免下次会议复用陈旧状态
                            try:
                                if getattr(conn, "asr", None) is not None:
                                    if hasattr(conn.asr, "stop_ws_connection"):
                                        conn.asr.stop_ws_connection()
                                    import inspect
                                    if hasattr(conn.asr, "close") and inspect.iscoroutinefunction(conn.asr.close):
                                        asyncio.create_task(conn.asr.close())
                            except Exception:
                                pass
                            asyncio.create_task(finalize_meeting_and_send_summary(conn))
                    # 任务1：进入工作模式时单播一次分组任务快照
                    try:
                        if state == "start" and mode == "working":
                            # 去抖：避免与注册/hello触发的快照在极短时间内重复
                            import time as _t
                            now_ms = int(_t.time() * 1000)
                            last_ms = int(getattr(conn, "_last_workflow_snapshot_ms", 0) or 0)
                            if now_ms - last_ms >= 1500:
                                group_key = (getattr(conn, "device_id", "") or "")[:8]
                                if group_key:
                                    from core.utils.tasks_store import get_task_store
                                    tasks = get_task_store().list_by_group(group_key)
                                    envelope = {"type": "workflow", "event": "update", "tasks": tasks}
                                    try:
                                        await conn.send_json(envelope)
                                    except Exception:
                                        pass
                                    conn._last_workflow_snapshot_ms = now_ms
                                    conn.logger.bind(tag=TAG).info(f"[Workflow] op=snapshot source=mode_start group={group_key} to={getattr(conn,'device_id','')} count={len(tasks)}")
                    except Exception:
                        pass
                else:
                    await conn.websocket.send(
                        json.dumps({
                            "type": "mode",
                            "status": "error",
                            "message": "invalid state or mode"
                        })
                    )
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"处理mode消息异常: {e}")
        
        elif msg_json["type"] == "peer":
            # 板间通信骨架：仅校验并入队，后续由AI中转路由处理
            conn.logger.bind(tag=TAG).info(f"收到peer消息：{filter_sensitive_info(msg_json)}")
            try:
                to_list = msg_json.get("to", [])
                payload = msg_json.get("payload", {})
                if not isinstance(to_list, list) or not isinstance(payload, dict):
                    await conn.websocket.send(
                        json.dumps({"type": "peer", "status": "error", "message": "invalid to/payload"})
                    )
                    return
                # 调用AI中转路由（串行以保证顺序；如需提升吞吐可放线程池）
                await handle_peer_message(conn, to_list, payload)
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"处理peer消息异常: {e}")
        elif msg_json["type"] == "server":
            # 记录日志时过滤敏感信息
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到服务器消息：{safe_detail}")
            # 如果配置是从API读取的，则需要验证secret
            if not conn.read_config_from_api:
                return
            # 获取post请求的secret
            post_secret = msg_json.get("content", {}).get("secret", "")
            secret = conn.config["manager-api"].get("secret", "")
            # 如果secret不匹配，则返回
            if post_secret != secret:
                await conn.websocket.send(
                    json.dumps(
                        {
                            "type": "server",
                            "status": "error",
                            "message": "服务器密钥验证失败",
                        }
                    )
                )
                return
            # 动态更新配置
            if msg_json["action"] == "update_config":
                try:
                    # 更新WebSocketServer的配置
                    if not conn.server:
                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "server",
                                    "status": "error",
                                    "message": "无法获取服务器实例",
                                    "content": {"action": "update_config"},
                                }
                            )
                        )
                        return

                    if not await conn.server.update_config():
                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "server",
                                    "status": "error",
                                    "message": "更新服务器配置失败",
                                    "content": {"action": "update_config"},
                                }
                            )
                        )
                        return

                    # 发送成功响应
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "server",
                                "status": "success",
                                "message": "配置更新成功",
                                "content": {"action": "update_config"},
                            }
                        )
                    )
                except Exception as e:
                    conn.logger.bind(tag=TAG).error(f"更新配置失败: {str(e)}")
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "server",
                                "status": "error",
                                "message": f"更新配置失败: {str(e)}",
                                "content": {"action": "update_config"},
                            }
                        )
                    )
            # 重启服务器
            elif msg_json["action"] == "restart":
                await conn.handle_restart(msg_json)
        else:
            conn.logger.bind(tag=TAG).error(f"收到未知类型消息：{message}")
    except json.JSONDecodeError:
        await conn.websocket.send(message)

```

```python
import json
from core.handle.abortHandle import handleAbortMessage
from core.handle.helloHandle import handleHelloMessage
from core.handle.mcpHandle import handle_mcp_message
from core.handle.peerHandle import handle_peer_message
from core.handle.meeting_handle import handle_meeting_message
from core.handle.coding_handle import handle_coding_message
from core.handle.workflow_handle import handle_workflow_message
from core.utils.util import remove_punctuation_and_length, filter_sensitive_info
from core.handle.receiveAudioHandle import startToChat, handleAudioMessage
from core.handle.sendAudioHandle import send_stt_message, send_tts_message
from core.handle.iotHandle import handleIotDescriptors, handleIotStatus
from core.handle.reportHandle import enqueue_asr_report
import asyncio
import time
from core.handle.meeting_handle import finalize_meeting_and_send_summary

TAG = __name__


async def handleTextMessage(conn, message):
    """处理文本消息"""
    try:
        msg_json = json.loads(message)
        if isinstance(msg_json, int):
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message if isinstance(message, str) else str(message)
            conn.logger.bind(tag=TAG).info(f"收到文本消息：{safe_msg}")
            await conn.websocket.send(message)
            return
        if msg_json["type"] == "hello":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到hello消息：{safe_msg}")
            await handleHelloMessage(conn, msg_json)
        elif msg_json["type"] == "abort":
            conn.logger.bind(tag=TAG).info(f"收到abort消息：{message}")
            await handleAbortMessage(conn)
        elif msg_json["type"] == "listen":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到listen消息：{safe_msg}")
            if "mode" in msg_json:
                conn.client_listen_mode = msg_json["mode"]
                conn.logger.bind(tag=TAG).debug(
                    f"客户端拾音模式：{conn.client_listen_mode}"
                )
            if msg_json["state"] == "start":
                # 最小去抖：忽略距上次同类事件 <300ms 的重复 start
                try:
                    import time as _t
                    now_ms = int(_t.time() * 1000)
                    last_ms = int(getattr(conn, "_last_listen_start_ms", 0) or 0)
                    if now_ms - last_ms < 300:
                        return
                    conn._last_listen_start_ms = now_ms
                except Exception:
                    pass
                conn.client_have_voice = True
                conn.client_voice_stop = False
                # 记录设备侧边界最新时间，用于回退策略判断
                try:
                    import time as _t
                    conn._last_listen_event_ms = int(_t.time() * 1000)
                except Exception:
                    pass
            elif msg_json["state"] == "stop":
                # 最小去抖：忽略距上次同类事件 <300ms 的重复 stop
                try:
                    import time as _t
                    now_ms = int(_t.time() * 1000)
                    last_ms = int(getattr(conn, "_last_listen_stop_ms", 0) or 0)
                    if now_ms - last_ms < 300:
                        return
                    conn._last_listen_stop_ms = now_ms
                except Exception:
                    pass
                conn.client_have_voice = True
                conn.client_voice_stop = True
                try:
                    import time as _t
                    conn._last_listen_event_ms = int(_t.time() * 1000)
                except Exception:
                    pass
                # 新增：通知流式ASR“本段结束”，促使尽快产出最终结果
                try:
                    if getattr(conn, "asr", None) is not None and hasattr(conn.asr, "on_client_listen_stop"):
                        maybe = conn.asr.on_client_listen_stop(conn)
                        if asyncio.iscoroutine(maybe):
                            await maybe
                except Exception:
                    pass
                if len(conn.asr_audio) > 0:
                    await handleAudioMessage(conn, b"")
            elif msg_json["state"] == "detect":
                conn.client_have_voice = False
                conn.asr_audio.clear()
                if "text" in msg_json:
                    original_text = msg_json["text"]  # 保留原始文本
                    filtered_len, filtered_text = remove_punctuation_and_length(
                        original_text
                    )

                    # 模式切换（进入工作模式）意图识别与回显/播报抑制
                    try:
                        normalized = str(original_text or "").strip().lower()
                        mode_switch_keywords = [
                            "进入工作模式",
                            "工作模式",
                            "切到工作模式",
                            "切换到工作模式",
                            "workflow mode",
                            "working mode",
                            "switch to working mode",
                            "enter working mode",
                        ]
                        if any(k.lower() in normalized for k in mode_switch_keywords):
                            # 下发带意图标注的 STT（不触发 TTS），并仅发送模式确认
                            try:
                                await conn.send_json({
                                    "type": "stt",
                                    "text": original_text,
                                    "intent": "mode_switch",
                                    "target_mode": "working",
                                    "session_id": getattr(conn, "session_id", ""),
                                })
                            except Exception:
                                pass
                            # 复用现有 mode 流程，设置工作模式并触发一次快照单播
                            try:
                                await handleTextMessage(
                                    conn,
                                    json.dumps(
                                        {
                                            "type": "mode",
                                            "state": "start",
                                            "mode": "working",
                                        },
                                        ensure_ascii=False,
                                    ),
                                )
                            except Exception:
                                pass
                            return
                    except Exception:
                        pass

                    # 识别是否是唤醒词
                    is_wakeup_words = filtered_text in conn.config.get("wakeup_words")
                    # 是否开启唤醒词回复
                    enable_greeting = conn.config.get("enable_greeting", True)

                    if is_wakeup_words and not enable_greeting:
                        # 如果是唤醒词，且关闭了唤醒词回复，就不用回答
                        await send_stt_message(conn, original_text)
                        await send_tts_message(conn, "stop", None)
                        conn.client_is_speaking = False
                    elif is_wakeup_words:
                        conn.just_woken_up = True
                        # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）
                        enqueue_asr_report(conn, "嘿，你好呀", [])
                        await startToChat(conn, "嘿，你好呀")
                    else:
                        # 语音指令直达（工作模式）：assign/complete/refresh
                        try:
                            normalized = str(original_text or "").strip().lower()
                            # 仅在工作模式才进行直达解析
                            if getattr(conn, "current_mode", None) == "working":
                                assign_kw = ["认领任务", "领取任务", "我来做", "assign to me", "claim task"]
                                complete_kw = ["完成任务", "标记完成", "做完了", "mark done", "complete task"]
                                refresh_kw = ["刷新列表", "刷新任务", "拉取任务", "refresh", "pull", "update list"]
                                intent = None
                                if any(k.lower() in normalized for k in assign_kw):
                                    intent = "assign"
                                elif any(k.lower() in normalized for k in complete_kw):
                                    intent = "complete"
                                elif any(k.lower() in normalized for k in refresh_kw):
                                    intent = "refresh"
                                if intent is not None:
                                    # 可选：回包一个轻量意图（无 TTS 回显）
                                    try:
                                        await conn.send_json({
                                            "type": "workflow",
                                            "event": "command",
                                            "intent": intent,
                                        })
                                    except Exception:
                                        pass
                                    # 具体执行
                                    from core.utils.tasks_store import get_task_store
                                    store = get_task_store()
                                    group_key = (getattr(conn, "device_id", "") or "")[:8]
                                    # 在没有任务时，避免空数组频发：拉取一次并返回
                                    if intent == "refresh":
                                        tasks = store.list_by_group(group_key)
                                        envelope = {"type": "workflow", "event": "update", "tasks": tasks}
                                        try:
                                            await conn.send_json(envelope)
                                        except Exception:
                                            pass
                                        return
                                    # 认领/完成：取最近一个可操作任务（open，owner为空/非我）
                                    tasks = store.list_by_group(group_key) or []
                                    target_id = None
                                    if intent == "assign":
                                        for t in tasks:
                                            if t.get("status") == "open" and (not t.get("owner") or t.get("owner") != getattr(conn, "device_id", None)):
                                                target_id = t.get("id")
                                                break
                                        if target_id is None and tasks:
                                            target_id = tasks[0].get("id")
                                        if target_id:
                                            # 构造 assign 消息并复用 handler（含幂等返回）
                                            await handle_workflow_message(conn, {"type": "workflow", "event": "assign", "id": target_id})
                                            return
                                    elif intent == "complete":
                                        for t in tasks:
                                            if t.get("status") == "open":
                                                target_id = t.get("id")
                                                break
                                        if target_id:
                                            await handle_workflow_message(conn, {"type": "workflow", "event": "complete", "ids": [target_id]})
                                            return
                        except Exception:
                            pass
                        # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）；默认走常规对话
                        enqueue_asr_report(conn, original_text, [])
                        await startToChat(conn, original_text)
        elif msg_json["type"] == "iot":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到iot消息：{safe_msg}")
            if "descriptors" in msg_json:
                asyncio.create_task(handleIotDescriptors(conn, msg_json["descriptors"]))
            if "states" in msg_json:
                asyncio.create_task(handleIotStatus(conn, msg_json["states"]))
        elif msg_json["type"] == "mcp":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到mcp消息：{safe_msg}")
            if "payload" in msg_json:
                asyncio.create_task(
                    handle_mcp_message(conn, conn.mcp_client, msg_json["payload"])
                )
        elif msg_json["type"] == "meeting":
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到meeting消息：{safe_detail}")
            if msg_json.get("phase") == "finalize":
                # W1: 立即回执 + 立即停止定时器（双保险）并打印三段连续日志
                try:
                    conn.logger.bind(tag=TAG).info("finalize request")
                    ack_started_at = int(getattr(conn, "meeting_start_ts", 0) or 0)
                    pending_count = len(getattr(conn, "meeting_pending_texts", []) or [])
                    await conn.websocket.send(
                        json.dumps({
                            "type": "meeting",
                            "phase": "finalize",
                            "sessionId": getattr(conn, "session_id", ""),
                            "startedAt": ack_started_at,
                            "pendingCount": pending_count,
                        }, ensure_ascii=False)
                    )
                    conn.logger.bind(tag=TAG).info("send ack")
                except Exception:
                    pass
                # 标记 finalize 中，停止会中定时任务与推送，避免“结束中仍在增加片段”
                try:
                    setattr(conn, "meeting_finalizing", True)
                except Exception:
                    pass
                try:
                    from core.handle.meeting_handle import stop_meeting_timers
                    stop_meeting_timers(conn)
                    conn.logger.bind(tag=TAG).info("stop timers done")
                except Exception:
                    conn.logger.bind(tag=TAG).warning("stop timers encountered error (ignored)")
                # 关闭/重置 ASR 流式连接，避免下次会议复用陈旧状态
                try:
                    if getattr(conn, "asr", None) is not None:
                        if hasattr(conn.asr, "stop_ws_connection"):
                            conn.asr.stop_ws_connection()
                        # 如实现了异步 close，则后台触发
                        import inspect
                        if hasattr(conn.asr, "close") and inspect.iscoroutinefunction(conn.asr.close):
                            asyncio.create_task(conn.asr.close())
                except Exception:
                    pass
                # 异步生成并下发最终纪要
                asyncio.create_task(finalize_meeting_and_send_summary(conn))
            else:
                asyncio.create_task(handle_meeting_message(conn, msg_json))
        elif msg_json["type"] == "coding":
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到coding消息：{safe_detail}")
            asyncio.create_task(handle_coding_message(conn, msg_json))
        elif msg_json["type"] == "workflow":
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到workflow消息：{safe_detail}")
            asyncio.create_task(handle_workflow_message(conn, msg_json))
        elif msg_json["type"] == "config_update":
            # 兼容旧式 config_update：仅提示并忽略（避免“未知类型”噪声）
            try:
                cfg_keys = list((msg_json.get("config") or {}).keys())
                conn.logger.bind(tag=TAG).info(f"收到兼容 config_update（忽略实际更新）：keys={cfg_keys}")
            except Exception:
                conn.logger.bind(tag=TAG).info("收到兼容 config_update（忽略实际更新）")
            try:
                await conn.websocket.send(json.dumps({"type": "config_update", "status": "ok", "noop": True}))
            except Exception:
                pass
        elif msg_json["type"] == "mode":
            # 模式切换骨架：start/end + mode
            conn.logger.bind(tag=TAG).info(f"收到mode消息：{message}")
            try:
                state = msg_json.get("state")
                mode = msg_json.get("mode")
                if state in ["start", "end"] and mode in ["meeting", "coding", "working"]:
                    # 仅更新会话级状态（后续根据 mode 影响处理策略）
                    if state == "start":
                        # 幂等：若已处于该模式则直接回执并跳过重复初始化
                        if getattr(conn, "current_mode", None) == mode:
                            try:
                                await conn.websocket.send(json.dumps({"type":"mode","status":"ok","state":"start","mode":mode}))
                            except Exception:
                                pass
                            return
                        conn.current_mode = mode
                        if mode == "meeting":
                            conn.meeting_segments.clear()
                            conn.meeting_start_ts = time.time() * 1000
                            conn.meeting_last_snippet_ts = 0.0
                            conn.meeting_last_snippet_index = 0
                            # 播放进入会议提示音（后端下发TTS音频 or 控制端提示）
                            try:
                                await conn.websocket.send(
                                    json.dumps({
                                        "type": "tts",
                                        "state": "start",
                                        "url": "config/assets/evening.wav",
                                        "text": "已进入会议模式"
                                    }, ensure_ascii=False)
                                )
                                # 立即发送 stop 以最小化占用（客户端可按需播放本地资源）
                                await conn.websocket.send(
                                    json.dumps({
                                        "type": "tts",
                                        "state": "stop"
                                    }, ensure_ascii=False)
                                )
                            except Exception:
                                pass
                            # 会议模式优先设备侧VAD（可选）
                            try:
                                srv = getattr(conn, "server", None)
                                base_cfg = getattr(srv, "config", None) if srv else None
                                if isinstance(base_cfg, dict):
                                    meeting_cfg = base_cfg.get("meeting", {})
                                else:
                                    meeting_cfg = conn.config.get("meeting", {})
                            except Exception:
                                meeting_cfg = conn.config.get("meeting", {})
                            if bool(meeting_cfg.get("prefer_device_vad", True)):
                                conn.client_listen_mode = "manual"
                                conn.logger.bind(tag=TAG).info("会议模式已启用设备侧VAD优先（listen start/stop 括起语音段）")
                            # 尝试加载活跃会中状态，实现断线续传
                            try:
                                from core.handle.meeting_handle import load_active_state_if_any, start_meeting_checkpoint_timer, start_meeting_timers
                                await load_active_state_if_any(conn)
                                # 启动会议相关定时任务（transcript 聚合 + checkpoint）
                                start_meeting_timers(conn)
                                start_meeting_checkpoint_timer(conn)
                            except Exception:
                                pass
                        elif mode == "working":
                            # 任务1-1：进入工作模式后显式开启拾音（manual），确保设备处于可听状态
                            try:
                                # 更新连接侧拾音模式与最近边界时间
                                conn.client_listen_mode = "manual"
                                try:
                                    import time as _t
                                    conn._last_listen_event_ms = int(_t.time() * 1000)
                                except Exception:
                                    pass
                                await conn.websocket.send(
                                    json.dumps(
                                        {
                                            "type": "listen",
                                            "state": "start",
                                            "mode": "manual",
                                        },
                                        ensure_ascii=False,
                                    )
                                )
                            except Exception:
                                pass
                    else:
                        conn.current_mode = None
                        # 退出会议模式时恢复自动拾音
                        if mode == "meeting":
                            conn.client_listen_mode = "auto"
                        if mode == "meeting":
                            # 退出 meeting 等价 finalize：立即回执确认并停止推送（同样打印三段日志）
                            try:
                                conn.logger.bind(tag=TAG).info("finalize request")
                                ack_started_at = int(getattr(conn, "meeting_start_ts", 0) or 0)
                                pending_count = len(getattr(conn, "meeting_pending_texts", []) or [])
                                await conn.websocket.send(json.dumps({
                                    "type": "meeting",
                                    "phase": "finalize",
                                    "sessionId": getattr(conn, "session_id", ""),
                                    "startedAt": ack_started_at,
                                    "pendingCount": pending_count,
                                }, ensure_ascii=False))
                                conn.logger.bind(tag=TAG).info("send ack")
                            except Exception:
                                pass
                            try:
                                setattr(conn, "meeting_finalizing", True)
                            except Exception:
                                pass
                            try:
                                from core.handle.meeting_handle import stop_meeting_timers
                                stop_meeting_timers(conn)
                                conn.logger.bind(tag=TAG).info("stop timers done")
                            except Exception:
                                conn.logger.bind(tag=TAG).warning("stop timers encountered error (ignored)")
                            # 关闭/重置 ASR 流式连接，避免下次会议复用陈旧状态
                            try:
                                if getattr(conn, "asr", None) is not None:
                                    if hasattr(conn.asr, "stop_ws_connection"):
                                        conn.asr.stop_ws_connection()
                                    import inspect
                                    if hasattr(conn.asr, "close") and inspect.iscoroutinefunction(conn.asr.close):
                                        asyncio.create_task(conn.asr.close())
                            except Exception:
                                pass
                            asyncio.create_task(finalize_meeting_and_send_summary(conn))
                    # 任务1：进入工作模式时单播一次分组任务快照
                    try:
                        if state == "start" and mode == "working":
                            # 去抖：避免与注册/hello触发的快照在极短时间内重复
                            import time as _t
                            now_ms = int(_t.time() * 1000)
                            last_ms = int(getattr(conn, "_last_workflow_snapshot_ms", 0) or 0)
                            if now_ms - last_ms >= 1500:
                                group_key = (getattr(conn, "device_id", "") or "")[:8]
                                if group_key:
                                    from core.utils.tasks_store import get_task_store
                                    tasks = get_task_store().list_by_group(group_key)
                                    envelope = {"type": "workflow", "event": "update", "tasks": tasks}
                                    try:
                                        await conn.send_json(envelope)
                                    except Exception:
                                        pass
                                    conn._last_workflow_snapshot_ms = now_ms
                                    conn.logger.bind(tag=TAG).info(f"[Workflow] op=snapshot source=mode_start group={group_key} to={getattr(conn,'device_id','')} count={len(tasks)}")
                    except Exception:
                        pass
                else:
                    await conn.send_json({
                        "type": "mode",
                        "status": "error",
                        "message": "invalid state or mode"
                    })
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"处理mode消息异常: {e}")
        
        elif msg_json["type"] == "peer":
            # 板间通信骨架：仅校验并入队，后续由AI中转路由处理
            conn.logger.bind(tag=TAG).info(f"收到peer消息：{filter_sensitive_info(msg_json)}")
            try:
                to_list = msg_json.get("to", [])
                payload = msg_json.get("payload", {})
                if not isinstance(to_list, list) or not isinstance(payload, dict):
                    await conn.websocket.send(
                        json.dumps({"type": "peer", "status": "error", "message": "invalid to/payload"})
                    )
                    return
                # 调用AI中转路由（串行以保证顺序；如需提升吞吐可放线程池）
                await handle_peer_message(conn, to_list, payload)
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"处理peer消息异常: {e}")
        elif msg_json["type"] == "server":
            # 记录日志时过滤敏感信息
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到服务器消息：{safe_detail}")
            # 如果配置是从API读取的，则需要验证secret
            if not conn.read_config_from_api:
                return
            # 获取post请求的secret
            post_secret = msg_json.get("content", {}).get("secret", "")
            secret = conn.config["manager-api"].get("secret", "")
            # 如果secret不匹配，则返回
            if post_secret != secret:
                await conn.websocket.send(
                    json.dumps(
                        {
                            "type": "server",
                            "status": "error",
                            "message": "服务器密钥验证失败",
                        }
                    )
                )
                return
            # 动态更新配置
            if msg_json["action"] == "update_config":
                try:
                    # 更新WebSocketServer的配置
                    if not conn.server:
                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "server",
                                    "status": "error",
                                    "message": "无法获取服务器实例",
                                    "content": {"action": "update_config"},
                                }
                            )
                        )
                        return

                    if not await conn.server.update_config():
                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "server",
                                    "status": "error",
                                    "message": "更新服务器配置失败",
                                    "content": {"action": "update_config"},
                                }
                            )
                        )
                        return

                    # 发送成功响应
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "server",
                                "status": "success",
                                "message": "配置更新成功",
                                "content": {"action": "update_config"},
                            }
                        )
                    )
                except Exception as e:
                    conn.logger.bind(tag=TAG).error(f"更新配置失败: {str(e)}")
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "server",
                                "status": "error",
                                "message": f"更新配置失败: {str(e)}",
                                "content": {"action": "update_config"},
                            }
                        )
                    )
            # 重启服务器
            elif msg_json["action"] == "restart":
                await conn.handle_restart(msg_json)
        else:
            conn.logger.bind(tag=TAG).error(f"收到未知类型消息：{message}")
    except json.JSONDecodeError:
        await conn.websocket.send(message)

```

```python
import os
import sys
import copy
import json
import uuid
import time
import queue
import asyncio
import threading
import traceback
from config.logger import truncate_for_log
import subprocess
import websockets
from core.handle.mcpHandle import call_mcp_tool
from core.utils.util import (
    extract_json_from_string,
    check_vad_update,
    check_asr_update,
    filter_sensitive_info,
    parse_ids_from_handshake,
)
from typing import Dict, Any
from core.mcp.manager import MCPManager
from core.utils.modules_initialize import (
    initialize_modules,
    initialize_tts,
    initialize_asr,
)
from core.handle.reportHandle import report
from core.providers.tts.default import DefaultTTS
from concurrent.futures import ThreadPoolExecutor
from core.utils.dialogue import Message, Dialogue
from core.providers.asr.dto.dto import InterfaceType
from core.handle.textHandle import handleTextMessage
from core.handle.functionHandler import FunctionHandler
from plugins_func.loadplugins import auto_import_modules
from plugins_func.register import Action, ActionResponse
from core.auth import AuthMiddleware, AuthenticationError
from config.config_loader import get_private_config_from_api
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
from config.logger import setup_logging, build_module_string, update_module_string
from config.manage_api_client import DeviceNotFoundException, DeviceBindException


TAG = __name__

auto_import_modules("plugins_func.functions")


class TTSException(RuntimeError):
    pass


class ConnectionHandler:
    def __init__(
        self,
        config: Dict[str, Any],
        _vad,
        _asr,
        _llm,
        _memory,
        _intent,
        server=None,
    ):
        self.common_config = config
        self.config = copy.deepcopy(config)
        self.session_id = str(uuid.uuid4())
        self.logger = setup_logging()
        self.server = server  # 保存server实例的引用

        self.auth = AuthMiddleware(config)
        self.need_bind = False
        self.bind_code = None
        self.read_config_from_api = self.config.get("read_config_from_api", False)

        self.websocket = None
        self.headers = None
        self.device_id = None
        self.client_ip = None
        self.client_ip_info = {}
        self.prompt = None
        self.welcome_msg = None
        self.max_output_size = 0
        self.chat_history_conf = 0
        self.audio_format = "opus"

        # 客户端状态相关
        self.client_abort = False
        self.client_is_speaking = False
        self.client_listen_mode = "auto"

        # 线程任务相关（在连接开始时绑定运行中的事件循环）
        self.loop = None
        self.stop_event = threading.Event()
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

        # 添加上报线程池
        self.report_queue = queue.Queue()
        self.report_thread = None
        # 未来可以通过修改此处，调节asr的上报和tts的上报，目前默认都开启
        self.report_asr_enable = self.read_config_from_api
        self.report_tts_enable = self.read_config_from_api

        # 依赖的组件
        self.vad = None
        self.asr = None
        self.tts = None
        self._asr = _asr
        self._vad = _vad
        self.llm = _llm
        self.memory = _memory
        self.intent = _intent

        # vad相关变量
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0.0
        self.client_no_voice_last_time = 0.0
        self.client_voice_stop = False
        self.client_voice_frame_count = 0

        # asr相关变量
        # 因为实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR
        # 所以涉及到ASR的变量，需要在这里定义，属于connection的私有变量
        self.asr_audio = []
        self.asr_audio_queue = queue.Queue()

        # llm相关变量
        self.llm_finish_task = True
        self.dialogue = Dialogue()

        # tts相关变量
        self.sentence_id = None

        # iot相关变量
        self.iot_descriptors = {}
        self.func_handler = None

        # 模式状态（meeting/coding/working）
        self.current_mode = None
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
        # 编码模式日志流运行标志/阶段名（用于 stop/clear/phase 扩展）
        self.coding_stream_running = False
        self.coding_phase_name = ""

        self.cmd_exit = self.config["exit_commands"]
        self.max_cmd_length = 0
        for cmd in self.cmd_exit:
            if len(cmd) > self.max_cmd_length:
                self.max_cmd_length = len(cmd)

        # 是否在聊天结束后关闭连接
        self.close_after_chat = False
        self.load_function_plugin = False
        self.intent_type = "nointent"

        self.timeout_task = None
        # 放宽默认空闲阈值：默认 600s + 60s 兜底；允许配置覆盖
        try:
            base_idle = int(self.config.get("close_connection_no_voice_time", 600))
        except Exception:
            base_idle = 600
        self.timeout_seconds = base_idle + 60  # 第一层之外的兜底关闭

        # {"mcp":true} 表示启用MCP功能
        self.features = None

        # LLM 按模式实例缓存（随连接释放）
        self._llm_cache = {}

    def _get_base_config(self) -> Dict[str, Any]:
        try:
            srv = getattr(self, "server", None)
            base_cfg = getattr(srv, "config", None) if srv else None
            if isinstance(base_cfg, dict):
                return base_cfg
        except Exception:
            pass
        return self.config if isinstance(self.config, dict) else {}

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

        base_cfg = self._get_base_config()
        # 读取映射
        mapping = {}
        try:
            mapping = base_cfg.get("llm_by_mode", {}) or {}
        except Exception:
            mapping = {}

        mapping_val = mapping.get(key, None)
        if mapping_val is None:
            # 用途未配置专用 LLM，回退 default 并记录告警
            try:
                self.logger.bind(tag=TAG).warning(
                    f"get_llm_for: 未找到用途 {key} 的 llm_by_mode 配置，回退到 default"
                )
            except Exception:
                pass
            mapping_val = mapping.get("default")

        alias = None
        overrides = None
        if isinstance(mapping_val, dict):
            # 支持 { alias: xxx, overrides: { model_name: '...' } } 或直接平铺覆盖字段
            alias = mapping_val.get("alias") or mapping_val.get("name") or mapping_val.get("module") or mapping_val.get("llm")
            overrides = mapping_val.get("overrides")
            if overrides is None:
                # 将除别名键外的其余键视为覆盖
                tmp = dict(mapping_val)
                for k in ["alias", "name", "module", "llm", "overrides"]:
                    tmp.pop(k, None)
                overrides = tmp if len(tmp) > 0 else None
        elif isinstance(mapping_val, str) and len(mapping_val) > 0:
            alias = mapping_val

        # 回退默认 alias
        try:
            if alias is None:
                alias = self.config["selected_module"]["LLM"]
        except Exception:
            alias = None

        # 若无覆盖且别名等于当前默认，直接复用
        try:
            current_default_alias = self.config["selected_module"]["LLM"]
            if (overrides is None or len(overrides) == 0) and alias == current_default_alias and getattr(self, "llm", None) is not None:
                self._llm_cache[key] = self.llm
                return self.llm
        except Exception:
            pass

        # 构造/复用实例（合并覆盖）：优先使用 server 级共享注册表
        try:
            from core.utils import llm as llm_utils
            base_conf = None
            if alias:
                base_conf = copy.deepcopy(self.config.get("LLM", {}).get(alias))
                # 若连接级配置未包含该别名，尝试从服务器级配置读取（支持热更）
                if not base_conf:
                    try:
                        srv = getattr(self, "server", None)
                        srv_cfg = getattr(srv, "config", None) if srv else None
                        if isinstance(srv_cfg, dict):
                            base_conf = copy.deepcopy(srv_cfg.get("LLM", {}).get(alias))
                    except Exception:
                        pass
            if not base_conf:
                # 回退：无对应配置则复用默认，并给出一次告警
                try:
                    self.logger.bind(tag=TAG).warning(
                        f"get_llm_for: llm_by_mode[{key}] 别名未命中(alias={alias}), 回退默认LLM"
                    )
                except Exception:
                    pass
                self._llm_cache[key] = self.llm
                return self.llm
            # 若 server 提供共享注册表，优先复用
            try:
                srv = getattr(self, "server", None)
                if srv and hasattr(srv, "get_or_create_llm") and callable(getattr(srv, "get_or_create_llm")):
                    instance = srv.get_or_create_llm(alias, overrides)
                else:
                    # 直接合并覆盖并创建独立实例
                    if overrides and isinstance(overrides, dict):
                        for k, v in overrides.items():
                            base_conf[k] = v
                    llm_type = base_conf.get("type", alias)
                    instance = llm_utils.create_instance(llm_type, base_conf)
            except Exception:
                if overrides and isinstance(overrides, dict):
                    for k, v in overrides.items():
                        base_conf[k] = v
                llm_type = base_conf.get("type", alias)
                instance = llm_utils.create_instance(llm_type, base_conf)
            self._llm_cache[key] = instance
            return instance
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"get_llm_for 失败({key}): {e}，回退默认LLM")
            self._llm_cache[key] = self.llm
            return self.llm

    async def handle_connection(self, ws, path=None):
        try:
            # 绑定当前运行事件循环供跨线程调度使用
            try:
                self.loop = asyncio.get_running_loop()
            except Exception:
                self.loop = asyncio.get_event_loop()
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
                self.headers = headers_lower
            except Exception:
                self.headers = {}

            # 优先从 URL 查询参数解析 device-id/client-id；其次尝试 Header；最后回退

            def _normalize_id(value: str | None) -> str | None:
                if value is None:
                    return None
                try:
                    v = str(value).strip().strip('"').strip("'")
                    if v == "":
                        return None
                    return v.lower()
                except Exception:
                    return None

            device_id_from_query = None
            client_id_from_query = None
            try:
                candidate_paths = []
                if isinstance(path, str) and len(path) > 0:
                    candidate_paths.append(path)
                ws_path = getattr(ws, "path", "")
                if isinstance(ws_path, str) and len(ws_path) > 0 and ws_path not in candidate_paths:
                    candidate_paths.append(ws_path)
                # 兼容不同版本 websockets 的属性命名，尽量获取带 query 的原始 URI
                for attr in ["request_uri", "raw_request_uri", "request_path", "raw_path"]:
                    try:
                        val = getattr(ws, attr, "")
                        if isinstance(val, str) and len(val) > 0 and val not in candidate_paths:
                            candidate_paths.append(val)
                    except Exception:
                        pass
                # 从候选 path 中解析 query 参数（统一解析函数）
                for p in candidate_paths:
                    try:
                        did, cid, _ = parse_ids_from_handshake(p)
                        if did:
                            device_id_from_query = _normalize_id(did)
                            client_id_from_query = _normalize_id(cid or did)
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            # 兜底：从 server 的握手缓存读取（适配 websockets 传参差异）
            try:
                server_obj = getattr(self, "server", None)
                if (device_id_from_query is None) and server_obj is not None:
                    cache = getattr(server_obj, "_handshake_cache", None)
                    if isinstance(cache, dict):
                        # 按连接对象 id 存储
                        cached = cache.get(id(ws))
                        if isinstance(cached, dict):
                            did = cached.get("device-id")
                            cid = cached.get("client-id") or did
                            device_id_from_query = _normalize_id(did)
                            client_id_from_query = _normalize_id(cid)
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
                # 打印来源与解析快照（包含原始 path 片段便于定位异常客户端）
                try:
                    raw_paths_snapshot = []
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                        for attr in ["request_uri", "raw_request_uri", "request_path", "raw_path"]:
                            val = getattr(ws, attr, "")
                            if isinstance(val, str) and val:
                                raw_paths_snapshot.append(val[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    src = "query" if device_id_from_query else "header"
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={src}, rawPaths={truncate_for_log(str(raw_paths_snapshot))})"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={'query' if device_id_from_query else 'header'})"
                    )
            else:
                # 容错：仍未取到则自动分配，保证连接可用；同时输出诊断快照
                auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
                self.headers["device-id"] = auto_device_id
                self.headers["client-id"] = auto_device_id
                try:
                    raw_paths_snapshot = []
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    header_keys = list(self.headers.keys())
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}; rawPaths={truncate_for_log(str(raw_paths_snapshot))}, headerKeys={truncate_for_log(str(header_keys))}"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}"
                    )
            # 获取客户端ip地址
            try:
                remote = getattr(ws, "remote_address", None)
                if isinstance(remote, tuple) and len(remote) >= 1:
                    self.client_ip = remote[0]
                else:
                    self.client_ip = str(remote) if remote is not None else ""
            except Exception:
                self.client_ip = ""
            self.logger.bind(tag=TAG).info(
                f"{self.client_ip} conn - Headers: {self.headers}"
            )

            # 进行认证
            await self.auth.authenticate(self.headers)

            # 认证通过,继续处理
            self.websocket = ws
            self.device_id = self.headers.get("device-id", None)
            # 在 server 上注册设备路由（自动断开旧连接）
            if self.server and self.device_id:
                ok = await self.server.register_device_handler(self.device_id, self)
                if ok is False:
                    self.logger.bind(tag=TAG).error(f"设备注册失败: {self.device_id}")
                    await ws.send("设备注册失败")
                    await self.close(ws)
                    return

            # 启动超时检查任务
            self.timeout_task = asyncio.create_task(self._check_timeout())

            self.welcome_msg = self.config["xiaozhi"]
            self.welcome_msg["session_id"] = self.session_id
            await self.send_json(self.welcome_msg)

            # 获取差异化配置
            self._initialize_private_config()
            # 异步初始化
            self.executor.submit(self._initialize_components)

            try:
                async for message in self.websocket:
                    await self._route_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.bind(tag=TAG).info("客户端断开连接")

        except AuthenticationError as e:
            self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
            return
        except Exception as e:
            stack_trace = traceback.format_exc()
            try:
                safe_e = truncate_for_log(str(e))
                safe_tb = truncate_for_log(stack_trace)
            except Exception:
                safe_e = str(e)
                safe_tb = stack_trace
            self.logger.bind(tag=TAG).error(f"Connection error: {safe_e}-{safe_tb}")
            return
        finally:
            try:
                # 注销设备路由映射
                if self.server and self.device_id:
                    await self.server.unregister_device_handler(self.device_id, self)
            finally:
                await self._save_and_close(ws)

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

    def reset_timeout(self):
        """重置超时计时器"""
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
        self.timeout_task = asyncio.create_task(self._check_timeout())

    async def _route_message(self, message):
        """消息路由"""
        # 重置超时计时器
        self.reset_timeout()

        if isinstance(message, str):
            # 轻量 ping/keepalive：收到后仅重置计时器并忽略
            try:
                import json as _json
                try:
                    obj = _json.loads(message)
                except Exception:
                    obj = None
                if isinstance(obj, dict) and obj.get("type") in ("ping", "keepalive"):
                    try:
                        # 可选：立即回 pong
                        await self.websocket.send(_json.dumps({"type": "pong"}))
                    except Exception:
                        pass
                    return
            except Exception:
                pass
            await handleTextMessage(self, message)
        elif isinstance(message, bytes):
            if self.vad is None:
                return
            if self.asr is None:
                return
            self.asr_audio_queue.put(message)

    async def handle_restart(self, message):
        """处理服务器重启请求"""
        try:

            self.logger.bind(tag=TAG).info("收到服务器重启指令，准备执行...")

            # 发送确认响应
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "success",
                        "message": "服务器重启中...",
                        "content": {"action": "restart"},
                    }
                )
            )

            # 异步执行重启操作
            def restart_server():
                """实际执行重启的方法"""
                time.sleep(1)
                self.logger.bind(tag=TAG).info("执行服务器重启...")
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
                os._exit(0)

            # 使用线程执行重启避免阻塞事件循环
            threading.Thread(target=restart_server, daemon=True).start()

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"重启失败: {str(e)}")
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "error",
                        "message": f"Restart failed: {str(e)}",
                        "content": {"action": "restart"},
                    }
                )
            )

    def _initialize_components(self):
        try:
            self.selected_module_str = build_module_string(
                self.config.get("selected_module", {})
            )
            update_module_string(self.selected_module_str)
            """初始化组件"""
            if self.config.get("prompt") is not None:
                self.prompt = self.config["prompt"]
                self.change_system_prompt(self.prompt)
                self.logger.bind(tag=TAG).info(
                    f"初始化组件: prompt成功 {self.prompt[:50]}..."
                )

            """初始化本地组件"""
            if self.vad is None:
                self.vad = self._vad
            if self.asr is None:
                self.asr = self._initialize_asr()
            # 打开语音识别通道
            asyncio.run_coroutine_threadsafe(self.asr.open_audio_channels(self), self.loop)

            if self.tts is None:
                self.tts = self._initialize_tts()
            # 会议模式可禁用 TTS 通道（懒启动）
            disable_tts = False
            try:
                srv = getattr(self, "server", None)
                base_cfg = getattr(srv, "config", None) if srv else None
                if isinstance(base_cfg, dict):
                    meeting_cfg2 = base_cfg.get("meeting", {})
                else:
                    meeting_cfg2 = self.config.get("meeting", {})
                disable_tts = bool(meeting_cfg2.get("disable_tts", False))
            except Exception:
                disable_tts = False
            if not disable_tts:
                asyncio.run_coroutine_threadsafe(self.tts.open_audio_channels(self), self.loop)

            """加载记忆"""
            self._initialize_memory()
            """加载意图识别"""
            self._initialize_intent()
            """初始化上报线程"""
            self._init_report_threads()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"实例化组件失败: {e}")

    def _init_report_threads(self):
        """初始化ASR和TTS上报线程"""
        if not self.read_config_from_api or self.need_bind:
            return
        if self.chat_history_conf == 0:
            return
        if self.report_thread is None or not self.report_thread.is_alive():
            self.report_thread = threading.Thread(
                target=self._report_worker, daemon=True
            )
            self.report_thread.start()
            self.logger.bind(tag=TAG).info("TTS上报线程已启动")

    def _initialize_tts(self):
        """初始化TTS"""
        tts = None
        if not self.need_bind:
            tts = initialize_tts(self.config)

        if tts is None:
            tts = DefaultTTS(self.config, delete_audio_file=True)

        return tts

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

    def _initialize_private_config(self):
        """如果是从配置文件获取，则进行二次实例化"""
        if not self.read_config_from_api:
            return
        """从接口获取差异化的配置进行二次实例化，非全量重新实例化"""
        try:
            begin_time = time.time()
            private_config = get_private_config_from_api(
                self.config,
                self.headers.get("device-id"),
                self.headers.get("client-id", self.headers.get("device-id")),
            )
            private_config["delete_audio"] = bool(self.config.get("delete_audio", True))
            self.logger.bind(tag=TAG).info(
                f"{time.time() - begin_time} 秒，获取差异化配置成功: {json.dumps(filter_sensitive_info(private_config), ensure_ascii=False)}"
            )
        except DeviceNotFoundException as e:
            self.need_bind = True
            private_config = {}
        except DeviceBindException as e:
            self.need_bind = True
            self.bind_code = e.bind_code
            private_config = {}
        except Exception as e:
            self.need_bind = True
            self.logger.bind(tag=TAG).error(f"获取差异化配置失败: {e}")
            private_config = {}

        init_llm, init_tts, init_memory, init_intent = (
            False,
            False,
            False,
            False,
        )

        init_vad = check_vad_update(self.common_config, private_config)
        init_asr = check_asr_update(self.common_config, private_config)

        if init_vad:
            self.config["VAD"] = private_config["VAD"]
            self.config["selected_module"]["VAD"] = private_config["selected_module"][
                "VAD"
            ]
        if init_asr:
            self.config["ASR"] = private_config["ASR"]
            self.config["selected_module"]["ASR"] = private_config["selected_module"][
                "ASR"
            ]
        if private_config.get("TTS", None) is not None:
            init_tts = True
            self.config["TTS"] = private_config["TTS"]
            self.config["selected_module"]["TTS"] = private_config["selected_module"][
                "TTS"
            ]
        if private_config.get("LLM", None) is not None:
            init_llm = True
            self.config["LLM"] = private_config["LLM"]
            self.config["selected_module"]["LLM"] = private_config["selected_module"][
                "LLM"
            ]
        if private_config.get("Memory", None) is not None:
            init_memory = True
            self.config["Memory"] = private_config["Memory"]
            self.config["selected_module"]["Memory"] = private_config[
                "selected_module"
            ]["Memory"]
        if private_config.get("Intent", None) is not None:
            init_intent = True
            self.config["Intent"] = private_config["Intent"]
            model_intent = private_config.get("selected_module", {}).get("Intent", {})
            self.config["selected_module"]["Intent"] = model_intent
            # 加载插件配置
            if model_intent != "Intent_nointent":
                plugin_from_server = private_config.get("plugins", {})
                for plugin, config_str in plugin_from_server.items():
                    plugin_from_server[plugin] = json.loads(config_str)
                self.config["plugins"] = plugin_from_server
                self.config["Intent"][self.config["selected_module"]["Intent"]][
                    "functions"
                ] = plugin_from_server.keys()
        if private_config.get("prompt", None) is not None:
            self.config["prompt"] = private_config["prompt"]
        if private_config.get("summaryMemory", None) is not None:
            self.config["summaryMemory"] = private_config["summaryMemory"]
        if private_config.get("device_max_output_size", None) is not None:
            self.max_output_size = int(private_config["device_max_output_size"])
        if private_config.get("chat_history_conf", None) is not None:
            self.chat_history_conf = int(private_config["chat_history_conf"])
        try:
            modules = initialize_modules(
                self.logger,
                private_config,
                init_vad,
                init_asr,
                init_llm,
                init_tts,
                init_memory,
                init_intent,
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"初始化组件失败: {e}")
            modules = {}
        if modules.get("tts", None) is not None:
            self.tts = modules["tts"]
        if modules.get("vad", None) is not None:
            self.vad = modules["vad"]
        if modules.get("asr", None) is not None:
            self.asr = modules["asr"]
        if modules.get("llm", None) is not None:
            self.llm = modules["llm"]
        if modules.get("intent", None) is not None:
            self.intent = modules["intent"]
        if modules.get("memory", None) is not None:
            self.memory = modules["memory"]

    def _initialize_memory(self):
        if self.memory is None:
            return
        """初始化记忆模块"""
        # 按模式选择记忆总结 LLM（可被 llm_by_mode.memory 覆盖）
        chosen_llm = self.llm
        try:
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                selected = self.get_llm_for("memory")
                if selected is not None:
                    chosen_llm = selected
        except Exception:
            pass

        self.memory.init_memory(
            role_id=self.device_id,
            llm=chosen_llm,
            summary_memory=self.config.get("summaryMemory", None),
            save_to_file=not self.read_config_from_api,
        )

        # 获取记忆总结配置
        memory_config = self.config["Memory"]
        memory_type = self.config["Memory"][self.config["selected_module"]["Memory"]][
            "type"
        ]
        # 如果使用 nomen，直接返回
        if memory_type == "nomem":
            return
        # 使用 mem_local_short 模式
        elif memory_type == "mem_local_short":
            memory_llm_name = memory_config[self.config["selected_module"]["Memory"]][
                "llm"
            ]
            if memory_llm_name and memory_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                memory_llm_config = self.config["LLM"][memory_llm_name]
                memory_llm_type = memory_llm_config.get("type", memory_llm_name)
                memory_llm = llm_utils.create_instance(
                    memory_llm_type, memory_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为记忆总结创建了专用LLM: {memory_llm_name}, 类型: {memory_llm_type}"
                )
                self.memory.set_llm(memory_llm)
            else:
                # 否则使用主LLM
                self.memory.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

    def _initialize_intent(self):
        if self.intent is None:
            return
        self.intent_type = self.config["Intent"][
            self.config["selected_module"]["Intent"]
        ]["type"]
        if self.intent_type == "function_call" or self.intent_type == "intent_llm":
            self.load_function_plugin = True
        """初始化意图识别模块"""
        # 获取意图识别配置
        intent_config = self.config["Intent"]
        intent_type = self.config["Intent"][self.config["selected_module"]["Intent"]][
            "type"
        ]

        # 如果使用 nointent，直接返回
        if intent_type == "nointent":
            return
        # 使用 intent_llm 模式
        elif intent_type == "intent_llm":
            intent_llm_name = intent_config[self.config["selected_module"]["Intent"]][
                "llm"
            ]

            if intent_llm_name and intent_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                intent_llm_config = self.config["LLM"][intent_llm_name]
                intent_llm_type = intent_llm_config.get("type", intent_llm_name)
                intent_llm = llm_utils.create_instance(
                    intent_llm_type, intent_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为意图识别创建了专用LLM: {intent_llm_name}, 类型: {intent_llm_type}"
                )
                # 按模式选择意图识别 LLM（可被 llm_by_mode.intent 覆盖）
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(intent_llm)
                    else:
                        self.intent.set_llm(intent_llm)
                except Exception:
                    self.intent.set_llm(intent_llm)
            else:
                # 否则使用主LLM
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(self.llm)
                    else:
                        self.intent.set_llm(self.llm)
                except Exception:
                    self.intent.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

        """加载插件"""
        self.func_handler = FunctionHandler(self)
        self.mcp_manager = MCPManager(self)

        """加载MCP工具"""
        asyncio.run_coroutine_threadsafe(
            self.mcp_manager.initialize_servers(), self.loop
        )

    def change_system_prompt(self, prompt):
        self.prompt = prompt
        # 更新系统prompt至上下文
        self.dialogue.update_system_message(self.prompt)

    def chat(self, query, tool_call=False):
        try:
            safe_query = truncate_for_log(query)
        except Exception:
            safe_query = query
        self.logger.bind(tag=TAG).info(f"大模型收到用户消息: {safe_query}")
        self.llm_finish_task = False

        if not tool_call:
            self.dialogue.put(Message(role="user", content=query))

        # Define intent functions
        functions = None
        if self.intent_type == "function_call" and hasattr(self, "func_handler"):
            functions = self.func_handler.get_functions()
        if hasattr(self, "mcp_client"):
            mcp_tools = self.mcp_client.get_available_tools()
            if mcp_tools is not None and len(mcp_tools) > 0:
                if functions is None:
                    functions = []
                functions.extend(mcp_tools)
        response_message = []

        try:
            # 使用带记忆的对话
            memory_str = None
            if self.memory is not None:
                future = asyncio.run_coroutine_threadsafe(
                    self.memory.query_memory(query), self.loop
                )
                memory_str = future.result()

            self.sentence_id = str(uuid.uuid4().hex)


            # 按当前模式选择 LLM（默认chat；coding/working 切换对应别名）
            purpose = self.current_mode or "chat"
            active_llm = self.llm
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                try:
                    active_llm = self.get_llm_for(purpose) or self.llm
                except Exception:
                    active_llm = self.llm

            if self.intent_type == "function_call" and functions is not None:
                # 使用支持functions的streaming接口
                llm_responses = active_llm.response_with_functions(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                    functions=functions,
                )
            else:
                llm_responses = active_llm.response(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM 处理出错 {query}: {e}")
            return None

        # 处理流式响应
        tool_call_flag = False
        function_name = None
        function_id = None
        function_arguments = ""
        content_arguments = ""
        text_index = 0
        self.client_abort = False
        for response in llm_responses:
            if self.client_abort:
                break
            if self.intent_type == "function_call" and functions is not None:
                content, tools_call = response
                if "content" in response:
                    content = response["content"]
                    tools_call = None
                if content is not None and len(content) > 0:
                    content_arguments += content

                if not tool_call_flag and content_arguments.startswith("<tool_call>"):
                    # print("content_arguments", content_arguments)
                    tool_call_flag = True

                if tools_call is not None and len(tools_call) > 0:
                    tool_call_flag = True
                    if tools_call[0].id is not None:
                        function_id = tools_call[0].id
                    if tools_call[0].function.name is not None:
                        function_name = tools_call[0].function.name
                    if tools_call[0].function.arguments is not None:
                        function_arguments += tools_call[0].function.arguments
            else:
                content = response
            if content is not None and len(content) > 0:
                if not tool_call_flag:
                    response_message.append(content)
                    if text_index == 0:
                        self.tts.tts_text_queue.put(
                            TTSMessageDTO(
                                sentence_id=self.sentence_id,
                                sentence_type=SentenceType.FIRST,
                                content_type=ContentType.ACTION,
                            )
                        )
                    self.tts.tts_text_queue.put(
                        TTSMessageDTO(
                            sentence_id=self.sentence_id,
                            sentence_type=SentenceType.MIDDLE,
                            content_type=ContentType.TEXT,
                            content_detail=content,
                        )
                    )
                    text_index += 1
        # 处理function call
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
            if not bHasError:
                response_message.clear()
                self.logger.bind(tag=TAG).debug(
                    f"function_name={function_name}, function_id={function_id}, function_arguments={function_arguments}"
                )
                function_call_data = {
                    "name": function_name,
                    "id": function_id,
                    "arguments": function_arguments,
                }

                # 处理Server端MCP工具调用
                if self.mcp_manager.is_mcp_tool(function_name):
                    result = self._handle_mcp_tool_call(function_call_data)
                elif hasattr(self, "mcp_client") and self.mcp_client.has_tool(
                    function_name
                ):
                    # 如果是小智端MCP工具调用
                    self.logger.bind(tag=TAG).debug(
                        f"调用小智端MCP工具: {function_name}, 参数: {function_arguments}"
                    )
                    try:
                        result = asyncio.run_coroutine_threadsafe(
                            call_mcp_tool(
                                self, self.mcp_client, function_name, function_arguments
                            ),
                            self.loop,
                        ).result()
                        self.logger.bind(tag=TAG).debug(f"MCP工具调用结果: {result}")

                        resultJson = None
                        if isinstance(result, str):
                            try:
                                resultJson = json.loads(result)
                            except Exception as e:
                                self.logger.bind(tag=TAG).error(
                                    f"解析MCP工具返回结果失败: {e}"
                                )

                        # 视觉大模型不经过二次LLM处理
                        if (
                            resultJson is not None
                            and isinstance(resultJson, dict)
                            and "action" in resultJson
                        ):
                            result = ActionResponse(
                                action=Action[resultJson["action"]],
                                result=None,
                                response=resultJson.get("response", ""),
                            )
                        else:
                            result = ActionResponse(
                                action=Action.REQLLM, result=result, response=""
                            )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"MCP工具调用失败: {e}")
                        result = ActionResponse(
                            action=Action.REQLLM, result="MCP工具调用失败", response=""
                        )
                else:
                    # 处理系统函数
                    result = self.func_handler.handle_llm_function_call(
                        self, function_call_data
                    )
                self._handle_function_result(result, function_call_data)

        # 存储对话内容
        if len(response_message) > 0:
            self.dialogue.put(
                Message(role="assistant", content="".join(response_message))
            )
        if text_index > 0:
            self.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=self.sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )
        self.llm_finish_task = True
        self.logger.bind(tag=TAG).debug(
            json.dumps(self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False)
        )

        return True

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

            tool_result = asyncio.run_coroutine_threadsafe(
                self.mcp_manager.execute_tool(function_name, args_dict), self.loop
            ).result()
            # meta=None content=[TextContent(type='text', text='北京当前天气:\n温度: 21°C\n天气: 晴\n湿度: 6%\n风向: 西北 风\n风力等级: 5级', annotations=None)] isError=False
            content_text = ""
            if tool_result is not None and tool_result.content is not None:
                for content in tool_result.content:
                    content_type = content.type
                    if content_type == "text":
                        content_text = content.text
                    elif content_type == "image":
                        pass

            if len(content_text) > 0:
                return ActionResponse(
                    action=Action.REQLLM, result=content_text, response=""
                )

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP工具调用错误: {e}")
            return ActionResponse(
                action=Action.REQLLM, result="工具调用出错", response=""
            )

        return ActionResponse(action=Action.REQLLM, result="工具调用出错", response="")

    def _handle_function_result(self, result, function_call_data):
        if result.action == Action.RESPONSE:  # 直接回复前端
            text = result.response
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        elif result.action == Action.REQLLM:  # 调用函数后再请求llm生成回复
            text = result.result
            if text is not None and len(text) > 0:
                function_id = function_call_data["id"]
                function_name = function_call_data["name"]
                function_arguments = function_call_data["arguments"]
                self.dialogue.put(
                    Message(
                        role="assistant",
                        tool_calls=[
                            {
                                "id": function_id,
                                "function": {
                                    "arguments": function_arguments,
                                    "name": function_name,
                                },
                                "type": "function",
                                "index": 0,
                            }
                        ],
                    )
                )

                self.dialogue.put(
                    Message(
                        role="tool",
                        tool_call_id=(
                            str(uuid.uuid4()) if function_id is None else function_id
                        ),
                        content=text,
                    )
                )
                self.chat(text, tool_call=True)
        elif result.action == Action.NOTFOUND or result.action == Action.ERROR:
            text = result.result
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        else:
            pass

    def _report_worker(self):
        """聊天记录上报工作线程"""
        while not self.stop_event.is_set():
            try:
                # 从队列获取数据，设置超时以便定期检查停止事件
                item = self.report_queue.get(timeout=1)
                if item is None:  # 检测毒丸对象
                    break
                type, text, audio_data, report_time = item
                try:
                    # 检查线程池状态
                    if self.executor is None:
                        continue
                    # 提交任务到线程池
                    self.executor.submit(
                        self._process_report, type, text, audio_data, report_time
                    )
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"聊天记录上报线程异常: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"聊天记录上报工作线程异常: {e}")

        self.logger.bind(tag=TAG).info("聊天记录上报线程已退出")

    def _process_report(self, type, text, audio_data, report_time):
        """处理上报任务"""
        try:
            # 执行上报（传入二进制数据）
            report(self, type, text, audio_data, report_time)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"上报处理异常: {e}")
        finally:
            # 标记任务完成
            self.report_queue.task_done()

    def clearSpeakStatus(self):
        self.client_is_speaking = False
        self.logger.bind(tag=TAG).debug(f"清除服务端讲话状态")

    async def close(self, ws=None):
        """资源清理方法"""
        try:
            # 取消超时任务
            if self.timeout_task:
                self.timeout_task.cancel()
                self.timeout_task = None

            # 取消编码洞察定时任务
            try:
                if hasattr(self, "coding_insight_task") and self.coding_insight_task and not self.coding_insight_task.done():
                    self.coding_insight_task.cancel()
            except Exception:
                pass

            # 清理MCP资源
            if hasattr(self, "mcp_manager") and self.mcp_manager:
                await self.mcp_manager.cleanup_all()

            # 触发停止事件
            if self.stop_event:
                self.stop_event.set()

            # 清空任务队列
            self.clear_queues()

            # 关闭WebSocket连接
            if ws:
                await ws.close()
            elif self.websocket:
                await self.websocket.close()

            # 最后关闭线程池（避免阻塞）
            if self.executor:
                try:
                    # Python 3.9+ 支持 cancel_futures
                    self.executor.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    self.executor.shutdown(wait=False)
                self.executor = None

            # 清理 LLM 实例缓存
            try:
                if hasattr(self, "_llm_cache") and isinstance(self._llm_cache, dict):
                    self._llm_cache.clear()
            except Exception:
                pass

            # 关闭 asr/tts/llm 资源
            try:
                if hasattr(self, "asr") and hasattr(self.asr, "close") and callable(getattr(self.asr, "close")):
                    maybe_close = self.asr.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "tts") and hasattr(self.tts, "close") and callable(getattr(self.tts, "close")):
                    maybe_close = self.tts.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "llm") and hasattr(self.llm, "close") and callable(getattr(self.llm, "close")):
                    maybe_close = self.llm.close()  # 供应商可选实现
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass

            self.logger.bind(tag=TAG).info("连接资源已释放")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"关闭连接时出错: {e}")

    def clear_queues(self):
        """清空所有任务队列"""
        if self.tts:
            self.logger.bind(tag=TAG).debug(
                f"开始清理: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

            # 使用非阻塞方式清空队列
            for q in [
                self.tts.tts_text_queue,
                self.tts.tts_audio_queue,
                self.report_queue,
            ]:
                if not q:
                    continue
                while True:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break

            self.logger.bind(tag=TAG).debug(
                f"清理结束: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

    def reset_vad_states(self):
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0
        self.client_voice_stop = False
        self.logger.bind(tag=TAG).debug("VAD states reset.")

    async def send_text(self, text: str) -> None:
        """统一文本发送包装。"""
        try:
            if self.websocket:
                await self.websocket.send(text)
        except Exception:
            pass

    async def send_json(self, payload: dict) -> None:
        """统一 JSON 发送包装，自动兼容 send_json 缺失并回退字符串。"""
        try:
            if self.websocket is None:
                return
            try:
                await self.websocket.send_json(payload)
            except AttributeError:
                import json as _json
                await self.websocket.send(_json.dumps(payload, ensure_ascii=False))
        except Exception:
            # 发送错误不应中断主流程
            pass

    def chat_and_close(self, text):
        """Chat with the user and then close the connection"""
        try:
            # Use the existing chat method
            self.chat(text)

            # After chat is complete, close the connection
            self.close_after_chat = True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Chat and close error: {str(e)}")

    async def _check_timeout(self):
        """检查连接超时"""
        try:
            while not self.stop_event.is_set():
                await asyncio.sleep(self.timeout_seconds)
                if not self.stop_event.is_set():
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
                    if self.stop_event.is_set():
                        break
                    self.logger.bind(tag=TAG).info("连接超时，准备关闭")
                    await self.close(self.websocket)
                    break
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"超时检查任务出错: {e}")

```

---

**User**

继续

继续

---

**Cursor**

```python
import os
import sys
import copy
import json
import uuid
import time
import queue
import asyncio
import threading
import traceback
from config.logger import truncate_for_log
import subprocess
import websockets
from core.handle.mcpHandle import call_mcp_tool
from core.utils.util import (
    extract_json_from_string,
    check_vad_update,
    check_asr_update,
    filter_sensitive_info,
    parse_ids_from_handshake,
)
from typing import Dict, Any
from core.mcp.manager import MCPManager
from core.utils.modules_initialize import (
    initialize_modules,
    initialize_tts,
    initialize_asr,
)
from core.handle.reportHandle import report
from core.providers.tts.default import DefaultTTS
from concurrent.futures import ThreadPoolExecutor
from core.utils.dialogue import Message, Dialogue
from core.providers.asr.dto.dto import InterfaceType
from core.handle.textHandle import handleTextMessage
from core.handle.functionHandler import FunctionHandler
from plugins_func.loadplugins import auto_import_modules
from plugins_func.register import Action, ActionResponse
from core.auth import AuthMiddleware, AuthenticationError
from config.config_loader import get_private_config_from_api
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
from config.logger import setup_logging, build_module_string, update_module_string
from config.manage_api_client import DeviceNotFoundException, DeviceBindException


TAG = __name__

auto_import_modules("plugins_func.functions")


class TTSException(RuntimeError):
    pass


class ConnectionHandler:
    def __init__(
        self,
        config: Dict[str, Any],
        _vad,
        _asr,
        _llm,
        _memory,
        _intent,
        server=None,
    ):
        self.common_config = config
        self.config = copy.deepcopy(config)
        self.session_id = str(uuid.uuid4())
        self.logger = setup_logging()
        self.server = server  # 保存server实例的引用

        self.auth = AuthMiddleware(config)
        self.need_bind = False
        self.bind_code = None
        self.read_config_from_api = self.config.get("read_config_from_api", False)

        self.websocket = None
        self.headers = None
        self.device_id = None
        self.client_ip = None
        self.client_ip_info = {}
        self.prompt = None
        self.welcome_msg = None
        self.max_output_size = 0
        self.chat_history_conf = 0
        self.audio_format = "opus"

        # 客户端状态相关
        self.client_abort = False
        self.client_is_speaking = False
        self.client_listen_mode = "auto"

        # 线程任务相关（在连接开始时绑定运行中的事件循环）
        self.loop = None
        self.stop_event = threading.Event()
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

        # 添加上报线程池
        self.report_queue = queue.Queue()
        self.report_thread = None
        # 未来可以通过修改此处，调节asr的上报和tts的上报，目前默认都开启
        self.report_asr_enable = self.read_config_from_api
        self.report_tts_enable = self.read_config_from_api

        # 依赖的组件
        self.vad = None
        self.asr = None
        self.tts = None
        self._asr = _asr
        self._vad = _vad
        self.llm = _llm
        self.memory = _memory
        self.intent = _intent

        # vad相关变量
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0.0
        self.client_no_voice_last_time = 0.0
        self.client_voice_stop = False
        self.client_voice_frame_count = 0

        # asr相关变量
        # 因为实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR
        # 所以涉及到ASR的变量，需要在这里定义，属于connection的私有变量
        self.asr_audio = []
        self.asr_audio_queue = queue.Queue()

        # llm相关变量
        self.llm_finish_task = True
        self.dialogue = Dialogue()

        # tts相关变量
        self.sentence_id = None

        # iot相关变量
        self.iot_descriptors = {}
        self.func_handler = None

        # 模式状态（meeting/coding/working）
        self.current_mode = None
        # 语音分段有限状态机：idle|listening|finalizing
        self.listen_state = "idle"
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
        # 编码模式日志流运行标志/阶段名（用于 stop/clear/phase 扩展）
        self.coding_stream_running = False
        self.coding_phase_name = ""

        self.cmd_exit = self.config["exit_commands"]
        self.max_cmd_length = 0
        for cmd in self.cmd_exit:
            if len(cmd) > self.max_cmd_length:
                self.max_cmd_length = len(cmd)

        # 是否在聊天结束后关闭连接
        self.close_after_chat = False
        self.load_function_plugin = False
        self.intent_type = "nointent"

        self.timeout_task = None
        # 放宽默认空闲阈值：默认 600s + 60s 兜底；允许配置覆盖
        try:
            base_idle = int(self.config.get("close_connection_no_voice_time", 600))
        except Exception:
            base_idle = 600
        self.timeout_seconds = base_idle + 60  # 第一层之外的兜底关闭

        # {"mcp":true} 表示启用MCP功能
        self.features = None

        # LLM 按模式实例缓存（随连接释放）
        self._llm_cache = {}

    def _get_base_config(self) -> Dict[str, Any]:
        try:
            srv = getattr(self, "server", None)
            base_cfg = getattr(srv, "config", None) if srv else None
            if isinstance(base_cfg, dict):
                return base_cfg
        except Exception:
            pass
        return self.config if isinstance(self.config, dict) else {}

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

        base_cfg = self._get_base_config()
        # 读取映射
        mapping = {}
        try:
            mapping = base_cfg.get("llm_by_mode", {}) or {}
        except Exception:
            mapping = {}

        mapping_val = mapping.get(key, None)
        if mapping_val is None:
            # 用途未配置专用 LLM，回退 default 并记录告警
            try:
                self.logger.bind(tag=TAG).warning(
                    f"get_llm_for: 未找到用途 {key} 的 llm_by_mode 配置，回退到 default"
                )
            except Exception:
                pass
            mapping_val = mapping.get("default")

        alias = None
        overrides = None
        if isinstance(mapping_val, dict):
            # 支持 { alias: xxx, overrides: { model_name: '...' } } 或直接平铺覆盖字段
            alias = mapping_val.get("alias") or mapping_val.get("name") or mapping_val.get("module") or mapping_val.get("llm")
            overrides = mapping_val.get("overrides")
            if overrides is None:
                # 将除别名键外的其余键视为覆盖
                tmp = dict(mapping_val)
                for k in ["alias", "name", "module", "llm", "overrides"]:
                    tmp.pop(k, None)
                overrides = tmp if len(tmp) > 0 else None
        elif isinstance(mapping_val, str) and len(mapping_val) > 0:
            alias = mapping_val

        # 回退默认 alias
        try:
            if alias is None:
                alias = self.config["selected_module"]["LLM"]
        except Exception:
            alias = None

        # 若无覆盖且别名等于当前默认，直接复用
        try:
            current_default_alias = self.config["selected_module"]["LLM"]
            if (overrides is None or len(overrides) == 0) and alias == current_default_alias and getattr(self, "llm", None) is not None:
                self._llm_cache[key] = self.llm
                return self.llm
        except Exception:
            pass

        # 构造/复用实例（合并覆盖）：优先使用 server 级共享注册表
        try:
            from core.utils import llm as llm_utils
            base_conf = None
            if alias:
                base_conf = copy.deepcopy(self.config.get("LLM", {}).get(alias))
                # 若连接级配置未包含该别名，尝试从服务器级配置读取（支持热更）
                if not base_conf:
                    try:
                        srv = getattr(self, "server", None)
                        srv_cfg = getattr(srv, "config", None) if srv else None
                        if isinstance(srv_cfg, dict):
                            base_conf = copy.deepcopy(srv_cfg.get("LLM", {}).get(alias))
                    except Exception:
                        pass
            if not base_conf:
                # 回退：无对应配置则复用默认，并给出一次告警
                try:
                    self.logger.bind(tag=TAG).warning(
                        f"get_llm_for: llm_by_mode[{key}] 别名未命中(alias={alias}), 回退默认LLM"
                    )
                except Exception:
                    pass
                self._llm_cache[key] = self.llm
                return self.llm
            # 若 server 提供共享注册表，优先复用
            try:
                srv = getattr(self, "server", None)
                if srv and hasattr(srv, "get_or_create_llm") and callable(getattr(srv, "get_or_create_llm")):
                    instance = srv.get_or_create_llm(alias, overrides)
                else:
                    # 直接合并覆盖并创建独立实例
                    if overrides and isinstance(overrides, dict):
                        for k, v in overrides.items():
                            base_conf[k] = v
                    llm_type = base_conf.get("type", alias)
                    instance = llm_utils.create_instance(llm_type, base_conf)
            except Exception:
                if overrides and isinstance(overrides, dict):
                    for k, v in overrides.items():
                        base_conf[k] = v
                llm_type = base_conf.get("type", alias)
                instance = llm_utils.create_instance(llm_type, base_conf)
            self._llm_cache[key] = instance
            return instance
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"get_llm_for 失败({key}): {e}，回退默认LLM")
            self._llm_cache[key] = self.llm
            return self.llm

    async def handle_connection(self, ws, path=None):
        try:
            # 绑定当前运行事件循环供跨线程调度使用
            try:
                self.loop = asyncio.get_running_loop()
            except Exception:
                self.loop = asyncio.get_event_loop()
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
                self.headers = headers_lower
            except Exception:
                self.headers = {}

            # 优先从 URL 查询参数解析 device-id/client-id；其次尝试 Header；最后回退

            def _normalize_id(value: str | None) -> str | None:
                if value is None:
                    return None
                try:
                    v = str(value).strip().strip('"').strip("'")
                    if v == "":
                        return None
                    return v.lower()
                except Exception:
                    return None

            device_id_from_query = None
            client_id_from_query = None
            try:
                candidate_paths = []
                if isinstance(path, str) and len(path) > 0:
                    candidate_paths.append(path)
                ws_path = getattr(ws, "path", "")
                if isinstance(ws_path, str) and len(ws_path) > 0 and ws_path not in candidate_paths:
                    candidate_paths.append(ws_path)
                # 兼容不同版本 websockets 的属性命名，尽量获取带 query 的原始 URI
                for attr in ["request_uri", "raw_request_uri", "request_path", "raw_path"]:
                    try:
                        val = getattr(ws, attr, "")
                        if isinstance(val, str) and len(val) > 0 and val not in candidate_paths:
                            candidate_paths.append(val)
                    except Exception:
                        pass
                # 从候选 path 中解析 query 参数（统一解析函数）
                for p in candidate_paths:
                    try:
                        did, cid, _ = parse_ids_from_handshake(p)
                        if did:
                            device_id_from_query = _normalize_id(did)
                            client_id_from_query = _normalize_id(cid or did)
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            # 兜底：从 server 的握手缓存读取（适配 websockets 传参差异）
            try:
                server_obj = getattr(self, "server", None)
                if (device_id_from_query is None) and server_obj is not None:
                    cache = getattr(server_obj, "_handshake_cache", None)
                    if isinstance(cache, dict):
                        # 按连接对象 id 存储
                        cached = cache.get(id(ws))
                        if isinstance(cached, dict):
                            did = cached.get("device-id")
                            cid = cached.get("client-id") or did
                            device_id_from_query = _normalize_id(did)
                            client_id_from_query = _normalize_id(cid)
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
                # 打印来源与解析快照（包含原始 path 片段便于定位异常客户端）
                try:
                    raw_paths_snapshot = []
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                        for attr in ["request_uri", "raw_request_uri", "request_path", "raw_path"]:
                            val = getattr(ws, attr, "")
                            if isinstance(val, str) and val:
                                raw_paths_snapshot.append(val[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    src = "query" if device_id_from_query else "header"
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={src}, rawPaths={truncate_for_log(str(raw_paths_snapshot))})"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={'query' if device_id_from_query else 'header'})"
                    )
            else:
                # 容错：仍未取到则自动分配，保证连接可用；同时输出诊断快照
                auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
                self.headers["device-id"] = auto_device_id
                self.headers["client-id"] = auto_device_id
                try:
                    raw_paths_snapshot = []
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    header_keys = list(self.headers.keys())
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}; rawPaths={truncate_for_log(str(raw_paths_snapshot))}, headerKeys={truncate_for_log(str(header_keys))}"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}"
                    )
            # 获取客户端ip地址
            try:
                remote = getattr(ws, "remote_address", None)
                if isinstance(remote, tuple) and len(remote) >= 1:
                    self.client_ip = remote[0]
                else:
                    self.client_ip = str(remote) if remote is not None else ""
            except Exception:
                self.client_ip = ""
            self.logger.bind(tag=TAG).info(
                f"{self.client_ip} conn - Headers: {self.headers}"
            )

            # 进行认证
            await self.auth.authenticate(self.headers)

            # 认证通过,继续处理
            self.websocket = ws
            self.device_id = self.headers.get("device-id", None)
            # 在 server 上注册设备路由（自动断开旧连接）
            if self.server and self.device_id:
                ok = await self.server.register_device_handler(self.device_id, self)
                if ok is False:
                    self.logger.bind(tag=TAG).error(f"设备注册失败: {self.device_id}")
                    await ws.send("设备注册失败")
                    await self.close(ws)
                    return

            # 启动超时检查任务
            self.timeout_task = asyncio.create_task(self._check_timeout())

            self.welcome_msg = self.config["xiaozhi"]
            self.welcome_msg["session_id"] = self.session_id
            await self.send_json(self.welcome_msg)

            # 获取差异化配置
            self._initialize_private_config()
            # 异步初始化
            self.executor.submit(self._initialize_components)

            try:
                async for message in self.websocket:
                    await self._route_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.bind(tag=TAG).info("客户端断开连接")

        except AuthenticationError as e:
            self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
            return
        except Exception as e:
            stack_trace = traceback.format_exc()
            try:
                safe_e = truncate_for_log(str(e))
                safe_tb = truncate_for_log(stack_trace)
            except Exception:
                safe_e = str(e)
                safe_tb = stack_trace
            self.logger.bind(tag=TAG).error(f"Connection error: {safe_e}-{safe_tb}")
            return
        finally:
            try:
                # 注销设备路由映射
                if self.server and self.device_id:
                    await self.server.unregister_device_handler(self.device_id, self)
            finally:
                await self._save_and_close(ws)

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

    def reset_timeout(self):
        """重置超时计时器"""
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
        self.timeout_task = asyncio.create_task(self._check_timeout())

    async def _route_message(self, message):
        """消息路由"""
        # 重置超时计时器
        self.reset_timeout()

        if isinstance(message, str):
            # 轻量 ping/keepalive：收到后仅重置计时器并忽略
            try:
                import json as _json
                try:
                    obj = _json.loads(message)
                except Exception:
                    obj = None
                if isinstance(obj, dict) and obj.get("type") in ("ping", "keepalive"):
                    try:
                        # 可选：立即回 pong
                        await self.websocket.send(_json.dumps({"type": "pong"}))
                    except Exception:
                        pass
                    return
            except Exception:
                pass
            await handleTextMessage(self, message)
        elif isinstance(message, bytes):
            if self.vad is None:
                return
            if self.asr is None:
                return
            self.asr_audio_queue.put(message)

    async def handle_restart(self, message):
        """处理服务器重启请求"""
        try:

            self.logger.bind(tag=TAG).info("收到服务器重启指令，准备执行...")

            # 发送确认响应
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "success",
                        "message": "服务器重启中...",
                        "content": {"action": "restart"},
                    }
                )
            )

            # 异步执行重启操作
            def restart_server():
                """实际执行重启的方法"""
                time.sleep(1)
                self.logger.bind(tag=TAG).info("执行服务器重启...")
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
                os._exit(0)

            # 使用线程执行重启避免阻塞事件循环
            threading.Thread(target=restart_server, daemon=True).start()

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"重启失败: {str(e)}")
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "error",
                        "message": f"Restart failed: {str(e)}",
                        "content": {"action": "restart"},
                    }
                )
            )

    def _initialize_components(self):
        try:
            self.selected_module_str = build_module_string(
                self.config.get("selected_module", {})
            )
            update_module_string(self.selected_module_str)
            """初始化组件"""
            if self.config.get("prompt") is not None:
                self.prompt = self.config["prompt"]
                self.change_system_prompt(self.prompt)
                self.logger.bind(tag=TAG).info(
                    f"初始化组件: prompt成功 {self.prompt[:50]}..."
                )

            """初始化本地组件"""
            if self.vad is None:
                self.vad = self._vad
            if self.asr is None:
                self.asr = self._initialize_asr()
            # 打开语音识别通道
            asyncio.run_coroutine_threadsafe(self.asr.open_audio_channels(self), self.loop)

            if self.tts is None:
                self.tts = self._initialize_tts()
            # 会议模式可禁用 TTS 通道（懒启动）
            disable_tts = False
            try:
                srv = getattr(self, "server", None)
                base_cfg = getattr(srv, "config", None) if srv else None
                if isinstance(base_cfg, dict):
                    meeting_cfg2 = base_cfg.get("meeting", {})
                else:
                    meeting_cfg2 = self.config.get("meeting", {})
                disable_tts = bool(meeting_cfg2.get("disable_tts", False))
            except Exception:
                disable_tts = False
            if not disable_tts:
                asyncio.run_coroutine_threadsafe(self.tts.open_audio_channels(self), self.loop)

            """加载记忆"""
            self._initialize_memory()
            """加载意图识别"""
            self._initialize_intent()
            """初始化上报线程"""
            self._init_report_threads()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"实例化组件失败: {e}")

    def _init_report_threads(self):
        """初始化ASR和TTS上报线程"""
        if not self.read_config_from_api or self.need_bind:
            return
        if self.chat_history_conf == 0:
            return
        if self.report_thread is None or not self.report_thread.is_alive():
            self.report_thread = threading.Thread(
                target=self._report_worker, daemon=True
            )
            self.report_thread.start()
            self.logger.bind(tag=TAG).info("TTS上报线程已启动")

    def _initialize_tts(self):
        """初始化TTS"""
        tts = None
        if not self.need_bind:
            tts = initialize_tts(self.config)

        if tts is None:
            tts = DefaultTTS(self.config, delete_audio_file=True)

        return tts

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

    def _initialize_private_config(self):
        """如果是从配置文件获取，则进行二次实例化"""
        if not self.read_config_from_api:
            return
        """从接口获取差异化的配置进行二次实例化，非全量重新实例化"""
        try:
            begin_time = time.time()
            private_config = get_private_config_from_api(
                self.config,
                self.headers.get("device-id"),
                self.headers.get("client-id", self.headers.get("device-id")),
            )
            private_config["delete_audio"] = bool(self.config.get("delete_audio", True))
            self.logger.bind(tag=TAG).info(
                f"{time.time() - begin_time} 秒，获取差异化配置成功: {json.dumps(filter_sensitive_info(private_config), ensure_ascii=False)}"
            )
        except DeviceNotFoundException as e:
            self.need_bind = True
            private_config = {}
        except DeviceBindException as e:
            self.need_bind = True
            self.bind_code = e.bind_code
            private_config = {}
        except Exception as e:
            self.need_bind = True
            self.logger.bind(tag=TAG).error(f"获取差异化配置失败: {e}")
            private_config = {}

        init_llm, init_tts, init_memory, init_intent = (
            False,
            False,
            False,
            False,
        )

        init_vad = check_vad_update(self.common_config, private_config)
        init_asr = check_asr_update(self.common_config, private_config)

        if init_vad:
            self.config["VAD"] = private_config["VAD"]
            self.config["selected_module"]["VAD"] = private_config["selected_module"][
                "VAD"
            ]
        if init_asr:
            self.config["ASR"] = private_config["ASR"]
            self.config["selected_module"]["ASR"] = private_config["selected_module"][
                "ASR"
            ]
        if private_config.get("TTS", None) is not None:
            init_tts = True
            self.config["TTS"] = private_config["TTS"]
            self.config["selected_module"]["TTS"] = private_config["selected_module"][
                "TTS"
            ]
        if private_config.get("LLM", None) is not None:
            init_llm = True
            self.config["LLM"] = private_config["LLM"]
            self.config["selected_module"]["LLM"] = private_config["selected_module"][
                "LLM"
            ]
        if private_config.get("Memory", None) is not None:
            init_memory = True
            self.config["Memory"] = private_config["Memory"]
            self.config["selected_module"]["Memory"] = private_config[
                "selected_module"
            ]["Memory"]
        if private_config.get("Intent", None) is not None:
            init_intent = True
            self.config["Intent"] = private_config["Intent"]
            model_intent = private_config.get("selected_module", {}).get("Intent", {})
            self.config["selected_module"]["Intent"] = model_intent
            # 加载插件配置
            if model_intent != "Intent_nointent":
                plugin_from_server = private_config.get("plugins", {})
                for plugin, config_str in plugin_from_server.items():
                    plugin_from_server[plugin] = json.loads(config_str)
                self.config["plugins"] = plugin_from_server
                self.config["Intent"][self.config["selected_module"]["Intent"]][
                    "functions"
                ] = plugin_from_server.keys()
        if private_config.get("prompt", None) is not None:
            self.config["prompt"] = private_config["prompt"]
        if private_config.get("summaryMemory", None) is not None:
            self.config["summaryMemory"] = private_config["summaryMemory"]
        if private_config.get("device_max_output_size", None) is not None:
            self.max_output_size = int(private_config["device_max_output_size"])
        if private_config.get("chat_history_conf", None) is not None:
            self.chat_history_conf = int(private_config["chat_history_conf"])
        try:
            modules = initialize_modules(
                self.logger,
                private_config,
                init_vad,
                init_asr,
                init_llm,
                init_tts,
                init_memory,
                init_intent,
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"初始化组件失败: {e}")
            modules = {}
        if modules.get("tts", None) is not None:
            self.tts = modules["tts"]
        if modules.get("vad", None) is not None:
            self.vad = modules["vad"]
        if modules.get("asr", None) is not None:
            self.asr = modules["asr"]
        if modules.get("llm", None) is not None:
            self.llm = modules["llm"]
        if modules.get("intent", None) is not None:
            self.intent = modules["intent"]
        if modules.get("memory", None) is not None:
            self.memory = modules["memory"]

    def _initialize_memory(self):
        if self.memory is None:
            return
        """初始化记忆模块"""
        # 按模式选择记忆总结 LLM（可被 llm_by_mode.memory 覆盖）
        chosen_llm = self.llm
        try:
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                selected = self.get_llm_for("memory")
                if selected is not None:
                    chosen_llm = selected
        except Exception:
            pass

        self.memory.init_memory(
            role_id=self.device_id,
            llm=chosen_llm,
            summary_memory=self.config.get("summaryMemory", None),
            save_to_file=not self.read_config_from_api,
        )

        # 获取记忆总结配置
        memory_config = self.config["Memory"]
        memory_type = self.config["Memory"][self.config["selected_module"]["Memory"]][
            "type"
        ]
        # 如果使用 nomen，直接返回
        if memory_type == "nomem":
            return
        # 使用 mem_local_short 模式
        elif memory_type == "mem_local_short":
            memory_llm_name = memory_config[self.config["selected_module"]["Memory"]][
                "llm"
            ]
            if memory_llm_name and memory_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                memory_llm_config = self.config["LLM"][memory_llm_name]
                memory_llm_type = memory_llm_config.get("type", memory_llm_name)
                memory_llm = llm_utils.create_instance(
                    memory_llm_type, memory_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为记忆总结创建了专用LLM: {memory_llm_name}, 类型: {memory_llm_type}"
                )
                self.memory.set_llm(memory_llm)
            else:
                # 否则使用主LLM
                self.memory.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

    def _initialize_intent(self):
        if self.intent is None:
            return
        self.intent_type = self.config["Intent"][
            self.config["selected_module"]["Intent"]
        ]["type"]
        if self.intent_type == "function_call" or self.intent_type == "intent_llm":
            self.load_function_plugin = True
        """初始化意图识别模块"""
        # 获取意图识别配置
        intent_config = self.config["Intent"]
        intent_type = self.config["Intent"][self.config["selected_module"]["Intent"]][
            "type"
        ]

        # 如果使用 nointent，直接返回
        if intent_type == "nointent":
            return
        # 使用 intent_llm 模式
        elif intent_type == "intent_llm":
            intent_llm_name = intent_config[self.config["selected_module"]["Intent"]][
                "llm"
            ]

            if intent_llm_name and intent_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                intent_llm_config = self.config["LLM"][intent_llm_name]
                intent_llm_type = intent_llm_config.get("type", intent_llm_name)
                intent_llm = llm_utils.create_instance(
                    intent_llm_type, intent_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为意图识别创建了专用LLM: {intent_llm_name}, 类型: {intent_llm_type}"
                )
                # 按模式选择意图识别 LLM（可被 llm_by_mode.intent 覆盖）
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(intent_llm)
                    else:
                        self.intent.set_llm(intent_llm)
                except Exception:
                    self.intent.set_llm(intent_llm)
            else:
                # 否则使用主LLM
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(self.llm)
                    else:
                        self.intent.set_llm(self.llm)
                except Exception:
                    self.intent.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

        """加载插件"""
        self.func_handler = FunctionHandler(self)
        self.mcp_manager = MCPManager(self)

        """加载MCP工具"""
        asyncio.run_coroutine_threadsafe(
            self.mcp_manager.initialize_servers(), self.loop
        )

    def change_system_prompt(self, prompt):
        self.prompt = prompt
        # 更新系统prompt至上下文
        self.dialogue.update_system_message(self.prompt)

    def chat(self, query, tool_call=False):
        try:
            safe_query = truncate_for_log(query)
        except Exception:
            safe_query = query
        self.logger.bind(tag=TAG).info(f"大模型收到用户消息: {safe_query}")
        self.llm_finish_task = False

        if not tool_call:
            self.dialogue.put(Message(role="user", content=query))

        # Define intent functions
        functions = None
        if self.intent_type == "function_call" and hasattr(self, "func_handler"):
            functions = self.func_handler.get_functions()
        if hasattr(self, "mcp_client"):
            mcp_tools = self.mcp_client.get_available_tools()
            if mcp_tools is not None and len(mcp_tools) > 0:
                if functions is None:
                    functions = []
                functions.extend(mcp_tools)
        response_message = []

        try:
            # 使用带记忆的对话
            memory_str = None
            if self.memory is not None:
                future = asyncio.run_coroutine_threadsafe(
                    self.memory.query_memory(query), self.loop
                )
                memory_str = future.result()

            self.sentence_id = str(uuid.uuid4().hex)


            # 按当前模式选择 LLM（默认chat；coding/working 切换对应别名）
            purpose = self.current_mode or "chat"
            active_llm = self.llm
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                try:
                    active_llm = self.get_llm_for(purpose) or self.llm
                except Exception:
                    active_llm = self.llm

            if self.intent_type == "function_call" and functions is not None:
                # 使用支持functions的streaming接口
                llm_responses = active_llm.response_with_functions(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                    functions=functions,
                )
            else:
                llm_responses = active_llm.response(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM 处理出错 {query}: {e}")
            return None

        # 处理流式响应
        tool_call_flag = False
        function_name = None
        function_id = None
        function_arguments = ""
        content_arguments = ""
        text_index = 0
        self.client_abort = False
        for response in llm_responses:
            if self.client_abort:
                break
            if self.intent_type == "function_call" and functions is not None:
                content, tools_call = response
                if "content" in response:
                    content = response["content"]
                    tools_call = None
                if content is not None and len(content) > 0:
                    content_arguments += content

                if not tool_call_flag and content_arguments.startswith("<tool_call>"):
                    # print("content_arguments", content_arguments)
                    tool_call_flag = True

                if tools_call is not None and len(tools_call) > 0:
                    tool_call_flag = True
                    if tools_call[0].id is not None:
                        function_id = tools_call[0].id
                    if tools_call[0].function.name is not None:
                        function_name = tools_call[0].function.name
                    if tools_call[0].function.arguments is not None:
                        function_arguments += tools_call[0].function.arguments
            else:
                content = response
            if content is not None and len(content) > 0:
                if not tool_call_flag:
                    response_message.append(content)
                    if text_index == 0:
                        self.tts.tts_text_queue.put(
                            TTSMessageDTO(
                                sentence_id=self.sentence_id,
                                sentence_type=SentenceType.FIRST,
                                content_type=ContentType.ACTION,
                            )
                        )
                    self.tts.tts_text_queue.put(
                        TTSMessageDTO(
                            sentence_id=self.sentence_id,
                            sentence_type=SentenceType.MIDDLE,
                            content_type=ContentType.TEXT,
                            content_detail=content,
                        )
                    )
                    text_index += 1
        # 处理function call
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
            if not bHasError:
                response_message.clear()
                self.logger.bind(tag=TAG).debug(
                    f"function_name={function_name}, function_id={function_id}, function_arguments={function_arguments}"
                )
                function_call_data = {
                    "name": function_name,
                    "id": function_id,
                    "arguments": function_arguments,
                }

                # 处理Server端MCP工具调用
                if self.mcp_manager.is_mcp_tool(function_name):
                    result = self._handle_mcp_tool_call(function_call_data)
                elif hasattr(self, "mcp_client") and self.mcp_client.has_tool(
                    function_name
                ):
                    # 如果是小智端MCP工具调用
                    self.logger.bind(tag=TAG).debug(
                        f"调用小智端MCP工具: {function_name}, 参数: {function_arguments}"
                    )
                    try:
                        result = asyncio.run_coroutine_threadsafe(
                            call_mcp_tool(
                                self, self.mcp_client, function_name, function_arguments
                            ),
                            self.loop,
                        ).result()
                        self.logger.bind(tag=TAG).debug(f"MCP工具调用结果: {result}")

                        resultJson = None
                        if isinstance(result, str):
                            try:
                                resultJson = json.loads(result)
                            except Exception as e:
                                self.logger.bind(tag=TAG).error(
                                    f"解析MCP工具返回结果失败: {e}"
                                )

                        # 视觉大模型不经过二次LLM处理
                        if (
                            resultJson is not None
                            and isinstance(resultJson, dict)
                            and "action" in resultJson
                        ):
                            result = ActionResponse(
                                action=Action[resultJson["action"]],
                                result=None,
                                response=resultJson.get("response", ""),
                            )
                        else:
                            result = ActionResponse(
                                action=Action.REQLLM, result=result, response=""
                            )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"MCP工具调用失败: {e}")
                        result = ActionResponse(
                            action=Action.REQLLM, result="MCP工具调用失败", response=""
                        )
                else:
                    # 处理系统函数
                    result = self.func_handler.handle_llm_function_call(
                        self, function_call_data
                    )
                self._handle_function_result(result, function_call_data)

        # 存储对话内容
        if len(response_message) > 0:
            self.dialogue.put(
                Message(role="assistant", content="".join(response_message))
            )
        if text_index > 0:
            self.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=self.sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )
        self.llm_finish_task = True
        self.logger.bind(tag=TAG).debug(
            json.dumps(self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False)
        )

        return True

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

            tool_result = asyncio.run_coroutine_threadsafe(
                self.mcp_manager.execute_tool(function_name, args_dict), self.loop
            ).result()
            # meta=None content=[TextContent(type='text', text='北京当前天气:\n温度: 21°C\n天气: 晴\n湿度: 6%\n风向: 西北 风\n风力等级: 5级', annotations=None)] isError=False
            content_text = ""
            if tool_result is not None and tool_result.content is not None:
                for content in tool_result.content:
                    content_type = content.type
                    if content_type == "text":
                        content_text = content.text
                    elif content_type == "image":
                        pass

            if len(content_text) > 0:
                return ActionResponse(
                    action=Action.REQLLM, result=content_text, response=""
                )

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP工具调用错误: {e}")
            return ActionResponse(
                action=Action.REQLLM, result="工具调用出错", response=""
            )

        return ActionResponse(action=Action.REQLLM, result="工具调用出错", response="")

    def _handle_function_result(self, result, function_call_data):
        if result.action == Action.RESPONSE:  # 直接回复前端
            text = result.response
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        elif result.action == Action.REQLLM:  # 调用函数后再请求llm生成回复
            text = result.result
            if text is not None and len(text) > 0:
                function_id = function_call_data["id"]
                function_name = function_call_data["name"]
                function_arguments = function_call_data["arguments"]
                self.dialogue.put(
                    Message(
                        role="assistant",
                        tool_calls=[
                            {
                                "id": function_id,
                                "function": {
                                    "arguments": function_arguments,
                                    "name": function_name,
                                },
                                "type": "function",
                                "index": 0,
                            }
                        ],
                    )
                )

                self.dialogue.put(
                    Message(
                        role="tool",
                        tool_call_id=(
                            str(uuid.uuid4()) if function_id is None else function_id
                        ),
                        content=text,
                    )
                )
                self.chat(text, tool_call=True)
        elif result.action == Action.NOTFOUND or result.action == Action.ERROR:
            text = result.result
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        else:
            pass

    def _report_worker(self):
        """聊天记录上报工作线程"""
        while not self.stop_event.is_set():
            try:
                # 从队列获取数据，设置超时以便定期检查停止事件
                item = self.report_queue.get(timeout=1)
                if item is None:  # 检测毒丸对象
                    break
                type, text, audio_data, report_time = item
                try:
                    # 检查线程池状态
                    if self.executor is None:
                        continue
                    # 提交任务到线程池
                    self.executor.submit(
                        self._process_report, type, text, audio_data, report_time
                    )
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"聊天记录上报线程异常: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"聊天记录上报工作线程异常: {e}")

        self.logger.bind(tag=TAG).info("聊天记录上报线程已退出")

    def _process_report(self, type, text, audio_data, report_time):
        """处理上报任务"""
        try:
            # 执行上报（传入二进制数据）
            report(self, type, text, audio_data, report_time)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"上报处理异常: {e}")
        finally:
            # 标记任务完成
            self.report_queue.task_done()

    def clearSpeakStatus(self):
        self.client_is_speaking = False
        self.logger.bind(tag=TAG).debug(f"清除服务端讲话状态")

    async def close(self, ws=None):
        """资源清理方法"""
        try:
            # 取消超时任务
            if self.timeout_task:
                self.timeout_task.cancel()
                self.timeout_task = None

            # 取消编码洞察定时任务
            try:
                if hasattr(self, "coding_insight_task") and self.coding_insight_task and not self.coding_insight_task.done():
                    self.coding_insight_task.cancel()
            except Exception:
                pass

            # 清理MCP资源
            if hasattr(self, "mcp_manager") and self.mcp_manager:
                await self.mcp_manager.cleanup_all()

            # 触发停止事件
            if self.stop_event:
                self.stop_event.set()

            # 清空任务队列
            self.clear_queues()

            # 关闭WebSocket连接
            if ws:
                await ws.close()
            elif self.websocket:
                await self.websocket.close()

            # 最后关闭线程池（避免阻塞）
            if self.executor:
                try:
                    # Python 3.9+ 支持 cancel_futures
                    self.executor.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    self.executor.shutdown(wait=False)
                self.executor = None

            # 清理 LLM 实例缓存
            try:
                if hasattr(self, "_llm_cache") and isinstance(self._llm_cache, dict):
                    self._llm_cache.clear()
            except Exception:
                pass

            # 关闭 asr/tts/llm 资源
            try:
                if hasattr(self, "asr") and hasattr(self.asr, "close") and callable(getattr(self.asr, "close")):
                    maybe_close = self.asr.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "tts") and hasattr(self.tts, "close") and callable(getattr(self.tts, "close")):
                    maybe_close = self.tts.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "llm") and hasattr(self.llm, "close") and callable(getattr(self.llm, "close")):
                    maybe_close = self.llm.close()  # 供应商可选实现
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass

            self.logger.bind(tag=TAG).info("连接资源已释放")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"关闭连接时出错: {e}")

    def clear_queues(self):
        """清空所有任务队列"""
        if self.tts:
            self.logger.bind(tag=TAG).debug(
                f"开始清理: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

            # 使用非阻塞方式清空队列
            for q in [
                self.tts.tts_text_queue,
                self.tts.tts_audio_queue,
                self.report_queue,
            ]:
                if not q:
                    continue
                while True:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break

            self.logger.bind(tag=TAG).debug(
                f"清理结束: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

    def reset_vad_states(self):
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0
        self.client_voice_stop = False
        self.logger.bind(tag=TAG).debug("VAD states reset.")

    async def send_text(self, text: str) -> None:
        """统一文本发送包装。"""
        try:
            if self.websocket:
                await self.websocket.send(text)
        except Exception:
            pass

    async def send_json(self, payload: dict) -> None:
        """统一 JSON 发送包装，自动兼容 send_json 缺失并回退字符串。"""
        try:
            if self.websocket is None:
                return
            try:
                await self.websocket.send_json(payload)
            except AttributeError:
                import json as _json
                await self.websocket.send(_json.dumps(payload, ensure_ascii=False))
        except Exception:
            # 发送错误不应中断主流程
            pass

    def chat_and_close(self, text):
        """Chat with the user and then close the connection"""
        try:
            # Use the existing chat method
            self.chat(text)

            # After chat is complete, close the connection
            self.close_after_chat = True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Chat and close error: {str(e)}")

    async def _check_timeout(self):
        """检查连接超时"""
        try:
            while not self.stop_event.is_set():
                await asyncio.sleep(self.timeout_seconds)
                if not self.stop_event.is_set():
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
                    if self.stop_event.is_set():
                        break
                    self.logger.bind(tag=TAG).info("连接超时，准备关闭")
                    await self.close(self.websocket)
                    break
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"超时检查任务出错: {e}")

```

```python
*** Begin Patch
*** Update File: /Users/tlovo/code_ai/Badge-ai/backend/core/providers/asr/base.py
@@
     async def receive_audio(self, conn, audio, audio_have_voice):
-        if conn.client_listen_mode == "auto" or conn.client_listen_mode == "realtime":
-            have_voice = audio_have_voice
-        else:
-            # 设备侧边界优先；若长时间未收到 device listen start/stop，回退使用服务端VAD
-            try:
-                fallback_ms = int(((getattr(conn, "config", {}) or {}).get("meeting", {}) or {}).get("manual_listen_fallback_ms", 5000))
-            except Exception:
-                fallback_ms = 5000
-            last_listen_ms = int(getattr(conn, "_last_listen_event_ms", 0) or 0)
-            now_ms = int(time.time() * 1000)
-            if last_listen_ms <= 0 or (now_ms - last_listen_ms) > fallback_ms:
-                have_voice = audio_have_voice
-            else:
-                have_voice = conn.client_have_voice
+        # 基于有限状态机与模式的分段策略
+        listen_mode = getattr(conn, "client_listen_mode", "auto")
+        listen_state = getattr(conn, "listen_state", "idle")
+        have_voice = audio_have_voice
+        if listen_mode != "auto":
+            # 设备侧边界优先；必要时使用回退超时启用服务端VAD
+            try:
+                fallback_ms = int(((getattr(conn, "config", {}) or {}).get("meeting", {}) or {}).get("manual_listen_fallback_ms", 5000))
+            except Exception:
+                fallback_ms = 5000
+            last_listen_ms = int(getattr(conn, "_last_listen_event_ms", 0) or 0)
+            now_ms = int(time.time() * 1000)
+            fallback_active = (last_listen_ms <= 0) or ((now_ms - last_listen_ms) > fallback_ms)
+            if not fallback_active:
+                if listen_state == "idle":
+                    # 非监听期丢弃（保留少量尾缓冲）
+                    conn.asr_audio.append(audio)
+                    conn.asr_audio = conn.asr_audio[-10:]
+                    return
+                elif listen_state == "listening":
+                    have_voice = True if conn.client_have_voice else audio_have_voice
+                elif listen_state == "finalizing":
+                    # 立即触发一次结束识别
+                    asr_audio_task = copy.deepcopy(conn.asr_audio)
+                    conn.asr_audio.clear()
+                    conn.reset_vad_states()
+                    if len(asr_audio_task) > 15:
+                        await self.handle_voice_stop(conn, asr_audio_task)
+                    # 回到 idle
+                    conn.listen_state = "idle"
+                    return
 
         # 如果本次没有声音，本段也没声音，就把声音丢弃了
         conn.asr_audio.append(audio)
         if have_voice == False and conn.client_have_voice == False:
             conn.asr_audio = conn.asr_audio[-10:]
             return
@@
     async def handle_voice_stop(self, conn, asr_audio_task):
@@
-            try:
-                now_ms = int(time.time() * 1000)
-                payload = {"type": "audio", "event": "transcription", "text": raw_text, "ts": now_ms, "session_id": getattr(conn, "session_id", "")}
-                try:
-                    await conn.websocket.send_json(payload)
-                except AttributeError:
-                    await conn.websocket.send(json.dumps(payload, ensure_ascii=False))
-            except Exception:
-                pass
+            try:
+                now_ms = int(time.time() * 1000)
+                payload = {"type": "audio", "event": "transcription", "text": raw_text, "ts": now_ms, "session_id": getattr(conn, "session_id", "")}
+                try:
+                    await conn.send_json(payload)
+                except Exception:
+                    pass
+            except Exception:
+                pass
*** End Patch
```

```python
*** Begin Patch
*** Update File: /Users/tlovo/code_ai/Badge-ai/backend/core/providers/asr/base.py
@@
     async def receive_audio(self, conn, audio, audio_have_voice):
-        if conn.client_listen_mode == "auto" or conn.client_listen_mode == "realtime":
-            have_voice = audio_have_voice
-        else:
-            # 设备侧边界优先；若长时间未收到 device listen start/stop，回退使用服务端VAD
-            try:
-                fallback_ms = int(((getattr(conn, "config", {}) or {}).get("meeting", {}) or {}).get("manual_listen_fallback_ms", 5000))
-            except Exception:
-                fallback_ms = 5000
-            last_listen_ms = int(getattr(conn, "_last_listen_event_ms", 0) or 0)
-            now_ms = int(time.time() * 1000)
-            if last_listen_ms <= 0 or (now_ms - last_listen_ms) > fallback_ms:
-                have_voice = audio_have_voice
-            else:
-                have_voice = conn.client_have_voice
+        # 有限状态机 + 回退策略
+        listen_mode = getattr(conn, "client_listen_mode", "auto")
+        have_voice = audio_have_voice
+        if listen_mode != "auto":
+            try:
+                fallback_ms = int(((getattr(conn, "config", {}) or {}).get("meeting", {}) or {}).get("manual_listen_fallback_ms", 5000))
+            except Exception:
+                fallback_ms = 5000
+            last_listen_ms = int(getattr(conn, "_last_listen_event_ms", 0) or 0)
+            now_ms = int(time.time() * 1000)
+            if last_listen_ms > 0 and (now_ms - last_listen_ms) <= fallback_ms:
+                # 设备边界有效期内：以设备标记为准
+                have_voice = conn.client_have_voice
 
         # 如果本次没有声音，本段也没声音，就把声音丢弃了
         conn.asr_audio.append(audio)
         if have_voice == False and conn.client_have_voice == False:
             conn.asr_audio = conn.asr_audio[-10:]
             return
@@
-            try:
-                now_ms = int(time.time() * 1000)
-                payload = {"type": "audio", "event": "transcription", "text": raw_text, "ts": now_ms, "session_id": getattr(conn, "session_id", "")}
-                try:
-                    await conn.websocket.send_json(payload)
-                except AttributeError:
-                    await conn.websocket.send(json.dumps(payload, ensure_ascii=False))
-            except Exception:
-                pass
+            try:
+                now_ms = int(time.time() * 1000)
+                payload = {"type": "audio", "event": "transcription", "text": raw_text, "ts": now_ms, "session_id": getattr(conn, "session_id", "")}
+                try:
+                    await conn.send_json(payload)
+                except Exception:
+                    pass
+            except Exception:
+                pass
*** End Patch
```

