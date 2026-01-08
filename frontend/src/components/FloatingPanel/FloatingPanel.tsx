/**
 * FloatingPanel 左侧悬浮窗
 * 
 * 功能：
 * - 对话列表
 * - 文字输入
 * - 语音按钮
 * - 文件上传
 * - 可折叠
 */

import React, { useState, useEffect, useRef } from 'react';
import { wsClient } from '@/services/websocket';
import { EventType, ChatMessagePayload } from '@/services/protocol';
import { useCanvasStore } from '@/store/useCanvasStore';
import {
  MessageSquare,
  ChevronLeft,
  ChevronRight,
  Send,
  Mic,
  Upload,
  Bot,
  User,
  Plus,
} from 'lucide-react';
import { TemplateSelector } from './TemplateSelector';
import './FloatingPanel.css';

interface ChatMessage {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: Date;
}

export const FloatingPanel: React.FC = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  
  const { tables, activeTableId, createTable } = useCanvasStore();

  // 监听聊天消息
  useEffect(() => {
    const unsubChat = wsClient.on<ChatMessagePayload>(EventType.CHAT_MESSAGE, (data) => {
      const newMessage: ChatMessage = {
        id: `${Date.now()}_${Math.random()}`,
        role: data.role,
        content: data.content,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, newMessage]);
    });

    return () => {
      unsubChat();
    };
  }, []);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 发送消息
  const handleSend = () => {
    if (!inputValue.trim()) return;

    // 添加用户消息到本地
    const userMessage: ChatMessage = {
      id: `${Date.now()}_user`,
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // 构建完整的表格上下文（用于咨询分析）
    const tablesContext: Record<string, {
      id: string;
      title: string;
      rows: unknown[];
      schema: unknown[];
      metadata: unknown;
    }> = {};
    
    Object.entries(tables).forEach(([id, table]) => {
      tablesContext[id] = {
        id: table.id,
        title: table.title,
        rows: table.rows,
        schema: table.schema,
        metadata: table.metadata || {},
      };
    });

    // 发送到后端（包含完整表格数据）
    wsClient.send('chat', {
      content: inputValue,
      context: {
        tables: tablesContext,
        activeTableId: activeTableId, // 改名为 activeTableId 以明确语义
      },
    });

    setInputValue('');
  };

  // 文件上传
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);

    try {
      // 创建新表格来接收数据
      const tableId = createTable({
        title: file.name.replace(/\.[^/.]+$/, ''),
      });

      // 上传文件
      const formData = new FormData();
      formData.append('file', file);
      formData.append('task_type', 'extract');
      formData.append('client_id', wsClient.clientId);
      formData.append('table_id', tableId);

      const response = await fetch('/api/task/submit', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('上传失败');
      }

      // 添加系统消息
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}_system`,
          role: 'system',
          content: `正在处理文件: ${file.name}`,
          timestamp: new Date(),
        },
      ]);
    } catch (error) {
      console.error('Upload error:', error);
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}_error`,
          role: 'system',
          content: `上传失败: ${error instanceof Error ? error.message : '未知错误'}`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // 语音输入
  const handleVoice = async () => {
    if (isRecording) {
      // 停止录音
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      const chunks: Blob[] = [];

      mediaRecorder.ondataavailable = (e) => {
        chunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop());
        
        const audioBlob = new Blob(chunks, { type: 'audio/webm' });
        
        // 上传音频
        const formData = new FormData();
        formData.append('file', audioBlob, 'voice.webm');
        formData.append('task_type', 'audio');
        formData.append('client_id', wsClient.clientId);

        try {
          setMessages((prev) => [
            ...prev,
            {
              id: `${Date.now()}_system`,
              role: 'system',
              content: '正在识别语音...',
              timestamp: new Date(),
            },
          ]);

          const response = await fetch('/api/task/submit', {
            method: 'POST',
            body: formData,
          });

          if (!response.ok) {
            throw new Error('语音识别失败');
          }
        } catch (error) {
          setMessages((prev) => [
            ...prev,
            {
              id: `${Date.now()}_error`,
              role: 'system',
              content: `语音处理失败: ${error instanceof Error ? error.message : '未知错误'}`,
              timestamp: new Date(),
            },
          ]);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);

      // 5秒后自动停止
      setTimeout(() => {
        if (mediaRecorderRef.current?.state === 'recording') {
          mediaRecorderRef.current.stop();
          setIsRecording(false);
        }
      }, 5000);

    } catch (error) {
      console.error('Microphone access error:', error);
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}_error`,
          role: 'system',
          content: '无法访问麦克风，请检查权限设置',
          timestamp: new Date(),
        },
      ]);
    }
  };

  return (
    <div className={`floating-panel ${isCollapsed ? 'collapsed' : ''}`}>
      {/* 模板选择弹窗 */}
      {showTemplates && (
        <div className="template-modal">
          <div className="template-modal-backdrop" onClick={() => setShowTemplates(false)} />
          <TemplateSelector onClose={() => setShowTemplates(false)} />
        </div>
      )}

      {/* 折叠按钮 */}
      <button
        className="collapse-btn"
        onClick={() => setIsCollapsed(!isCollapsed)}
        title={isCollapsed ? '展开' : '收起'}
      >
        {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>

      {!isCollapsed && (
        <>
          {/* 标题栏 */}
          <div className="panel-header">
            <MessageSquare size={18} />
            <span>AI 助手</span>
          </div>

          {/* 消息列表 */}
          <div className="messages-container">
            {messages.length === 0 ? (
              <div className="empty-messages">
                <Bot size={32} />
                <p>上传文件或输入指令开始</p>
              </div>
            ) : (
              messages.map((msg) => (
                <div key={msg.id} className={`message ${msg.role}`}>
                  <div className="message-avatar">
                    {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
                  </div>
                  <div className="message-content">{msg.content}</div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 输入区域 */}
          <div className="input-area">
            {/* 工具栏 */}
            <div className="input-toolbar">
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls,.csv,.docx,.doc,.pdf,.png,.jpg,.jpeg"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
              />
              <button
                className="tool-btn"
                onClick={() => setShowTemplates(true)}
                title="新建表格"
              >
                <Plus size={16} />
              </button>
              <button
                className="tool-btn"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                title="上传文件"
              >
                <Upload size={16} />
              </button>
              <button 
                className={`tool-btn ${isRecording ? 'recording' : ''}`}
                onClick={handleVoice} 
                title={isRecording ? '停止录音' : '语音输入'}
              >
                <Mic size={16} />
              </button>
            </div>

            {/* 文本输入 */}
            <div className="text-input-wrapper">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="输入指令或问题..."
              />
              <button
                className="send-btn"
                onClick={handleSend}
                disabled={!inputValue.trim()}
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default FloatingPanel;

