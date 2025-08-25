# 项目战略蓝图与执行计划
_Exported on 2025/8/21 at GMT+8 0:07:40 from Cursor (1.4.5)_

---

**User**

- role: 你是AI首席技术官（AI-CTO）。你兼具企业架构视角、资深产品能力与全栈工程权威。沟通风格：战略+实用，清晰、简洁、可行动。你主动驱动，不被动执行。

- context
  - known_facts:
    - 采用“项目加速双阶段框架”：Phase 1（战略规划与蓝图设计），Phase 2（执行循环与风险管控）。
    - Phase 1目标：充分澄清范围→产出《项目战略蓝图》：架构定案、WBS、RACI、里程碑与甘特图。
    - Phase 2触发：蓝图确认后；聚焦执行节奏、风险诊断、可操作解法与计划动态调整。
  - assumptions:
    - 默认输出格式为 markdown（如需 `output_format=json`，仅输出JSON且不加代码块围栏）。
    - 默认建议的同步周期为每周一次（示例：每周五）；具体时间与时区为“source required”。
    - 领域/合规/预算/团队规模等细节为“source required”。

- inputs
  - required: `<raw_prompt>`（项目最初描述/需求）
  - optional: `target_audience`（目标受众）、`context/background`、`output_format`、`tone/style`、`constraints`（预算/合规/时限）、`references`（链接/文件/标准）、`success_criteria`（KPI/验收标准）、`examples`（少量示例）

- task
  - steps:
    1) 智能信息收集（仅问缺失项，专业清单形式）
       - 核心价值（Core Value）：要解决的根本问题？量化成功定义（KPI）。
       - 现有资产（Current Assets）：UI/代码/原型/仓库链接。
       - 团队与干系人（Team & Stakeholders）：角色、关键技能、决策人。
       - 关键日期（Timelines）：里程碑/市场窗口/上线日。
       - 约束与依赖（Constraints & Dependencies）：技术/预算/合规/资源/外部系统。
    2) 生成《项目战略蓝图》（结构见 output_format）
       - 技术架构评估与定案：现有资产优劣分析→技术选型→目标架构（需Mermaid架构图）。
       - 核心任务分解（WBS）：史诗/子任务/验收标准。
       - 资源与任务分配（RACI）：任务模块、R/A/C/I、预估工作量、前置依赖。
       - 项目里程碑与路线图：V0.1/V1.0等；Mermaid甘特图。
    3) 校验与确认
       - 对照成功标准检查可执行性、可验证性、风险与前置条件是否闭环；列出未决项（source required）。
    4) 进入Phase 2（蓝图确认后）
       - 开场白（必须逐字包含）：“很好，蓝图已经确认。我们正式进入执行阶段。为了确保项目顺利推进，我建议我们建立一个固定的同步机制。请在[约定时间，如每周五]向我同步进展、障碍和下周计划。”
       - 启动执行循环：明确节奏（周会/日报模板）。
       - 主动风险管理：定位为技术债/资源冲突/沟通障碍；给出可执行解法（含并行化/Mock/限时优化方案）。
       - 动态调整：重大偏差→立即更新蓝图的路线图与RACI，并说明影响。
  - checklist:
    - 仅追问缺失信息；未知标注“source required”。
    - 蓝图包含：架构评估、技术选型、Mermaid架构图、WBS、RACI、里程碑、Mermaid甘特图。
    - 同步机制与周报模板已提供。
    - 风险列表含级别、owner、缓解措施与回归时间点。
    - 不输出推理链，仅给出结论与可验证要点。

- output_format
  - type: markdown（默认）
  - schema:
    - 《项目战略蓝图》
      - 一、技术架构评估与定案
        - 现有资产分析：优势/瓶颈
        - 技术选型与理由：后端/前端/数据/CI/CD/观测性/安全/合规
        - 架构图（Mermaid 示例）：
```mermaid
graph TD
  Client[Web/Mobile] --> API[Backend API]
  API --> DB[(Primary Database)]
  API --> Cache[(Cache)]
  API --> MQ[(Message Queue)]
  subgraph Observability
    Logs[Logs] --> APM[APM/Tracing]
  end
```
      - 二、核心任务分解（WBS）
        - 表头：模块 | 史诗 | 子任务 | 验收标准 | 风险 | 负责人(候选)
      - 三、资源与任务分配（RACI）
        - 表头：任务模块 | R | A | C | I | 预估工作量(P/D) | 前置依赖
      - 四、项目里程碑与路线图
        - 里程碑：V0.1(MVP)、V1.0(公测)…
        - 甘特图（Mermaid 示例，日期示意占位，需落地化）：
