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
    // 处理 FormData：删除默认 Content-Type，让浏览器自动设置 multipart/form-data
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    } else if (config.data && typeof config.data === 'object') {
      // 非 FormData 的对象数据，转换 key 为 snake_case
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
  async recognizeImage(file: File, templateId?: string, clientId?: string): Promise<ApiResponse<RecognitionResult>> {
    const formData = new FormData()
    formData.append('file', file)
    if (templateId) {
      formData.append('template_id', templateId)
    }
    if (clientId) {
      formData.append('client_id', clientId)
    }

    const { data } = await apiClient.post<ApiResponse<RecognitionResult>>(
      '/workflow/visual',
      formData,
      {
        headers: {
          // 不手动设置 Content-Type，让浏览器自动处理 boundary
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
    context?: Record<string, any>,
    clientId?: string
  ): Promise<ApiResponse<any>> {
    const formData = new FormData()
    formData.append('file', audioBlob, 'audio.wav')
    if (context) {
      formData.append('context', JSON.stringify(keysToSnake(context)))
    }
    if (clientId) {
      formData.append('client_id', clientId)
    }

    const { data } = await apiClient.post<ApiResponse<any>>('/workflow/audio', formData, {
      headers: {
        // 让浏览器自动处理
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

  /**
   * 上传文档并提取数据（支持 Excel/Word/PPT/PDF/图片）
   */
  async extractDocument(file: File, templateId?: string, clientId?: string): Promise<ApiResponse<DocumentExtractResult>> {
    const formData = new FormData()
    formData.append('file', file)
    if (templateId) {
      formData.append('template_id', templateId)
    }
    if (clientId) {
      formData.append('client_id', clientId)
    }

    const { data } = await apiClient.post<ApiResponse<DocumentExtractResult>>(
      '/document/extract',
      formData,
      {
        headers: {
          // 让浏览器自动处理
        },
        timeout: 180000, // 文档处理+校准可能较慢，超时3分钟
      }
    )
    return data
  },

  /**
   * 获取支持的文档类型
   */
  async getSupportedDocumentTypes(): Promise<SupportedTypesResult> {
    const { data } = await apiClient.get<SupportedTypesResult>('/document/supported-types')
    return data
  },
}

// 文档提取结果类型
export interface DocumentExtractResult {
  success: boolean
  fileType: string
  rows: any[][]
  rowCount: number
  message: string
  ambiguousItems?: any[]
  rawColumns?: string[]
  pageCount?: number
}

// 支持的文档类型
export interface SupportedTypesResult {
  supportedTypes: Record<string, string[]>
  allExtensions: string[]
}

export default apiClient
