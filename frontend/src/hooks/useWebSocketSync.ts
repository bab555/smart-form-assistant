/**
 * WebSocket 事件同步 Hook
 * 
 * 将后端推送的事件同步到 CanvasStore
 */

import { useEffect, useCallback } from 'react';
import { wsClient } from '@/services/websocket';
import { EventType } from '@/services/protocol';
import { useCanvasStore } from '@/store/useCanvasStore';
import { toast } from '@/components/Toast';

export function useWebSocketSync() {
  // 从 store 获取操作方法
  const createTable = useCanvasStore((state) => state.createTable);
  const appendRow = useCanvasStore((state) => state.appendRow);
  const replaceRows = useCanvasStore((state) => state.replaceRows);
  const updateCell = useCanvasStore((state) => state.updateCell);
  const addRow = useCanvasStore((state) => state.addRow);
  const deleteRow = useCanvasStore((state) => state.deleteRow);
  const setCalibrationNote = useCanvasStore((state) => state.setCalibrationNote);
  const updateMetadata = useCanvasStore((state) => state.updateMetadata);
  const setStreaming = useCanvasStore((state) => state.setStreaming);
  const setConnected = useCanvasStore((state) => state.setConnected);

  // 处理 CONNECTION_ACK
  const handleConnectionAck = useCallback(() => {
    console.log('[Sync] Connected');
    setConnected(true);
  }, [setConnected]);

  // 处理 TABLE_CREATE
  const handleTableCreate = useCallback((data: any) => {
    console.log('[Sync] Table create:', data);
    const tableId = createTable({
      id: data.table_id,
      title: data.title || '导入数据',
      schema: data.schema,
      rows: data.rows || [],
      position: data.position,
      metadata: data.metadata,
    });
    setStreaming(tableId, true);
  }, [createTable, setStreaming]);

  // 处理 ROW_COMPLETE
  const handleRowComplete = useCallback((data: any) => {
    const { table_id, row } = data;
    console.log('[Sync] Row complete:', table_id, row);
    
    if (table_id && row) {
      // 如果表格不存在，先创建
      const tables = useCanvasStore.getState().tables;
      if (!tables[table_id]) {
        createTable({
          id: table_id,
          title: '导入数据',
        });
        setStreaming(table_id, true);
      }
      appendRow(table_id, row);
    }
  }, [createTable, appendRow, setStreaming]);

  // 处理 TABLE_REPLACE
  const handleTableReplace = useCallback((data: any) => {
    const { table_id, rows, schema } = data;
    console.log('[Sync] Table replace:', table_id, rows?.length);
    
    if (table_id && rows) {
      replaceRows(table_id, rows, schema);
    }
  }, [replaceRows]);

  // 处理 CELL_UPDATE
  const handleCellUpdate = useCallback((data: any) => {
    const { table_id, row_index, col_key, value } = data;
    console.log('[Sync] Cell update:', table_id, row_index, col_key, value);
    
    if (table_id !== undefined && row_index !== undefined && col_key) {
      updateCell(table_id, row_index, col_key, value);
    }
  }, [updateCell]);

  // 处理 CALIBRATION_NOTE
  const handleCalibrationNote = useCallback((data: any) => {
    const { table_id, row_index, note } = data;
    console.log('[Sync] Calibration note:', table_id, row_index, note);
    
    if (table_id && row_index !== undefined && note) {
      setCalibrationNote(table_id, row_index, note);
    }
  }, [setCalibrationNote]);

  // 处理 TABLE_METADATA
  const handleTableMetadata = useCallback((data: any) => {
    const { table_id, ...metadata } = data;
    console.log('[Sync] Table metadata:', table_id, metadata);
    
    if (table_id) {
      updateMetadata(table_id, metadata);
    }
  }, [updateMetadata]);

  // 处理 TOOL_CALL (Agent 工具调用)
  const handleToolCall = useCallback((data: any) => {
    const { tool, params } = data;
    console.log('[Sync] Tool call:', tool, params);
    
    // create_table 不需要 activeTableId
    if (tool === 'create_table') {
      createTable({
        id: params.table_id,
        title: params.title || '新表格',
        schema: params.schema,
        rows: params.data,
      });
      return;
    }
    
    // 获取当前活动表格
    const { activeTableId } = useCanvasStore.getState();
    const tableId = params?.table_id || activeTableId;
    
    if (!tableId) {
      console.warn('[Sync] No active table for tool call');
      return;
    }

    switch (tool) {
      case 'update_cell':
        if (params.row_index !== undefined && params.key && params.value !== undefined) {
          updateCell(tableId, params.row_index, params.key, params.value);
        }
        break;
      case 'add_row':
        addRow(tableId, params.data);
        break;
      case 'delete_row':
        if (params.row_index !== undefined) {
          deleteRow(tableId, params.row_index);
        }
        break;
      default:
        console.warn('[Sync] Unknown tool:', tool);
    }
  }, [createTable, updateCell, addRow, deleteRow]);

  // 处理 TASK_START
  const handleTaskStart = useCallback((data: any) => {
    const { table_id } = data;
    console.log('[Sync] Task start:', data);
    
    if (table_id) {
      setStreaming(table_id, true);
    }
  }, [setStreaming]);

  // 处理 TASK_FINISH
  const handleTaskFinish = useCallback((data: any) => {
    const { table_id } = data;
    console.log('[Sync] Task finish:', data);
    
    if (table_id) {
      setStreaming(table_id, false);
    }
  }, [setStreaming]);

  // 处理 ERROR
  const handleError = useCallback((data: any) => {
    console.error('[Sync] Error:', JSON.stringify(data, null, 2));
    
    // 尝试提取错误信息
    let message = '发生未知错误';
    if (typeof data === 'string') {
      message = data;
    } else if (data) {
      message = data.msg || data.message || data.error || data.detail || JSON.stringify(data);
    }
    
    toast.error(`任务失败: ${message}`);
  }, []);

  // 初始化连接和事件监听
  useEffect(() => {
    // 连接 WebSocket
    wsClient.connect().catch((e) => {
      console.error('[Sync] Connect failed:', e);
    });

    // 注册事件处理器
    const unsubscribers = [
      wsClient.on(EventType.CONNECTION_ACK, handleConnectionAck),
      wsClient.on(EventType.TABLE_CREATE, handleTableCreate),
      wsClient.on(EventType.ROW_COMPLETE, handleRowComplete),
      wsClient.on(EventType.TABLE_REPLACE, handleTableReplace),
      wsClient.on(EventType.CELL_UPDATE, handleCellUpdate),
      wsClient.on(EventType.CALIBRATION_NOTE, handleCalibrationNote),
      wsClient.on(EventType.TABLE_METADATA, handleTableMetadata),
      wsClient.on(EventType.TOOL_CALL, handleToolCall),
      wsClient.on(EventType.TASK_START, handleTaskStart),
      wsClient.on(EventType.TASK_FINISH, handleTaskFinish),
      wsClient.on(EventType.ERROR, handleError),
    ];

    // 处理断连
    const handleDisconnect = () => {
      setConnected(false);
    };
    
    // 监听 window 的 offline 事件
    window.addEventListener('offline', handleDisconnect);

    // 清理
    return () => {
      unsubscribers.forEach((unsub) => unsub());
      window.removeEventListener('offline', handleDisconnect);
    };
  }, [
    handleConnectionAck,
    handleTableCreate,
    handleRowComplete,
    handleTableReplace,
    handleCellUpdate,
    handleCalibrationNote,
    handleTableMetadata,
    handleToolCall,
    handleTaskStart,
    handleTaskFinish,
    handleError,
    setConnected,
  ]);

  return {
    isConnected: useCanvasStore((state) => state.isConnected),
    clientId: wsClient.clientId,
  };
}

