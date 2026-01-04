/**
 * 文件上传组件
 */

import { useRef } from 'react'
import { X, Upload, Image as ImageIcon } from 'lucide-react'
import { useFileUpload } from '@hooks/useFileUpload'

interface FileUploadProps {
  onClose: () => void
}

export default function FileUpload({ onClose }: FileUploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { uploadState, selectFile, uploadFile, isUploading } = useFileUpload()

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      selectFile(file)
    }
  }

  const handleUpload = () => {
    uploadFile()
    // 上传成功后关闭
    setTimeout(() => {
      if (uploadState.status === 'success') {
        onClose()
      }
    }, 1000)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-[500px] shadow-xl">
        {/* 标题栏 */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">上传图片</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        {/* 上传区域 */}
        <div
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-primary transition-colors"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="hidden"
          />

          {uploadState.preview ? (
            <div className="space-y-3">
              <img
                src={uploadState.preview}
                alt="Preview"
                className="max-h-48 mx-auto rounded-lg"
              />
              <p className="text-sm text-gray-600">{uploadState.file?.name}</p>
            </div>
          ) : (
            <>
              <Upload size={48} className="mx-auto text-gray-400 mb-3" />
              <p className="text-gray-600 mb-2">点击或拖拽上传图片</p>
              <p className="text-xs text-gray-400">支持 JPG、PNG、WEBP 格式，最大 10MB</p>
            </>
          )}
        </div>

        {/* 错误提示 */}
        {uploadState.status === 'error' && uploadState.errorMessage && (
          <div className="mt-3 p-3 bg-red-50 text-red-600 rounded-lg text-sm">
            {uploadState.errorMessage}
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex gap-3 mt-4">
          <button
            onClick={handleUpload}
            disabled={!uploadState.file || isUploading}
            className="flex-1 px-4 py-3 bg-primary text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isUploading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                上传中...
              </>
            ) : (
              <>
                <ImageIcon size={18} />
                开始识别
              </>
            )}
          </button>

          <button
            onClick={onClose}
            className="px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  )
}

