/**
 * Agent 状态与 WebSocket 消息定义
 */

/**
 * Agent 工作流步骤
 */
export type AgentStep = 'idle' | 'ocr' | 'calibrating' | 'filling' | 'waiting_user' | 'error'

/**
 * WebSocket 消息类型
 */
export type WSMessageType =
  | 'ping'
  | 'pong'
  | 'agent_thought'
  | 'tool_action'
  | 'step_start'
  | 'step_log'
  | 'step_end'
  | 'error'
  | 'user_voice_text'

/**
 * WebSocket 消息基础结构
 */
export interface WSMessage {
  type: WSMessageType
  timestamp: string
}

/**
 * Agent 思考消息
 */
export interface AgentThoughtMessage extends WSMessage {
  type: 'agent_thought'
  content: string
  step: AgentStep
  status?: string
}

/**
 * 用户语音转文字消息
 */
export interface UserVoiceTextMessage extends WSMessage {
  type: 'user_voice_text'
  content: string
}

/**
 * 工具调用消息
 */
export interface ToolActionMessage extends WSMessage {
  type: 'tool_action'
  tool: string
  params: Record<string, any>
  content?: string
}

/**
 * 步骤开始消息
 */
export interface StepStartMessage extends WSMessage {
  type: 'step_start'
  step: AgentStep
  status: 'running'
}

/**
 * 步骤日志消息
 */
export interface StepLogMessage extends WSMessage {
  type: 'step_log'
  message: string
  step: AgentStep
}

/**
 * 步骤结束消息
 */
export interface StepEndMessage extends WSMessage {
  type: 'step_end'
  step: AgentStep
  status: 'success' | 'failed'
}

/**
 * 错误消息
 */
export interface ErrorMessage extends WSMessage {
  type: 'error'
  code: number
  message: string
}

/**
 * 所有可能的 WebSocket 消息类型联合
 */
export type WebSocketMessage =
  | AgentThoughtMessage
  | ToolActionMessage
  | StepStartMessage
  | StepLogMessage
  | StepEndMessage
  | ErrorMessage
  | UserVoiceTextMessage
  | WSMessage

/**
 * Agent 状态
 */
export interface AgentState {
  isConnected: boolean
  currentStep: AgentStep
  isThinking: boolean
  logs: LogEntry[]
}

export interface LogEntry {
  timestamp: string
  step: AgentStep
  message: string
  type: 'info' | 'success' | 'warning' | 'error'
}
