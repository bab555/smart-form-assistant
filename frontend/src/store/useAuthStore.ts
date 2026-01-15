/**
 * 认证状态管理
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  userType: 'purchaser' | 'supplier';
  userId: string;
  genusId: string;
  name: string;
}

interface AuthState {
  isLoggedIn: boolean;
  isLoading: boolean;
  user: User | null;
  token: string | null;
  
  // Actions
  login: (username: string, password: string, remember: boolean) => Promise<boolean>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<boolean>;
  setLoading: (loading: boolean) => void;
}

const API_BASE = '/api';

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      isLoggedIn: false,
      isLoading: false,
      user: null,
      token: null,
      
      setLoading: (loading: boolean) => set({ isLoading: loading }),
      
      login: async (username: string, password: string, remember: boolean) => {
        set({ isLoading: true });
        
        try {
          const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, remember }),
          });
          
          const result = await response.json();
          
          if (result.success && result.data) {
            set({
              isLoggedIn: true,
              user: {
                userType: result.data.userType,
                userId: result.data.userId,
                genusId: result.data.genusId,
                name: result.data.name,
              },
              token: result.data.token,
              isLoading: false,
            });
            return true;
          } else {
            set({ isLoading: false });
            return false;
          }
        } catch (error) {
          console.error('Login error:', error);
          set({ isLoading: false });
          return false;
        }
      },
      
      logout: async () => {
        const { token } = get();
        
        try {
          await fetch(`${API_BASE}/auth/logout`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });
        } catch (error) {
          console.error('Logout error:', error);
        }
        
        set({
          isLoggedIn: false,
          user: null,
          token: null,
        });
      },
      
      checkAuth: async () => {
        const { token } = get();
        
        if (!token) {
          return false;
        }
        
        try {
          const response = await fetch(`${API_BASE}/auth/check`, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });
          
          const result = await response.json();
          
          if (result.success && result.data) {
            set({
              isLoggedIn: true,
              user: {
                userType: result.data.userType,
                userId: result.data.userId,
                genusId: result.data.genusId,
                name: result.data.name,
              },
            });
            return true;
          } else {
            set({
              isLoggedIn: false,
              user: null,
              token: null,
            });
            return false;
          }
        } catch (error) {
          console.error('Check auth error:', error);
          return false;
        }
      },
    }),
    {
      name: 'auth-storage', // localStorage key
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isLoggedIn: state.isLoggedIn,
      }),
    }
  )
);

