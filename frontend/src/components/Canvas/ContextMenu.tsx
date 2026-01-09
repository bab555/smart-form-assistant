/**
 * 右键菜单组件 - 白色主题
 */

import React, { useEffect, useRef } from 'react';
import { Plus, Download, X, Minus } from 'lucide-react';
import './ContextMenu.css';

export interface MenuItem {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  divider?: boolean;
  danger?: boolean;  // 危险操作（红色高亮）
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
            className={`context-menu-item ${item.disabled ? 'disabled' : ''} ${item.danger ? 'danger' : ''}`}
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

// 预定义菜单项 - 画布右键菜单（仅导出所有）
export const createCanvasMenuItems = (
  onExportAll: () => void,
  hasTableData: boolean,
): MenuItem[] => [
  {
    label: '导出所有 Sheet',
    icon: <Download size={14} />,
    onClick: onExportAll,
    disabled: !hasTableData,
  },
];

// 表格右键菜单项
export const createTableMenuItems = (
  onAddRow: () => void,
  onDeleteRow: () => void,
  onExportCurrent: () => void,
  onExportAll: () => void,
  onCloseSheet: () => void,
  canDeleteRow: boolean,
): MenuItem[] => [
  {
    label: '添加行',
    icon: <Plus size={14} />,
    onClick: onAddRow,
  },
  {
    label: '删除选中行',
    icon: <Minus size={14} />,
    onClick: onDeleteRow,
    disabled: !canDeleteRow,
    danger: true,
  },
  {
    label: '导出当前 Sheet',
    icon: <Download size={14} />,
    onClick: onExportCurrent,
    divider: true,
  },
  {
    label: '导出所有 Sheet',
    icon: <Download size={14} />,
    onClick: onExportAll,
  },
  {
    label: '关闭当前 Sheet',
    icon: <X size={14} />,
    onClick: onCloseSheet,
    divider: true,
    danger: true,
  },
];

export default ContextMenu;

