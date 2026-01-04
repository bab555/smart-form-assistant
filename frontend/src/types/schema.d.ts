/**
 * 核心数据模型定义
 * 参考文档: 01_project_master_control.md
 */

/**
 * 基础表单项 (FormItem)
 * 前端与后端交换的最小数据单元
 */
export interface FormItem {
  key: string // 字段唯一标识 (e.g., "product_name")
  label: string // 显示名称 (e.g., "商品名称")
  value: any // 实际值
  originalText?: string // OCR/ASR 原始识别文本 (用于校对)
  confidence: number // 置信度 0.0 - 1.0
  isAmbiguous: boolean // 是否有歧义 (触发黄色高亮)
  candidates?: string[] // 候选值 (仅当 isAmbiguous=true 时存在)
  dataType: 'string' | 'number' | 'date' | 'enum'
}

/**
 * 识别请求 (RecognitionRequest)
 */
export interface RecognitionRequest {
  requestId: string // UUID v4
  inputType: 'image_handwriting' | 'image_print' | 'audio_command'
  fileUrl: string // OSS路径或base64
  templateId?: string // 关联的表单模板ID
}

/**
 * 标准响应封套 (Standard Response Envelope)
 */
export interface ApiResponse<T = any> {
  code: number // 业务状态码
  message: string // 提示信息
  data: T // 实际载荷
  traceId: string // 用于链路追踪
}

/**
 * 错误码枚举
 */
export enum ErrorCode {
  SUCCESS = 200,
  INVALID_INPUT = 4001,
  AMBIGUOUS_INTENT = 4002,
  OCR_FAILED = 5001,
  SKILL_EXECUTION_ERROR = 5002,
  CALIBRATION_FAILED = 5003,
}

/**
 * 表单模板定义
 */
export interface FormTemplate {
  templateId: string
  name: string
  columns: ColumnDefinition[]
}

export interface ColumnDefinition {
  key: string
  label: string
  dataType: 'string' | 'number' | 'date' | 'enum'
  required: boolean
  enumOptions?: string[]
}

/**
 * 表格行数据（多个 FormItem 组成一行）
 */
export type FormRow = FormItem[]

/**
 * 识别结果响应
 */
export interface RecognitionResult {
  requestId: string
  rows: FormRow[]
  timestamp: string // ISO 8601
}

