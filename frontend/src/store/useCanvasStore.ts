/**
 * Canvas 状态管理 (Zustand)
 * 
 * 原则：
 * - 这是唯一权威数据源 (SoT)
 * - 后端推送的数据最终都反映到这里
 * - 用户编辑也直接修改这里
 */

import { create } from 'zustand';
import { ColumnSchema, TableMetadata } from '@/services/protocol';

// ========== 类型定义 ==========

export interface TableRow {
  [key: string]: unknown;
}

export interface TableData {
  id: string;
  title: string;
  position: { x: number; y: number };
  size: { width: number; height: number };
  schema: ColumnSchema[];
  rows: TableRow[];
  metadata: TableMetadata;
  calibrationNotes: Record<number, string>;  // rowIndex -> note (保留用于高亮提示)
  isStreaming: boolean;
}

export interface CanvasState {
  // 数据
  tables: Record<string, TableData>;
  activeTableId: string | null;
  isConnected: boolean;
  
  // Actions - 表格管理
  createTable: (options?: Partial<TableData>) => string;
  removeTable: (tableId: string) => void;
  setActiveTable: (tableId: string | null) => void;
  
  // Actions - 表格位置/大小
  updateTablePosition: (tableId: string, position: { x: number; y: number }) => void;
  updateTableSize: (tableId: string, size: { width: number; height: number }) => void;
  
  // Actions - 数据操作
  appendRow: (tableId: string, row: TableRow) => void;
  replaceRows: (tableId: string, rows: TableRow[], schema?: ColumnSchema[]) => void;
  updateCell: (tableId: string, rowIndex: number, colKey: string, value: unknown) => void;
  addRow: (tableId: string, row?: TableRow) => void;
  deleteRow: (tableId: string, rowIndex: number) => void;
  
  // Actions - Schema
  updateSchema: (tableId: string, schema: ColumnSchema[]) => void;
  updateMetadata: (tableId: string, metadata: Partial<TableMetadata>) => void;
  
  // Actions - 校对
  setCalibrationNote: (tableId: string, rowIndex: number, note: string) => void;
  clearCalibrationNote: (tableId: string, rowIndex: number) => void;
  
  // Actions - 流式状态
  setStreaming: (tableId: string, isStreaming: boolean) => void;
  
  // Actions - 连接状态
  setConnected: (isConnected: boolean) => void;

  // UI - 客户选择高亮
  customerHighlightUntil: Record<string, number>; // tableId -> timestamp(ms)
  highlightCustomerSelect: (tableId: string, durationMs?: number) => void;
  
  // UI - "请选择客户" 全局弹窗
  showCustomerModal: boolean;
  customerModalTableId: string | null;
  openCustomerModal: (tableId: string) => void;
  closeCustomerModal: () => void;

  // UI - 居中提示（用于“多表需分别选择客户”等场景）
  centerNotice: { visible: boolean; message: string; type: 'warning' | 'info' | 'success' | 'error' };
  showCenterNotice: (message: string, type?: 'warning' | 'info' | 'success' | 'error') => void;
  hideCenterNotice: () => void;
  
  // Actions - 批量操作
  clearAll: () => void;
  importTables: (tables: Record<string, TableData>) => void;
  
  // 多表场景：只清空指定表格的客户选择
  resetCustomers: (tableIds: string[]) => void;
}

// ========== 基础模板（标准订单格式） ==========

const DEFAULT_SCHEMA: ColumnSchema[] = [
  { key: '序号', title: '序号', type: 'text', width: 70 },
  { key: '识别商品', title: '识别商品', type: 'text', width: 180 },
  { key: '订单商品', title: '订单商品', type: 'text', width: 180 },
  { key: '规格', title: '规格', type: 'text', width: 130 },
  { key: '单位', title: '单位', type: 'text', width: 80 },
  { key: '数量', title: '数量', type: 'number', width: 90 },
  { key: '备注', title: '备注', type: 'text', width: 200 },
];

const createDefaultTable = (id: string, options?: Partial<TableData>): TableData => {
  const schema = options?.schema || DEFAULT_SCHEMA;
  
  // 如果明确传入 rows（包括空数组），使用传入的值
  // 只有在没有传入 rows 时才使用默认空行
  let rows: TableRow[];
  if (options?.rows !== undefined) {
    rows = options.rows;
  } else {
    // 确保至少有一行数据，避免 react-datasheet-grid 空数据 bug（仅在用户手动创建表格时）
    const defaultRow = schema.reduce((acc, col) => {
      acc[col.key] = col.type === 'number' ? 0 : '';
      return acc;
    }, {} as TableRow);
    rows = [defaultRow];
  }
  
  return {
    id,
    title: options?.title || '新订单',
    position: options?.position || { x: 0, y: 0 },
    size: options?.size || { width: 800, height: 600 },
    schema,
    rows,
    metadata: options?.metadata || {},
    calibrationNotes: {},
    isStreaming: false,
  };
};

