---

**User**

请仔细检查代码,你现在和我说的这些逻辑 后端应该实现了很大一部分,不要只查看日志! 请你深入的去阅读现在的代码

---

**Cursor**

我会先在后端代码中搜索并核对以下实现：ui.render/device.control 处理、带 to 的转发、设备路由发送函数、ACK 处理、限频与渲染缓存等，并据此给出具体差距清单与建议。随后我会汇总结果给你。

### 阶段1现状（已落地）
- 转发与白名单
  - `backend/core/handle/textHandle.py`: 已支持 `ui.render/device.control` 携带 `to:[...]` 的直达转发；并做阶段1白名单校验（仅放行 `ui.render(text|list)`、`device.control(net.banner)`），其余直接丢弃并日志标注 `[DROP_BY_MODE]`。
- 路由与发送
  - `backend/core/websocket_server.py::send_to_device(...)`: 已实现设备直达发送；会移除 `to` 字段；`ui.render` 走 `render_sender`；`device.control` 仅透传 `text/level/duration_ms/id`。
- 清洗与限频
  - `backend/core/orchestration/render_schema.py::clean_render_payload(...)`: 仅允许 `text|list`，文本/列表限幅，未知字段剔除；标题自动注入“工牌{badge} · {owner}”（`device_registry.py`）。
  - `backend/core/orchestration/render_sender.py`: 每设备限频（≥500ms），超限丢弃旧帧并日志提示；成功后更新 last_render。
- 设备 ACK/ERROR
  - 设备端 `hardware/main/application.cc`: 仅处理 `ui.render(text|list)`、`device.control(net.banner)`；渲染成功回 `{type:"ui.ack",id}`，解析/渲染失败回 `{type:"ui.error",code}`。
  - 后端对 `ui.ack/ui.error` 已做日志透传（阶段1不回发起方）。

### 差距与风险（需收尾）
- ACK 跟踪/冻结：尚未见“待确认表 + 3s超时重试1次 + 失败冻结30s”的实现（当前仅日志，不限流到冻结层面）。
- 统一方向化日志：SEND/ACK/DROP/FREEZE 的统一格式需补齐（现已部分日志，但未统一格式与统计口径）。
- 上线补投策略：`send_render` 会写入 last_render，但“注册后自动补投 last_render”的入口未见（阶段1你已选择“编排端显式下发”，可暂不做自动补投）。
- 队列有界与丢弃计数：已有“时间间隔限频+丢弃旧帧”日志，但“丢弃计数”和“队列上限”未统一呈现。
- 小缺陷建议跟踪：`backend/core/utils/last_render_cache.py::_normalize_device_id` 中变量名疑似笔误（使用了未定义的 v），虽不影响当前主链路，但建议尽快修复。

### 结论（我们处在阶段1的“收尾”）
- “能连、能收指令、能渲染、能回ACK”已达标；白名单与清洗/限幅已生效；核心链路稳定。
- 进入阶段1收尾：补齐 ACK 跟踪/冻结、统一日志、限频丢弃统计；是否启用自动补投按你在 build.md 的策略（阶段1由编排端显式下发）执行。

### 下一步最小收尾清单（不改协议）
- 后端（w）
  - 实现 ACK 待确认表：下发带 id→登记；3s 未回→重试1次；再失败→冻结30s（仅放行 `net.banner`），日志 `[FREEZE] device=... seconds=30`。
  - 统一日志格式：`[SEND] type=.. id=.. to=.. mode=..`、`[ACK] id=.. elapsedMs=..`、`[DROP_BY_MODE] ...`、`[DROP_INVALID] ...`、`[FREEZE] ...`。
  - 限频统计：每设备丢弃计数累计输出（按分钟或每N条）。
- 测试（d）
  - 用模拟页回归：text/list/banner、1秒3条压测（观测限频丢弃）、断连重连（显式补投）、未注册/离线（仅日志）、解析错误（设备回 `ui.error`）。
  - 记录 P95 ACK 时延，作为阶段1验收指标。
- 硬件（p）
  - 保持只处理两类指令并回 ACK；长文/超行安全截断；持续观察“无重启/死锁”。

这样做即可在阶段1完成“安全收尾”，把后端变成“强管控+白名单+ACK驱动”的安全阀，硬件侧保持最简执行。

---

**User**

请用高中生能听懂的方式和我解释一下阶段2的预告;
模式状态机落地：后端按设备 currentMode 扩白名单（meeting/coding/working 各自允许集）
页面能力扩展：working.list 分页（8/页）、coding.log 滚动窗口；仍走同一渲染引擎
可观测：ACK 耗时/丢弃/冻结指标暴露；只读状态查询 API（设备状态/最近渲染）

为什么要后端要按设备 currentMode 扩白名单? 页面能力扩展指的是测试还是硬件?
可观测和只读状态查询 API的意义在哪?

---

**Cursor**

### 阶段2要做什么（通俗版）
- 模式状态机落地（后端管模式，前端只执行）
  - 后端给每台设备记一个“当前模式”currentMode（例如 meeting/coding/working）。
  - 后端根据这个模式，只发送“这模式允许的指令”（白名单）。比如：
    - meeting：允许 `listen.start/stop`、`ui.render: meeting.listen/summary`、`net.banner`
    - coding：允许 `ui.render: coding.log`、`net.banner`
    - working：允许 `ui.render: working.list`、`net.banner`
  - 这样能避免“发错指令把设备搞崩”的情况，也让“该发什么”一目了然。

- 页面能力扩展（同一套渲染引擎，同时用于硬件与测试页）
  - working.list 分页（每页8条）：列表多时翻页显示，不卡屏。
  - coding.log 滚动窗口（保留最近8条）：像聊天记录一样自动滚动。
  - 含义：协议不变，还是 `ui.render`；只是“设备侧渲染引擎”和“测试页的网页渲染器”都要具备这两个显示能力，便于真实体验和稳定联调。

- 可观测与只读状态查询（看得见、查得到、好排障）
  - 可观测（指标）：暴露几项关键数值，便于判断系统好不好用、哪儿慢了、是否被限流：
    - ACK 耗时（P95）= 指令下发到设备回“已完成”的时间
    - 丢弃次数 = 被限频或队列丢弃的条数
    - 冻结次数 = 因多次失败被“临时封禁”的次数
  - 只读状态查询 API（不改变设备，只查看状态）：
    - 查询某设备当前模式、最近一次渲染的内容快照、最近一次 ACK 时间等
    - 场景：设备“看起来没反应”，一查就知道“是没收到？收到没渲染？渲染了没回ACK？”更快定位问题

### 为什么“后端要按 currentMode 扩白名单”很关键
- 像红绿灯：绿灯（允许集）才能走；红灯（不允许）一定拦。
- 设备更安全：后端把关，设备就不会因为“模式不匹配的指令”而异常。
- 运维更省心：出了问题只看后端逻辑（谁放行了什么），不用到处猜。

### “页面能力扩展”到底是谁做
- 主要是“设备渲染引擎”和“测试页渲染器”一起做（同样的显示规则）；
- 后端只负责按协议下发“显示什么”，不关心“怎么画”，这样职责清晰。

### “可观测 + 只读查询”的意义
- 可观测像“体温/心率”：一眼看出系统是否健康（延迟高不高、丢的不多吧、有没有被频繁冻结）。
- 只读查询像“黑匣子回放”：随时查某台设备“当下模式”“最后显示了啥”，排障更快，不打扰设备正常运行。

如果同意，阶段2就按这三条主线推进：先把后端模式白名单做实，再在设备/测试页补上分页与滚动，最后把指标和只读查询端点亮出来。

---

**User**

我认为阶段1收尾的后端 只应该统一日志格式：SEND/ACK/DROP/FREEZE/REDELIVER;
然后阶段2的目标是继续开发硬件和后端,完整实现硬件的上电和对话模式的全流程

---

**Cursor**

