/**
 * 全局常量定义
 */

// 颜色主题（与 Tailwind 配置同步）
export const COLORS = {
  primary: '#1677FF',
  success: '#52C41A',
  warning: '#FAAD14',
  danger: '#FF4D4F',
  background: '#F5F7FA',
  card: '#FFFFFF',
} as const

// API 端点
export const API_ENDPOINTS = {
  workflow: {
    visual: '/workflow/visual',
    audio: '/workflow/audio',
  },
  template: {
    list: '/template/list',
    get: '/template',
  },
} as const

// WebSocket 事件
export const WS_EVENTS = {
  PING: 'ping',
  PONG: 'pong',
  AGENT_THOUGHT: 'agent_thought',
  TOOL_ACTION: 'tool_action',
  STEP_START: 'step_start',
  STEP_LOG: 'step_log',
  STEP_END: 'step_end',
  ERROR: 'error',
} as const

// 置信度阈值
export const CONFIDENCE_THRESHOLD = {
  HIGH: 0.9, // 高置信度，直接填入
  LOW: 0.7, // 低置信度，标记为歧义
} as const

// 录音配置
export const AUDIO_CONFIG = {
  sampleRate: 16000,
  numberOfAudioChannels: 1,
  mimeType: 'audio/wav',
  timeSlice: 1000,
  maxDuration: 60, // 秒
} as const

// 文件上传配置
export const UPLOAD_CONFIG = {
  maxSize: 10 * 1024 * 1024, // 10MB
  allowedTypes: ['image/jpeg', 'image/png', 'image/jpg', 'image/webp'],
  allowedExtensions: ['.jpg', '.jpeg', '.png', '.webp'],
} as const

// 动画配置
export const ANIMATION_DURATION = {
  fast: 150,
  normal: 300,
  slow: 500,
} as const

// LocalStorage Keys
export const STORAGE_KEYS = {
  FORM_DRAFT: 'smart_form_draft',
  USER_PREFERENCES: 'user_preferences',
  RECENT_TEMPLATES: 'recent_templates',
} as const

