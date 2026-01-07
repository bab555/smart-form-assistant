/**
 * WebSocket 客户端 (极简版)
 * 
 * 原则：
 * - 极简：只做 connect/reconnect/send/on
 * - 无心跳：依赖原生 onclose
 * - 事件驱动：通过 EventEmitter 模式分发消息
 */

import { EventType, WebSocketMessage } from './protocol';

type MessageHandler<T = unknown> = (data: T, message: WebSocketMessage<T>) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string = '';
  private handlers = new Map<string, Set<MessageHandler>>();
  private reconnectTimer: number | null = null;
  private _isConnected = false;
  
  // 生成唯一的 client_id
  public readonly clientId: string = `client_${Math.random().toString(36).slice(2, 10)}_${Date.now()}`;

  /**
   * 连接到 WebSocket 服务器
   */
  connect(url?: string): Promise<void> {
    // 解析 URL
    this.url = this.resolveUrl(url);
    
    return new Promise((resolve, reject) => {
      try {
        const wsUrl = `${this.url}/agent?client_id=${this.clientId}`;
        console.log(`[WS] Connecting to ${wsUrl}`);
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
          console.log(`[WS] Connected (client_id: ${this.clientId})`);
          this._isConnected = true;
          this.clearReconnectTimer();
          resolve();
        };
        
        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data) as WebSocketMessage;
            this.dispatch(message);
          } catch (e) {
            console.error('[WS] Failed to parse message:', e);
          }
        };
        
        this.ws.onerror = (error) => {
          console.error('[WS] Error:', error);
          reject(error);
        };
        
        this.ws.onclose = () => {
          console.log('[WS] Disconnected');
          this._isConnected = false;
          this.scheduleReconnect();
        };
        
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.clearReconnectTimer();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this._isConnected = false;
  }

  /**
   * 发送消息
   */
  send(type: string, data: Record<string, unknown> = {}) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[WS] Not connected, cannot send');
      return false;
    }
    
    const message = {
      type,
      client_id: this.clientId,
      timestamp: new Date().toISOString(),
      data,
    };
    
    this.ws.send(JSON.stringify(message));
    return true;
  }

  /**
   * 订阅事件
   */
  on<T = unknown>(eventType: EventType | string, handler: MessageHandler<T>) {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set());
    }
    this.handlers.get(eventType)!.add(handler as MessageHandler);
    
    // 返回取消订阅函数
    return () => {
      this.handlers.get(eventType)?.delete(handler as MessageHandler);
    };
  }

  /**
   * 取消订阅
   */
  off(eventType: EventType | string, handler?: MessageHandler) {
    if (handler) {
      this.handlers.get(eventType)?.delete(handler);
    } else {
      this.handlers.delete(eventType);
    }
  }

  /**
   * 是否已连接
   */
  get isConnected(): boolean {
    return this._isConnected && this.ws?.readyState === WebSocket.OPEN;
  }

  // ========== 私有方法 ==========

  /**
   * 解析 WebSocket URL
   */
  private resolveUrl(url?: string): string {
    const configUrl = url || import.meta.env.VITE_WS_URL || '/ws';
    
    // 如果是完整 URL，直接返回
    if (configUrl.startsWith('ws://') || configUrl.startsWith('wss://')) {
      return configUrl;
    }
    
    // 相对路径：从当前页面推断
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const path = configUrl.startsWith('/') ? configUrl : `/${configUrl}`;
    
    return `${protocol}//${host}${path}`;
  }

  /**
   * 分发消息到处理器
   */
  private dispatch(message: WebSocketMessage) {
    const { type, data } = message;
    
    // 调用对应类型的处理器
    const handlers = this.handlers.get(type);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(data, message);
        } catch (e) {
          console.error(`[WS] Handler error for ${type}:`, e);
        }
      });
    }
    
    // 也触发通配符处理器 (如果有)
    const wildcardHandlers = this.handlers.get('*');
    if (wildcardHandlers) {
      wildcardHandlers.forEach((handler) => {
        try {
          handler(data, message);
        } catch (e) {
          console.error('[WS] Wildcard handler error:', e);
        }
      });
    }
  }

  /**
   * 安排重连
   */
  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    
    console.log('[WS] Scheduling reconnect in 1s...');
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect(this.url).catch((e) => {
        console.error('[WS] Reconnect failed:', e);
      });
    }, 1000);
  }

  /**
   * 清除重连定时器
   */
  private clearReconnectTimer() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}

// 导出单例
export const wsClient = new WebSocketClient();

// 也导出类（方便测试或创建多实例）
export { WebSocketClient };
