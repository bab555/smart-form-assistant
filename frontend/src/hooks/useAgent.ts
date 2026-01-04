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

  const { setCurrentStep, setThinking, updateCell, addRow, setAmbiguous } = useFormStore()

  // 处理 WebSocket 消息
  const handleMessage = useCallback(
    (message: WebSocketMessage) => {
      console.log('收到消息:', message)

      switch (message.type) {
        case 'step_start':
          if ('step' in message) {
            setCurrentStep(message.step as AgentStep)
            setThinking(true)
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
            setThinking(false)
          }
          break

        case 'agent_thought':
          if ('content' in message) {
            addLog('idle', message.content as string, 'info')
          }
          break

        case 'tool_action':
          if ('tool' in message && 'params' in message) {
            handleToolAction(message.tool as string, message.params as Record<string, any>)
          }
          break

        case 'error':
          if ('message' in message) {
            addLog('error', message.message as string, 'error')
            setThinking(false)
          }
          break

        case 'pong':
          // Heartbeat response
          break

        default:
          console.warn('未知消息类型:', message)
      }
    },
    [setCurrentStep, setThinking, updateCell, addRow, setAmbiguous]
  )

  // 处理工具调用
  const handleToolAction = useCallback(
    (tool: string, params: Record<string, any>) => {
      switch (tool) {
        case 'update_table':
          // 更新表格
          if (params.rows) {
            params.rows.forEach((row: any) => {
              addRow(row)
            })
          }
          break

        case 'update_cell':
          // 更新单元格
          if (params.rowIndex !== undefined && params.key && params.value !== undefined) {
            updateCell(params.rowIndex, params.key, params.value)
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
            setAmbiguous(params.rowIndex, params.key, params.candidates)
          }
          break

        default:
          console.warn('未知工具:', tool)
      }
    },
    [updateCell, addRow, setAmbiguous]
  )

  // 添加日志
  const addLog = useCallback(
    (step: AgentStep, message: string, type: 'info' | 'success' | 'warning' | 'error') => {
      setAgentState((prev: any) => ({
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

  // 连接 WebSocket
  useEffect(() => {
    wsClient
      .connect()
      .then(() => {
        setAgentState((prev: any) => ({ ...prev, isConnected: true }))
      })
      .catch((error) => {
        console.error('WebSocket 连接失败:', error)
        setAgentState((prev: any) => ({ ...prev, isConnected: false }))
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
  const sendMessage = useCallback((message: any) => {
    wsClient.send(message)
  }, [])

  // 清空日志
  const clearLogs = useCallback(() => {
    setAgentState((prev: any) => ({ ...prev, logs: [] }))
  }, [])

  return {
    agentState,
    sendMessage,
    clearLogs,
    isConnected: agentState.isConnected,
    logs: agentState.logs,
  }
}

