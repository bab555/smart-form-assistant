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
  MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'
import type { LogEntry } from '@types'
import { useEffect, useMemo, useRef } from 'react'

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
    const currentIndex = STEPS_ORDER.indexOf(normalizedStep)
    
    setNodes((nds) =>
      nds.map((node) => {
        // 判断节点状态
        let stepKey = node.id
        if (stepKey === 'calibration') stepKey = 'calibration' 
        
        const nodeIndex = STEPS_ORDER.indexOf(stepKey)
        
        let style: React.CSSProperties = {
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
        if (normalizedStep === stepKey) {
          style.background = 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)'
          style.color = '#ffffff'
          style.border = 'none'
          style.boxShadow = '0 0 30px rgba(59, 130, 246, 0.6), 0 0 10px rgba(59, 130, 246, 0.4) inset'
          style.transform = 'scale(1.15)'
          style.zIndex = 10
        }
        // Completed 状态
        else if (currentIndex > nodeIndex && currentIndex !== -1) {
          style.background = '#ecfdf5'
          style.color = '#059669'
          style.borderColor = '#10b981'
          style.boxShadow = '0 2px 4px rgba(16, 185, 129, 0.1)'
        }

        return {
          ...node,
          style,
        }
      })
    )

    // 更新连线样式
    setEdges((eds) =>
      eds.map((edge) => {
        const sourceIndex = STEPS_ORDER.indexOf(edge.source)
        const targetIndex = STEPS_ORDER.indexOf(edge.target)
        
        // 只要源节点已完成或正在进行，连线就应该激活（或者更严格一点：正在流向目标时激活）
        // 简单的逻辑：如果当前步骤 >= 目标步骤，说明数据已经流过这条线
        // 或者：如果当前步骤 == 源步骤，说明正在从源流向目标（激活当前边）
        
        // 优化逻辑：只有当前正在进行的边的上一条边才激活
        const isCurrentPath = currentIndex >= sourceIndex
        
        return {
          ...edge,
          animated: isCurrentPath, // 只要流过就保持 animated
          style: {
            stroke: isCurrentPath ? '#3b82f6' : '#e2e8f0',
            strokeWidth: isCurrentPath ? 3 : 2,
            opacity: isCurrentPath ? 1 : 0.5,
            transition: 'all 0.5s ease',
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isCurrentPath ? '#3b82f6' : '#e2e8f0',
          },
        }
      })
    )
  }, [normalizedStep, setNodes, setEdges])

  return (
    <div className="h-full w-full bg-slate-50 relative group">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        attributionPosition="bottom-right"
        proOptions={{ hideAttribution: true }}
        minZoom={0.5}
        maxZoom={1.5}
      >
        <Background gap={24} color="#e2e8f0" size={1} />
        <Controls showInteractive={false} className="opacity-0 group-hover:opacity-100 transition-opacity" />
      </ReactFlow>

      {/* 日志悬浮面板 - 美化版 */}
      <div className="absolute bottom-6 left-6 right-6 pointer-events-none">
        <div className="bg-white/90 backdrop-blur-md rounded-2xl p-4 max-h-48 shadow-2xl border border-white/50 pointer-events-auto overflow-hidden flex flex-col transition-all duration-300 hover:shadow-blue-200/50">
          <div className="flex items-center gap-2 mb-3 shrink-0 border-b border-gray-100 pb-2">
            <div className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500"></span>
            </div>
            <h4 className="text-xs font-bold text-gray-700 uppercase tracking-widest font-mono">System Logs</h4>
          </div>
          
          <div className="flex-1 overflow-y-auto custom-scrollbar pr-2 space-y-2">
            {logs.length === 0 ? (
              <p className="text-xs text-gray-400 italic text-center py-4">等待任务开始...</p>
            ) : (
              logs.map((log, index) => (
                <div 
                  key={index} 
                  className={`flex gap-3 text-xs p-1.5 rounded-lg transition-colors ${
                    index === logs.length - 1 ? 'bg-blue-50/80 animate-pulse' : 'hover:bg-gray-50'
                  }`}
                >
                  <span className="font-mono text-gray-400 min-w-[64px] scale-90 origin-left">
                    {new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                  <span className={`${
                    log.status === 'error' ? 'text-red-600 font-bold' : 
                    log.status === 'success' ? 'text-emerald-600 font-medium' : 
                    'text-slate-600'
                  } break-words flex-1`}>
                    {log.message}
                  </span>
                </div>
              ))
            )}
            <div ref={logEndRef} />
          </div>
        </div>
      </div>
    </div>
  )
}
