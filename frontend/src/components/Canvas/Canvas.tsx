/**
 * Canvas 画布容器 (Sheet 模式)
 * 
 * 功能：
 * - 顶部状态栏 (时间, 连接状态)
 * - 表格 Tab 页签 (Sheet1, Sheet2...)
 * - 仅渲染当前激活的表格 (Active Sheet)
 */

import React, { useEffect, useState, useCallback } from 'react';
import { useCanvasStore } from '@/store/useCanvasStore';
import { TableCard } from './TableCard';
import { ContextMenu, createCanvasMenuItems } from './ContextMenu';
import { exportAllTablesToExcel, exportTableToExcel } from '@/utils/export';
import { Plus, Clock, Download, X, AlertCircle } from 'lucide-react';
import './Canvas.css';

interface ContextMenuState {
  isOpen: boolean;
  x: number;
  y: number;
}

export const Canvas: React.FC = () => {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({ isOpen: false, x: 0, y: 0 });
  const [closingTableId, setClosingTableId] = useState<string | null>(null);
  
  // Store Selectors
  const tables = useCanvasStore(state => state.tables);
  const activeTableId = useCanvasStore(state => state.activeTableId);
  const isConnected = useCanvasStore(state => state.isConnected);
  
  // Store Actions
  const createTable = useCanvasStore(state => state.createTable);
  const setActiveTable = useCanvasStore(state => state.setActiveTable);
  const removeTable = useCanvasStore(state => state.removeTable);

  const activeTable = activeTableId ? tables[activeTableId] : null;

  // 实时时钟
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // 新建表格
  const handleCreateTable = useCallback(() => {
    const tableCount = Object.keys(tables).length;
    const newId = createTable({
      title: `Sheet${tableCount + 1}`,
    });
    // 自动切换到新表
    setActiveTable(newId);
  }, [tables, createTable, setActiveTable]);

  // 点击关闭按钮
  const handleCloseRequest = useCallback((e: React.MouseEvent, tableId: string) => {
    e.stopPropagation();
    setClosingTableId(tableId);
  }, []);

  // 确认关闭
  const confirmClose = (withDownload: boolean) => {
    if (!closingTableId) return;
    
    if (withDownload) {
      const table = tables[closingTableId];
      if (table) {
        exportTableToExcel(table);
      }
    }
    
    removeTable(closingTableId);
    
    // 如果关闭的是当前激活表，切换到前一个表
    if (activeTableId === closingTableId) {
      const tableIds = Object.keys(tables);
      const index = tableIds.indexOf(closingTableId);
      if (index > 0) {
        setActiveTable(tableIds[index - 1]);
      } else if (tableIds.length > 1) {
        // 如果还有其他表，切换到原本的第二个（现在的第一个）
        const nextId = tableIds.find(id => id !== closingTableId);
        setActiveTable(nextId || null);
      } else {
        setActiveTable(null);
      }
    }
    
    setClosingTableId(null);
  };

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

  // 画布右键菜单项（仅导出所有）
  const canvasMenuItems = createCanvasMenuItems(
    handleExportAll,
    Object.keys(tables).length > 0
  );

  return (
    <div className="canvas-container" onContextMenu={handleContextMenu}>
      {/* 关闭确认弹窗 */}
      {closingTableId && (
        <div className="template-modal-overlay">
          <div className="template-modal-backdrop" onClick={() => setClosingTableId(null)} />
          <div className="confirm-modal">
            <div className="confirm-header">
              <AlertCircle size={20} className="text-blue-500" />
              <span>关闭表格确认</span>
            </div>
            <div className="confirm-body">
              <p>您确定要关闭表格 "{tables[closingTableId]?.title}" 吗？</p>
              <p className="text-sm text-gray-500 mt-2">未保存的内容将会丢失。</p>
            </div>
            <div className="confirm-footer">
              <button className="btn-cancel" onClick={() => setClosingTableId(null)}>取消</button>
              <button className="btn-download" onClick={() => confirmClose(true)}>
                <Download size={14} />
                下载并关闭
              </button>
              <button className="btn-danger" onClick={() => confirmClose(false)}>直接关闭</button>
            </div>
          </div>
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

      {/* 顶部 Header: 标题/状态/操作 */}
      <div className="canvas-header">
        <div className="header-left">
          <div className="header-title">订单录入系统</div>
          <div className="status-clock" style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: '#64748b' }}>
            <Clock size={14} />
            <span>{currentTime.toLocaleTimeString('zh-CN', { hour12: false })}</span>
          </div>
          <div style={{ 
            display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, 
            color: isConnected ? '#22c55e' : '#ef4444',
            background: isConnected ? '#f0fdf4' : '#fef2f2',
            padding: '2px 8px', borderRadius: 12, border: `1px solid ${isConnected ? '#bbf7d0' : '#fecaca'}`
          }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor' }} />
            <span>{isConnected ? '在线' : '离线'}</span>
          </div>
        </div>
        
        <div className="header-right">
          {Object.keys(tables).length > 0 && (
            <button
              className="action-btn"
              onClick={handleExportAll}
              title="导出所有表格"
            >
              <Download size={14} />
              <span>导出全部</span>
            </button>
          )}
        </div>
      </div>

      {/* Sheet Tabs 页签 */}
      <div className="sheet-tabs">
        {Object.values(tables).map((table) => (
          <div
            key={table.id}
            className={`sheet-tab ${activeTableId === table.id ? 'active' : ''}`}
            onClick={() => setActiveTable(table.id)}
          >
            <span>{table.title}</span>
            <div 
              className="sheet-tab-close" 
              onClick={(e) => handleCloseRequest(e, table.id)}
            >
              <X size={12} />
            </div>
          </div>
        ))}
        <div className="new-sheet-btn" onClick={handleCreateTable} title="新建 Sheet">
          <Plus size={16} />
        </div>
      </div>

      {/* 画布主区域 */}
      <div className="canvas-content">
        {activeTable ? (
          <TableCard 
            key={activeTable.id} 
            table={activeTable}
            onCloseRequest={(tableId) => setClosingTableId(tableId)}
          />
        ) : (
          /* 空状态 */
          <div className="canvas-empty">
            <div className="create-btn-large" onClick={handleCreateTable}>
              <Plus size={48} strokeWidth={1.5} color="#cbd5e1" />
              <span style={{ fontSize: 16, fontWeight: 500, color: '#64748b' }}>新建订单 Sheet</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Canvas;
