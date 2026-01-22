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
import { useDataStore } from '@/store/useDataStore';
import { useAuthStore } from '@/store/useAuthStore';
import { AlertTriangle, Loader2, X, Plus, Download, Calendar, User, Store, ClipboardList, AlertCircle, Send, Settings, Trash2 } from 'lucide-react';
import { exportTableToExcel, exportAllTablesToExcel } from '@/utils/export';
import { ContextMenu, MenuItem } from './ContextMenu';
import { wsClient } from '@/services/websocket';
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
        删除
      </button>
    </div>
  );
};

// "订单商品"单元格渲染器
// - exact: 直接显示
// - fuzzy: 显示⚠️ + 最接近结果，点击弹窗
// - not_found: 显示"库中没有该商品"
const OrderProductCellRenderer: React.FC<ICellRendererParams & { 
  tableId: string; 
  customerId?: string; 
  onRequireCustomer: () => void;
  onOpenProductPicker: (rowIndex: number) => void;
}> = (props) => {
  const rowIndex = props.rowIndex;
  const row = (props.data || {}) as any;
  const status = row.__order_status as string | undefined;
  const fuzzyMatch = (row.__fuzzy_match || '') as string;
  const value = (row['订单商品'] || '') as string;
  const calibrationHint = (row.__calibration_hint || '') as string;

  // 未选客户：不允许编辑/选择
  const disabled = !props.customerId;

  // 统一：不论是否精确/模糊/无匹配，都允许点开弹窗（弹窗展示完整商品库名称列表）
  return (
    <div
      className={`order-product-clickable ${status === 'fuzzy' ? 'order-fuzzy-cell' : ''} ${status === 'not_found' ? 'order-not-found' : ''} ${disabled ? 'disabled' : ''}`}
      onClick={(e) => {
        e.stopPropagation();
        if (disabled) return props.onRequireCustomer();
        props.onOpenProductPicker(rowIndex);
      }}
      title="点击从完整商品库中选择"
    >
      {status === 'fuzzy' && <span className="fuzzy-warning">⚠️</span>}
      <span className="fuzzy-text">
        {status === 'fuzzy'
          ? (fuzzyMatch || value || '待确认')
          : status === 'not_found'
            ? (calibrationHint || '库中没有该商品')
            : (value || '（点击选择商品）')}
      </span>
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
  const customerHighlightUntil = useCanvasStore((state) => state.customerHighlightUntil);
  const openCustomerModal = useCanvasStore((state) => state.openCustomerModal);
  
  // 动态数据（从远端 API 加载）
  const partners = useDataStore((state) => state.partners);
  const restaurants = useDataStore((state) => state.restaurants);
  const orderTypes = useDataStore((state) => state.orderTypes);
  const loadRestaurants = useDataStore((state) => state.loadRestaurants);
  const loadOrderTypes = useDataStore((state) => state.loadOrderTypes);
  const syncProducts = useDataStore((state) => state.syncProducts);
  
  // 右键菜单状态
  const [contextMenu, setContextMenu] = useState<{ isOpen: boolean; x: number; y: number }>({
    isOpen: false,
    x: 0,
    y: 0,
  });
  
  // 删除行确认弹窗
  const [deletingRowIndex, setDeletingRowIndex] = useState<number | null>(null);
  // "替换为订单商品"弹窗
  const [applyingRowIndex, setApplyingRowIndex] = useState<number | null>(null);
  // 商品选择弹窗（点击商品 / 添加新商品）
  // mode: 'edit' 编辑现有行, 'add' 新增商品
  const [productPickerState, setProductPickerState] = useState<{
    isOpen: boolean;
    rowIndex: number;
    mode: 'edit' | 'add';
  }>({ isOpen: false, rowIndex: -1, mode: 'edit' });

  // 商品库名称列表（全量）
  const [productNames, setProductNames] = useState<string[]>([]);
  const [productNamesLoading, setProductNamesLoading] = useState(false);
  const [productSearch, setProductSearch] = useState('');

  // 偏好编辑弹窗
  const [preferenceEditorOpen, setPreferenceEditorOpen] = useState(false);
  const [preferences, setPreferences] = useState<Array<{ recognized: string; order_product: string }>>([]);
  const [preferencesLoading, setPreferencesLoading] = useState(false);
  const [preferenceSearch, setPreferenceSearch] = useState('');

  const normalize = useCallback((s: string) => s.trim().toLowerCase().replace(/\s+/g, ''), []);

  const fuzzyScore = useCallback((text: string, query: string) => {
    // 简单模糊匹配评分：
    // - 完全相等：1000
    // - 包含：700 - index
    // - 子序列匹配（按顺序包含每个字符）：最多 500 - gap
    const t = normalize(text);
    const q = normalize(query);
    if (!q) return 1;
    if (t === q) return 1000;
    const idx = t.indexOf(q);
    if (idx >= 0) return 700 - Math.min(idx, 200);

    // 子序列
    let ti = 0;
    let matched = 0;
    let first = -1;
    let last = -1;
    for (let qi = 0; qi < q.length; qi++) {
      const ch = q[qi];
      let found = false;
      while (ti < t.length) {
        if (t[ti] === ch) {
          found = true;
          if (first < 0) first = ti;
          last = ti;
          ti += 1;
          break;
        }
        ti += 1;
      }
      if (!found) return 0;
      matched += 1;
    }
    const span = first >= 0 && last >= 0 ? (last - first + 1) : 9999;
    const gaps = span - matched;
    return Math.max(0, 500 - Math.min(gaps, 500));
  }, [normalize]);

  const filteredProductNames = useMemo(() => {
    const q = productSearch.trim();
    if (!q) return productNames.slice(0, 500);
    const scored = productNames
      .map((name) => ({ name, score: fuzzyScore(name, q) }))
      .filter((x) => x.score > 0)
      .sort((a, b) => b.score - a.score || a.name.length - b.name.length);
    return scored.slice(0, 500).map((x) => x.name);
  }, [productNames, productSearch, fuzzyScore]);

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

  // 删除行（显示确认弹窗）
  const handleDeleteRowRequest = useCallback((rowIndex: number) => {
    if (!table.metadata.customerId) {
      openCustomerModal(table.id);
      return;
    }
    // 如果只剩一行，不允许删除
    if (table.rows.length <= 1) {
      return;
    }
    setDeletingRowIndex(rowIndex);
  }, [table.rows.length, table.metadata.customerId, table.id, openCustomerModal]);

  const handleApplyOrderRequest = useCallback((rowIndex: number) => {
    if (!table.metadata.customerId) {
      openCustomerModal(table.id);
      return;
    }
    setApplyingRowIndex(rowIndex);
  }, [table.id, table.metadata.customerId, openCustomerModal]);

  // 确认删除行
  const confirmDeleteRow = useCallback(() => {
    if (deletingRowIndex !== null) {
      deleteRow(table.id, deletingRowIndex);
      setDeletingRowIndex(null);
    }
  }, [table.id, deletingRowIndex, deleteRow]);

  const closeApplyModal = useCallback(() => setApplyingRowIndex(null), []);

  // 打开商品选择弹窗（点击感叹号）
  const ensureProductNamesLoaded = useCallback(async () => {
    if (productNames.length > 0 || productNamesLoading) return;
    setProductNamesLoading(true);
    try {
      const resp = await fetch('/api/products/names');
      if (!resp.ok) throw new Error('获取商品库失败');
      const names = await resp.json();
      if (Array.isArray(names)) setProductNames(names.map((x) => String(x)));
    } catch {
      // ignore: modal 内提示
      setProductNames([]);
    } finally {
      setProductNamesLoading(false);
    }
  }, [productNames.length, productNamesLoading]);

  const openProductPicker = useCallback((rowIndex: number, mode: 'edit' | 'add' = 'edit') => {
    setProductSearch('');
    setProductPickerState({ isOpen: true, rowIndex, mode });
    void ensureProductNamesLoaded();
  }, [ensureProductNamesLoaded]);

  // 添加新商品（打开商品选择弹窗）
  const handleAddProduct = useCallback((e?: React.MouseEvent) => {
    e?.stopPropagation();
    openProductPicker(-1, 'add');
  }, [openProductPicker]);

  // 关闭商品选择弹窗
  const closeProductPicker = useCallback(() => {
    setProductPickerState({ isOpen: false, rowIndex: -1, mode: 'edit' });
  }, []);

  // 打开偏好编辑器
  const openPreferenceEditor = useCallback(async () => {
    if (!table.metadata.customerId) {
      openCustomerModal(table.id);
      return;
    }
    setPreferenceSearch('');
    setPreferencesLoading(true);
    setPreferenceEditorOpen(true);
    try {
      const resp = await fetch(`/api/preferences/${encodeURIComponent(table.metadata.customerId)}`);
      if (!resp.ok) throw new Error('获取偏好失败');
      const data = await resp.json();
      setPreferences(data.preferences || []);
    } catch (err) {
      console.error('获取偏好失败:', err);
      setPreferences([]);
    } finally {
      setPreferencesLoading(false);
    }
  }, [table.metadata.customerId, table.id, openCustomerModal]);

  // 关闭偏好编辑器
  const closePreferenceEditor = useCallback(() => {
    setPreferenceEditorOpen(false);
    setPreferences([]);
  }, []);

  // 保存偏好
  const savePreferences = useCallback(async () => {
    if (!table.metadata.customerId) return;
    try {
      const resp = await fetch(`/api/preferences/${encodeURIComponent(table.metadata.customerId)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preferences),
      });
      if (!resp.ok) throw new Error('保存失败');
      closePreferenceEditor();
    } catch (err) {
      console.error('保存偏好失败:', err);
      alert('保存偏好失败，请重试');
    }
  }, [table.metadata.customerId, preferences, closePreferenceEditor]);

  // 添加新偏好
  const addPreference = useCallback(() => {
    setPreferences(prev => [...prev, { recognized: '', order_product: '' }]);
  }, []);

  // 删除偏好
  const deletePreference = useCallback((index: number) => {
    setPreferences(prev => prev.filter((_, i) => i !== index));
  }, []);

  // 更新偏好
  const updatePreference = useCallback((index: number, field: 'recognized' | 'order_product', value: string) => {
    setPreferences(prev => prev.map((item, i) => 
      i === index ? { ...item, [field]: value } : item
    ));
  }, []);

  // 过滤后的偏好列表
  const filteredPreferences = useMemo(() => {
    const q = preferenceSearch.trim().toLowerCase();
    if (!q) return preferences;
    return preferences.filter(p => 
      p.recognized.toLowerCase().includes(q) || 
      p.order_product.toLowerCase().includes(q)
    );
  }, [preferences, preferenceSearch]);

  // 选择商品（商品选择弹窗中用户选择后）
  const handleProductSelect = useCallback((selectedProduct: string) => {
    const { rowIndex, mode } = productPickerState;
    
    if (mode === 'add') {
      // 新增商品模式：添加一行新数据
      // 计算新的序号（当前最大序号 + 1）
      const maxSeq = table.rows.reduce((max, row) => {
        const seq = Number(row['序号']) || 0;
        return Math.max(max, seq);
      }, 0);
      
      // 创建新行（序号、识别商品、订单商品 填入选择的商品名）
      const newRow: Record<string, unknown> = {
        '序号': maxSeq + 1,
        '识别商品': selectedProduct,
        '订单商品': selectedProduct,
        '数量': 1,
        '单位': '',
        '规格': '',
        '备注': '',
        __order_status: 'exact',
        __order_candidates: [],
        __order_selected: '',
        __goods_id: '', // 初始化为空，等待后端返回
      };
      
      addRow(table.id, newRow);
      
      // 同时请求后端获取该商品的规格/单位信息
      wsClient.send('apply_order_product', {
        table_id: table.id,
        row_index: table.rows.length, // 新行的索引
        mode: 'A',
        recognized: selectedProduct,
        selected: selectedProduct,
        order_value: selectedProduct,
        customer_id: table.metadata.customerId || '',
      });
    } else {
      // 编辑现有行模式
      if (rowIndex < 0) return;
      
      const row = table.rows[rowIndex] as any;
      const recognized = (row?.['识别商品'] || '').toString();
      
      // 发送请求，让后端覆盖 订单商品、规格、单位 + 记录偏好
      wsClient.send('apply_order_product', {
        table_id: table.id,
        row_index: rowIndex,
        mode: 'A', // 默认记录偏好
        recognized,
        selected: selectedProduct,
        order_value: selectedProduct,
        customer_id: table.metadata.customerId || '',
      });
    }
    
    closeProductPicker();
  }, [productPickerState, table.id, table.metadata.customerId, table.rows, closeProductPicker, addRow]);

  const confirmApplyOrder = useCallback(async (mode: 'A' | 'B' | 'C') => {
    if (applyingRowIndex === null) return;
    if (mode === 'C') {
      closeApplyModal();
      return;
    }
    const row = table.rows[applyingRowIndex] as any;
    const recognized = (row?.['识别商品'] || '').toString();
    const selected = (row?.__order_selected || '').toString();
    const orderValue = (row?.['订单商品'] || '').toString();

    wsClient.send('apply_order_product', {
      table_id: table.id,
      row_index: applyingRowIndex,
      mode,
      recognized,
      selected,
      order_value: orderValue,
      customer_id: table.metadata.customerId || '',
    });

    closeApplyModal();
  }, [applyingRowIndex, closeApplyModal, table.id, table.metadata.customerId, table.rows]);

  // 导出所有
  const handleExportAll = useCallback(() => {
    if (!table.metadata.customerId) {
      openCustomerModal(table.id);
      return;
    }
    exportAllTablesToExcel(tables);
  }, [tables, table.id, table.metadata.customerId, openCustomerModal]);

  // 关闭当前 Sheet（不再限制客户选择）
  const handleCloseSheet = useCallback(() => {
    if (onCloseRequest) {
      onCloseRequest(table.id);
    }
  }, [table.id, onCloseRequest]);
  
  // 导出
  const handleExport = useCallback((e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (!table.metadata.customerId) {
      openCustomerModal(table.id);
      return;
    }
    exportTableToExcel(table);
  }, [table, openCustomerModal]);

  // 元数据变更
  const handleClientChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const clientId = e.target.value;
    const client = partners.find(c => c.id === clientId);
    // 选择客户后，清空餐厅和订单类型
    updateMetadata(table.id, { 
      customerId: clientId, 
      customer: client ? client.name : '',
      restaurantId: '',
      restaurant: '',
      orderTypeId: '',
      orderType: '',
    });

    // 如果是配送商模式（需要选择客户），选择客户后重新加载关联数据
    if (clientId) {
        // 并行加载
        void loadRestaurants(clientId);
        void loadOrderTypes(clientId);
        // 自动触发商品库同步（或者检查是否需要同步）
        // 这里为了简化流程，自动触发同步（或者可以加个按钮让用户点）
        // 考虑到用户抱怨"商品库没有取到"，这里自动同步一下比较保险
        void syncProducts(clientId);
    }
  };

  const handleRestaurantChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const restaurantId = e.target.value;
    const restaurant = restaurants.find(r => r.id === restaurantId);
    updateMetadata(table.id, { 
      restaurantId, 
      restaurant: restaurant ? restaurant.name : '' 
    });
  };

  const handleOrderTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const orderTypeId = e.target.value;
    const orderType = orderTypes.find(o => o.id === orderTypeId);
    updateMetadata(table.id, { 
      orderTypeId, 
      orderType: orderType ? orderType.name : '' 
    });
  };

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateMetadata(table.id, { date: e.target.value });
  };

  // 检查表格是否有未处理的商品（需要选择的行）
  const checkUnprocessedRows = useCallback((rows: TableRow[]) => {
    const unprocessed: number[] = [];
    rows.forEach((row, index) => {
      const status = (row as Record<string, unknown>).__order_status;
      // 如果状态不是 'exact'（精确匹配），说明需要用户处理
      if (status && status !== 'exact') {
        unprocessed.push(index + 1); // 行号从1开始显示
      }
    });
    return unprocessed;
  }, []);

  // 准备提交数据：用"订单商品"覆盖，提取需要的字段
  const prepareSubmitData = useCallback((rows: TableRow[]) => {
    return rows.map((row) => {
      const r = row as Record<string, unknown>;
      return {
        goodsId: r['__goods_id'], // 必须包含商品ID
        quantity: r['数量'] || 0,
        unit: r['单位'] || '',
        remark: r['备注'] || '',
      };
    });
  }, []);

  // 提交当前订单
  const handleSubmitCurrent = useCallback(async () => {
    if (!table.metadata.customerId) {
      openCustomerModal(table.id);
      return;
    }
    
    // 检查是否有未处理的行
    const unprocessed = checkUnprocessedRows(table.rows);
    if (unprocessed.length > 0) {
      alert(`以下行的商品尚未确认，请先处理：\n第 ${unprocessed.join('、')} 行\n\n请点击对应行的商品进行选择确认。`);
      return;
    }

    // 检查元数据完整性
    if (!table.metadata.restaurantId) {
      alert('请选择餐厅');
      return;
    }
    if (!table.metadata.orderTypeId) {
      alert('请选择订单类型');
      return;
    }
    
    // 准备提交数据
    const items = prepareSubmitData(table.rows);
    const submitPayload = {
      partnerId: table.metadata.customerId,
      restaurantId: table.metadata.restaurantId,
      orderTypeId: table.metadata.orderTypeId,
      date: table.metadata.date?.split('T')[0] || new Date().toISOString().split('T')[0], // YYYY-MM-DD
      items: items,
    };
    
    console.log('提交当前订单数据:', submitPayload);
    
    try {
      // 获取 Token
      const token = useAuthStore.getState().token;
      if (!token) {
        alert('未登录或登录已过期');
        return;
      }

      const response = await fetch('/api/order/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(submitPayload)
      });

      const result = await response.json();
      
      if (result.success) {
        alert(`订单提交成功！\n订单ID: ${result.orderId}\n单号: ${result.tradeNo}`);
      } else {
        alert(`提交失败: ${result.message}`);
      }
    } catch (error) {
      console.error('Submit error:', error);
      alert('提交请求失败，请检查网络');
    }

  }, [table.id, table.metadata, table.rows, openCustomerModal, checkUnprocessedRows, prepareSubmitData]);

  // 提交所有订单
  const handleSubmitAll = useCallback(async () => {
    if (!table.metadata.customerId) {
      openCustomerModal(table.id);
      return;
    }
    
    // 检查所有表格是否有未处理的行
    const allUnprocessed: { tableTitle: string; rows: number[] }[] = [];
    Object.values(tables).forEach((t) => {
      const unprocessed = checkUnprocessedRows(t.rows);
      if (unprocessed.length > 0) {
        allUnprocessed.push({
          tableTitle: t.title || t.id,
          rows: unprocessed,
        });
      }
    });
    
    if (allUnprocessed.length > 0) {
      const msg = allUnprocessed
        .map((u) => `【${u.tableTitle}】第 ${u.rows.join('、')} 行`)
        .join('\n');
      alert(`以下表格存在未确认的商品：\n${msg}\n\n请先处理完毕再提交。`);
      return;
    }
    
    // 逐个提交（串行，避免并发问题）
    let successCount = 0;
    let failCount = 0;
    const token = useAuthStore.getState().token;
    
    if (!token) {
        alert('未登录或登录已过期');
        return;
    }

    for (const t of Object.values(tables)) {
        // 简单校验元数据
        if (!t.metadata.restaurantId || !t.metadata.orderTypeId) {
            alert(`表格 ${t.title || t.id} 缺少餐厅或订单类型，跳过提交`);
            failCount++;
            continue;
        }

        const items = prepareSubmitData(t.rows);
        const submitPayload = {
            partnerId: t.metadata.customerId,
            restaurantId: t.metadata.restaurantId,
            orderTypeId: t.metadata.orderTypeId,
            date: t.metadata.date?.split('T')[0] || new Date().toISOString().split('T')[0],
            items: items,
        };

        try {
            const response = await fetch('/api/order/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(submitPayload)
            });
            const result = await response.json();
            if (result.success) {
                successCount++;
            } else {
                console.error(`表格 ${t.title} 提交失败:`, result.message);
                failCount++;
            }
        } catch (e) {
            console.error(`表格 ${t.title} 提交异常:`, e);
            failCount++;
        }
    }
    
    alert(`批量提交完成\n成功: ${successCount}\n失败: ${failCount}`);

  }, [table.id, table.metadata.customerId, tables, openCustomerModal, checkUnprocessedRows, prepareSubmitData]);

  // 获取餐厅和订单类型列表（现在是全局列表，不再按客户分组）
  const currentRestaurants = restaurants;
  const currentOrderTypes = orderTypes;

  // 列定义
  const columnDefs: ColDef<TableRow>[] = useMemo(() => {
    // 数据列
    const dataCols = table.schema.map((col, index) => {
      const isNumber = col.type === 'number';
      const isLastDataCol = index === table.schema.length - 1;
      const isOrderProduct = col.key === '订单商品';
      return {
        field: col.key,
        headerName: col.title,
        editable: !isOrderProduct, // 订单商品使用自定义渲染（内部输入框/单选）
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
        // 如果是"订单商品"列（校对结果），给予特殊样式 + 自定义渲染
        cellStyle: isOrderProduct ? { color: '#2563eb', fontWeight: 500 } : undefined,
        ...(isOrderProduct
          ? {
              cellRenderer: OrderProductCellRenderer,
              autoHeight: true,
              cellRendererParams: {
                tableId: table.id,
                customerId: table.metadata.customerId,
                onRequireCustomer: () => {
                  openCustomerModal(table.id);
                },
                onOpenProductPicker: openProductPicker,
              },
            }
          : {}),
      } as ColDef<TableRow>;
    });
    
    // 操作列
    const actionCol: ColDef<TableRow> = {
      headerName: '',
      field: '__actions__',
      width: 86,
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
  }, [table.schema, table.id, table.metadata.customerId, handleDeleteRowRequest, handleApplyOrderRequest, openCustomerModal, openProductPicker]);

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
    // 编辑单元格不再限制客户选择（用户可自由编辑，提交/下载时再校验客户）
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
      label: '添加新商品',
      icon: <Plus size={14} />,
      onClick: () => handleAddProduct(),
    },
    {
      label: '删除选中行',
      icon: <X size={14} />,
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
  ], [table.id, table.rows.length, handleAddProduct, handleDeleteRowRequest, handleExport, handleExportAll, handleCloseSheet]);

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

      {/* "替换为订单商品"弹窗（A/B/C） */}
      {applyingRowIndex !== null && (
        <div className="confirm-modal-overlay">
          <div className="confirm-modal-backdrop" onClick={closeApplyModal} />
          <div className="confirm-modal">
            <div className="confirm-header">
              <AlertTriangle size={20} className="icon-warning" />
              <span>自动填入订单商品信息</span>
            </div>
            <div className="confirm-body">
              <p>将使用商品库中的规格/单位覆盖当前行（数量不变）。</p>
              <p className="confirm-hint">A 会记录该客户的"识别商品→订单商品"偏好，用于后续校对增强。</p>
            </div>
            <div className="confirm-footer">
              <button className="btn-primary" onClick={() => confirmApplyOrder('A')}>A：储存偏好并填入</button>
              <button className="btn-secondary" onClick={() => confirmApplyOrder('B')}>B：不储存填入</button>
              <button className="btn-cancel" onClick={() => confirmApplyOrder('C')}>C：取消</button>
            </div>
          </div>
        </div>
      )}

      {/* 商品选择弹窗（选择/添加商品） */}
      {productPickerState.isOpen && (
        <div className="confirm-modal-overlay product-picker-overlay">
          <div className="confirm-modal-backdrop" onClick={closeProductPicker} />
        <div className="product-picker-modal large">
            <div className="confirm-header">
              <Plus size={20} className="icon-primary" />
              <span>{productPickerState.mode === 'add' ? '添加新商品' : '选择商品'}</span>
            </div>
            <div className="product-picker-body">
              <p className="picker-hint">
                {productPickerState.mode === 'add' 
                  ? '从商品库中选择要添加的商品，选择后自动添加一行：' 
                  : '从完整商品库中搜索并选择正确的商品：'}
              </p>
              <input
                className="picker-search"
                placeholder="搜索商品名..."
                value={productSearch}
                onChange={(e) => setProductSearch(e.target.value)}
              />
              {productNamesLoading ? (
                <div className="picker-loading">加载商品库中...</div>
              ) : filteredProductNames.length === 0 ? (
                <div className="product-empty">没有匹配到商品，请换个关键词试试</div>
              ) : (
                <div className="product-grid">
                  {filteredProductNames.map((product, index) => (
                    <button
                      key={`${product}_${index}`}
                      className="product-chip"
                      onClick={() => handleProductSelect(product)}
                      title={product}
                    >
                      {product}
                    </button>
                  ))}
                </div>
              )}
              <p className="picker-note">
                {productPickerState.mode === 'add' 
                  ? '选择后将自动添加一行新商品（自动递增序号）。' 
                  : '选择后将自动覆盖「识别商品」「规格」「单位」并记录偏好。'}
              </p>
            </div>
            <div className="confirm-footer">
              <button className="btn-cancel" onClick={closeProductPicker}>取消</button>
            </div>
          </div>
        </div>
      )}

      {/* 偏好编辑弹窗 */}
      {preferenceEditorOpen && (
        <div className="confirm-modal-overlay preference-editor-overlay">
          <div className="confirm-modal-backdrop" onClick={closePreferenceEditor} />
          <div className="preference-editor-modal">
            <div className="confirm-header">
              <Settings size={20} className="icon-primary" />
              <span>编辑偏好映射</span>
            </div>
            <div className="preference-editor-body">
              <p className="picker-hint">
                管理「识别商品 → 订单商品」的偏好映射，系统会根据此映射自动校正识别结果。
              </p>
              <div className="preference-toolbar">
                <input
                  className="picker-search"
                  placeholder="搜索偏好..."
                  value={preferenceSearch}
                  onChange={(e) => setPreferenceSearch(e.target.value)}
                />
                <button className="btn-add-pref" onClick={addPreference}>
                  <Plus size={14} />
                  添加
                </button>
              </div>
              {preferencesLoading ? (
                <div className="picker-loading">加载偏好中...</div>
              ) : filteredPreferences.length === 0 && !preferenceSearch ? (
                <div className="preference-empty">暂无偏好记录，点击"添加"创建新偏好</div>
              ) : filteredPreferences.length === 0 ? (
                <div className="preference-empty">没有匹配的偏好</div>
              ) : (
                <div className="preference-list">
                  <div className="preference-header-row">
                    <span className="pref-col-recognized">识别商品</span>
                    <span className="pref-col-arrow">→</span>
                    <span className="pref-col-order">订单商品</span>
                    <span className="pref-col-action">操作</span>
                  </div>
                  {filteredPreferences.map((pref, index) => {
                    const realIndex = preferences.findIndex(p => p === pref);
                    return (
                      <div className="preference-row" key={index}>
                        <input
                          className="pref-input"
                          value={pref.recognized}
                          placeholder="识别商品名"
                          onChange={(e) => updatePreference(realIndex, 'recognized', e.target.value)}
                        />
                        <span className="pref-arrow">→</span>
                        <input
                          className="pref-input"
                          value={pref.order_product}
                          placeholder="订单商品名"
                          onChange={(e) => updatePreference(realIndex, 'order_product', e.target.value)}
                        />
                        <button 
                          className="pref-delete-btn" 
                          onClick={() => deletePreference(realIndex)}
                          title="删除此偏好"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
              <p className="picker-note">
                偏好会按客户隔离存储，当前客户: {table.metadata.customerId || '(未选择)'}
              </p>
            </div>
            <div className="confirm-footer">
              <button className="btn-cancel" onClick={closePreferenceEditor}>取消</button>
              <button className="btn-primary" onClick={savePreferences}>保存</button>
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
          <button className="action-btn submit-btn" onClick={handleSubmitCurrent} title="提交当前订单">
            <Send size={14} />
            <span>提交当前订单</span>
          </button>
          <button className="action-btn submit-btn" onClick={handleSubmitAll} title="提交所有订单">
            <Send size={14} />
            <span>提交所有订单</span>
          </button>
        </div>
      </div>

      {/* 订单元数据区域 */}
      <div className="metadata-panel">
        <div
          className={`metadata-item customer-select-wrapper ${
            (customerHighlightUntil[table.id] || 0) > Date.now() ? 'customer-highlight' : ''
          }`}
        >
          <User size={14} className="meta-icon" />
          <span className="meta-label">客户:</span>
          <select 
            className="meta-select"
            value={table.metadata.customerId || ''}
            onChange={handleClientChange}
          >
            <option value="">-- 选择客户 --</option>
            {partners.map(c => (
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

        {/* 编辑偏好按钮 */}
        <button className="preference-btn" onClick={openPreferenceEditor} title="编辑偏好">
          <Settings size={14} />
          <span>编辑偏好</span>
        </button>

        {/* 添加新商品按钮 */}
        <button className="add-row-btn" onClick={handleAddProduct} title="添加新商品">
          <Plus size={14} />
          <span>添加商品</span>
        </button>
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
