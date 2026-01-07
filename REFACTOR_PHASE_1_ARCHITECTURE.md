# 系统重构记录 - 第一部分：核心架构定义 (ComfyUI 模式)

## 1. 核心理念 (Philosophy)
将项目重构为 **"单一执行引擎 + 事件驱动渲染"** 模式。
- **后端 (Python)**: 无状态执行器。接收任务，执行 Graph，推送结果。不保留 Session。
- **前端 (TS)**: 状态持有者 + 被动渲染器。持有表格数据，监听后端事件，实时渲染。
- **通信**: WebSocket 长连接，无主动心跳，依赖原生断连检测。

### 1.1 一体化边界（必须遵守）
- **唯一权威数据源（SoT）**：前端 `CanvasStore` 是唯一权威数据源；后端不作为业务数据存储。
- **后端职责**：提取/格式化/校对建议/工具指令（对画布的“操作建议”），不持久化画布与表格状态。
- **重连与同步**：`sync_state` 的语义是“前端把当前画布快照同步给后端”，用于继续对话/校对/建议；不是恢复后端任务流水。

## 2. 技术选型 (Tech Stack)

| 模块 | 选型 | 理由 |
| :--- | :--- | :--- |
| **画布拖拽** | `@dnd-kit` | 现代、轻量、Hook 友好、支持未来扩展 |
| **表格组件** | `react-datasheet-grid` | 轻量、类 Excel、开源免费、开箱即用 |
| **流式解析** | 行级流式 (JSONL) | 后端按行推送，前端零解析成本 |
| **心跳机制** | 无主动心跳 | 前后一体部署，依赖原生 `onclose` |
| **Session** | 无状态后端 | 前端持有数据，重连时主动同步 |

## 3. 统一通信协议 (Unified Protocol)

### 3.1 基础消息结构
```python
class WebSocketMessage(BaseModel):
    type: str            # 事件类型
    client_id: str       # 会话ID
    timestamp: str       # ISO 8601 时间戳
    data: Dict[str, Any] # 负载数据
```

### 3.2 核心事件类型

| 事件类型 | 触发场景 | 数据载荷 | 前端行为 |
| :--- | :--- | :--- | :--- |
| `connection_ack` | WS 连接成功 | `{ "status": "connected" }` | 显示"在线" |
| `task_start` | 任务入队 | `{ "task_id": "...", "type": "extract" }` | 显示 Loading |
| `node_start` | 节点开始 | `{ "node": "ocr", "name": "识别中..." }` | 高亮节点(可选) |
| `node_finish` | 节点完成 | `{ "node": "ocr" }` | 节点完成(可选) |
| `row_complete` | **行级流式** | `{ "table_id": "t1", "row": {...} }` | **追加整行到表格** |
| `table_replace` | 全量刷新 | `{ "table_id": "t1", "rows": [...] }` | 替换整个表格 |
| `chat_message` | 对话消息 | `{ "role": "agent", "content": "..." }` | 追加到聊天窗 |
| `calibration_note` | 校对建议 | `{ "table_id": "t1", "row": 0, "note": "..." }` | 显示行尾提示 |
| `task_finish` | 任务完成 | `{ "task_id": "..." }` | 恢复空闲状态 |
| `error` | 异常 | `{ "code": 500, "msg": "..." }` | 红色报错 |

### 3.2.1 UI 展示原则（去掉传统“后端状态可视化”）
- **只展示右上角连接灯**（在线/离线），不展示“后端运行步骤/状态条”。原因：极速出表 + 行级流式，本身就是最直观反馈。
- `task_start/node_start/node_finish` 事件 **仅用于日志/调试**（可选记录），不得作为前端业务逻辑分支条件（例如禁止出现“必须等到 node=ocr 才允许编辑”）。

### 3.3 断连与重连 (简化方案)
```
前端 WebSocket.onclose 触发
       ↓
立即尝试重连（本地部署无需退避）
       ↓
重连成功，前端发送 { type: "sync_state", tables: {...} }
       ↓
后端恢复上下文（可选）
```

## 4. 后端架构 (Backend Architecture)

### 4.1 目录结构
```text
backend/
  app/
    core/
      protocol.py          # [New] 协议定义 (事件类型枚举)
      connection_manager.py # [Simplify] 极简连接管理
    agents/
      graph.py             # [Refactor] ComfyUI 风格统一 Graph
      nodes/               # [New] 拆分节点
        router_node.py     # 路由判断
        ocr_node.py        # OCR 识别
        llm_node.py        # LLM 格式化
        calibration_node.py # 后台校对
    api/
      endpoints.py         # [Clean] 只保留 /task/submit
      websocket.py         # [Simplify] 极简 WS 处理
```

### 4.2 统一入口
```python
@router.post("/task/submit")
async def submit_task(
    file: UploadFile, 
    task_type: str,     # "extract" | "audio" | "chat"
    client_id: str,
    background_tasks: BackgroundTasks
):
    # 1. 保存文件
    # 2. 异步启动 Graph (background_tasks.add_task)
    # 3. 立即返回 { task_id: "..." }
```

## 5. 前端架构 (Frontend Architecture)

### 5.1 目录结构
```text
frontend/
  src/
    services/
      websocket.ts         # [Simplify] 极简 WS 客户端
      protocol.ts          # [New] 事件类型定义
    store/
      useCanvasStore.ts    # [New] 画布状态 (多表格)
    components/
      Canvas/              # [New] 画布容器
        Canvas.tsx
        TableCard.tsx      # 可拖拽表格卡片
      FloatingPanel/       # [New] 左侧悬浮窗
        FloatingPanel.tsx
        ChatList.tsx
        InputArea.tsx
```

### 5.2 WebSocket 客户端 (极简版)
```typescript
class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers = new Map<string, Function[]>();

  connect(url: string) {
    this.ws = new WebSocket(url);
    this.ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      this.emit(msg.type, msg.data);
    };
    this.ws.onclose = () => this.reconnect();
  }

  on(type: string, handler: Function) { ... }
  emit(type: string, data: any) { ... }
  send(data: any) { this.ws?.send(JSON.stringify(data)); }
  
  private reconnect() {
    setTimeout(() => this.connect(this.url), 1000);
  }
}
```

---
**记录时间**: 2026-01-07
**状态**: 规划完成，待执行