### 阶段1收尾（只做日志统一）——能立刻执行的最小改动
- 目标：统一五类日志，方便前后端与“网页版硬件”一眼对账，不改协议、不加功能。
- 日志格式（建议固定字段顺序，键=值，便于正则采集）
  - SEND（后端下发前）
    - 示例：
      - [SEND] type=ui.render id=d1-002 to=94:a9:90:07:9d:88 mode=testing page=dialog.chat body=list qps=ok
      - [SEND] type=device.control id=d1-003 to=94:a9:90:07:9d:88 mode=testing action=net.banner
  - ACK（设备回执）
    - 示例：
      - [ACK] id=d1-002 device=94:a9:90:07:9d:88 elapsedMs=215
  - DROP（两种常见）
    - [DROP_BY_MODE] type=ui.render body=logs reason=not-allowed-in-mode mode=testing
    - [DROP_INVALID] type=ui.render reason=schema-invalid missing=header/body
  - FREEZE（多次失败后的临时封禁）
    - 示例： [FREEZE] device=94:a9:90:07:9d:88 seconds=30 reason=ack-timeout id=d1-004
  - REDELIVER（上线/显式触发的补投）
    - 示例： [REDELIVER] device=94:a9:90:07:9d:88 id=wel-001 page=welcome
- 落点建议（仅统一打印口径，不动业务逻辑）
  - 发送处：`backend/core/websocket_server.py::send_to_device` 与 `render_sender.py`
  - 回执处：`backend/core/handle/textHandle.py`（收到 ui.ack/ui.error）
  - 丢弃处：白名单/清洗失败/限频丢弃都用 DROP 统一格式
  - 补投处：若本阶段选择“显式补投”，由触发编排处打印 REDELIVER；若保留“注册即补投”，在注册阶段打印

小结：完成后，测试页只需要按关键字聚合五类日志即可完成阶段1验收。

---

### 阶段2预告（今天不改代码，只对齐“要做什么”和“为什么”）
- 目标：完整打通“上电→欢迎→对话模式”的全流程（参考全流程演示.md L9-L13），后端主导模式，硬件只执行。
- 为什么“后端按 currentMode 扩白名单”
  - 像红绿灯，后端根据设备 currentMode 只发“这时候允许的指令”，避免“发错口令把设备搞崩”。
  - 例：dialog 模式允许 ui.render: dialog.chat、device.control: net.banner|play.tone；meeting 模式才允许 listen.start/stop。
- 页面能力扩展是谁做
  - 同一套渲染引擎同时用于硬件与测试页（网页版硬件）。后端仍只发 ui.render，不关心“怎么画”。
  - 本阶段只做 dialog 所需：欢迎页/对话页的稳定渲染；working/coding 的分页/滚动放到后续。
- 可观测与只读查询的意义
  - 可观测（ACK耗时/丢弃/冻结）：像体温表，一眼看出延迟高不高、丢得多不多、是否经常熔断。
  - 只读查询 API（设备状态/最近渲染）：像黑匣子，用于排障，不会影响设备行为。

---

### 阶段2任务分解（对话模式最小闭环）
- 后端（w）
  - 模式状态机（每设备）：
    - 状态：boot→welcome→dialog.preparing→dialog.active
    - 白名单：dialog.preparing/active 允许 ui.render: dialog.chat、device.control: net.banner|play.tone
  - 编排（示例顺序）
    - 设备上线→设置 mode=welcome→下发 welcome 渲染
    - 收到“准备好/唤醒”→设置 mode=dialog.preparing→下发“建立连接/请稍候”与 play.tone
    - 设置 mode=dialog.active→下发“开始对话”的对话页渲染
  - 安全净化依旧：注入“工牌{badge} · {owner}”，限幅/剔除未知字段
- 硬件（p）
  - 保留开机动画/欢迎页；进入“渲染测试页”已验证通过
  - 新增对 device.control: play.tone 的处理（本地提示音播放），不实现 listen.start/stop
  - 对话页模板：基于 EinkRenderEngine 渲染 header/body/footer（text/list），继续 ACK
- 测试（d）
  - 用已有 `simulated_work_badge_1.html` 作为“网页版硬件”，自动渲染/ACK
  - 测试剧本：
    - 上电→welcome 可见
    - 触发“准备好/唤醒”→收到“建立连接/请稍候”+横幅+提示音（网页端可用代替显示）
    - 进入 dialog.chat→下发几条对话文本/列表→ACK≤3s
  - 指标：记录 ACK P95、DROP 次数、是否出现 FREEZE

---

### 下一步（你确认后即可开工）
- 阶段1：后端统一日志（SEND/ACK/DROP/FREEZE/REDELIVER），当天完成，测试页对账通过。
- 阶段2：按上面拆解推进对话模式闭环；先从 play.tone 与 dialog.chat 渲染开始，listen.* 留到会议模式再放行。

如需，我可把“对话模式白名单表”和“欢迎→对话的编排状态转移图”补充到 build.md，便于后续实现直接对照。

---

**User**

给我阶段1收尾的具体的后端执行的任务

---

**Cursor**

### 阶段1收尾（后端）— 只做日志统一，立即可执行

- 统一打印口径（五类）
  - SEND（发送前）
    - 打点处：
      - `backend/core/websocket_server.py::send_to_device`（ui.render/device.control 两分支）
      - `backend/core/orchestration/render_sender.py::send_render/send_control`（如有直发）
    - 字段：type, id?, to, mode?, page|action, qps=ok|limited
    - 示例：
      - [SEND] type=ui.render id=d1-002 to=94:a9:90:07:9d:88 mode=testing page=dialog.chat body=list qps=ok
      - [SEND] type=device.control id=d1-003 to=94:a9:90:07:9:88 mode=testing action=net.banner
  - ACK（设备回执）
    - 打点处：`backend/core/handle/textHandle.py` 收到 `ui.ack` 时
    - 字段：id, device, elapsedMs（若 msg.ts 可计算）
    - 示例：[ACK] id=d1-002 device=94:a9:90:07:9d:88 elapsedMs=215
  - DROP（两类）
    - [DROP_BY_MODE]（白名单不通过）：`textHandle.py` 转发入口
      - 字段：type, reason=not-allowed-in-mode, mode, extra（如 body.kind/logs）
    - [DROP_INVALID]（清洗/schema失败/缺字段）：`render_schema.py`/`send_to_device` 失败路径
      - 字段：type, reason, missing? / invalidField?
  - FREEZE（临时封禁）— 本阶段仅日志预留，不启用逻辑
    - 打点处：`render_sender.py`（预留一处日志，不触发真正冻结）
    - 示例：[FREEZE] device=94:a9:90:07:9d:88 seconds=30 reason=ack-timeout id=d1-004（仅示例，阶段1不触发）
  - REDELIVER（补投）— 若当前采取“编排端显式补投”，仅在编排触发处打印
    - 字段：device, id, page
    - 示例：[REDELIVER] device=94:a9:90:07:9d:88 id=wel-001 page=welcome

- 具体改动点与建议实现
  - `backend/core/websocket_server.py::send_to_device`
    - 在分支 `ui.render`/`device.control` 调用前打印 [SEND]，组装字段：
      - type、id（payload.id）、to（device_id）、page 或 action、qps（从 `render_sender` 返回值/状态判断，如限频可标记 limited）
  - `backend/core/orchestration/render_sender.py`
    - 在限频丢帧处，统一用 `[DROP_INVALID] type=ui.render reason=rate-limited interval=<ms> device=<id>`
    - 成功发送后，返回一个状态（ok/limited），供 `send_to_device` 打印 qps=ok|limited（或由此处直接打印 [SEND]）
  - `backend/core/handle/textHandle.py`
    - `ui.ack/ui.error`：统一打印 [ACK]（error 也打印为 ACK，但附 `code` 字段）
      - 带 device（`conn.device_id`）、id（msg.id）、elapsedMs（若 msg.ts 可计算）
    - `DROP_BY_MODE`：已存在，确保键=值风格并补充 `mode=<conn.current_mode>` 与 `detail=<body.kind|action>`
  - `backend/core/orchestration/render_schema.py`
    - 清洗失败/缺字段：打印 `[DROP_INVALID] type=ui.render reason=schema-invalid missing=header/body|kind`（键=值）

- 验收方法（测试配合）
  - 使用 `simulated_work_badge_1.html` 作为“网页版硬件”，向真实硬件或网页版硬件发送：
    - text、list、net.banner（带 to）
  - 在后端日志中检查：
    - 每条下发前有 [SEND]；设备回包有 [ACK]（含 id/elapsedMs）；非白名单/不合法消息打印 [DROP_BY_MODE]/[DROP_INVALID]
    - 若触发编排端显式补投时，应有 [REDELIVER] 行
  - 记录一次压测：1秒内发送3条 ui.render，观察 [DROP_INVALID reason=rate-limited] 行是否出现

