# 系统重构记录 - 第三部分：高级特性与 API 扩展 (Advanced Features & API)

## 1. 外部数据接入与 Skills 转换 (External Data Integration)

### 1.1 知识库导入 API (`/api/skills/import`)
允许用户上传自己的商品库/客户库 Excel。
- **逻辑**:
  1. 读取 Excel 头，自动生成 `Table Schema`。
  2. 读取每一行，生成向量索引 `(Text -> SkillID)`。
  3. 存入 `VectorStore` 和 `SkillRegistry`。
- **UI**: "新建表格" -> "从我的模板选择" -> 列出已导入的 Excel 文件名。

## 2. 深度智能填表 (Deep Intelligent Filling)

### 2.1 语音全自动创建
用户: "帮我建个表，要买10斤土豆，明天送给老王。"
- **Agent 思考**:
  1. 意图: Create Table。
  2. 提取实体: 土豆 (Product), 10斤 (Qty), 老王 (Customer), 明天 (Date)。
  3. 知识检索: "土豆" -> SKU "荷兰土豆"; "老王" -> Customer "王记餐饮"。
  4. 行动: 调用 `create_table` -> `add_row`。

### 2.2 咨询与推理
用户: "这个订单算下来多少钱？"
- **Agent 思考**:
  1. 获取当前激活表格的数据。
  2. 代码解释器 (Code Interpreter): 遍历 rows，累加 `price * quantity`。
  3. 回复: "总金额是 580 元。"

## 3. 分级 Skills 架构 (Hierarchical Skills)

### 3.1 动态 Router
在 `Graph` 的入口处增加 `IntentClassifier` 节点（使用轻量模型）：
- **Intent**: `Operational` (增删改) -> Route to **ActionAgent** (严谨，调用 Tools)。
- **Intent**: `Consultative` (咨询) -> Route to **ChatAgent** (发散，RAG，通用对话)。
- **Intent**: `Extraction` (提取) -> Route to **ExtractorAgent** (专注 JSON 格式化)。

## 4. 细节优化 (Micro Features)

### 4.1 表单头信息提取
- 在 `Fast-OCR` 阶段，专门截取图片**顶部 1/5 区域**。
- 专门 Prompt: "提取日期、单号、客户名"。
- 结果存入表格的 `metadata` 字段，前端渲染在表格上方的 `Header Area`。
- **日期处理**: 统一转换为 `YYYY-MM-DD` 格式。

### 4.2 状态栏与时间
- **位置**: Canvas 右上角。
- **内容**: 
  - 实时时钟 (每秒刷新)。
  - 连接灯（在线/离线）。
  - 令牌消耗 (Token Usage - 可选)。

> 说明：本项目按“一体化”原则默认**不做主动心跳**，因此不提供 Ping 延迟展示；连接状态以 WebSocket 的 open/close 为准。

---
**记录时间**: 2026-01-07
**状态**: 规划完成，待执行
