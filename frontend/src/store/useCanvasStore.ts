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
  calibrationNotes: Record<number, string>;  // rowIndex -> note
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
  
  // Actions - 批量操作
  clearAll: () => void;
  importTables: (tables: Record<string, TableData>) => void;
}

// ========== 基础模板（与后端一致） ==========

const DEFAULT_SCHEMA: ColumnSchema[] = [
  { key: '品名', title: '品名', type: 'text' },
  { key: '数量', title: '数量', type: 'number' },
  { key: '规格', title: '规格', type: 'text' },
  { key: '单价', title: '单价', type: 'number' },
  { key: '总价', title: '总价', type: 'number' },
];

const createDefaultTable = (id: string, options?: Partial<TableData>): TableData => {
  const schema = options?.schema || DEFAULT_SCHEMA;
  
  // 确保至少有一行数据，避免 react-datasheet-grid 空数据 bug
  const defaultRow = schema.reduce((acc, col) => {
    acc[col.key] = col.type === 'number' ? 0 : '';
    return acc;
  }, {} as TableRow);
  
  return {
    id,
    title: options?.title || '新表格',
    position: options?.position || { x: 100, y: 100 },
    size: options?.size || { width: 600, height: 400 },
    schema,
    rows: options?.rows?.length ? options.rows : [defaultRow],
    metadata: options?.metadata || {},
    calibrationNotes: {},
    isStreaming: false,
  };
};

// ========== Store ==========

export const useCanvasStore = create<CanvasState>((set) => ({
  // 初始状态
  tables: {},
  activeTableId: null,
  isConnected: false,

  // 表格管理
  createTable: (options) => {
    const id = options?.id || `table_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
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
      return {
        tables: rest,
        activeTableId: state.activeTableId === tableId ? null : state.activeTableId,
      };
    });
  },

  setActiveTable: (tableId) => {
    set({ activeTableId: tableId });
  },

  // 位置/大小
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

  // 批量操作
  clearAll: () => {
    set({ tables: {}, activeTableId: null });
  },

  importTables: (tables) => {
    set({ tables });
  },
}));

