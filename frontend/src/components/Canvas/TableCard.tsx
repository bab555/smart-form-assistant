/**
 * TableCard 表格卡片 (Sheet 模式)
 * 
 * 功能：
 * - 铺满当前视图
 * - 类 Excel 单元格编辑 (AG Grid)
 * - 显示校对建议
 * - 订单元数据管理 (客户, 时间)
 * - 行末删除按钮
 */

import React, { useMemo, useState, useCallback, useEffect, useRef } from 'react';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef, CellValueChangedEvent, ICellRendererParams } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-quartz.css';
import { useCanvasStore, TableData, TableRow } from '@/store/useCanvasStore';
import { AlertTriangle, Loader2, X, Plus, Download, Calendar, User, Minus, Store, ClipboardList, AlertCircle } from 'lucide-react';
import { exportTableToExcel, exportAllTablesToExcel } from '@/utils/export';
import { ContextMenu, MenuItem } from './ContextMenu';
import './TableCard.css';

// 格式化日期为 datetime-local 输入框格式
const formatDateTimeLocal = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}`;
};

// Mock 客户数据
const MOCK_CLIENTS = [
  { id: 'c1', name: '张三餐饮' },
  { id: 'c2', name: '李四超市' },
  { id: 'c3', name: '王五食堂' },
  { id: 'c4', name: '赵六酒店' },
];

// Mock 餐厅数据（按客户分组）
const MOCK_RESTAURANTS: Record<string, Array<{ id: string; name: string }>> = {
  'c1': [
    { id: 'r1-1', name: '张三餐饮-东风路店' },
    { id: 'r1-2', name: '张三餐饮-人民路店' },
    { id: 'r1-3', name: '张三餐饮-中山店' },
  ],
  'c2': [
    { id: 'r2-1', name: '李四超市-总店' },
    { id: 'r2-2', name: '李四超市-分店' },
  ],
  'c3': [
    { id: 'r3-1', name: '王五食堂-A区' },
    { id: 'r3-2', name: '王五食堂-B区' },
    { id: 'r3-3', name: '王五食堂-C区' },
  ],
  'c4': [
    { id: 'r4-1', name: '赵六酒店-大堂' },
    { id: 'r4-2', name: '赵六酒店-宴会厅' },
  ],
};

// Mock 订单类型数据（按客户分组）
const MOCK_ORDER_TYPES: Record<string, Array<{ id: string; name: string }>> = {
  'c1': [
    { id: 'ot1-1', name: '订单1-日常采购' },
    { id: 'ot1-2', name: '订单2-活动采购' },
  ],
  'c2': [
    { id: 'ot2-1', name: '订单1-门店补货' },
    { id: 'ot2-2', name: '订单2-促销备货' },
  ],
  'c3': [
    { id: 'ot3-1', name: '订单1-早餐' },
    { id: 'ot3-2', name: '订单2-午餐' },
    { id: 'ot3-3', name: '订单3-晚餐' },
  ],
  'c4': [
    { id: 'ot4-1', name: '订单1-日常' },
    { id: 'ot4-2', name: '订单2-宴席' },
  ],
};

// 行操作按钮组件
const RowActionsCellRenderer: React.FC<ICellRendererParams & { onDelete: (rowIndex: number) => void }> = (props) => {
  const rowIndex = props.rowIndex;
  
  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    props.onDelete(rowIndex);
  };

  return (
    <div className="row-actions-cell">
      <button 
        className="row-action-btn delete" 
        onClick={handleDelete}
        title="删除此行"
      >
        <Minus size={14} />
      </button>
    </div>
  );
};

// 从父组件传递的回调
interface TableCardProps {
  table: TableData;
  onCloseRequest?: (tableId: string) => void;  // 关闭 Sheet 请求（触发确认弹窗）
}

export const TableCard: React.FC<TableCardProps> = ({ table, onCloseRequest }) => {
  const tables = useCanvasStore((state) => state.tables);
  const updateCell = useCanvasStore((state) => state.updateCell);
  const addRow = useCanvasStore((state) => state.addRow);
  const deleteRow = useCanvasStore((state) => state.deleteRow);
  const clearCalibrationNote = useCanvasStore((state) => state.clearCalibrationNote);
  const updateMetadata = useCanvasStore((state) => state.updateMetadata);
  
  // 右键菜单状态
  const [contextMenu, setContextMenu] = useState<{ isOpen: boolean; x: number; y: number }>({
    isOpen: false,
    x: 0,
    y: 0,
  });
  
  // 删除行确认弹窗
  const [deletingRowIndex, setDeletingRowIndex] = useState<number | null>(null);

  // 时间输入框是否正在编辑（用户操作期间停止自动同步）
  const isEditingTimeRef = useRef<boolean>(false);

  // 初始化时间（如果没有）
  useEffect(() => {
    if (!table.metadata.date) {
      const formatted = formatDateTimeLocal(new Date());
      updateMetadata(table.id, { date: formatted });
    }
  }, [table.id, table.metadata.date, updateMetadata]);

  // 时间自动同步：每分钟同步系统时间（用户编辑期间暂停）
  useEffect(() => {
    let intervalId: ReturnType<typeof setInterval> | null = null;
    
    // 计算到下一分钟的延迟
    const now = new Date();
    const msUntilNextMinute = (60 - now.getSeconds()) * 1000 - now.getMilliseconds();
    
    // 首次同步（等到下一个整分钟）
    const timeoutId = setTimeout(() => {
      // 首次同步
      if (!isEditingTimeRef.current) {
        const formatted = formatDateTimeLocal(new Date());
        updateMetadata(table.id, { date: formatted });
      }
      
      // 之后每分钟同步一次
      intervalId = setInterval(() => {
        if (!isEditingTimeRef.current) {
          const formatted = formatDateTimeLocal(new Date());
          updateMetadata(table.id, { date: formatted });
        }
      }, 60000); // 每60秒
    }, msUntilNextMinute);

    // 清理函数
    return () => {
      clearTimeout(timeoutId);
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [table.id, updateMetadata]);

  // 时间输入框聚焦/失焦处理
  const handleTimeFocus = useCallback(() => {
    isEditingTimeRef.current = true;
  }, []);

  const handleTimeBlur = useCallback(() => {
    isEditingTimeRef.current = false;
  }, []);
  
  // 添加新行
  const handleAddRow = useCallback((e?: React.MouseEvent) => {
    e?.stopPropagation();
    addRow(table.id);
  }, [table.id, addRow]);

  // 删除行（显示确认弹窗）
  const handleDeleteRowRequest = useCallback((rowIndex: number) => {
    // 如果只剩一行，不允许删除
    if (table.rows.length <= 1) {
      return;
    }
    setDeletingRowIndex(rowIndex);
  }, [table.rows.length]);

  // 确认删除行
  const confirmDeleteRow = useCallback(() => {
    if (deletingRowIndex !== null) {
      deleteRow(table.id, deletingRowIndex);
      setDeletingRowIndex(null);
    }
  }, [table.id, deletingRowIndex, deleteRow]);

  // 导出所有
  const handleExportAll = useCallback(() => {
    exportAllTablesToExcel(tables);
  }, [tables]);

  // 关闭当前 Sheet
  const handleCloseSheet = useCallback(() => {
    if (onCloseRequest) {
      onCloseRequest(table.id);
    }
  }, [table.id, onCloseRequest]);
  
  // 导出
  const handleExport = useCallback((e?: React.MouseEvent) => {
    e?.stopPropagation();
    exportTableToExcel(table);
  }, [table]);

  // 元数据变更
  const handleClientChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const clientId = e.target.value;
    const client = MOCK_CLIENTS.find(c => c.id === clientId);
    // 选择客户后，清空餐厅和订单类型
    updateMetadata(table.id, { 
      customerId: clientId, 
      customer: client ? client.name : '',
      restaurantId: '',
      restaurant: '',
      orderTypeId: '',
      orderType: '',
    });
  };

  const handleRestaurantChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const restaurantId = e.target.value;
    const restaurants = MOCK_RESTAURANTS[table.metadata.customerId as string] || [];
    const restaurant = restaurants.find(r => r.id === restaurantId);
    updateMetadata(table.id, { 
      restaurantId, 
      restaurant: restaurant ? restaurant.name : '' 
    });
  };

  const handleOrderTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const orderTypeId = e.target.value;
    const orderTypes = MOCK_ORDER_TYPES[table.metadata.customerId as string] || [];
    const orderType = orderTypes.find(o => o.id === orderTypeId);
    updateMetadata(table.id, { 
      orderTypeId, 
      orderType: orderType ? orderType.name : '' 
    });
  };

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateMetadata(table.id, { date: e.target.value });
  };

  // 获取当前客户的餐厅和订单类型列表
  const currentRestaurants = table.metadata.customerId 
    ? (MOCK_RESTAURANTS[table.metadata.customerId as string] || []) 
    : [];
  const currentOrderTypes = table.metadata.customerId 
    ? (MOCK_ORDER_TYPES[table.metadata.customerId as string] || []) 
    : [];

  // 列定义
  const columnDefs: ColDef<TableRow>[] = useMemo(() => {
    // 数据列
    const dataCols = table.schema.map((col, index) => {
      const isNumber = col.type === 'number';
      const isLastDataCol = index === table.schema.length - 1;
      return {
        field: col.key,
        headerName: col.title,
        editable: true,
        // 最后一列使用 flex 填充剩余空间
        ...(isLastDataCol 
          ? { flex: 1, minWidth: col.width || 150 } 
          : { width: col.width || (isNumber ? 110 : 160) }
        ),
        resizable: true,
        valueParser: isNumber
          ? (params) => {
              const v = params.newValue;
              if (v === '' || v === null || v === undefined) return 0;
              const n = Number(v);
              return Number.isFinite(n) ? n : 0;
            }
          : undefined,
        // 如果是"订单商品"列（校对结果），给予特殊样式
        cellStyle: col.key === '订单商品' ? { color: '#2563eb', fontWeight: 500 } : undefined,
      } as ColDef<TableRow>;
    });
    
    // 操作列
    const actionCol: ColDef<TableRow> = {
      headerName: '',
      field: '__actions__',
      width: 50,
      pinned: 'right',
      lockPosition: true,
      resizable: false,
      editable: false,
      sortable: false,
      filter: false,
      cellRenderer: RowActionsCellRenderer,
      cellRendererParams: {
        onDelete: handleDeleteRowRequest,
      },
    };
    
    return [...dataCols, actionCol];
  }, [table.schema, handleDeleteRowRequest]);

  const defaultColDef = useMemo<ColDef<TableRow>>(
    () => ({
      sortable: false, 
      filter: false,
      resizable: true,
    }),
    []
  );

  const onCellValueChanged = (e: CellValueChangedEvent<TableRow>) => {
    const rowIndex = e.rowIndex;
    const field = e.colDef.field;
    if (rowIndex == null || !field) return;
    updateCell(table.id, rowIndex, field, e.newValue);
  };

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
  
  const tableMenuItems: MenuItem[] = useMemo(() => [
    {
      label: '添加行',
      icon: <Plus size={14} />,
      onClick: () => handleAddRow(),
    },
    {
      label: '删除选中行',
      icon: <Minus size={14} />,
      onClick: () => {
        // 删除最后一行（或选中行，这里简化处理）
        if (table.rows.length > 1) {
          handleDeleteRowRequest(table.rows.length - 1);
        }
      },
      disabled: table.rows.length <= 1,
      danger: true,
    },
    {
      label: '导出当前 Sheet',
      icon: <Download size={14} />,
      onClick: () => handleExport(),
      divider: true,
    },
    {
      label: '导出所有 Sheet',
      icon: <Download size={14} />,
      onClick: () => handleExportAll(),
    },
    {
      label: '关闭当前 Sheet',
      icon: <X size={14} />,
      onClick: () => handleCloseSheet(),
      divider: true,
      danger: true,
    },
  ], [table.id, table.rows.length, handleAddRow, handleDeleteRowRequest, handleExport, handleExportAll, handleCloseSheet]);

  // 获取有校对备注的行索引
  const rowsWithNotes = Object.keys(table.calibrationNotes).map(Number);

  return (
    <div className="table-card" onContextMenu={handleContextMenu}>
      {/* 右键菜单 */}
      {contextMenu.isOpen && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          items={tableMenuItems}
          onClose={closeContextMenu}
        />
      )}

      {/* 删除行确认弹窗 */}
      {deletingRowIndex !== null && (
        <div className="confirm-modal-overlay">
          <div className="confirm-modal-backdrop" onClick={() => setDeletingRowIndex(null)} />
          <div className="confirm-modal">
            <div className="confirm-header">
              <AlertCircle size={20} className="icon-warning" />
              <span>删除行确认</span>
            </div>
            <div className="confirm-body">
              <p>确定要删除第 {deletingRowIndex + 1} 行吗？</p>
              <p className="confirm-hint">此操作不可恢复。</p>
            </div>
            <div className="confirm-footer">
              <button className="btn-cancel" onClick={() => setDeletingRowIndex(null)}>取消</button>
              <button className="btn-danger" onClick={confirmDeleteRow}>删除</button>
            </div>
          </div>
        </div>
      )}
      
      {/* 标题栏 / 工具栏 */}
      <div className="table-card-header">
        <div className="header-left">
          {table.isStreaming && (
            <div className="streaming-badge">
              <Loader2 size={14} className="streaming-indicator" />
              <span>正在生成...</span>
            </div>
          )}
        </div>
        <div className="header-right">
          <button className="action-btn add-btn" onClick={handleAddRow} title="添加行">
            <Plus size={14} />
            <span>添加行</span>
          </button>
        </div>
      </div>

      {/* 订单元数据区域 */}
      <div className="metadata-panel">
        <div className="metadata-item">
          <User size={14} className="meta-icon" />
          <span className="meta-label">客户:</span>
          <select 
            className="meta-select"
            value={table.metadata.customerId || ''}
            onChange={handleClientChange}
          >
            <option value="">-- 选择客户 --</option>
            {MOCK_CLIENTS.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>

        <div className="metadata-item">
          <Store size={14} className="meta-icon" />
          <span className="meta-label">餐厅:</span>
          <select 
            className="meta-select"
            value={table.metadata.restaurantId || ''}
            onChange={handleRestaurantChange}
            disabled={!table.metadata.customerId}
          >
            <option value="">-- 选择餐厅 --</option>
            {currentRestaurants.map(r => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
        </div>

        <div className="metadata-item">
          <ClipboardList size={14} className="meta-icon" />
          <span className="meta-label">订单类型:</span>
          <select 
            className="meta-select"
            value={table.metadata.orderTypeId || ''}
            onChange={handleOrderTypeChange}
            disabled={!table.metadata.customerId}
          >
            <option value="">-- 选择类型 --</option>
            {currentOrderTypes.map(o => (
              <option key={o.id} value={o.id}>{o.name}</option>
            ))}
          </select>
        </div>

        <div className="metadata-item">
          <Calendar size={14} className="meta-icon" />
          <span className="meta-label">时间:</span>
          <input 
            type="datetime-local" 
            className="meta-input"
            value={table.metadata.date || ''}
            onChange={handleDateChange}
            onFocus={handleTimeFocus}
            onBlur={handleTimeBlur}
            title="自动同步系统时间（编辑时暂停同步）"
          />
        </div>
      </div>

      {/* 表格主体 */}
      <div className="table-card-body">
        <div className="ag-theme-quartz" style={{ width: '100%', height: '100%' }}>
          <AgGridReact<TableRow>
            rowData={table.rows}
            columnDefs={columnDefs}
            defaultColDef={defaultColDef}
            stopEditingWhenCellsLoseFocus
            onCellValueChanged={onCellValueChanged}
            suppressRowClickSelection
          />
        </div>
      </div>

      {/* 底部校对区域 (固定在底部，如有建议则显示) */}
      {rowsWithNotes.length > 0 && (
        <div className="calibration-panel">
          <div className="panel-title">
            <AlertTriangle size={14} />
            <span>AI 校对建议 ({rowsWithNotes.length})</span>
          </div>
          <div className="panel-list">
            {rowsWithNotes.map((rowIndex) => (
              <div key={rowIndex} className="note-item">
                <span className="note-row-idx">行 {rowIndex + 1}</span>
                <span className="note-text">{table.calibrationNotes[rowIndex]}</span>
                <button
                  className="note-dismiss"
                  onClick={() => clearCalibrationNote(table.id, rowIndex)}
                  title="已阅"
                >
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default TableCard;
