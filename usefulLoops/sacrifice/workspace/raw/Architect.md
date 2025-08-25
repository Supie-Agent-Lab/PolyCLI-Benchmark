# 全栈架构演进方案讨论
_Exported on 2025/8/24 at GMT+8 21:11:40 from Cursor (1.4.5)_

---

**User**

  "role": "你是一位世界级的全栈顶级架构师，具备贯穿技术演进（过去/现在/未来）的全局视野与务实判断。你的目标是在满足业务长期价值的前提下，给出可落地、可验证、性能优雅且避免过度设计的演进方案。在多轮对话中，你需要用高中生能听懂的方式解释‘是什么/为什么/怎么做’，遵循80/20原则，优先解决最关键的20%问题以覆盖80%的需求。禁止展示思维链，仅输出必要的结论、依据与行动项。",
  "context": {
    "known_facts": [
      "需分析用户提供的项目资料（如代码、`@index.md`、`@log.md`）来评估现状（As-Is），并基于新需求设计最优的演进方案（To-Be）。",
      "所有技术决策必须以长期业务价值为最高准则，保持中立、客观且可验证。",
      "运行环境应能访问并解析通过`@`符号引用的本地文件或目录。若无法访问，必须在第一时间明确声明此限制，并请求用户提供替代材料。"
    ],
    "assumptions": [
      "目标受众是技术负责人、架构师和产品负责人的混合团队，因此沟通需兼顾技术深度与业务影响。",
      "默认输出格式为结构化Markdown，语气专业、简洁。",
      "所有未由用户提供的引用、数据与指标，统一标注为 'source required'，并在最终的 'Citations' 部分列出所需来源。",
      "如果未提供具体的时间规划，则使用‘Qx YYYY’或‘里程碑 X’作为占位符，并同样标注 'source required'。"
    ]
  },
  "task": {
    "workflow": [
      "1. **分析 (Analyze)**: 深入理解用户的原始意图、业务目标、受众、约束及成功标准。精确抽取所有可验证的数据点和潜在的风险假设。",
      "2. **诊断 (Diagnose)**: 识别并标记输入信息中的歧义、缺失信息、范围失衡或不可验证的断言。基于诊断，提出不超过3个最关键的澄清问题以弥补信息鸿沟。",
      "3. **重构 (Reconstruct)**: 设计并阐述推荐的目标架构及其边界。补充必要的上下文，将实施路径分解为清晰的步骤和核查清单，并明确说明关键决策的取舍（trade-offs）与备选方案。",
      "4. **验证 (Validate)**: 确保方案具备可执行性、可测试性和可复用性。检查输出格式是否合规，引用是否完整。严格遵守不泄露思维链的约束。",
      "5. **规划 (Plan)**: 输出分阶段的、可操作的迁移路径，包括具体的任务、里程碑、潜在风险及应对策略。必须包含回滚计划或灰度发布策略。"
    ],
    "checklist": [
      "已确认可访问所有`@`引用的文件；若无法访问，已在回复起始处声明限制并请求替代材料。",
      "已完整覆盖现状评估（As-Is）、目标架构（To-Be）、设计原理与取舍、分阶段迁移计划、风险与对策这五大核心模块。",
      "所有引用的信息均已提供可验证的来源（链接、文件名、编号）；缺失处已明确标注 'source required'。",
      "关键的架构决策和其业务影响已通过高中生能理解的简明语言进行了解释和总结。"
    ]
  },
  "output_format": {
    "type": "markdown",
    "schema": {
      "H1": "1. 现有架构评估 (As-Is Assessment)",
      "H3_1": "优点 (Pros)",
      "H3_2": "缺点与挑战 (Cons & Challenges)",
      "H1_2": "2. 需求合理性与影响分析 (Requirement & Impact Analysis)",
      "List_Items_2": ["业务目标与新需求", "合理性评估", "架构冲击"],
      "H1_3": "3. 推荐目标架构与设计原理 (Target Architecture & Principles)",
      "H3_3_1": "架构总览",
      "H3_3_2": "关键设计决策与理由 (Why)",
      "H3_3_3": "技术选型权衡",
      "H1_4": "4. 具体实施与迁移路径 (Implementation & Migration Path)",
      "H3_4_1": "分阶段计划 (e.g., 阶段一：...)",
      "H3_4_2": "风险与应对策略 (Risks & Mitigations)",
      "H3_4_3": "Citations"
    }
  },
  "constraints": [
    "严格禁止输出思维链（chain-of-thought）。仅提供最终的结论、关键依据和结构化的结果。",
    "所有信息来源必须可验证（URL、文件名、参考编号），无法验证处明确标注 'source required'。",
    "架构设计优先满足长期业务价值和系统的可运维性，坚决避免不必要的复杂性或过度设计。",
    "对关键技术术语进行最简化解释，必要时使用类比或示例，但保留标准的技术名词以便精确沟通。",
    "如果因环境限制无法访问`@`引用的文件，必须首先声明该问题，暂停给出深度结论，并等待用户提供信息。"
  ],
  "evaluation": [
    "**清晰度**: 输出严格遵守指定的Markdown结构，语言专业简洁。",
    "**可执行性**: 提供的迁移步骤清晰、可落地，风险和对策具有现实意义。",
    "**可验证性**: 引用来源完整或已明确标记缺失项，所有结论都有据可循。",
    "**复用性**: 整个分析框架和输出模板具有高度的可复用性，能迁移至不同项目。",
    "**决策透明度**: 关键决策的利弊、成本和风险都得到了均衡且透明的阐述。"
  ],
  "clarification_questions": [
    "1. 请提供所有相关的 `@` 文件清单和关键代码的目录结构。如果无法直接提供访问权限，请分享其内容的节选或替代链接。",
    "2. 该项目的核心业务北极星指标是什么？验收新架构的量化标准具体有哪些（例如，延迟需低于200ms，成本需降低30%）？",
    "3. 在时间、预算、团队技能或合规性方面，是否存在任何不可逾越的硬性约束（例如，必须在两个季度内上线，必须使用私有云部署）？"
  ]

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

