# 信息网络类刷题系统 功能设计说明书

（V 1.1 — 2025-08-07）

---

## 1  项目概述

* **目标** ：为参加"信息中心 2025 年 8 月作业人员资格考试"的考生提供一款轻量级、跨平台的刷题与模拟考试Web系统，覆盖复习、练习、统考模拟、成绩统计等完整闭环。
* **题源** ：全部来自《信息网络类.xlsx》（单选/多选/判断/小案例/大案例五个 sheet）。
* **核心诉求**
  1. "即装即用"——后台一键导入 Excel 后即可开放给考生使用。
  2. "自动组卷"——按题型、难度、随机乱序生成模拟卷；合格线 90 分；防切屏策略通过页面可见性API监控。
  3. "多人隔离"——账号注册、刷题记录、错题本均按用户隔离。
  4. "超轻部署"——后端仅依赖 Python + FastAPI + SQLite（单文件 DB）；前端采用 React + Vite 构建现代化Web应用，支持响应式设计适配PC/平板/手机。

---

## 2  系统架构

```
┌─────────────────┐
│   React Web     │  <–– HTTP(JSON)+Token ––>  ┌─────────────┐
│  (Vite + TS)    │                           │  FastAPI     │
│  响应式UI设计   │                           │  (uvicorn)   │
└─────────────────┘                           │  ▶SQLite     │
        │                                      │  ▶pydantic   │
        │  WebSocket(实时得分)                 │  ▶sqlmodel   │
        │                                      └─────────────┘
        ▼                                             │
  浏览器本地存储                                      │导入脚本
  (LocalStorage/                                      ▼
   SessionStorage)                        Excel→ETL→Question表
```

* **前端** ：
  * React 18 + TypeScript + Vite（现代化构建工具）
  * UI组件库：Ant Design 或 Material-UI
  * 状态管理：Redux Toolkit 或 Zustand
  * 路由管理：React Router v6
  * 图表渲染：ECharts for React
  * 本地缓存：LocalStorage存储错题本与最近成绩，支持离线查看
  * PWA支持：Service Worker实现离线缓存和推送通知
* **后端** ：
  * FastAPI + SQLModel（轻 ORM）
  * SQLite 数据库存储；单文件，Docker 镜像 < 50 MB
  * Excel 导入脚本：`python import_questions.py 文件路径`
  * JWT Token 认证（用户名 + 密码（bcrypt hash）；登录成功返回 JWT。）

---

## 3  主要功能模块

| 模块                | 子功能                                              | 关键点                                                          |
| ------------------- | --------------------------------------------------- | --------------------------------------------------------------- |
| **用户&权限** | 注册/登录（用户名 + 密码）、角色区分（管理员/考生） | 普通考生仅可做题查看自身数据；管理员可批量导入题库/查看全局统计 |
| **题库管理**  | Excel 导入、题目预览、批量启停                      | 解析五类 Sheet；字段映射见附录 A                                |
| **练习模式**  | 分类练习、随机练习、收藏/错题本                     | 题干、选项、解析分离储存；支持多图文                            |
| **模拟考试**  | 自动组卷、计时交卷、防切屏次数计数                  | 题型比例与总分由管理员后台配置                                  |
| **成绩统计**  | 个人统计（得分曲线、正确率）、全站统计              | WebSocket 推送实时得分；Echarts 渲染                            |
| **系统设置**  | 版本检查、缓存清理、反馈                            | 反馈直接记录到 `feedback`表                                   |

---

## 4  自动组卷逻辑

| 步骤                      | 说明                                                               |
| ------------------------- | ------------------------------------------------------------------ |
| 1. 读取管理员设置的卷规则 | 例：单选 40 ×1 分、判断 20 ×1 分、多选 20 ×2 分、案例 2 ×10 分 |
| 2. 分题型随机抽题         | `SELECT … ORDER BY RANDOM() LIMIT N`                            |
| 3. 乱序处理               | 题目顺序 & 选项顺序均打乱并写入 `ExamPaperDetail`                |
| 4. 计时开始               | 默认 60 分钟，可后台配置                                           |
| 5. 交卷 & 判分            | 多选题需完全匹配才得分；60 s 未返回即自动交卷                      |
| 6. 结果持久化             | `ExamResult`,`ExamAnswer`两表                                  |

---

## 5  数据模型（核心表）