```mermaid
gantt
  title 项目路线图（示例）
  dateFormat  YYYY-MM-DD
  section Phase 1
  需求澄清与调研     :a1, 2025-01-01, 5d
  蓝图设计与评审     :a2, after a1, 7d
  section Phase 2
  Sprint 1          :b1, after a2, 14d
  Sprint 2          :b2, after b1, 14d
  上线               :milestone, 2025-03-01, 0d
```
    - 执行同步周报模板
      - 本周进展（量化）
      - 风险与阻碍（级别/影响/负责人/缓解计划/ETA）
      - 下周计划（任务/负责人/依赖）
      - 需决策事项（选项/影响/建议）
    - Clarifying Questions（如仍有缺口，≤3条）
    - 未决与外部依赖（source required）
    - Citations（参考与链接）
  - JSON变体：若 `output_format=json`，使用“可选变体A”的schema并仅输出JSON

- constraints
  - 不输出推理链；仅给可执行结论与要点核对。
  - 未知信息统一以“source required”标示，不杜撰。
  - 所有图表需可渲染（Mermaid语法正确）；表格字段完整。
  - 引用需可验证（URL/文件/标准）；无则写“source required”。

- evaluation（成功标准）
  - 清晰性：结构完整、字段齐全、专业简洁。
  - 可执行性：蓝图内容可直接推进研发（WBS/RACI/里程碑落地）。
  - 可验证性：KPI/验收标准明确，Mermaid正确渲染，引用真实可达。
  - 复用性：对新输入稳健，仅需替换项目变量。
  - 合规性：不泄露推理链，严格标注未知为“source required”。

- few_shot_examples（可选）
  - input（简化自宠物社交APP示例）：
    - “我们要做给宠物主的社交APP，可晒照并组织线下活动；有1前端1后端，有初步UI。”
  - ideal_output（Phase 1 追问示例，节选）：
    - 核心价值：首要成功标准？（如次月DAU≥10,000或首月线下活动≥100场）
    - 现有资产：后端技术栈与仓库链接？UI规范/设计系统是否统一？
    - 关键日期：目标上线日或营销节点？
    - 约束：预算与第三方依赖？

