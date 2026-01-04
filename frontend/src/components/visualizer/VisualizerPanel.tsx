/**
 * 可视化面板组件 - 中栏
 */

import { useFormStore } from '@hooks/useFormStore'
import { useAgent } from '@hooks/useAgent'
import CoreOrb from './CoreOrb'
import ProcessGraph from './ProcessGraph'

export default function VisualizerPanel() {
  const { currentStep, isThinking } = useFormStore()
  const { isConnected, logs } = useAgent()

  return (
    <div className="h-full flex flex-col">
      {/* 标题栏 */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-800">思维可视化</h2>
            <p className="text-xs text-gray-500 mt-1">AI 工作流程实时展示</p>
          </div>
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success' : 'bg-gray-300'}`}
            />
            <span className="text-xs text-gray-500">
              {isConnected ? '已连接' : '未连接'}
            </span>
          </div>
        </div>
      </div>

      {/* 可视化内容 */}
      <div className="flex-1 overflow-hidden relative">
        {currentStep === 'idle' && !isThinking ? (
          <CoreOrb />
        ) : (
          <ProcessGraph currentStep={currentStep} logs={logs} />
        )}
      </div>

      {/* 状态栏 */}
      <div className="px-4 py-2 border-t border-gray-200 bg-gray-50">
        <p className="text-xs text-gray-600">
          当前状态: <span className="font-medium">{getStepLabel(currentStep)}</span>
        </p>
      </div>
    </div>
  )
}

function getStepLabel(step: string): string {
  const labels: Record<string, string> = {
    idle: '待机',
    ocr: '图像识别中',
    calibrating: '数据校准中',
    filling: '填充数据中',
    waiting_user: '等待用户确认',
    error: '错误',
  }
  return labels[step] || step
}

