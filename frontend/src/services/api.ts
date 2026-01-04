/**
 * API 服务层
 * 封装所有后端 API 请求
 */

import axios, { AxiosInstance, AxiosError } from 'axios'
import type { ApiResponse, RecognitionResult } from '@types'
import { keysToCamel, keysToSnake } from './transformers'

// 创建 Axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器：将 camelCase 转换为 snake_case
apiClient.interceptors.request.use(
  (config) => {
    if (config.data && typeof config.data === 'object') {
      config.data = keysToSnake(config.data)
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：将 snake_case 转换为 camelCase
apiClient.interceptors.response.use(
  (response) => {
    if (response.data) {
      response.data = keysToCamel(response.data)
    }
    return response
  },
  (error: AxiosError<ApiResponse>) => {
    // 统一错误处理
    if (error.response?.data) {
      const errorData = keysToCamel(error.response.data)
      console.error('API Error:', errorData)
      return Promise.reject(errorData)
    }
    return Promise.reject(error)
  }
)

/**
 * API 方法集合
 */
export const api = {
  /**
   * 上传图片并识别
   */
  async recognizeImage(file: File, templateId?: string): Promise<ApiResponse<RecognitionResult>> {
    const formData = new FormData()
    formData.append('file', file)
    if (templateId) {
      formData.append('template_id', templateId)
    }

    const { data } = await apiClient.post<ApiResponse<RecognitionResult>>(
      '/workflow/visual',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )
    return data
  },

  /**
   * 上传音频并处理
   */
  async recognizeAudio(
    audioBlob: Blob,
    context?: Record<string, any>
  ): Promise<ApiResponse<any>> {
    const formData = new FormData()
    formData.append('file', audioBlob, 'audio.wav')
    if (context) {
      formData.append('context', JSON.stringify(keysToSnake(context)))
    }

    const { data } = await apiClient.post<ApiResponse<any>>('/workflow/audio', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return data
  },

  /**
   * 获取表单模板列表
   */
  async getTemplates(): Promise<ApiResponse<any[]>> {
    const { data } = await apiClient.get<ApiResponse<any[]>>('/template/list')
    return data
  },

  /**
   * 获取单个模板详情
   */
  async getTemplate(templateId: string): Promise<ApiResponse<any>> {
    const { data } = await apiClient.get<ApiResponse<any>>(`/template/${templateId}`)
    return data
  },

  /**
   * 提交表单数据
   */
  async submitForm(formData: any): Promise<ApiResponse<any>> {
    const { data } = await apiClient.post<ApiResponse<any>>('/form/submit', formData)
    return data
  },
}

export default apiClient

