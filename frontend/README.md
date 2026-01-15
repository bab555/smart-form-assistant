# 智能订单助手 - 前端项目

AI 驱动的多模态智能订单识别系统

## 🚀 项目简介

这是一个基于 React + TypeScript + Vite 的现代化前端应用，采用三栏式沉浸布局，实现了：

- 🎙️ **语音输入**：支持实时语音识别和命令执行
- 📷 **图像识别**：OCR 自动提取订单信息
- 🤖 **AI Agent**：智能数据校准与歧义处理
- 📊 **智能表格**：可编辑的数据网格，实时状态反馈
- 🎨 **可视化流程**：AI 思维过程实时展示

## 📁 项目结构

```
frontend/
├── src/
│   ├── components/        # React 组件
│   │   ├── layout/       # 布局组件
│   │   ├── chat/         # 聊天交互组件
│   │   ├── visualizer/   # 可视化组件
│   │   └── grid/         # 表格组件
│   ├── hooks/            # 自定义 Hooks
│   ├── services/         # API 服务层
│   ├── types/            # TypeScript 类型定义
│   ├── utils/            # 工具函数
│   ├── styles/           # 全局样式
│   └── test/             # 测试配置
├── public/               # 静态资源
└── 配置文件 ...
```

## 🛠️ 技术栈

### 核心框架
- **React 18** - UI 框架
- **TypeScript** - 类型系统
- **Vite** - 构建工具

### 状态管理
- **Zustand** - 轻量级状态管理
- **TanStack Query** - 服务端状态管理

### UI 组件
- **TailwindCSS** - 样式框架
- **AG Grid** - 高性能数据表格
- **React Flow** - 流程图可视化
- **Framer Motion** - 动画库
- **Lucide React** - 图标库

### 通信
- **Axios** - HTTP 客户端
- **WebSocket** - 实时通信

### 开发工具
- **ESLint** - 代码检查
- **Prettier** - 代码格式化
- **Vitest** - 单元测试

## 🎯 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env.local` 并配置：

```ini
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
VITE_DEBUG=true
```

### 3. 启动开发服务器

```bash
npm run dev
```

应用将运行在 `http://localhost:3000`

### 4. 构建生产版本

```bash
npm run build
```

## 📜 可用脚本

```bash
# 开发
npm run dev              # 启动开发服务器
npm run build           # 构建生产版本
npm run preview         # 预览构建结果

# 代码质量
npm run lint            # 运行 ESLint 检查
npm run lint:fix        # 自动修复 ESLint 问题
npm run format          # 使用 Prettier 格式化代码
npm run type-check      # TypeScript 类型检查

# 测试
npm run test            # 运行单元测试
npm run test:ui         # 打开测试 UI 界面
npm run test:coverage   # 生成测试覆盖率报告
```

## 🎨 UI 布局设计

### 三栏式布局 (25% - 35% - 40%)

#### 左栏：智能交互区
- 聊天流显示（类似 ChatGPT）
- 语音输入按钮（按住说话）
- 图片上传按钮
- 文本输入框

#### 中栏：思维可视化区
- 待机态：呼吸动画的核心球
- 工作态：流程节点图（React Flow）
- 状态展示：OCR → 校准 → 查询 → 填充
- 实时日志显示

#### 右栏：智能表格区
- 可编辑数据表格（AG Grid）
- 状态标识：
  - ✅ 高置信度（绿色边框）
  - ⚠️ 歧义单元格（黄色背景）
  - 📝 用户修改（红色三角标记）
- 工具栏：提交、导出、清空

## 🔌 API 集成

### REST API

```typescript
// 图片识别
POST /api/workflow/visual
Body: FormData { file: File }

// 语音识别
POST /api/workflow/audio
Body: FormData { file: Blob }

// 获取模板
GET /api/template/list
```

### WebSocket

```typescript
// 连接
ws://localhost:8000/ws/agent

// 消息格式
{
  "type": "agent_thought" | "tool_action" | "step_start" | "step_end",
  "content": "...",
  "timestamp": "ISO 8601"
}
```

## 📊 数据模型

### FormItem（表单项）

```typescript
interface FormItem {
  key: string              // 字段标识
  label: string            // 显示名称
  value: any               // 实际值
  originalText?: string    // OCR 原始文本
  confidence: number       // 置信度 0.0-1.0
  isAmbiguous: boolean     // 是否有歧义
  candidates?: string[]    // 候选值
  dataType: 'string' | 'number' | 'date' | 'enum'
}
```

### 命名规范

- **API 路径**: `kebab-case` (`/api/smart-form`)
- **JSON 字段**: `snake_case` (`product_name`)
- **前端变量**: `camelCase` (`productName`)

*前端自动转换 snake_case ↔ camelCase*

## 🧪 测试

运行测试：

```bash
npm run test
```

查看测试覆盖率：

```bash
npm run test:coverage
```

示例测试位于 `src/utils/__tests__/helpers.test.ts`

## 🎭 核心功能

### 1. 多模态输入
- 支持语音、图片、文字三种输入方式
- 实时 ASR 和 OCR 识别
- 自动上传和处理

### 2. 智能校准
- AI 自动匹配数据库标准值
- 置信度评分系统
- 歧义检测与人机协作

### 3. 实时可视化
- Agent 工作流程动态展示
- 节点状态高亮
- 执行日志实时更新

### 4. 智能表格
- Excel 风格操作（Tab、Enter）
- 自定义单元格渲染器
- 歧义单元格交互式选择

## 🚧 开发计划

- [ ] 表单模板动态加载
- [ ] 历史记录管理
- [ ] 离线缓存支持
- [ ] 多语言国际化
- [ ] 暗黑模式
- [ ] 移动端适配

## 📝 开发规范

### Git 提交规范

```
feat: 新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式调整
refactor: 代码重构
test: 测试相关
chore: 构建/工具链更新
```

### 代码风格

- 使用 ESLint + Prettier 自动格式化
- 遵循 TypeScript 严格模式
- 组件使用函数式 + Hooks
- 文件命名：PascalCase（组件）、camelCase（工具）

## 📚 参考文档

- [设计规范](./02_ui_ux_design.md)
- [工程文档](./03_frontend_spec.md)
- [数据标准](./01_project_master_control.md)

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

MIT License

---

**Made with ❤️ for efficient form filling**

