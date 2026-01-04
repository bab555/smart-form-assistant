/**
 * 聊天流组件 - 显示消息列表
 */

import { useEffect, useRef } from 'react'
import ChatBubble from './ChatBubble'
import type { ChatMessage } from '@types'

interface ChatStreamProps {
  messages: ChatMessage[]
}

export default function ChatStream({ messages }: ChatStreamProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  // 自动滚动到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="h-full overflow-y-auto custom-scrollbar px-4 py-3 space-y-3">
      {messages.map((message) => (
        <ChatBubble key={message.id} message={message} />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}

