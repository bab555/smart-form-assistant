"""
Skills API - 模板管理

提供：
1. 模板列表
2. 模板导入
3. 模板删除
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Dict, Any, Optional
import pandas as pd
from io import BytesIO
import json
from pathlib import Path

from app.core.logger import app_logger as logger
from app.core.templates import DEFAULT_SCHEMA, DEFAULT_HEADERS

router = APIRouter()

# ========== 内置模板定义 ==========

BUILT_IN_TEMPLATES = [
    {
        "id": "basic",
        "name": "基础订单模板",
        "category": "general",
        "description": "通用订单表格，包含品名、数量、规格、单价、总价",
        "schema": DEFAULT_SCHEMA,
        "is_builtin": True,
    },
    {
        "id": "product_library",
        "name": "商品库模板",
        "category": "product",
        "description": "完整商品信息，从商品库导入",
        "schema": [
            {"key": "商品ID", "title": "商品ID", "type": "text"},
            {"key": "商品名称", "title": "商品名称", "type": "text"},
            {"key": "一级分类", "title": "一级分类", "type": "text"},
            {"key": "二级分类", "title": "二级分类", "type": "text"},
            {"key": "商品规格", "title": "商品规格", "type": "text"},
            {"key": "单位", "title": "单位", "type": "text"},
            {"key": "单价", "title": "单价", "type": "number"},
        ],
        "is_builtin": True,
    },
]

# 用户自定义模板存储路径
CUSTOM_TEMPLATES_PATH = Path("./data/custom_templates.json")


def load_custom_templates() -> List[Dict]:
    """加载用户自定义模板"""
    if CUSTOM_TEMPLATES_PATH.exists():
        try:
            with open(CUSTOM_TEMPLATES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载自定义模板失败: {e}")
    return []


def save_custom_templates(templates: List[Dict]):
    """保存用户自定义模板"""
    CUSTOM_TEMPLATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CUSTOM_TEMPLATES_PATH, "w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)


@router.get("/list")
async def list_skills():
    """
    获取所有可用模板
    
    Returns:
        skills: 模板列表
    """
    # 合并内置模板和自定义模板
    custom = load_custom_templates()
    all_templates = BUILT_IN_TEMPLATES + custom
    
    return {
        "skills": all_templates,
        "total": len(all_templates),
    }


@router.get("/{skill_id}")
async def get_skill(skill_id: str):
    """
    获取单个模板详情
    """
    # 先查内置
    for t in BUILT_IN_TEMPLATES:
        if t["id"] == skill_id:
            return t
    
    # 再查自定义
    for t in load_custom_templates():
        if t["id"] == skill_id:
            return t
    
    raise HTTPException(status_code=404, detail="模板不存在")


@router.post("/import")
async def import_skill(
    file: UploadFile = File(...),
    name: str = Form(...),
    category: str = Form("general"),
    description: str = Form(""),
):
    """
    导入 Excel 模板
    
    从 Excel 第一行提取表头作为 schema
    """
    try:
        content = await file.read()
        
        # 读取 Excel
        ext = file.filename.lower().split('.')[-1] if file.filename else 'xlsx'
        if ext == 'csv':
            df = pd.read_csv(BytesIO(content), nrows=1)
        else:
            df = pd.read_excel(BytesIO(content), nrows=1)
        
        # 提取表头作为 schema
        schema = []
        for col in df.columns:
            col_name = str(col).strip()
            if col_name and not col_name.startswith("Unnamed"):
                # 推断类型
                col_type = "text"
                if df[col].dtype in ['int64', 'float64']:
                    col_type = "number"
                
                schema.append({
                    "key": col_name,
                    "title": col_name,
                    "type": col_type,
                })
        
        if not schema:
            raise HTTPException(status_code=400, detail="无法从文件提取表头")
        
        # 生成模板 ID
        import hashlib
        template_id = hashlib.md5(f"{name}_{category}".encode()).hexdigest()[:8]
        
        # 创建模板
        new_template = {
            "id": template_id,
            "name": name,
            "category": category,
            "description": description or f"从 {file.filename} 导入",
            "schema": schema,
            "is_builtin": False,
        }
        
        # 保存到自定义模板
        custom = load_custom_templates()
        
        # 检查是否已存在同名模板
        custom = [t for t in custom if t["id"] != template_id]
        custom.append(new_template)
        
        save_custom_templates(custom)
        
        logger.info(f"导入模板成功: {name}, {len(schema)} 列")
        
        return {
            "success": True,
            "template": new_template,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导入模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str):
    """
    删除自定义模板（内置模板不可删除）
    """
    # 检查是否是内置模板
    for t in BUILT_IN_TEMPLATES:
        if t["id"] == skill_id:
            raise HTTPException(status_code=400, detail="内置模板不可删除")
    
    # 删除自定义模板
    custom = load_custom_templates()
    new_custom = [t for t in custom if t["id"] != skill_id]
    
    if len(new_custom) == len(custom):
        raise HTTPException(status_code=404, detail="模板不存在")
    
    save_custom_templates(new_custom)
    
    return {
        "success": True,
        "message": "删除成功",
    }
