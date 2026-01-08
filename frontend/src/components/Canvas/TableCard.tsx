/**
 * TableCard 可拖拽表格卡片
 * 
 * 功能：
 * - 可拖拽移动
 * - 类 Excel 单元格编辑 (AG Grid)
 * - 显示校对建议
 * - 导出 Excel
 */

import React, { useMemo, useState, useCallback } from 'react';
import { useDraggable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef, CellValueChangedEvent } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-quartz.css';
import { useCanvasStore, TableData, TableRow } from '@/store/useCanvasStore';
import { GripVertical, X, AlertTriangle, Loader2, Download, Plus, Maximize2, Trash2 } from 'lucide-react';
import { exportTableToExcel } from '@/utils/export';
import { ContextMenu, MenuItem } from './ContextMenu';
import './TableCard.css';

interface TableCardProps {
  table: TableData;
}

export const TableCard: React.FC<TableCardProps> = ({ table }) => {
  const removeTable = useCanvasStore((state) => state.removeTable);
  const setActiveTable = useCanvasStore((state) => state.setActiveTable);
  const activeTableId = useCanvasStore((state) => state.activeTableId);
  const clearCalibrationNote = useCanvasStore((state) => state.clearCalibrationNote);
  const updateCell = useCanvasStore((state) => state.updateCell);
  const addRow = useCanvasStore((state) => state.addRow);
  const updateTableSize = useCanvasStore((state) => state.updateTableSize);
  
  // Resize 状态
  const [isResizing, setIsResizing] = useState(false);
  
  // 右键菜单状态
  const [contextMenu, setContextMenu] = useState<{ isOpen: boolean; x: number; y: number }>({
    isOpen: false,
    x: 0,
    y: 0,
  });
  
  // 拖拽
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: table.id,
  });

  const style: React.CSSProperties = {
    position: 'absolute',
    left: table.position.x,
    top: table.position.y,
    width: table.size.width,
    height: table.size.height,
    transform: CSS.Transform.toString(transform),
    zIndex: isDragging ? 1000 : activeTableId === table.id ? 100 : 1,
    opacity: isDragging ? 0.8 : 1,
  };
  
  // 添加新行
  const handleAddRow = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    addRow(table.id);
  }, [table.id, addRow]);
  
  // 关闭表格
  const handleClose = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    removeTable(table.id);
  }, [table.id, removeTable]);
  
  // Resize 处理
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    setIsResizing(true);
    
    const startX = e.clientX;
    const startY = e.clientY;
    const startWidth = table.size.width;
    const startHeight = table.size.height;
    
    const handleMouseMove = (moveEvent: MouseEvent) => {
      const newWidth = Math.max(400, startWidth + (moveEvent.clientX - startX));
      const newHeight = Math.max(200, startHeight + (moveEvent.clientY - startY));
      updateTableSize(table.id, { width: newWidth, height: newHeight });
    };
    
    const handleMouseUp = () => {
      setIsResizing(false);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [table.id, table.size.width, table.size.height, updateTableSize]);

  const columnDefs: ColDef<TableRow>[] = useMemo(() => {
    return table.schema.map((col) => {
      const isNumber = col.type === 'number';
      return {
        field: col.key,
        headerName: col.title,
        editable: true,
        width: col.width || (isNumber ? 110 : 160),
        resizable: true,
        valueParser: isNumber
          ? (params) => {
              const v = params.newValue;
              if (v === '' || v === null || v === undefined) return 0;
              const n = Number(v);
              return Number.isFinite(n) ? n : 0;
            }
          : undefined,
      } as ColDef<TableRow>;
    });
  }, [table.schema]);

  const defaultColDef = useMemo<ColDef<TableRow>>(
    () => ({
      sortable: false,
      filter: false,
    }),
    []
  );

  const onCellValueChanged = (e: CellValueChangedEvent<TableRow>) => {
    const rowIndex = e.rowIndex;
    const field = e.colDef.field;
    if (rowIndex == null || !field) return;
    updateCell(table.id, rowIndex, field, e.newValue);
  };

  // 导出单个表格
  const handleExport = useCallback((e?: React.MouseEvent) => {
    e?.stopPropagation();
    exportTableToExcel(table);
  }, [table]);
  
  // 右键菜单处理
  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({
      isOpen: true,
      x: e.clientX,
      y: e.clientY,
    });
  }, []);
  
  const closeContextMenu = useCallback(() => {
    setContextMenu(prev => ({ ...prev, isOpen: false }));
  }, []);
  
  // 表格右键菜单项
  const tableMenuItems: MenuItem[] = useMemo(() => [
    {
      label: '添加行',
      icon: <Plus size={14} />,
      onClick: () => addRow(table.id),
    },
    {
      label: '导出此表格',
      icon: <Download size={14} />,
      onClick: () => handleExport(),
      divider: true,
    },
    {
      label: '关闭表格',
      icon: <Trash2 size={14} />,
      onClick: () => removeTable(table.id),
    },
  ], [table.id, addRow, handleExport, removeTable]);

  // 获取有校对备注的行索引
  const rowsWithNotes = Object.keys(table.calibrationNotes).map(Number);

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`table-card ${isDragging ? 'dragging' : ''} ${activeTableId === table.id ? 'active' : ''}`}
      onClick={() => setActiveTable(table.id)}
      onContextMenu={handleContextMenu}
    >
      {/* 右键菜单 */}
      {contextMenu.isOpen && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          items={tableMenuItems}
          onClose={closeContextMenu}
        />
      )}
      
      {/* 标题栏 - 整个标题栏可拖拽 */}
      <div className="table-card-header" {...listeners} {...attributes}>
        <div className="header-left">
          <GripVertical size={16} className="drag-handle-icon" />
          <span className="table-title">{table.title}</span>
          {table.metadata.date && (
            <span className="table-date">📅 {table.metadata.date}</span>
          )}
          {table.isStreaming && (
            <Loader2 size={14} className="streaming-indicator" />
          )}
        </div>
        <div className="header-right" onPointerDown={(e) => e.stopPropagation()}>
          <button
            className="action-btn"
            onClick={handleAddRow}
            title="添加行"
          >
            <Plus size={14} />
          </button>
          <button
            className="action-btn"
            onClick={handleExport}
            title="导出 Excel"
          >
            <Download size={14} />
          </button>
          <button
            className="close-btn"
            onClick={handleClose}
            title="关闭表格"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* 表格内容 */}
      <div className="table-card-body">
        <div
          className="ag-theme-quartz"
          style={{ width: '100%', flex: 1, minHeight: 150 }}
          onClick={(e) => e.stopPropagation()}
        >
          <AgGridReact<TableRow>
            rowData={table.rows}
            columnDefs={columnDefs}
            defaultColDef={defaultColDef}
            stopEditingWhenCellsLoseFocus
            onCellValueChanged={onCellValueChanged}
            suppressRowClickSelection
            domLayout="autoHeight"
          />
        </div>
      </div>

      {/* 校对建议区域 */}
      {rowsWithNotes.length > 0 && (
        <div className="calibration-notes">
          <div className="notes-header">
            <span className="notes-title">
              <AlertTriangle size={12} />
              校对建议 ({rowsWithNotes.length})
            </span>
          </div>
          {rowsWithNotes.map((rowIndex) => (
            <div key={rowIndex} className="note-item">
              <span className="note-row">行 {rowIndex + 1}</span>
              <span className="note-text">{table.calibrationNotes[rowIndex]}</span>
              <button
                className="note-dismiss"
                onClick={(e) => {
                  e.stopPropagation();
                  clearCalibrationNote(table.id, rowIndex);
                }}
                title="忽略此建议"
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}
      
      {/* Resize Handle */}
      <div
        className={`resize-handle ${isResizing ? 'resizing' : ''}`}
        onMouseDown={handleResizeStart}
        title="拖动调整大小"
      >
        <Maximize2 size={12} />
      </div>
    </div>
  );
};

export default TableCard;
