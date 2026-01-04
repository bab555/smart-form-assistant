/**
 * 聊天面板组件 - 左栏
 */

import { useState } from 'react'
import ChatStream from './ChatStream'
import InputArea from './InputArea'
import type { ChatMessage } from '@types'

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      role: 'system',
      content: '您好！我是智能表单助手，可以通过语音或图片帮您快速填写表单。',
      timestamp: new Date().toISOString(),
    },
  ])

  const handleSendMessage = (content: string, metadata?: any) => {
    const newMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
      metadata,
    }
    setMessages((prev) => [...prev, newMessage])
  }

  return (
    <div className="h-full flex flex-col">
      {/* 标题栏 */}
      <div className="px-4 py-3 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-800">智能对话</h2>
        <p className="text-xs text-gray-500 mt-1">语音或文字交互</p>
      </div>

      {/* 聊天流 */}
      <div className="flex-1 overflow-hidden">
        <ChatStream messages={messages} />
      </div>

      {/* 输入区 */}
      <div className="border-t border-gray-200">
        <InputArea onSendMessage={handleSendMessage} />
      </div>
    </div>
  )
}

