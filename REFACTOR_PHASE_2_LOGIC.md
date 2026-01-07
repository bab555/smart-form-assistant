# 系统重构记录 - 第二部分：业务逻辑与 UI 交互重构 (Canvas & Order Logic)

## 1. 核心理念 (Philosophy)
从"单据录入流"转变为 **"智能画布工作台"**。
- **Canvas First**: 无限画布，支持多表格并存。
- **Speed First**: 追求极致响应速度（体感 < 2s）。
- **AI as Co-pilot**: 先填表（快），后校对（准）。

## 2. 技术选型 (UI Tech Stack)

| 模块 | 选型 | 版本 | 说明 |
| :--- | :--- | :--- | :--- |
| **画布拖拽** | `@dnd-kit/core` | ^6.x | 表格卡片拖拽定位 |
| **表格渲染** | `react-datasheet-grid` | ^4.x | 类 Excel 单元格编辑 |
| **左侧面板** | 原生 CSS + Framer Motion | - | 折叠/展开动画 |
| **图标** | `lucide-react` | - | 沿用现有 |

## 3. UI 架构 (UI Architecture)

### 3.1 整体布局
```
┌─────────────────────────────────────────────────────────┐
│                                           [连接灯 ●]    │
├────────┬────────────────────────────────────────────────┤
│        │                                                │
│  左侧  │              Canvas 画布区域                    │
│  悬浮  │                                                │
│  窗    │    ┌──────────────┐    ┌──────────────┐       │
│        │    │  表格卡片 1   │    │  表格卡片 2   │       │
│ [折叠] │    │  (可拖拽)     │    │  (可拖拽)     │       │
│        │    └──────────────┘    └──────────────┘       │
│        │                                                │
│        │                    [+] 新建表格                 │
└────────┴────────────────────────────────────────────────┘
```

#### UI 展示原则（收敛）
- **只在右上角显示连接灯**（在线/离线）。
- 不展示后端运行步骤/状态条/进度条（极速 + 行级流式本身就是反馈）。

### 3.2 左侧悬浮窗 (FloatingPanel)
```typescript
interface FloatingPanelProps {
  isCollapsed: boolean;
  onToggle: () => void;
}

// 内部结构
<FloatingPanel>
  <ChatList messages={...} />      // 对话历史
  <InputArea onSend={...} />       // 文字输入
  <VoiceButton onRecord={...} />   // 语音按钮
  <FileUploader onUpload={...} />  // 文件上传
</FloatingPanel>
```

### 3.3 表格卡片 (TableCard)
```typescript
interface TableCardProps {
  id: string;
  title: string;
  position: { x: number; y: number };
  size: { width: number; height: number };
  data: Row[];
  schema: Column[];
  isStreaming: boolean;  // 正在接收流式数据
  onDataChange: (data: Row[]) => void;
}

// 使用 @dnd-kit 实现拖拽
<DndContext>
  <TableCard draggable>
    <TitleBar>{title} [📅 日期: 2026-01-07]</TitleBar>
    <DataSheetGrid data={data} columns={schema} onChange={...} />
    <CalibrationNotes notes={...} />  // 校对建议行
  </TableCard>
</DndContext>
```

## 4. 数据模型 (Data Model)

### 4.1 Canvas Store
```typescript
interface CanvasState {
  // 多表格存储
  tables: Record<string, TableData>;
  activeTableId: string | null;
  
  // Actions
  createTable: (template?: string) => string;
  removeTable: (id: string) => void;
  updateTablePosition: (id: string, pos: {x, y}) => void;
  
  // 数据操作
  appendRow: (tableId: string, row: Row) => void;      // 行级流式
  replaceRows: (tableId: string, rows: Row[]) => void; // 全量替换
  updateCell: (tableId: string, rowIdx: number, colKey: string, value: any) => void;
  
  // 校对
  setCalibrationNote: (tableId: string, rowIdx: number, note: string) => void;
}

interface TableData {
  id: string;
  title: string;
  position: { x: number; y: number };
  size: { width: number; height: number };
  schema: Column[];        // 表头定义
  rows: Row[];             // 数据行
  metadata: {              // 表单头信息
    date?: string;
    orderNo?: string;
    customer?: string;
  };
  calibrationNotes: Record<number, string>;  // rowIndex -> 校对建议
  isStreaming: boolean;
}
```

## 5. 业务流程 (Business Flow)

### 5.1 极速填表 (Fast-Fill)
```
用户上传文件
     ↓
POST /task/submit { file, type: "extract", client_id }
     ↓
后端 Router 判断文件类型
     ↓
┌─────────────────┬─────────────────┬─────────────────┐
│ Excel/Word      │ Image/PDF(打印) │ Image(手写)     │
│ 直接解析        │ Fast-OCR        │ VL-Model        │
│ < 0.5s          │ < 1s            │ 3-5s            │
└────────┬────────┴────────┬────────┴────────┬────────┘
         ↓                 ↓                 ↓
      LLM 格式化 (JSONL 输出，按行)
         ↓
WebSocket 推送 { type: "row_complete", row: {...} }
         ↓
前端 appendRow() 实时显示
```

### 5.2 异步校对 (Async Calibration)
```
Fast-Fill 完成
     ↓
后端自动创建 CalibrationTask (后台队列)
     ↓
逐行检查:
  - 数量 × 单价 = 金额？
  - 商品名在知识库中？
  - 规格是否匹配？
     ↓
如有问题，推送 { type: "calibration_note", row: 0, note: "价格可能有误" }
     ↓
前端 setCalibrationNote() 显示黄色提示
```

### 5.3 Agent 画布操作
用户语音: "新建一个蔬菜订单表"
```
WebSocket 发送 { type: "chat", content: "新建一个蔬菜订单表" }
     ↓
Agent IntentClassifier: Operational
     ↓
Agent 调用 Tool: create_table(template="vegetable_order")
     ↓
WebSocket 推送 { type: "table_create", table: {...} }
     ↓
前端 createTable() 在画布显示新表格
```

## 6. 组件实现要点

### 6.1 react-datasheet-grid 配置
```typescript
import { DataSheetGrid, textColumn, intColumn } from 'react-datasheet-grid';

const columns = [
  { ...textColumn, title: '商品名', key: 'product' },
  { ...intColumn, title: '数量', key: 'quantity' },
  { ...textColumn, title: '单位', key: 'unit' },
  { ...intColumn, title: '单价', key: 'price' },
];

<DataSheetGrid
  value={rows}
  onChange={setRows}
  columns={columns}
/>
```

### 6.3 用户与 Agent 的并行权限与冲突策略（必须明确）
- **用户权限**：单元格编辑、增删行列、拖拽/缩放表格卡片、修改表头/列。
- **Agent 权限**：通过工具调用执行相同操作，并具备跨表能力（新建/合并/批量修改）。
- **冲突处理（SoT 原则）**：
  - 前端 `CanvasStore` 为唯一权威数据源。
  - 当 Agent 输出与用户最近编辑冲突时：**不自动覆盖用户输入**，改为写入 `calibration_note` 或备注列提示用户确认。

### 6.2 @dnd-kit 拖拽配置
```typescript
import { DndContext, useDraggable } from '@dnd-kit/core';

function TableCard({ id, position }) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({ id });
  
  const style = {
    position: 'absolute',
    left: position.x + (transform?.x || 0),
    top: position.y + (transform?.y || 0),
  };
  
  return (
    <div ref={setNodeRef} style={style} {...listeners} {...attributes}>
      {/* 表格内容 */}
    </div>
  );
}
```

---
**记录时间**: 2026-01-07
**状态**: 规划完成，待执行
