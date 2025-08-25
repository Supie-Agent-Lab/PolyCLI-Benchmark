---

**Cursor**

### 结论
- 建议直接复用现有 `test/simulated_work_badge_1.html`，做“极小增强”。无需新写页面，避免分叉与维护成本。

### 为什么复用更好
- 页面已稳定：内置连接、日志/错误处理、原始 JSON 发送、在线列表等基础设施齐全。
- 只缺“to”转发入口：当前渲染测试区已能发 `ui.render/device.control`，稍加一个“目标ID(to)”输入即可满足现阶段需求。

### 测试页极小增强（建议）
- UI 增加：在“渲染引擎测试 (ui.render / device.control)”区域加一个输入框
  - 字段：目标设备ID（to），默认填硬件 MAC（如 `94:a9:90:07:9d:88`）
- 发送逻辑调整：
  - `send_ui_render`/`send_net_banner`/`send_raw_json`：若“目标ID”非空，则注入 `to:[<canonical id>]` 后再发送
  - 规范化 `to`：小写、去空格（保持与后端一致）
- 快捷体验（可选）：
  - 在线列表点击写入“目标ID”输入框
  - 预置 hardware 部三台的快捷按钮（仅写入输入框，不改逻辑）

### 验收
- 从测试页发送三条消息（text、list、net.banner），带 `to` 为硬件 MAC：
  - 后端日志显示“转发→送达”，设备渲染成功，设备回 `ui.ack`
- 断连→重连：后端补投“最后一次渲染”，设备恢复显示

### 注意
- 统一 `device-id` 格式（小写 MAC，冒号分隔）
- 控制发送速率（每设备≤2 QPS），避免被限频丢帧
- “未注册设备”只打后端日志，UI不显示设备标识

---

**User**

很好,基于复用现有页面的逻辑,进一步优化测试的安排

---

**Cursor**

### 结论
- 直接复用 `test/simulated_work_badge_1.html`，不新建页面。
- 测试优先用“Raw JSON”带 `to:["<device-id>"]` 发送；待后续极小增强（在“渲染引擎测试”面板加“目标ID”输入并注入 `to`）后，再用按钮发送。

### 测试前置
- 确认硬件已上线且握手日志含 `device-id`（如 `94:a9:90:07:9d:88`）。
- 确认 `backend/data/devices.yaml` 映射正确（仅显示“工牌{badge} · {owner}”，不显示 MAC）。
- 后端已支持两类消息的“带 to 转发”与“上线补投 last_render_cache”（在转发 `ui.render` 时也要 `set_last(deviceId, payload_without_to)`）。

### 用例集（按优先级）
- 1) 基础连通
  - 操作：硬件与测试页分别连接；测试页收到 hello；后端日志出现在线设备。
  - 预期：连接稳定，无异常日志。
- 2) 文本渲染（ui.render:text）
  - 发送（Raw JSON）：
  ```json
  { "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-001","page":"dialog.chat",
    "header":{"title":"工牌001 · 文先生"},
    "body":{"kind":"text","text":"Hello 渲染测试"},
    "footer":{"hint":"后端→设备 OK"} }
  ```
  - 预期：设备≤3s渲染成功并回 `{type:"ui.ack",id:"d1-001"}`；后端日志记录ACK。
- 3) 列表渲染（ui.render:list）
  - 发送（Raw JSON，行数>8用于截断验证）：
  ```json
  { "type":"ui.render","to":["94:a9:90:07:9:88"],"id":"d1-002","page":"dialog.chat",
    "header":{"title":"工牌001 · 文先生"},
    "body":{"kind":"list","items":["1","2","3","4","5","6","7","8","9","10"]},
    "footer":{"hint":"最多显示8行"} }
  ```
  - 预期：设备仅显示前8行并回ACK。
- 4) 顶部横幅（device.control:net.banner）
  - 发送：
  ```json
  { "type":"device.control","to":["94:a9:90:07:9d:88"],"id":"d1-003","action":"net.banner",
    "text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
  ```
  - 预期：设备顶部显示约3秒并回ACK。
- 5) 限频与稳态（建议）
  - 操作：在1秒内快速连发3条 `ui.render:text`。
  - 预期：遵守“每设备≤2 QPS”；超过的请求可能被丢弃或延后（以后端日志为准）；正常路径仍回ACK。
- 6) 断连→重连补投
  - 操作：成功渲染后断开硬件网络后再重连。
  - 预期：后端自动补投“最后一次渲染”，设备恢复显示；如未生效，检查转发路径是否已 `set_last(...)`。
- 7) 未注册设备/离线目标（健壮性）
  - 操作：向不存在或未注册 `device-id` 发送。
  - 预期：后端日志显示“目标不在线/未注册设备”，无错误抛出；无设备渲染/ACK。
- 8) 解析错误（负向）
  - 发送（缺少必需字段）：
  ```json
  { "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"bad-001","page":"dialog.chat",
    "body":{"kind":"text"} }
  ```
  - 预期：设备回 `{type:"ui.error",id:"bad-001",code:"INVALID_PAYLOAD"}`；后端日志可见。

