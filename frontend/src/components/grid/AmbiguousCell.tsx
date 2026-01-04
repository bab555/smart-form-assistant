/**
 * 歧义单元格组件 - 显示候选值下拉框
 */

import { useState } from 'react'
import { AlertCircle, Check } from 'lucide-react'
import { useFormStore } from '@hooks/useFormStore'
import type { FormItem } from '@types'

interface AmbiguousCellProps {
  cell: FormItem
  rowIndex: number
}

export default function AmbiguousCell({ cell, rowIndex }: AmbiguousCellProps) {
  const [showDropdown, setShowDropdown] = useState(false)
  const { resolveAmbiguity } = useFormStore()

  const handleSelect = (value: string) => {
    resolveAmbiguity(rowIndex, cell.key, value)
    setShowDropdown(false)
  }

  return (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center gap-1 text-warning hover:text-orange-600 transition-colors"
      >
        <AlertCircle size={16} />
        <span className="text-sm">{cell.value || '请选择'}</span>
      </button>

      {showDropdown && (
        <>
          {/* 遮罩层 */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setShowDropdown(false)}
          />

          {/* 下拉菜单 */}
          <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 min-w-[150px]">
            <div className="p-2">
              <p className="text-xs text-gray-500 mb-2">请选择正确的值：</p>
              {cell.candidates?.map((candidate: string, index: number) => (
                <button
                  key={index}
                  onClick={() => handleSelect(candidate)}
                  className="w-full text-left px-3 py-2 rounded hover:bg-gray-100 transition-colors flex items-center justify-between group"
                >
                  <span className="text-sm">{candidate}</span>
                  <Check
                    size={14}
                    className="text-success opacity-0 group-hover:opacity-100 transition-opacity"
                  />
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

