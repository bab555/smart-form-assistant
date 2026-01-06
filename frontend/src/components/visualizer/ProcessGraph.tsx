/**
 * 流程图组件 - 使用 React Flow 显示 AI 工作流
 */

import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
} from 'reactflow'
import 'reactflow/dist/style.css'
import type { LogEntry } from '@types'
import { useEffect, useMemo, useRef } from 'react'
import { Terminal } from 'lucide-react'

interface ProcessGraphProps {
  currentStep: string // 使用 string 以兼容后端更细粒度的步骤
  logs: LogEntry[]
}

// 步骤定义与顺序
const STEPS_ORDER = ['idle', 'ocr', 'analyzing', 'extraction', 'calibration', 'calibrating', 'filling']

// 节点定义
const initialNodes: Node[] = [
  {
    id: 'ocr',
    type: 'default',
    data: { label: 'OCR 视觉识别' },
    position: { x: 250, y: 50 },
  },
  {
    id: 'analyzing',
    type: 'default',
    data: { label: '内容语义分析' },
    position: { x: 250, y: 150 },
  },
  {
    id: 'extraction',
    type: 'default',
    data: { label: '结构化数据提取' },
    position: { x: 250, y: 250 },
  },
  {
    id: 'calibration',
    type: 'default',
    data: { label: '知识库智能校准' },
    position: { x: 250, y: 350 },
  },
  {
    id: 'filling',
    type: 'default',
    data: { label: '表格自动填充' },
    position: { x: 250, y: 450 },
  },
]

// 连线定义
const initialEdges: Edge[] = [
  { id: 'e1', source: 'ocr', target: 'analyzing' },
  { id: 'e2', source: 'analyzing', target: 'extraction' },
  { id: 'e3', source: 'extraction', target: 'calibration' },
  { id: 'e4', source: 'calibration', target: 'filling' },
]

export default function ProcessGraph({ currentStep, logs }: ProcessGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const logEndRef = useRef<HTMLDivElement>(null)

  // 自动滚动日志
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  // 映射前端/后端步骤名称
  const normalizedStep = useMemo(() => {
    if (currentStep === 'calibrating') return 'calibration'
    return currentStep
  }, [currentStep])

  // 根据当前步骤更新节点样式
  useEffect(() => {
    // const currentIndex = STEPS_ORDER.indexOf(normalizedStep)
    
    setNodes((nds) =>
      nds.map((node) => {
        // 判断节点状态
        let stepKey = node.id
        if (stepKey === 'calibration') stepKey = 'calibration' 
        
        // 简单处理：如果当前是 idle 或 thinking 但不是特定流程步骤，视为不活跃
        // 如果是特定步骤，则激活
        const isActive = normalizedStep === stepKey
        // const isPassed = currentIndex > -1 && STEPS_ORDER.indexOf(stepKey) < currentIndex // 暂时不需 passed 样式

        const style: React.CSSProperties = {
          padding: '12px 24px',
          borderRadius: '16px',
          fontSize: '14px',
          fontWeight: 600,
          width: '200px',
          textAlign: 'center',
          transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
          border: '1px solid #e2e8f0',
        }
        
        // 默认状态
        style.background = '#ffffff'
        style.color = '#94a3b8'

        // Active 状态
        if (isActive) {
          style.background = 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)'
          style.color = '#ffffff'
          style.boxShadow = '0 0 20px rgba(59, 130, 246, 0.5)'
          style.transform = 'scale(1.05)'
          style.border = 'none'
        }

        return {
          ...node,
          style,
        }
      })
    )

    // 更新连线动画
    setEdges((eds) =>
      eds.map((edge) => {
        const sourceIndex = STEPS_ORDER.indexOf(edge.source)
        const targetIndex = STEPS_ORDER.indexOf(edge.target)
        const currentStepIndex = STEPS_ORDER.indexOf(normalizedStep)
        
        // 当步骤在 source 和 target 之间时，或者刚刚经过 source 时激活连线
        const isActive = currentStepIndex >= sourceIndex && currentStepIndex <= targetIndex && currentStepIndex !== -1

        return {
          ...edge,
          animated: isActive,
          style: {
            stroke: isActive ? '#3b82f6' : '#e2e8f0',
            strokeWidth: isActive ? 2 : 1,
            opacity: isActive ? 1 : 0.5,
          },
        }
      })
    )
  }, [normalizedStep, setNodes, setEdges])

  return (
    <div className="h-full w-full relative bg-gray-50">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        attributionPosition="bottom-right"
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={20} size={1} color="#e2e8f0" />
        <Controls showInteractive={false} />
      </ReactFlow>

      {/* 实时日志浮层 */}
      <div className="absolute top-4 right-4 w-80 max-h-96 bg-white/80 backdrop-blur-md rounded-xl shadow-lg border border-gray-100 flex flex-col overflow-hidden pointer-events-none">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2 bg-gray-50/50">
          <Terminal size={14} className="text-gray-500" />
          <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider">System Log</span>
          {normalizedStep !== 'idle' && (
            <span className="ml-auto w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          )}
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3 font-mono text-xs custom-scrollbar">
          {logs.length === 0 ? (
            <div className="text-gray-400 italic text-center py-4">系统就绪，等待任务...</div>
          ) : (
            logs.map((log, index) => (
              <div key={index} className="flex gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
                <span className="text-gray-300 shrink-0 select-none">
                  {new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' })}
                </span>
                <span className={`break-words ${
                  log.type === 'error' ? 'text-red-500' :
                  log.type === 'success' ? 'text-green-600' :
                  log.type === 'warning' ? 'text-amber-500' :
                  'text-gray-600'
                }`}>
                  {log.type === 'error' && '❌ '}
                  {log.type === 'success' && '✅ '}
                  {log.message}
                </span>
              </div>
            ))
          )}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  )
}
