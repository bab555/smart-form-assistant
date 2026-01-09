"""
RESTful API 端点 (重构版)

原则：
- 统一入口 /task/submit
- 只做文件接收和任务分发
- 业务逻辑在 Graph 中
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional
from app.core.logger import app_logger as logger
from app.core.connection_manager import manager
from app.core.protocol import EventType
from app.utils.helpers import generate_trace_id
import asyncio

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "smart-form-backend",
        "connections": manager.get_connection_count()
    }


@router.post("/task/submit")
async def submit_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    task_type: str = Form("extract"),  # "extract" | "audio" | "chat"
    client_id: str = Form(...),
    table_id: Optional[str] = Form(None),
):
    """
    统一任务提交入口
    
    Args:
        file: 上传的文件
        task_type: 任务类型
        client_id: 客户端 ID（用于 WebSocket 推送）
        table_id: 目标表格 ID（可选，不提供则创建新表格）
    
    Returns:
        task_id: 任务 ID
    """
    task_id = generate_trace_id()
    logger.info(f"[Task] Received: {task_id}, type={task_type}, file={file.filename}, client={client_id}")
    
    # 检查客户端是否在线
    if not manager.is_connected(client_id):
        logger.warning(f"[Task] Client not connected: {client_id}")
        # 不阻止任务，但记录警告
    
    # 读取文件内容
    try:
        file_content = await file.read()
        file_name = file.filename or "unknown"
    except Exception as e:
        logger.error(f"[Task] Failed to read file: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to read file")
    
    # 如果没有指定 table_id，生成一个
    actual_table_id = table_id or f"table_{task_id[:8]}"
    
    # 异步执行任务
    background_tasks.add_task(
        execute_task,
        task_id=task_id,
        task_type=task_type,
        client_id=client_id,
        table_id=actual_table_id,
        file_content=file_content,
        file_name=file_name,
    )
    
    # 直接执行 (已注释，避免阻塞)
    # await execute_task(
    #     task_id=task_id,
    #     task_type=task_type,
    #     client_id=client_id,
    #     table_id=actual_table_id,
    #     file_content=file_content,
    #     file_name=file_name,
    # )
    
    # 立即返回
    return {
        "task_id": task_id,
        "table_id": actual_table_id,
        "status": "queued"
    }


async def execute_task(
    task_id: str,
    task_type: str,
    client_id: str,
    table_id: str,
    file_content: bytes,
    file_name: str,
):
    """
    执行任务（后台）
    
    调用 Agent Graph 的 run_task 函数
    """
    logger.info(f"[Task] Executing: {task_id}")
    
    try:
        # 导入并执行 Graph
        from app.agents.graph import run_task
        
        await run_task(
            task_id=task_id,
            client_id=client_id,
            task_type=task_type,
            file_content=file_content,
            file_name=file_name,
            table_id=table_id,
        )
        
    except Exception as e:
        logger.error(f"[Task] Failed: {task_id} - {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 发送错误事件
        await manager.send(client_id, EventType.ERROR, {
            "code": 500,
            "message": f"任务执行失败: {str(e)}",
            "task_id": task_id,
        })


# ========== 兼容性端点（逐步废弃）==========

@router.get("/template/list")
async def get_templates():
    """获取表单模板列表"""
    # 返回空列表，Phase 3 会实现 Skills 导入
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
            "pdf": [".pdf"],
            "image": [".png", ".jpg", ".jpeg", ".gif", ".webp"],
        }
    }
