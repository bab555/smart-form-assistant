/**
 * App 入口组件 (订单系统)
 * 
 * 功能：
 * - 登录认证
 * - 路由守卫
 * - 主应用布局
 */

import React, { useEffect, useState } from 'react';
import { Canvas } from './components/Canvas';
import { FloatingPanel } from './components/FloatingPanel';
import { ToastContainer, useToast } from './components/Toast';
import { useWebSocketSync } from './hooks/useWebSocketSync';
import { useAuthStore } from './store/useAuthStore';
import { useDataStore } from './store/useDataStore';
import { Login } from './pages/Login';
import './App.css';

const App: React.FC = () => {
  const { isLoggedIn, checkAuth, user, logout } = useAuthStore();
  const { reset: resetData } = useDataStore();
  const [isChecking, setIsChecking] = useState(true);
  const [showApp, setShowApp] = useState(false);
  
  // 初始化 WebSocket 事件同步（仅在登录后）
  useWebSocketSync();
  
  const { toasts, removeToast } = useToast();
  
  // 检查登录状态
  useEffect(() => {
    const check = async () => {
      setIsChecking(true);
      const valid = await checkAuth();
      setIsChecking(false);
      
      if (valid) {
        setShowApp(true);
      }
    };
    
    check();
  }, [checkAuth]);
  
  // 登录成功回调
  const handleLoginSuccess = () => {
    setShowApp(true);
  };
  
  // 登出
  const handleLogout = async () => {
    await logout();
    resetData();
    setShowApp(false);
  };
  
  // 检查中显示加载
  if (isChecking) {
    return (
      <div className="app-loading">
        <div className="loading-spinner"></div>
        <p>加载中...</p>
      </div>
    );
  }
  
  // 未登录显示登录页
  if (!isLoggedIn || !showApp) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }
  
  // 已登录显示主应用
  return (
    <div className="app">
      {/* 顶部用户栏 */}
      <div className="app-topbar">
        <div className="topbar-left">
          <span className="topbar-logo">📋</span>
          <span className="topbar-title">智能订单助手</span>
        </div>
        <div className="topbar-right">
          <span className="user-info">
            <span className="user-type">
              {user?.userType === 'purchaser' ? '🏫 学校' : '🚚 配送商'}
            </span>
            <span className="user-name">{user?.name}</span>
          </span>
          <button className="logout-btn" onClick={handleLogout}>
            退出
          </button>
        </div>
      </div>
      
      {/* 主内容区 */}
      <div className="app-main">
        {/* 左侧：AI 助手面板 */}
        <FloatingPanel />
        {/* 右侧：表格工作区 */}
        <Canvas />
      </div>
      
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
};

export default App;
