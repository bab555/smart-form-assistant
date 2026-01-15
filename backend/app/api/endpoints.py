"""
RESTful API 端点 (极简版)

原则：
- 文件上传 -> 保存 -> 返回路径
- 业务逻辑全在 WebSocket 通道处理
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, Response
from typing import Optional
from pathlib import Path
import aiofiles
import uuid
from app.core.logger import app_logger as logger
from app.core.connection_manager import manager
from app.services.knowledge_base import vector_store
from app.core.file_parser import parse_file_content
from app.services.preference_store import preference_store

router = APIRouter()

# 上传目录
# 重要：不要用相对路径（在 uvicorn reloader / 多进程下 cwd 可能变化，导致“偶发找不到文件”）
# 固定到 backend/uploads，保证 WS 读取稳定
UPLOAD_DIR = (Path(__file__).resolve().parents[2] / "uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "smart-form-backend",
        "connections": manager.get_connection_count()
    }


@router.get("/file/preview")
async def preview_file(path: str):
    """预览文件内容 (解析后的文本)"""
    if not path:
        raise HTTPException(status_code=400, detail="Missing path")
    
    try:
        p = Path(path)
        # 兼容相对路径
        if not p.is_absolute():
            backend_root = Path(__file__).resolve().parents[2]
            p = (backend_root / p).resolve()
            
        if not p.exists():
            # 尝试在 uploads 目录下直接查找文件名
            p_uploads = UPLOAD_DIR / Path(path).name
            if p_uploads.exists():
                p = p_uploads
            else:
                raise HTTPException(status_code=404, detail=f"File not found: {path}")
        
        async with aiofiles.open(p, 'rb') as f:
            content = await f.read()
            
        # 使用 file_parser 解析内容
        parsed_text = parse_file_content(content, p.name)
        return {"content": parsed_text}
        
    except Exception as e:
        logger.error(f"[Preview] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
):
    """
    纯文件上传接口
    
    Returns:
        file_path: 服务器上的文件路径
        name: 原始文件名
    """
    try:
        # 生成唯一文件名
        ext = Path(file.filename).suffix if file.filename else ""
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = UPLOAD_DIR / unique_name
        
        # 保存文件
        content = await file.read()
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        logger.info(f"[Upload] Saved: {file.filename} -> {file_path}")
        
        return {
            "success": True,
            # 返回绝对路径，避免 WS 侧因 cwd 不一致导致 os.path.exists 失败
            "path": str(file_path.resolve()),
            "name": file.filename,
            "size": len(content)
        }
        
    except Exception as e:
        logger.error(f"[Upload] Failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/task/submit")
async def submit_task(
    file: UploadFile = File(...),
    task_type: str = Form("extract"),
    client_id: str = Form(...),
    table_id: Optional[str] = Form(None),
):
    """
    兼容旧接口：文件上传 + 返回路径
    
    注意：实际处理逻辑已移至 WebSocket 通道
    这里只做文件保存，不再触发后台任务
    """
    try:
        # 保存文件
        ext = Path(file.filename).suffix if file.filename else ""
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = UPLOAD_DIR / unique_name
        
        content = await file.read()
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        logger.info(f"[Task Submit] Saved: {file.filename} -> {file_path}, client={client_id}")
        
        return {
            "success": True,
            "file_path": str(file_path.resolve()),
            "path": str(file_path.resolve()),
            "name": file.filename,
            "task_type": task_type,
            "client_id": client_id,
            "table_id": table_id
        }
        
    except Exception as e:
        logger.error(f"[Task Submit] Failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


# ========== 兼容性端点 ==========

@router.get("/template/list")
async def get_templates():
    """获取表单模板列表"""
    return {
        "code": 200,
        "message": "获取成功",
        "data": {"templates": []},
    }


@router.get("/document/supported-types")
async def get_supported_types():
    """获取支持的文档类型"""
    return {
        "supported_types": {
            "excel": [".xlsx", ".xls", ".csv"],
            "word": [".docx", ".doc"],
            "image": [".png", ".jpg", ".jpeg", ".gif", ".webp"],
            "text": [".txt"],
        }
    }


@router.get("/products/names")
async def get_product_names():
    """返回完整商品库名称列表（JSON数组）"""
    try:
        return Response(content=vector_store.get_product_names_json(), media_type="application/json")
    except Exception as e:
        logger.error(f"[Products] get names failed: {str(e)}")
        raise HTTPException(status_code=500, detail="获取商品库失败")


# ========== 偏好管理 API ==========

@router.get("/preferences/{customer_id}")
async def get_preferences(customer_id: str):
    """获取某客户的偏好映射列表"""
    try:
        await preference_store._load()
        cid = preference_store._normalize_customer_id(customer_id)
        prefs = preference_store._cache.get(cid, {})
        # 返回数组格式，方便前端展示
        items = [{"recognized": k, "order_product": v} for k, v in prefs.items()]
        return {"customer_id": cid, "preferences": items}
    except Exception as e:
        logger.error(f"[Preferences] get failed: {str(e)}")
        raise HTTPException(status_code=500, detail="获取偏好失败")


@router.put("/preferences/{customer_id}")
async def update_preferences(customer_id: str, items: list):
    """批量更新某客户的偏好（覆盖）"""
    try:
        cid = preference_store._normalize_customer_id(customer_id)
        new_prefs = {}
        for item in items:
            r = (item.get("recognized") or "").strip()
            o = (item.get("order_product") or "").strip()
            if r and o:
                new_prefs[r] = o
        
        async with preference_store._lock:
            preference_store._cache[cid] = new_prefs
            try:
                preference_store.path.write_text(
                    __import__("json").dumps(preference_store._cache, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
            except Exception as e:
                logger.warning(f"[PreferenceStore] save failed: {e}")
        
        return {"success": True, "count": len(new_prefs)}
    except Exception as e:
        logger.error(f"[Preferences] update failed: {str(e)}")
        raise HTTPException(status_code=500, detail="更新偏好失败")


@router.delete("/preferences/{customer_id}/{recognized}")
async def delete_preference(customer_id: str, recognized: str):
    """删除某条偏好"""
    try:
        cid = preference_store._normalize_customer_id(customer_id)
        async with preference_store._lock:
            if cid in preference_store._cache and recognized in preference_store._cache[cid]:
                del preference_store._cache[cid][recognized]
                try:
                    preference_store.path.write_text(
                        __import__("json").dumps(preference_store._cache, ensure_ascii=False, indent=2),
                        encoding="utf-8"
                    )
                except Exception as e:
                    logger.warning(f"[PreferenceStore] save failed: {e}")
                return {"success": True}
            else:
                return {"success": False, "message": "偏好不存在"}
    except Exception as e:
        logger.error(f"[Preferences] delete failed: {str(e)}")
        raise HTTPException(status_code=500, detail="删除偏好失败")
