---

**Cursor**

## 1. 现有架构评估 (As-Is Assessment)

### 优点 (Pros)
- **前后端分层清晰**：传输层（WebSocket/MQTT+UDP）与应用状态机（`hardware/main/application.cc`）解耦；显示/UI集中在 `EinkDisplayST7306`。（来源：`collaboration/index.md` L41-L44）
- **板级封装稳定**：4.2" ST7306 BWR 板级抽象与显示/按键行为已固化，具备调试序列、分页、去抖和状态栏统一风格。（来源：`collaboration/index.md` L12-L18；`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 25/32/53/60/61/63）
- **会议闭环完善**：片段累计→节流→总结→存档→查询 API（Recent/Detail/Transcript）→Webhook，幂等/并发/清洗与限幅齐全。（来源：`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 8/30/34/38/43/48/50/54/57/58/62）
- **可靠通信与可观测**：握手修复、设备路由、踢旧迎新、`server.stats` 周期/事件广播、端到端诊断日志完善。（来源：`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 3/4/10/35）
- **工作流与协同能力**：内存+JSON 任务库、字段级更新、分组广播、查询/导入自会议、assign/complete 幂等与快照单播。（来源：`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 27/28/64/65）
- **LLM 按用途选型**：按模式/用途动态选择与缓存 LLM，支持热更与降级回退。（来源：`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 46/51）
- **测试与联调工具链**：双页/模拟器/会议专项页面、自动化脚本、离线补投/别名学习、断言丰富。（来源：`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 5/12/14/18/23/42/47/55/56/66）

### 缺点与挑战 (Cons & Challenges)
- **应用主循环耦合偏高**：`application.cc` 混合音频/显示/状态/协议多职责，扩展与并发边界风险大。（来源：`collaboration/index.md` L48-L55）
- **显示刷新成本高**：ST7306 实现以全屏写为主，缺少“真实窗口化的局部刷新/瓦片更新”，影响性能/寿命。（来源：`collaboration/index.md` L47/L58-L66）
- **存储层分散且以 JSON 为主**：离线 peer 队列/会议索引/任务库均为文件存储（虽已做原子/分片/清理），并发一致性与检索扩展受限。（来源：`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 15/38/50/58/64）
- **安全与限流策略仍偏基础**：WS 鉴权对齐度、ACL/频控/配额在多处实现但未形成统一策略中心。（来源：`collaboration/index.md` L49；`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 35/58）
- **环境耦合**：测试/工具默认固定 LAN 地址（`192.168.0.94`），迁移/CI 体验一般。（来源：`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 5/12）
- **混合线程/协程模型**：连接级线程池与异步事件混用，虽已缩减与可配，但边界需持续保护。（来源：`collaboration/index.md` L50；`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 44/57）


## 2. 需求合理性与影响分析 (Requirement & Impact Analysis)

- **业务目标与新需求**
  - **稳定的会议纪要链路**：更快、更稳的转写与总结，可靠的查询/回放/通知。（来源：`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 34/38/43/48/57/62）
  - **协同与任务闭环**：从会议导入行动项、分组同步、可查询/可分发、设备可见。（来源：`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 64/65）
  - **设备端体验**：更低刷新开销与更强健的模式边界、断连/重连稳定。（来源：`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 25/53/60/61/63）

- **合理性评估**
  - 与现状演进方向一致（已具备原型/接口/限幅/幂等/清洗），继续稳健化与规模化是合理的。
  - 优先将“数据可靠性（ACID/幂等/可回放）”与“端侧刷新成本”纳入第一优先级，长期价值最高。

- **架构冲击**
  - 引入统一存储（如 SQLite/WAL）与治理（ACL/配额/限流）会触及后端多模块与工具链，但可渐进。
  - 显示局部刷新需要驱动与 UI 框架小幅改造，但收益显著。

- **待澄清（仅3项）**
  1) 统一 SLO 目标：端到端会议总结延迟、转写推送周期、API P95 延迟与失败率的目标数值？（source required）  
  2) 部署与合规：是否必须私有化部署/内网隔离？数据（转写/纪要）是否需加密存储/签名审计？（source required）  
  3) 规模与成本：并发设备/会话峰值与预算上限（云/本地），是否要求边缘侧自治缓存？（source required）


## 3. 推荐目标架构与设计原理 (Target Architecture & Principles)

### 架构总览
- **数据与治理中台（后端）**
  - 统一本地嵌入式存储层：SQLite + WAL（会议索引/片段游标、离线队列、任务库）；现有 JSON 仅作导出与回放。
  - 统一治理层：鉴权（Token/JWT + 设备白名单）、ACL、QPS/配额、请求体限幅、审计日志。
  - 协议契约稳定：WS（会议/工作流/编码/peer）+ HTTP（只读查询与批量导入）统一返回包装与 CORS/鉴权策略。
- **端侧显示与音频**
  - ST7306 驱动层支持“矩形局部刷新/瓦片渲染”；UI 组件标注“可局刷区域”，减少整屏重绘。
  - 会议模式状态机最小化：推流/边界/finalize/summary/断连恢复路径再收敛。
- **可观测性**
  - 统一指标：会话/队列/推送周期/LLM耗时/DB IOPS/WS 连接寿命；日志抽样 + 关键事件埋点。

### 关键设计决策与理由 (Why)
- **SQLite 替代 JSON（保留导出）**：获得原子性/并发安全/索引查询能力，降低数据损坏与读放大；便于分页与过滤。（现 JSON 已做原子写与分片，但再演进将更稳健）
- **显示局部刷新**：减少 E‑ink 刷新耗时与功耗，降低鬼影，提升交互实时性；与分页/横幅/计时等 UI 强相关。
- **统一治理**：把 ACL/频控/配额策略收敛到一处，避免多实现不一致与旁路风险。
- **幂等/回放优先**：所有 finalize/assign/complete 等修改类动作均幂等化，结合 DB 唯一键与事务。

### 技术选型权衡
- **SQLite vs 轻量 KV（RocksDB/Badger）**：SQLite 更易用/跨平台/自带 SQL；RocksDB 写放大与运维复杂度更高。选 SQLite。
- **WS 鉴权（JWT）vs 简单 Token**：Token 更易落地；JWT 可包含设备声明并离线验证。先 Token，后平滑升级。
- **E‑ink 局刷（驱动+UI）vs 纯 UI 节流**：仅 UI 节流不足以降低整屏写成本；推荐驱动支持矩形更新，UI 才能真正分块刷新。


## 4. 具体实施与迁移路径 (Implementation & Migration Path)

### 分阶段计划 (e.g., 阶段一：...)
- 阶段一（硬化，里程碑 1，Q1 YYYY，source required）
  - 后端：建立 SQLite 存储层（会议索引/片段游标、离线队列、任务库），提供读路径双写验证；统一返回包装与鉴权中间件移植至 `/supie/meetings/*` 与 `/supie/workflow*`。
  - 端侧：梳理会议模式状态机（推流/边界/finalize/断连恢复），将“总结中”与“停止推流”对齐既有 ACK 语义。
  - 核查清单：Finalize ACK <100ms；Transcript 周期热更“下一周期生效”；离线补投 redelivery 统计稳定。

- 阶段二（性能，里程碑 2，Q2 YYYY，source required）
  - 显示：ST7306 支持矩形局部刷新 API；`EinkDisplayST7306` 标注可局刷区域（状态栏/横幅/计时/列表行/页脚）；UI 调度“最小脏矩形”。
  - 后端：队列有界化与背压策略（丢弃最旧 + 计数指标）；LLM 耗时指标与失败降级观测。
  - 核查清单：整屏刷新次数/分钟下降 ≥50%（source required）；会议端到端 P95 延迟目标达成（source required）。

- 阶段三（治理与规模，里程碑 3，Q3 YYYY，source required）
  - 安全：WS 握手鉴权（Token/JWT），设备白名单与会话 ACL 收敛；API 速率限制/配额按组。
  - 协同：任务导入/指派与分组广播在 DB 层唯一键约束与幂等校验。
  - 核查清单：未授权访问 100% 拦截；速率限制误杀率 <1%（source required）。