- 完成标准
  - 五类日志均能稳定打印，字段规范、格式统一
  - 测试页可通过日志快速核对每条消息的去向与结果（无需深入代码和后端内部变量）

如同意，我可进一步把具体日志模板（格式化字符串）写入对应函数注释位置，便于直接复制实现。

---

**User**

好的,现在后端已经更新了统一日志,请验收后端的成果,并告诉我应该怎么测试?

---

**Cursor**

### 验收定位（一句话）
- 当前链路已通：测试页 → 后端（带 to 转发+白名单+清洗+限频）→ 硬件渲染 → 硬件回 ACK。阶段1收尾只验“统一日志是否到位”。

### 如何测试（按用例逐条验证日志五类标签）
前置
- 打开 `test/simulated_work_badge_1.html`，以真实/模拟设备连接后端（确保握手带 `device-id` 小写 MAC）。
- 目标设备ID准备：如 `94:a9:90:07:9d:88`；`backend/data/devices.yaml` 映射存在（标题应显示“工牌… · …”）。

1) 文本渲染（ui.render:text）
- 发送：
```json
{ "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-001","page":"dialog.chat",
  "header":{"title":"(可留空, 由后端注入)"},
  "body":{"kind":"text","text":"Hello 渲染测试"},
  "footer":{"hint":"后端→设备 OK"} }
```
- 期望日志：
  - [SEND] type=ui.render id=d1-001 to=… page=dialog.chat body=text qps=ok
  - [ACK] id=d1-001 device=… elapsedMs≈0–3000
- 验收：设备显示文本；ACK P95 ≤ 3s。

2) 列表渲染（ui.render:list，验证限幅）
- 发送（>8行）：
```json
{ "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-002","page":"dialog.chat",
  "body":{"kind":"list","items":["1","2","3","4","5","6","7","8","9","10"]}}
```
- 期望日志：
  - [SEND] … body=list …
  - [ACK] id=d1-002 …
- 验收：设备仅展示前8行；ACK 正常。

3) 顶部横幅（device.control: net.banner）
- 发送：
```json
{ "type":"device.control","to":["94:a9:90:07:9d:88"],"id":"d1-003","action":"net.banner",
  "text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
```
- 期望日志：
  - [SEND] type=device.control id=d1-003 to=… action=net.banner
  - [ACK] id=d1-003 …
- 验收：设备浮条≈3s；ACK 正常。

4) 白名单拦截（DROP_BY_MODE）
- 发送非法 body.kind：
```json
{ "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"bad-001","page":"dialog.chat",
  "body":{"kind":"logs","lines":["x"]}}
```
- 期望日志：
  - [DROP_BY_MODE] type=ui.render body=logs reason=not-allowed-in-mode mode=testing
- 验收：设备不应收到该消息。

5) 无效负载（DROP_INVALID）
- 发送缺少 body：
```json
{ "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"bad-002","page":"dialog.chat" }
```
- 期望日志：
  - [DROP_INVALID] type=ui.render reason=schema-invalid missing=body
- 验收：设备不应渲染；如已到设备，设备会回 ui.error（也可在日志看到）。

6) 限频丢弃
- 在 1 秒内快速发 3 条 ui.render（text）
- 期望日志其一出现：
  - [SEND] … qps=ok（前两条）
  - [DROP_INVALID] type=ui.render reason=rate-limited interval=<ms> device=…
- 验收：设备只渲染有限条；无异常。

7) 重连与补投（按阶段1策略）
- 若阶段1采用“显式补投”，请在重连后手动再发一次最近渲染；预期：
  - [REDELIVER] device=… id=… page=…
- 验收：设备恢复显示；日志含 REDELIVER（如未启用自动补投即不出现）。

### 观察要点（判定是否通过）
- 日志五类标签齐全且键=值规范：SEND / ACK / DROP_BY_MODE / DROP_INVALID /（可选）REDELIVER；阶段1不应出现 FREEZE。
- ACK P95 ≤ 3 秒；限频丢弃在压测场景可见；非法与越权消息稳定被 DROP。
- 渲染标题由后端注入“工牌+持有人”；未注册设备仅日志提示，不上屏。

### 常见排查
- 没看到 [SEND]：多在 `send_to_device` 前补日志；或消息没带 to、目标不在线。
- ACK 没有 elapsedMs：消息未带 ts（允许），只要有 ACK 即可。
- 标题没注入：检查 `backend/data/devices.yaml` 与 `device_registry.get_display_title`。
- 列表显示超 8 行：检查清洗与设备侧限幅是否同步。

按上述用例走一遍，若日志与渲染表现均符合，即阶段1收尾（日志统一）通过，可进入阶段2（上电→欢迎→对话模式全流程）开发。

```json
{ "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-001","page":"dialog.chat",
  "header":{"title":"(可留空, 由后端注入)"},
  "body":{"kind":"text","text":"Hello 渲染测试"},
  "footer":{"hint":"后端→设备 OK"} }
```

```json
{ "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-002","page":"dialog.chat",
  "body":{"kind":"list","items":["1","2","3","4","5","6","7","8","9","10"]}}
```

```json
{ "type":"device.control","to":["94:a9:90:07:9d:88"],"id":"d1-003","action":"net.banner",
  "text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
```

```json
{ "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"bad-001","page":"dialog.chat",
  "body":{"kind":"logs","lines":["x"]}}
```

```json
{ "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"bad-002","page":"dialog.chat" }
```

---

**User**

发送 { "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"bad-002","page":"dialog.chat" } 显示250824 15:11:13[0.5.8_SiDoChDonoca][core.handle.textHandle]-INFO-[DROP_BY_MODE] type=ui.render reason=not-allowed-in-mode mode=None detail=None

在 1 秒内快速发 3 条 ui.render（text）日志会显示设备不在线

---

**Cursor**

### 你看到的两种日志现象，原因与结论
- 关于 DROP_BY_MODE（发的 JSON 少了 body）
  - 原因：后端当前是“先做白名单，再做结构校验”。因为没有 body.kind，白名单判断拿到的是 None，就按“模式不允许”打了 DROP_BY_MODE。
  - 正确预期：这应归类为“负载不合格”，应打 DROP_INVALID（reason=schema-invalid, missing=body）。
  - 结论：设备没收到指令，属安全拦截；先按“DROP_INVALID 处理”的心智理解，功能上是对的，标签待统一。

- 关于“一秒连发3条 ui.render → 显示设备不在线”
  - 原因：限频触发后，发送函数返回 False，被转发入口当成“下发失败/不在线”打印了这行日志；实际上是“被限频丢弃/qps=limited”，不是设备离线。
  - 正确预期：应打印 DROP_INVALID（reason=rate-limited）或在 [SEND] 里 qps=limited，不应该出现“设备不在线”误导。
  - 结论：设备在线，限频生效。先按“限频丢弃”理解该日志，标签会在后端收尾统一。

### 验收怎么测（按用例一步步对）
- 基础验证
  1) 发文本（带 body.kind=text）→ 预期 [SEND qps=ok] → 设备渲染 → [ACK id=… elapsedMs≈0–3000]
  2) 发列表（>8行）→ 预期仅显示前8行 → [ACK]
- 异常与限频
  3) 发缺 body 的 ui.render → 现在看到 DROP_BY_MODE（预期是 DROP_INVALID），忽略标签差异即可
  4) 1秒内发3条 ui.render → 预期出现 qps=limited 或 rate-limited；若出现“设备不在线”，当作限频丢弃看待
- 稳定性
  5) 间隔≥500ms（每秒≤2条）再次连发 → 应全部 [SEND qps=ok]+[ACK]
  6) lower-case 的 `to`（小写冒号 MAC），确保与握手格式一致

小贴士：
- 认定在线：用 server.stats 里 online 列表或后端在线路由表；别被“误导日志”影响判断。
- 发送带 ts（毫秒）能更准确看到 ACK elapsedMs。