---

**User**

请用高中生能听懂的方式简单和我解释ui.render | device.control | ui.ack | ui.error、id/ts 这些分别有什么用? 举例子说明

---

**Cursor**

### 用一句话说明
- `ui.render`：后端发“请把这页画出来”的指令。
- `device.control`：后端发“请做个动作”的指令（开录音、播提示音、翻页…）。
- `ui.ack`：设备回“我完成了”的回执。
- `ui.error`：设备回“出错了”的说明。
- `id`：像快递单号，用来一一对应请求和回执。
- `ts`：时间戳（毫秒），记录这条消息是什么时间发的，便于排序与排查。

### 详细但好懂的解释
- **`ui.render`（渲染页面）**：后端告诉设备“把屏幕按这个内容显示”。  
  - 类比：老师发投影PPT第3页，告诉你标题/正文/底部提示该怎么摆。
- **`device.control`（控制动作）**：后端像遥控器一样让设备做事。  
  - 例：开始/停止录音(`listen.start/stop`)、播放提示音(`play.tone`)、翻页(`page.next`)。
- **`ui.ack`（确认完成）**：设备做完后回一句“OK”，让后端知道已成功。
- **`ui.error`（报错）**：设备没做成，告诉后端是什么错（例如格式不对、频率太快、硬件忙）。
- **`id`（唯一编号）**：每条指令的“条形码”。后端用它确认哪条完成了；设备用它标注哪条失败了。
- **`ts`（时间戳）**：后端打的时间标签。遇到乱序/重发时，能按时间判断新旧，方便排查。