- 阶段四（体验与运维，里程碑 4，Q4 YYYY，source required）
  - 端侧：断连/重连横幅一致化，长会/短会边界体验打磨；会议横幅/计时 UI 稳态。
  - 运维：可观测面板（metrics + 日志采样 + 关键事件）、一键导出会议/任务快照。

- 灰度与回滚
  - 双写/影子读：引入 SQLite 后，短期并行产出 JSON + SQLite；只读 API 先走 SQLite，回滚直接切回 JSON。
  - Feature flag：`meeting.broadcast`、`include_origin`、`api_rate_limit`、`transcript_push_interval_ms` 等全部可热更，任一异常逐项关闭。
  - 端侧：驱动局刷通过编译开关与回退路径保留整屏刷新。

### 风险与应对策略 (Risks & Mitigations)
- **DB 引入复杂度**：设备/容器权限与备份策略增加 → 采用内嵌 SQLite + WAL，提供每日 JSON 导出与一致性校验。
- **局部刷新不稳定**：硬件差异/窗口寄存器不一致 → 先开发板与小样验证，设置“整屏回退”阈值。
- **治理误伤**：限流/ACL 可能阻断联调 → 管控台白名单/豁免规则与实时日志面板，逐步收紧。
- **线程/协程边界**：并发 finalize/推送与队列冲突 → 连接级互斥 + 任务取消幂等已存在，继续添加“操作级幂等键”。

### Citations
- 架构索引与风险：`collaboration/index.md` L41-L66  
- 会议闭环/查询/Webhook/分片/指标：`backend/core/handle/meeting_handle.py`；`backend/core/http_server.py`；`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 34/38/43/48/50/58  
- 握手/路由/观测/限流：`backend/core/websocket_server.py`；`backend/core/connection.py`；`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 3/4/35  
- 工作流：`backend/core/handle/workflow_handle.py`；`backend/core/utils/tasks_store.py`；`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 27/64/65  
- 端侧 UI/驱动/交互：`hardware/main/display/eink_display_st7306.{h,cc}`；`hardware/main/st7306_driver.{h,c}`；`hardware/main/application.cc`；`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 25/53/60/61/63  
- LLM 选型与热更：`backend/core/connection.py`；`/Users/tlovo/code_ai/AI-Badge/log.md` 编辑内容 46/51  
- 未提供的定量指标与里程碑：source required


——

简明术语说明
- **幂等**：同一操作执行多次，结果等价一次，避免重复副作用。  
- **ACL**：访问控制列表，定义谁能访问哪些资源。  
- **局部刷新（Partial Update）**：只重绘屏幕的一小块矩形区域，降低耗时与功耗。


### 给产品/技术负责人可执行的小清单（80/20）
- 先做“SQLite + WAL”承接会议索引/离线队列/任务库（读双写 JSON），同时统一 `/supie/meetings/*` 与 `/supie/workflow*` 鉴权/限流。  
- 端侧先标注 UI“可局刷区域”，驱动提供矩形更新原语，首页状态栏/横幅/页脚与列表行优先改造。  
- 建立 SLO 仪表（转写周期、finalize ACK、summary P95），异常一键回退到 JSON/整屏刷新/关闭广播。  


请补充答复（澄清问题）
1) 目标 SLO/成本指标（延迟/成功率/并发/预算）？  
2) 部署与合规（私有化/内网/加密/审计）刚性约束？  
3) 峰值设备数与热路径（会议/协同）的年度增长预期？


- 我已成功访问并解析 `@collaboration/index.md` 与提供的 `@log.md`（协同工作日志记录）。若需补充更多源码或配置，请告知具体 `@` 文件。

---

**User**

# 代码参考
硬件部分代码是hardware 
后端部分代码是backend 
测试部分代码是test 

# 任务总纲
项目索引请参考index.md @index.md 
项目日志暂无

# 用户需求
项目需要需要在3天内做到软硬件一体结合,让硬件能结合后端实装多功能(会议模式 编码模式 工作模式);

项目计划重构硬件逻辑,删除现在的硬件(4.2bwr板子)的所有非核心逻辑,降低硬件代码复杂度, 用最简单的方式实现所有功能( (对话模式 编码模式 会议模式 工作模式);

具体计划是硬件不需要知道“自己处在什么模式” , 硬件只需要保证网络系统,显示系统和音频系统正常即可,后端来判断和处理所有逻辑,后端来标记状态和指挥硬件进入什么模式; 具体流程请参考全流程演示.md @全流程演示.md 

还有一个想法是在硬件侧构建一个万能绘制函数 (硬件类似前端页面, 保证页面能正常切换和刷新, 后端发送指令 硬件接收到指令后 使用万能绘制函数去绘制需要的页面);

# 人员状态
项目有一位全栈工程师w ,一位硬件工程师p, 一位初级软件工程师d, 我们每天有效工作只有10小时; 上午3小时 下午4小时 晚上3小时;


---

**Cursor**

## 1. 现有架构评估 (As-Is Assessment)

### 优点 (Pros)
- **分层清晰、职责合理**：硬件侧入口、应用编排、驱动与显示、协议（WS/MQTT+UDP）分层明确；后端具备 WS/HTTP 服务、会/工/码三类业务处理与测试脚手架。（来源：`collaboration/index.md` L5-L20、L28-L36）
- **板级与显示抽象**：4.2" ST7306（BWR）板级封装、GFX/LVGL 桥接、显示抽象与字体/布局已成型，便于复用。（来源：`collaboration/index.md` L12-L21、L16-L19）
- **协议面向设备**：后端具备 WebSocket 路由/心跳与会话管理、HTTP 只读能力（OTA/vision等），可承载“后端主导模式”的目标形态。（来源：`collaboration/index.md` L28-L35）

### 缺点与挑战 (Cons & Challenges)
- **硬件侧状态机耦合偏重**：`hardware/main/application.cc` 汇聚音频/显示/模式/协议多职责，后续扩展与并发边界复杂。（来源：`collaboration/index.md` L48-L55）
- **E‑ink 局部刷新能力不足**：当前以整屏刷新为主，缺少真正的“矩形局刷/瓦片更新”，影响交互延迟与功耗。（来源：`collaboration/index.md` L47、L58-L66）
- **跨端“一致模式语义”缺口**：硬件自知模式与后端判断模式存在潜在不一致，易产生状态漂移；缺少统一“渲染契约”。（来源：`collaboration/全流程演示.md` 全文）

已确认可访问 `@index.md` 与 `@全流程演示.md`；项目日志“暂无”，其余引用标注为 source required。


## 2. 需求合理性与影响分析 (Requirement & Impact Analysis)

- **业务目标与新需求**
  - 3 天内实现“软硬件一体”，由后端统一判定/指挥模式（对话/会议/工作/编码），硬件仅保障网络/显示/音频通路，并提供“万能绘制函数”以渲染后端下发页面。（来源：`collaboration/全流程演示.md`）
- **合理性评估**
  - 80/20 路径明确：以“后端主导 + UI 渲染 DSL”即可最小化硬件改动并快速联调；符合短期交付与长期可演进的平衡。
- **架构冲击**
  - 正向：统一“渲染协议”后，模式逻辑回归后端，硬件复杂度显著下降。
  - 需要变更：硬件需新增“渲染引擎（万能绘制函数）”与“音频/录制控制指令”处理；后端需新增“模式编排→渲染指令”转换层与最小只读/调试 API。

澄清问题（不超过3项）
1) 明确 3 天内的硬性验收指标：端到端演示需覆盖哪些页面/事件、转写/总结时延与成功率的 SLO？（source required）  
2) 部署与合规：是否需私有化/内网；会议内容/摘要是否需落盘/加密/脱敏；是否要求 API Token？（source required）  
3) 目标设备规模（并发连接数）与演示场景（单台/多台互动/离线补投）的最低门槛？（source required）


## 3. 推荐目标架构与设计原理 (Target Architecture & Principles)