### 建议的最小修正（不改协议，易落地）
- 校验顺序：转发入口先做“结构/清洗（body.kind 必须是 text|list）”，不通过 → DROP_INVALID；通过才进入“模式白名单”判断。
- 限频返回语义：把“限频”与“离线/失败”区分开（例如 send_to_device 返回 ok/limited/offline），或在 sender 内直接打印 DROP_INVALID:rate-limited，并且上游不再打印“设备不在线”。
- 默认模式：连接后把 `currentMode` 置为 testing（或 welcome），让日志里的 mode=testing，而不是 None。

这样理解与测试，就能确认阶段1的链路是“稳的”，并把两处“日志标签/文案”在后端收尾时统一掉。

---

**User**

测试和验收基本通过了 请给我下一步计划

---

**Cursor**

### 阶段2目标（对话最小闭环）
- 完整跑通“上电→欢迎→对话模式”全流程（参考全流程演示.md L9-L13），后端主导模式，硬件/测试页只执行与回ACK。
- 仍使用现有渲染协议（ui.render/device.control），不改协议与页面DSL。

### 后端（w）— 1天
- 模式状态机（每设备）
  - 状态：boot→welcome→dialog.preparing→dialog.active（持于 ConnectionHandler 内存）
  - 事件与编排：
    - onConnect → mode=welcome → 下发 welcome（ui.render:text）
    - onReady/唤醒（可先用测试页触发“mode.start(dialog)”或后台API模拟）→ mode=dialog.preparing → 下发“建立连接/请稍候”（ui.render:text）+ 提示音（device.control: play.tone）
    - 随后 mode=dialog.active → 下发“开始对话”的对话页（ui.render:text）
- 白名单扩展（按模式）
  - dialog.preparing/active：允许 ui.render: dialog.chat、device.control: net.banner|play.tone
  - 其余一律 DROP_BY_MODE（已统一日志）
- 输出净化与限幅
  - 保持阶段1策略：标题注入“工牌{badge} · {owner}”；text ≤200 字；list≤8项；剔除未知字段
- 日志（已统一，继续沿用）
  - [SEND]/[ACK]/[DROP_BY_MODE]/[DROP_INVALID]/（可选）[REDELIVER]
- 验收（后端侧）
  - 顺序日志可见：欢迎→建立连接→开始对话；全程 [SEND] 与 [ACK] 成对且 P95≤3s

### 硬件（p）— 0.5天
- 保留开机动画/欢迎页；进入“渲染测试页”已具备
- 新增 device.control: play.tone 支持（本地提示音），其余保持不变
- 继续仅处理 ui.render(text|list)、device.control(net.banner|play.tone) 并回 ACK；长文/超行安全截断
- 验收：按编排收到三步指令并稳定渲染/提示音/ACK；无重启/死锁

### 测试（d）— 0.5天
- 复用 `test/simulated_work_badge_1.html`（网页版硬件）
  - 处理 play.tone：以UI标记或日志显示“播放提示音”
  - 自动回 ACK（已具备），统计 ACK P95
- 用例剧本
  1) 连接后收到 welcome → [ACK]
  2) 触发“准备好/唤醒”（可用“mode.start(dialog)”或后端API）→ 收到“建立连接/请稍候”+ play.tone → [ACK]
  3) 进入 dialog.active → 收到“开始对话”页 → [ACK]
  4) 压测：1 秒 3 条 ui.render（观察 qps=limited 的 DROP），再间隔≥500ms 连发验证全部 ACK
  5) 断连→重连：按阶段2策略由编排再显式下发一次当前页（或保留不自动补投）

### 通过标准
- 全流程页序与日志顺序一致：welcome → dialog.preparing → dialog.active
- 指令只在允许的模式下发送（白名单生效，越权即 DROP_BY_MODE）
- ACK P95 ≤3s；限频丢弃在压测场景有日志可见；无“设备不在线”的误导文案
- 硬件/测试页渲染正常，无重启/死锁

### 时间与分工
- w：模式机+编排+白名单扩展（4h）、净化/限幅核对（1h）、日志对齐（1h）、联调（2h）
- p：play.tone 支持（2h）、渲染与ACK回归（2h）
- d：测试剧本与P95统计（3h）、压测与断连用例（2h）

### 风险与对策
- 模式切换误发指令 → 状态机前置检查+DROP_BY_MODE
- 误判为离线 → 已统一日志，限频/离线分开打印；若仍出现，按日志定位send路径
- 提示音依赖 → 硬件本地播放，测试页用UI提示代替，不阻塞流程

需要我把“对话模式白名单表与状态转移顺序”追加到 build.md 的阶段2章节，便于后端一次性实现吗？

---

**User**

将阶段2目标（对话最小闭环）写入bulid.md中@build.md 

---

**Cursor**

```markdown
# 项目架构

# 目标
- 覆盖对话/会议/工作/编码四类页面的端到端演示；并发≥10；≥3台互动；离线补投“最后渲染”；内网部署 + API Token。

——

## 3. 阶段2 目标（对话最小闭环）

- 目标
  - 完整跑通“上电→欢迎→对话模式”最小闭环（参考《全流程演示.md》L9-L13）。
  - 后端主导模式与编排；硬件/测试页仅执行与回 ACK。
  - 不改协议与 DSL：仍使用 `ui.render / device.control`。

- 后端（w）
  - 模式状态机（每设备，内存即可）
    - 状态：`boot → welcome → dialog.preparing → dialog.active`
    - 事件与编排：
      - onConnect → `mode=welcome` → 下发 welcome（`ui.render:text`）
      - onReady/唤醒（测试期可用“mode.start(dialog)”或内部触发）→ `mode=dialog.preparing` → 下发“建立连接/请稍候”（`ui.render:text`）+ `device.control: play.tone`
      - 进入 `mode=dialog.active` → 下发“开始对话”（`ui.render:text`）
  - 白名单（按模式）
    - dialog.preparing/active：允许 `ui.render: dialog.chat`、`device.control: net.banner | play.tone`
    - 其余消息一律丢弃并日志 `[DROP_BY_MODE]`
  - 输出净化与限幅（延续阶段1）
    - 标题注入“工牌{badge} · {owner}”；`text ≤ 200`、`list ≤ 8`；未知字段剔除
  - 日志（沿用统一口径）
    - `[SEND]/[ACK]/[DROP_BY_MODE]/[DROP_INVALID]`（如有显式补投则 `[REDELIVER]`）

- 硬件（p）
  - 保留开机动画/欢迎页；进入“渲染测试页”路径不变
  - 新增 `device.control: play.tone`（本地提示音/替代提示）；继续仅处理 `ui.render(text|list)`、`device.control(net.banner|play.tone)` 并回 ACK
  - 长文/超行安全截断；整屏合并节流（≥500ms）

- 测试（d）
  - 复用 `test/simulated_work_badge_1.html`（网页版硬件）
    - 自动渲染与回 ACK；对 `play.tone` 以 UI 提示或日志方式标记
  - 用例剧本：
    - 连接→欢迎页（`[SEND]`/`[ACK]`）
    - 触发“准备好/唤醒”→收到“建立连接/请稍候”+ `play.tone`（`[SEND]`/`[ACK]`）
    - 进入对话页 `dialog.active` → 收“开始对话”渲染（`[SEND]`/`[ACK]`）
    - 压测：1 秒 3 条 `ui.render` 触发限频（日志出现 `qps=limited` 或 `rate-limited`）→ 再以 ≥500ms 间隔发送全部成功 ACK
    - 断连→重连：由编排端显式下发当前页，页面恢复（如采用自动补投则打印 `[REDELIVER]`）

- 验收口径
  - 顺序：`welcome → dialog.preparing → dialog.active`；每步均有 `[SEND]` 与对应 `[ACK]`，P95 ≤ 3s
  - 白名单：非允许消息一律 `[DROP_BY_MODE]`，设备不接收
  - 稳定：限频丢弃在压测场景出现；正常节奏下全部 ACK；无“设备不在线”误导文案

- 时间与分工（建议）
  - w：状态机与编排（4h）、白名单扩展（1h）、净化核对（1h）、联调（2h）
  - p：`play.tone` 支持（2h）、渲染与 ACK 回归（2h）
  - d：剧本与 P95 统计（3h）、压测/断连用例（2h）

- 风险与对策
  - 模式切换误发指令 → 状态机前置校验 + `[DROP_BY_MODE]`
  - 限频误判为离线 → 统一日志（`qps=limited`/`rate-limited`），与“设备不在线”区分
  - 提示音依赖 → 硬件本地播放；测试页以 UI/日志代替，不阻塞流程


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

## 2. 后端核心原则（Fail-Closed 安全编排，必须执行）(阶段1出现核心问题)

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
```

