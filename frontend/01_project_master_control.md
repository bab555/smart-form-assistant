# 01. 项目总控与标准化规范 (Master Control & Standardization)

## 1. 核心原则
*   **单一数据源**: 所有跨端数据结构（Interface/Schema）以此文档为准。
*   **命名公约**:
    *   **API 路径**: `kebab-case` (e.g., `/api/smart-form/submit`)
    *   **JSON 字段 (网络传输)**: `snake_case` (e.g., `product_name`, `confidence_score`)
    *   **前端变量 (TS)**: `camelCase` (e.g., `productName`) —— *前端负责转换*
    *   **后端变量 (Py)**: `snake_case` (e.g., `product_name`)
    *   **数据库字段**: `snake_case`
*   **时间格式**: ISO 8601 (`YYYY-MM-DDTHH:mm:ssZ`)

---

## 2. 通用数据模型 (Core Data Models)

### 2.1 基础表单项 (FormItem)
这是前端表格和后端识别结果交换的最小单元。

```typescript
// TS Definition
interface FormItem {
  key: string;            // 字段唯一标识 (e.g., "product_name")
  label: string;          // 显示名称 (e.g., "商品名称")
  value: any;             // 实际值
  original_text?: string; // OCR/ASR 原始识别文本 (用于校对)
  confidence: number;     // 置信度 0.0 - 1.0
  is_ambiguous: boolean;  // 是否有歧义 (触发黄色高亮)
  candidates?: string[];  // 候选值 (仅当 is_ambiguous=true 时存在)
  data_type: 'string' | 'number' | 'date' | 'enum';
}
```

### 2.2 识别请求 (RecognitionRequest)
```json
{
  "request_id": "uuid-v4",
  "input_type": "image_handwriting" | "image_print" | "audio_command",
  "file_url": "oss_path/to/file",  // 或 base64
  "template_id": "string"          // 关联的表单模板ID
}
```

### 2.3 标准响应封套 (Standard Response Envelope)
所有 API 返回必须包裹在此结构中。
```json
{
  "code": 200,          // 业务状态码
  "message": "success", // 提示信息
  "data": { ... },      // 实际载荷
  "trace_id": "uuid"    // 用于链路追踪
}
```

---

## 3. 错误码定义 (Error Codes)
| Code | Enum | Description |
| :--- | :--- | :--- |
| 200 | `SUCCESS` | 成功 |
| 4001 | `INVALID_INPUT` | 输入格式错误或文件损坏 |
| 4002 | `AMBIGUOUS_INTENT` | 意图不明，需要用户澄清 |
| 5001 | `OCR_FAILED` | OCR 引擎调用失败 |
| 5002 | `SKILL_EXECUTION_ERROR` | 知识库技能执行异常 |
| 5003 | `CALIBRATION_FAILED` | 校准失败 (无法找到匹配项) |

---

## 4. 全局环境变量 (Environment Variables)

### 后端 (.env)
```ini
# Server
PORT=8000
WORKERS=4

# Cloud Services (Aliyun)
ALIYUN_ACCESS_KEY_ID=
ALIYUN_ACCESS_KEY_SECRET=
ALIYUN_OSS_BUCKET=
ALIYUN_QWEN_MODEL=qwen-max
ALIYUN_OCR_ENDPOINT=
ALIYUN_ASR_APPKEY=

# Database (MySQL)
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=smart_form_db
```

### 前端 (.env.local)
```ini
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

---

## 5. 术语表 (Glossary)
*   **Orchestrator (总控)**: 负责分发任务的主 Agent。
*   **Skill (技能)**: 特指封装了向量检索的独立功能单元 (Function)。
*   **Calibration (校准)**: 从“OCR原始文本”到“标准数据库字段”的映射过程。
*   **Ambiguity (歧义)**: 当 Calibration 发现多个相似度极高的候选值时的状态。

