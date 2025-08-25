---

**Cursor**

```yaml
devices:
  "94:a9:90:07:9d:88":
    badge: "001"
    owner: "文先生"
    group: "硬件部"
  "80:b5:4e:ee:cb:60":
    badge: "002"
    owner: "彭先生"
    group: "硬件部"
  "d0:cf:13:25:02:7c":
    badge: "003"
    owner: "邓先生"
    group: "硬件部"
  "a2:1b:3c:4d:5e:6f":
    badge: "004"
    owner: "刘先生"
    group: "研发部"
  "aa:bb:cc:dd:ee:01":
    badge: "005"
    owner: "赵女士"
    group: "研发部"
  "de:ad:be:ef:00:11":
    badge: "006"
    owner: "陈先生"
    group: "生态部"
  "12:34:56:78:9a:bc":
    badge: "007"
    owner: "孙女士"
    group: "生态部"
  "fe:ed:fa:ce:10:20":
    badge: "008"
    owner: "王博士"
    group: "算法部"
  "0a:1b:2c:3d:4e:5f":
    badge: "009"
    owner: "周先生"
    group: "算法部"


```

已为 `backend/data/devices.yaml` 增加“组”字段，并随机新增若干设备与持有人，分别归入硬件部/研发部/生态部/算法部：
```yaml
devices:
  "94:a9:90:07:9d:88": { badge: "001", owner: "文先生", group: "硬件部" }
  "80:b5:4e:ee:cb:60": { badge: "002", owner: "彭先生", group: "硬件部" }
  "d0:cf:13:25:02:7c": { badge: "003", owner: "邓先生", group: "硬件部" }

  "a2:1b:3c:4d:5e:6f": { badge: "004", owner: "刘先生", group: "研发部" }
  "aa:bb:cc:dd:ee:01": { badge: "005", owner: "赵女士", group: "研发部" }

  "de:ad:be:ef:00:11": { badge: "006", owner: "陈先生", group: "生态部" }
  "12:34:56:78:9a:bc": { badge: "007", owner: "孙女士", group: "生态部" }

  "fe:ed:fa:ce:10:20": { badge: "008", owner: "王博士", group: "算法部" }
  "0a:1b:2c:3d:4e:5f": { badge: "009", owner: "周先生", group: "算法部" }
```

说明：
- 渲染时仍仅显示“工牌编号 + 持有人”，不显示 MAC；组字段可用于后端编排做分组广播或统计（非必显）。
- 找不到映射时：UI不显示任何设备标识，仅在后端日志提示“未注册设备”。

```yaml
devices:
  "94:a9:90:07:9d:88": { badge: "001", owner: "文先生", group: "硬件部" }
  "80:b5:4e:ee:cb:60": { badge: "002", owner: "彭先生", group: "硬件部" }
  "d0:cf:13:25:02:7c": { badge: "003", owner: "邓先生", group: "硬件部" }

  "a2:1b:3c:4d:5e:6f": { badge: "004", owner: "刘先生", group: "研发部" }
  "aa:bb:cc:dd:ee:01": { badge: "005", owner: "赵女士", group: "研发部" }

  "de:ad:be:ef:00:11": { badge: "006", owner: "陈先生", group: "生态部" }
  "12:34:56:78:9a:bc": { badge: "007", owner: "孙女士", group: "生态部" }

  "fe:ed:fa:ce:10:20": { badge: "008", owner: "王博士", group: "算法部" }
  "0a:1b:2c:3d:4e:5f": { badge: "009", owner: "周先生", group: "算法部" }
```

---

**User**

好的现在请给我详细的执行步骤和执行方案 我们准备开始工作了

“硬件（p）
新建 EinkRenderEngine::{Init, Render, DrawHeader, DrawBody, DrawFooter}（三分区，整屏+节流）。
application.cc 增加 HandleUiRender/HandleDeviceControl 与 ACK 发送；listen.start/stop 驱动音频推流。
后端（w+d）
新建 render_schema.py（校验/清洗）、render_sender.py（限频+最后渲染缓存）、render_orchestrator.py（welcome/meeting.enter/finalize_ack/summary/working.list/coding.log）。
websocket_server 注册成功后补投“最后渲染”；textHandle 调 orchestrator。
准备最小联调脚本/页面下发示例载荷。”

