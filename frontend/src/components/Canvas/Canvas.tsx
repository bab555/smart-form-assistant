/**
 * Canvas 画布容器
 * 
 * 功能：
 * - 显示多个可拖拽的表格卡片
 * - 右上角连接状态灯
 * - 新建表格按钮
 * - 从模板新建
 */

import React, { useEffect, useState, useCallback } from 'react';
import { DndContext, DragEndEvent } from '@dnd-kit/core';
import { useCanvasStore } from '@/store/useCanvasStore';
import { TableCard } from './TableCard';
import { ContextMenu, createCanvasMenuItems } from './ContextMenu';
import { TemplateSelector } from '@/components/FloatingPanel/TemplateSelector';
import { exportAllTablesToExcel } from '@/utils/export';
import { Plus, Clock, Download } from 'lucide-react';
import './Canvas.css';

interface ContextMenuState {
  isOpen: boolean;
  x: number;
  y: number;
}

export const Canvas: React.FC = () => {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({ isOpen: false, x: 0, y: 0 });
  const [showTemplates, setShowTemplates] = useState(false);
  
  // 使用独立的 selector 订阅，避免整个 store 变化触发重渲染
  const tables = useCanvasStore(state => state.tables);
  const isConnected = useCanvasStore(state => state.isConnected);
  
  // Actions 是稳定的，可以一起获取
  const createTable = useCanvasStore(state => state.createTable);
  const updateTablePosition = useCanvasStore(state => state.updateTablePosition);

  // 实时时钟
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // 处理拖拽结束
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, delta } = event;
    const tableId = active.id as string;
    const table = tables[tableId];
    
    if (table && delta) {
      updateTablePosition(tableId, {
        x: table.position.x + delta.x,
        y: table.position.y + delta.y,
      });
    }
  };

  // 新建表格
  const handleCreateTable = useCallback(() => {
    const tableCount = Object.keys(tables).length;
    createTable({
      title: `表格 ${tableCount + 1}`,
      position: {
        x: 100 + tableCount * 50,
        y: 100 + tableCount * 50,
      },
    });
  }, [tables, createTable]);

  // 右键菜单
  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setContextMenu({
      isOpen: true,
      x: e.clientX,
      y: e.clientY,
    });
  }, []);

  const closeContextMenu = useCallback(() => {
    setContextMenu((prev) => ({ ...prev, isOpen: false }));
  }, []);

  // 导出所有表格
  const handleExportAll = useCallback(() => {
    exportAllTablesToExcel(tables);
  }, [tables]);

  // 从模板新建
  const handleCreateFromTemplate = useCallback(() => {
    setShowTemplates(true);
  }, []);

  const canvasMenuItems = createCanvasMenuItems(
    handleCreateTable,
    handleExportAll,
    handleCreateFromTemplate,
    false
  );

  return (
    <div className="canvas-container" onContextMenu={handleContextMenu}>
      {/* 模板选择器弹窗 */}
      {showTemplates && (
        <div className="template-modal-overlay">
          <div className="template-modal-backdrop" onClick={() => setShowTemplates(false)} />
          <TemplateSelector onClose={() => setShowTemplates(false)} />
        </div>
      )}
      {/* 右键菜单 */}
      {contextMenu.isOpen && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          items={canvasMenuItems}
          onClose={closeContextMenu}
        />
      )}

      {/* 右上角状态栏 */}
      <div className="canvas-status-bar">
        {/* 导出所有表格按钮 */}
        {Object.keys(tables).length > 0 && (
          <button
            className="export-all-btn"
            onClick={handleExportAll}
            title="导出所有表格"
          >
            <Download size={14} />
            <span>导出全部</span>
          </button>
        )}
        <div className="status-clock">
          <Clock size={14} />
          <span>{currentTime.toLocaleTimeString('zh-CN', { hour12: false })}</span>
        </div>
        <div className={`connection-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
          <span className="indicator-dot" />
          <span className="indicator-text">{isConnected ? '在线' : '离线'}</span>
        </div>
      </div>

      {/* 画布主区域 */}
      <DndContext onDragEnd={handleDragEnd}>
        <div className="canvas-area">
          {Object.values(tables).map((table) => (
            <TableCard key={table.id} table={table} />
          ))}

          {/* 空状态 / 新建按钮 */}
          {Object.keys(tables).length === 0 ? (
            <div className="canvas-empty">
              <button className="create-table-btn large" onClick={handleCreateTable}>
                <Plus size={32} />
                <span>新建表格</span>
              </button>
            </div>
          ) : (
            <button
              className="create-table-btn floating"
              onClick={handleCreateTable}
              title="新建表格"
            >
              <Plus size={20} />
            </button>
          )}
        </div>
      </DndContext>
    </div>
  );
};

export default Canvas;