| 表名           | 字段 (主要)                                                                        | 说明           |
| -------------- | ---------------------------------------------------------------------------------- | -------------- |
| `User`       | id, phone, name, role, password_hash                                               | 考生 & 管理员  |
| `Question`   | id, type, difficulty, category, stem, options(JSON), answer, explanation, keywords | 统一存放五类题 |
| `ExamPaper`  | id, user_id, start_time, end_time, score, cut_count                                | 一次模拟卷实例 |
| `ExamAnswer` | id, paper_id, question_id, user_answer, is_correct                                 | 逐题记录       |
| `Favorite`   | id, user_id, question_id, tag                                                      | 收藏/错题本    |
| `Feedback`   | id, user_id, content, screenshot_url                                               | 用户反馈       |

> SQLite 兼容 JSON 字段；如需迁移到 PostgreSQL 仅需改连接串。

---

## 6  API 接口示例

| 方法                             | 路径                                | 描述 |
| -------------------------------- | ----------------------------------- | ---- |
| `POST /auth/send_code`         | 发送短信验证码                      |      |
| `POST /auth/login`             | 手机+验证码登录，返回 JWT           |      |
| `GET  /questions`              | 列表查询（分页、按题型/关键词筛选） |      |
| `POST /exam/start`             | 创建一场模拟考试并返回题目列表      |      |
| `POST /exam/{paper_id}/submit` | 提交答案批卷                        |      |
| `GET  /stats/me`               | 当前用户练习/考试统计               |      |
| `POST /admin/upload_excel`     | 管理员上传题库文件                  |      |
| `GET  /admin/exam_rules`       | 获取/设置组卷规则                   |      |

---

## 7  页面&交互流程

1. **首页/登录页** → 用户名、密码输入 → 验证成功进入主界面
2. **主界面（导航栏+内容区）**
   * 顶部导航：分类练习、随机练习、模拟考试、我的统计、个人中心
   * 左侧菜单（PC端）或底部导航（移动端）
3. **练习页面**
   * 左侧题型筛选面板（PC端）或顶部题型筛选Tab（移动端）
   * 题目展示区域，支持键盘快捷键（A/B/C/D选择）
   * 底部操作栏："加入错题本""收藏""上一题""下一题"按钮
4. **考试页面**
   * 顶部倒计时进度条
   * 右侧题目导航面板（PC端显示题号网格）
   * 页面可见性监听（document.visibilityState）→ 增加切屏计数
   * 全屏模式支持，防止意外退出
5. **成绩页面**
   * 总分展示 & 及格状态提示
   * 可视化图表：雷达图显示各题型正确率
   * 错题列表，点击可跳转到解析页面
   * 成绩分享功能（生成图片）
6. **个人中心**
   * 我的收藏 / 错题本（支持标签分类）
   * 练习历史（时间轴展示）
   * 系统设置 / 意见反馈
   * 数据导出功能

---

## 8  非功能需求

| 项目           | 指标                                                  |
| -------------- | ----------------------------------------------------- |
| **部署** | 前端：`npm run build && nginx`；后端：`docker run -d -p 8000:80 exam-app` |
| **性能** | ≤ 1 s 返回 1k 题目查询；并发 200 在线考试；首屏加载 < 2s |
| **安全** | HTTPS；JWT 过期 2h；XSS/CSRF 防护；SQL 注入自动防护（ORM） |
| **兼容性** | 支持 Chrome 90+、Firefox 88+、Safari 14+、Edge 90+ |
| **响应式** | 适配 PC（≥1200px）、平板（768-1199px）、手机（<768px） |
| **备份** | 每日 cron 复制 `exam.db`到对象存储                  |
| **监控** | Prometheus + Grafana Dashboard（CPU/内存/QPS/错误率） |

---

## 9  开发里程碑（建议）

| 周次 | 交付                                       | 负责人      |
| ---- | ------------------------------------------ | ----------- |
| W1   | 完成 ER 图 & API 草案；Excel ETL 脚本      | 后端        |
| W2   | 题库导入 & 基础练习接口；React基础页面搭建    | 后端 & 前端 |
| W3   | 模拟考试流程 + 判卷；成绩可视化页面        | 全栈        |
| W4   | 管理后台（导入、规则配置）；PWA功能集成 | 全栈        |
| W5   | 构建打包 & 内测；性能压测 & 灰度上线           | DevOps      |

---

## 10  附录 A — Excel 字段映射示意（单选为例）