### 执行节奏与分工
- 测试（d）
  - 使用“Raw JSON”发送上述三条核心载荷（text/list/banner）；记录发送时间与ACK时间（P95≤3s）。
  - 断连重连剧本；未注册/离线/解析错误用例。
  - 可选：把“在线设备列表点击→写入目标ID输入框”的逻辑用于 Raw JSON 目标填充。
- 后端（w）
  - 确认两类消息的“带 to 转发”已实现，且 `ui.render` 转发路径同步 `last_render_cache.set_last(...)`。
  - 上线补投在 `register_device_handler` 后调用；日志包含“转发/ACK/补投”关键行。

### 注意
- 统一 `device-id` 小写、冒号分隔；严格控制发送频率（≤2 QPS）。
- UI 文案只显示“工牌+持有人”，从 `devices.yaml` 注入；未注册设备不显示标识，仅日志提示。

```json
  { "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-001","page":"dialog.chat",
    "header":{"title":"工牌001 · 文先生"},
    "body":{"kind":"text","text":"Hello 渲染测试"},
    "footer":{"hint":"后端→设备 OK"} }
```

```json
  { "type":"ui.render","to":["94:a9:90:07:9:88"],"id":"d1-002","page":"dialog.chat",
    "header":{"title":"工牌001 · 文先生"},
    "body":{"kind":"list","items":["1","2","3","4","5","6","7","8","9","10"]},
    "footer":{"hint":"最多显示8行"} }
```

```json
  { "type":"device.control","to":["94:a9:90:07:9d:88"],"id":"d1-003","action":"net.banner",
    "text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
```

```json
  { "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"bad-001","page":"dialog.chat",
    "body":{"kind":"text"} }
```

---

**User**

我希望测试页面实现硬件的感觉,这样会更加直观,就是把测试页面当成是一个网页版的硬件,去对接后端的所有逻辑,而且能清晰的测试全流程,看到所有日志情况;

---

**Cursor**

### 结论
- 直接复用 `test/simulated_work_badge_1.html`，把它当“网页版硬件”。只做极小增强：自动渲染 `ui.render`、响应 `device.control`、自动回 ACK、全链路可视日志。

### 页面极小增强（像硬件一样工作）
- 渲染引擎（JS 版）
  - 处理 `type=="ui.render"`：解析 `header.title/body(kind=text|list)/footer.hint/icons{net,rec,battery}`，更新“E‑Ink渲染屏”（新增一个 header/body/footer 三栏区域）。
  - 自动 ACK：若带 `id`，渲染完成后发 `{type:"ui.ack", id, status:"ok"}`。
- 控制指令
  - 处理 `type=="device.control"`：
    - `net.banner`：顶部浮条显示 `text`（默认3s），完毕回 ACK（若带 id）。
    - `listen.start/stop`：切换 header 的录制红点（REC），并回 ACK（不做音频）。
- 日志与指标
  - 方向化日志：`[RX][ui.render] id=...`、`[ACK] id=... ms=...`、`[ERR] code=...`。
  - 统计：显示本会话 ACK 次数、P95 时延（简单计算）、最近一次补投命中时间。

### 推荐测试流程（阶段1）
- A. 启动
  - 用页面连接后端，`device-id` 填硬件 MAC（小写冒号分隔）。
  - 预期：后端日志出现该设备在线；若有 last_render，页面收到并渲染。
- B. 文本/列表渲染
  - 由“控制端”（可用脚本/另一个页面/后端调试接口）发送带 `to:["<mac>"]` 的 `ui.render:text|list` 三条样例；期望页面渲染并 ACK≤3s。
- C. 横幅与状态
  - 发送 `device.control: net.banner`；浮条显示≈3s；回 ACK。
  - 发送 `device.control: listen.start/stop`；页面 header 的 REC 点亮/熄灭；回 ACK。
- D. 限频与稳态
  - 1 秒内快速发 3 条 `ui.render`，观察页面仅按顺序渲染，后端可能丢弃超限且记录丢弃日志。
- E. 断连→重连补投
  - 手动断开页面→重连；后端自动补投“最后一次渲染”，页面恢复显示并记录“补投成功”。

### 分工与时间
- 测试（d）2–3h
  - 在现有页面加“E‑Ink渲染屏”容器与渲染/控制处理；实现自动 ACK；完善方向化日志与 ACK 时延统计。
  - 提供一键“自测”按钮：本页自发 `to:[自身 device-id]` 的三条样例（text/list/banner）压通后端转发回本页（回环验证）。
- 后端（w）2–3h
  - 确认“带 to 转发”与“last_render_cache 补投”已启用；`ui.render` 转发成功后 `set_last(deviceId, payload_without_to)`。
  - 日志关键行：`[FORWARD] ...`、`[ACK_RX] id=... ms=...`、`[REDELIVER] last_render sent`。
- 硬件（p）0h（阶段1不参与），仅保持真实设备在线以便对照（可选）。