### 架构总览
- **后端主导的“页面渲染 DSL + 动作指令”**
  - 通过 WebSocket 下发两类消息：a) `ui.render`（页面/区域内容）；b) `device.control`（如 `listen.start/stop`、`play.tone`、`tts` 提示、网络状态提示）。
  - 后端持有“模式状态机”，把业务状态映射为“渲染指令 + 动作指令”，硬件不持久化模式。
- **硬件“万能绘制函数（Render Engine）”**
  - 输入：简洁 JSON DSL；输出：按区域（header/body/footer）局部刷新（若驱动不支持，则整屏回退+节流）。
  - 缓存最近一次渲染的区域签名，做最小重绘。
- **显示分区与最小脏矩形**
  - Header：标题/网络/电量/录制图标；Body：列表/段落/日志；Footer：提示/分页。
  - 渲染指令可带 `regionsChanged: ["header","body"]`，指导局刷。
- **音频与录制控制**
  - 设备仅响应 `device.control.listen` 与音频设备开关；会议/编码边界由后端判定并驱动。

### 关键设计决策与理由 (Why)
- **模式下沉后端**：避免设备状态漂移，统一策略/灰度由后端集中控制，便于回放与审计。
- **轻量 UI DSL**：用“结构化内容 + 简单布局槽位”覆盖 80% 页面，成本低于通用画布协议；后续可渐进增强。
- **最小重绘**：E‑ink 下局刷/节流优先，优先减少整屏刷新次数，提升稳定观感与功耗指标。

建议的最小 UI DSL（示例）
```json
{
  "type": "ui.render",
  "page": "meeting.listen",  // meeting.listen | meeting.summary | working.list | coding.log | welcome | dialog
  "header": { "title": "会议模式", "icons": { "net": "ok", "rec": true, "battery": 82 } },
  "body": {
    "kind": "list",          // list | bullets | text | kv | logs
    "items": ["已连接后端", "请开始发言…"]
  },
  "footer": { "hint": "双击结束并生成纪要", "page": { "index": 1, "total": 1 } },
  "regionsChanged": ["header","body"]
}
```

设备控制（示例）
```json
{ "type": "device.control", "action": "listen.start" }
{ "type": "device.control", "action": "listen.stop" }
{ "type": "device.control", "action": "play.tone", "name": "meeting_enter" }
{ "type": "device.control", "action": "tts", "text": "已进入会议模式" }
```

### 技术选型权衡
- **UI DSL 粒度**：过细会变成“远程画布”（复杂/低效）；本方案以“页面类型 + 槽位内容”为度，兼顾可控与通用。
- **局部刷新**：若 `st7306_driver` 暂不支持安全窗口刷新，先以“区域边界整屏节流”上限保护，后续补驱动矩形刷写（source required）。
- **状态存储**：短期以内存+日志；若需落盘/查询再引入 SQLite/WAL（source required）。


## 4. 具体实施与迁移路径 (Implementation & Migration Path)

### 分阶段计划 (e.g., 阶段一：...)
以“3 天 × 每天 10 小时 × 3 人（w/p/d）”为节奏，目标是“端到端演示可用 + 可回滚”。

- 阶段一（D1：协议与硬件骨架）
  - 后端（w+d）
    - 定义并输出 `ui.render`/`device.control` 的后端编排层（基于现有 WS 服务 `backend/core/websocket_server.py`）。  
    - 建立最小页面映射：`welcome`/`dialog`/`meeting.listen`/`meeting.summary`/`working.list`/`coding.log`。  
    - 按《全流程演示》将关键节点映射为渲染+控制指令（例如：进入会议→render.listen + play.tone + listen.start）。  
  - 硬件（p）
    - 新增 Render Engine：解析 `ui.render`，分区绘制（header/body/footer），先整屏渲染，预留 `regionsChanged` 钩子。  
    - JSON 路由：`application.cc` 仅保留 `ui.render` 与 `device.control` 分支；移除/封存“自知模式”的分支。  
  - 联调（全员）
    - 测试页/脚本最小化：一键下发典型页面指令与控制指令；完成“欢迎→会议聆听”演示。
  - 通过标准
    - 设备开机 ≤10s 连上后端；收到 `ui.render:welcome` 并正确显示。  
    - 一次点击/命令可进入“会议聆听”页并显示录制图标。  

- 阶段二（D2：会议/工作/编码三页闭环）
  - 后端（w+d）
    - 会议：实现“结束→finalize→render.summary”链路（可先用固定/模板化 bullets 占位）。  
    - 工作：`working.list` 显示 5-12 条任务；分页信息下发。  
    - 编码：`coding.log` 以日志滚动列表渲染，含阶段/步骤行。  
  - 硬件（p）
    - Render Engine 增强：分页/滚动/截断（UTF-8 安全）；局部刷新预留（可暂用整屏节流）。  
    - `device.control.listen.start/stop` 映射到音频推流/停止。  
  - 联调（全员）
    - “会议：聆听→结束→纪要页”全链路演示；“工作/编码”能收渲染指令并正确显示。  
  - 通过标准
    - 纪要页渲染 2-6 条要点；工作页分页显示；编码页显示 6-8 行日志滚动。  

- 阶段三（D3：稳健性与回滚/演示化）
  - 后端（w）
    - 统一 ACK：每次 `ui.render` 下发后返回 `{status:"ok"}`；失败重试与限频（保护 E‑ink）。  
    - 快捷场景编排：一键“全流程演示”脚本（对话→会议→纪要→工作→编码）。  
  - 硬件（p）
    - 渲染节流：同页重复渲染 500ms 合并；Header/Body/Foot 签名比对避免无效刷新。  
    - 断连/重连横幅：网络中断提示 + 恢复后自动请求一次 `ui.render`（当前页）。  
  - 测试（d）
    - 录屏/指标记录：从点击“进入会议”到纪要显示的用时；任务/日志渲染正确性。  
  - 通过标准
    - 全流程演示一键通过；断连后 5s 内恢复 UI；回滚开关可在硬件侧“本地静态页面”演示。

交付清单（D3 晚）
- 渲染协议文档（JSON 字段、页面类型、区域定义、示例载荷）。  
- 硬件渲染引擎代码与最小单元测试（渲染/截断/分页）。  
- 后端编排层（模式→渲染/控制映射）与一键演示脚本。  
- 回滚策略：硬件“本地静态 UI + 手动提示音”；后端“关闭渲染层改为固定演示页面”。

### 风险与应对策略 (Risks & Mitigations)
- **E‑ink 局刷风险**：若驱动窗口化未就绪，则使用“区域级整屏节流 + 指令限频”，确保观感与寿命（后续再补矩形局刷）。（source required）
- **音频通路差异**：不同板卡/麦阵参数差异 → 统一用 `listen.start/stop` 控制，非会议时默认关闭推流，保护带宽与功耗。
- **后端编排复杂度**：短时间内重写完整状态机风险高 → 按《全流程演示》只覆盖最短链路（最小 MVP），其余场景先降级为固定提示。
- **联调时间紧**：三端并行导致等待 → 以“协议先行 + 假数据渲染”推进 UI 与演示，最后再串接真实 ASR/LLM。

### Citations
- 项目索引/分层与风险：`collaboration/index.md` L5-L21、L22-L27、L28-L36、L46-L56、L58-L66  
- 全流程/业务期望：`collaboration/全流程演示.md` L9-L18（对话切换）、L19-L29（会议流程）、L30-L42（工作流）、L44-L56（编码流程）  
- 具体驱动/应用文件位置（用于落地）：`hardware/main/application.cc`、`hardware/main/display/eink_display_st7306.{h,cc}`、`hardware/main/st7306_driver.{h,c}`、`backend/core/websocket_server.py`、`backend/core/http_server.py`（source required 之详细行号）  
- 指标/SLO/规模与里程碑时间：source required


### 术语最简说明
- **UI DSL**：一份简短 JSON，描述“显示什么、放在哪个区域”，像“填空模板”。  
- **局部刷新**：只重绘屏幕的小矩形区域，避免整屏闪烁与耗时。  
- **编排（Orchestration）**：后端把“业务状态”翻译为“渲染指令 + 设备控制”的过程。


——

