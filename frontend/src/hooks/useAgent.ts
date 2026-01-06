/**
 * Agent WebSocket 连接与状态管理
 */

import { useEffect, useState, useCallback } from 'react'
import { wsClient } from '@services/websocket'
import type { AgentState, WebSocketMessage, AgentStep } from '@types'
import { useFormStore } from './useFormStore'

export function useAgent() {
  const [agentState, setAgentState] = useState<AgentState>({
    isConnected: false,
    currentStep: 'idle',
    isThinking: false,
    logs: [],
  })

  // 添加日志
  const addLog = useCallback(
    (step: AgentStep, message: string, type: 'info' | 'success' | 'warning' | 'error') => {
      setAgentState((prev) => ({
        ...prev,
        logs: [
          ...prev.logs,
          {
            timestamp: new Date().toISOString(),
            step,
            message,
            type,
          },
        ],
      }))
    },
    []
  )

  // 处理工具调用 - 直接从 store 获取最新 actions
  const handleToolAction = useCallback(
    (tool: string, params: Record<string, unknown>) => {
      console.log('🔧 执行工具调用:', tool, params)
      
      // 直接获取最新的 store state 和 actions
      const store = useFormStore.getState()
      
      switch (tool) {
        case 'update_table':
          // 更新表格
          if (params.rows && Array.isArray(params.rows)) {
            params.rows.forEach((row) => {
              store.addRow(row)
            })
          }
          break

        case 'update_cell':
          // 更新单元格
          const rowIndex = params.rowIndex as number
          // 将 key 转换为 snake_case (后端可能发送 "Miao Shu"，需转为 "miao_shu")
          const rawKey = params.key as string
          const key = rawKey.toLowerCase().replace(/\s+/g, '_')
          const value = params.value
          
          console.log(`📝 更新单元格: rowIndex=${rowIndex}, key=${key}, value=${value}`)
          console.log('当前 rows:', store.rows)
          
          if (rowIndex !== undefined && key && value !== undefined) {
            // 检查行是否存在
            if (store.rows[rowIndex]) {
              console.log(`行 ${rowIndex} 存在:`, store.rows[rowIndex])
              // 检查 key 是否存在
              const cell = store.rows[rowIndex].find((c: any) => c.key === key)
              if (cell) {
                console.log(`找到 key=${key} 的单元格:`, cell)
              } else {
                console.warn(`❌ 未找到 key=${key} 的单元格，可用的 keys:`, store.rows[rowIndex].map((c: any) => c.key))
              }
            } else {
              console.warn(`❌ 行 ${rowIndex} 不存在`)
            }
            
            store.updateCell(rowIndex, key, value)
            console.log('✅ updateCell 已调用，更新后的 rows:', useFormStore.getState().rows)
          } else {
            console.warn('❌ 参数不完整:', { rowIndex, key, value })
          }
          break

        case 'mark_ambiguous':
          // 标记歧义
          if (
            params.rowIndex !== undefined &&
            params.key &&
            params.candidates &&
            Array.isArray(params.candidates)
          ) {
            store.setAmbiguous(
              params.rowIndex as number,
              params.key as string,
              params.candidates as string[]
            )
          }
          break

        default:
          console.warn('未知工具:', tool)
      }
    },
    []
  )

  // 处理 WebSocket 消息
  const handleMessage = useCallback(
    (message: WebSocketMessage) => {
      console.log('📨 收到消息:', message)
      
      // 直接获取最新的 store
      const store = useFormStore.getState()

      switch (message.type) {
        case 'step_start':
          if ('step' in message) {
            store.setCurrentStep(message.step as AgentStep)
            store.setThinking(true)
            addLog(message.step as AgentStep, `开始执行: ${message.step}`, 'info')
          }
          break

        case 'step_log':
          if ('step' in message && 'message' in message) {
            addLog(message.step as AgentStep, message.message as string, 'info')
          }
          break

        case 'step_end':
          if ('step' in message && 'status' in message) {
            const logType = message.status === 'success' ? 'success' : 'error'
            addLog(message.step as AgentStep, `完成: ${message.step}`, logType)
            store.setThinking(false)
          }
          break

        case 'agent_thought':
          if ('content' in message) {
            addLog('idle', message.content as string, 'info')
          }
          break

        case 'tool_action':
          if ('tool' in message && 'params' in message) {
            const tool = message.tool as string
            const params = message.params as Record<string, unknown>
            handleToolAction(tool, params)
          }
          break

        case 'error':
          if ('message' in message) {
            addLog('error', message.message as string, 'error')
            store.setThinking(false)
          }
          break

        case 'pong':
          // Heartbeat response
          break

        default:
          console.warn('未知消息类型:', message)
      }
    },
    [addLog, handleToolAction]
  )

  // 连接 WebSocket
  useEffect(() => {
    wsClient
      .connect()
      .then(() => {
        setAgentState((prev) => ({ ...prev, isConnected: true }))
      })
      .catch((error) => {
        console.error('WebSocket 连接失败:', error)
        setAgentState((prev) => ({ ...prev, isConnected: false }))
      })

    // 注册消息处理器
    wsClient.onMessage(handleMessage)

    // 清理
    return () => {
      wsClient.offMessage(handleMessage)
      wsClient.disconnect()
    }
  }, [handleMessage])

  // 发送消息
  const sendMessage = useCallback((message: unknown) => {
    wsClient.send(message)
  }, [])

  // 清空日志
  const clearLogs = useCallback(() => {
    setAgentState((prev) => ({ ...prev, logs: [] }))
  }, [])

  return {
    agentState,
    sendMessage,
    clearLogs,
    isConnected: agentState.isConnected,
    logs: agentState.logs,
  }
}
