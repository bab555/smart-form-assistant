/**
 * 核心球体组件 - 待机态动画
 */

export default function CoreOrb() {
  return (
    <div className="h-full flex items-center justify-center overflow-hidden">
      <div className="relative w-80 h-80 flex items-center justify-center">
        {/* 背景光晕 */}
        <div className="absolute inset-0 bg-blue-500/5 rounded-full blur-3xl animate-pulse" />

        {/* 外层轨道圈 - 慢速旋转 */}
        <div className="absolute inset-10 rounded-full border border-blue-200/50 animate-[spin_20s_linear_infinite]" />
        <div className="absolute inset-10 rounded-full border-t-2 border-primary/30 rotate-45 animate-[spin_20s_linear_infinite]" />
        
        {/* 中层机械圈 - 反向旋转 */}
        <div className="absolute inset-20 rounded-full border border-dashed border-blue-300/50 animate-[spin_15s_linear_infinite_reverse]" />
        
        {/* 内层能量环 - 呼吸 */}
        <div className="absolute inset-28 rounded-full border-2 border-primary/20 animate-ping" style={{ animationDuration: '3s' }} />
        
        {/* 核心球体 */}
        <div className="relative z-10 w-24 h-24">
          {/* 核心实体 */}
          <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary via-blue-500 to-indigo-600 shadow-[0_0_50px_rgba(37,99,235,0.6)] animate-pulse"></div>
          
          {/* 核心高光 */}
          <div className="absolute top-2 left-4 w-8 h-4 rounded-full bg-white/30 blur-sm transform -rotate-45"></div>
          
          {/* 内部纹理 */}
          <div className="absolute inset-0 rounded-full border border-white/20 scale-90"></div>
        </div>

        {/* 粒子装饰 (示意) */}
        <div className="absolute top-1/4 left-1/4 w-1 h-1 bg-blue-400 rounded-full animate-ping" style={{ animationDelay: '0.5s' }} />
        <div className="absolute bottom-1/3 right-1/4 w-1.5 h-1.5 bg-indigo-400 rounded-full animate-ping" style={{ animationDelay: '1.2s' }} />
        <div className="absolute top-1/2 right-10 w-1 h-1 bg-primary rounded-full animate-ping" style={{ animationDelay: '2s' }} />

        {/* 提示文字 */}
        <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 text-center whitespace-nowrap">
          <p className="text-sm font-medium text-gray-500 animate-pulse tracking-widest">A.I. SYSTEM READY</p>
          <p className="text-xs text-gray-400 mt-1 scale-90">等待指令输入...</p>
        </div>
      </div>
    </div>
  )
}
