---

**User**

为什么不新建 EinkRenderEngine 文件了?

---

**Cursor**

### 原因（简明）
- 为了“今天就能跑通”且不增复杂度：少文件、少接口、少CMake改动，直接在 `application.cc` 写一个简化渲染函数，风险最低、速度最快。
- 先验证链路，再抽象：Day 1 只要能收指令→渲染→回 ACK；等需求稳定（更多页面类型/分页/局部刷新）再抽成 `EinkRenderEngine` 不迟。
- 易回退/定位：出现问题只看一个文件，排查成本更低。

### 何时再拆出 `EinkRenderEngine`
- 出现这些需求任一即抽象：分页/滚动、`regionsChanged` 局部刷新、主题/字体复用、列表>2种显示风格、要做单元测试/多板共用。

### 可选折中（若你更想分层）
- 也可以先建一个极小壳（50行级），只暴露 `Render(title, body, hint)`，内部仍是整屏+节流；对 Day 1 工期几乎不变，但文件会多一对。

---

**User**

## 任务1 请用高中生能听懂方式举例说明解释一下这些需求的具体场景“分页/滚动、regionsChanged 局部刷新、主题/字体复用、列表>2种显示风格、要做单元测试/多板共用。”

## 任务2  EinkRenderEngine和极小壳的差距是什么?

## 任务3 最好的方式是啥?

---

**Cursor**

### 任务1：这些需求各是什么，什么时候会用到（通俗例子）
- 分页/滚动
  - 场景：任务列表有20条，但屏幕一次只能放下8条。分页=像翻书一样看第1/2/3页；滚动=像聊天记录往上推，始终只显示最近8条。
- regionsChanged 局部刷新
  - 场景：只改了“标题”或“页脚”，正文没变。局部刷新=只擦掉改动的那一小块重画，省时间、省电，减少闪烁；不用整屏重画。
- 主题/字体复用
  - 场景：不同模式统一风格（标题用黑体18号，正文用14号，页脚灰色细字），换主题只改一处配置，所有页面跟着换。
- 列表>2种显示风格
  - 场景：任务清单需要“[P0][进行中] 标题”样式；会议纪要是“• 要点”；编码日志是“[INFO]/[ERROR] 消息”。这就是3种以上的列表风格。
- 单元测试/多板共用
  - 场景：后续要换屏幕型号或新增板子，希望渲染代码不用重写；或在PC上跑单元测试验证“传入JSON→输出绘制指令”，不依赖真实硬件。

### 任务2：EinkRenderEngine vs “极小壳”，差别在哪
- 能力范围
  - 极小壳：只有一个超简接口（如 Render(title, body, hint)），整屏重画，忽略局部刷新、样式、状态管理。
  - EinkRenderEngine：支持头/体/脚分区、分页/滚动、regionsChanged 局部刷新、主题/字体、列表多风格、错误与边界处理。
- 可扩展性/复用
  - 极小壳：快速落地，后面要加功能时需要改外层逻辑或直接改实现，复用弱。
  - EinkRenderEngine：清晰分层（布局/绘制/样式），更容易在多板/多页面场景复用。
- 可测试性
  - 极小壳：几乎不做抽象，单测价值低。
  - EinkRenderEngine：可把“布局计算/分页/裁剪”做纯函数，写单元测试更容易。
- 复杂度/成本
  - 极小壳：最少文件/最少改动，今天就能跑；但未来扩展时可能要“翻修”。
  - EinkRenderEngine：前期多写一些代码/接口，但后期扩展平滑、维护成本更低。

### 任务3：最好的方式（结合你“只做核心、降复杂度”的原则）
- 今日（Day 1）：极小壳 or 直接在 application.cc 内部函数
  - 只做“能连、能收指令、能渲染、能回ACK”。实现 `ui.render(text/list)` + `device.control(net.banner)`，整屏重画+≥500ms节流。
  - 不建独立引擎类，避免新增文件与构建改动，最快打通链路。
- 近期（需要时再抽象）
  - 当出现以下任意诉求时，再把渲染函数平移为独立 `EinkRenderEngine`：
    - 需要分页/滚动（列表>8条）；
    - 需要根据 `regionsChanged` 真正做局部刷新；
    - 需要统一主题/字体并一处改全局；
    - 需要≥3种列表风格（任务/纪要/日志并存）；
    - 需要做渲染逻辑的单元测试或多板共用。
