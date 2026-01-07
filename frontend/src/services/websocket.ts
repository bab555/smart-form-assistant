/**
 * WebSocket 客户端封装
 */

import type { WebSocketMessage } from '@types'

export type MessageHandler = (message: WebSocketMessage) => void

export class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private messageHandlers: Set<MessageHandler> = new Set()
  private isManualClose = false
  public readonly clientId: string

  constructor(url?: string) {
    // 处理 WebSocket URL
    const configUrl = url || import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'
    this.url = this.resolveWebSocketUrl(configUrl)
    // 生成随机 Client ID
    this.clientId = `client_${Math.random().toString(36).substring(2, 9)}_${Date.now()}`
  }

  /**
   * 将相对路径转换为完整的 WebSocket URL
   */
  private resolveWebSocketUrl(configUrl: string): string {
    // 如果已经是完整的 ws:// 或 wss:// URL，直接返回
    if (configUrl.startsWith('ws://') || configUrl.startsWith('wss://')) {
      return configUrl
    }

    // 相对路径：从当前页面 URL 推断
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    
    // 确保路径以 / 开头
    const path = configUrl.startsWith('/') ? configUrl : `/${configUrl}`
    
    return `${protocol}//${host}${path}`
  }

  /**
   * 连接 WebSocket
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // 带上 client_id 参数
        this.ws = new WebSocket(`${this.url}/agent?client_id=${this.clientId}`)

        this.ws.onopen = () => {
          console.log(`WebSocket 连接成功 (Client ID: ${this.clientId})`)
          this.reconnectAttempts = 0
          this.isManualClose = false
          this.sendPing()
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            this.notifyHandlers(message)
          } catch (error) {
            console.error('解析 WebSocket 消息失败:', error)
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket 错误:', error)
          reject(error)
        }

        this.ws.onclose = () => {
          console.log('WebSocket 连接关闭')
          if (!this.isManualClose) {
            this.reconnect()
          }
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.isManualClose = true
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * 发送消息
   */
  send(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket 未连接，无法发送消息')
    }
  }

  /**
   * 发送 Ping
   */
  private sendPing() {
    this.send({ type: 'ping' })
  }

  /**
   * 重新连接
   */
  private reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('WebSocket 重连次数已达上限')
      return
    }

    this.reconnectAttempts++
    console.log(`尝试重连 WebSocket (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

    setTimeout(() => {
      this.connect().catch((error) => {
        console.error('重连失败:', error)
      })
    }, this.reconnectDelay * this.reconnectAttempts)
  }

  /**
   * 注册消息处理器
   */
  onMessage(handler: MessageHandler) {
    this.messageHandlers.add(handler)
  }

  /**
   * 移除消息处理器
   */
  offMessage(handler: MessageHandler) {
    this.messageHandlers.delete(handler)
  }

  /**
   * 通知所有处理器
   */
  private notifyHandlers(message: WebSocketMessage) {
    this.messageHandlers.forEach((handler) => {
      try {
        handler(message)
      } catch (error) {
        console.error('消息处理器执行失败:', error)
      }
    })
  }

  /**
   * 获取连接状态
   */
  get isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }
}

// 导出单例
export const wsClient = new WebSocketClient()
