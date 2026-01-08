/**
 * 导出工具函数
 * 使用 xlsx 库在前端生成 Excel 文件
 */

import * as XLSX from 'xlsx';
import { TableData } from '@/store/useCanvasStore';

/**
 * 将单个表格导出为 Excel 文件
 */
export const exportTableToExcel = (table: TableData) => {
  const wb = XLSX.utils.book_new();
  const ws = createSheetFromTable(table);
  
  XLSX.utils.book_append_sheet(wb, ws, table.title || 'Sheet1');
  
  const fileName = `${table.title || 'export'}_${formatDate(new Date())}.xlsx`;
  XLSX.writeFile(wb, fileName);
};

/**
 * 将所有表格导出为一个多 Sheet 的 Excel 文件
 */
export const exportAllTablesToExcel = (tables: Record<string, TableData>) => {
  const tableList = Object.values(tables);
  if (tableList.length === 0) return;

  const wb = XLSX.utils.book_new();
  
  tableList.forEach((table, index) => {
    const ws = createSheetFromTable(table);
    // Sheet 名称不能重复，且长度有限制
    let sheetName = table.title || `Sheet${index + 1}`;
    sheetName = sheetName.replace(/[\\/?*:[\]]/g, '').slice(0, 31);
    
    // 如果名称重复，添加后缀
    if (wb.SheetNames.includes(sheetName)) {
      sheetName = `${sheetName}_${index}`;
    }
    
    XLSX.utils.book_append_sheet(wb, ws, sheetName);
  });

  const fileName = `所有表格_${formatDate(new Date())}.xlsx`;
  XLSX.writeFile(wb, fileName);
};

// ========== 辅助函数 ==========

function createSheetFromTable(table: TableData): XLSX.WorkSheet {
  // 1. 准备表头 (使用 schema 中的 title)
  const headerKeys = table.schema.map(col => col.key);
  const headerTitles = table.schema.map(col => col.title);
  
  // 2. 准备数据行
  const data = table.rows.map(row => {
    const rowData: Record<string, any> = {};
    headerKeys.forEach((key, index) => {
      // 使用 Title 作为 key，这样导出的 Excel 表头就是中文
      rowData[headerTitles[index]] = row[key];
    });
    return rowData;
  });

  // 3. 生成 Sheet
  const ws = XLSX.utils.json_to_sheet(data, { header: headerTitles });
  
  // 4. 设置列宽 (可选优化)
  const wscols = table.schema.map(_ => ({ wch: 15 })); // 默认宽度
  ws['!cols'] = wscols;

  return ws;
}

function formatDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  const h = String(date.getHours()).padStart(2, '0');
  const min = String(date.getMinutes()).padStart(2, '0');
  return `${y}${m}${d}_${h}${min}`;
}