请确认三项澄清（SLO/合规/规模），我将据此细化 D1-D3 的验收标准、回滚开关与演示脚本参数。

```json
{
  "type": "ui.render",
  "page": "meeting.listen",  // meeting.listen | meeting.summary | working.list | coding.log | welcome | dialog
  "header": { "title": "会议模式", "icons": { "net": "ok", "rec": true, "battery": 82 } },
  "body": {
    "kind": "list",          // list | bullets | text | kv | logs
    "items": ["已连接后端", "请开始发言…"]
  },
  "footer": { "hint": "双击结束并生成纪要", "page": { "index": 1, "total": 1 } },
  "regionsChanged": ["header","body"]
}
```

```json
{ "type": "device.control", "action": "listen.start" }
{ "type": "device.control", "action": "listen.stop" }
{ "type": "device.control", "action": "play.tone", "name": "meeting_enter" }
{ "type": "device.control", "action": "tts", "text": "已进入会议模式" }
```

---

**User**

澄清问题
1) 3 天内的硬性验收指标：端到端演示需覆盖(对话模式 会议模式 工作模式和编码模式)的所有页面
2) 部署与合规：内网部署即可；会议内容/摘要无需加密和脱敏；后端能力使用的全部是 API Token
3) 目标设备规模（并发连接数超过10台）演示场景最低门槛需要（三台以上互动 + 离线补投）的？（source required）

---

**Cursor**

## 1. 现有架构评估 (As-Is Assessment)

### 优点 (Pros)
- **分层清晰**：硬件侧入口/应用/显示/驱动/协议分层，后端具备 WS/HTTP 与会议/工作流/编码处理骨架。（来源：`collaboration/index.md` L5-L21、L28-L36）
- **显示与板级抽象可复用**：ST7306 E‑ink、GFX/LVGL 桥接、统一状态栏/分页能力，便于快速接入渲染协议。（来源：`collaboration/index.md` L12-L21）
- **流程蓝本明确**：对话/会议/工作/编码的全流程页签与事件顺序清晰，可直接映射到“渲染+控制”协议。（来源：`collaboration/全流程演示.md` L9-L56）

### 缺点与挑战 (Cons & Challenges)
- **硬件侧多职责耦合**：模式逻辑、UI、音频、协议集中在 `application.cc`，维护成本高。（来源：`collaboration/index.md` L48-L55）
- **E‑ink 刷新成本高**：缺少“矩形局部刷新/瓦片更新”，整屏刷新频率需节流。（来源：`collaboration/index.md` L47、L58-L66）
- **状态一致性**：硬件自知模式与后端模式易漂移，缺少统一“渲染契约”。（来源：`collaboration/全流程演示.md` 全文）


## 2. 需求合理性与影响分析 (Requirement & Impact Analysis)

- **业务目标与新需求**
  - 3 天内完成“软硬件一体”：后端主导模式，硬件仅保障网络/显示/音频通路；通过“万能绘制函数”渲染全部页面（对话/会议/工作/编码）。（来源：`collaboration/全流程演示.md`）
  - 部署与合规：内网部署；无需加密/脱敏；统一 API Token 鉴权（后端）。（用户澄清）
  - 演示规模：并发>10台，至少3台互动+离线补投演示。（用户澄清）

- **合理性评估**
  - 以“后端编排 + UI DSL（页面槽位）+ 设备控制指令”满足 80/20，硬件最小改造即可覆盖全部页面与模式。

- **架构冲击**
  - 正面：统一模式判定与编排在后端，消除硬件状态机复杂性。
  - 变更点：新增“ui.render/device.control”协议、硬件渲染引擎与后端编排层；离线补投需最小持久化。


## 3. 推荐目标架构与设计原理 (Target Architecture & Principles)

### 架构总览
- **协议层（WS）**
  - 下行：`ui.render`（页面渲染）/`device.control`（录音边界/提示音/tts/网络横幅/分页）。
  - 上行：`hello/heartbeat` 与用户交互事件（如“确认进入X模式”语音意图由后端判定）。
- **后端编排**
  - 将《全流程演示》中的节点映射为“状态→渲染 + 控制”：如“进入会议”→`ui.render:meeting.listen` + `device.control:listen.start`。
  - 设备级“最后一次渲染缓存”（内存+可选落盘），断连/重连自动补投一次。
- **硬件渲染引擎（万能绘制函数）**
  - 输入：简洁 UI DSL（页面类型 + header/body/footer 槽位 + 分页/图标）。
  - 输出：调用 E‑ink 分区绘制；优先局部刷新（若驱动不具备则整屏+节流回退）。

### 关键设计决策与理由 (Why)
- **后端主导模式**：统一策略/幂等/灰度，消除端侧状态漂移。
- **UI DSL（页面+槽位）而非远程画布**：简单、稳定、可验证；便于后续演进。
- **最小脏矩形**：降低刷新时延与功耗，提升观感与寿命。

### 技术选型权衡
- **鉴权**：内网 + API Token，先全局中间件，后续再细化端到端 JWT（可选，非本期）。
- **离线补投**：设备“最后渲染状态”+简易队列即可满足演示；后续再引入 SQLite/WAL（source required）。
- **局部刷新**：若 `st7306_driver` 暂不具备安全窗口刷新，则区域级整屏节流+QPS 限制先保交付（后续增强，source required）。


## 4. 具体实施与迁移路径 (Implementation & Migration Path)

### 分阶段计划 (e.g., 阶段一：...)
- 阶段一（D1，骨架联通，w+p+d）
  - 后端（w+d）
    - 定义消息契约：`type:"ui.render"` 与 `type:"device.control"`（页面ID、header/body/footer 槽位、分页、icons、regionsChanged）。
    - 编排最小实现：覆盖页面
      - 对话：`dialog.chat`
      - 会议：`meeting.listen`、`meeting.summary`、`meeting.end`
      - 工作：`working.list`、`working.detail`、`working.assign`、`working.end`
      - 编码：`coding.listen`、`coding.tasks_confirm`、`coding.log`、`coding.end`
    - 渲染 ACK：设备回 `{status:"ok"}`；后端失败重试+限频（每设备≤2 QPS）。
    - 最后渲染缓存：内存字典（deviceId→renderPayload）；重连后自动补发。
  - 硬件（p）
    - 渲染引擎：解析 `ui.render`，三分区（header/body/footer）；整屏渲染 + 500ms 合并节流；预留 `regionsChanged` 钩子。
    - 控制指令：`device.control.listen.start/stop` → 开/停录音推流；`play.tone/tts` → 本地或后端提示音；`page.next/prev` → 翻页。
    - 移除“硬件自知模式”分支，仅保留网络/显示/音频通道与通用渲染。
  - 测试（d）
    - 新增 `test/ws_render_demo.html`：可一键下发各页面渲染/控制指令；并发模拟≥3连接。
  - 通过标准
    - 设备开机后显示 `welcome`→一键进入 `meeting.listen` 并显示录制图标；渲染 ACK 正常。

- 阶段二（D2，三模式闭环，w+p+d）
  - 后端（w+d）
    - 会议：语音边界→`listen.stop`→`meeting.finalize`→`ui.render:meeting.summary`；可先模板 bullets（占位），满足演示。
    - 工作：`working.list`（8/页，≥12条分页）、`working.detail/assign` 模拟负载。
    - 编码：`coding.listen`→`tasks_confirm`→`coding.log`（6-8 行滚动）→`end`。
    - 并发与互动：≥10连接压测；3台互动（A发指令→B/C 收到渲染），离线设备重连收到“最后渲染”补投。
  - 硬件（p）
    - 文本截断/分页/滚动；UTF-8 安全；页脚“第x/共y页”；网络断连横幅+自动请求一次恢复渲染。
  - 测试（d）
    - 脚本 `test/run_render_flow.py`：串起四模式所有页面；记录时间戳与 ACK。
  - 通过标准
    - 四模式“所有页面”均可渲染并在 2 步内切换；≥10并发稳定；3台互动成功；离线重连补投成功。

