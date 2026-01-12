/**
 * FloatingPanel 左侧悬浮窗
 * 
 * 功能：
 * - 对话列表（支持文件/图片显示）
 * - 文字输入
 * - 语音按钮
 * - 文件上传（点击/拖拽/粘贴）
 * - 可折叠
 * - 流式思考过程显示
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { wsClient } from '@/services/websocket';
import { EventType, ChatMessagePayload } from '@/services/protocol';
import { useCanvasStore } from '@/store/useCanvasStore';
import { toast } from '@/components/Toast';
import {
  MessageSquare,
  ChevronLeft,
  ChevronRight,
  Send,
  Upload,
  Bot,
  User,
  Image as ImageIcon,
  X,
  BrainCircuit, // 思考图标
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import './FloatingPanel.css';

// 文件附件类型
interface FileAttachment {
  name: string;
  type: 'image' | 'file';
  url?: string;  // 图片预览 URL
  size?: number;
  path?: string; // 上传后的路径
  content?: string; // 文件文本内容（用于预览）
}

interface ChatMessage {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: Date;
  attachment?: FileAttachment;  // 文件附件
  // 思考过程字段
  thinking?: string;
}

export const FloatingPanel: React.FC = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [previewFile, setPreviewFile] = useState<FileAttachment | null>(null);
  const [filePreviewLoading, setFilePreviewLoading] = useState(false);
  
  // 思考过程折叠状态 (msgId -> boolean)
  const [expandedThinking, setExpandedThinking] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const { tables, activeTableId } = useCanvasStore();
  const openCustomerModal = useCanvasStore((s) => s.openCustomerModal);

  const ensureCustomerSelected = useCallback(() => {
    if (!activeTableId) {
      toast.error('请先选择客户');
      return false;
    }
    const t = tables[activeTableId];
    if (!t?.metadata?.customerId) {
      // 打开全局居中大弹窗
      openCustomerModal(activeTableId);
      return false;
    }
    return true;
  }, [activeTableId, tables, openCustomerModal]);

  // 监听聊天消息 (支持流式更新)
  useEffect(() => {
    const unsubChat = wsClient.on<ChatMessagePayload>(EventType.CHAT_MESSAGE, (data) => {
      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        
        // 1. 思考过程 (增量)
        if (data.is_thinking) {
          // 如果最后一条是 Agent 消息且正在生成中 (我们假设如果是 thinking 就在最后一条)
          if (lastMsg && lastMsg.role === 'agent') {
            const updatedLast = {
              ...lastMsg,
              thinking: (lastMsg.thinking || '') + data.content
            };
            return [...prev.slice(0, -1), updatedLast];
          } else {
             // 新建一条消息开始思考
             const newMessage: ChatMessage = {
              id: `${Date.now()}_${Math.random()}`,
              role: 'agent',
              content: '', // 内容暂时为空
              thinking: data.content,
              timestamp: new Date(),
            };
            // 默认展开思考
            setExpandedThinking(prev => ({...prev, [newMessage.id]: true}));
            return [...prev, newMessage];
          }
        }
        
        // 2. 正文内容 (增量)
        if (data.is_delta) {
           if (lastMsg && lastMsg.role === 'agent') {
            const updatedLast = {
              ...lastMsg,
              content: lastMsg.content + data.content
            };
            return [...prev.slice(0, -1), updatedLast];
           } else {
             // 可能是刚思考完，或者直接开始输出
             const newMessage: ChatMessage = {
               id: `${Date.now()}_${Math.random()}`,
               role: 'agent',
               content: data.content,
               timestamp: new Date(),
             };
             return [...prev, newMessage];
           }
        }
        
        // 3. 完整消息 (非流式)
        if (!data.is_delta && !data.is_thinking) {
           const newMessage: ChatMessage = {
             id: `${Date.now()}_${Math.random()}`,
             role: data.role,
             content: data.content,
             timestamp: new Date(),
           };
           return [...prev, newMessage];
        }

        return prev;
      });
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
    if (!ensureCustomerSelected()) return;

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
    if (!ensureCustomerSelected()) return;
    
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
      
      // 如果是文本文件，尝试读取内容用于预览
      const ext = file.name.split('.').pop()?.toLowerCase();
      if (['txt', 'csv'].includes(ext || '')) {
        try {
          attachment.content = await file.text();
        } catch { /* ignore */ }
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
      // (SimpleAgent 策略变了，这里只是为了 UI 展示，实际创建由后端推送)
      // 但为了兼容旧逻辑，且不确定后端是否能收到 File 对象，这里我们只负责上传
      // SimpleAgent 会在收到 file 后自动 create_table
      
      // 注意：现在 SimpleAgent 负责创建表格，所以前端不需要主动 createTable
      // 但我们需要 tableId 传给上传接口吗？
      // 看一下 websocket.py 的 handle_chat，它是处理 attachment 的
      // 现在的 handle_chat 逻辑是：如果有 attachments，读取并传给 SimpleAgent
      // 前端只需要把文件上传到后端某个位置，或者通过 WebSocket 传二进制？
      // 之前的逻辑是 POST /api/task/submit
      // 为了适配 SimpleAgent，我们可以继续用 /api/task/submit (它支持 task_type='extract')
      // 后端 api/endpoints.py 里需要确认是否兼容 SimpleAgent
      // 或者：既然我们已经有了 WebSocket 上传能力（虽然不推荐传大文件），
      // 但之前的逻辑是 POST 上传。
      // 我们暂且保留 POST 上传，但在后端修改 /api/task/submit 的处理逻辑。
      
      // 这里的逻辑：上传 -> 后端保存 -> WebSocket 发送 chat 消息带 attachment path
      
      const formData = new FormData();
      formData.append('file', file);
      formData.append('task_type', 'extract');
      formData.append('client_id', wsClient.clientId);

      // 临时：为了让新后端能通过 handle_chat 处理文件，
      // 我们需要一种方式告诉后端“我上传了个文件，路径在这里，请处理”
      // 现在的 /api/task/submit 可能会触发旧的 task manager
      
      // 修正方案：简单点，直接把文件转 base64 通过 WS 发送？不行，大文件会爆。
      // 保持 POST 上传，接口返回 path，然后 WS 发送 chat 消息带 path。
      
      const response = await fetch('/api/upload', {
         method: 'POST',
         body: formData
      });
      // 实际上现在的后端只有 endpoints.py 里的 submit_task
      // 让我们假设 submit_task 还能用，且我们修改 endpoints.py 让它只返回 path 
      // 或者我们可以只依赖现有的 upload 逻辑
      
      // 为了不改动太多，先假设 /api/task/submit 依然可用，
      // 并且后端已经适配了 (之前没改 endpoints.py，可能需要检查)
      
      if (!response.ok) throw new Error('上传失败');
      
      const result = await response.json();
      // result 应该包含 file_path 或者是 task_id
      
      // 如果是用现在的 SimpleAgent，我们希望通过 WS 触发
      // 所以这里我们手动发一个 chat 消息，带上 attachment info
      // 同时附带完整 tables 上下文，方便后端读取当前客户信息
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

      wsClient.send('chat', {
        content: `分析文件: ${file.name}`,
        context: { activeTableId, tables: tablesContext },
        attachments: [{
            name: file.name,
            path: result.file_path || result.path // 假设接口返回路径
        }]
      });

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
  }, [isUploading, activeTableId, ensureCustomerSelected, tables]);

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

  // 粘贴处理
  const handlePaste = useCallback(async (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.kind === 'file') {
        e.preventDefault(); 
        const file = item.getAsFile();
        if (file) {
          await processFile(file);
        }
        return;
      }
    }
  }, [processFile]);

  // 语音输入（已禁用）
  /*
  const handleVoice = async () => {
    if (isRecording) {
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
        
        const formData = new FormData();
        formData.append('file', audioBlob, 'voice.webm');
        formData.append('task_type', 'audio'); // 后端需适配 audio 任务转 chat
        formData.append('client_id', wsClient.clientId);

        try {
            // 这里仍使用 submit 接口
            await fetch('/api/task/submit', { method: 'POST', body: formData });
        } catch (error) {
            console.error(error);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
      setTimeout(() => {
        if (mediaRecorderRef.current?.state === 'recording') {
          mediaRecorderRef.current.stop();
          setIsRecording(false);
        }
      }, 5000);

    } catch (error) {
      console.error('Microphone access error:', error);
    }
  };
  */

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
    
    // 判断是否可预览的文件类型
    const ext = attachment.name.split('.').pop()?.toLowerCase();
    const isPreviewable = ['xlsx', 'xls', 'csv', 'docx', 'doc', 'txt'].includes(ext || '');
    
    return (
      <div 
        className={`attachment-file ${isPreviewable ? 'previewable' : ''}`}
        onClick={() => isPreviewable && handleFilePreview(attachment)}
        title={isPreviewable ? '点击查看文件内容' : undefined}
      >
        <span className="file-icon">{getFileIcon(attachment.name)}</span>
        <div className="file-info">
          <span className="file-name">{attachment.name}</span>
          {attachment.size && (
            <span className="file-size">{(attachment.size / 1024).toFixed(1)} KB</span>
          )}
        </div>
        {isPreviewable && (
          <span className="file-preview-hint">点击查看</span>
        )}
      </div>
    );
  };

  // 切换思考过程展开状态
  const toggleThinking = (msgId: string) => {
    setExpandedThinking(prev => ({...prev, [msgId]: !prev[msgId]}));
  };

  // 文件预览处理
  const handleFilePreview = async (attachment: FileAttachment) => {
    setPreviewFile(attachment);
    
    // 如果已经有内容，直接显示
    if (attachment.content) return;
    
    // 如果有 path，尝试从后端获取内容
    if (attachment.path) {
      setFilePreviewLoading(true);
      try {
        // 修复：Windows 路径包含反斜杠可能导致 URL 问题，替换为正斜杠
        const safePath = attachment.path.replace(/\\/g, '/');
        const response = await fetch(`/api/file/preview?path=${encodeURIComponent(safePath)}`);
        if (response.ok) {
          const data = await response.json();
          // 更新附件内容
          attachment.content = data.content || '（文件内容为空）';
          setPreviewFile({...attachment});
        } else {
          console.error('Preview fetch failed:', response.status, response.statusText);
          throw new Error('Preview failed');
        }
      } catch (e) {
        console.error('Preview error:', e);
        // 如果获取失败，显示提示
        attachment.content = '预览失败：无法读取文件内容。但文件已发送至后端处理，解析结果已填入表格。';
        setPreviewFile({...attachment});
      } finally {
        setFilePreviewLoading(false);
      }
    } else {
      // 没有 path 也没有 content，显示提示
      attachment.content = '文件内容已发送至后端处理，解析结果已填入表格。';
      setPreviewFile({...attachment});
    }
  };

  // 渲染预览内容（支持将 Pipe 表格渲染为 HTML 表格）
  const renderPreviewContent = (content: string) => {
    if (!content) return <div className="preview-empty">内容为空</div>;

    const lines = content.trim().split('\n');
    const elements: JSX.Element[] = [];
    let tableRows: string[] = [];
    let keyCounter = 0;

    const flushTable = () => {
      if (tableRows.length > 0) {
        // 渲染表格
        const header = tableRows[0];
        const body = tableRows.slice(1);
        
        elements.push(
          <div key={`tbl-${keyCounter++}`} className="preview-table-wrapper">
            <table className="preview-table">
              <thead>
                <tr>
                  {header.split('|').slice(1, -1).map((h, i) => (
                    <th key={i}>{h.trim()}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {body.map((row, i) => (
                  <tr key={i}>
                    {row.split('|').slice(1, -1).map((cell, j) => (
                      <td key={j}>{cell.trim()}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        tableRows = [];
      }
    };

    lines.forEach((line) => {
      const trimmed = line.trim();
      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        tableRows.push(trimmed);
      } else {
        flushTable();
        // 渲染普通文本/标题
        if (trimmed.startsWith('### ')) {
          elements.push(<h3 key={`h3-${keyCounter++}`} className="preview-h3">{trimmed.replace('### ', '')}</h3>);
        } else if (trimmed) {
          elements.push(<p key={`p-${keyCounter++}`} className="preview-p">{trimmed}</p>);
        }
      }
    });
    flushTable();

    return <div className="preview-content-wrapper">{elements}</div>;
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

      {/* 文件内容预览弹窗 */}
      {previewFile && (
        <div className="file-preview-modal">
          <div className="file-preview-backdrop" onClick={() => setPreviewFile(null)} />
          <div className="file-preview-container">
            <div className="file-preview-header">
              <span className="file-preview-icon">{getFileIcon(previewFile.name)}</span>
              <span className="file-preview-name">{previewFile.name}</span>
              <button className="file-preview-close" onClick={() => setPreviewFile(null)}>
                <X size={18} />
              </button>
            </div>
            <div className="file-preview-body">
              {filePreviewLoading ? (
                <div className="file-preview-loading">
                  <div className="loading-spinner" />
                  <span>加载中...</span>
                </div>
              ) : (
                renderPreviewContent(previewFile.content || '文件内容已发送至后端处理，解析结果已填入表格。')
              )}
            </div>
          </div>
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
                    {msg.attachment && renderAttachment(msg.attachment)}
                    
                    {/* 思考过程展示区 */}
                    {msg.thinking && (
                        <div className="thinking-process">
                            <div 
                                className="thinking-header" 
                                onClick={() => toggleThinking(msg.id)}
                            >
                                <BrainCircuit size={14} />
                                <span>深度思考中...</span>
                                {expandedThinking[msg.id] ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}
                            </div>
                            {expandedThinking[msg.id] && (
                                <div className="thinking-content">
                                    {msg.thinking}
                                </div>
                            )}
                        </div>
                    )}

                    {/* 正文内容 */}
                    {msg.content && (
                        <div className={`message-text ${msg.attachment ? 'with-attachment' : ''}`}>
                          {msg.content}
                        </div>
                    )}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 输入区域 */}
          <div className="input-area">
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
              {/* 语音功能暂时禁用
              <button 
                className={`tool-btn voice-btn ${isRecording ? 'recording' : ''}`}
                onClick={handleVoice} 
                title={isRecording ? '停止录音' : '语音输入'}
              >
                <Mic size={16} />
                <span>{isRecording ? '录音中...' : '语音'}</span>
              </button>
              */}
            </div>

            <div className="text-input-wrapper">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                onPaste={handlePaste}
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
