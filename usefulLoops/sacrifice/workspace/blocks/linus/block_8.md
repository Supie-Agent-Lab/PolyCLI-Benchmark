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

