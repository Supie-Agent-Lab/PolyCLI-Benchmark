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

