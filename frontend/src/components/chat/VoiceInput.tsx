/**
 * 语音输入组件
 */

import { X, Mic, Square } from 'lucide-react'
import { useVoiceRecorder } from '@hooks/useVoiceRecorder'
import { useMutation } from '@tanstack/react-query'
import { api } from '@services/api'
import { wsClient } from '@services/websocket'
import { useFormStore } from '@hooks/useFormStore'

interface VoiceInputProps {
  onClose: () => void
}

export default function VoiceInput({ onClose }: VoiceInputProps) {
  const { recordingState, startRecording, stopRecording, cancelRecording } = useVoiceRecorder()
  const { rows } = useFormStore()

  // 语音识别 Mutation
  const recognizeMutation = useMutation({
    mutationFn: (audioBlob: Blob) => {
      // 传入当前表格数据作为上下文，以及 clientId
      const context = { rows }
      return api.recognizeAudio(audioBlob, context, wsClient.clientId)
    },
    onSuccess: (response) => {
      console.log('语音识别成功:', response)
      // 注意：后端会通过 WebSocket 推送 tool_action 和 agent_thought
      // 前端的 useAgent Hook 和 ChatPanel 会监听这些消息并更新 UI
      // 这里不需要额外操作
      onClose()
    },
    onError: (error) => {
      console.error('语音识别失败:', error)
    },
  })

  // 处理停止录音
  const handleStop = async () => {
    const blob = await stopRecording()
    if (blob) {
      recognizeMutation.mutate(blob)
    }
  }

  // 处理取消
  const handleCancel = () => {
    cancelRecording()
    onClose()
  }

  // 格式化时长
  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-96 shadow-xl">
        {/* 标题栏 */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">语音输入</h3>
          <button onClick={handleCancel} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        {/* 录音状态显示 */}
        <div className="flex flex-col items-center py-8">
          <div
            className={`w-24 h-24 rounded-full flex items-center justify-center mb-4 ${
              recordingState.isRecording ? 'bg-danger animate-pulse' : 'bg-primary'
            }`}
          >
            <Mic size={40} className="text-white" />
          </div>

          <p className="text-2xl font-mono mb-2">{formatDuration(recordingState.duration)}</p>

          <p className="text-sm text-gray-500">
            {recordingState.isRecording ? '正在录音...' : '准备录音'}
          </p>
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-3">
          {!recordingState.isRecording ? (
            <button
              onClick={startRecording}
              className="flex-1 px-4 py-3 bg-primary text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              开始录音
            </button>
          ) : (
            <button
              onClick={handleStop}
              className="flex-1 px-4 py-3 bg-danger text-white rounded-lg hover:bg-red-600 transition-colors flex items-center justify-center gap-2"
            >
              <Square size={18} fill="white" />
              停止录音
            </button>
          )}

          <button
            onClick={handleCancel}
            className="px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            取消
          </button>
        </div>

        {/* 加载状态 */}
        {recognizeMutation.isPending && (
          <div className="mt-4 text-center text-sm text-gray-500">正在识别中...</div>
        )}
      </div>
    </div>
  )
}