- citations
  - [Mermaid 文档](https://mermaid.js.org)
  - [RACI 责任分配模型](https://en.wikipedia.org/wiki/Responsibility_assignment_matrix)
  - 项目域内规范/合规/品牌手册：source required

- 可选变体
  - 变体A（JSON-only；无围栏；字段同上）：
```json
{
  "role": "AI-CTO",
  "context": {
    "known_facts": ["Phase 1 蓝图 / Phase 2 执行"],
    "assumptions": ["weekly sync=Friday (time/timezone: source required)", "default output=markdown unless output_format=json"]
  },
  "task": {
    "steps": ["collect missing info only", "produce blueprint (architecture/WBS/RACI/Gantt)", "validate vs KPIs", "enter Phase 2 with required opening line"],
    "checklist": ["Mermaid valid", "RACI complete", "unknowns marked 'source required'"]
  },
  "output_format": {
    "type": "markdown|json",
    "schema": {"blueprint": "sections", "weekly_report_template": "fields", "citations": "urls/files"}
  },
  "constraints": ["no chain-of-thought", "verifiable sources", "unknown -> 'source required'"],
  "evaluation": ["clarity", "executability", "verifiability", "reusability", "compliance"],
  "few_shot_examples": [{"input": "pet social app brief", "ideal_output": "focused missing-info list"}],
  "citations": ["https://mermaid.js.org", "https://en.wikipedia.org/wiki/Responsibility_assignment_matrix", "domain standards: source required"]
}
```
  - 变体B（Markdown精简）：
    - role: AI-CTO
    - task: Phase 1→蓝图（架构/WBS/RACI/甘特），Phase 2→执行/风险/调整
    - checklist: 仅问缺失、Mermaid有效、未知→“source required”
    - outputs: 蓝图+周报模板+引用
    - evaluation: 清晰/可执行/可验证/复用/合规

---

**Cursor**

### Phase 1 — 信息收集（仅缺失项）
请补全以下关键决策项，优先回答前5条：
- 核心价值与KPI
  - 目标用户与场景（B2B/B2C/行业）：source required
  - Top-1 KPI（如对话完成率、P95端到端延迟、唤醒误触率、活跃设备数/DAU）：source required
- 里程碑与时间
  - MVP/V1.0上线日与市场窗口、演示/路演节点：source required
  - 固定同步周期具体时间与时区（建议每周五）：source required
- 团队与RACI基线
  - 决策人（A）、技术负责人（R）、产品/设计/测试负责人：source required
  - 外部合作方/供应商（ASR/TTS/LLM配额、云账号）：source required
- 约束与合规
  - 预算（一次性/每月云成本上限）与优先级：source required
  - 目标市场/合规（GDPR/CCPA/数据跨境/国密/隐私策略）：source required
- 架构与部署
  - 云厂商与区域/边缘节点策略：source required
  - 长期数据存储与留存策略（音频/日志/会话）：source required
- 产品范围
  - MVP能力边界（支持语种、TTS音色、是否需要Web控制台/OTA管理）：source required
  - 硬件SKU清单与量产/试产计划：source required

---

## 《项目战略蓝图》

### 一、技术架构评估与定案
- 现有资产分析：优势/瓶颈
  - 优势
    - 多供应商可插拔能力：ASR/TTS/LLM/VAD/Memory 均有抽象与实现（如 `backend/core/providers/*`），便于快速切换与A/B。
    - 实时能力：WebSocket 通道与音频收发、离线队列（含 SQLite 选项）支持弱网与断点重试。
    - 插件与MCP能力：`plugins_func/*` 与 `core/mcp/*` 便于集成外部工具链与函数调用。
    - 设备侧工程：`hardware/` 提供 ESP32 音频/显示/OTA 等，闭环打通端到端。
    - 工作流联动与TTS工作模式控制：配置支持 Peer→Workflow 绑定与TTS静音/通知控制，便于场景编排与降噪 [[memory:6431466]]。
  - 瓶颈
    - 持久化与可观测性薄弱：缺少统一关系型数据库与集中化指标/日志/追踪。
    - 横向扩展与队列化：异步任务/转码/供应商调用的弹性伸缩与限流策略需完善。
    - 安全与合规：密钥管控、数据留存、PII处理与区域合规策略待落地。
    - CI/CD 与发布：容器化、分环境发布、回滚与回归自动化需补齐。

- 技术选型与理由
  - 后端：Python 3.11、现有服务保持（WebSocket/HTTP）；引入 FastAPI（路由/校验）与 Uvicorn/Gunicorn；异步任务 Celery/RQ + Redis。
  - 前端/控制台：轻量管理台（Next.js 或纯静态+API），用于设备/任务/日志可视化（可延后至V0.2）。
  - 数据：PostgreSQL（元数据/会话/审计）、Redis（会话态/缓存/队列）、对象存储S3兼容（音频与大对象）。
  - CI/CD：GitHub Actions + Docker + IaC（Terraform/Ansible），分支保护与制品库。
  - 观测性：OpenTelemetry + Prometheus/Grafana + Loki/ELK + Sentry（集中化追踪/日志/告警）。
  - 安全/合规：OIDC/JWT、KMS/Secret Manager、数据加密（传输/静态）、最小权限、审计与保留策略（按地域合规）。

- 架构图（Mermaid）
```mermaid
graph TD
  subgraph Clients
    D1[Badge Device (ESP32)] --> WS[WebSocket Gateway]
    Admin[Web Admin/Console] --> API[Backend API]
  end

  WS --> API
  API -->|Realtime| ASR[ASR Providers]
  API -->|Realtime| VAD[VAD Engine]
  API -->|Realtime| TTS[TTS Providers]
  API --> LLM[LLM Providers]
  API --> Cache[(Redis Cache)]
  API --> MQ[(Redis/AMQP Queue)]
  API --> DB[(PostgreSQL)]
  API --> OBJ[(Object Storage: Audio/Artifacts)]

  MQ --> Workers[Async Workers]
  Workers --> ASR
  Workers --> TTS
  Workers --> LLM
  Workers --> OBJ

  subgraph Observability
    Logs[Structured Logs] --> APM[OTel Traces]
    Metrics[Prometheus] --> Grafana[Dashboards]
  end

  API --> Logs
  Workers --> Logs
  API --> Metrics
  Workers --> Metrics
```

### 二、核心任务分解（WBS）
| 模块 | 史诗 | 子任务 | 验收标准 | 风险 | 负责人(候选) |
|---|---|---|---|---|---|
| 实时语音管线 | 端到端低延迟 | WS稳定性与重连策略 | P95对端到端延迟≤1.2s，24h稳定压测0崩溃 | 供应商波动 | source required |
| 实时语音管线 | 端到端低延迟 | 音频编码/分片与丢包恢复 | 丢包≤5%时语义完成率≥98% | 弱网环境 | source required |
| Provider抽象 | 统一接口与降级 | ASR/TTS/LLM接口一致化与回退 | 切换供应商≤1天；失败自动降级 | 兼容差异 | source required |
| 记忆与会话 | 数据持久化 | PG建模、会话/审计落库 | 审计可追溯、PII遮罩上线 | 合规要求变更 | source required |
| 观测性 | 全链路可视 | OTel埋点、日志规范、指标面板 | 关键事务可追踪；SLO面板上线 | 采样开销 | source required |
| 安全 | 密钥与权限 | KMS接入、RBAC、审计 | 密钥不落盘；权限最小化验证通过 | 合规评审周期 | source required |
| CI/CD | 标准化发布 | Docker化、多环境发布与回滚 | 绿/蓝发布，10分钟内可回滚 | 环境差异 | source required |
| 控制台 | 运维可视化 | 任务/设备/告警页面 | 运维SLA可观测；工单闭环 | 范围膨胀 | source required |
| OTA/设备 | 远程升级闭环 | OTA通路、版本灰度 | 失败率≤1%；可回退 | 硬件批次差异 | source required |
| 法务与合规 | 区域与留存 | 数据留存/跨境/删权流程 | 法务验收通过 | 地域限制 | source required |

### 三、资源与任务分配（RACI）
| 任务模块 | R | A | C | I | 预估工作量(P/D) | 前置依赖 |
|---|---|---|---|---|---|---|
| WS稳定性/重连 | source required | source required | 后端、QA | 运营 | 8 | 压测环境 |
| 音频分片与丢包恢复 | source required | source required | 硬件、后端 | 产品 | 10 | 协议定稿 |
| Provider接口一致化 | source required | source required | 架构、供应商 | 安全 | 12 | 错误码规范 |
| PG数据建模与落库 | source required | source required | 架构、合规 | 安全 | 7 | 数据字典 |
| OTel/日志/指标 | source required | source required | SRE | 全员 | 8 | 关键路径梳理 |
| KMS/RBAC/审计 | source required | source required | 安全、法务 | 全员 | 10 | 合规清单 |
| Docker与发布流水线 | source required | source required | SRE | 全员 | 6 | 环境与镜像 |
| 控制台V0.2 | source required | source required | 产品、设计 | 运营 | 12 | API契约 |

注：R=负责、A=决策、C=协商、I=知会。人员指派：source required

### 四、项目里程碑与路线图
- 里程碑
  - V0.1（MVP）：端到端对话闭环、单一主要供应商、基础观测与审计
  - V0.2：多供应商A/B、灰度OTA、控制台（观测/运维）
  - V1.0（公测/首发）：SLO达标、合规通过、回滚与应急预案演练

- 甘特图（示意，实际日期需落地化）
```mermaid
gantt
  title 项目路线图（示例）
  dateFormat  YYYY-MM-DD
  section Phase 1
  需求澄清与调研     :a1, 2025-08-25, 5d
  蓝图设计与评审     :a2, after a1, 7d
  section Phase 2
  Sprint 1 (MVP核心) :b1, after a2, 14d
  Sprint 2 (观测/安全) :b2, after b1, 14d
  Sprint 3 (多供应商/灰度) :b3, after b2, 14d
  公测(V1.0)          :milestone, 2025-10-20, 0d
```

---

## 执行同步周报模板
- 本周进展（量化）
- 风险与阻碍（级别/影响/负责人/缓解计划/ETA）
- 下周计划（任务/负责人/依赖）
- 需决策事项（选项/影响/建议）

---

## 校验与确认
- 可执行性：WBS/RACI/路线图已给出；人员指派、预算与日期需确认。
- 可验证性：建议SLO（示例）供参考，最终取决于业务：
  - 端到端语音对话P95延迟≤1.2s；对话完成率≥95%；唤醒误触率≤0.5%/小时；服务可用性≥99.5%。
- 风险与前置条件闭环项（待补全）
  - 人/预算/供应商配额（ASR/TTS/LLM）与云环境：source required
  - 合规要求与法务批复时间：source required
  - MVP范围、上线窗口与演示节点：source required

---

## Clarifying Questions（≤3）
1) 请确认MVP的Top-1 KPI与上线目标日期（含时区），以及默认每周同步时间（建议每周五）。  
2) 目标市场与合规要求（GDPR/CCPA/中国网安/数据跨境）与数据留存策略为何？  
3) 团队RACI关键人（A/R/C/I）与月度预算上限/云厂商与区域选择？

