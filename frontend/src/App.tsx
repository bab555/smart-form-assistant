/**
 * App 入口组件 (订单系统)
 * 
 * 功能：
 * - SSO 无感登录 (监听 postMessage 或 URL 参数)
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
// import { Login } from './pages/Login'; // 移除登录页
import './App.css';

const App: React.FC = () => {
  const { isLoggedIn, checkAuth, user, logout, loginWithToken } = useAuthStore();
  const { reset: resetData, loadPartners } = useDataStore();
  const [isChecking, setIsChecking] = useState(true);
  
  // 初始化 WebSocket 事件同步（仅在登录后）
  useWebSocketSync();
  
  const { toasts, removeToast } = useToast();
  
  // 1. 初始化检查：URL参数 / 本地存储 / postMessage
  useEffect(() => {
    const init = async () => {
      setIsChecking(true);
      
      // A. 优先检查 URL 参数 (方便调试: ?access_token=xxx)
      const params = new URLSearchParams(window.location.search);
      const urlToken = params.get('access_token');
      
      if (urlToken) {
        console.log('[App] Found token in URL, attempting SSO...');
        const success = await loginWithToken(urlToken);
        if (success) {
            // 清除 URL 参数，避免刷新重复提交
            window.history.replaceState({}, '', window.location.pathname);
            setIsChecking(false);
            return;
        }
      }
      
      // B. 检查本地已有登录状态
      const valid = await checkAuth();
      if (valid) {
          console.log('[App] Local session valid');
      }
      
      setIsChecking(false);
    };
    
    init();
  }, [checkAuth, loginWithToken]);
  
  // 2. 监听 iframe postMessage 消息
  useEffect(() => {
    const handleMessage = async (event: MessageEvent) => {
      // 安全检查：建议校验 event.origin
      // if (event.origin !== "https://your-parent-site.com") return;
      
      const { type, token } = event.data || {};
      
      if (type === 'SET_TOKEN' && token) {
        console.log('[App] Received token via postMessage');
        setIsChecking(true);
        await loginWithToken(token);
        setIsChecking(false);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [loginWithToken]);
  
  // 3. 登录成功后加载基础数据（合作伙伴列表）
  useEffect(() => {
    if (isLoggedIn) {
      console.log('[App] User logged in, loading partners...');
      loadPartners();
    }
  }, [isLoggedIn, loadPartners]);
  
  // 登出
  const handleLogout = async () => {
    await logout();
    resetData();
    // 通知父页面已登出 (可选)
    window.parent.postMessage({ type: 'LOGOUT_SUCCESS' }, '*');
  };
  
  // 加载中状态
  if (isChecking) {
    return (
      <div className="app-loading">
        <div className="loading-spinner"></div>
        <p>正在连接系统...</p>
      </div>
    );
  }
  
  // 未登录状态 - 显示提示而不是登录框
  if (!isLoggedIn) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-gray-50 text-gray-500">
        <div className="mb-4 text-4xl">🔐</div>
        <h2 className="text-xl font-medium mb-2">等待授权</h2>
        <p className="mb-8">请从数智食堂系统进入，或等待授权信息...</p>
        {/* 开发模式下提供一个模拟入口 (可选) */}
        {process.env.NODE_ENV === 'development' && (
           <div className="text-xs text-gray-400 border p-4 rounded bg-white">
             <p>开发调试：</p>
             <p>URL添加 ?access_token=TEST_TOKEN</p>
             <p>或 postMessage: {'{ type: "SET_TOKEN", token: "..." }'}</p>
           </div>
        )}
      </div>
    );
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
