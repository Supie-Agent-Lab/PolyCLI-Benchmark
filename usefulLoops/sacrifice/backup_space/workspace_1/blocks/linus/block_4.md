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