- 阶段三（D3，稳健化与演示打包，w+p+d）
  - 后端（w）
    - Token 鉴权中间件（WS 升级与 HTTP 辅助接口）；渲染限频（每设备≤2 QPS）与队列有界（≤10，丢弃旧帧+计数）。
    - “全流程演示脚本”：对话→会议→纪要→工作→编码，一键跑通。
  - 硬件（p）
    - 分区签名：header/body/footer 变更比对，减少无效刷新；断连/重连横幅与恢复策略完善。
  - 测试（d）
    - 三机互动脚本 + 离线补投剧本；并发10-15稳定性；录屏与验收清单输出。
  - 通过标准（硬性验收）
    - 覆盖对话/会议/工作/编码的“所有页面”；并发≥10；三台互动；离线补投可见；均在内网+Token 鉴权环境运行。

- 回滚/灰度
  - Feature Flag：`render.enabled`（关闭即回本地静态页面演示）；`render.qps_limit`、`offline.redeliver` 可随时关闭。
  - 若渲染不稳：硬件切换“整屏节流模式”，后端降级为“关键页面少刷+ACK 门控”。

### 风险与应对策略 (Risks & Mitigations)
- **E‑ink 局刷不就绪**：先整屏+节流+分区签名，保证观感；后续补矩形刷新（source required）。
- **并发>10下抖动**：下行渲染限频、队列有界化、ACK 门控与重试指数退避。
- **离线补投一致性**：仅补投“最后渲染”而非历史队列，避免堆积与错序；重连后后端主动下发一次快照。
- **时间紧/多端并行**：协议先行+假数据渲染；D2/D3 再串真实 ASR/LLM（可保留模板 bullets）。

### Citations
- 架构与风险：`collaboration/index.md` L5-L21、L28-L36、L46-L66  
- 全流程/页面枚举：`collaboration/全流程演示.md` L9-L56  
- 具体文件落点（实现参考）：`hardware/main/application.cc`、`hardware/main/display/eink_display_st7306.{h,cc}`、`hardware/main/st7306_driver.{h,c}`、`backend/core/websocket_server.py`、`backend/core/http_server.py`（source required）  
- 并发规模/演示门槛：用户澄清（本对话）  
- 局部刷新/SQLite 引入等更深演进：source required

——

### 面向高中生的简明说明
- 我们把“该显示什么页面、什么时候开始/停止录音”等决定放在后端；硬件只负责“画出来、录/停音、连网”。
- 后端发来一张“页面说明书”（JSON），硬件用“万能绘制函数”把它画到屏上；这样能很快做出所有页面。
- 断网了也不怕：我们记住“最后一张画”，等网络恢复再发一次，继续显示。

### 3 天任务分工建议（10h/天）
- D1：协议与渲染骨架（w：后端编排/契约；p：渲染引擎；d：测试页）。  
- D2：三模式闭环+并发与离线补投（w：编排&缓存；p：分页/截断/横幅；d：脚本与录屏）。  
- D3：鉴权/限频/有界队列与一键演示（w：Token/限流；p：分区签名与节流；d：验收报告）。

如需，我可基于上述契约输出“后端最小编排模块与硬件渲染引擎”的代码骨架清单与接口对接点，便于今天直接开工。

---

**User**

请按照这个计划,基于上述契约输出“后端最小编排模块与硬件渲染引擎”的代码骨架清单与接口对接点,放到build.md里@build.md 

---

**Cursor**

我将把“后端最小编排模块与硬件渲染引擎”的骨架与接口对接点写入 `collaboration/build.md`，包含模块清单、消息契约、对接文件与函数签名、以及3天分工与验收清单。随后你可以按清单开工实现。

