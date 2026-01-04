/**
 * 类型定义聚合导出
 */

export * from './schema'
export * from './agent'

/**
 * 聊天消息类型
 */
export interface ChatMessage {
  id: string
  role: 'user' | 'agent' | 'system'
  content: string
  timestamp: string
  metadata?: {
    audioUrl?: string
    imageUrl?: string
    confidence?: number
  }
}

/**
 * 文件上传状态
 */
export interface UploadState {
  file: File | null
  preview: string | null
  status: 'idle' | 'uploading' | 'success' | 'error'
  progress: number
  errorMessage?: string
}

/**
 * 语音录制状态
 */
export interface RecordingState {
  isRecording: boolean
  audioBlob: Blob | null
  duration: number
  status: 'idle' | 'recording' | 'processing' | 'success' | 'error'
}

