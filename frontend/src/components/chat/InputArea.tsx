/**
 * 输入区域组件 - 语音/图片/文字输入
 * 
 * 语音输入改为：点击按钮直接开始录音，再次点击停止并发送
 */

import { useState, useEffect } from 'react'
import { Mic, Upload, Send, Square, Loader2 } from 'lucide-react'
import FileUpload from './FileUpload'
import { useVoiceRecorder } from '@hooks/useVoiceRecorder'
import { useMutation } from '@tanstack/react-query'
import { api } from '@services/api'
import { wsClient } from '@services/websocket'
import { useFormStore } from '@hooks/useFormStore'

interface InputAreaProps {
  onSendMessage: (content: string, metadata?: any) => void
}

export default function InputArea({ onSendMessage }: InputAreaProps) {
  const [textInput, setTextInput] = useState('')
  const [showUploadModal, setShowUploadModal] = useState(false)
  
  // 语音录制
  const { recordingState, startRecording, stopRecording, cancelRecording, reset } = useVoiceRecorder()
  const { rows } = useFormStore()
  const isRecording = recordingState.isRecording
  
  // 录音时长显示
  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  // 语音识别 Mutation
  const recognizeMutation = useMutation({
    mutationFn: (audioBlob: Blob) => {
      const context = { rows }
      return api.recognizeAudio(audioBlob, context, wsClient.clientId)
    },
    onSuccess: (response) => {
      console.log('语音识别成功:', response)
      reset()
    },
    onError: (error) => {
      console.error('语音识别失败:', error)
      reset()
    },
  })

  // 处理语音按钮点击
  const handleVoiceClick = async () => {
    if (isRecording) {
      // 停止录音并发送
      const blob = await stopRecording()
      if (blob) {
        recognizeMutation.mutate(blob)
      }
    } else {
      // 开始录音
      startRecording()
    }
  }

  // 取消录音（可以通过 Esc 键）
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isRecording) {
        cancelRecording()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isRecording, cancelRecording])

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

  const isPending = recognizeMutation.isPending

  return (
    <>
      <div className="p-3 space-y-2">
        {/* 工具按钮 */}
        <div className="flex gap-2 items-center">
          {/* 语音按钮 - 点击切换录音状态 */}
          <button
            onClick={handleVoiceClick}
            disabled={isPending}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200 ${
              isRecording
                ? 'bg-danger text-white animate-pulse hover:bg-red-600'
                : isPending
                ? 'bg-gray-400 text-white cursor-not-allowed'
                : 'bg-primary text-white hover:bg-blue-600'
            }`}
          >
            {isPending ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                <span className="text-sm font-medium">识别中...</span>
              </>
            ) : isRecording ? (
              <>
                <Square size={18} fill="white" />
                <span className="text-sm font-medium">{formatDuration(recordingState.duration)}</span>
                <span className="text-xs opacity-75">点击停止</span>
              </>
            ) : (
              <>
                <Mic size={18} />
                <span className="text-sm font-medium">语音输入</span>
              </>
            )}
          </button>

          {/* 录音提示 */}
          {isRecording && (
            <span className="text-xs text-gray-500 animate-pulse">
              按 ESC 取消
            </span>
          )}

          <button
            onClick={() => setShowUploadModal(true)}
            disabled={isRecording || isPending}
            className="flex items-center gap-2 px-4 py-2 bg-success text-white rounded-lg hover:bg-green-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Upload size={18} />
            <span className="text-sm font-medium">上传文件</span>
          </button>
        </div>

        {/* 文字输入框 */}
        <div className="flex gap-2">
          <input
            type="text"
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={isRecording ? "正在录音..." : "输入文字消息..."}
            disabled={isRecording || isPending}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
          <button
            onClick={handleSendText}
            disabled={!textInput.trim() || isRecording || isPending}
            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={18} />
          </button>
        </div>
      </div>

      {/* 文件上传模态框 */}
      {showUploadModal && <FileUpload onClose={() => setShowUploadModal(false)} />}
    </>
  )
}