---

**Cursor**

### 结论
- 可以开工。按下列步骤，硬件与后端可并行推进，D1 即可看到“欢迎/会议聆听页+开始录音”的端到端效果，D2 覆盖四类页面，D3 完成稳健化与一键演示。
- 设备展示只用“工牌编号+持有人”，缺失映射时不显示任何设备标识，仅在后端日志提示“未注册设备”。

### 执行方案（按优先级与顺序）

- 硬约定（全员先确认）
  - 渲染协议：以 build.md 的“渲染协议契约 v1”为唯一对齐源。
  - 设备映射：`backend/data/devices.yaml` 已建立；渲染时仅注入 `badge/owner`，不显示 MAC；无映射仅日志提示。
  - 限频：每设备渲染 ≤2 QPS；设备端整屏渲染合并节流 ≥500ms。
  - 补投：设备注册成功/hello 后，仅补投“最后一次渲染”快照。

——

## Day 1（打通骨架与最小闭环）

- 硬件（p）
  - 新建 `hardware/main/display/eink_render_engine.h/.cc`
    - 接口：`EinkRenderEngine::Init(EinkDisplayST7306*)`、`Render(RenderPayload)`、`DrawHeader/DrawBody/DrawFooter`
    - 策略：头/体/脚三分区渲染；当前先整屏刷新；500ms 合并节流；UTF‑8 安全截断；列表/日志每页≤8条
  - 改造 `hardware/main/application.cc`
    - 路由：新增 `HandleUiRender(const cJSON*)`、`HandleDeviceControl(const cJSON*)`
    - ACK：若下行带 `id`，渲染/执行完成后发送 `{type:"ui.ack", id, status:"ok"}`
    - 设备控制：`listen.start` 开启音频推流（启动 `audio_processor_`/OPUS）；`listen.stop` 停止推流；`play.tone/tts/page.next/prev` 最小实现
    - 保留旧逻辑但默认走新路径（加一个运行时开关便于回退）
  - 可见成果：设备上能显示“欢迎/会议聆听”两页，并能响应“开始录音/停止录音”

- 后端（w+d）
  - 新增 `backend/core/orchestration/render_schema.py`
    - 输入清洗：校验 `type/page/header/body/footer/regionsChanged/id/ts`，裁剪无效值，给默认值
  - 新增 `backend/core/utils/last_render_cache.py`
    - 内存缓存：`set_last(device_id, payload)`、`get_last(device_id)`，可加简单 TTL（可选）
  - 新增 `backend/core/orchestration/render_sender.py`
    - 限频与发送：每设备 2 QPS；超过则丢弃队首旧帧，保留最新；统一 `send_render(conn, payload)`、`send_control(conn, action, **kw)`
    - 每次渲染前调用 schema 校验/清洗；发送后更新 `last_render_cache`
  - 新增 `backend/core/orchestration/render_orchestrator.py`
    - 读取设备映射：加载 `backend/data/devices.yaml`（启动加载+热更可后续加）
    - 页面编排：
      - `show_welcome(conn)`：header 标题“工牌{badge} · {owner}”；body 提示“正在连接…”；不显示 MAC
      - `meeting_enter(conn)`：render `meeting.listen` + control `listen.start`
      - `meeting_finalize_ack(conn)`：control `listen.stop` + render 占位“总结中…”
      - `meeting_show_summary(conn, summary)`：render `meeting.summary`（bullets 2~6 条）
      - `working_show_list(conn, tasks, page=1)`：render `working.list`（≤8/页，页脚页码）
      - `coding_show_log(conn, lines, phase)`：render `coding.log`（滚动窗口≤8行）
    - 显示文案仅注入 `badge/owner`；无映射只打印“未注册设备:<mac>”，文案不显示任何标识
  - 集成点
    - `backend/core/websocket_server.py`：设备注册成功后查询 `last_render_cache`，如有→补发一次
    - `backend/core/handle/textHandle.py`：`mode.start(meeting)` → `meeting_enter`；`meeting.finalize` → `meeting_finalize_ack`，待总结完成后 `meeting_show_summary`
  - 联调脚本/页面（最小）
    - 准备 `test/ws_render_demo.html` 或 `test/demo_render.py`（不依赖后端业务，仅对指定 device-id 下发示例载荷，验证渲染/ACK）

