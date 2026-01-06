/**
 * 文件上传 Hook - 支持图片和文档
 */

import { useState, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@services/api'
import { wsClient } from '@services/websocket'
import type { UploadState } from '@types'
import { useFormStore } from './useFormStore'

// 支持的文件类型
const SUPPORTED_TYPES = {
  image: ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp'],
  excel: ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel', 'text/csv'],
  word: ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword'],
  ppt: ['application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/vnd.ms-powerpoint'],
  pdf: ['application/pdf'],
}

// 所有支持的 MIME 类型
// const ALL_SUPPORTED_TYPES = Object.values(SUPPORTED_TYPES).flat()

// 最大文件大小 20MB
const MAX_FILE_SIZE = 20 * 1024 * 1024

// 判断文件类型
function getFileCategory(file: File): 'image' | 'document' | 'unknown' {
  const type = file.type
  const name = file.name.toLowerCase()
  
  if (SUPPORTED_TYPES.image.includes(type)) {
    return 'image'
  }
  
  // Excel, Word, PPT, PDF 都归类为 document
  if (
    SUPPORTED_TYPES.excel.includes(type) ||
    SUPPORTED_TYPES.word.includes(type) ||
    SUPPORTED_TYPES.ppt.includes(type) ||
    SUPPORTED_TYPES.pdf.includes(type) ||
    name.endsWith('.csv') ||
    name.endsWith('.xlsx') ||
    name.endsWith('.xls') ||
    name.endsWith('.docx') ||
    name.endsWith('.doc') ||
    name.endsWith('.pptx') ||
    name.endsWith('.ppt') ||
    name.endsWith('.pdf')
  ) {
    return 'document'
  }
  
  return 'unknown'
}

// 格式化文件大小
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(2) + ' MB'
}

export function useFileUpload() {
  const [uploadState, setUploadState] = useState<UploadState>({
    file: null,
    preview: null,
    status: 'idle',
    progress: 0,
  })

  const { addRow, setCurrentStep, setThinking } = useFormStore()

  // 图片识别 Mutation
  const imageMutation = useMutation({
    mutationFn: (file: File) => api.recognizeImage(file, undefined, wsClient.clientId),
    onMutate: () => {
      setUploadState((prev) => ({ ...prev, status: 'uploading', progress: 0 }))
      setCurrentStep('ocr')
      setThinking(true)
    },
    onSuccess: (response) => {
      handleUploadSuccess(response)
    },
    onError: (error: any) => {
      handleUploadError(error)
    },
  })

  // 文档提取 Mutation
  const documentMutation = useMutation({
    mutationFn: (file: File) => api.extractDocument(file, undefined, wsClient.clientId),
    onMutate: () => {
      setUploadState((prev) => ({ ...prev, status: 'uploading', progress: 0 }))
      setCurrentStep('ocr')
      setThinking(true)
    },
    onSuccess: (response) => {
      handleUploadSuccess(response)
    },
    onError: (error: any) => {
      handleUploadError(error)
    },
  })

  // 处理上传成功
  const handleUploadSuccess = useCallback((response: any) => {
    if (response.code === 200 && response.data?.rows) {
      // 将识别结果添加到表格
      response.data.rows.forEach((row: any) => {
        addRow(row)
      })

      setUploadState((prev) => ({
        ...prev,
        status: 'success',
        progress: 100,
      }))
      
      console.log(`✅ 文件处理成功: ${response.data.rowCount} 行数据`)
    } else {
      setUploadState((prev) => ({
        ...prev,
        status: 'error',
        errorMessage: response.message || '处理失败',
      }))
    }
    setThinking(false)
    setCurrentStep('idle')
  }, [addRow, setCurrentStep, setThinking])

  // 处理上传错误
  const handleUploadError = useCallback((error: any) => {
    setUploadState((prev) => ({
      ...prev,
      status: 'error',
      errorMessage: error.message || '上传失败',
    }))
    setThinking(false)
    setCurrentStep('error')
  }, [setCurrentStep, setThinking])

  /**
   * 验证文件
   */
  const validateFile = useCallback((file: File): string | null => {
    const category = getFileCategory(file)
    
    // 检查文件类型
    if (category === 'unknown') {
      return '不支持的文件类型。支持：图片 (JPG/PNG)、Excel、Word、PPT、PDF'
    }

    // 检查文件大小
    if (file.size > MAX_FILE_SIZE) {
      return `文件大小超过限制。最大支持 ${formatFileSize(MAX_FILE_SIZE)}`
    }

    return null
  }, [])

  /**
   * 选择文件
   */
  const selectFile = useCallback(
    (file: File) => {
      // 验证文件
      const error = validateFile(file)
      if (error) {
        setUploadState({
          file: null,
          preview: null,
          status: 'error',
          progress: 0,
          errorMessage: error,
        })
        return false
      }

      // 只有图片才生成预览
      const category = getFileCategory(file)
      const previewUrl = category === 'image' ? URL.createObjectURL(file) : null

      setUploadState({
        file,
        preview: previewUrl,
        status: 'idle',
        progress: 0,
      })

      return true
    },
    [validateFile]
  )

  /**
   * 上传文件
   */
  const uploadFile = useCallback(
    async (file?: File) => {
      const targetFile = file || uploadState.file

      if (!targetFile) {
        console.warn('没有选择文件')
        return
      }

      // 如果传入了新文件，先选择它
      if (file) {
        const isValid = selectFile(file)
        if (!isValid) return
      }

      // 根据文件类型选择不同的上传 API
      const category = getFileCategory(targetFile)
      
      console.log(`📤 开始上传: ${targetFile.name} (类型: ${category})`)
      
      if (category === 'image') {
        imageMutation.mutate(targetFile)
      } else if (category === 'document') {
        documentMutation.mutate(targetFile)
      } else {
        setUploadState((prev) => ({
          ...prev,
          status: 'error',
          errorMessage: '不支持的文件类型',
        }))
      }
    },
    [uploadState.file, selectFile, imageMutation, documentMutation]
  )

  /**
   * 重置状态
   */
  const reset = useCallback(() => {
    // 释放预览 URL
    if (uploadState.preview) {
      URL.revokeObjectURL(uploadState.preview)
    }

    setUploadState({
      file: null,
      preview: null,
      status: 'idle',
      progress: 0,
      })
  }, [uploadState.preview])

  return {
    uploadState,
    selectFile,
    uploadFile,
    reset,
    isUploading: imageMutation.isPending || documentMutation.isPending,
  }
}