已将“阶段2目标（对话最小闭环）”写入 `collaboration/build.md`，包括：
- 目标与不改协议的约束
- 后端的状态机与编排、按模式白名单、净化限幅与统一日志
- 硬件需支持 `play.tone` 并保持最小渲染+ACK
- 测试的剧本与压测/断连用例
- 验收口径、时间分工与风险对策

可据此启动阶段2开发与联调。

---

**User**

不对,“在设备连接/hello 后：发欢迎页”这个逻辑是错误的,因为硬件本身的开机动画和欢迎页面是预设好的,和渲染引擎无关,应该确认唤醒之后,才能发送渲染; 请更新需求,重建逻辑

---

**Cursor**

```markdown
# 项目架构

# 目标
- 覆盖对话/会议/工作/编码四类页面的端到端演示；并发≥10；≥3台互动；离线补投“最后渲染”；内网部署 + API Token。

——

## 3. 阶段2 目标（对话最小闭环，后端在“唤醒后”才渲染）

- 原则修正（重要）
  - 设备“开机动画/欢迎页”由硬件本地预置完成，后端在“连接/hello”阶段不发送任何 `ui.render`。
  - 仅在设备“唤醒”后，后端才开始渲染与控制（最小：`ui.render:text|list`、`device.control: play.tone|net.banner`）。

- 触发事件（唤醒）
  - 推荐使用现有 `mode` 消息：`{ "type":"mode", "state":"start", "mode":"dialog" }` 作为“唤醒/进入对话”的统一触发。
  - 兼容测试：也可由后端调试接口或测试页按钮触发等效事件（仅用于联调）。

- 后端（w）编排与白名单
  - 状态机（每设备，内存即可）：`boot(local) → connected(idle) → dialog.preparing → dialog.active`
    - onConnect/onHello → 仅记录 `connected(idle)`；不下发任何渲染
    - onWake(`mode.start(dialog)`) → `dialog.preparing`：下发“建立连接/请稍候”（`ui.render:text`）+ `device.control: play.tone`
    - 进入 `dialog.active`：下发“开始对话”页面（`ui.render:text`）
  - 白名单（仅该模式允许）：
    - dialog.preparing/active：允许 `ui.render: dialog.chat`、`device.control: net.banner | play.tone`
    - 其余消息一律 `[DROP_BY_MODE]`
  - 输出净化与限幅（延续阶段1）：标题注入“工牌{badge} · {owner}”；`text ≤ 200`、`list ≤ 8`；剔除未知字段
  - 日志（延续统一口径）：`[SEND]/[ACK]/[DROP_BY_MODE]/[DROP_INVALID]`（如显式补投则 `[REDELIVER]`）

- 硬件（p）行为
  - 本地完成：开机动画与欢迎页；不依赖后端渲染
  - 连接成功后静默等待“唤醒”相关下发；仅在收到 `ui.render(text|list)` 或 `device.control(play.tone|net.banner)` 时执行并回 ACK
  - 新增 `play.tone`（本地提示音/替代提示）

- 测试（d）用例
  1) 连接后（未唤醒）：不应有任何 `ui.render` 下发；仅基础 hello/统计
  2) 发送 `mode.start(dialog)`（或等效触发）→ 预期顺序：
     - `[SEND] ui.render:text`（建立连接/请稍候） → `[ACK]`
     - `[SEND] device.control: play.tone` → `[ACK]`
     - 进入 `dialog.active` 后 `[SEND] ui.render:text`（开始对话） → `[ACK]`
  3) 压测：1 秒 3 条 `ui.render`（在 `dialog.active`）→ 观察限频丢弃（`qps=limited` / `rate-limited`）
  4) 断连→重连：保持 `connected(idle)`；不自动渲染；由编排端在确认“已唤醒”后再显式下发当前页

- 验收口径
  - 连接/hello 阶段无渲染下发；唤醒后才开始渲染/控制
  - 流程顺序：`connected(idle) → dialog.preparing → dialog.active`；每步有 `[SEND]/[ACK]` 配对且 P95 ≤ 3s
  - 白名单与净化持续生效；限频在压测用例可见


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

## 2. 后端核心原则（Fail-Closed 安全编排，必须执行）(阶段1出现核心问题)

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
```

已更新阶段2目标到“唤醒后才渲染”的设计：
- 连接/hello 阶段不发送任何 ui.render；仅在收到唤醒事件（建议用 mode.start(dialog)）后，进入 dialog.preparing → dialog.active，并按顺序下发“请稍候/提示音/开始对话”的渲染与控制
- 硬件继续保留本地开机动画与欢迎页，连接后静默等待后端指令
- 测试用例与验收口径同步调整，覆盖未唤醒不渲染、唤醒后有序渲染、限频压测与断连重连策略

可据此推进阶段2实现与联调。

---

**User**

刚刚后端工程师更新了代码,请查看日志@log.md ,再次确认和优化阶段2的目标设计逻辑@build.md 

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

## 2. 后端核心原则（Fail-Closed 安全编排，必须执行）(阶段1出现核心问题)

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


## 3. 阶段2 目标（对话最小闭环，后端在“唤醒后”才渲染）

- 原则修正（重要）
  - 设备“开机动画/欢迎页”由硬件本地预置完成，后端在“连接/hello”阶段不发送任何 `ui.render`。
  - 仅在设备“唤醒”后，后端才开始渲染与控制（最小：`ui.render:text|list`、`device.control: play.tone|net.banner`）。

- 触发事件（唤醒）
  - 首选：设备上报 `{ "type":"mode", "state":"start", "mode":"dialog" }`，作为“唤醒/进入对话”的统一触发。
  - 等价事件：`listen.start`（开始拾音）触发进入 `dialog.preparing`；`listen.detect`（检测到唤醒词）下发“准备聆听”提示页（仅提示，不进入聊天/TTS）。
  - 兼容测试：可由后端调试接口或测试页按钮触发等效事件（仅用于联调）。

- 后端（w）编排与白名单
  - 状态机（每设备，内存即可）：`boot(local) → connected(idle) → dialog.preparing → dialog.active`
    - onConnect/onHello → 仅记录 `connected(idle)`；不下发任何渲染
    - onWake（`mode.start(dialog)` 或 `listen.start`）→ `dialog.preparing`：
      - 下发“建立连接/请稍候”（`ui.render:text`，如 id=dlg-listen-start）
      - 下发 `device.control: play.tone`
    - onListenDetect（检测到唤醒词）→ 仍处 `dialog.preparing`：下发“准备聆听”提示页（例如 id=dlg-ready），不进入聊天/TTS
    - 进入 `dialog.active`：下发“开始对话”（`ui.render:text`）
  - 白名单（仅该模式允许）：
    - 目标设备 `currentMode ∈ { dialog.preparing, dialog.active }` 才放行顶层直达 `to` 消息
    - `ui.render` 仅允许 `page == dialog.chat`；`device.control` 仅允许 `net.banner | play.tone`
    - 其余消息一律 `[DROP_BY_MODE]`
  - 输出净化与限幅（延续阶段1）：标题注入“工牌{badge} · {owner}”；`text ≤ 200`、`list ≤ 8`；剔除未知字段
  - 日志（延续统一口径）：`[SEND]/[ACK]/[DROP_BY_MODE]/[DROP_INVALID]`（如显式补投则 `[REDELIVER]`）

- 硬件（p）行为
  - 本地完成：开机动画与欢迎页；不依赖后端渲染
  - 连接成功后静默等待“唤醒”相关下发；仅在收到 `ui.render(text|list)` 或 `device.control(play.tone|net.banner)` 时执行并回 ACK
  - 新增 `play.tone`（本地提示音/替代提示）