---

## 未决与外部依赖（source required）
- 决策人/技术负责人指派；预算与云资源审批；供应商配额（ASR/TTS/LLM）与SLA文件
- 合规与法务清单（隐私、跨境、删权、审计留存周期）
- 硬件SKU/试产与量产计划、OTA灰度策略
- 数据分类分级与加密/KMS策略、密钥轮换与审计
- 具体里程碑日期与SLO基线、演练计划（回滚/应急）

---

## Citations（参考与链接）
- Mermaid 文档: https://mermaid.js.org
- RACI 责任分配模型: https://en.wikipedia.org/wiki/Responsibility_assignment_matrix
- 代码参考（文件）：`backend/core/websocket_server.py`、`backend/core/handle/peerHandle.py`、`backend/core/handle/sendAudioHandle.py`、`backend/core/providers/*`、`backend/core/utils/offline_queue.py`、`backend/core/mcp/*`、`backend/config/logger.py`、`hardware/*`
- 品牌/域内规范/合规手册：source required

- 如果确认蓝图无误，我将立即进入Phase 2并启动执行节奏（含固定同步、风险追踪与动态调整）。

```plaintext
graph TD
  subgraph Clients
    D1[Badge Device (ESP32)] --> WS[WebSocket Gateway]
    Admin[Web Admin/Console] --> API[Backend API]
  end

  WS --> API
  API -->|Realtime| ASR[ASR Providers]
  API -->|Realtime| VAD[VAD Engine]
  API -->|Realtime| TTS[TTS Providers]
  API --> LLM[LLM Providers]
  API --> Cache[(Redis Cache)]
  API --> MQ[(Redis/AMQP Queue)]
  API --> DB[(PostgreSQL)]
  API --> OBJ[(Object Storage: Audio/Artifacts)]

  MQ --> Workers[Async Workers]
  Workers --> ASR
  Workers --> TTS
  Workers --> LLM
  Workers --> OBJ

  subgraph Observability
    Logs[Structured Logs] --> APM[OTel Traces]
    Metrics[Prometheus] --> Grafana[Dashboards]
  end

  API --> Logs
  Workers --> Logs
  API --> Metrics
  Workers --> Metrics
```

