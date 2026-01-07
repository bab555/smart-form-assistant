# 重构执行路线图 (Execution Roadmap)

本文档是 Phase 1/2/3 的统一执行计划，按依赖顺序排列。

## 执行原则
1. **前后端同步推进**：每个阶段的前后端任务可以并行开发，但需要在"联调点"对齐。
2. **最小可运行优先**：每个阶段结束时，系统必须能跑通一个完整流程。
3. **不破坏现有功能**：在新代码完全可用之前，旧代码保留可切换。

---

## Phase 1: 通信基础 (Foundation)

### 目标
建立稳固的 WebSocket 通信层，前后端能互相发消息。

### 任务清单

| # | 位置 | 文件 | 任务 | 依赖 |
|---|------|------|------|------|
| 1.1 | 后端 | `app/core/protocol.py` | 定义 EventType 枚举、WebSocketMessage 模型 | - |
| 1.2 | 后端 | `app/core/connection_manager.py` | 极简重写：connect/disconnect/send_to_client | 1.1 |
| 1.3 | 后端 | `app/api/websocket.py` | 简化 WS 端点，只做消息路由 | 1.2 |
| 1.4 | 前端 | `src/services/protocol.ts` | 定义 EventType、消息类型 (与后端对齐) | - |
| 1.5 | 前端 | `src/services/websocket.ts` | 极简重写：connect/reconnect/on/send | 1.4 |
| 1.6 | 联调 | - | 验证：前端连接后端，收发 `connection_ack` | 1.3, 1.5 |

### 验收标准
- [x] 前端打开页面，右上角连接灯变绿
- [x] 控制台可见 `connection_ack` 消息
- [x] 断网后连接灯变红，恢复后自动重连变绿

---

## Phase 2: 画布与极速填表 (Canvas & Fast-Fill)

### 目标
实现多表格画布 UI，并打通"上传文件 -> 极速出表"的完整流程。

### 任务清单

| # | 位置 | 文件 | 任务 | 依赖 |
|---|------|------|------|------|
| 2.1 | 前端 | `src/store/useCanvasStore.ts` | 多表格状态管理 (tables, appendRow, replaceRows...) | 1.5 |
| 2.2 | 前端 | `src/components/Canvas/Canvas.tsx` | 画布容器 + 右上角连接灯 | 2.1 |
| 2.3 | 前端 | `src/components/Canvas/TableCard.tsx` | 可拖拽表格卡片 (@dnd-kit + react-datasheet-grid) | 2.1 |
| 2.4 | 前端 | `src/components/FloatingPanel/` | 左侧悬浮窗 (ChatList, InputArea, FileUploader) | 2.1 |
| 2.5 | 后端 | `app/api/endpoints.py` | 统一入口 `/task/submit`，删除旧端点 | 1.2 |
| 2.6 | 后端 | `app/agents/nodes/router_node.py` | 文件类型判断 (Excel/Word/Image/PDF) | - |
| 2.7 | 后端 | `app/agents/nodes/ocr_node.py` | Fast-OCR 逻辑 | - |
| 2.8 | 后端 | `app/agents/nodes/llm_node.py` | LLM JSONL 格式化 + 行级推送 | 1.2, 2.6, 2.7 |
| 2.9 | 后端 | `app/agents/graph.py` | ComfyUI 风格重写：Router -> OCR/Parser -> LLM -> Push | 2.6, 2.7, 2.8 |
| 2.10 | 联调 | - | 验证：上传图片 -> 表格一行行出现 | 2.4, 2.9 |

### 验收标准
- [x] 上传 Excel：< 1s 出表
- [x] 上传打印图片：< 2s 开始出行
- [x] 上传手写图片：< 5s 开始出行
- [x] 用户可拖拽表格卡片、编辑单元格、增删行

---

## Phase 3: 高级特性 (Advanced)

### 目标
实现 Skills 导入、分级 Agent、后台校对。

### 任务清单

| # | 位置 | 文件 | 任务 | 依赖 |
|---|------|------|------|------|
| 3.1 | 后端 | `app/api/skills.py` | `/api/skills/import` 接口 | - |
| 3.2 | 后端 | `app/services/skill_registry.py` | Skills 注册与模板管理 | 3.1 |
| 3.3 | 后端 | `app/agents/nodes/calibration_node.py` | 后台校对逻辑 (计算/知识库匹配) | 2.9 |
| 3.4 | 后端 | `app/agents/intent_classifier.py` | 意图分类 (Operational/Consultative/Extraction) | - |
| 3.5 | 后端 | `app/agents/graph.py` | 增加 IntentClassifier 入口 | 3.4 |
| 3.6 | 前端 | `src/components/FloatingPanel/TemplateSelector.tsx` | 新建表格时选择模板 | 3.2 |
| 3.7 | 联调 | - | 验证：导入商品库 Excel -> 新建表格可选模板 | 3.2, 3.6 |
| 3.8 | 联调 | - | 验证：填表后自动出现校对建议 | 3.3 |

### 验收标准
- [x] 导入 Excel 后，"新建表格"下拉可见模板
- [x] 填表完成后，行尾自动出现校对建议（如有问题）
- [x] 语音说"这个订单多少钱"，Agent 能计算并回复

---

## 清理任务 (Cleanup)

在所有 Phase 完成后，删除旧代码：

| 文件/目录 | 说明 |
|-----------|------|
| `app/api/endpoints.py` 中的旧端点 | `/workflow/visual`, `/document/extract` 等 |
| `app/agents/` 中的旧逻辑 | 非节点化的 graph.py 旧代码 |
| `frontend/src/hooks/useFormStore.ts` | 被 useCanvasStore 取代 |
| `frontend/src/components/visualizer/` | 旧的流程可视化组件 |

---

**记录时间**: 2026-01-07
**状态**: 待执行

