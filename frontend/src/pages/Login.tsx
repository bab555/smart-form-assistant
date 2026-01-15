/**
 * 登录页面
 * 
 * 风格：与主应用一致（深蓝色渐变 + 白色卡片）
 */

import React, { useState } from 'react';
import { useAuthStore } from '../store/useAuthStore';
import { useDataStore } from '../store/useDataStore';
import './Login.css';

interface LoginProps {
  onLoginSuccess: () => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState('');
  const [showSync, setShowSync] = useState(false);
  
  const { login, isLoading } = useAuthStore();
  const { 
    loadPartners, 
    loadRestaurants, 
    loadOrderTypes, 
    syncProducts,
    syncMessage,
    syncProgress,
  } = useDataStore();
  
  // 登录成功后的数据加载流程
  const handlePostLogin = async () => {
    setShowSync(true);
    
    try {
      // 1. 加载基础数据
      await Promise.all([
        loadPartners(),
        loadRestaurants(),
        loadOrderTypes(),
      ]);
      
      // 2. 如果有合作方，同步商品库
      const currentPartners = useDataStore.getState().partners;
      if (currentPartners.length > 0) {
        const firstPartnerId = currentPartners[0].id;
        useDataStore.getState().setSelectedPartner(firstPartnerId);
        await syncProducts(firstPartnerId);
      }
      
      // 完成
      setTimeout(() => {
        setShowSync(false);
        onLoginSuccess();
      }, 500);
      
    } catch (error) {
      console.error('Post login error:', error);
      setShowSync(false);
      onLoginSuccess();
    }
  };
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (!username.trim()) {
      setError('请输入手机号');
      return;
    }
    
    if (!password.trim()) {
      setError('请输入密码');
      return;
    }
    
    const success = await login(username.trim(), password, remember);
    
    if (success) {
      await handlePostLogin();
    } else {
      setError('用户名或密码错误');
    }
  };
  
  // 同步遮罩
  if (showSync) {
    return (
      <div className="login-page">
        <div className="sync-overlay">
          <div className="sync-card">
            <div className="sync-icon">
              <svg viewBox="0 0 24 24" className="sync-spinner">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none" strokeDasharray="31.4" strokeDashoffset="10" />
              </svg>
            </div>
            <h3>正在同步资料</h3>
            <p>{syncMessage || '正在加载数据...'}</p>
            <div className="sync-progress-bar">
              <div 
                className="sync-progress-fill" 
                style={{ width: `${syncProgress}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="login-page">
      <div className="login-container">
        {/* Logo 区域 */}
        <div className="login-header">
          <div className="login-logo">
            <span className="logo-icon">📋</span>
          </div>
          <h1>智能订单助手</h1>
          <p>AI 驱动的订单智能识别系统</p>
        </div>
        
        {/* 登录表单 */}
        <form className="login-form" onSubmit={handleSubmit}>
          {error && (
            <div className="login-error">
              <span className="error-icon">⚠️</span>
              {error}
            </div>
          )}
          
          <div className="form-group">
            <label htmlFor="username">
              <span className="input-icon">📱</span>
              手机号
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="请输入手机号"
              autoComplete="username"
              disabled={isLoading}
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">
              <span className="input-icon">🔒</span>
              密码
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              autoComplete="current-password"
              disabled={isLoading}
            />
          </div>
          
          <div className="form-options">
            <label className="remember-me">
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
                disabled={isLoading}
              />
              <span className="checkbox-custom"></span>
              记住登录
            </label>
          </div>
          
          <button 
            type="submit" 
            className="login-button"
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <span className="button-spinner"></span>
                登录中...
              </>
            ) : (
              '登 录'
            )}
          </button>
        </form>
        
        {/* 底部信息 */}
        <div className="login-footer">
          <p>© 2026 智能订单助手 · 安全登录</p>
        </div>
      </div>
    </div>
  );
};

export default Login;