- 为什么这样最好
  - 满足你“只做核心、不过度设计”的要求：今天不增加复杂度，马上可测。
  - 给未来留了接口位置：一旦功能增长，平移为 `EinkRenderEngine` 的代价很小（把现有渲染函数挪到新文件即可），而不是推倒重来。

---

**User**

我认为不对,硬件需要保留开机动画与欢迎页；唤醒后切到“渲染测试页（文案固定：等待后端指令…）”。
然后直接一步到位 开发独立的EinkRenderEngine函数, 做到“能连、能收指令、能渲染、能回ACK”,后续在优化EinkRenderEngine函数来增加功能

---

**Cursor**

### 结论
- 同意你的方案：保留开机动画与欢迎页；唤醒后进入“渲染测试页（等待后端指令…）”；一步到位新建独立 `EinkRenderEngine`，先实现“能连、能收指令、能渲染、能回 ACK”，后续在同一引擎内迭代增强。

### 实施原则
- 不加额外复杂度：只支持最小协议子集（`ui.render: text|list`、`device.control: net.banner`）。
- 不要运行时开关：新路径直接生效。
- 不显示 MAC：仅显示“工牌编号 + 持有人”；未注册设备仅后端日志提示，不上屏。

### Day 1 硬件（p）工作清单
- 文件与接口
  - 新建 `hardware/main/display/eink_render_engine.h/.cc`
    - 最小接口：
      - `void Init(EinkDisplayST7306* display);`
      - `bool Render(const RenderPayload& payload);`  // 整屏刷新、≥500ms合并节流、UTF‑8截断、list≤8行
    - 最小数据结构（即可）：`RenderPayload{ page:string; headerTitle:string; bodyKind: TEXT|LIST; bodyText:string; bodyList:vector<string>; footerHint:string; }`
- 接入 `application.cc`
  - 开机动画→欢迎页保持不变；唤醒后切“渲染测试页（固定文案：等待后端指令…）”
  - 在 `OnIncomingJson` 仅保留两类分支：
    - `type=="ui.render"`：解析字段
      - 读 `header.title | body.kind in ["text","list"] | body.text | body.items | footer.hint | id?`
      - 组装 `RenderPayload`→ `EinkRenderEngine::Render(payload)`
      - 若含 `id`：渲染完成后回 `{type:"ui.ack",id,status:"ok"}`
      - 解析失败：回 `{type:"ui.error",id?,code:"INVALID_PAYLOAD"}`
    - `type=="device.control" && action=="net.banner"`：顶部 3s 横幅提示（简单绘制），含 `id` 则回 ACK
  - 记录日志（方便联调）：`[RENDER_RX] type/page/id`、`[RENDER_OK] id`、`[RENDER_ERR] code`
- 不做
  - 不实现 `listen.start/stop`、不做分页/滚动/局部刷新、无主题系统
- 验收（Day 1）
  - 上电→欢迎→唤醒→渲染测试页
  - 后端发三种载荷（text/list/net.banner）均正确显示并回 ACK
  - 断连重连后，能展示“最后一次渲染”的补投结果

### Day 1 后端（w+d）工作清单
- 设备映射已就绪：`backend/data/devices.yaml`（仅注入 `badge/owner` 到标题，未注册仅日志提示）
- 发送器（轻量）
  - `render_sender.py`：`send_render(conn,payload)` 限频每设备≤2 QPS、更新 `last_render_cache`（内存）
  - `send_control(conn,"net.banner",text,level,duration_ms)`
- 补投
  - `websocket_server`：设备注册成功后，如有 `last_render_cache` → 自动补发一次
- 最小编排/测试
  - 连接后发送一次欢迎 `ui.render`（标题“工牌{badge} · {owner}”，正文“连接成功”）
  - 准备小脚本/页面，向指定设备下发：
    - 文本渲染、列表渲染、`net.banner`，并检查 ACK

### 最小测试载荷（复制即用）
- 文本
```json
{ "type":"ui.render","id":"d1-001","page":"dialog.chat",
  "header":{"title":"工牌001 · 文先生"},
  "body":{"kind":"text","text":"Hello 渲染测试"},
  "footer":{"hint":"后端→设备 OK"} }
```
- 列表
```json
{ "type":"ui.render","id":"d1-002","page":"dialog.chat",
  "header":{"title":"工牌001 · 文先生"},
  "body":{"kind":"list","items":["第一行","第二行","第三行"]},
  "footer":{"hint":"最多显示8行"} }
```
- 顶部横幅
```json
{ "type":"device.control","id":"d1-003","action":"net.banner",
  "text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
```

