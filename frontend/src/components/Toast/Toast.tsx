/**
 * Toast 通知组件
 * 
 * 功能：
 * - 显示成功/错误/警告/信息通知
 * - 自动消失
 * - 支持多个 Toast 堆叠
 */

import React, { useEffect, useState, useCallback } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';
import './Toast.css';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

interface ToastProps {
  toast: ToastItem;
  onRemove: (id: string) => void;
}

const iconMap = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const Toast: React.FC<ToastProps> = ({ toast, onRemove }) => {
  const [isLeaving, setIsLeaving] = useState(false);
  const Icon = iconMap[toast.type];

  const handleRemove = useCallback(() => {
    setIsLeaving(true);
    setTimeout(() => onRemove(toast.id), 300);
  }, [toast.id, onRemove]);

  useEffect(() => {
    const timer = setTimeout(handleRemove, toast.duration || 4000);
    return () => clearTimeout(timer);
  }, [toast.duration, handleRemove]);

  return (
    <div className={`toast toast-${toast.type} ${isLeaving ? 'leaving' : ''}`}>
      <Icon size={18} className="toast-icon" />
      <span className="toast-message">{toast.message}</span>
      <button className="toast-close" onClick={handleRemove}>
        <X size={14} />
      </button>
    </div>
  );
};

// ========== Toast Container ==========

interface ToastContainerProps {
  toasts: ToastItem[];
  onRemove: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onRemove }) => {
  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>
  );
};

// ========== Toast Hook ==========

let toastId = 0;
const listeners: Set<(toasts: ToastItem[]) => void> = new Set();
let toastList: ToastItem[] = [];

function emitChange() {
  listeners.forEach((listener) => listener([...toastList]));
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastItem[]>(toastList);

  useEffect(() => {
    listeners.add(setToasts);
    return () => {
      listeners.delete(setToasts);
    };
  }, []);

  const addToast = useCallback((type: ToastType, message: string, duration?: number) => {
    const id = `toast_${++toastId}`;
    toastList = [...toastList, { id, type, message, duration }];
    emitChange();
    return id;
  }, []);

  const removeToast = useCallback((id: string) => {
    toastList = toastList.filter((t) => t.id !== id);
    emitChange();
  }, []);

  return {
    toasts,
    addToast,
    removeToast,
    success: (message: string, duration?: number) => addToast('success', message, duration),
    error: (message: string, duration?: number) => addToast('error', message, duration),
    warning: (message: string, duration?: number) => addToast('warning', message, duration),
    info: (message: string, duration?: number) => addToast('info', message, duration),
  };
}

// ========== 全局 Toast 方法 ==========

export const toast = {
  success: (message: string, duration?: number) => {
    const id = `toast_${++toastId}`;
    toastList = [...toastList, { id, type: 'success', message, duration }];
    emitChange();
    return id;
  },
  error: (message: string, duration?: number) => {
    const id = `toast_${++toastId}`;
    toastList = [...toastList, { id, type: 'error', message, duration }];
    emitChange();
    return id;
  },
  warning: (message: string, duration?: number) => {
    const id = `toast_${++toastId}`;
    toastList = [...toastList, { id, type: 'warning', message, duration }];
    emitChange();
    return id;
  },
  info: (message: string, duration?: number) => {
    const id = `toast_${++toastId}`;
    toastList = [...toastList, { id, type: 'info', message, duration }];
    emitChange();
    return id;
  },
};

export default Toast;