```markdown
# 后端最小编排模块与硬件渲染引擎 — 代码骨架与接口对接点（D1–D3）

目标（3天硬性验收）
- 覆盖对话/会议/工作/编码四类页面的端到端演示；并发≥10；≥3台互动；离线补投“最后渲染”；内网部署 + API Token。

——

## 0. 渲染协议契约（最小版）

- 下行：`ui.render`
  - 字段：
    - `page`: string（页面标识）
      - `welcome | dialog.chat | meeting.listen | meeting.summary | working.list | working.detail | working.assign | working.end | coding.listen | coding.tasks_confirm | coding.log | coding.end`
    - `header?`: { `title`: string, `icons?`: { `net?`: "ok|bad|off", `rec?`: bool, `battery?`: int(0..100) } }
    - `body?`: 
      - `{ kind: "list", items: string[] }`
      - `{ kind: "bullets", items: string[] }`
      - `{ kind: "text", text: string }`
      - `{ kind: "logs", lines: string[] }`
      - `{ kind: "kv", items: [{k:string,v:string}] }`
    - `footer?`: { `hint?`: string, `page?`: { `index`: int>=1, `total`: int>=1 } }
    - `regionsChanged?`: string[]（`header|body|footer`，用于最小重绘）
    - `id?`: string（本次渲染ID，便于 ACK）
    - `ts?`: number（服务器毫秒时间戳）

- 下行：`device.control`
  - `action`: 
    - 录音边界：`listen.start | listen.stop`
    - 提示：`play.tone`（`name`）、`tts`（`text`）
    - 导航：`page.next | page.prev`
    - 网络横幅：`net.banner`（`text`, `level: info|warn|error`, `duration_ms?`）
  - 其它字段：`name?`、`text?`、`duration_ms?`

- 上行 ACK（两种皆可，后端需兼容）
  - `{ "type":"ui.ack", "id":"<render-id>", "status":"ok" }`
  - 或 `{ "type":"ui.render", "status":"ok", "id":"<render-id>" }`

- 发送约束
  - 渲染限频：每设备 ≤2 QPS；设备断连时仅缓存“最后一次渲染”。
  - 补投：设备重连或 `hello` 后，后端自动补发“最后一次渲染”。

示例：meeting.listen（进入会议）
```json
{
  "type": "ui.render",
  "page": "meeting.listen",
  "header": { "title": "会议模式", "icons": { "net": "ok", "rec": true, "battery": 82 } },
  "body": { "kind": "list", "items": ["已连接后端", "请开始发言…"] },
  "footer": { "hint": "双击结束并生成纪要", "page": { "index": 1, "total": 1 } },
  "regionsChanged": ["header","body"],
  "id": "rnd-123",
  "ts": 1730000000000
}
```

示例：device.control（开始录音）
```json
{ "type": "device.control", "action": "listen.start" }
```

——

## 1. 后端代码骨架清单（模块 + 对接点）

新增文件
- `backend/core/orchestration/render_schema.py`
  - 定义 UI DSL 结构与轻量校验（dict→安全过滤/裁剪/默认值）。
  - `def validate_render_payload(payload: dict) -> dict`

- `backend/core/orchestration/render_orchestrator.py`
  - 将业务事件（进入会议/finalize/工作列表/编码日志）映射为 `ui.render` + `device.control`。
  - 关键函数（最小集）：
    - `async def show_welcome(conn)`
    - `async def meeting_enter(conn)` → render `meeting.listen` + control `listen.start`
    - `async def meeting_finalize_ack(conn)` → control `listen.stop` + render 占位（“总结中…”）
    - `async def meeting_show_summary(conn, summary)` → render `meeting.summary`
    - `async def working_show_list(conn, tasks, page_index=1)` → render `working.list`
    - `async def coding_show_log(conn, lines, phase=None)` → render `coding.log`

- `backend/core/orchestration/render_sender.py`
  - QPS/队列门控 + 发送 + ACK 等待（可选）+ 最后渲染缓存。
  - `async def send_render(conn, payload: dict, regions=None, wait_ack=False) -> None`
  - `async def send_control(conn, action: str, **kwargs) -> None`

- `backend/core/utils/last_render_cache.py`
  - 维护 `device_id -> last_render_payload`（内存）；TTL 可选；提供 get/set。
  - `def set_last(device_id: str, payload: dict) -> None`
  - `def get_last(device_id: str) -> dict | None`

可选新增（演示/联调）
- `backend/core/handle/render_demo_handle.py`
  - 暴露内部调用编排的最小入口（仅测试用），如：`{"type":"demo","event":"meeting_flow"}`。

改造/对接
- `backend/core/websocket_server.py`
  - 注册设备成功后：查询 `last_render_cache.get(device_id)`，如存在→补发一次。
  - 暴露便捷发送：`async def send_to_device(device_id: str, payload: dict) -> bool`。

- `backend/core/connection.py`
  - 握手成功后：调用 `render_orchestrator.show_welcome(conn)`（可选）。
  - 处理设备上行 `ui.ack`（记录 ACK/耗时/失败重试计数）。

- `backend/core/handle/textHandle.py`
  - 在 `mode.start(meeting)` → `await render_orchestrator.meeting_enter(conn)`。
  - 在 `meeting.phase=="finalize"` → `await render_orchestrator.meeting_finalize_ack(conn)`；待总结完成后 `meeting_show_summary`。
  - `workflow.update` → `working_show_list`；`coding.*` → `coding_show_log`。

- `backend/core/http_server.py`（可选）
  - 新增只读演示接口：
    - `GET /supie/render/last?deviceId=...`：返回缓存的最后渲染。
    - `POST /supie/demo/flow`：触发一键全流程演示（内部调用 orchestrator）。

数据/行为约束
- 每设备渲染发送限频（默认≤2 QPS），超限丢弃旧帧并计数；`last_render_cache` 始终更新为最新帧。
- 所有下行渲染在发送前调用 `render_schema.validate_render_payload()` 防御性清洗。

——

## 2. 硬件代码骨架清单（模块 + 对接点）

新增文件
- `hardware/main/display/eink_render_engine.h`
  - `struct RenderHeader { std::string title; bool icon_rec; int battery; std::string net; };`
  - `struct PageInfo { int index; int total; };`
  - `enum class BodyKind { LIST, BULLETS, TEXT, LOGS, KV };`
  - `struct RenderBody { BodyKind kind; std::vector<std::string> items; std::string text; /* kv可后续扩展 */ };`
  - `struct RenderFooter { std::string hint; PageInfo page; };`
  - `struct RenderPayload { std::string page; RenderHeader header; RenderBody body; RenderFooter footer; std::vector<std::string> regionsChanged; std::string id; };`
  - `class EinkRenderEngine { public: void Init(EinkDisplayST7306* disp); bool Render(const RenderPayload& p); /* 返回是否成功 */ private: bool DrawHeader(const RenderHeader&); bool DrawBody(const RenderBody&); bool DrawFooter(const RenderFooter&); /* 内部做UTF-8 截断/分页/脏矩形 */ };`

- `hardware/main/display/eink_render_engine.cc`
  - 实现三分区渲染，当前版本先整屏刷新 + 500ms 合并节流；预留 `regionsChanged` 做局部刷新（驱动就绪后切换）。

修改文件
- `hardware/main/application.cc`
  - JSON 路由合并：仅保留两类下行处理入口
    - `void HandleUiRender(const cJSON* msg)` → 解析为 `RenderPayload`，调用 `EinkRenderEngine::Render()`，随后 `SendAckIfHasId()`。
    - `void HandleDeviceControl(const cJSON* msg)` → `listen.start/stop` → 开/停音频推流；`play.tone/tts` → 播放提示音/走本地或后端；`page.next/prev` → 驱动翻页并重绘。
  - ACK：
    - `void SendAckIfHasId(const std::string& id)` → 发送 `{type:"ui.ack", id, status:"ok"}`。
  - 清理：移除“硬件自知模式”的状态与大部分页面渲染逻辑（保留必要的音频/网络/显示初始化）。

- `hardware/main/protocols/websocket_protocol.*`（如需）
  - 保持 `SendJson/OnIncomingJson`；无需新增类型，仅转发到 `application.cc` 的两个入口。

渲染与刷新策略
- 先整屏 + 合并节流（≥500ms），避免E‑ink闪烁；保留 `regionsChanged` 钩子，后续切矩形局刷。
- 文本渲染：UTF‑8 安全截断，列表/日志每页≤8条，页脚统一“第x/共y页”。

——

## 3. 关键接口对接点（文件/函数）

- 后端
  - `backend/core/websocket_server.py`：`register_device_handler()` 成功后补投 `last_render_cache`；`send_to_device()` 统一出口。
  - `backend/core/connection.py`：握手完成后可调用 `orchestrator.show_welcome()`；处理 `ui.ack` 统计。
  - `backend/core/handle/textHandle.py`：将 `mode/meeting/workflow/coding` 事件转发至 orchestrator（不再下发“页面细节”，由 orchestrator 构造）。

- 硬件
  - `application.cc::OnIncomingJson(...)` → 分派到 `HandleUiRender/HandleDeviceControl`。
  - `EinkRenderEngine::Render(...)` → 调用 `EinkDisplayST7306` 的现有绘制能力完成三分区刷新。
  - 录音通路：`listen.start/stop` → 控制 `audio_processor_`/OPUS 推流；保留既有实现，仅改由 `device.control` 驱动。

——

## 4. D1–D3 分工与里程碑

- D1（骨架联通）
  - 后端（w+d）：`render_schema/orchestrator/sender/last_render_cache` 最小实现；`websocket_server` 注册补投；`textHandle` 事件→orchestrator。
  - 硬件（p）：`EinkRenderEngine` 雏形与三分区整屏渲染；`application.cc` 接口与 ACK；实现 `listen.start/stop`。
  - 通过：欢迎页→会议聆听页 + 录音开启；ACK 正常；断连重连补投。

- D2（三模式闭环 + 并发/离线）
  - 后端（w+d）：`meeting_finalize_ack/summary`、`working_list`（分页）、`coding_log`（滚动）；限频与队列门控；10+ 并发与3台互动；离线设备补投“最后渲染”。
  - 硬件（p）：文本截断/分页/页脚；网络横幅；断连后自动请求恢复渲染。
  - 通过：四类页面全部渲染；并发≥10；三台互动；离线补投成功。

- D3（演示化与守护）
  - 后端（w）：API Token 中间件；`/supie/demo/flow` 一键演示；ACK/失败重试统计与日志。
  - 硬件（p）：分区签名比对（减少无效重绘）；节流整合；页面导航指令。
  - 测试（d）：`ws_render_demo.html` 与 `run_render_flow.py`；录屏与验收报告。

——

## 5. 验收清单（硬性）

- 对话/会议/工作/编码“所有页面”均可通过 `ui.render` 正确渲染；
- `device.control` 能开启/停止录音、触发提示音、页内翻页；
- 并发≥10连接稳定；≥3台互动（A发起→B/C 同步渲染）；
- 离线补投：设备重连后收到“最后渲染”快照；
- 内网部署 + API Token 鉴权下运行；
- 回滚：一键关闭 `render.enabled`（后端不再下发渲染），硬件改为本地静态页面演示。

——

## 6. 回滚与配置开关（建议）

- 后端 `server.config`：
  - `render.enabled: true|false`
  - `render.qps_limit_per_device: 2`
  - `render.wait_ack: false`
  - `render.offline_redeliver: true`

- 硬件编译开关：
  - `EINK_PARTIAL_UPDATE`（后续启用矩形局刷时打开）
  - `RENDER_THROTTLE_MS=500`

——

## 7. 附：最小页面负载样例

欢迎页
```json
{ "type":"ui.render", "page":"welcome", "header":{ "title":"欢迎" }, "body":{ "kind":"text", "text":"正在连接…" }, "footer":{ "hint":"成功连接后将进入对话" }, "regionsChanged":["header","body"] }
```

工作列表（分页）
```json
{ "type":"ui.render", "page":"working.list", "header":{ "title":"工作模式" }, "body":{ "kind":"list", "items":["[P0] 修复登录","[P1] 优化列表", "[P2] 编写用例", "[P3] 文档整理" ] }, "footer":{ "hint":"短按翻页", "page":{ "index":1, "total":2 } }, "regionsChanged":["body","footer"], "id":"wk-001" }
```

编码日志
```json
{ "type":"ui.render", "page":"coding.log", "header":{ "title":"编码模式" }, "body":{ "kind":"logs", "lines":["build: 拉起构建","test: 单测通过","deploy: 部署完成" ] }, "footer":{ "hint":"phase: build" }, "regionsChanged":["body"], "id":"cd-001" }
```


```