- D1 验收
  - 设备上电后显示欢迎页；一键切“会议聆听”并能开始/停止录音
  - 渲染 ACK 正确；断连重连后补投“最后一次渲染”

——

## Day 2（覆盖四类页面 + 并发/离线）

- 硬件（p）
  - `EinkRenderEngine` 完善：列表分页（8/页）、页脚“第x/共y页”、日志滚动窗口、整屏节流与重复渲染去抖
  - 断连/重连提示横幅：收到 `net.banner` 时显示 2~3s；重连后主动请求一次当前页重绘（可由后端补投覆盖）

- 后端（w+d）
  - 会议：串联后端现有总结流程，完成 `meeting_show_summary` 页面；summary 为空也能输出“空骨架”
  - 工作：`working_show_list` 输入≥12个任务时验证分页；从任意模式切换到工作页渲染正确
  - 编码：`coding_show_log` 模拟 6~8 条日志滚动与 `phase` 提示
  - 并发与离线
    - 使用 10+ 连接（真实/模拟混合）验证限频与稳定性
    - 3 台设备互动：A 发控制，B/C 同步接收渲染；断开 B，再重连触发“最后渲染”补投

- D2 验收
  - 四类页面（welcome/dialog.chat/meeting.listen/meeting.summary/working.list/coding.log）均能通过 `ui.render` 正确显示
  - 并发≥10 稳定；三台互动无异常；离线重连补投可见

——

## Day 3（稳健化与一键演示）

- 硬件（p）
  - 分区签名：对 header/body/footer 做内容哈希，未变化不重绘（仍保留整屏节流上限）
  - `ui.error`：渲染/控制失败上报标准错误码（如 RATE_LIMITED/DISPLAY_FAILURE/AUDIO_FAILURE）

- 后端（w+d）
  - Token 鉴权中间件（WS/HTTP 同源）：内网演示下仍建议启用
  - 一键演示：`/supie/demo/flow` 或脚本触发“对话→会议→纪要→工作→编码”的全链路
  - 观测日志：ACK 耗时、限频丢弃计数、未注册设备告警

- D3 验收
  - 一键演示跑通；错误路径友好（`ui.error` 可见）；回滚生效（关闭 `render.enabled` + 硬件切回旧渲染）

——

## 实施细节与注意点

- 文件与接口对齐（硬件）
  - `eink_render_engine.h/.cc`：暴露 `Init/Render/DrawHeader/DrawBody/DrawFooter`
  - `application.cc`：在 `OnIncomingJson` 中仅保留两类入口；ACK 统一函数 `SendAckIfHasId(id)`
  - 控制映射：`listen.start/stop` → 音频推流管理；`play.tone/tts` → 本地提示音优先；`page.next/prev` → 翻页并触发渲染

- 文件与接口对齐（后端）
  - `render_schema.py`：输入清洗函数（保证设备端不会收到坏字段/坏类型）
  - `last_render_cache.py`：线程安全简单即可（演示期不必持久化）
  - `render_sender.py`：限频、发送、缓存三合一；提供 `send_render/send_control`
  - `render_orchestrator.py`：读取 `devices.yaml`，生成“工牌{badge} · {owner}”标题；缺映射仅日志，不显示标识

- 测试与联调建议
  - 真实设备优先，搭配 2~3 个浏览器/脚本模拟连接做高并发
  - 观测点：整屏刷新频次（肉眼观感）、ACK 时延（日志）、限频丢弃计数、离线补投命中率

- 回滚与安全阀
  - 后端：`render.enabled=false` 立即停止下发渲染；可仅下发 `net.banner` 提示
  - 硬件：运行时开关切回“旧渲染路径”；遇到 `ui.render` 可直接忽略并本地显示静态页面

——

## 今日行动列表（可直接执行）

- 硬件（p）
  - 创建 `eink_render_engine.h/.cc`，在 `application.cc` 接上 `HandleUiRender/HandleDeviceControl` 与 ACK
  - 渲染“欢迎/会议聆听”页，打通 `listen.start/stop`；节流≥500ms

- 后端（w+d）
  - 创建 `render_schema.py/last_render_cache.py/render_sender.py/render_orchestrator.py`
  - `websocket_server` 注册成功后补投“最后渲染”；`textHandle` 调用 orchestrator
  - 准备 `test/ws_render_demo.html` 或 `demo_render.py` 下发 `welcome/meeting.listen/working.list/coding.log` 示例载荷

