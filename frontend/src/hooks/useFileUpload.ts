/**
 * 文件上传 Hook
 */

import { useState, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@services/api'
import type { UploadState } from '@types'
import { UPLOAD_CONFIG } from '@utils/constants'
import { isValidImageFile, formatFileSize } from '@utils/helpers'
import { useFormStore } from './useFormStore'

export function useFileUpload() {
  const [uploadState, setUploadState] = useState<UploadState>({
    file: null,
    preview: null,
    status: 'idle',
    progress: 0,
  })

  const { addRow, setCurrentStep, setThinking } = useFormStore()

  // 文件上传 Mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.recognizeImage(file),
    onMutate: () => {
      setUploadState((prev: any) => ({ ...prev, status: 'uploading', progress: 0 }))
      setCurrentStep('ocr')
      setThinking(true)
    },
    onSuccess: (response) => {
      if (response.code === 200 && response.data?.rows) {
        // 将识别结果添加到表格
        response.data.rows.forEach((row: any) => {
          addRow(row)
        })

        setUploadState((prev: any) => ({
          ...prev,
          status: 'success',
          progress: 100,
        }))
      }
      setThinking(false)
      setCurrentStep('idle')
    },
    onError: (error: any) => {
      setUploadState((prev: any) => ({
        ...prev,
        status: 'error',
        errorMessage: error.message || '上传失败',
      }))
      setThinking(false)
      setCurrentStep('error')
    },
  })

  /**
   * 验证文件
   */
  const validateFile = useCallback((file: File): string | null => {
    // 检查文件类型
    if (!isValidImageFile(file)) {
      return `不支持的文件类型。请上传 ${UPLOAD_CONFIG.allowedExtensions.join(', ')} 格式的图片。`
    }

    // 检查文件大小
    if (file.size > UPLOAD_CONFIG.maxSize) {
      return `文件大小超过限制。最大支持 ${formatFileSize(UPLOAD_CONFIG.maxSize)}。`
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

      // 生成预览
      const previewUrl = URL.createObjectURL(file)

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

      // 执行上传
      uploadMutation.mutate(targetFile)
    },
    [uploadState.file, selectFile, uploadMutation]
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
    isUploading: uploadMutation.isPending,
  }
}

