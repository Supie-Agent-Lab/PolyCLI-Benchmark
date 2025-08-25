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