- 验收点（今天）
  - 一台设备：欢迎→会议聆听（开始/停止录音）+ ACK
  - 断连重连：收到“最后渲染”补投并正确显示

需要我把“最小页面示例 JSON（欢迎/会议/工作/编码）”再按设备编号/持有人注入策略（从 devices.yaml 读取）整理成一组可直接发送的样例吗？

---

**User**

我们需要再次讨论一下硬件工程师的任务- 首先需要遵循一个原则 - 只确保核心功能的实现 ,不需要做任何增加硬件复杂度的任务 
所以现在不需要能显示会议聆听页面 - 我只需要能保证硬件能和后端正常通信,接收到后端指令后能正确渲染即可

所以我认为现在需要做到的流程是在结合全流程演示的情况下 @全流程演示.md  保留开机动画和欢迎页面,然后唤醒后直接进入一个页面接受后端发送的消息,来测试硬件引擎是否正常工作;

这是第一天需要实现的内容

请基于我的判断,再次给出工作安排和详细计划

---

**Cursor**

### 原则
- 只做核心：能连后端、能收指令、能按指令渲染并回 ACK。先不做会议聆听页、不做复杂分页/局刷/日志滚动。

### Day 1 工作安排（硬件 p）
- 目标：上电→开机动画→欢迎页；唤醒后进入“渲染测试页”；收到 `ui.render/device.control` 后正确渲染/执行，并回 `ui.ack`。
- 不做：会议聆听/总结页、分页/日志滚动、局部刷新、任务列表等复杂 UI。
- 实施步骤
  1) 开关与页面
     - 运行时开关：`RENDER_LITE_D1=true`（默认启用新路径，可随时回退旧逻辑）。
     - 保留开机动画与欢迎页；新增“渲染测试页”（固定文案：例如“等待后端指令…”）。
  2) JSON 路由（仅两类）
     - `ui.render` → 解析 `page/header.title/body(kind=text|list)/footer.hint` 四项，其他字段忽略；调用简易渲染函数。
     - `device.control` → 先支持 `net.banner`（在顶部显示3秒提示条）；其他 action 先忽略并回 ACK（占位）。
  3) ACK 标准
     - 若消息含 `id`，渲染或执行完成后发送 `{type:"ui.ack", id, status:"ok"}`；解析失败发 `{type:"ui.error", code:"INVALID_PAYLOAD"}`。
  4) 简易渲染函数（轻量，不建复杂引擎）
     - `RenderLite(headerTitle, bodyTextOrList, footerHint)`：整屏刷新+≥500ms 合并节流；UTF‑8 安全截断；list ≤8行。
  5) 唤醒入口
     - 唤醒（按键/唤醒词）后切到“渲染测试页”，并保持 WebSocket 已连接状态。
  6) 日志
     - 打印 `[UI_LITE] recv type/id/page`、`[UI_LITE] render ok`、`[UI_LITE] ack sent`、`[UI_LITE] error code=...`。

### Day 1 工作安排（后端 w+d）
- 目标：能向指定设备发送最小 `ui.render` 与 `device.control`，并收到 `ui.ack`；设备重连后自动补投“最后一次渲染”。
- 实施步骤
  1) 设备映射：已在 `backend/data/devices.yaml`；编排时注入“工牌{badge} · {owner}”（不显示 MAC）。
  2) 发送器（轻量版）
     - `render_sender.py`：`send_render(conn, payload)` → 限频每设备≤2 QPS；更新 `last_render_cache`（内存）。
     - `send_control(conn, action, **kw)` → 下发 `net.banner` 用于验证。
  3) 补投
     - `websocket_server` 注册成功后，若有 `last_render_cache` → 自动补发一次。
  4) 最小编排
     - 连接后调用一次 `show_welcome(conn)` → 下发欢迎文案（仅标题/正文/底部提示）。
     - 测试脚本/页面：一键向目标设备发送渲染与横幅指令，观察 ACK。