已将“后端最小编排模块与硬件渲染引擎”的骨架与接口对接点写入 `collaboration/build.md`，包含：
- 渲染协议契约（ui.render/device.control），ACK、限频与离线补投规则
- 后端新增/改造文件清单与函数签名（schema、orchestrator、sender、last_render_cache、对接 textHandle/websocket_server/connection）
- 硬件渲染引擎最小接口（`EinkRenderEngine` 三分区渲染）、`application.cc` 两类处理入口与 ACK
- D1–D3 分工、验收清单、回滚/配置开关与页面示例载荷

如需，我可以按该清单先创建后端 `orchestration` 模块与硬件 `eink_render_engine` 头文件空实现，便于今天直接开工。

---

**User**

先不用创建 先和我解释和讨论一下 
build文档是不是包含了所有必要核心内容?
build文档是不是按照高优先级到低优先级的顺序来列出的?

比如这个( ## 0. 渲染协议契约（最小版）) 是不是最重要的部分?

---

**Cursor**

### 结论
- 是，当前 build 文档已覆盖“3天可交付”的核心要素（80/20）：渲染协议、后端编排骨架、硬件渲染引擎、对接点、分阶段计划、验收、回滚/配置与样例载荷。
- 是，整体按优先级从高到低组织：先“协议契约”，再“后端/硬件最小实现与对接”，最后“计划/验收/回滚/样例”。
- 是，`## 0. 渲染协议契约（最小版）`是最重要部分；没有这层契约，两端无法对齐、也无法并行开发与联调。

### 建议的最小补强（按优先级）
- 高优先：
  - ACK/错误语义表：渲染失败、超限、无效载荷、设备忙的标准返回码与重试策略。
  - 限频/背压细则：丢弃策略（丢旧/丢新）、队列上限、观测指标（丢弃计数）。
  - 鉴权落点与样例：WS 升级/HTTP 中间件接入点与 API Token 的配置片段。
- 中优先：
  - 离线补投策略说明：仅补“最后渲染”的理由、TTL/覆盖规则与重连触发点。
  - 测试清单最小化：指定两个文件名（HTML+脚本）与一键跑通命令，便于当日联调。
  - Schema 版本位与向后兼容：`schemaVersion` 或保留字段与静默名单（老消息不报错）。

需要的话，我可以把以上补强精简为 2–3 小节直接追加到 build 文档，不改变现有结构与优先级。

---

**User**

先不补强 先实现核心功能 还有个问题 硬件渲染引擎的可实现性高吗?

---

**Cursor**

### 结论
- 可实现性高。沿用现有 `EinkDisplayST7306`/GFX 能力，用“头/体/脚三分区 + 整屏节流”的最小实现，3天内可稳定落地并覆盖四类页面演示。

### 为什么可实现
- 已有显示与字体/布局基础：`hardware/main/display/eink_display_st7306.{h,cc}`、`st7306_driver.{h,c}` 已能稳定绘制文本、列表、页脚（来源：index.md）。
- 协议极简：UI DSL 只需“页面类型 + 槽位内容（header/body/footer）”，硬件侧只做映射，不做业务判断。
- 刷新策略先简单再优化：先整屏刷新 + 500ms 合并节流，后续再接“regionsChanged→局部刷新”（局刷可待驱动验证，当前不阻塞演示）。

### 3天落地路径（硬件侧）
- D1：渲染引擎骨架
  - 新增 `EinkRenderEngine::{Init, Render, DrawHeader, DrawBody, DrawFooter}`。
  - `application.cc` 只保留两类分支：`ui.render`→Render、`device.control`→`listen.start/stop`/tone/翻页；下行带 `id` 则回 `ui.ack`。
- D2：可用性强化
  - UTF-8 安全截断、分页（每页≤8行）、页脚“第x/共y页”、简单日志滚动。
  - 整屏节流（≥500ms），避免抖动；断连横幅 + 重连后请求一次当前页重绘。
- D3：观感与稳健
  - 分区签名（header/body/footer 内容哈希）→无变化不重绘。
  - 预留 `regionsChanged` 钩子，若驱动矩形局刷就绪则替换对应区域刷新；未就绪则维持整屏节流。

### 风险与对策
- 局部刷新未就绪：先整屏+节流（观感可接受），后续平滑切局刷（source required）。
- 文本溢出/多语言：统一用像素宽度截断与多行折行；列表强制上限与省略号。
- 音频/推流边界：全部由 `device.control.listen.start/stop` 驱动，避免端侧自判。

### 验收口径（硬件）
- 能按 `ui.render` 渲染以下页面：`welcome/dialog.chat/meeting.listen/meeting.summary/working.list/coding.log`。
- `device.control` 可开/停录音、显示横幅、翻页；ACK 正常。
- 3台互动与断连重连场景：重连后收到“最后渲染”并正确重绘。
- 整屏刷新频率受控（节流≥500ms），无明显闪烁。

---

**User**

请完整的将渲染协议契约的所有内容展现出来@build.md 

---

**Cursor**

我将扩充 build.md 的“渲染协议契约”章节，补齐字段定义、约束、错误码、ACK/限频、兼容性与多页示例，确保双方依此可立即并行开发与联调。现在进行编辑。

```markdown
# 项目架构 — 后端最小编排模块与硬件渲染引擎

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

——

## 1. 后端代码骨架清单（模块 + 对接点）

新增文件
- `backend/core/orchestration/render_schema.py`
  - 定义 UI DSL 结构与轻量校验（dict→安全过滤/裁剪/默认值）。
  - `def validate_render_payload(payload: dict) -> dict`

- `backend/core/orchestration/render_orchestrator.py`
  - 将业务事件（进入会议/finalize/工作列表/编码日志）映射为 `ui.render` + `device.control`。
  - 关键函数（最小集）：
    - `async def show_welcome(conn)`
    - `async def meeting_enter(conn)` → render `meeting.listen` + control `listen.start`
    - `async def meeting_finalize_ack(conn)` → control `listen.stop` + render 占位（“总结中…”）
    - `async def meeting_show_summary(conn, summary)` → render `meeting.summary`
    - `async def working_show_list(conn, tasks, page_index=1)` → render `working.list`
    - `async def coding_show_log(conn, lines, phase=None)` → render `coding.log`

- `backend/core/orchestration/render_sender.py`
  - QPS/队列门控 + 发送 + ACK 等待（可选）+ 最后渲染缓存。
  - `async def send_render(conn, payload: dict, regions=None, wait_ack=False) -> None`
  - `async def send_control(conn, action: str, **kwargs) -> None`

- `backend/core/utils/last_render_cache.py`
  - 维护 `device_id -> last_render_payload`（内存）；TTL 可选；提供 get/set。
  - `def set_last(device_id: str, payload: dict) -> None`
  - `def get_last(device_id: str) -> dict | None`

可选新增（演示/联调）
- `backend/core/handle/render_demo_handle.py`
  - 暴露内部调用编排的最小入口（仅测试用），如：`{"type":"demo","event":"meeting_flow"}`。

改造/对接
- `backend/core/websocket_server.py`
  - 注册设备成功后：查询 `last_render_cache.get(device_id)`，如存在→补发一次。
  - 暴露便捷发送：`async def send_to_device(device_id: str, payload: dict) -> bool`。

- `backend/core/connection.py`
  - 握手成功后：调用 `render_orchestrator.show_welcome(conn)`（可选）。
  - 处理设备上行 `ui.ack`（记录 ACK/耗时/失败重试计数）。

- `backend/core/handle/textHandle.py`
  - 在 `mode.start(meeting)` → `await render_orchestrator.meeting_enter(conn)`。
  - 在 `meeting.phase=="finalize"` → `await render_orchestrator.meeting_finalize_ack(conn)`；待总结完成后 `meeting_show_summary`。
  - `workflow.update` → `working_show_list`；`coding.*` → `coding_show_log`。

- `backend/core/http_server.py`（可选）
  - 新增只读演示接口：
    - `GET /supie/render/last?deviceId=...`：返回缓存的最后渲染。
    - `POST /supie/demo/flow`：触发一键全流程演示（内部调用 orchestrator）。

数据/行为约束
- 每设备渲染发送限频（默认≤2 QPS），超限丢弃旧帧并计数；`last_render_cache` 始终更新为最新帧。
- 所有下行渲染在发送前调用 `render_schema.validate_render_payload()` 防御性清洗。

——

## 2. 硬件代码骨架清单（模块 + 对接点）

新增文件
- `hardware/main/display/eink_render_engine.h`
  - `struct RenderHeader { std::string title; bool icon_rec; int battery; std::string net; };`
  - `struct PageInfo { int index; int total; };`
  - `enum class BodyKind { LIST, BULLETS, TEXT, LOGS, KV };`
  - `struct RenderBody { BodyKind kind; std::vector<std::string> items; std::string text; /* kv可后续扩展 */ };`
  - `struct RenderFooter { std::string hint; PageInfo page; };`
  - `struct RenderPayload { std::string page; RenderHeader header; RenderBody body; RenderFooter footer; std::vector<std::string> regionsChanged; std::string id; };`
  - `class EinkRenderEngine { public: void Init(EinkDisplayST7306* disp); bool Render(const RenderPayload& p); /* 返回是否成功 */ private: bool DrawHeader(const RenderHeader&); bool DrawBody(const RenderBody&); bool DrawFooter(const RenderFooter&); /* 内部做UTF-8 截断/分页/脏矩形 */ };`

- `hardware/main/display/eink_render_engine.cc`
  - 实现三分区渲染，当前版本先整屏刷新 + 500ms 合并节流；预留 `regionsChanged` 做局部刷新（驱动就绪后切换）。

修改文件
- `hardware/main/application.cc`
  - JSON 路由合并：仅保留两类下行处理入口
    - `void HandleUiRender(const cJSON* msg)` → 解析为 `RenderPayload`，调用 `EinkRenderEngine::Render()`，随后 `SendAckIfHasId()`。
    - `void HandleDeviceControl(const cJSON* msg)` → `listen.start/stop` → 开/停音频推流；`play.tone/tts` → 播放提示音/走本地或后端；`page.next/prev` → 驱动翻页并重绘。
  - ACK：
    - `void SendAckIfHasId(const std::string& id)` → 发送 `{type:"ui.ack", id, status:"ok"}`。
  - 清理：移除“硬件自知模式”的状态与大部分页面渲染逻辑（保留必要的音频/网络/显示初始化）。

- `hardware/main/protocols/websocket_protocol.*`（如需）
  - 保持 `SendJson/OnIncomingJson`；无需新增类型，仅转发到 `application.cc` 的两个入口。

渲染与刷新策略
- 先整屏 + 合并节流（≥500ms），避免E‑ink闪烁；保留 `regionsChanged` 钩子，后续切矩形局刷。
- 文本渲染：UTF‑8 安全截断，列表/日志每页≤8条，页脚统一“第x/共y页”。

——

## 3. 关键接口对接点（文件/函数）

- 后端
  - `backend/core/websocket_server.py`：`register_device_handler()` 成功后补投 `last_render_cache`；`send_to_device()` 统一出口。
  - `backend/core/connection.py`：握手完成后可调用 `orchestrator.show_welcome()`；处理 `ui.ack` 统计。
  - `backend/core/handle/textHandle.py`：将 `mode/meeting/workflow/coding` 事件转发至 orchestrator（不再下发“页面细节”，由 orchestrator 构造）。

- 硬件
  - `application.cc::OnIncomingJson(...)` → 分派到 `HandleUiRender/HandleDeviceControl`。
  - `EinkRenderEngine::Render(...)` → 调用 `EinkDisplayST7306` 的现有绘制能力完成三分区刷新。
  - 录音通路：`listen.start/stop` → 控制 `audio_processor_`/OPUS 推流；保留既有实现，仅改由 `device.control` 驱动。

——

## 4. D1–D3 分工与里程碑

- D1（骨架联通）
  - 后端（w+d）：`render_schema/orchestrator/sender/last_render_cache` 最小实现；`websocket_server` 注册补投；`textHandle` 事件→orchestrator。
  - 硬件（p）：`EinkRenderEngine` 雏形与三分区整屏渲染；`application.cc` 接口与 ACK；实现 `listen.start/stop`。
  - 通过：欢迎页→会议聆听页 + 录音开启；ACK 正常；断连重连补投。

- D2（三模式闭环 + 并发/离线）
  - 后端（w+d）：`meeting_finalize_ack/summary`、`working_list`（分页）、`coding_log`（滚动）；限频与队列门控；10+ 并发与3台互动；离线设备补投“最后渲染”。
  - 硬件（p）：文本截断/分页/页脚；网络横幅；断连后自动请求恢复渲染。
  - 通过：四类页面全部渲染；并发≥10；三台互动；离线补投成功。

- D3（演示化与守护）
  - 后端（w）：API Token 中间件；`/supie/demo/flow` 一键演示；ACK/失败重试统计与日志。
  - 硬件（p）：分区签名比对（减少无效重绘）；节流整合；页面导航指令。
  - 测试（d）：`ws_render_demo.html` 与 `run_render_flow.py`；录屏与验收报告。

——

## 5. 验收清单（硬性）

- 对话/会议/工作/编码“所有页面”均可通过 `ui.render` 正确渲染；
- `device.control` 能开启/停止录音、触发提示音、页内翻页；
- 并发≥10连接稳定；≥3台互动（A发起→B/C 同步渲染）；
- 离线补投：设备重连后收到“最后渲染”快照；
- 内网部署 + API Token 鉴权下运行；
- 回滚：一键关闭 `render.enabled`（后端不再下发渲染），硬件改为本地静态页面演示。

——

## 6. 回滚与配置开关（建议）

- 后端 `server.config`：
  - `render.enabled: true|false`
  - `render.qps_limit_per_device: 2`
  - `render.wait_ack: false`
  - `render.offline_redeliver: true`

- 硬件编译开关：
  - `EINK_PARTIAL_UPDATE`（后续启用矩形局刷时打开）
  - `RENDER_THROTTLE_MS=500`

——

## 7. 附：最小页面负载样例

欢迎页
```json
{ "type":"ui.render", "page":"welcome", "header":{ "title":"欢迎" }, "body":{ "kind":"text", "text":"正在连接…" }, "footer":{ "hint":"成功连接后将进入对话" }, "regionsChanged":["header","body"] }
```

工作列表（分页）
```json
{ "type":"ui.render", "page":"working.list", "header":{ "title":"工作模式" }, "body":{ "kind":"list", "items":["[P0] 修复登录","[P1] 优化列表", "[P2] 编写用例", "[P3] 文档整理" ] }, "footer":{ "hint":"短按翻页", "page":{ "index":1, "total":2 } }, "regionsChanged":["body","footer"], "id":"wk-001" }
```

编码日志
```json
{ "type":"ui.render", "page":"coding.log", "header":{ "title":"编码模式" }, "body":{ "kind":"logs", "lines":["build: 拉起构建","test: 单测通过","deploy: 部署完成" ] }, "footer":{ "hint":"phase: build" }, "regionsChanged":["body"], "id":"cd-001" }
```



```

已将“渲染协议契约”扩展为完整规范（v1）并写入 `collaboration/build.md`：
- 全量字段与行为：`ui.render | device.control | ui.ack | ui.error`、`id/ts`、向前兼容要求
- 页面与槽位定义：header/body/footer、五种 body.kind、regionsChanged 行为建议
- 设备与后端行为：ACK 时机、错误上报、限频与补投、并发顺序
- 错误码枚举与示例：`INVALID_PAYLOAD/RATE_LIMITED/BUSY/...`
- 多页示例：welcome/dialog/meeting.listen/meeting.summary/working.list/coding.log、控制指令、ACK/error

可据此并行实现后端编排与硬件渲染引擎。需要我先起后端 `render_schema.py/render_orchestrator.py` 骨架吗？