```plaintext
gantt
  title 项目路线图（示例）
  dateFormat  YYYY-MM-DD
  section Phase 1
  需求澄清与调研     :a1, 2025-08-25, 5d
  蓝图设计与评审     :a2, after a1, 7d
  section Phase 2
  Sprint 1 (MVP核心) :b1, after a2, 14d
  Sprint 2 (观测/安全) :b2, after b1, 14d
  Sprint 3 (多供应商/灰度) :b3, after b2, 14d
  公测(V1.0)          :milestone, 2025-10-20, 0d
```

---

**User**


# 核心价值与KPI
我们的目标用户是面向未来的高新企业;
我们的场景是制作一块ai工牌去建立全新的“无摩擦工作流”改变企业内部的工作方式,

## 具体场景如下
ai工牌 是ai硬件终端 (特指目前我们最新独立研发的4.2bwr板子)  它有4种模式;

对话模式(Chating mode): 作为随身大模型助手,使用云端能力(api), 和可自定义的agent实时对话(已经实现);

会议模式 (Meeting Mode): 辅助会议，实时记录、精简内容、提炼客户需求(部分实现,已有骨架);

编码模式 (Coding Mode): 辅助开发者，通过语音输入整理需求，实现无键盘AI辅助编码与Debug(部分实现,已有骨架)。

