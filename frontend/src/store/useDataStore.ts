/**
 * 动态数据状态管理
 * 
 * 管理：
 * - 合作方列表（配送商/学校）
 * - 餐厅列表
 * - 订单类型
 * - 商品库同步状态
 */

import { create } from 'zustand';
import { useAuthStore } from './useAuthStore';
import { toast } from '../components/Toast';

interface Partner {
  id: string;
  name: string;
}

interface Restaurant {
  id: string;
  name: string;
}

interface OrderType {
  id: string;
  name: string;
}

interface DataState {
  // 合作方（学校看配送商，配送商看学校）
  partners: Partner[];
  selectedPartnerId: string | null;
  
  // 餐厅
  restaurants: Restaurant[];
  
  // 订单类型
  orderTypes: OrderType[];
  
  // 同步状态
  isSyncing: boolean;
  syncMessage: string;
  syncProgress: number; // 0-100
  
  // 商品库
  productNames: string[];
  
  // Actions
  loadPartners: () => Promise<void>;
  loadRestaurants: (partnerId?: string) => Promise<void>;
  loadOrderTypes: (partnerId?: string) => Promise<void>;
  syncProducts: (partnerId: string) => Promise<boolean>;
  setSelectedPartner: (partnerId: string | null) => void;
  setSyncStatus: (syncing: boolean, message?: string, progress?: number) => void;
  reset: () => void;
}

const API_BASE = '/api';

const getAuthHeader = (): Record<string, string> => {
  const token = useAuthStore.getState().token;
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

export const useDataStore = create<DataState>((set) => ({
  partners: [],
  selectedPartnerId: null,
  restaurants: [],
  orderTypes: [],
  isSyncing: false,
  syncMessage: '',
  syncProgress: 0,
  productNames: [],
  
  loadPartners: async () => {
    let attempts = 0;
    const maxAttempts = 3;
    
    while (attempts < maxAttempts) {
      try {
        const response = await fetch(`${API_BASE}/data/partners`, {
          headers: getAuthHeader(),
        });
        const result = await response.json();
        
        if (result.success) {
          set({ partners: result.data || [] });
          return; // 成功获取，直接返回
        }
        // 如果 API 返回明确的失败，也视为一次尝试失败，继续重试
        console.warn(`[LoadPartners] Attempt ${attempts + 1} failed:`, result.message);
      } catch (error) {
        console.error(`[LoadPartners] Attempt ${attempts + 1} error:`, error);
      }
      
      attempts++;
      if (attempts < maxAttempts) {
        // 等待后重试 (1s, 2s)
        await new Promise(resolve => setTimeout(resolve, 1000 * attempts));
      }
    }
    
    // 3次尝试后仍失败，弹出提示
    toast.error('获取客户列表失败 (3次重试无效)，请刷新页面或检查网络', 5000);
  },
  
  loadRestaurants: async (partnerId?: string) => {
    try {
      const url = partnerId 
        ? `${API_BASE}/data/restaurants?partnerId=${partnerId}`
        : `${API_BASE}/data/restaurants`;
        
      const response = await fetch(url, {
        headers: getAuthHeader(),
      });
      const result = await response.json();
      
      if (result.success) {
        set({ restaurants: result.data || [] });
      }
    } catch (error) {
      console.error('Load restaurants error:', error);
    }
  },
  
  loadOrderTypes: async (partnerId?: string) => {
    try {
      const url = partnerId 
        ? `${API_BASE}/data/order_types?partnerId=${partnerId}`
        : `${API_BASE}/data/order_types`;

      const response = await fetch(url, {
        headers: getAuthHeader(),
      });
      const result = await response.json();
      
      if (result.success) {
        set({ orderTypes: result.data || [] });
      }
    } catch (error) {
      console.error('Load order types error:', error);
    }
  },
  
  syncProducts: async (partnerId: string) => {
    set({ 
      isSyncing: true, 
      syncMessage: '正在同步商品库...', 
      syncProgress: 10 
    });
    
    try {
      // 模拟进度
      const progressInterval = setInterval(() => {
        set((state) => ({
          syncProgress: Math.min(state.syncProgress + 10, 90)
        }));
      }, 500);
      
      const response = await fetch(`${API_BASE}/data/sync_products`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify({ partnerId }),
      });
      
      clearInterval(progressInterval);
      
      const result = await response.json();
      
      if (result.success) {
        set({ 
          isSyncing: false, 
          syncMessage: `同步完成，共 ${result.count} 个商品`,
          syncProgress: 100 
        });
        
        // 延迟清除消息
        setTimeout(() => {
          set({ syncMessage: '', syncProgress: 0 });
        }, 2000);
        
        return true;
      } else {
        set({ 
          isSyncing: false, 
          syncMessage: result.message || '同步失败',
          syncProgress: 0 
        });
        return false;
      }
    } catch (error) {
      console.error('Sync products error:', error);
      // 增加错误反馈
      toast.error('因为网络波动问题，调用失败，请重试');
      
      set({ 
        isSyncing: false, 
        syncMessage: '网络错误，同步失败',
        syncProgress: 0 
      });
      return false;
    }
  },
  
  setSelectedPartner: (partnerId: string | null) => {
    set({ selectedPartnerId: partnerId });
  },
  
  setSyncStatus: (syncing: boolean, message = '', progress = 0) => {
    set({ isSyncing: syncing, syncMessage: message, syncProgress: progress });
  },
  
  reset: () => {
    set({
      partners: [],
      selectedPartnerId: null,
      restaurants: [],
      orderTypes: [],
      isSyncing: false,
      syncMessage: '',
      syncProgress: 0,
      productNames: [],
    });
  },
}));

