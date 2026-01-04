/**
 * 表格面板组件 - 右栏
 */

import { Save, Trash2, Download } from 'lucide-react'
import SmartTable from './SmartTable'
import { useFormStore } from '@hooks/useFormStore'
import { downloadAsFile } from '@utils/helpers'

export default function GridPanel() {
  const { rows, clearRows, hasAmbiguousCells } = useFormStore()

  const handleSubmit = () => {
    if (hasAmbiguousCells()) {
      alert('表格中仍有未解决的歧义单元格，请先处理。')
      return
    }
    console.log('提交表单数据:', rows)
    // TODO: 调用提交 API
  }

  const handleClear = () => {
    if (confirm('确定要清空所有数据吗？')) {
      clearRows()
    }
  }

  const handleExport = () => {
    const data = rows.map((row) =>
      row.reduce((acc: Record<string, any>, cell: any) => {
        acc[cell.key] = cell.value
        return acc
      }, {} as Record<string, any>)
    )
    downloadAsFile(data, `表单数据_${new Date().toISOString()}.json`)
  }

  return (
    <div className="h-full flex flex-col">
      {/* 标题栏 + 工具栏 */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-800">智能表格</h2>
            <p className="text-xs text-gray-500 mt-1">
              共 {rows.length} 行数据
              {hasAmbiguousCells() && (
                <span className="ml-2 text-warning">⚠ 有歧义项需确认</span>
              )}
            </p>
          </div>
        </div>

        {/* 工具按钮 */}
        <div className="flex gap-2">
          <button
            onClick={handleSubmit}
            disabled={rows.length === 0}
            className="flex items-center gap-1 px-3 py-1.5 bg-success text-white text-sm rounded hover:bg-green-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save size={16} />
            提交
          </button>

          <button
            onClick={handleExport}
            disabled={rows.length === 0}
            className="flex items-center gap-1 px-3 py-1.5 bg-primary text-white text-sm rounded hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download size={16} />
            导出
          </button>

          <button
            onClick={handleClear}
            disabled={rows.length === 0}
            className="flex items-center gap-1 px-3 py-1.5 bg-danger text-white text-sm rounded hover:bg-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Trash2 size={16} />
            清空
          </button>
        </div>
      </div>

      {/* 表格区域 */}
      <div className="flex-1 overflow-hidden">
        <SmartTable />
      </div>
    </div>
  )
}