// ========== 默认表格 ==========

const DEFAULT_TABLE_ID = 'sheet_default';
const DEFAULT_TABLE: TableData = {
  id: DEFAULT_TABLE_ID,
  title: 'Sheet1',
  position: { x: 0, y: 0 },
  size: { width: 800, height: 600 },
  schema: DEFAULT_SCHEMA,
  rows: [],  // 空行，等待用户填入或后端推送
  metadata: {},
  calibrationNotes: {},
  isStreaming: false,
};

// ========== Store ==========

export const useCanvasStore = create<CanvasState>((set) => ({
  // 初始状态：自带一个默认表格，避免"没有当前表格"问题
  tables: { [DEFAULT_TABLE_ID]: DEFAULT_TABLE },
  activeTableId: DEFAULT_TABLE_ID,
  isConnected: false,
  customerHighlightUntil: {},
  showCustomerModal: false,
  customerModalTableId: null,
  centerNotice: { visible: false, message: '', type: 'warning' },

  // 表格管理
  createTable: (options) => {
    const id = options?.id || `sheet_${Date.now()}`;
    const newTable = createDefaultTable(id, options);
    
    set((state) => ({
      tables: { ...state.tables, [id]: newTable },
      activeTableId: id,
    }));
    
    return id;
  },

  removeTable: (tableId) => {
    set((state) => {
      const { [tableId]: removed, ...rest } = state.tables;
      const remainingCount = Object.keys(rest).length;
      
      // 如果删除后没有表格了，自动创建一个新的默认表格
      if (remainingCount === 0) {
        const newId = `sheet_${Date.now()}`;
        const newTable = createDefaultTable(newId, { title: 'Sheet1', rows: [] });
        return {
          tables: { [newId]: newTable },
          activeTableId: newId,
        };
      }
      
      // 否则正常删除，切换到其他表格
      const newActiveId = state.activeTableId === tableId 
        ? Object.keys(rest)[0] 
        : state.activeTableId;
      
      return {
        tables: rest,
        activeTableId: newActiveId,
      };
    });
  },

  setActiveTable: (tableId) => {
    set({ activeTableId: tableId });
  },

  // 位置/大小 (虽然 Sheet 模式下不怎么用了，但为了兼容性保留)
  updateTablePosition: (tableId, position) => {
    set((state) => {
      const table = state.tables[tableId];
      if (!table) return state;
      return {
        tables: {
          ...state.tables,
          [tableId]: { ...table, position },
        },
      };
    });
  },

  updateTableSize: (tableId, size) => {
    set((state) => {
      const table = state.tables[tableId];
      if (!table) return state;
      return {
        tables: {
          ...state.tables,
          [tableId]: { ...table, size },
        },
      };
    });
  },

  // 数据操作
  appendRow: (tableId, row) => {
    set((state) => {
      const table = state.tables[tableId];
      if (!table) return state;
      return {
        tables: {
          ...state.tables,
          [tableId]: {
            ...table,
            rows: [...table.rows, row],
          },
        },
      };
    });
  },

  replaceRows: (tableId, rows, schema) => {
    set((state) => {
      const table = state.tables[tableId];
      if (!table) return state;
      return {
        tables: {
          ...state.tables,
          [tableId]: {
            ...table,
            rows,
            schema: schema || table.schema,
          },
        },
      };
    });
  },

  updateCell: (tableId, rowIndex, colKey, value) => {
    set((state) => {
      const table = state.tables[tableId];
      if (!table || !table.rows[rowIndex]) return state;
      
      const newRows = [...table.rows];
      newRows[rowIndex] = { ...newRows[rowIndex], [colKey]: value };
      
      return {
        tables: {
          ...state.tables,
          [tableId]: { ...table, rows: newRows },
        },
      };
    });
  },

  addRow: (tableId, row) => {
    set((state) => {
      const table = state.tables[tableId];
      if (!table) return state;
      
      // 如果没有提供 row，创建空行
      const newRow = row || table.schema.reduce((acc, col) => {
        acc[col.key] = col.type === 'number' ? 0 : '';
        return acc;
      }, {} as TableRow);
      
      return {
        tables: {
          ...state.tables,
          [tableId]: {
            ...table,
            rows: [...table.rows, newRow],
          },
        },
      };
    });
  },

  deleteRow: (tableId, rowIndex) => {
    set((state) => {
      const table = state.tables[tableId];
      if (!table) return state;
      
      const newRows = table.rows.filter((_, i) => i !== rowIndex);
      
      // 同时清理对应的校对备注
      const newNotes = { ...table.calibrationNotes };
      delete newNotes[rowIndex];
      // 调整后续行的索引
      Object.keys(newNotes).forEach((key) => {
        const idx = parseInt(key);
        if (idx > rowIndex) {
          newNotes[idx - 1] = newNotes[idx];
          delete newNotes[idx];
        }
      });
      
      return {
        tables: {
          ...state.tables,
          [tableId]: {
            ...table,
            rows: newRows,
            calibrationNotes: newNotes,
          },
        },
      };
    });
  },

  // Schema
  updateSchema: (tableId, schema) => {
    set((state) => {
      const table = state.tables[tableId];
      if (!table) return state;
      return {
        tables: {
          ...state.tables,
          [tableId]: { ...table, schema },
        },
      };
    });
  },

  updateMetadata: (tableId, metadata) => {
    set((state) => {
      const table = state.tables[tableId];
      if (!table) return state;
      return {
        tables: {
          ...state.tables,
          [tableId]: {
            ...table,
            metadata: { ...table.metadata, ...metadata },
          },
        },
      };
    });
  },

  // 校对
  setCalibrationNote: (tableId, rowIndex, note) => {
    set((state) => {
      const table = state.tables[tableId];
      if (!table) return state;
      return {
        tables: {
          ...state.tables,
          [tableId]: {
            ...table,
            calibrationNotes: {
              ...table.calibrationNotes,
              [rowIndex]: note,
            },
          },
        },
      };
    });
  },

  clearCalibrationNote: (tableId, rowIndex) => {
    set((state) => {
      const table = state.tables[tableId];
      if (!table) return state;
      
      const newNotes = { ...table.calibrationNotes };
      delete newNotes[rowIndex];
      
      return {
        tables: {
          ...state.tables,
          [tableId]: { ...table, calibrationNotes: newNotes },
        },
      };
    });
  },

  // 流式状态
  setStreaming: (tableId, isStreaming) => {
    set((state) => {
      const table = state.tables[tableId];
      if (!table) return state;
      return {
        tables: {
          ...state.tables,
          [tableId]: { ...table, isStreaming },
        },
      };
    });
  },

  // 连接状态
  setConnected: (isConnected) => {
    set({ isConnected });
  },

  // UI - 客户选择高亮
  highlightCustomerSelect: (tableId, durationMs = 3000) => {
    const until = Date.now() + durationMs;
    set((state) => ({
      customerHighlightUntil: { ...state.customerHighlightUntil, [tableId]: until },
    }));

    // 到期自动清理（容错：若期间再次触发，以最新 until 为准）
    setTimeout(() => {
      set((state) => {
        const current = state.customerHighlightUntil[tableId] || 0;
        if (current > Date.now()) return state;
        const next = { ...state.customerHighlightUntil };
        delete next[tableId];
        return { customerHighlightUntil: next };
      });
    }, durationMs + 50);
  },

  // UI - "请选择客户" 全局弹窗
  openCustomerModal: (tableId) => {
    set({ showCustomerModal: true, customerModalTableId: tableId });
  },
  closeCustomerModal: () => {
    set({ showCustomerModal: false, customerModalTableId: null });
  },

  showCenterNotice: (message, type = 'warning') => {
    set({ centerNotice: { visible: true, message, type } });
  },
  hideCenterNotice: () => {
    set({ centerNotice: { visible: false, message: '', type: 'warning' } });
  },

  // 批量操作
  clearAll: () => {
    set({ tables: {}, activeTableId: null });
  },

  importTables: (tables) => {
    set({ tables });
  },

  resetCustomers: (tableIds: string[]) => {
    set((state) => {
      const newTables = { ...state.tables };
      
      tableIds.forEach((id) => {
        if (newTables[id]) {
          newTables[id] = {
            ...newTables[id],
            metadata: {
              ...newTables[id].metadata,
              customerId: '',
              customer: '',
              restaurantId: '',
              restaurant: '',
              orderTypeId: '',
              orderType: '',
            },
          };
        }
      });
      
      return { tables: newTables };
    });
  },
}));