### 明日（Day 2）在同一引擎内的增量（备忘）
- 增加 `coding.log`（logs 8行滚动窗口）
- 增加 `working.list` 分页（8/页，页脚“第x/共y页”）
- 清理不可用分支，保留引擎单一入口，继续整屏+节流；`regionsChanged` 与局刷留到后续

这样即可兼顾你的“核心最小可用”与“后续在同一模块持续增强”，今天就能并行联调。需要我落地文件骨架（空实现+接口）吗？

```json
{ "type":"ui.render","id":"d1-001","page":"dialog.chat",
  "header":{"title":"工牌001 · 文先生"},
  "body":{"kind":"text","text":"Hello 渲染测试"},
  "footer":{"hint":"后端→设备 OK"} }
```

```json
{ "type":"ui.render","id":"d1-002","page":"dialog.chat",
  "header":{"title":"工牌001 · 文先生"},
  "body":{"kind":"list","items":["第一行","第二行","第三行"]},
  "footer":{"hint":"最多显示8行"} }
```

```json
{ "type":"device.control","id":"d1-003","action":"net.banner",
  "text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
```

```json
{ "type":"device.control","id":"d1-003","action":"net.banner",
  "text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
```

---

**User**

不需要落地 我认为这是今天的第一阶段 将方案写入了build.md中 请再次仔细的审查一遍和详细的补全信息,然后项目就要开始了!

---

**Cursor**

```markdown
<<'PATCH'
*** Begin Patch
*** Update File: collaboration/build.md
@@
 ## 7. 附：最小页面负载样例
@@
 { "type":"ui.render", "page":"coding.log", "header":{ "title":"编码模式" }, "body":{ "kind":"logs", "lines":["build: 拉起构建","test: 单测通过","deploy: 部署完成" ] }, "footer":{ "hint":"phase: build" }, "regionsChanged":["body"], "id":"cd-001" }
 ```
 
