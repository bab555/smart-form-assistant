/**
 * 通信协议定义 (Protocol Definition)
 * 与后端 protocol.py 保持一致
 * 
 * 原则：
 * - 前端 CanvasStore 是唯一权威数据源 (SoT)
 * - 后端是无状态执行器
 * - 事件仅用于推送结果，不驱动前端业务逻辑分支
 */

// ========== 事件类型 ==========

export enum EventType {
  // 连接管理
  CONNECTION_ACK = 'connection_ack',
  SYNC_STATE = 'sync_state',
  
  // 任务状态 (仅用于日志/调试)
  TASK_START = 'task_start',
  TASK_FINISH = 'task_finish',
  NODE_START = 'node_start',
  NODE_FINISH = 'node_finish',
  
  // 数据更新 (核心)
  ROW_COMPLETE = 'row_complete',
  TABLE_REPLACE = 'table_replace',
  TABLE_CREATE = 'table_create',
  TABLE_DELETE = 'table_delete',
  CELL_UPDATE = 'cell_update',
  
  // 校对建议
  CALIBRATION_NOTE = 'calibration_note',
  
  // 对话
  CHAT_MESSAGE = 'chat_message',
  
  // 工具调用
  TOOL_CALL = 'tool_call',
  
  // 表格元数据
  TABLE_METADATA = 'table_metadata',
  
  // 异常
  ERROR = 'error',
}

// ========== 消息结构 ==========

export interface WebSocketMessage<T = Record<string, unknown>> {
  type: EventType | string;
  client_id: string;
  timestamp: string;
  data: T;
}

// ========== Payload 类型 ==========

export interface ConnectionAckPayload {
  status: 'connected';
}

export interface TaskStartPayload {
  task_id: string;
  task_type: 'extract' | 'audio' | 'chat';
}

export interface TaskFinishPayload {
  task_id: string;
  success: boolean;
  message?: string;
}

export interface RowCompletePayload {
  table_id: string;
  row: Record<string, unknown>;
}

export interface TableReplacePayload {
  table_id: string;
  rows: Record<string, unknown>[];
  schema?: ColumnSchema[];
  metadata?: TableMetadata;
}

export interface TableCreatePayload {
  table_id: string;
  title: string;
  schema: ColumnSchema[];
  rows?: Record<string, unknown>[];
  position?: { x: number; y: number };
  metadata?: TableMetadata;
}

export interface CellUpdatePayload {
  table_id: string;
  row_index: number;
  col_key: string;
  value: unknown;
}

export interface CalibrationNotePayload {
  table_id: string;
  row_index: number;
  note: string;
  severity: 'info' | 'warning' | 'error';
}

export interface ChatMessagePayload {
  role: 'user' | 'agent' | 'system';
  content: string;
  content_type: 'text' | 'markdown';
}

export interface ErrorPayload {
  code: number;
  message: string;
  details?: Record<string, unknown>;
}

// ========== 辅助类型 ==========

export interface ColumnSchema {
  key: string;
  title: string;
  type?: 'text' | 'number' | 'date';
  width?: number;
}

export interface TableMetadata {
  date?: string;
  orderNo?: string;
  customer?: string;
  [key: string]: unknown;
}

// ========== 类型守卫 ==========

export function isEventType(type: string): type is EventType {
  return Object.values(EventType).includes(type as EventType);
}

