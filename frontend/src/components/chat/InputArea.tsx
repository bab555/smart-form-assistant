/**
 * 输入区域组件 - 语音/图片/文字输入
 */

import { useState } from 'react'
import { Mic, Upload, Send } from 'lucide-react'
import VoiceInput from './VoiceInput'
import FileUpload from './FileUpload'

interface InputAreaProps {
  onSendMessage: (content: string, metadata?: any) => void
}

export default function InputArea({ onSendMessage }: InputAreaProps) {
  const [textInput, setTextInput] = useState('')
  const [showVoiceModal, setShowVoiceModal] = useState(false)
  const [showUploadModal, setShowUploadModal] = useState(false)

  const handleSendText = () => {
    if (textInput.trim()) {
      onSendMessage(textInput.trim())
      setTextInput('')
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendText()
    }
  }

  return (
    <>
      <div className="p-3 space-y-2">
        {/* 工具按钮 */}
        <div className="flex gap-2">
          <button
            onClick={() => setShowVoiceModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            <Mic size={18} />
            <span className="text-sm font-medium">语音输入</span>
          </button>

          <button
            onClick={() => setShowUploadModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-success text-white rounded-lg hover:bg-green-600 transition-colors"
          >
            <Upload size={18} />
            <span className="text-sm font-medium">上传图片</span>
          </button>
        </div>

        {/* 文字输入框 */}
        <div className="flex gap-2">
          <input
            type="text"
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入文字消息..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <button
            onClick={handleSendText}
            disabled={!textInput.trim()}
            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={18} />
          </button>
        </div>
      </div>

      {/* 语音输入模态框 */}
      {showVoiceModal && <VoiceInput onClose={() => setShowVoiceModal(false)} />}

      {/* 文件上传模态框 */}
      {showUploadModal && <FileUpload onClose={() => setShowUploadModal(false)} />}
    </>
  )
}