### 小例子
- 后端让设备进入“会议聆听”页，并开始录音
```json
{ "type": "ui.render", "id": "meet-001", "ts": 1730000000001,
  "page": "meeting.listen",
  "header": { "title": "会议模式", "icons": { "net": "ok", "rec": true } },
  "body": { "kind": "list", "items": ["已连接后端", "请开始发言…"] },
  "footer": { "hint": "双击结束并生成纪要" }
}
```
- 设备渲染完成后回执
```json
{ "type": "ui.ack", "id": "meet-001", "status": "ok" }
```
- 后端紧接着让设备开始录音
```json
{ "type": "device.control", "id": "ctl-100", "ts": 1730000000002, "action": "listen.start" }
```
- 设备执行完成再次回执
```json
{ "type": "ui.ack", "id": "ctl-100", "status": "ok" }
```
- 如果设备太忙（比如刷新过于频繁）就报错
```json
{ "type": "ui.error", "id": "meet-001", "code": "RATE_LIMITED", "message": "render qps exceeded" }
```

### 为什么需要它们
- **清晰分工**：`ui.render` 负责“画面”，`device.control` 负责“动作”。
- **可验证**：用 `id` + `ui.ack` 能明确知道“哪条”完成了。
- **可诊断**：`ui.error` + `ts` 让问题定位更快（是旧消息？还是格式错？还是频率超了？）。

```json
{ "type": "ui.render", "id": "meet-001", "ts": 1730000000001,
  "page": "meeting.listen",
  "header": { "title": "会议模式", "icons": { "net": "ok", "rec": true } },
  "body": { "kind": "list", "items": ["已连接后端", "请开始发言…"] },
  "footer": { "hint": "双击结束并生成纪要" }
}
```

```json
{ "type": "ui.ack", "id": "meet-001", "status": "ok" }
```

```json
{ "type": "device.control", "id": "ctl-100", "ts": 1730000000002, "action": "listen.start" }
```

```json
{ "type": "ui.ack", "id": "ctl-100", "status": "ok" }
```

```json
{ "type": "ui.error", "id": "meet-001", "code": "RATE_LIMITED", "message": "render qps exceeded" }
```

---

**User**

有个问题 这个渲染协议契约是唯一契约吗? 在哪里显示硬件的mac地址?

---

**Cursor**

### 简答
- 不是唯一契约。渲染协议只负责“怎么画/做什么动作”。还有基础契约：WebSocket 握手（带 `device-id`/`client-id` + Token）、以及回执/报错（`ui.ack/ui.error`）。
- 硬件的 MAC（即 `device-id`）不单独做协议字段，而是由后端在生成页面时，直接放进要渲染的内容里显示即可。

### 怎么显示 MAC（推荐做法）
- 在欢迎或对话页的标题中附带：
  - `header.title: "欢迎 · 80:b5:4e:ee:cb:60"` 或 `header.title: "对话 · 80:b5:4e..."`（截断）
- 在正文里以列表/文本显示：
  - `body: { kind: "list", items: ["设备ID: 80:b5:4e:ee:cb:60", "..."] }`
- 在页脚提示：
  - `footer.hint: "设备ID 80:b5:4e:ee:cb:60"`
- 临时横幅（提示条）：
  - `device.control: { type:"device.control", action:"net.banner", text:"设备 80:b5:4e:ee:cb:60 已连接", level:"info" }`

说明：
- 后端已从 WS 握手的 `?device-id=<mac>` 获取身份，因此在编排 `ui.render` 时把该值注入 `header/body/footer` 任一槽位即可显示。无需修改协议结构。

---

**User**

现在## 0. 渲染协议契约是不是已经足够完善,可以开始让硬件工程师制作硬件渲染引擎和后端开始调整了?

---

**Cursor**

### 结论
- 是的，`## 0. 渲染协议契约（完整规范 v1）`已足够启动硬件渲染引擎开发与后端编排调整，可并行开工。

### 开始前最后确认（不改协议，只是执行口径）
- 渲染限频：每设备 ≤2 QPS；设备端整屏渲染合并节流 ≥500ms。
- 分页约定：列表/日志每页≤8条；UTF‑8 安全截断，必要时尾部省略号。
- ACK 规则：带 `id` 的 `ui.render/device.control`，设备完成后回 `{type:"ui.ack", id, status:"ok"}`；失败回 `{type:"ui.error", code:...}`。
- 补投策略：设备重连/hello 后，后端仅补投“最后一次渲染”快照。
- 设备ID展示：由后端把 `device-id` 注入 `header/body/footer` 文案显示（协议无需新增字段）。
- 局部刷新：当前不要求，先整屏+节流；后续可利用 `regionsChanged` 做局刷优化。

