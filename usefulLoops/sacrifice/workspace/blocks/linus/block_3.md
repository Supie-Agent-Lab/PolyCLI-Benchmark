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