| Excel 列     | Question 字段    | 说明                |
| ------------ | ---------------- | ------------------- |
| 序号         | `external_id`  | 原始排序            |
| 题型         | `type`= single | 单选/多选/判断…    |
| 难易度       | `difficulty`   | 易/适中/难          |
| 考试类别     | `category`     | 信息网络            |
| 题干         | `stem`         | 富文本存 Markdown   |
| A, B, C, D… | `options`      | 存入 JSON 数组      |
| 答案         | `answer`       | 如 "C" 或 "ABD" |
| 答案解析     | `explanation`  | 解析或引用条款      |
| 试题关键词   | `keywords`     | 逗号分隔            |
| 是否保命题型 | `is_must_know` | bool                |

> 其余四类 Sheet 同理，脚本按首行关键词自动映射。

---

## 11  附录 B — React Web 技术栈实现方案

### 项目结构
```
frontend/
├── public/
│   ├── manifest.json          # PWA 配置
│   └── sw.js                  # Service Worker
├── src/
│   ├── components/            # 通用组件
│   │   ├── QuestionCard/      # 题目卡片组件
│   │   ├── Timer/             # 倒计时组件
│   │   └── Charts/            # 图表组件
│   ├── pages/                 # 页面组件
│   │   ├── Login/             # 登录页
│   │   ├── Practice/          # 练习页
│   │   ├── Exam/              # 考试页
│   │   └── Profile/           # 个人中心
│   ├── hooks/                 # 自定义Hook
│   │   ├── useAuth.ts         # 认证Hook
│   │   ├── useLocalStorage.ts # 本地存储Hook
│   │   └── useWebSocket.ts    # WebSocket Hook
│   ├── store/                 # 状态管理
│   │   ├── authSlice.ts       # 认证状态
│   │   ├── examSlice.ts       # 考试状态
│   │   └── index.ts           # Store配置
│   ├── services/              # API服务
│   │   ├── api.ts             # API配置
│   │   ├── auth.ts            # 认证API
│   │   └── exam.ts            # 考试API
│   └── utils/                 # 工具函数
│       ├── constants.ts       # 常量定义
│       ├── helpers.ts         # 辅助函数
│       └── validators.ts      # 表单验证
├── package.json
└── vite.config.ts
```

### 核心依赖包
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.8.0",
    "@reduxjs/toolkit": "^1.9.3",
    "react-redux": "^8.0.5",
    "antd": "^5.2.0",
    "echarts": "^5.4.1",
    "echarts-for-react": "^3.0.2",
    "axios": "^1.3.4",
    "dayjs": "^1.11.7"
  },
  "devDependencies": {
    "@types/react": "^18.0.28",
    "@types/react-dom": "^18.0.11",
    "@vitejs/plugin-react": "^3.1.0",
    "typescript": "^4.9.3",
    "vite": "^4.1.0",
    "vite-plugin-pwa": "^0.14.4"
  }
}
```

### 关键特性实现

**1. 防切屏监控**
```typescript
// hooks/useVisibilityMonitor.ts
export const useVisibilityMonitor = () => {
  const [switchCount, setSwitchCount] = useState(0);
  
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        setSwitchCount(prev => prev + 1);
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);
  
  return switchCount;
};
```

**2. 本地缓存策略**
```typescript
// utils/storage.ts
export const storage = {
  setWrongAnswers: (answers: WrongAnswer[]) => {
    localStorage.setItem('wrongAnswers', JSON.stringify(answers));
  },
  getWrongAnswers: (): WrongAnswer[] => {
    const data = localStorage.getItem('wrongAnswers');
    return data ? JSON.parse(data) : [];
  },
  setExamHistory: (history: ExamResult[]) => {
    localStorage.setItem('examHistory', JSON.stringify(history));
  }
};
```

**3. PWA 配置**
```json
// public/manifest.json
{
  "name": "信息网络类刷题系统",
  "short_name": "刷题系统",
  "description": "信息中心作业人员资格考试刷题系统",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#1890ff",
  "background_color": "#ffffff",
  "icons": [
    {
      "src": "/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    }
  ]
}
```

**4. 响应式设计**
```scss
// styles/responsive.scss
@media (max-width: 768px) {
  .question-container {
    padding: 16px;
    .options-grid {
      grid-template-columns: 1fr;
    }
  }
}

@media (min-width: 1200px) {
  .exam-layout {
    .question-panel { width: 70%; }
    .navigation-panel { width: 30%; }
  }
}
```
