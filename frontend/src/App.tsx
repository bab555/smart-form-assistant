/**
 * App 入口组件 (重构版)
 * 
 * 布局：
 * - 全屏画布 (Canvas)
 * - 左侧悬浮窗 (FloatingPanel)
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
      <Canvas />
      <FloatingPanel />
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
};

export default App;