### 样例载荷（控制端发送，带 to）
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
  "body":{"kind":"list","items":["第一行","第二行","第三行","4","5","6","7","8","9","10"]},
  "footer":{"hint":"最多显示8行"} }
```
- 横幅
```json
{ "type":"device.control","to":["94:a9:90:07:9d:88"],"id":"d1-003","action":"net.banner",
  "text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
```

### 风险与对策
- 发送端与设备同页回环：允许，用于本地压测；若担忧回环干扰，可在页面提供“自测开关”。
- UI 兼容：`ui.render` 未带 icons/页脚时，按缺省渲染；异常负载回 `ui.error: INVALID_PAYLOAD` 并在日志显示。

```json
{ "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-001","page":"dialog.chat",
  "header":{"title":"工牌001 · 文先生"},
  "body":{"kind":"text","text":"Hello 渲染测试"},
  "footer":{"hint":"后端→设备 OK"} }
```

```json
{ "type":"ui.render","to":["94:a9:90:07:9:88"],"id":"d1-002","page":"dialog.chat",
  "header":{"title":"工牌001 · 文先生"},
  "body":{"kind":"list","items":["第一行","第二行","第三行","4","5","6","7","8","9","10"]},
  "footer":{"hint":"最多显示8行"} }
```

```json
{ "type":"device.control","to":["94:a9:90:07:9d:88"],"id":"d1-003","action":"net.banner",
  "text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
```

---

**User**

刚刚连调时,出现了硬件无限重启的bug,我认为后端问题非常大,正如我们设计原则里所说,后端负责处理所有的逻辑和任务编排,而硬件只负责接受和执行后端发送的任务,所以说后端不能发送任何导致硬件出故障的信息或者说非法信息, 请仔细参考全流程编排, 努力思考现在后端架构应该怎么更新和适配硬件侧,我认为后端应该要知道每一台设备处于什么模式,只能发送什么信息才正确; 不需要修改代码 和我认真讨论和总结

---

**Cursor**

### 结论
- 后端必须“强约束+白名单化”对每台设备的编排，按设备所处模式只发送该模式允许、且经过严密校验和限幅的指令。默认失败关闭（fail-closed）：任何不确定、超限或未通过校验的消息一律不发或降级为空操作，避免再次触发硬件异常。
- 阶段1先把“测试/欢迎路径”做安全编排闭环：只允许 `ui.render(text|list)` 和 `device.control(net.banner)` 两种类型，其他一律丢弃并记录日志；严格 ACK 驱动和补投，保障“能连、能收指令、能渲染、能回 ACK”。

### 参考全流程后的后端适配要点（不改代码，仅结论与安排）
- 核心原则
  - 单一事实源（Single Source of Truth）：后端为每台设备维护“会话状态+模式”，以此决策“能发什么/何时发/是否重试”。硬件不自判模式。
  - 白名单发送（Positive Gating）：只发“当前模式允许”的消息，严格模式-指令矩阵；不在白名单内的指令一律不发。
  - 消息净化（Sanitize）：上游请求与编排结果都要做 Schema 校验+长度限幅+字段裁剪（文本长度、列表项数、icons 枚举）。
  - ACK 驱动（Ack-Driven）：每次发送带 id；收到 `ui.ack` 才进入下一步；未 ACK 触发指数退避重试；重试上限后“冻结该设备 30s”并报警。
  - 失败关闭（Fail-Closed）：任何异常（校验失败、超限、未知字段、异常模式）→ 不发、打日志；绝不“猜测性补全”下发。
  - 节流与背压：每设备渲染 ≤2 QPS；队列有界（丢最旧，计数告警）；设备上线只补投“最后一次渲染”。

- 设备状态模型（后端内存即可，持久化可后续）
  - 基本字段：`deviceId, badge, owner, group, currentMode(in: boot|welcome|testing|dialog|meeting|working|coding), lastRenderId, lastAckTs, errorCounters, lastRenderSnapshot`
  - 能力标签（可选）：`supports_banner, supports_logs, supports_list`（阶段1默认 true，仅用于日志与风险标记）

- 模式-指令白名单矩阵（阶段1必须执行）
  - boot/welcome：只允许 `ui.render(text|list)`（欢迎/提示），禁止所有 `device.control`（除 `net.banner`）
  - testing（渲染测试页）：允许 `ui.render(text|list)`、`device.control(net.banner)`；禁止 `listen.* / tts / 其他`
  - 未进入会议/编码/工作模式前：禁止 `meeting.* / coding.* / workflow.* / tts / listen.*`
  - 任何未知 `type` 或未知 `action`：直接丢弃，日志 `[DROP_UNKNOWN]`
  - 任何未通过 schema 或超限：`[DROP_INVALID]`，不发

- 安全渲染构建器（在编排层统一“出厂前净化”）
  - `header.title`：注入“工牌{badge} · {owner}”（未注册仅日志，不显示任何设备标识）
  - `body.text`：剪裁到 N 字符（UTF‑8 安全，阶段1建议 ≤ 200）
  - `body.items`：≤8 项，每项 ≤ 50 字符
  - `icons.net/rec/battery`：只接受枚举/范围，异常丢弃该字段
  - `footer.hint`：≤ 50 字符
  - 输出只包含协议契约列出的字段（多余字段剔除）

- 严格 ACK 流程
  - 发送时分配 `id`，写入“待确认表”；收到设备 `ui.ack(id)` 才清除
  - 超时（例如 3s）未 ACK：重试一次；仍失败→冻结该设备 30s（期间仅允许 `net.banner` 和“恢复欢迎页”）
  - 多次失败触发设备级熔断（circuit breaker），保障不再向硬件倾倒消息

- 上线补投（无害化）
  - 仅补投“最后一次渲染”快照（已经过净化、且是白名单内的类型）
  - 补投也走 ACK，失败就停（不连环重试）

- 日志与可观测
  - 每条指令发送与 ACK 都要打印方向化日志：`[SEND] type=id=.. to=.. mode=..`、`[ACK] id=.. ms=..`、`[DROP_INVALID] code=.. reason=..`、`[FREEZE] device=.. seconds=30`
  - 统计每设备：发送次数、ACK 时延 P95、丢弃原因计数、冻结次数

### 分阶段落地（仍处阶段1，只做最小闭环）
- 立即执行（不改协议，不引入新页面）
  - 设备状态登记：连接成功即 `mode=welcome`；唤醒后端显式切 `mode=testing`（或测试页按钮触发）；只有 `testing` 才允许两个指令
  - 在“转发入口”上加白名单矩阵与净化：对 `ui.render/device.control` 进行模式校验→不合法 DROP；合法→净化→发送
  - 对 `ui.render` 转发成功即更新 `lastRenderCache`（用于上线补投）
  - 开启 ACK 驱动与重试/冻结（可先日志模拟，随后启用 1 次重试 + 冻结）
- 验收口径（本阶段）
  - 测试页或脚本向目标设备发带 `to` 的三条消息（text/list/banner）→ 设备渲染并回 ACK；后端统计 ACK 时延≤3s
  - 发送任意“非白名单”的消息（如 listen.start/tts/meeting.*）：后端日志 `[DROP_BY_MODE]`，硬件不再收到异常指令
  - 断连重连：仅补投“最后一次渲染”，设备稳定恢复；无环状重发

### 未来阶段（对齐全流程演示）
- 扩展模式矩阵：meeting/coding/working 引入相应的允许指令（例如 meeting.listen 时才允许 `listen.start/stop` 等），并按相位推进
- 引入“设备能力探测/宣告”：设备 hello 时携带功能位（如是否支持 `logs`、字体/分辨率），后端对小屏/大屏差异做模板适配
- 单元/契约测试：用“网页版硬件”页面跑全流程契约测试（每条指令→渲染快照→ACK→统计）

### 总结
- 问题根因是“后端未做严格模式白名单与净化，向硬件发出了不安全/越界的指令”。解决之道是把“编排安全”前置为硬约束：每台设备的“模式-指令白名单+Schema+限幅+ACK驱动+失败关闭+补投最小化”，并以日志与统计可视化全链路。这样硬件只需执行指令，不再因后端越界消息而进入异常路径，达成“后端负全责、硬件最简化”的目标。

---

**User**

是的 我认为这次讨论的内容非常非常重要,请写入bulid.md里 明确后端的核心原则,然后给出后端清晰详细的任务,现在就指派和修复这个问题

---

**Cursor**

```markdown
# 项目架构

# 目标
- 覆盖对话/会议/工作/编码四类页面的端到端演示；并发≥10；≥3台互动；离线补投“最后渲染”；内网部署 + API Token。

——

## 0. 渲染协议契约（完整规范 v1）

- 通用
  - 传输：WebSocket JSON 文本帧
  - `type`: `ui.render | device.control | ui.ack | ui.error`
  - `id?`: 渲染或控制指令的业务ID（用于幂等/ACK 关联），字符串
  - `ts?`: 服务器毫秒时间戳（整数）
  - 字段未识别时必须忽略（向前兼容），非法类型按错误处理

- 下行：`ui.render`（页面渲染指令）
  - `page`: string（页面标识，枚举）
    - `welcome | dialog.chat | meeting.listen | meeting.summary | working.list | working.detail | working.assign | working.end | coding.listen | coding.tasks_confirm | coding.log | coding.end`
  - `header?`: 对象
    - `title`: string（建议≤16个全角字符，超出设备端截断）
    - `icons?`: 对象 `{ net?: "ok|bad|off", rec?: boolean, battery?: 0..100 }`
  - `body?`: 变体对象（五选一）
    - `{ kind: "list", items: string[] }`（每页建议≤8项）
    - `{ kind: "bullets", items: string[] }`（建议≤6条）
    - `{ kind: "text", text: string }`（自动按宽度换行/截断）
    - `{ kind: "logs", lines: string[] }`（滚动窗口建议≤8行）
    - `{ kind: "kv", items: [{k:string, v:string}] }`（详情/诊断用）
  - `footer?`: 对象 `{ hint?: string, page?: { index: int>=1, total: int>=1 } }`
  - `regionsChanged?`: string[]（`header|body|footer`，用于最小重绘提示。设备可忽略并整屏节流）
  - 设备行为：
    - 收到后应尽快渲染（≥500ms 内允许合并节流）
    - 若含 `id`，渲染完成后发送 `ui.ack`
    - 文本超长需安全截断（UTF‑8）并可追加省略号

- 下行：`device.control`（设备控制指令）
  - `action`: 枚举
    - 录音边界：`listen.start | listen.stop`
    - 提示：`play.tone`（`name` 必填）、`tts`（`text` 必填）
    - 导航：`page.next | page.prev`
    - 网络横幅：`net.banner`（`text`, `level: info|warn|error`, `duration_ms?`）
  - 其它字段：`name?`、`text?`、`duration_ms?`
  - 设备行为：
    - 指令应尽快执行；失败回 `ui.error`
    - 若含 `id`，执行完成后发送 `ui.ack`

- 上行：`ui.ack`（确认）
  - `{ type: "ui.ack", id: string, status: "ok" }`
  - 发送时机：完成渲染/控制动作后 ≤5s；重复 `id` 应幂等（忽略二次发送）

- 上行：`ui.error`（错误）
  - 结构：`{ type: "ui.error", id?: string, code: string, message?: string }`
  - `code` 枚举：
    - `INVALID_PAYLOAD`（字段缺失/类型错误）
    - `RATE_LIMITED`（达到限频或队列上限）
    - `BUSY`（设备忙，暂不可渲染/控制）
    - `UNSUPPORTED_PAGE`、`UNSUPPORTED_BODY_KIND`
    - `DISPLAY_FAILURE`、`AUDIO_FAILURE`
    - `INTERNAL_ERROR`

- 限频与补投（强约束）
  - 渲染：每设备 ≤2 QPS；超限时丢弃队首旧帧并保留最新（后端可重新下发）
  - 控制：每设备 ≤5 QPS（建议）；设备可合并短时间重复指令
  - 离线补投：仅补投“最后一次渲染”，在设备注册成功或 `hello` 后自动发送

- 兼容性与约束
  - 字符串统一 UTF‑8；`battery` 取值 0..100；未知 `net` 值按 `bad` 渲染
  - 设备应忽略未知字段与未知 `page/body.kind/action`（并可上报 `ui.error`）
  - 排序/并发：同一设备按到达顺序处理；若 `device.control` 与 `ui.render` 并发到达，设备可先执行 `device.control`

示例：welcome
```json
{ "type":"ui.render", "page":"welcome", "header":{ "title":"欢迎" }, "body":{ "kind":"text", "text":"正在连接…" }, "footer":{ "hint":"成功连接后将进入对话" }, "regionsChanged":["header","body"], "id":"wel-001" }
```

示例：dialog.chat（文本提示）
```json
{ "type":"ui.render", "page":"dialog.chat", "header":{ "title":"对话" }, "body":{ "kind":"text", "text":"请说出您的问题…" }, "footer":{ "hint":"说“进入会议模式”可切换" }, "regionsChanged":["body"], "id":"dlg-001" }
```

示例：meeting.listen（进入会议）
```json
{ "type":"ui.render", "page":"meeting.listen", "header":{ "title":"会议模式", "icons":{ "net":"ok", "rec":true, "battery":82 } }, "body":{ "kind":"list", "items":["已连接后端","请开始发言…"] }, "footer":{ "hint":"双击结束并生成纪要", "page":{ "index":1, "total":1 } }, "regionsChanged":["header","body"], "id":"meet-001" }
```

示例：meeting.summary（要点）
```json
{ "type":"ui.render", "page":"meeting.summary", "header":{ "title":"会议纪要" }, "body":{ "kind":"bullets", "items":["目标确认：本周完成登录联调","风险：外部依赖进度不稳","行动：A负责接口联调，B补充用例"] }, "footer":{ "hint":"长按3秒重新进入会议" }, "regionsChanged":["body"], "id":"meet-sum-001" }
```

示例：working.list（分页）
```json
{ "type":"ui.render", "page":"working.list", "header":{ "title":"工作模式" }, "body":{ "kind":"list", "items":["[P0] 修复登录","[P1] 优化列表","[P2] 编写用例","[P3] 文档整理"] }, "footer":{ "hint":"短按翻页", "page":{ "index":1, "total":2 } }, "regionsChanged":["body","footer"], "id":"work-001" }
```

示例：coding.log（滚动）
```json
{ "type":"ui.render", "page":"coding.log", "header":{ "title":"编码模式" }, "body":{ "kind":"logs", "lines":["build: 拉起构建","test: 单测通过","deploy: 部署完成"] }, "footer":{ "hint":"phase: build" }, "regionsChanged":["body"], "id":"code-001" }
```

示例：device.control（开始/停止录音、提示与横幅）
```json
{ "type":"device.control", "id":"ctl-001", "action":"listen.start" }
{ "type":"device.control", "id":"ctl-002", "action":"listen.stop" }
{ "type":"device.control", "id":"ctl-003", "action":"play.tone", "name":"meeting_enter" }
{ "type":"device.control", "id":"ctl-004", "action":"tts", "text":"已进入会议模式" }
{ "type":"device.control", "id":"ctl-005", "action":"net.banner", "text":"网络中断，重连中…", "level":"warn", "duration_ms":3000 }
```

示例：ACK 与 错误
```json
{ "type":"ui.ack", "id":"meet-001", "status":"ok" }
{ "type":"ui.error", "id":"meet-001", "code":"RATE_LIMITED", "message":"render qps exceeded" }
```

## 1. 阶段1

- 方案：保留开机动画与欢迎页；唤醒后进入“渲染测试页（等待后端指令…）”；一步到位新建独立 `EinkRenderEngine`，先实现“能连、能收指令、能渲染、能回 ACK”，后续在同一引擎内迭代增强。

### 实施原则
- 不加额外复杂度：只支持最小协议子集（`ui.render: text|list`、`device.control: net.banner`）。
- 不要运行时开关：新路径直接生效。
- 不显示 MAC：仅显示“工牌编号 + 持有人”；未注册设备仅后端日志提示，不上屏。

### 硬件
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

### 后端
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

——

## 2. 后端核心原则（Fail-Closed 安全编排，必须执行）

- 单一事实源（Session/Device State）
  - 后端为每台设备维护：`deviceId, badge, owner, group, currentMode(in: boot|welcome|testing|dialog|meeting|working|coding), lastRenderId, lastAckTs, errorCounters, lastRenderSnapshot`。
  - 硬件不自判模式；所有可发内容由后端依据该状态决策。

- 白名单矩阵（按模式只发允许的指令）
  - 阶段1：`welcome/testing` 仅允许 `ui.render(text|list)` 与 `device.control(net.banner)`；其余一律丢弃并记日志 `[DROP_BY_MODE]`。
  - 未进入 `meeting/working/coding` 前，禁止任何 `meeting.* / workflow.* / coding.* / tts / listen.*`。

- 消息净化（Sanitize）
  - 渲染输出统一走净化：
    - `header.title` 注入“工牌{badge} · {owner}”；未注册设备仅日志提示，不在 UI 显示任何设备标识。
    - `body.text` 截断（UTF‑8 安全，建议 ≤200 字）；`body.items` ≤8 项，每项 ≤50 字；未知字段剔除。
    - `icons.net/rec/battery` 仅接受枚举/范围；异常丢弃该字段。

- ACK 驱动与重试/冻结
  - 每次发送带 `id` → 进入待确认表；收到 `ui.ack(id)` 后清除。
  - 超时（建议 3s）未 ACK：重试 1 次；再失败 → 冻结该设备 30s，仅允许 `net.banner` 或欢迎页提示。
  - 失败关闭（fail-closed）：任何未知/越权/超限/校验失败消息一律不发。

- 限频与背压
  - 每设备渲染 ≤2 QPS；队列有界（丢弃最旧，计数告警）。
  - 上线补投仅发送“最后一次渲染”快照（已净化、白名单内）。

- 可观测与审计
  - 方向化日志：`[SEND] type=id=.. to=.. mode=..`、`[ACK] id=.. ms=..`、`[DROP_INVALID]`、`[DROP_BY_MODE]`、`[FREEZE] device=.. seconds=30`、`[REDELIVER] last_render sent`。
  - 指标：每设备发送次数、ACK 时延 P95、丢弃原因计数、冻结次数。

——

## 3. 阶段1 后端任务与指派（立即修复）

- 路由与发送（w）
  - `backend/core/websocket_server.py`
    - 新增 `async def send_to_device(device_id, payload: dict|str) -> bool`（dict 自动 JSON 序列化）。
    - 设备注册成功后：读取 `last_render_cache.get(device_id)` → 如存在直接补投（日志 `[REDELIVER]`）。

- 消息转发与白名单（w）
  - 统一入口（`backend/core/connection.py` 或 `handle/textHandle.py`）：
    - 对 `type in {"ui.render","device.control"}` 且含 `to:[...]` 的消息：
      - 目标 IDs 标准化（小写、去空白/引号）。
      - 基于设备 `currentMode` 执行白名单校验（阶段1 仅允许 text|list 与 net.banner）。
      - 通过校验 → 调净化构建器生成安全载荷（删除 `to`），调用 `send_to_device`。
      - 不通过 → 丢弃并日志 `[DROP_BY_MODE]`；不回发起方回执（阶段1）。
    - 设备上行 `{type:"ui.ack"|"ui.error"}`：记录日志与耗时（阶段1 不回发起方）。

- 净化与限频（w）
  - `backend/core/orchestration/render_schema.py`：轻量校验/清洗，仅允许 `body.kind in {text,list}`，执行截断/裁剪/剔除未知字段。
  - `backend/core/orchestration/render_sender.py`：
    - `send_render(conn_or_device_id, payload)`：每设备 ≤2 QPS，发送前清洗；成功后 `last_render_cache.set_last(device_id, payload_without_to)`。
    - `send_control(conn_or_device_id, action="net.banner", **kw)`：构造安全 `device.control` 并发送。

- 渲染快照缓存（w）
  - `backend/core/utils/last_render_cache.py`：`set_last/get_last`（内存实现即可，线程安全可用简单锁）。

- 设备映射注入（w）
  - 读取 `backend/data/devices.yaml` 注入 `badge/owner` 至 `header.title`；未注册设备仅日志，不在 UI 显示任何设备标识。

- 测试与验收（d）
  - 复用 `test/simulated_work_badge_1.html` 作为“网页版硬件”：
    - 自动处理 `ui.render(text|list)`、`device.control(net.banner)` 并回 `ui.ack`（若带 `id`）。
    - 方向化日志与 ACK 时延统计（展示 P95）。
  - 控制端（本页 Raw JSON 或脚本）向目标设备发送三条样例（均带 `to`）：text/list/banner。
  - 用例：限频（1s 内 3 条）、断连→重连补投、未注册/离线目标、解析错误（应见 `ui.error`）。

- 今日验收口径
  - 带 `to` 的 `ui.render/device.control` 正确转发并渲染；设备 `ui.ack` P95 ≤3s。
  - 非白名单消息被后端丢弃（`[DROP_BY_MODE]`），硬件不再收到异常指令。
  - 断连重连仅补投“最后一次渲染”，设备稳定恢复显示。


```

已将本次“后端核心原则（Fail-Closed 安全编排）”与“阶段1 后端任务与指派（立即修复）”写入 `collaboration/build.md`，明确：
- 后端必须维护设备会话/模式状态，按白名单矩阵只发允许的消息
- 统一净化渲染输出（标题注入工牌/持有人、文本/列表限幅、剔除未知字段）
- ACK 驱动 + 超时重试 + 设备冻结（失败关闭）
- 每设备≤2 QPS、队列有界、上线仅补投最后一帧
- 路由/发送、白名单转发、净化与限频、渲染缓存、映射注入的具体负责人与文件落点
- 测试职责独立（复用 `test/simulated_work_badge_1.html` 作为“网页版硬件”）、用例与验收口径

可以据此开始阶段1修复与联调。

---

**User**

# 代码参考
硬件部分代码是hardware 
后端部分代码是backend 
测试部分代码是test 

# 任务总纲
项目索引请参考index.md @index.md 
项目日志请参考log.md @log.md 

# 任务
现在后端 硬件端 测试端都分别进行了开发和更新,请仔细验收,看看目前进度和状态;
目前实测,通过html测试页面和后端,能让硬件刷新页面了;
请和我讨论现在处在阶段1的什么位置? 后面应该怎么安排?

---

**Cursor**

### 阶段1当前状态（结论）
- 已打通链路：HTML 测试页 → 后端 → 硬件，硬件可按 `ui.render(text|list)` 刷新页面。
- 握手含 `device-id`，后端可路由到指定设备；设备映射 `devices.yaml` 生效（仅显示“工牌+持有人”）。
- 渲染协议 v1 已固化；后端“直达转发+白名单（text|list / net.banner）+清洗/限幅”已规划并部分落地（详见 `build.md` 与 `log.md`）。

### 与阶段1目标对照（完成/待办）
- 已完成
  - “能连、能收指令、能渲染”验证通过
  - 设备仅处理 `ui.render(text|list)` 与 `device.control(net.banner)`，其余忽略
  - 测试页可作为“网页版硬件”观测收发日志
- 待完成（本阶段收尾必做）
  - 后端严格白名单落地到“转发入口”（只放行 text|list / net.banner，其余 `[DROP_BY_MODE]`）
  - 输出净化（标题注入工牌/持有人；文本/列表限幅；剔除未知字段）在所有下发路径生效
  - ACK 驱动：发送带 id → 记录待确认 → 超时3s重试1次 → 仍失败冻结设备30s，仅允许横幅
  - 限频与队列：每设备≤2 QPS；队列有界（丢最旧并记数）；上线补投策略与日志与 `build.md` 保持一致（阶段1建议不自动补投，由编排端显式下发）
  - 方向化日志：SEND/ACK/DROP/FREEZE 统一格式，便于测试页核对

### 下一步安排（阶段1收尾）
- 后端（w）
  - 完成“转发入口”白名单与净化、ACK 跟踪与冻结、限频与丢弃计数、统一日志
  - `render_sender` 发送成功后仅更新 last_render（用于可选补投/回显）
- 测试（d）
  - 在 `simulated_work_badge_1.html` 启用“自动 ACK”与“渲染屏”联动（已能渲染/ACK则记录 P95 时延）
  - 用例回归：text/list/banner、1秒3条压测（观测限频丢弃）、断连重连、未注册/离线路由、解析错误（`ui.error`）
- 硬件（p）
  - 继续只处理两类消息并回 ACK；长文/超行安全截断；确认无重启/死锁

### 阶段1验收口径（达成即切阶段2）
- 指令转发：带 `to` 的 `ui.render/device.control` 均能送达目标设备并回 ACK（P95≤3s）
- 安全：非白名单消息后端丢弃，硬件不再收到越权限令
- 稳定：限频与丢弃计数生效；断连重连流程稳定（是否补投按约定）

### 阶段2预告（不立即执行，仅对齐方向）
- 模式状态机落地：后端按设备 `currentMode` 扩白名单（meeting/coding/working 各自允许集）
- 页面能力扩展：`working.list` 分页（8/页）、`coding.log` 滚动窗口；仍走同一渲染引擎
- 可观测：ACK 耗时/丢弃/冻结指标暴露；只读状态查询 API（设备状态/最近渲染）

---

**User**

请用高中生能听懂的方式和我解释一下

(待完成（本阶段收尾必做）
后端严格白名单落地到“转发入口”（只放行 text|list / net.banner，其余 [DROP_BY_MODE]）
输出净化（标题注入工牌/持有人；文本/列表限幅；剔除未知字段）在所有下发路径生效
ACK 驱动：发送带 id → 记录待确认 → 超时3s重试1次 → 仍失败冻结设备30s，仅允许横幅
限频与队列：每设备≤2 QPS；队列有界（丢最旧并记数）；上线补投策略与日志与 build.md 保持一致（阶段1建议不自动补投，由编排端显式下发）
方向化日志：SEND/ACK/DROP/FREEZE 统一格式，便于测试页核对
下一步安排（阶段1收尾）
后端（w）
完成“转发入口”白名单与净化、ACK 跟踪与冻结、限频与丢弃计数、统一日志
render_sender 发送成功后仅更新 last_render（用于可选补投/回显）
测试（d）
在 simulated_work_badge_1.html 启用“自动 ACK”与“渲染屏”联动（已能渲染/ACK则记录 P95 时延）
用例回归：text/list/banner、1秒3条压测（观测限频丢弃）、断连重连、未注册/离线路由、解析错误（ui.error）
硬件（p）
继续只处理两类消息并回 ACK；长文/超行安全截断；确认无重启/死锁)

---

**Cursor**

### 用最容易懂的比喻讲清楚

- 白名单落地到“转发入口”
  - 像校门口保安只放行“学生证”与“家长证”。现在只放这两类指令：ui.render 的 text/list、device.control 的 net.banner。其他一律不放行，记一条“拦截原因”（DROP_BY_MODE）。

- 输出净化（发出前的体检）
  - 标题统一写“工牌001 · 文先生”（从名单里查），不显示 MAC。
  - 文本太长就截断，列表最多 8 行，超的丢掉。
  - 任何奇怪/没定义的字段一律剔除，保证下发给硬件的内容干净、可预期。

- ACK 驱动（签收单）
  - 每条下发都带一个 id。当对方处理完，会回“签收单”（ACK）。
  - 3 秒没回就再发一次；如果还是没回，先“临时封禁”这台设备 30 秒（冻结），这 30 秒里只允许发横幅提示，防止把设备搞崩。

- 限频与队列（闸门 + 垃圾桶）
  - 每台设备每秒最多 2 条渲染指令（≤2 QPS）。
  - 队列满了就丢最旧那条，并把“丢了几条”记到帐上。
  - 上线补投：阶段1建议“由编排端显式再发一次”，不做自动连环补投，避免噪声。

- 方向化日志（统一口径，便于对账）
  - 发送/SEND、签收/ACK、拦截/DROP、冻结/FREEZE 都用固定格式打印，测试页一眼能对上。

### 阶段1收尾：谁做什么（清晰可落地）

- 后端（w）
  - 在“转发入口”加白名单判断与净化（只放 text/list、net.banner；其他 DROP）。
  - 给每条下发建“待签收表”，记录 id、时间；3 秒没回重试一次；再失败冻结设备 30 秒。
  - 加每设备≤2 QPS 的限流与“丢最旧”的有界队列，并统计丢弃次数。
  - 统一日志格式：SEND/ACK/DROP/FREEZE/REDELIVER。
  - 发送成功后再更新 last_render（仅用于可选补投/回显）。

- 测试（d）
  - 把 `simulated_work_badge_1.html` 当“网页版硬件”：自动渲染 ui.render(text/list)、响应 net.banner，并自动回 ACK（带时延统计 P95）。
  - 回归用例：
    - 基本三条：text、list、net.banner（都带 to）。
    - 压测：1 秒发 3 条（观察限频丢弃）。
    - 断连→重连（观察显式补投后恢复）。
    - 未注册/离线目标（应仅日志，不到设备）。
    - 解析错误（设备回 ui.error）。

- 硬件（p）
  - 继续只处理两类消息并回 ACK；长文/超行安全截断。
  - 连续联调确认“不会重启/死锁”。

这样做的意义：后端像“总调度 + 安全网”，任何越界/脏消息都拦住；硬件只做“显示/执行 + 回签收”，系统就稳了。

