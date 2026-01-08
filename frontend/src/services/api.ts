/**
 * API 服务封装
 * 
 * 统一的 HTTP 请求封装
 */

import { wsClient } from './websocket';

// 基础配置
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

interface RequestOptions extends RequestInit {
  timeout?: number;
}

// ========== 基础请求方法 ==========

async function request<T>(
  url: string,
  options: RequestOptions = {}
): Promise<T> {
  const { timeout = 30000, ...fetchOptions } = options;
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(`${API_BASE}${url}`, {
      ...fetchOptions,
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || error.message || `HTTP ${response.status}`);
    }
    
    return response.json();
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('请求超时');
    }
    throw error;
  }
}

// ========== Task API ==========

export interface SubmitTaskParams {
  file: File;
  taskType?: 'extract' | 'audio' | 'chat';
  tableId?: string;
}

export interface SubmitTaskResponse {
  task_id: string;
  table_id: string;
  status: string;
}

/**
 * 提交任务
 */
export async function submitTask(params: SubmitTaskParams): Promise<SubmitTaskResponse> {
  const formData = new FormData();
  formData.append('file', params.file);
  formData.append('task_type', params.taskType || 'extract');
  formData.append('client_id', wsClient.clientId);
  
  if (params.tableId) {
    formData.append('table_id', params.tableId);
  }
  
  return request<SubmitTaskResponse>('/task/submit', {
    method: 'POST',
    body: formData,
    timeout: 60000, // 文件上传用更长超时
  });
}

// ========== Skills API ==========

export interface Skill {
  id: string;
  name: string;
  category: string;
  description?: string;
  schema: Array<{
    key: string;
    title: string;
    type?: string;
  }>;
}

export interface ImportSkillParams {
  file: File;
  name?: string;
  category?: string;
  description?: string;
}

export interface ImportSkillResponse {
  skill_id: string;
  name: string;
  category: string;
  schema: Skill['schema'];
  row_count: number;
}

/**
 * 获取 Skills 列表
 */
export async function getSkills(category?: string): Promise<{ skills: Skill[] }> {
  const url = category ? `/skills/list?category=${category}` : '/skills/list';
  return request<{ skills: Skill[] }>(url);
}

/**
 * 获取单个 Skill
 */
export async function getSkill(skillId: string): Promise<Skill> {
  return request<Skill>(`/skills/${skillId}`);
}

/**
 * 导入 Skill
 */
export async function importSkill(params: ImportSkillParams): Promise<ImportSkillResponse> {
  const formData = new FormData();
  formData.append('file', params.file);
  
  if (params.name) formData.append('name', params.name);
  if (params.category) formData.append('category', params.category);
  if (params.description) formData.append('description', params.description);
  
  return request<ImportSkillResponse>('/skills/import', {
    method: 'POST',
    body: formData,
  });
}

/**
 * 删除 Skill
 */
export async function deleteSkill(skillId: string): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(`/skills/${skillId}`, {
    method: 'DELETE',
  });
}

// ========== Health API ==========

export interface HealthResponse {
  status: string;
  service: string;
  connections: number;
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<HealthResponse> {
  return request<HealthResponse>('/health');
}

// ========== 导出 ==========

export const api = {
  submitTask,
  getSkills,
  getSkill,
  importSkill,
  deleteSkill,
  healthCheck,
};

export default api;
