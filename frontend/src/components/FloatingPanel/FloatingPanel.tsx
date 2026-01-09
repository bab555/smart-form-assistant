/**
 * FloatingPanel 左侧悬浮窗
 * 
 * 功能：
 * - 对话列表（支持文件/图片显示）
 * - 文字输入
 * - 语音按钮
 * - 文件上传（点击/拖拽/粘贴）
 * - 可折叠
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  Image as ImageIcon,
  X,
} from 'lucide-react';
import './FloatingPanel.css';

// 文件附件类型
interface FileAttachment {
  name: string;
  type: 'image' | 'file';
  url?: string;  // 图片预览 URL
  size?: number;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: Date;
  attachment?: FileAttachment;  // 文件附件
}

export const FloatingPanel: React.FC = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
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

  // 判断是否为图片文件
  const isImageFile = (file: File) => {
    return file.type.startsWith('image/');
  };

  // 获取文件图标
  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    if (['xlsx', 'xls', 'csv'].includes(ext || '')) return '📊';
    if (['docx', 'doc'].includes(ext || '')) return '📝';
    if (['pdf'].includes(ext || '')) return '📄';
    return '📎';
  };

  // 通用文件处理函数
  const processFile = useCallback(async (file: File) => {
    if (isUploading) return;
    
    setIsUploading(true);

    try {
      // 创建文件附件信息
      const isImage = isImageFile(file);
      const attachment: FileAttachment = {
        name: file.name,
        type: isImage ? 'image' : 'file',
        size: file.size,
      };

      // 如果是图片，创建预览 URL
      if (isImage) {
        attachment.url = URL.createObjectURL(file);
      }

      // 添加用户上传消息到聊天记录
      const uploadMessage: ChatMessage = {
        id: `${Date.now()}_upload`,
        role: 'user',
        content: isImage ? '上传了一张图片' : `上传了文件: ${file.name}`,
        timestamp: new Date(),
        attachment,
      };
      setMessages((prev) => [...prev, uploadMessage]);

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
          content: `正在处理: ${file.name}`,
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
    }
  }, [isUploading, createTable]);

  // 文件选择
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    await processFile(file);
    
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // 拖拽处理
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      await processFile(files[0]);
    }
  }, [processFile]);

  // 粘贴处理（只处理文件/图片，不处理文字）
  const handlePaste = useCallback(async (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      
      // 只处理文件类型（图片或其他文件）
      if (item.kind === 'file') {
        e.preventDefault(); // 阻止默认粘贴行为
        const file = item.getAsFile();
        if (file) {
          await processFile(file);
        }
        return;
      }
    }
    // 如果不是文件，不做任何处理，让默认行为处理文字粘贴
  }, [processFile]);

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

  // 渲染消息附件
  const renderAttachment = (attachment: FileAttachment) => {
    if (attachment.type === 'image' && attachment.url) {
      return (
        <div className="attachment-image" onClick={() => setPreviewImage(attachment.url || null)}>
          <img src={attachment.url} alt={attachment.name} />
          <div className="image-overlay">
            <ImageIcon size={16} />
            <span>点击查看</span>
          </div>
        </div>
      );
    }
    
    return (
      <div className="attachment-file">
        <span className="file-icon">{getFileIcon(attachment.name)}</span>
        <div className="file-info">
          <span className="file-name">{attachment.name}</span>
          {attachment.size && (
            <span className="file-size">{(attachment.size / 1024).toFixed(1)} KB</span>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className={`floating-panel ${isCollapsed ? 'collapsed' : ''}`}>
      {/* 图片预览弹窗 */}
      {previewImage && (
        <div className="image-preview-modal" onClick={() => setPreviewImage(null)}>
          <button className="preview-close" onClick={() => setPreviewImage(null)}>
            <X size={24} />
          </button>
          <img src={previewImage} alt="预览" />
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

          {/* 消息列表（支持拖拽） */}
          <div 
            ref={messagesContainerRef}
            className={`messages-container ${isDragOver ? 'drag-over' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onPaste={handlePaste}
            tabIndex={0}
          >
            {/* 拖拽提示 */}
            {isDragOver && (
              <div className="drag-overlay">
                <Upload size={48} />
                <p>释放以上传文件</p>
              </div>
            )}

            {messages.length === 0 ? (
              <div className="empty-messages">
                <Bot size={32} />
                <p>上传文件或输入指令开始</p>
                <p className="hint">支持拖拽文件或粘贴截图</p>
              </div>
            ) : (
              messages.map((msg) => (
                <div key={msg.id} className={`message ${msg.role}`}>
                  <div className="message-avatar">
                    {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
                  </div>
                  <div className="message-bubble">
                    {/* 如果有附件，先显示附件 */}
                    {msg.attachment && renderAttachment(msg.attachment)}
                    {/* 消息文本（如果有附件，显示较小的文字） */}
                    <div className={`message-text ${msg.attachment ? 'with-attachment' : ''}`}>
                      {msg.content}
                    </div>
                  </div>
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
                accept=".xlsx,.xls,.csv,.docx,.doc,.pdf,.png,.jpg,.jpeg,.webp,.gif"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
              />
              <button
                className="tool-btn upload-btn"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                title="上传文件"
              >
                <Upload size={16} />
                <span>上传</span>
              </button>
              <button 
                className={`tool-btn voice-btn ${isRecording ? 'recording' : ''}`}
                onClick={handleVoice} 
                title={isRecording ? '停止录音' : '语音输入'}
              >
                <Mic size={16} />
                <span>{isRecording ? '录音中...' : '语音'}</span>
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

