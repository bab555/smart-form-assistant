/**
 * 流程图组件 - 使用 React Flow 显示 AI 工作流
 */

import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from 'reactflow'
import 'reactflow/dist/style.css'
import type { AgentStep, LogEntry } from '@types'
import { useEffect } from 'react'

interface ProcessGraphProps {
  currentStep: AgentStep
  logs: LogEntry[]
}

const initialNodes: Node[] = [
  {
    id: '1',
    type: 'default',
    data: { label: 'OCR 识别' },
    position: { x: 100, y: 50 },
  },
  {
    id: '2',
    type: 'default',
    data: { label: '数据校准' },
    position: { x: 100, y: 150 },
  },
  {
    id: '3',
    type: 'default',
    data: { label: '技能查询' },
    position: { x: 100, y: 250 },
  },
  {
    id: '4',
    type: 'default',
    data: { label: '填充表格' },
    position: { x: 100, y: 350 },
  },
]

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', animated: false },
  { id: 'e2-3', source: '2', target: '3', animated: false },
  { id: 'e3-4', source: '3', target: '4', animated: false },
]

export default function ProcessGraph({ currentStep, logs }: ProcessGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  // 根据当前步骤更新节点样式
  useEffect(() => {
    setNodes((nds) =>
      nds.map((node) => {
        let style = {}
        let className = ''

        // 根据步骤高亮节点
        if (
          (currentStep === 'ocr' && node.id === '1') ||
          (currentStep === 'calibrating' && node.id === '2') ||
          (currentStep === 'filling' && node.id === '4')
        ) {
          style = {
            background: '#1677FF',
            color: 'white',
            border: '2px solid #1677FF',
          }
          className = 'animate-pulse'
        }

        return {
          ...node,
          style,
          className,
        }
      })
    )

    // 激活当前连线
    setEdges((eds) =>
      eds.map((edge) => {
        const isActive =
          (currentStep === 'ocr' && edge.id === 'e1-2') ||
          (currentStep === 'calibrating' && edge.id === 'e2-3') ||
          (currentStep === 'filling' && edge.id === 'e3-4')

        return {
          ...edge,
          animated: isActive,
          style: isActive ? { stroke: '#1677FF', strokeWidth: 2 } : {},
        }
      })
    )
  }, [currentStep, setNodes, setEdges])

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>

      {/* 日志显示区 */}
      {logs.length > 0 && (
        <div className="absolute bottom-4 left-4 right-4 bg-white bg-opacity-90 rounded-lg p-3 max-h-32 overflow-y-auto custom-scrollbar shadow-lg">
          <h4 className="text-xs font-semibold text-gray-700 mb-2">执行日志</h4>
          <div className="space-y-1">
            {logs.slice(-5).map((log, index) => (
              <p key={index} className="text-xs text-gray-600">
                <span className="font-mono text-gray-400">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>{' '}
                - {log.message}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