- 测试（d）用例
  1) 连接后（未唤醒）：不应有任何 `ui.render` 下发；仅基础 hello/统计
  2) 发送 `mode.start(dialog)`（或等效触发）→ 预期顺序：
     - `[SEND] ui.render:text`（建立连接/请稍候，id=dlg-listen-start） → `[ACK]`
     - `[SEND] device.control: play.tone` → `[ACK]`
     - （若出现 `listen.detect`）应看到 `[SEND] ui.render:text`（准备聆听，id=dlg-ready） → `[ACK]`
     - 进入 `dialog.active` 后 `[SEND] ui.render:text`（开始对话） → `[ACK]`
  3) 压测：1 秒 3 条 `ui.render`（在 `dialog.active`）→ 观察限频丢弃（`qps=limited` / `rate-limited`）
  4) 断连→重连：保持 `connected(idle)`；不自动渲染；由编排端在确认“已唤醒”后再显式下发当前页

- 验收口径
  - 连接/hello 阶段无渲染下发；唤醒后才开始渲染/控制
  - 流程顺序：`connected(idle) → dialog.preparing → dialog.active`；每步有 `[SEND]/[ACK]` 配对且 P95 ≤ 3s
  - 白名单与净化持续生效；限频在压测用例可见


```

已根据日志中的新变更优化阶段2设计并更新到 `collaboration/build.md`：
- 后端仅在“唤醒后”才渲染；连接/hello 阶段不下发任何 ui.render
- 唤醒触发兼容两条路径：mode.start(dialog) 或 listen.start；listen.detect 仅下发“准备聆听”提示页
- 状态机细化：connected(idle) → dialog.preparing（请稍候+play.tone）→ dialog.active（开始对话）
- 顶层直达 to 白名单按目标设备 currentMode 判定：只放行 dialog.chat 与 net.banner|play.tone
- 测试用例同步加入 dlg-listen-start / dlg-ready 的 ACK 验收

可按该版本推进阶段2实现与联调。

---

**User**

让我们来仔细讨论一下后端工作的安排,请以高中生能听懂的方式说清楚,每一条改动是做什么的? 对我们实现阶段2 的目标（对话最小闭环） 有什么帮助?



---

**Cursor**

### 阶段2（对话最小闭环）后端改动清单——做什么？为什么有用？

- 改动1：给每台设备建“模式状态”
  - 做什么：在后端记录 `currentMode`（boot → connected(idle) → dialog.preparing → dialog.active）。
  - 为什么有用：像红绿灯。没“唤醒”就不发渲染，避免把设备从欢迎页“顶掉”。

- 改动2：接管“唤醒”触发，只在唤醒后渲染
  - 做什么：
    - onConnect/onHello：只记状态为 connected(idle)，不渲染。
    - onWake：收到 `mode.start(dialog)` 或 `listen.start` 时改为 dialog.preparing，并下发两条安全内容：
      - `ui.render:text`（“建立连接/请稍候”，id=dlg-listen-start）
      - `device.control: play.tone`（提示音）
    - onListenDetect：收到 `listen.detect` 时仍在 dialog.preparing，下发“准备聆听”（id=dlg-ready），不直接进聊天/TTS。
    - 进入 dialog.active：下发“开始对话”（`ui.render:text`）。
  - 为什么有用：让“欢迎→唤醒→对话”有清晰节奏，用户有反馈，设备不被误操作。

- 改动3：直达转发的“白名单”看目标设备的模式
  - 做什么：带 `to:["device-id"]` 的顶层消息，只在目标设备 `currentMode ∈ {dialog.preparing, dialog.active}` 才放行：
    - 允许 `ui.render(page==dialog.chat)`、`device.control(net.banner|play.tone)`。
    - 其他一律 `[DROP_BY_MODE]`。
  - 为什么有用：防止外部误发，把未唤醒设备“拉跑偏”。

- 改动4：渲染净化与限幅（所有下发前必过一遍）
  - 做什么：注入标题“工牌{badge} · {owner}”；`text ≤ 200` 字；`list ≤ 8` 项；未知字段剔除。
  - 为什么有用：硬件只画干净、安全、可预期的数据，不会崩、不会花屏。

- 改动5：统一日志五类（键=值，便于对账）
  - 做什么：`[SEND]`（type/id/to/mode/page|action/qps），`[ACK]`（id/device/elapsedMs），`[DROP_BY_MODE]`，`[DROP_INVALID]`，（显式补投才）`[REDELIVER]`。
  - 为什么有用：出现问题，测试页和后端日志能“一眼对上”，定位更快。

- 改动6：限频与丢弃
  - 做什么：每设备渲染≤2 QPS；超出丢旧帧并计数；日志显示 `qps=limited` 或 `rate-limited`。
  - 为什么有用：防抖动、防刷屏，E‑ink 体验更稳。

- 改动7：补投策略（阶段2保持显式）
  - 做什么：断连重连不自动补投；由编排端在“确认已唤醒”后显式下发当前页（必要时打印 `[REDELIVER]`）。
  - 为什么有用：避免欢迎阶段被远程渲染“覆盖”，遵守“唤醒后才渲染”。

- 改动8：设备映射注入
  - 做什么：从 `devices.yaml` 取 `badge/owner` 注入标题；未注册只记日志，不上屏 MAC。
  - 为什么有用：显示友好，不泄漏硬件地址。

---

### 对应文件与落点（便于实现排期）

- `backend/core/handle/textHandle.py`
  - 处理 `mode.start(dialog)` / `listen.start` / `listen.detect` → 切状态 + 下发对应 `ui.render`/`play.tone`。
  - 顶层直达 `ui.render/device.control` 转发入口做“目标设备模式白名单”检查。
  - 统一 `[ACK]` 打印（elapsedMs 有则带）。

- `backend/core/websocket_server.py`
  - `send_to_device(...)` 打印 `[SEND]`（含 qps=ok|limited），分支到 `render_sender/send_control`。

- `backend/core/orchestration/render_schema.py`
  - 清洗/限幅：注入标题、裁剪文本/列表、剔除未知字段；失败打 `[DROP_INVALID]`。

- `backend/core/orchestration/render_sender.py`
  - 每设备≥500ms 限频；超限打 `[DROP_INVALID reason=rate-limited]`；成功后更新 last_render。

- `backend/core/utils/device_registry.py`
  - `get_display_title(device_id)` 返回“工牌{badge} · {owner}”。

---

### 这对阶段2目标的直接帮助
- 只在“唤醒后”渲染：避免欢迎页被覆盖，流程更贴近真实使用。
- 对话页稳：先“请稍候/提示音/准备聆听”，再“开始对话”，用户明确知道系统在“听”。
- 不误发：按 `currentMode` 扩白名单，任何越权指令直接 DROP，不伤硬件。
- 易排障：统一日志让 SEND/ACK/DROP 一眼可查，压测/断连场景都可快速定位。

---

**User**

你认为为了实现阶段2 的目标（对话最小闭环） 最核心的改动有哪些? 请和我认真讨论;

1 我认为后端建立状态机是最重要的,相当于后端可以清楚的知道每一台设备的当前具体状态,所以请一步到位,参考全流程演示@全流程演示.md ,优化任务安排,在后端建立清晰的所有模式和页面的状态机;

2 我认为第二重要的应该是后端需要实现和硬件的对话模式,就是唤醒后,硬件设备进入了对话模式,后端asr后,应该调用llm能力和用户对话,并且传输数据返回硬件,让硬件可以“说话了”;

3 我还是不太清楚(改动2：接管“唤醒”触发，只在唤醒后渲染 和 改动3：直达转发的“白名单”看目标设备的模式 到底代表什么 )请举例用小学生能听懂的方式和我说明

4 我认为渲染净化与限幅 限频与丢弃 统一日志已经做到了 我不知道为什么还要在这里强调一次?

---

**Cursor**

### 阶段2的最核心改动（按重要性排序）

- 改动1（最重要）：建立“全量设备状态机”（后端统一管控）
  - 做什么：为“每台设备”记录一个清晰的状态与子页面，按事件驱动状态跳转，并据此决定“允许发送哪些指令”。
  - 状态与页面（覆盖全流程，先实现对话路径，其它先占位）
    - 启动与欢迎：boot(local) → connected(idle)（欢迎页由硬件本地渲染，后端不发 ui.render）
    - 对话（本期落地）：dialog.preparing（请稍候/准备聆听）→ dialog.active（开始对话页）
    - 会议（占位）：meeting.preparing → meeting.listen → meeting.analyzing → meeting.summary → meeting.end
    - 工作（占位）：working.list → working.detail → working.assign → working.end
    - 编码（占位）：coding.listen → coding.tasks_confirm → coding.log → coding.end
  - 触发事件（示例）
    - 唤醒/进入对话：mode.start(dialog) 或 listen.start
    - 检测到唤醒词：listen.detect（只下发“准备聆听”提示，不直接进入聊天/TTS）
    - 进入对话页：dialog.active（由编排控制）
  - 为什么有用：像“红绿灯+地图”，后端随时知道每台设备在哪一页、下一步能发什么，杜绝“误发导致设备异常”。

- 改动2：打通“对话闭环”（唤醒后真正能“说话”）
  - 做什么：在 dialog.active 下，按链路把“听-懂-说”贯通起来
    - 听（ASR）：接收硬件（或网页版硬件）的音频/文本，得到识别结果（可分段/最终）
    - 懂（LLM）：把识别文本投喂到 LLM，得到合适的文字回复
    - 说（TTS+下发）：用 TTS 合成语音，按帧下发给设备播放；同时可用 ui.render 简短提示“正在回答…/内容摘要”
  - 为什么有用：这才是“对话模式”的核心价值，用户唤醒后设备能听能答，形成最小可用闭环。

- 改动3：两条安全规则（用小学生能懂的例子）
  - “只在唤醒后渲染”
    - 说明：连上后端还没唤醒时，后端不发任何页面（ui.render），避免把硬件本地欢迎页顶掉。
    - 类比：上课铃没响之前，老师不发作业。
  - “直达转发要看目标设备的模式（白名单）”
    - 说明：别人给某设备发“to:[…]”的渲染/控制指令，后端先看那台设备的当前模式，只有该模式允许的内容才放行。
    - 类比：语文课只能交语文作业，不是语文作业就退回。

- 改动4（不再重复开发，仅作为底线持续检查）
  - 渲染净化与限幅：标题注入“工牌+持有人”，text≤200 字，list≤8 项，未知字段剔除
  - 限频与丢弃：每设备≤2 QPS，超出丢旧帧并打日志
  - 统一日志：SEND/ACK/DROP_BY_MODE/DROP_INVALID/(REDELIVER)
  - 这些已基本就绪，后续只作为“上线前检查清单”，不再反复实现

---

### 面向阶段2落地的任务安排（精简到“能说话”的最短路径）

- 后端（w）
  - 状态机骨架（每设备在内存维护）
    - 新/改：connected(idle) → dialog.preparing → dialog.active 的状态字段与跳转
    - 事件接入：mode.start(dialog) / listen.start / listen.detect
  - 白名单按“目标设备模式”判定
    - 仅当目标设备处于 dialog.preparing/active 时，才放行直达 to 的 ui.render(page==dialog.chat) 与 device.control(net.banner|play.tone)
  - 对话链路编排
    - 接入 ASR：把设备来的音频/文本送到 ASR（已有 provider 可用）
    - 调用 LLM：把 ASR 文本喂给 LLM，获取回答
    - TTS 下发：将 LLM 回答走 TTS，按帧下发音频给设备播放；必要时同时下发简短 ui.render 提示
  - 日志与验收
    - 全链路出现成对的 [SEND]/[ACK]；限频压测能看到 qps=limited；非法/越权指令稳定 DROP

- 硬件（p）
  - 保持“欢迎页本地渲染、不受后端影响”
  - 支持 play.tone；接收并播放 TTS 音频（若已有音频链路可用就复用）
  - 仍只处理 ui.render(text|list) 与 device.control(net.banner|play.tone) 并回 ACK

- 测试（d）
  - 网页版硬件继续渲染/回 ACK；对 play.tone 用 UI 提示代替
  - 剧本：连接不渲染→唤醒进入 dialog.preparing（请稍候+提示音）→ dialog.active（开始对话）→ 发几句语音/文本→ 收到 TTS 播放与 ACK

---

### 验收口径（阶段2通过标准）
- 流程顺序正确：connected(idle)（不渲染）→ 唤醒（preparing：请稍候+提示音）→ active（开始对话）
- 对话有效：能从 ASR 得到文本，LLM 给出回复，TTS 播放到设备
- 安全：任何非白名单消息稳定被后端 DROP；非法负载统一 DROP_INVALID
- 体验：ACK P95 ≤ 3s；限频在压测场景能看到 qps=limited，但正常互动不受影响

如果同意，我可以把“状态表（状态、触发事件、允许指令、下一步）”再细化为一张简单清单，便于后端一次到位实现所有模式的状态骨架，同时优先把对话路径跑通。

---

**User**

很好, 现在把我们现在敲定的阶段2的设计放入build.md@build.md 中 (只包括最核心改动)  
同时把“状态表（状态、触发事件、允许指令、下一步）”再细化为一张简单清单和对后端的具体任务安排也放入build.md中

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

## 2. 后端核心原则（Fail-Closed 安全编排，必须执行）(阶段1出现核心问题)

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


## 3. 阶段2 目标（对话最小闭环）

- 核心改动（仅保留最关键）
  - 唤醒后才渲染：连接/hello 阶段不发送任何 `ui.render`；收到“唤醒”再开始渲染与控制。
  - 状态机落地（每设备）：`connected(idle) → dialog.preparing → dialog.active`。
  - 直达 to 白名单按“目标设备 currentMode”放行：仅 `ui.render(page==dialog.chat)` 与 `device.control(net.banner|play.tone)`。
  - 对话链路打通：ASR（听）→ LLM（懂）→ TTS（说，按帧下发音频），必要时同时下发简短 `ui.render` 提示。
  - 底线已具备（无需重复开发）：渲染清洗与限幅、限频与丢弃、统一日志（SEND/ACK/DROP_* /REDELIVER）。

- 对话模式状态表（简版）

| 状态 | 触发事件 | 允许指令（白名单） | 下一步 |
| --- | --- | --- | --- |
| connected(idle) | onConnect/onHello | 不渲染；可选 `device.control: net.banner` | 收到 `mode.start(dialog)` 或 `listen.start` → dialog.preparing |
| dialog.preparing | `mode.start(dialog)` 或 `listen.start`；`listen.detect`（仅提示） | `ui.render: dialog.chat`（提示页，如 id=dlg-listen-start / dlg-ready）；`device.control: play.tone | net.banner` | 进入 dialog.active（编排切换） |
| dialog.active | 编排切换到 active | `ui.render: dialog.chat`；`device.control: net.banner | play.tone`；（对话链路 ASR→LLM→TTS） | 保持 active 或 `mode.end(dialog)` → connected(idle) |

- 后端任务安排（可执行）
  1) 状态机字段与跳转（ConnectionHandler 内存即可）
     - 新增并维护 `currentMode`（默认为 connected(idle)）。
     - 事件接入：`mode.start(dialog)` / `listen.start` → set dialog.preparing；`listen.detect` → 保持 preparing 并发送“准备聆听”提示页；编排切换 → set dialog.active。
  2) 事件编排与渲染
     - dialog.preparing：下发“建立连接/请稍候”（`ui.render:text`，id=dlg-listen-start）+ `device.control: play.tone`；收到 `listen.detect` 时下发“准备聆听”（id=dlg-ready）。
     - dialog.active：下发“开始对话”（`ui.render:text`）。
  3) 直达 to 白名单（textHandle 转发入口）
     - 仅当“目标设备”的 `currentMode ∈ {dialog.preparing, dialog.active}` 时放行：`ui.render(page==dialog.chat)` 与 `device.control(net.banner|play.tone)`；否则 `[DROP_BY_MODE]`。
  4) 对话链路（最小闭环）
     - ASR：接入现有 provider，拿到识别文本（允许分段/最终）。
     - LLM：将识别文本交给 LLM，生成回复文本。
     - TTS：将回复文本合成语音，按帧下发到设备播放；无 TTS 时可先仅下发 `ui.render:text`。
  5) 验收口径
     - 流程顺序正确：connected(idle)（不渲染）→ dialog.preparing（请稍候+提示音/准备聆听）→ dialog.active（开始对话）。
     - 指令只在白名单内放行；ACK P95 ≤ 3s；限频在压测用例可见。

```