### 今日落地分工（即可开工）
- 硬件（p）
  - 新建 `EinkRenderEngine::{Init, Render, DrawHeader, DrawBody, DrawFooter}`（三分区，整屏+节流）。
  - `application.cc` 增加 `HandleUiRender/HandleDeviceControl` 与 ACK 发送；`listen.start/stop` 驱动音频推流。
- 后端（w+d）
  - 新建 `render_schema.py`（校验/清洗）、`render_sender.py`（限频+最后渲染缓存）、`render_orchestrator.py`（welcome/meeting.enter/finalize_ack/summary/working.list/coding.log）。
  - `websocket_server` 注册成功后补投“最后渲染”；`textHandle` 调 orchestrator。
  - 准备最小联调脚本/页面下发示例载荷。

如需，我可按此直接生成上述后端/硬件文件骨架（空实现 + 函数签名），方便即刻提交与编译。

---

**User**

我不太确定“
后端把 device-id 注入 header/body/footer 文案显示（协议无需新增字段）。” 这个描述中的device-id是什么意思?

我希望实现:
设备ID的展示应该在后端有对应的存放位置 比如 硬件mac地址(94:a9:90:07:9d:88) 对应的是工牌编号001 由文先生持有 



---

**Cursor**

### 简答
- **device-id 是什么**：就是设备在 WebSocket 握手里带的“设备标识”。建议取硬件的 MAC（小写、冒号分隔），例如 `94:a9:90:07:9d:88`。
- **你要的映射（MAC → 工牌编号/持有人）**：放在后端的“设备注册表”里，后端据此把人类可读信息（如“工牌001 · 文先生”）写进 `ui.render` 的文案槽位（header/body/footer）去显示。协议本身无需新增字段。

### 最小落地方式
- **存放位置（二选一）**
  - 方案A（推荐快速）：`backend/data/devices.yaml`
  - 方案B（合并到现有配置）：`backend/data/.config.yaml` 新增 `devices:` 段
- **示例内容**
```yaml
devices:
  "94:a9:90:07:9d:88":
    badge: "001"
    owner: "文先生"
    alias: "badge-001"   # 可选：显示/调试别名
```

### 后端怎么用
- 握手解析出 `device-id`（标准化成小写 MAC）→ 查 `devices[...]` → 得到 `badge/owner`。
- 在编排 `ui.render` 时，把信息写入文本槽位即可展示（无需改协议结构）。

### 渲染时怎么显示（示例）
- 欢迎页标题展示工牌与持有人：
```json
{
  "type": "ui.render",
  "page": "welcome",
  "header": { "title": "工牌001 · 文先生" },
  "body":   { "kind": "text", "text": "设备ID 94:a9:90:07:9d:88" },
  "footer": { "hint": "已连接后端，准备就绪" }
}
```
- 会议页展示在 footer 或 list 中：
```json
{
  "type": "ui.render",
  "page": "meeting.listen",
  "header": { "title": "会议模式 · 工牌001" },
  "body":   { "kind": "list", "items": ["持有人：文先生", "设备ID：94:a9:90:07:9:88", "请开始发言…"] },
  "footer": { "hint": "双击结束并生成纪要" }
}
```

### 边界与回退
- 找不到映射时：显示 MAC 即可（例如 `header.title: "设备 94:a9:90..."`），后端日志提示“未注册设备”。
- 可选增强：提供一个只读接口或 `update_config` 热更，把 `devices` 映射在运行期更新。

```yaml
devices:
  "94:a9:90:07:9d:88":
    badge: "001"
    owner: "文先生"
    alias: "badge-001"   # 可选：显示/调试别名
```

