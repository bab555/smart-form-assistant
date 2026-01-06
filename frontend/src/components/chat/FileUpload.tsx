/**
 * 文件上传组件 - 支持图片/Excel/Word/PPT/PDF
 */

import { useRef, useMemo } from 'react'
import { X, Upload, Image as ImageIcon, FileSpreadsheet, FileText, Presentation, File } from 'lucide-react'
import { useFileUpload } from '@hooks/useFileUpload'

interface FileUploadProps {
  onClose: () => void
}

// 支持的文件类型
const ACCEPTED_TYPES = {
  image: ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp'],
  excel: ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel', 'text/csv'],
  word: ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword'],
  ppt: ['application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/vnd.ms-powerpoint'],
  pdf: ['application/pdf'],
}

// 所有支持的 MIME 类型
// const ALL_ACCEPTED = Object.values(ACCEPTED_TYPES).flat().join(',')

// 文件扩展名
const ACCEPTED_EXTENSIONS = '.jpg,.jpeg,.png,.gif,.webp,.bmp,.xlsx,.xls,.csv,.docx,.doc,.pptx,.ppt,.pdf'

// 根据文件类型获取图标
function getFileIcon(file: File | null) {
  if (!file) return <Upload size={48} className="mx-auto text-gray-400 mb-3" />
  
  const type = file.type
  
  if (ACCEPTED_TYPES.image.includes(type)) {
    return <ImageIcon size={48} className="mx-auto text-blue-500 mb-3" />
  }
  if (ACCEPTED_TYPES.excel.includes(type) || file.name.endsWith('.csv')) {
    return <FileSpreadsheet size={48} className="mx-auto text-green-600 mb-3" />
  }
  if (ACCEPTED_TYPES.word.includes(type)) {
    return <FileText size={48} className="mx-auto text-blue-600 mb-3" />
  }
  if (ACCEPTED_TYPES.ppt.includes(type)) {
    return <Presentation size={48} className="mx-auto text-orange-500 mb-3" />
  }
  if (ACCEPTED_TYPES.pdf.includes(type)) {
    return <File size={48} className="mx-auto text-red-500 mb-3" />
  }
  
  return <File size={48} className="mx-auto text-gray-400 mb-3" />
}

// 根据文件类型获取标签
function getFileTypeLabel(file: File | null): string {
  if (!file) return ''
  
  const type = file.type
  
  if (ACCEPTED_TYPES.image.includes(type)) return '图片'
  if (ACCEPTED_TYPES.excel.includes(type) || file.name.endsWith('.csv')) return 'Excel'
  if (ACCEPTED_TYPES.word.includes(type)) return 'Word'
  if (ACCEPTED_TYPES.ppt.includes(type)) return 'PPT'
  if (ACCEPTED_TYPES.pdf.includes(type)) return 'PDF'
  
  return '文档'
}

// 检查是否为图片类型
function isImageFile(file: File | null): boolean {
  if (!file) return false
  return ACCEPTED_TYPES.image.includes(file.type)
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
    // 立即关闭弹窗，流程进度将在可视化面板展示
    onClose()
  }

  // 处理拖拽
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    const file = e.dataTransfer.files?.[0]
    if (file) {
      selectFile(file)
    }
  }

  // 文件类型标签
  const fileTypeLabel = useMemo(() => getFileTypeLabel(uploadState.file), [uploadState.file])
  const isImage = useMemo(() => isImageFile(uploadState.file), [uploadState.file])

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-[500px] shadow-xl">
        {/* 标题栏 */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">上传文件</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        {/* 上传区域 */}
        <div
          onClick={() => fileInputRef.current?.click()}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-primary transition-colors"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_EXTENSIONS}
            onChange={handleFileChange}
            className="hidden"
          />

          {uploadState.file ? (
            <div className="space-y-3">
              {/* 图片预览或文件图标 */}
              {isImage && uploadState.preview ? (
                <img
                  src={uploadState.preview}
                  alt="Preview"
                  className="max-h-48 mx-auto rounded-lg"
                />
              ) : (
                <div className="py-4">
                  {getFileIcon(uploadState.file)}
                </div>
              )}
              
              {/* 文件信息 */}
              <div className="space-y-1">
                <p className="text-sm font-medium text-gray-800">{uploadState.file.name}</p>
                <div className="flex items-center justify-center gap-2 text-xs text-gray-500">
                  <span className={`px-2 py-0.5 rounded-full ${
                    isImage ? 'bg-blue-100 text-blue-600' :
                    fileTypeLabel === 'Excel' ? 'bg-green-100 text-green-600' :
                    fileTypeLabel === 'Word' ? 'bg-blue-100 text-blue-600' :
                    fileTypeLabel === 'PPT' ? 'bg-orange-100 text-orange-600' :
                    fileTypeLabel === 'PDF' ? 'bg-red-100 text-red-600' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {fileTypeLabel}
                  </span>
                  <span>{(uploadState.file.size / 1024 / 1024).toFixed(2)} MB</span>
                </div>
              </div>
            </div>
          ) : (
            <>
              <Upload size={48} className="mx-auto text-gray-400 mb-3" />
              <p className="text-gray-600 mb-2">点击或拖拽上传文件</p>
              <div className="space-y-1">
                <p className="text-xs text-gray-400">
                  支持格式：图片 (JPG/PNG)、Excel、Word、PPT、PDF
                </p>
                <p className="text-xs text-gray-400">
                  最大 20MB
                </p>
              </div>
            </>
          )}
        </div>

        {/* 处理说明 */}
        {uploadState.file && (
          <div className="mt-3 p-3 bg-gray-50 rounded-lg text-xs text-gray-600">
            {isImage ? (
              <span>📷 将使用 AI 视觉模型识别图片中的表格/订单数据</span>
            ) : fileTypeLabel === 'Excel' ? (
              <span>📊 将直接解析 Excel 数据，保留原始结构</span>
            ) : (
              <span>📄 将转换为图片后使用 AI 视觉模型识别</span>
            )}
          </div>
        )}

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
                处理中...
              </>
            ) : (
              <>
                {isImage ? <ImageIcon size={18} /> : <FileText size={18} />}
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