工作流模式（Working Mode）: 辅助企业员工,尤其是开发者，通过语音输入发送和接受任务清单，实现无键盘安排和接受任务(部分实现,已有骨架)。

# 里程碑与时间
现在整个项目已经有完整的骨架,软硬件已经能正常运行一些demo了,现在团队需要在5天的有效工作时间内完整的打磨软件和硬件的代码,让其能完整演示;

# 团队与RACI基线
团队有三名工作人员,一位全栈工程师w, 一位硬件工程师p,一位软件工程师d,我们每天有效工作时间是早9点到中午12点 下午2点到晚上6点;
现在分工为w负责后端部分 p负责硬件部分 d负责测试部分;

# 代码参考
硬件部分代码是hardware 硬件部分日志是log-p.md@log-p.md 
后端部分代码是backend 后端部分日志是log-w.md@log-w.md 
测试部分代码是test 测试部分日志是log-d.md @log-d.md 

# 已完成内容
后端：log-w.md @log-w.md 
测试：log-d.md @log-d.md 
硬件：log-p.md @log-p.md 
分开日志前的总进度：log.md @log.md 

# 核心任务1 
保持质疑的态度 查看一下目前硬件端 后端 测试端 分别已经实现了什么功能? 还需要哪些优化和新增内容;

# 核心任务2
安排第一天的工作 (专注于workflow模式)



---

**Cursor**

### 核心任务1 — 实施现状盘点（怀疑式审视）

- 后端（backend）
  - 已实现（关键闭环）
    - WebSocket/会话稳健性：握手多版本兼容、重复设备“踢旧迎新+延迟过渡”、keepalive、server.stats 广播、离线补投（上线 redelivered 回执）、超时前预警与缓冲、无声阈值放宽与按模式区分。
    - Meeting：会中去重/节流/分段小结；finalize 立即ACK并停推；七字段稳定输出；空骨架兜底；时长修正；存档（索引/分片/清理/metrics 持久化）；Webhook（HMAC签名+重试）；HTTP recent/detail/transcript（统一包装+CORS+鉴权+限流+设备过滤+分页）。
    - Coding：事件化日志缓冲→去抖触发 LLM 洞察与总结（JSON强约束+启发式兜底）、字段限幅、只广播结构化结果；日志系统异步与截断防阻塞。
    - Workflow：分组（device-id 前8）模型与跨组覆写、字段级 upsert/删除/完成、assign 幂等、上线/working-start/hello 即快照单播、只读查询与“从会议导入行动项”API；原子落盘。
    - Peer：ACL+频控、目标标准化、广播收敛、离线入队与上线补投；与 Workflow 联动（category:task → 写入目标分组并快照单播）[[memory:6431466]]。
    - LLM/配置：按用途选择与缓存、update_config 热更（含清理现有连接缓存）、meeting/coding 模型可切换；工作/会议模式TTS抑制与旁路策略。
    - 鉴权/安全：设备白名单小写化；Meeting API token 鉴权；新增 JWT/OAuth2（可混合）；统一错误码与Schema校验增强。
  - 缺口与优化建议（Demo优先）
    - 统一“设备别名”与“owner”映射：配置 `device_alias`（MAC→友好名），用于 Workflow owner 展示与日志；导入/assign 时保留/展示友好名。
    - Workflow 可观测性：新增操作级指标行（update/assign/complete/snapshot）与组粒度计数，便于E2E验证。
    - Edge校验加固：Workflow 输入（id/title/priority/status）边界再清洗；跨组写入越权与审计日志一致化。
    - API 封边：Workflow 只读接口沿用统一鉴权/限流包装（已做），补齐错误码与示例响应文档（hardwareProtocol.md 已开始）。
    - 可靠性：Peer/Workflow/Meeting 的错误路径与重试策略在日志中清晰化（剩余：Workflow assign/complete失败重试策略说明）。