+
+——
+
+## 8. Day 1 最小落地（最终版）
+
+- 原则（强约束）
+  - 不新增运行时开关，新路径直接生效。
+  - 只做“能连、能收指令、能渲染、能回 ACK”。
+  - 渲染仅支持 `ui.render` 的 `text|list` 两种 body；控制仅支持 `device.control: net.banner`；其余先忽略。
+  - 不显示 MAC；仅显示“工牌{badge} · {owner}”；无映射时 UI 不显示任何设备标识，仅后端日志提示“未注册设备:<mac>”。
+  - 整屏刷新 + 合并节流 ≥500ms；UTF‑8 安全截断；列表最多 8 行。
+
+- 硬件（p）今日任务
+  - 保留开机动画与欢迎页；唤醒后进入“渲染测试页”（固定文案：例如“等待后端指令…”）。
+  - 新建独立 `EinkRenderEngine`（最小版）：
+    - `void Init(EinkDisplayST7306* display);`
+    - `struct RenderPayload { std::string page; std::string headerTitle; enum { TEXT, LIST } bodyKind; std::string bodyText; std::vector<std::string> bodyList; std::string footerHint; };`
+    - `bool Render(const RenderPayload& p);`（整屏重画、≥500ms 节流、UTF‑8 截断、list≤8 行）
+  - 在 `application.cc::OnIncomingJson` 中仅保留两类分支：
+    - `type=="ui.render"`：解析 `header.title/body.kind/body.text|items/footer.hint/id?` → 组装 `RenderPayload` → `EinkRenderEngine::Render()`；如含 `id`，渲染完成后回 `{type:"ui.ack", id, status:"ok"}`；解析失败回 `{type:"ui.error", id?, code:"INVALID_PAYLOAD"}`。
+    - `type=="device.control" && action=="net.banner"`：顶部显示提示条 `duration_ms`（默认 3000ms），完成后如含 `id` 回 ACK。
+  - 不做：`listen.start/stop`、分页/滚动、regionsChanged 局部刷新、主题/字体系统、其他控制指令。
+
+- 后端（w+d）今日任务
+  - 轻量发送器与缓存：
+    - `render_sender.py`：`send_render(conn, payload)`（每设备≤2 QPS、调用 schema 清洗、更新 `last_render_cache`）；`send_control(conn, action="net.banner", **kw)`。
+    - `last_render_cache`：内存 `set_last/get_last`；设备注册成功后由 `websocket_server` 自动补发“最后一次渲染”。
+  - 设备映射：从 `backend/data/devices.yaml` 读取 `badge/owner` 注入标题；无映射仅日志提示“未注册设备:<mac>”。
+  - 最小联调脚本/页面：对指定设备下发三条示例载荷（文本、列表、横幅），并验证设备回 `ui.ack`。
+
+- 最小测试载荷（复制即用）
+  - 文本
+    ```json
+    { "type":"ui.render","id":"d1-001","page":"dialog.chat",
+      "header":{"title":"工牌001 · 文先生"},
+      "body":{"kind":"text","text":"Hello 渲染测试"},
+      "footer":{"hint":"后端→设备 OK"} }
+    ```
+  - 列表
+    ```json
+    { "type":"ui.render","id":"d1-002","page":"dialog.chat",
+      "header":{"title":"工牌001 · 文先生"},
+      "body":{"kind":"list","items":["第一行","第二行","第三行"]},
+      "footer":{"hint":"最多显示8行"} }
+    ```
+  - 顶部横幅
+    ```json
+    { "type":"device.control","id":"d1-003","action":"net.banner",
+      "text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
+    ```
+
+- 今日验收
+  - 设备：上电→欢迎→唤醒→“渲染测试页”。
+  - 三条载荷均被正确渲染/执行并回 `ui.ack`；解析异常回 `ui.error: INVALID_PAYLOAD`。
+  - 断连→重连后，后端补投“最后一次渲染”，设备恢复显示。
+
*** End Patch
PATCH
```

我先读取当前的 build.md 内容，确认章节结构与行号，再追加“Day 1 最小落地（最终版）”章节与最小测试载荷，确保与现有格式一致。随后会一次性写入更新。

已复查并补全 build.md 的“阶段1（Day 1 最小落地）”信息，确保与“渲染协议契约 v1”和你的最新要求一致：
- 新路径直接生效，不加任何运行时开关
- 仅实现 ui.render(text|list) 与 device.control(net.banner)
- 保留开机动画与欢迎页；唤醒后进入“渲染测试页（等待后端指令…）”
- 新建独立 EinkRenderEngine（最小接口与数据结构已列出）
- application.cc 只保留两类分支，含 ACK/错误回报
- 后端轻量 sender/cache/补投与设备映射注入标题
- 最小测试载荷三条已提供

可以按该文档直接开工。

---

**User**

现在硬件方面已经开发和升级到了最新固件，且握手已带 device-id（后端日志已显示 94:a9:90:07:9d:88）。问题仅在后端当前不支持这两类消息的转发；按以上热修+带 to 发送，即可打通“能连、能收指令、能渲染、能回 ACK”。

请给我详细的查看之前的协作计划 参考硬件已新增部分@log.md  对后端任务进行安排 现在还是处于阶段1

---

**Cursor**

### 阶段1（后端）执行安排（结合已完成硬件与握手 device-id）

- 核心目标
  - 支持从任意已连接客户端向指定设备转发两类消息：`ui.render` 与 `device.control`（携带 `to:["<device-id>"]`）。
  - 设备上线时补投“最后一次渲染”快照。
  - 渲染内容仅注入“工牌{badge} · {owner}”，未注册设备不显示标识，只打日志。

- 必做改动（按文件）
  - backend/core/websocket_server.py
    - 注册路由：保证 `register_device_handler(device_id, conn)`、`get_device_handler(device_id)`、`unregister...` 可用。
    - 发送工具：新增 `async def send_to_device(device_id, payload: dict|str) -> bool`（dict 自动 json.dumps）。
    - 上线补投：在设备注册成功后读取 `last_render_cache.get(device_id)`，存在则直接 `send_to_device(...)`。
  - backend/core/utils/last_render_cache.py
    - 内存缓存：`set_last(device_id, payload)`、`get_last(device_id)`（简单 dict，TTL 可暂不做）。
  - backend/core/orchestration/render_schema.py
    - 轻量校验/清洗：校验 `type/page/header/body/footer/id`（仅支持 body.kind: text|list；忽略其余字段）。
  - backend/core/orchestration/render_sender.py
    - `async def send_render(conn_or_device_id, payload)`：每设备≤2 QPS 限频，清洗后发送；成功则 `last_render_cache.set_last(...)`。
    - `async def send_control(conn_or_device_id, action="net.banner", **kw)`：构造 `device.control` 并发送。
  - backend/core/connection.py（或 textHandle.py 的统一入口）
    - 转发热修：当收到消息 `type in {"ui.render","device.control"}` 且包含 `to: [ids...]`：
      - 标准化 ids（小写、去空白）；对每个在线 id：调用 `server.send_to_device(id, cleaned_payload)`，清除 `to` 字段后转发；
      - 不在线仅日志（阶段1不做离线队列）；不汇总回执（只记录日志）。
    - ACK 透传：收到设备上行 `{type:"ui.ack"| "ui.error"}` 时记录日志（阶段1不回送给发起方）。
  - backend/data/devices.yaml
    - 已有；在编排示例里读取 `badge/owner` 注入 `header.title`；未注册：日志“未注册设备:<mac>”，不在 UI 显示。

- 今日联调脚本/页面（任选其一）
  - test/demo_render.py（或 HTML）
    - 直连后端 WS，发送如下三条消息（都带 `to:["94:a9:90:07:9d:88"]`）：
      - 文本 ui.render、列表 ui.render、device.control: net.banner
    - 期望：后端日志显示“转发→已送达”，设备端回 `ui.ack`，后端记录 ACK。

- 示例载荷（直接发给后端，带 to）
```json
{ "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-001","page":"dialog.chat",
  "header":{"title":"工牌001 · 文先生"},
  "body":{"kind":"text","text":"Hello 渲染测试"},
  "footer":{"hint":"后端→设备 OK"} }
