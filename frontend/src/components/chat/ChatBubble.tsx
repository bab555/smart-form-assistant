/**
 * 聊天气泡组件
 */

import { User, Bot, Info } from 'lucide-react'
import type { ChatMessage } from '@types'
import { formatTimestamp } from '@utils/helpers'

interface ChatBubbleProps {
  message: ChatMessage
}

export default function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  // 系统消息样式
  if (isSystem) {
    return (
      <div className="flex items-start gap-2 chat-bubble-enter">
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
          <Info size={16} className="text-gray-500" />
        </div>
        <div className="flex-1">
          <div className="bg-gray-50 rounded-lg px-3 py-2 text-sm text-gray-600">
            {message.content}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div
      className={`flex items-start gap-2 chat-bubble-enter ${isUser ? 'flex-row-reverse' : ''}`}
    >
      {/* 头像 */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-primary' : 'bg-success'
        }`}
      >
        {isUser ? <User size={16} className="text-white" /> : <Bot size={16} className="text-white" />}
      </div>

      {/* 消息内容 */}
      <div className={`flex-1 ${isUser ? 'text-right' : ''}`}>
        <div
          className={`inline-block max-w-[80%] rounded-lg px-3 py-2 ${
            isUser ? 'bg-primary text-white' : 'bg-gray-100 text-gray-800'
          }`}
        >
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>
        <p className="text-xs text-gray-400 mt-1">{formatTimestamp(message.timestamp)}</p>
      </div>
    </div>
  )
}

