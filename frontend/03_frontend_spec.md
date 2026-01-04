# 03. 前端工程开发文档 (Frontend Engineering Spec)

## 1. 技术栈 (Tech Stack)
*   **Framework**: React 18 + TypeScript
*   **Build Tool**: Vite
*   **State Management**: Zustand (轻量级，适合处理 Agent 状态 + 表格数据)
*   **Data Grid**: AG Grid Community (高性能，支持复杂编辑)
*   **Visual Flow**: React Flow (绘制中栏的节点图)
*   **Styling**: TailwindCSS
*   **API Client**: Axios + React Query (TanStack Query)
*   **WebSocket**: 原生 WebSocket (用于流式对话)

---

## 2. 目录结构 (Directory Structure)
```
src/
├── assets/
├── components/
│   ├── layout/
│   │   └── MainLayout.tsx       // 左中右 Grid 容器
│   ├── chat/
│   │   ├── ChatBubble.tsx
│   │   └── VoiceInput.tsx       // 封装 RecordRTC
│   ├── visualizer/
│   │   ├── ProcessGraph.tsx     // React Flow 封装
│   │   └── StatusNodes.tsx      // 自定义节点
│   └── grid/
│       ├── SmartTable.tsx       // AG Grid 封装
│       └── CellEditors.tsx      // 自定义下拉编辑器
├── hooks/
│   ├── useAgent.ts              // 管理 WebSocket 连接与 Agent 状态
│   └── useFormStore.ts          // Zustand: 存储表格数据
├── services/
│   ├── api.ts
│   └── websocket.ts
├── types/
│   └── schema.d.ts              // 引用总控文档定义的 Interface
└── App.tsx
```

---

## 3. 核心模块实现

### 3.1 状态管理 (Zustand Store)
`useFormStore.ts`
```typescript
interface FormState {
  rows: FormItem[][]; // 多行数据
  isThinking: boolean;
  currentStep: 'idle' | 'ocr' | 'calibrating' | 'filling';
  
  // Actions
  updateCell: (rowIndex: number, key: string, value: any) => void;
  addRow: (row: FormItem[]) => void;
  setAmbiguous: (rowIndex: number, key: string, candidates: string[]) => void;
}
```

### 3.2 语音输入模块
*   使用 `RecordRTC` 录制音频 Blob。
*   上传到 `/api/workflow/audio`。
*   接收后端返回的 `Action` 指令，调用 `useFormStore` 修改状态。

### 3.3 中栏可视化 (Visualizer)
*   监听 WebSocket 消息事件：
    *   `STEP_START`: { step: 'ocr', status: 'running' } -> 节点变蓝，连线动画开始。
    *   `STEP_LOG`: { message: "Found 3 candidates" } -> 在节点旁显示 Tooltip。
    *   `STEP_END`: { step: 'ocr', status: 'success' } -> 节点变绿。

### 3.4 智能表格 (SmartGrid)
*   **Column Definition**: 根据 `template_id` 动态生成。
*   **Cell Renderer**:
    *   如果 `is_ambiguous === true`: 渲染黄色背景 + Warning Icon。
*   **Edit Handler**:
    *   用户修改单元格 -> 触发 `onCellValueChanged` -> 更新 Store -> (可选) 发送修正日志给后端。

---

## 4. 接口集成

### 4.1 WebSocket 协议
*   **Endpoint**: `/ws/agent`
*   **Client Message**:
    ```json
    { "type": "ping" }
    ```
*   **Server Message (Stream)**:
    ```json
    {
      "type": "agent_thought",
      "content": "正在查阅数据库...",
      "step": "skill_lookup"
    }
    // OR
    {
      "type": "tool_action",
      "tool": "update_table",
      "params": { ... }
    }
    ```

### 4.2 文件上传
*   **POST** `/api/workflow/visual`
*   **Response**: 返回完整的解析后 JSON 数组，直接替换或追加到 Grid。

