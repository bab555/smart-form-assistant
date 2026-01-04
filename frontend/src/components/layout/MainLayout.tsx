/**
 * 主布局组件 - 三栏式沉浸布局
 */

import ChatPanel from '../chat/ChatPanel'
import VisualizerPanel from '../visualizer/VisualizerPanel'
import GridPanel from '../grid/GridPanel'

export default function MainLayout() {
  return (
    <div className="h-screen w-screen overflow-hidden bg-background">
      {/* 三栏网格布局 */}
      <div className="h-full grid grid-cols-[25%_35%_40%] gap-2 p-2">
        {/* 左栏：智能交互区 */}
        <div className="bg-card rounded-lg shadow-lg overflow-hidden">
          <ChatPanel />
        </div>

        {/* 中栏：思维可视化区 */}
        <div className="bg-card rounded-lg shadow-lg overflow-hidden">
          <VisualizerPanel />
        </div>

        {/* 右栏：智能表格区 */}
        <div className="bg-card rounded-lg shadow-lg overflow-hidden">
          <GridPanel />
        </div>
      </div>
    </div>
  )
}