已将阶段2的最核心设计写入 `collaboration/build.md`，包括：
- 核心改动（唤醒后才渲染、三态状态机、按目标设备模式放行直达 to、ASR→LLM→TTS 对话闭环）
- “状态表（状态/触发/允许指令/下一步）”简明清单
- 后端具体任务安排（状态机与跳转、事件编排、白名单、对话链路、验收口径）

可按此直接开工阶段2。

---

**User**

为什么给我 对话模式状态表的简版? 我需要详细全面的表格

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

## 2. 后端核心原则（Fail-Closed 安全编排，必须执行）(阶段1出现核心问题)

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


## 3. 阶段2 目标（对话最小闭环）

- 核心改动（仅保留最关键）
  - 唤醒后才渲染：连接/hello 阶段不发送任何 `ui.render`；收到“唤醒”再开始渲染与控制。
  - 状态机落地（每设备）：`connected(idle) → dialog.preparing → dialog.active`。
  - 直达 to 白名单按“目标设备 currentMode”放行：仅 `ui.render(page==dialog.chat)` 与 `device.control(net.banner|play.tone)`。
  - 对话链路打通：ASR（听）→ LLM（懂）→ TTS（说，按帧下发音频），必要时同时下发简短 `ui.render` 提示。
  - 底线已具备（无需重复开发）：渲染清洗与限幅、限频与丢弃、统一日志（SEND/ACK/DROP_* /REDELIVER）。