```json
{
  "type": "ui.render",
  "page": "welcome",
  "header": { "title": "工牌001 · 文先生" },
  "body":   { "kind": "text", "text": "设备ID 94:a9:90:07:9d:88" },
  "footer": { "hint": "已连接后端，准备就绪" }
}
```

```json
{
  "type": "ui.render",
  "page": "meeting.listen",
  "header": { "title": "会议模式 · 工牌001" },
  "body":   { "kind": "list", "items": ["持有人：文先生", "设备ID：94:a9:90:07:9:88", "请开始发言…"] },
  "footer": { "hint": "双击结束并生成纪要" }
}
```

---

**User**

我希望使用方案A 请给我生成;

我希望渲染时只显示持有人和工牌编号,不显示设备mac地址;

找不到映射时：也不显示 MAC，后端日志提示“未注册设备”即可。

---

**Cursor**

我将新增设备映射文件，并填入你提供的示例（仅显示工牌编号与持有人；找不到映射时不显示 MAC，由后端记录“未注册设备”日志）。现在创建 backend/data/devices.yaml。

```yaml
devices:
  "94:a9:90:07:9d:88":
    badge: "001"
    owner: "文先生"


```

已创建映射文件:
- backend/data/devices.yaml
```yaml
devices:
  "94:a9:90:07:9d:88":
    badge: "001"
    owner: "文先生"
```

使用口径:
- 后端渲染时只取 `badge/owner` 注入文案，如“工牌001 · 文先生”；不显示 MAC。
- 无映射：不在 UI 显示任何设备标识，仅在日志记录“未注册设备: <mac>”。需要我把读取逻辑与注入示例加到 orchestrator 草案里吗？

```yaml
devices:
  "94:a9:90:07:9d:88":
    badge: "001"
    owner: "文先生"
```

---

**User**

##新增几块硬件
80:b5:4e:ee:cb:60 对应编号002 和彭先生
d0:cf:13:25:02:7c 对应编号003 和邓先生

## 我还需要确认一点
硬件 是先新建 EinkRenderEngine好还是先删除原先的逻辑好?

---

**Cursor**

我先把两台新设备写入 devices.yaml，然后给出“先新建还是先删除”的取舍建议与落地步骤。现在执行修改。

```yaml
devices:
  "94:a9:90:07:9d:88":
    badge: "001"
    owner: "文先生"
  "80:b5:4e:ee:cb:60":
    badge: "002"
    owner: "彭先生"
  "d0:cf:13:25:02:7c":
    badge: "003"
    owner: "邓先生"


```

- 已新增设备映射到 `backend/data/devices.yaml`:
```yaml
devices:
  "94:a9:90:07:9d:88": { badge: "001", owner: "文先生" }
  "80:b5:4e:ee:cb:60": { badge: "002", owner: "彭先生" }
  "d0:cf:13:25:02:7c": { badge: "003", owner: "邓先生" }
```

- 关于“先新建 EinkRenderEngine 还是先删除原逻辑”的建议：
  - 先新建，再渐进替换。理由：可并行联调、降低不可用风险、保留紧急回退。
  - 最小步骤：
    1) 新建 `EinkRenderEngine` 文件与 `application.cc` 两个入口（`HandleUiRender/HandleDeviceControl`），不动旧模式逻辑。
    2) 在编译开关或运行时开关下，优先走新路径；异常时可快速切回旧逻辑。
    3) 完成对话/会议/工作/编码四页渲染与 ACK 后，再删旧模式相关渲染分支。
  - 回退方案：`render.enabled=false`（后端）+ 硬件开关切回旧渲染路径，保障演示不受阻。

```yaml
devices:
  "94:a9:90:07:9d:88": { badge: "001", owner: "文先生" }
  "80:b5:4e:ee:cb:60": { badge: "002", owner: "彭先生" }
  "d0:cf:13:25:02:7c": { badge: "003", owner: "邓先生" }
```

---

**User**

@devices.yaml 增加 组概念 这几块硬件板子都属于硬件部; 然后随机新增几块板子和持有者 分别归入(研发部) / (生态部) /  (算法部)

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

