/**
 * 右键菜单组件
 */

import React, { useEffect, useRef } from 'react';
import { Plus, Copy, Trash2, FileSpreadsheet, Download } from 'lucide-react';
import './ContextMenu.css';

export interface MenuItem {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  divider?: boolean;
}

interface ContextMenuProps {
  x: number;
  y: number;
  items: MenuItem[];
  onClose: () => void;
}

export const ContextMenu: React.FC<ContextMenuProps> = ({ x, y, items, onClose }) => {
  const menuRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  // 调整位置避免超出视口
  const adjustedPosition = React.useMemo(() => {
    const menuWidth = 180;
    const menuHeight = items.length * 36 + 16;
    
    let adjustedX = x;
    let adjustedY = y;

    if (x + menuWidth > window.innerWidth) {
      adjustedX = x - menuWidth;
    }
    if (y + menuHeight > window.innerHeight) {
      adjustedY = y - menuHeight;
    }

    return { x: Math.max(0, adjustedX), y: Math.max(0, adjustedY) };
  }, [x, y, items.length]);

  return (
    <div
      ref={menuRef}
      className="context-menu"
      style={{ left: adjustedPosition.x, top: adjustedPosition.y }}
    >
      {items.map((item, index) => (
        <React.Fragment key={index}>
          {item.divider && <div className="context-menu-divider" />}
          <button
            className={`context-menu-item ${item.disabled ? 'disabled' : ''}`}
            onClick={() => {
              if (!item.disabled) {
                item.onClick();
                onClose();
              }
            }}
            disabled={item.disabled}
          >
            {item.icon && <span className="menu-icon">{item.icon}</span>}
            <span className="menu-label">{item.label}</span>
          </button>
        </React.Fragment>
      ))}
    </div>
  );
};

// 预定义菜单项
export const createCanvasMenuItems = (
  onCreateTable: () => void,
  onExportAll: () => void,
  onCreateFromTemplate: () => void,
  hasSelection: boolean,
  onPaste?: () => void
): MenuItem[] => [
  {
    label: '新建空白表格',
    icon: <Plus size={14} />,
    onClick: onCreateTable,
  },
  {
    label: '从模板新建',
    icon: <FileSpreadsheet size={14} />,
    onClick: onCreateFromTemplate,
  },
  {
    label: '导出所有表格',
    icon: <Download size={14} />,
    onClick: onExportAll,
    divider: true,
  },
  {
    label: '粘贴',
    icon: <Copy size={14} />,
    onClick: onPaste || (() => {}),
    disabled: !hasSelection,
  },
];

export const createTableMenuItems = (
  onDelete: () => void,
  onDuplicate: () => void,
  onExport: () => void
): MenuItem[] => [
  {
    label: '复制表格',
    icon: <Copy size={14} />,
    onClick: onDuplicate,
  },
  {
    label: '导出 CSV',
    icon: <Download size={14} />,
    onClick: onExport,
  },
  {
    label: '删除表格',
    icon: <Trash2 size={14} />,
    onClick: onDelete,
    divider: true,
  },
];

export default ContextMenu;