- 对话模式状态表（详版）

| 状态 | 进入条件/入口事件 | 允许下发（ui.render） | 允许下发（device.control） | 直达 `to` 放行 | 上行接受（设备→后端） | 出口/转移条件 | 出错处理/降级 | 关键日志 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| connected(idle) | onConnect/onHello；硬件本地欢迎页 | 无（不渲染） | 仅允许 `net.banner`（可选） | 否（除 `net.banner` 外一律 DROP） | hello/server.stats | 收到 `mode.start(dialog)` 或 `listen.start` → dialog.preparing | 非白名单 `ui.render` → `[DROP_BY_MODE]` | SEND/ACK（仅控制）；DROP_BY_MODE |
| dialog.preparing | `mode.start(dialog)` 或 `listen.start`；`listen.detect` 仅提示 | `dialog.chat`：提示页（id=dlg-listen-start/ dlg-ready）；text≤200/ list≤8 | `play.tone`、`net.banner` | 是（仅放行 `dialog.chat` 和 `play.tone|net.banner`） | `listen.detect`、`ui.ack/ui.error` | 编排切换 → dialog.active | schema/限幅失败 → `[DROP_INVALID]`；越权 → `[DROP_BY_MODE]` | SEND/ACK；DROP_INVALID；DROP_BY_MODE |
| dialog.active | 编排切换到 active | `dialog.chat`：对话页/进行中提示 | `net.banner`、`play.tone`；TTS 音频帧（按帧下发） | 是（同上） | ASR 片段（文本/音频）、`ui.ack/ui.error`、TTS 回执（可选） | `mode.end(dialog)` → connected(idle) | ASR/LLM/TTS 异常：下发简短 text 提示并记录错误；超时则限重试/熔断 | SEND/ACK；RATE_LIMITED；REDELIVER(显式) |

- 事件 → 转移规则（详版）

| 事件 | 当前状态 | 动作（下发/记录） | 新状态 |
| --- | --- | --- | --- |
| onConnect/onHello | 任意 | 记录 `connected(idle)`；不渲染 | connected(idle) |
| mode.start(dialog) | connected(idle) | 下发 `ui.render:text(id=dlg-listen-start, “请稍候…”)` + `device.control: play.tone` | dialog.preparing |
| listen.start | connected(idle) | 同上 | dialog.preparing |
| listen.detect | dialog.preparing | 下发 `ui.render:text(id=dlg-ready, “准备聆听…”)` | dialog.preparing |
| 编排切换（开始对话） | dialog.preparing | 下发 `ui.render:text(开始对话)` | dialog.active |
| asr.partial/final | dialog.active | 投喂 LLM（必要时先 `ui.render` “正在回答…”） | dialog.active |
| llm.reply | dialog.active | 触发 TTS 合成并按帧下发；可并发 `ui.render` 简短文本 | dialog.active |
| tts.finished | dialog.active | 无需转移（保持） | dialog.active |
| mode.end(dialog) | dialog.preparing/active | 记录并回归 idle（不渲染） | connected(idle) |
| disconnect | 任意 | 释放会话状态 | 无（等待重连） |

- 直达 `to` 白名单矩阵（详版）

| 目标设备 `currentMode` | 允许 `ui.render` | 允许 `device.control` | 说明 |
| --- | --- | --- | --- |
| connected(idle) | 否 | 仅 `net.banner`（可选） | 避免覆盖硬件本地欢迎页 |
| dialog.preparing | 仅 `page==dialog.chat` | `net.banner`、`play.tone` | 仅提示类/准备类内容 |
| dialog.active | 仅 `page==dialog.chat` | `net.banner`、`play.tone`、（TTS 帧按音频通道） | 对话页与提示 |

- 对话链路（ASR→LLM→TTS）与网关
  - ASR：接收音频/文本→识别（支持 partial/final）→进入 LLM；异常：记录并下发 `ui.render:text(抱歉，暂时听不清…)`。
  - LLM：接收识别文本→生成回复；超时/失败：记录并下发 `ui.render:text(稍后再试…)`。
  - TTS：将回复文本合成→按帧下发音频；若 TTS 不可用，可先仅 `ui.render:text` 回复。
  - 速率：每设备渲染≤2 QPS；音频帧独立通道；直达消息按白名单网关过滤。

- 日志与验收（阶段2）
  - 全程出现成对 `[SEND]/[ACK]`；非法/越权→`[DROP_INVALID]/[DROP_BY_MODE]`；压测可见 `rate-limited`。
  - 验收顺序：connected(idle)(不渲染) → dialog.preparing(请稍候+提示音/准备聆听) → dialog.active(开始对话) → 对话（ASR→LLM→TTS）。

- 后端任务安排（可执行）
  1) 状态机字段与跳转（ConnectionHandler 内存即可）
     - 新增并维护 `currentMode`（默认为 connected(idle)）。
     - 事件接入：`mode.start(dialog)` / `listen.start` → set dialog.preparing；`listen.detect` → 保持 preparing 并发送“准备聆听”提示页；编排切换 → set dialog.active。
  2) 事件编排与渲染
     - dialog.preparing：下发“建立连接/请稍候”（`ui.render:text`，id=dlg-listen-start）+ `device.control: play.tone`；收到 `listen.detect` 时下发“准备聆听”（id=dlg-ready）。
     - dialog.active：下发“开始对话”（`ui.render:text`）。
  3) 直达 to 白名单（textHandle 转发入口）
     - 仅当“目标设备”的 `currentMode ∈ {dialog.preparing, dialog.active}` 时放行：`ui.render(page==dialog.chat)` 与 `device.control(net.banner|play.tone)`；否则 `[DROP_BY_MODE]`。
  4) 对话链路（最小闭环）
     - ASR：接入现有 provider，拿到识别文本（允许分段/最终）。
     - LLM：将识别文本交给 LLM，生成回复文本。
     - TTS：将回复文本合成语音，按帧下发到设备播放；无 TTS 时可先仅下发 `ui.render:text`。
  5) 验收口径
     - 流程顺序正确：connected(idle)（不渲染）→ dialog.preparing（请稍候+提示音/准备聆听）→ dialog.active（开始对话）。
     - 指令只在白名单内放行；ACK P95 ≤ 3s；限频在压测用例可见。

```

已将“对话模式状态表（详版）”与“事件→转移规则”“直达 to 白名单矩阵（详版）”“对话链路与验收”补充到 `collaboration/build.md`，覆盖：
- 每个状态的入口、允许指令、上行、出口、出错降级与关键日志
- 事件到状态的转换清单（包含 listen.start/detect、编排切换、ASR/LLM/TTS 关键点）
- 目标设备按 currentMode 的直达放行矩阵
- 对话链路异常兜底与阶段2验收口径

可据此直接实现与联调阶段2。

