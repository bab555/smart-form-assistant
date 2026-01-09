/**
 * App 入口组件 (订单系统)
 * 
 * 布局：
 * - 左侧：AI 助手面板 (FloatingPanel) - 聊天、上传、状态
 * - 右侧：表格工作区 (Canvas) - Sheet 模式
 * - Toast 通知
 */

import React from 'react';
import { Canvas } from './components/Canvas';
import { FloatingPanel } from './components/FloatingPanel';
import { ToastContainer, useToast } from './components/Toast';
import { useWebSocketSync } from './hooks/useWebSocketSync';
import './App.css';

const App: React.FC = () => {
  // 初始化 WebSocket 事件同步
  useWebSocketSync();
  
  const { toasts, removeToast } = useToast();

  return (
    <div className="app">
      {/* 左侧：AI 助手面板 */}
      <FloatingPanel />
      {/* 右侧：表格工作区 */}
      <Canvas />
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
};

export default App;