### 最小测试载荷（用于联调）
- 渲染文本
```json
{ "type":"ui.render","id":"d1-001","page":"dialog.chat",
  "header":{"title":"工牌001 · 文先生"},
  "body":{"kind":"text","text":"Hello 渲染测试"},
  "footer":{"hint":"后端→设备 OK"} }
```
- 渲染列表
```json
{ "type":"ui.render","id":"d1-002","page":"dialog.chat",
  "header":{"title":"工牌001 · 文先生"},
  "body":{"kind":"list","items":["第一行","第二行","第三行"]},
  "footer":{"hint":"最多显示8行"} }
```
- 顶部横幅（3秒）
```json
{ "type":"device.control","id":"d1-003","action":"net.banner",
  "text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
```

### 联调流程（10分钟内）
1) 设备烧录运行（`RENDER_LITE_D1=true`），观察：开机动画→欢迎页→唤醒→“渲染测试页（等待后端指令…）”。
2) 连接后端，后端下发欢迎 `ui.render`；设备≤1s 内渲染并回 `ui.ack`。
3) 下发列表 `ui.render`；设备更新正文并回 `ui.ack`。
4) 下发 `net.banner`；设备顶部显示3秒提示条并回 `ui.ack`。
5) 断开设备网络→重连；后端自动补投“最后一次渲染”，设备恢复显示。

### 验收标准（Day 1）
- 能稳定接入后端；`ui.render/device.control` 按示例渲染/执行；每次含 `id` 的消息均回 `ui.ack`。
- 整屏刷新合并节流≥500ms；文本/列表能正确显示（列表≤8行，UTF‑8 截断无乱码）。
- 重连补投生效；日志包含收发与 ACK 关键行。
- 不展示 MAC；找不到映射也不展示任何设备标识，仅后端日志提示“未注册设备”。

### 回退与风险
- 回退：关闭 `RENDER_LITE_D1` 切回旧路径；后端可 `render.enabled=false` 停止下发渲染。
- 风险与对策：
  - 字段不全或类型错误 → 设备发 `ui.error: INVALID_PAYLOAD`，后端日志定位。
  - 刷新抖动 → 保持节流≥500ms；同内容不重绘（可用简单内容签名在 D2 再加）。

这样安排能在 Day 1 最小代价验证“通信→渲染→ACK→补投”，为后续模式页与复杂 UI 打基础。

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

---

**User**

回 ACK是什么意思

---

**Cursor**

### 简单说
“回 ACK”= 回确认。设备在“收到一条指令并处理完成后”，发一条确认消息给后端，表示“这条事办好了”。

### 用途
- 让后端知道哪条指令（通过 id）已成功执行，便于结束等待或停止重试。
- 若失败则回错误而不是 ACK（便于定位问题）。

### 何时回
- 收到带有 `id` 的 `ui.render` 或 `device.control`，完成渲染/动作后（建议≤5秒）回 ACK。

### 长什么样
- 成功：
```json
{ "type": "ui.ack", "id": "d1-001", "status": "ok" }
```
- 失败（不回 ACK，回错误）：
```json
{ "type": "ui.error", "id": "d1-001", "code": "INVALID_PAYLOAD", "message": "字段缺失" }
```

```json
{ "type": "ui.ack", "id": "d1-001", "status": "ok" }
```

```json
{ "type": "ui.error", "id": "d1-001", "code": "INVALID_PAYLOAD", "message": "字段缺失" }
```

---

**User**

我没看懂什么叫做运行时开关：RENDER_LITE_D1=true（默认启用新路径，可随时回退旧逻辑） 请用高中生能听懂的方式解释给我

---

**Cursor**

### 容易理解的解释
- 把它当作一个“开/关按钮”。ON（true）= 走“新渲染路径”；OFF（false）= 回到“旧逻辑”。
- “运行时”意思是：不改代码、不重编译，也能随时切换（比如读配置、按键切换、重启后生效）。

### 它的作用
- 新功能如果有问题，关掉开关就能迅速回退到旧逻辑，保证设备可用。
- 新逻辑稳定后，再把开关一直保持 ON。

### 代码里的样子（示意）
- 程序每次收到消息时，先看这个开关是 true 还是 false，然后决定走哪条路：
- true → 用新引擎渲染；false → 用旧的显示代码。

