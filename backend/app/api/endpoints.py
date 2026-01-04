"""
RESTful API 端点
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List
from app.models.schemas import (
    StandardResponse,
    ImageRecognitionRequest,
    AudioRecognitionRequest,
    FormSubmitRequest,
    KnowledgeSyncRequest,
    FormTemplate
)
from app.agents.graph import agent_graph, AgentState
from app.services.knowledge_base import vector_store
from app.utils.helpers import generate_trace_id
from app.core.logger import app_logger as logger


router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "smart-form-backend"}


@router.post("/workflow/visual", response_model=StandardResponse)
async def process_visual_input(
    file: UploadFile = File(...),
    template_id: Optional[str] = None
):
    """
    处理图片识别请求
    
    Args:
        file: 上传的图片文件
        template_id: 表单模板ID（可选）
    
    Returns:
        StandardResponse: 识别结果
    """
    trace_id = generate_trace_id()
    logger.info(f"[{trace_id}] 收到图片识别请求")
    
    try:
        # 读取文件
        image_data = await file.read()
        logger.info(f"[{trace_id}] 图片大小: {len(image_data)} bytes")
        
        # 初始化状态
        initial_state: AgentState = {
            "messages": [],
            "input_type": "image",
            "current_step": "idle",
            "image_data": image_data,
            "audio_data": None,
            "ocr_text": None,
            "asr_text": None,
            "form_data": {},
            "ambiguity_flag": False,
            "ambiguous_items": [],
            "next_action": None,
            "error": None
        }
        
        # 执行工作流
        logger.info(f"[{trace_id}] 执行 Agent 工作流...")
        result = await agent_graph.ainvoke(initial_state)
        
        # 检查错误
        if result.get('error'):
            logger.error(f"[{trace_id}] 工作流执行失败: {result['error']}")
            return StandardResponse(
                code=5001,
                message=f"OCR识别失败: {result['error']}",
                data=None,
                trace_id=trace_id
            )
        
        # 构建响应
        response_data = {
            "rows": result['form_data'].get('rows', []),
            "ambiguous_items": result.get('ambiguous_items', []),
            "ocr_text": result.get('ocr_text', ''),
            "message": result['messages'][-1].content if result['messages'] else ''
        }
        
        logger.info(f"[{trace_id}] 识别成功，返回 {len(response_data['rows'])} 行数据")
        
        return StandardResponse(
            code=200,
            message="识别成功",
            data=response_data,
            trace_id=trace_id
        )
        
    except Exception as e:
        logger.error(f"[{trace_id}] 处理失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return StandardResponse(
            code=5001,
            message=f"处理失败: {str(e)}",
            data=None,
            trace_id=trace_id
        )


@router.post("/workflow/audio", response_model=StandardResponse)
async def process_audio_input(
    file: UploadFile = File(...)
):
    """
    处理语音识别请求
    
    Args:
        file: 上传的音频文件
    
    Returns:
        StandardResponse: 识别和执行结果
    """
    trace_id = generate_trace_id()
    logger.info(f"[{trace_id}] 收到语音识别请求")
    
    try:
        # 读取文件
        audio_data = await file.read()
        logger.info(f"[{trace_id}] 音频大小: {len(audio_data)} bytes")
        
        # 初始化状态
        initial_state: AgentState = {
            "messages": [],
            "input_type": "audio",
            "current_step": "idle",
            "image_data": None,
            "audio_data": audio_data,
            "ocr_text": None,
            "asr_text": None,
            "form_data": {},
            "ambiguity_flag": False,
            "ambiguous_items": [],
            "next_action": None,
            "error": None
        }
        
        # 执行工作流
        logger.info(f"[{trace_id}] 执行 Agent 工作流...")
        result = await agent_graph.ainvoke(initial_state)
        
        # 检查错误
        if result.get('error'):
            logger.error(f"[{trace_id}] 工作流执行失败: {result['error']}")
            return StandardResponse(
                code=5001,
                message=f"ASR识别失败: {result['error']}",
                data=None,
                trace_id=trace_id
            )
        
        # 构建响应
        response_data = {
            "asr_text": result.get('asr_text', ''),
            "message": result['messages'][-1].content if result['messages'] else '',
            "action_executed": True
        }
        
        logger.info(f"[{trace_id}] 语音处理成功")
        
        return StandardResponse(
            code=200,
            message="处理成功",
            data=response_data,
            trace_id=trace_id
        )
        
    except Exception as e:
        logger.error(f"[{trace_id}] 处理失败: {str(e)}")
        
        return StandardResponse(
            code=5001,
            message=f"处理失败: {str(e)}",
            data=None,
            trace_id=trace_id
        )


@router.get("/template/list", response_model=StandardResponse)
async def get_templates():
    """
    获取表单模板列表
    
    Returns:
        StandardResponse: 模板列表
    """
    trace_id = generate_trace_id()
    
    # Mock 模板数据 (对齐前端 ColumnDefinition)
    templates = [
        {
            "template_id": "fruit_order",
            "name": "水果订单表",
            "columns": [
                {"key": "product_name", "label": "商品名称", "data_type": "string", "required": True},
                {"key": "quantity", "label": "数量", "data_type": "number", "required": True},
                {"key": "unit", "label": "单位", "data_type": "string", "required": True},
                {"key": "price", "label": "单价", "data_type": "number", "required": False},
                {"key": "customer", "label": "客户", "data_type": "string", "required": False}
            ]
        },
        {
            "template_id": "inventory",
            "name": "库存盘点表",
            "columns": [
                {"key": "product_name", "label": "商品名称", "data_type": "string", "required": True},
                {"key": "stock_quantity", "label": "库存数量", "data_type": "number", "required": True},
                {"key": "unit", "label": "单位", "data_type": "string", "required": True},
                {"key": "warehouse", "label": "仓库", "data_type": "string", "required": True}
            ]
        }
    ]
    
    return StandardResponse(
        code=200,
        message="获取成功",
        data={"templates": templates},
        trace_id=trace_id
    )


@router.post("/form/submit", response_model=StandardResponse)
async def submit_form(request: FormSubmitRequest):
    """
    提交表单数据
    
    Args:
        request: 表单提交请求
    
    Returns:
        StandardResponse: 提交结果
    """
    trace_id = generate_trace_id()
    logger.info(f"[{trace_id}] 收到表单提交请求")
    
    try:
        # 这里是 Mock 实现
        # 实际应该保存到数据库或调用外部API
        
        row_count = len(request.rows)
        logger.info(f"[{trace_id}] 提交 {row_count} 行数据")
        
        # Mock 保存成功
        result = {
            "saved_count": row_count,
            "submission_id": trace_id,
            "timestamp": generate_trace_id()
        }
        
        return StandardResponse(
            code=200,
            message="提交成功",
            data=result,
            trace_id=trace_id
        )
        
    except Exception as e:
        logger.error(f"[{trace_id}] 提交失败: {str(e)}")
        
        return StandardResponse(
            code=5002,
            message=f"提交失败: {str(e)}",
            data=None,
            trace_id=trace_id
        )


@router.post("/sync/knowledge", response_model=StandardResponse)
async def sync_knowledge(request: KnowledgeSyncRequest):
    """
    同步知识库
    
    Args:
        request: 同步请求
    
    Returns:
        StandardResponse: 同步结果
    """
    trace_id = generate_trace_id()
    logger.info(f"[{trace_id}] 收到知识库同步请求: {request.source}")
    
    try:
        # 重建向量索引
        await vector_store.initialize(force_rebuild=request.force_rebuild)
        
        result = {
            "synced": True,
            "index_size": vector_store.index.ntotal if vector_store.index else 0,
            "source": request.source
        }
        
        logger.info(f"[{trace_id}] 知识库同步成功")
        
        return StandardResponse(
            code=200,
            message="同步成功",
            data=result,
            trace_id=trace_id
        )
        
    except Exception as e:
        logger.error(f"[{trace_id}] 同步失败: {str(e)}")
        
        return StandardResponse(
            code=5002,
            message=f"同步失败: {str(e)}",
            data=None,
            trace_id=trace_id
        )
