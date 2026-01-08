/**
 * Template Selector - 模板选择组件
 * 
 * 功能：
 * 1. 显示可用模板列表
 * 2. 选择模板创建新表格
 * 3. 导入自定义模板
 */

import React, { useState, useEffect } from 'react';
import { useCanvasStore } from '@/store/useCanvasStore';
import './TemplateSelector.css';

interface Skill {
  id: string;
  name: string;
  category: string;
  description?: string;
  schema: Array<{
    key: string;
    title: string;
    type?: string;
  }>;
}

interface TemplateSelectorProps {
  onClose?: () => void;
}

export const TemplateSelector: React.FC<TemplateSelectorProps> = ({ onClose }) => {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  
  const { createTable } = useCanvasStore();

  // 加载模板列表
  useEffect(() => {
    fetchSkills();
  }, []);

  const fetchSkills = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/skills/list');
      if (!response.ok) throw new Error('获取模板失败');
      
      const data = await response.json();
      setSkills(data.skills || []);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  // 选择模板创建表格
  const handleSelectTemplate = (skill: Skill) => {
    createTable({
      title: skill.name,
      schema: skill.schema.map(s => ({
        key: s.key,
        title: s.title,
        type: (s.type as 'text' | 'number' | 'date') || 'text',
      })),
    });
    onClose?.();
  };

  // 创建空白表格
  const handleCreateBlank = () => {
    createTable();
    onClose?.();
  };

  // 导入 Excel 模板
  const handleImportTemplate = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('name', file.name.replace(/\.[^/.]+$/, ''));
      formData.append('category', 'general');

      const response = await fetch('/api/skills/import', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || '导入失败');
      }

      // 刷新列表
      await fetchSkills();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setImporting(false);
      // 重置 input
      e.target.value = '';
    }
  };

  return (
    <div className="template-selector">
      <div className="template-header">
        <h3>选择表格模板</h3>
        {onClose && (
          <button className="close-btn" onClick={onClose}>×</button>
        )}
      </div>

      {error && (
        <div className="template-error">
          {error}
        </div>
      )}

      <div className="template-list">
        {/* 空白表格选项 */}
        <div 
          className="template-item blank"
          onClick={handleCreateBlank}
        >
          <div className="template-icon">📋</div>
          <div className="template-info">
            <div className="template-name">空白表格</div>
            <div className="template-desc">从空白开始</div>
          </div>
        </div>

        {/* 模板列表 */}
        {loading ? (
          <div className="template-loading">加载中...</div>
        ) : (
          skills.map(skill => (
            <div 
              key={skill.id}
              className="template-item"
              onClick={() => handleSelectTemplate(skill)}
            >
              <div className="template-icon">
                {getCategoryIcon(skill.category)}
              </div>
              <div className="template-info">
                <div className="template-name">{skill.name}</div>
                <div className="template-desc">
                  {skill.schema.map(s => s.title).slice(0, 3).join('、')}
                  {skill.schema.length > 3 && '...'}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* 导入按钮 */}
      <div className="template-import">
        <label className={`import-btn ${importing ? 'importing' : ''}`}>
          <input 
            type="file" 
            accept=".xlsx,.xls,.csv"
            onChange={handleImportTemplate}
            disabled={importing}
          />
          {importing ? '导入中...' : '+ 导入 Excel 模板'}
        </label>
      </div>
    </div>
  );
};

function getCategoryIcon(category: string): string {
  switch (category) {
    case 'product':
      return '🥬';
    case 'customer':
      return '👤';
    case 'general':
      return '📝';
    default:
      return '📊';
  }
}

export default TemplateSelector;