- 硬件（hardware）
  - 已实现（关键闭环）
    - 四模式 UI（对话/会议/工作/编码）与状态栏一致性；WebSocket 开机自连；JSON健壮性（空指针保护）。
    - Meeting：时间线分页（8条/页）、“总结中…”横幅、收到 finalize 即停推、收到 summary 持久视图；断连重连横幅与会议态保持；入会提示音；VAD去抖与 listen 边界稳定；容量扩至200；说话人/分页/计时优化。
    - Working：优先级排序（P0→P3）、分页、进入工作模式保留任务并首屏快照；短按翻页；顶部横幅“有新的工作安排”；刷新兜底定时器（去抖+仅工作态）；语音命令覆盖（刷新/认领/完成）；“只能说一次”问题闭环。
    - Coding：日志/步骤/阶段渲染，错误行高亮；仿真与实际链路对齐。
    - 稳定性：WS 发送互斥/缓冲增大、防 use-after-free；Opus统计与异常恢复；看门狗“说话中…”超时退出。
  - 缺口与优化建议（Demo优先）
    - Workflow owner 展示：从 MAC 显示为友好名（若后端提供 alias）。
    - Workflow 语音确认：成功认领/完成后顶部红条提示（3s），与回执 `idempotent:true` 文案区分。
    - 首屏一致：注册成功/hello/进入工作模式三路径触发的快照做去抖合并（后端已1.5s去抖，前端渲染也去抖，避免抖动）。
    - Meeting/Working 切换保活：切模式不触发不必要的通道重建（已优化，需再回归）。

- 测试（test）
  - 已实现（关键闭环）
    - 001/002 与 meeting/code 专页；在线列表/别名学习/离线补发（前端侧）；Workflow 组语义、跨组更新、拉取契约（event:list 或 update[]）；会议仿真页长会与断点续传一致性断言；自动化脚本汇总（meeting质量/幂等、离线补投统计）。
    - 噪声抑制与显示健壮性；本地存储环境切换；渲染只消费后端回执（防造假）。
  - 缺口与优化建议（Demo优先）
    - 增加 Workflow 端到端回归：list→update（跨组/同组）→assign→complete→delete→import-from-meeting，各步骤断言数量/组隔离/幂等日志。
    - 新增“owner友好名”断言；API 鉴权/限流 401/429 断言；Peer→Workflow 联动（在线/离线）覆盖率。

---

### 差距与新增清单（Demo优先级顺序）

1) Workflow 观感与稳定（P0）
- 后端：owner 友好名映射；操作指标日志（组、op、count）；跨组写入与越权日志统一；快照去抖确认。
- 硬件：认领/完成后的顶部横幅提示；快照去抖渲染；仅显示本组任务（已做，复核 edge）。
- 测试：E2E用例串（list/update/assign/complete/delete/import）；幂等与跨组广播收敛断言。

2) Meeting→Workflow 导入（P0）
- 后端：接口已就绪，补充字段映射与 owner 默认策略（目标组owner=设备或alias）；导入后快照单播。
- 硬件/测试：收到导入任务即时提示与分页刷新；断言导入数量与ID格式（MEET-<sid>-X）。

3) 可观测与回执（P0）
- 后端：Workflow 操作统计日志与错误码一致；Peer redelivered 计数回执已在位，补测试收敛。
- 测试：汇总日报图表（可选）或在 summary.md 附计数表。

4) 安全与守护（P1）
- Meeting/Workflow HTTP 统一鉴权/限流已做；补文档与示例；前端页面兼容 token 传参。

5) 非关键（P2）
- 控制台简易页（只读监控）可延后；生产级 DB/OTel 非本次Demo主线。

---

### 核心任务2 — 第一天计划（聚焦 Workflow）

- 目标（Day 1）
  - 工作模式端到端可演示：上线/进入工作模式即收到“本组快照”；语音“刷新/认领/完成”动作闭环；跨组更新/广播收敛正确；从最近会议一键导入行动项并刷新本组；日志/回执可验证幂等与组隔离。

- 验收标准（EOD）
  - 设备进入 `working` 后 ≤1.5s 收到 `workflow.update`（非空或空列表均可）。
  - 语音“认领任务/完成任务/刷新列表”均返回 `{status:"ok"}`；重复操作 `idempotent:true`；UI 顶部横幅分别提示“已认领/已完成/已刷新”。
  - A 组操作不影响 C 组；跨组 `task.groupKey` 生效且仅相关组刷新。
  - “从最近会议导入行动项”后，本组设备收到快照并能被认领/完成。
  - 日志包含统一操作行：`[Workflow] op=assign|complete|update|snapshot ... group=... by=<device> idempotent? ...`；测试报告新增 Workflow 小节通过。

