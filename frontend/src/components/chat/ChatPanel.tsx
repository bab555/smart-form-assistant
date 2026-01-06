/**
 * 聊天面板组件 - 左栏
 * 
 * 修正：
 * 1. 消息需要通过 WebSocket 发送给后端 ChatAgent
 * 2. 监听 WebSocket 消息（Agent 回复、工具调用结果）
 */

import { useState, useEffect } from 'react'
import ChatStream from './ChatStream'
import InputArea from './InputArea'
import type { ChatMessage, WebSocketMessage } from '@types'
import { wsClient } from '@services/websocket'
import { useFormStore } from '@hooks/useFormStore'

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      role: 'system',
      content: '您好！我是智能表单助手，可以通过语音或图片帮您快速填写表单。',
      timestamp: new Date().toISOString(),
    },
  ])

  // 引用 Store 中的数据
  const { rows, selectedCellIndex, getCell } = useFormStore()
  
  // 发送消息处理
  const handleSendMessage = (content: string, metadata?: any) => {
    // 1. 本地立即显示用户消息
    const newMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
      metadata,
    }
    setMessages((prev) => [...prev, newMessage])

    // 2. 构建上下文数据 (可选：只传关键信息或当前选中行)
    const context = {
      rows: rows, // 实际应用中可能需要截断，避免 Token 过多
      selectedCell: selectedCellIndex ? getCell(selectedCellIndex.row, '') : null // 传递当前选中单元格信息如果需要
    }

    // 3. 通过 WebSocket 发送给后端
    wsClient.send({
      type: 'chat',
      content,
      context
    })
  }

  // 监听 WebSocket 消息，更新聊天列表
  useEffect(() => {
    const handleMessage = (message: WebSocketMessage) => {
      // 处理语音转文字后的用户消息（显示为用户发送的内容）
      if (message.type === 'user_voice_text' && 'content' in message && message.content) {
        setMessages((prev) => [
          ...prev,
          {
            id: `voice-${Date.now()}`,
            role: 'user',
            content: `🎤 ${message.content}`, // 添加麦克风图标标识语音来源
            timestamp: (message as any).timestamp || new Date().toISOString(),
          },
        ])
      }
      
      // 处理 Agent 回复
      if (message.type === 'agent_thought' && 'content' in message && message.content) {
        // 过滤掉 "正在思考..." 这种中间状态的消息
        if ('status' in message && message.status === 'thinking') {
          return
        }
        
        const msgId = `${Date.now()}-${(message.content as string).length}`
        
        setMessages((prev) => [
          ...prev,
          {
            id: msgId,
            role: 'agent', // Fixed: 'assistant' -> 'agent'
            content: message.content as string,
            timestamp: (message as any).timestamp || new Date().toISOString(),
          },
        ])
      }
      
      // 处理工具调用产生的系统通知
      if (message.type === 'tool_action') {
         setMessages((prev) => [
          ...prev,
          {
            id: `tool-${Date.now()}`,
            role: 'system', // 显示为系统通知
            content: `⚙️ ${'content' in message ? message.content : '正在执行操作...'}`,
            timestamp: (message as any).timestamp || new Date().toISOString(),
          },
        ])
      }
      
      // 处理错误消息
      if (message.type === 'error' && 'message' in message) {
         setMessages((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            role: 'agent', // Fixed: 'assistant' -> 'agent'
            content: `❌ 出错啦：${message.message}`,
            timestamp: (message as any).timestamp || new Date().toISOString(),
          },
        ])
      }
    }

    wsClient.onMessage(handleMessage)

    return () => {
      wsClient.offMessage(handleMessage)
    }
  }, []) // 依赖为空，只注册一次

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
