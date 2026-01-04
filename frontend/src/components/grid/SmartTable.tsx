/**
 * 智能表格组件 - 基于 AG Grid
 */

import { useMemo, useCallback } from 'react'
import { AgGridReact } from 'ag-grid-react'
import { ColDef } from 'ag-grid-community'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'
import { useFormStore } from '@hooks/useFormStore'
import AmbiguousCell from './AmbiguousCell'
import { getConfidenceColor } from '@utils/helpers'

export default function SmartTable() {
  const { rows, updateCell } = useFormStore()

  // 动态生成列定义
  const columnDefs = useMemo<ColDef[]>(() => {
    if (rows.length === 0) return []

    const firstRow = rows[0]
    return firstRow.map((item: any) => ({
      field: item.key,
      headerName: item.label,
      editable: true,
      cellStyle: (params: any) => {
        const rowData = rows[params.node.rowIndex || 0]
        const cell = rowData?.find((c: any) => c.key === params.colDef.field)

        if (!cell) return {}

        const style: any = {}

        // 歧义单元格
        if (cell.isAmbiguous) {
          style.backgroundColor = '#FFFBE6'
          style.borderColor = '#FAAD14'
          style.borderWidth = '2px'
        }

        // 置信度颜色（左侧边框）
        if (!cell.isAmbiguous) {
          style.borderLeft = `4px solid ${getConfidenceColor(cell.confidence)}`
        }

        return style
      },
      cellRenderer: (params: any) => {
        const rowData = rows[params.node.rowIndex || 0]
        const cell = rowData?.find((c: any) => c.key === params.colDef.field)

        if (cell?.isAmbiguous) {
          return <AmbiguousCell cell={cell} rowIndex={params.node.rowIndex || 0} />
        }

        return params.value
      },
    }))
  }, [rows])

  // 行数据
  const rowData = useMemo(() => {
    return rows.map((row) =>
      row.reduce((acc: Record<string, any>, cell: any) => {
        acc[cell.key] = cell.value
        return acc
      }, {} as Record<string, any>)
    )
  }, [rows])

  // 单元格编辑完成
  const onCellValueChanged = useCallback(
    (event: any) => {
      const rowIndex = event.node.rowIndex
      const field = event.colDef.field
      const newValue = event.newValue

      updateCell(rowIndex, field, newValue)
    },
    [updateCell]
  )

  if (rows.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        <div className="text-center">
          <p className="text-lg mb-2">暂无数据</p>
          <p className="text-sm">请上传图片或使用语音输入</p>
        </div>
      </div>
    )
  }

  return (
    <div className="ag-theme-alpine h-full w-full">
      <AgGridReact
        columnDefs={columnDefs}
        rowData={rowData}
        onCellValueChanged={onCellValueChanged}
        animateRows={true}
        enableCellTextSelection={true}
        suppressMovableColumns={false}
        defaultColDef={{
          resizable: true,
          sortable: true,
          filter: true,
        }}
      />
    </div>
  )
}