### 怎么设置（今天的最低成本做法）
- Day 1：默认设为 true（直接启用新路径）。
- 稍后可加两种实用切换方式（仍不改协议、不加复杂度）：
  - 在设备本地设置里存一个布尔值（NVS/Settings），开关写入后“重启生效”。
  - 预留一个按键组合（如长按3秒）切换开/关，并保存到设置里，下次开机沿用。

---

**User**

程序每次收到消息时，先看这个开关是 true 还是 false? 指的是哪个程序? 后端还是硬件端?

---

**Cursor**

- 是硬件端的开关（固件里的布尔量），不是后端。
- 触发点：设备收到 WebSocket 消息时（如 `application.cc::OnIncomingJson`），先读该开关。
  - 为 true：走新路径 → `HandleUiRender/HandleDeviceControl` →（简易）渲染引擎 → 回 ACK。
  - 为 false：走旧逻辑（忽略新协议渲染），保持原有页面流程。
- 后端可另有 `render.enabled`（是否下发渲染指令）的服务端开关，但与本硬件开关不同、互不替代。
- 设置方式建议：设备本地设置（NVS）或按键组合切换；开机读取，运行期可切换（重启或即时生效视实现而定）。

---

**User**

完全没有必要要这个东西好吗 没有任何意义 还增加了硬件的复杂度

---

**Cursor**

明白，不加任何“运行时开关”。新路径直接生效，尽量少文件、少分支、少状态。

### 原则（精简版）
- 仅做核心：能连后端、能收指令、能渲染、能回 ACK。
- Day 1 不做会议聆听/分页/局部刷新/日志滚动等复杂功能。
- 协议只实现 `ui.render`（text/list）与 `device.control: net.banner`，其余先忽略。

### 硬件（p）Day 1 执行
- 必做
  - 保留开机动画与欢迎页；唤醒后切到“渲染测试页（文案固定：等待后端指令…）”。
  - 在 `application.cc::OnIncomingJson` 只保留两类处理：
    - `ui.render`：解析 `header.title`、`body.kind in [text,list]`、`footer.hint`、`id?`；其他字段一律忽略。
    - `device.control: net.banner`：顶部画一条提示（默认3秒），其他 `action` 暂忽略。
  - 渲染函数（直接写在 `application.cc`，不新建类/文件）：
    - `RenderHeaderBodyFooter(title, body_text_or_list, hint)`：整屏刷新；≥500ms 合并节流；UTF‑8 截断；list ≤8行。
  - ACK：
    - 若收到的 JSON 带 `id`，渲染/执行完成后回 `{type:"ui.ack", id, status:"ok"}`；解析失败回 `{type:"ui.error", code:"INVALID_PAYLOAD"}`。
- 不做
  - 不新建 `EinkRenderEngine` 文件、不做局部刷新、不连动音频推流（listen.start/stop 暂不实现）。
- 验收
  - 上电→欢迎→唤醒→渲染测试页；
  - 后端发 `ui.render`/`device.control(net.banner)`，设备正确显示并回 ACK；
  - 断开→重连后端补投最后一帧，设备恢复显示。

### 后端（w+d）Day 1 执行
- 必做
  - 发送器（轻量版）：`render_sender.py`
    - `send_render(conn, payload)`：校验最小字段、每设备≤2 QPS、更新内存 `last_render_cache`；
    - `send_control(conn, action="net.banner", ...)`。
  - `websocket_server`：设备注册成功后，如有 `last_render_cache` → 自动补投。
  - 编排最小化：连接后发一次欢迎 `ui.render`；测试页/脚本可发三条载荷（text、list、net.banner）。
  - 从 `backend/data/devices.yaml` 取 `badge/owner` 注入标题，仅此，不显示 MAC；缺映射则标题用“工牌未知”（同时日志：未注册设备）。
- 不做
  - 不改业务流程、不接入 ASR/LLM、不做多页面编排。
- 验收
  - 能向目标设备发三种最小载荷并收到 ACK；
  - 重连后看到“最后一次渲染”的补投。

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

### 时间分配（当日）
- p：实现解析+渲染函数+ACK（4h），唤醒切页与整屏节流（2h），联调与日志（2h）。
- w+d：sender+cache+补投（3h），测试脚本/页面（2h），对接设备映射注入标题（1h），联调（2h）。

若同意，我按此口径继续准备后端最小 `render_sender.py`/缓存与示例脚本说明；硬件只改 `application.cc` 单文件即可。

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

