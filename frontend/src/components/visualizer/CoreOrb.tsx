/**
 * 核心球体组件 - 待机态动画
 */

export default function CoreOrb() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="relative">
        {/* 核心球体 */}
        <div className="w-32 h-32 rounded-full bg-gradient-to-br from-primary to-blue-400 animate-breathe shadow-2xl" />

        {/* 外圈光环 */}
        <div className="absolute inset-0 rounded-full border-4 border-primary opacity-20 animate-ping" />

        {/* 提示文字 */}
        <div className="absolute -bottom-12 left-1/2 -translate-x-1/2 whitespace-nowrap">
          <p className="text-sm text-gray-500 text-center">等待输入...</p>
        </div>
      </div>
    </div>
  )
}