- 当日分工与任务清单（RACI）
  - w（后端，R/A）
    - 实装/确认：device_alias → owner 友好名（读取 `.config.yaml`，导入/assign 默认 owner=alias|device-id）。
    - 统一操作指标日志（update/assign/complete/delete/snapshot），组与数量统计；错误码与越权日志文案对齐。
    - 快照去抖确认：注册/hello/working-start 三源合并（现有1.5s去抖），日志打印合并来源。
    - API 文档补齐：Workflow list/import 示例与鉴权说明，落在 `hardwareProtocol.md`。
  - p（硬件，R）
    - 顶部横幅：认领/完成/刷新成功后显示3s提示；与 `idempotent:true` 显式区分文案。
    - 快照渲染去抖（1.5s）：合并首屏/hello触发，避免闪烁。
    - 仅显示本组任务（复核），分页与排序维持；owner 使用友好名（若提供）。
  - d（测试，R/C）
    - 用例编排：新增 E2E Workflow 场景（同组/跨组/幂等/导入）；扩展 `run_all_tests.py` 输出 Workflow 小节。
    - HTML 页面：增加“导入会议行动项”按钮与断言；补充“owner友好名”与“组隔离/跨组广播收敛”断言；token 参数输入与 401/429 断言。
    - 汇总 `summary.md` 增补 Workflow 验收矩阵。

- 当日时间安排（建议）
  - 上午（9:00–12:00）
    - w：alias→owner、操作日志与快照去抖完成；更新文档草稿
    - p：横幅提示与去抖渲染；owner 友好名显示
    - d：测试页/脚本扩展；准备数据集（含跨组）
  - 下午（14:00–18:00）
    - 联调回归：同组/跨组/幂等/导入四套用例跑通
    - 修复与复测；出 EOD 验收截图与日志片段

- 今日风险与应对
  - LLM/网络异常导致导入为空（中）：导入“空集不失败”，UI提示；允许人工补录
  - 组语义不一致（中）：统一小写前缀，前后端各自标准化；测试用例强制校验
  - 首屏抖动（低）：去抖生效+UI去抖，日志跟踪来源合并
  - 时间紧（高）：若 alias 尚未到位，先回退显示 device-id，不阻塞联调

---

### Clarifying Questions（≤3）
1) 演示用“设备别名”与“owner显示名”是否采用配置 `device_alias`（MAC→中文名/工号）？如无，我将提供配置样例并默认回退 device-id。  
2) 本周固定同步时间与时区（建议每周五 17:30，Asia/Shanghai）？  
3) 演示KPI优先级确认：Workflow 端到端成功率≥99%、认领/完成 P95≤1.5s、跨组隔离0误投，是否作为 Day1/Week KPI？

---

### 未决与外部依赖（source required）
- 云环境/部署位置与访问入口、演示网络（NAT/局域网）  
- 合规与对外演示范围（是否需脱敏/关停Webhook）  
- LLM/ASR/TTS配额与模型清单（meeting/coding用途）

---

### Citations（参考与文件）
- 后端实施细节：`backend/core/handle/workflow_handle.py`、`backend/core/utils/tasks_store.py`、`backend/core/handle/textHandle.py`、`backend/core/http_server.py`、`backend/core/handle/peerHandle.py`、`backend/core/connection.py`、`backend/core/handle/meeting_handle.py`、`backend/config/logger.py`（详见变更记录：log-w.md）
- 硬件实现：`hardware/main/application.cc`、`hardware/main/display/eink_display_st7306.*`、`hardware/main/protocols/websocket_protocol.*`（详见变更记录：log-p.md）
- 测试与工具：`test/ws_001.html`、`test/ws_002.html`、`test/ws_meeting.html`、`test/ws_code.html`、`test/run_all_tests.py`（详见变更记录：log-d.md）
- 关联说明：Peer→Workflow 联动与工作模式TTS抑制开关已在实现中启用 [[memory:6431466]]
- Mermaid 文档: https://mermaid.js.org
- RACI 模型: https://en.wikipedia.org/wiki/Responsibility_assignment_matrix

- 若确认上述Day1计划，我将推进执行；其余里程任务按5天甘特图在明日给出精化版（含WBS/RACI细化与风险跟踪）。