```
```json
{ "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-002","page":"dialog.chat",
  "header":{"title":"工牌001 · 文先生"},
  "body":{"kind":"list","items":["第一行","第二行","第三行"]},
  "footer":{"hint":"最多显示8行"} }
```
```json
{ "type":"device.control","to":["94:a9:90:07:9d:88"],"id":"d1-003","action":"net.banner",
  "text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
```

- 验收标准（阶段1）
  - 收到带 `to` 的两类消息，能正确转发到设备；设备渲染并回 `ui.ack`；后端日志记录 ACK。
  - 设备重连后，后端自动补投“最后一次渲染”，设备恢复显示。
  - 渲染标题仅显示“工牌{badge} · {owner}”；未注册设备不显示标识，后端日志提示。

- 任务分配与预估
  - w：websocket_server 发送工具/补投集成 + 连接转发热修（3h）；sender+cache（3h）。
  - d：schema 清洗与联调脚本（3h）；设备映射读取与注入（1h）。
  - 联调：与硬件对齐 3 条样例载荷与 ACK（1h）。

- 风险与对策
  - 后端未识别 `to`：添加转发分支只匹配 `ui.render/device.control`，其他类型不影响。
  - 限频生效导致丢帧：仅阶段1，丢弃计数写日志；必要时降低发送频率。

```json
{ "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-001","page":"dialog.chat",
  "header":{"title":"工牌001 · 文先生"},
  "body":{"kind":"text","text":"Hello 渲染测试"},
  "footer":{"hint":"后端→设备 OK"} }
```

```json
{ "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-002","page":"dialog.chat",
  "header":{"title":"工牌001 · 文先生"},
  "body":{"kind":"list","items":["第一行","第二行","第三行"]},
  "footer":{"hint":"最多显示8行"} }
```

```json
{ "type":"device.control","to":["94:a9:90:07:9d:88"],"id":"d1-003","action":"net.banner",
  "text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
```

---

**User**

我认可这个安排 但是请细化任务分配  测试和后端的工作请区分开

---

**Cursor**

### 阶段1 任务分配（后端 vs 测试分离）

- 后端（w）
  - 路由与发送
    - 新增 `send_to_device(device_id, payload)`：`backend/core/websocket_server.py`
    - 设备注册成功后读取 `last_render_cache.get(device_id)` 并补投
  - 消息转发（热修，不改协议）
    - 在统一入口（`backend/core/connection.py` 或 `handle/textHandle.py`）处理两类消息转发：
      - 当 `type in {"ui.render","device.control"}` 且携带 `to:[...]`
        - 标准化目标IDs（小写、去空格/引号）
        - 删除 `to` 字段后原样转发到每个在线设备（调用 `send_to_device`）
        - 不在线仅日志（阶段1不做离线队列），不回执给发起方
      - 透传设备上行 `{type:"ui.ack"|"ui.error"}` 到日志（阶段1不回送发起方）
  - 限频与缓存
    - `backend/core/utils/last_render_cache.py`：`set_last/get_last`（内存即可）
    - `backend/core/orchestration/render_schema.py`：轻量清洗（仅允许 body.kind: text|list；忽略未知字段）
    - `backend/core/orchestration/render_sender.py`：
      - `send_render(conn_or_device_id, payload)`：每设备≤2 QPS；发送前清洗；成功后 `set_last`
      - `send_control(conn_or_device_id, action="net.banner", **kw)`
  - 设备映射注入
    - 读取 `backend/data/devices.yaml` 将 `badge/owner` 注入 `header.title`（如“工牌001 · 文先生”）；未注册仅日志，不在 UI 显示任何设备标识
  - 交付验收
    - 能接收带 `to` 的两类消息并成功转发；设备渲染并回 `ui.ack`；上线补投“最后一次渲染”

- 测试（d）
  - 控制端脚本/页面（任选其一或两个）
    - `test/demo_render.py`（或 HTML）：直连后端 WS，向指定设备发送三条样例载荷（都带 `to`）
      - 文本渲染 ui.render（text）
      - 列表渲染 ui.render（list ≤8行）
      - 顶部横幅 device.control（net.banner, 3s）
    - 参数化：`--to 94:a9:90:07:9d:88`（默认取硬件部一台），可切换为 002/003
    - 从 `devices.yaml` 读取 `badge/owner` 自动拼接 `header.title`
  - 断连重连剧本
    - 主动断开设备网络→重连，脚本观察后端是否补投“最后一次渲染”，设备是否恢复显示
  - 日志断言
    - 脚本输出：发送时间/类型/目标、收到 `ui.ack` 的时延（目标≤3s）、失败时打印 `ui.error`
    - 后端日志检查：转发成功/目标离线/上线补投
  - 交付验收
    - 三条载荷均在设备侧正确显示并回 ACK；重连后成功补投

### 今日优先级与时间预估
- w（后端）：发送工具+补投（2h）；转发热修（3h）；限频与缓存/清洗（2h）；映射注入与日志（1h）；联调（2h）
- d（测试）：脚本/页面（3h）；参数化与 devices.yaml 读取（1h）；断连重连用例（1h）；日志断言与联调（2h）

### 样例载荷（测试侧直接发送，注意带 to）
- 文本
```json
{ "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-001","page":"dialog.chat",
  "header":{"title":"工牌001 · 文先生"},
  "body":{"kind":"text","text":"Hello 渲染测试"},
  "footer":{"hint":"后端→设备 OK"} }
```
- 列表
```json
{ "type":"ui.render","to":["94:a9:90:07:9:88"],"id":"d1-002","page":"dialog.chat",
  "header":{"title":"工牌001 · 文先生"},
  "body":{"kind":"list","items":["第一行","第二行","第三行"]},
  "footer":{"hint":"最多显示8行"} }
```
- 顶部横幅
```json
{ "type":"device.control","to":["94:a9:90:07:9d:88"],"id":"d1-003","action":"net.banner",
  "text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
```

### 验收口径（阶段1）
- 指令转发：后端能把带 `to` 的 `ui.render/device.control` 转给目标设备
- 设备回执：每条消息设备均回 `ui.ack`，P95 ≤3s
- 补投生效：设备重连后展示“最后一次渲染”
- UI 文案：仅显示“工牌{badge} · {owner}”，未注册设备不显示标识，仅后端日志提示

```json
{ "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-001","page":"dialog.chat",
  "header":{"title":"工牌001 · 文先生"},
  "body":{"kind":"text","text":"Hello 渲染测试"},
  "footer":{"hint":"后端→设备 OK"} }
```

```json
{ "type":"ui.render","to":["94:a9:90:07:9:88"],"id":"d1-002","page":"dialog.chat",
  "header":{"title":"工牌001 · 文先生"},
  "body":{"kind":"list","items":["第一行","第二行","第三行"]},
  "footer":{"hint":"最多显示8行"} }
```

```json
{ "type":"device.control","to":["94:a9:90:07:9d:88"],"id":"d1-003","action":"net.banner",
  "text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
```

---

**User**

很不错 注意之前w为了后端和硬件设备联调 已经优化过了之前的测试页面@simulated_work_badge_1.html ; 为了后续的测试稳定性,有没有必要让测试新写一套全新的页面来测试现在的这套逻辑? 还是直接服用之前的测试页面来进行继续开发? 

