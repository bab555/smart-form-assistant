"""
RESTful API 端点
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
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
from app.services.document_service import document_service
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
    template_id: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None)
):
    """
    处理图片识别请求
    
    Args:
        file: 上传的图片文件
        template_id: 表单模板ID（可选）
        client_id: 客户端 ID（用于 WebSocket 推送）
    
    Returns:
        StandardResponse: 识别结果
    """
    trace_id = generate_trace_id()
    logger.info(f"[{trace_id}] 收到图片识别请求 (Client: {client_id})")
    
    try:
        # 读取文件
        image_data = await file.read()
        logger.info(f"[{trace_id}] 图片大小: {len(image_data)} bytes")
        
        # 初始化状态
        initial_state: AgentState = {
            "messages": [],
            "input_type": "image",
            "current_step": "idle",
            "client_id": client_id,
            "image_data": image_data,
            "audio_data": None,
            "ocr_text": None,
            "asr_text": None,
            "source_type": None,
            "content_analysis": None,
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
            "message": result['messages'][-1].content if result['messages'] else '',
            "is_article": result['form_data'].get('is_article', False)
        }
        
        logger.info(f"[{trace_id}] 识别成功，返回 {len(response_data['rows'])} 行数据")
        
        return StandardResponse(
            code=200,
            message=response_data['message'] or "识别成功",
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
    file: UploadFile = File(...),
    client_id: Optional[str] = Form(None)
):
    """
    处理语音识别请求
    """
    trace_id = generate_trace_id()
    logger.info(f"[{trace_id}] 收到语音识别请求 (Client: {client_id})")
    
    try:
        # 读取文件
        audio_data = await file.read()
        logger.info(f"[{trace_id}] 音频大小: {len(audio_data)} bytes")
        
        # 初始化状态
        initial_state: AgentState = {
            "messages": [],
            "input_type": "audio",
            "current_step": "idle",
            "client_id": client_id,
            "image_data": None,
            "audio_data": audio_data,
            "ocr_text": None,
            "asr_text": None,
            "source_type": None,
            "content_analysis": None,
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
    """获取表单模板列表"""
    trace_id = generate_trace_id()
    
    # Mock 模板数据
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
    """提交表单数据"""
    trace_id = generate_trace_id()
    logger.info(f"[{trace_id}] 收到表单提交请求")
    
    try:
        row_count = len(request.rows)
        logger.info(f"[{trace_id}] 提交 {row_count} 行数据")
        
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
    """同步知识库"""
    trace_id = generate_trace_id()
    logger.info(f"[{trace_id}] 收到知识库同步请求: {request.source}")
    
    try:
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


@router.post("/document/extract", response_model=StandardResponse)
async def extract_document(
    file: UploadFile = File(...),
    template_id: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None)
):
    """
    从文档中提取数据
    """
    trace_id = generate_trace_id()
    logger.info(f"[{trace_id}] 收到文档提取请求: {file.filename} (Client: {client_id})")
    
    try:
        # 检查文件类型
        file_type = document_service.get_file_type(file.filename)
        if not file_type:
            return StandardResponse(
                code=4001,
                message=f"不支持的文件类型: {file.filename}",
                data={"supported_types": list(document_service.SUPPORTED_EXTENSIONS.keys())},
                trace_id=trace_id
            )
        
        file_content = await file.read()
        logger.info(f"[{trace_id}] 文件大小: {len(file_content)} bytes, 类型: {file_type}")
        
        if file_type == 'excel':
            result = await document_service.extract_data(file_content, file.filename, None)
            result['source_type'] = 'excel'
            result['calibrated'] = False
            result['analysis'] = {"source_type": "excel", "should_calibrate": False, "reason": "Excel 文件无需校准"}
            
        elif file_type == 'word':
            result = await document_service.extract_data(file_content, file.filename, None)
            result['source_type'] = 'word'
            result['calibrated'] = False
            result['analysis'] = {"source_type": "word", "should_calibrate": False, "reason": "Word 文件无需校准"}
            
        elif file_type == 'image':
            logger.info(f"[{trace_id}] 图片类型，进入 Agent 工作流")
            initial_state = {
                "messages": [],
                "input_type": "image",
                "current_step": "idle",
                "client_id": client_id,
                "image_data": file_content,
                "audio_data": None,
                "ocr_text": None,
                "asr_text": None,
                "source_type": None,
                "content_analysis": None,
                "form_data": {},
                "ambiguity_flag": False,
                "ambiguous_items": [],
                "next_action": None,
                "error": None
            }
            final_state = await agent_graph.ainvoke(initial_state, config={"configurable": {"thread_id": trace_id}})
            form_data = final_state.get('form_data', {})
            result = {
                "success": True,
                "file_type": "image",
                "source_type": final_state.get('source_type', 'image'),
                "rows": form_data.get('rows', []),
                "row_count": len(form_data.get('rows', [])),
                "ambiguous_items": final_state.get('ambiguous_items', []),
                "calibrated": final_state.get('content_analysis', {}).get('should_calibrate', False),
                "analysis": final_state.get('content_analysis'),
                "is_article": form_data.get('is_article', False),
                "message": "图片处理完成"
            }
            if result.get('is_article'):
                result['message'] = "检测到文章内容，不适合表格提取"
            
        else:
            # PDF/PPT: 转图后进入 Agent 工作流
            logger.info(f"[{trace_id}] {file_type} 类型，先转图片再进入 Agent 工作流")
            try:
                images = await document_service.convert_to_images(file_content, file.filename)
                if not images: raise ValueError("文档转换失败")
                
                initial_state = {
                    "messages": [],
                    "input_type": "image",
                    "current_step": "idle",
                    "client_id": client_id,
                    "image_data": images[0],
                    "audio_data": None,
                    "ocr_text": None,
                    "asr_text": None,
                    "source_type": file_type,
                    "content_analysis": None,
                    "form_data": {},
                    "ambiguity_flag": False,
                    "ambiguous_items": [],
                    "next_action": None,
                    "error": None
                }
                final_state = await agent_graph.ainvoke(initial_state, config={"configurable": {"thread_id": trace_id}})
                form_data = final_state.get('form_data', {})
                result = {
                    "success": True,
                    "file_type": file_type,
                    "source_type": final_state.get('source_type', file_type),
                    "rows": form_data.get('rows', []),
                    "row_count": len(form_data.get('rows', [])),
                    "page_count": len(images),
                    "ambiguous_items": final_state.get('ambiguous_items', []),
                    "calibrated": final_state.get('content_analysis', {}).get('should_calibrate', False),
                    "analysis": final_state.get('content_analysis'),
                    "is_article": form_data.get('is_article', False),
                    "message": f"{file_type.upper()} 处理完成"
                }
                if result.get('is_article'):
                    result['message'] = "检测到文章内容，不适合表格提取"
            except Exception as e:
                logger.error(f"[{trace_id}] 文档转图片处理失败: {str(e)}")
                raise ValueError(f"文档处理失败: {str(e)}")
        
        return StandardResponse(
            code=200,
            message=result.get('message', '提取成功'),
            data=result,
            trace_id=trace_id
        )
        
    except ValueError as e:
        logger.error(f"[{trace_id}] 文档处理失败: {str(e)}")
        return StandardResponse(code=4002, message=str(e), data=None, trace_id=trace_id)
        
    except Exception as e:
        logger.error(f"[{trace_id}] 处理失败: {str(e)}")
        return StandardResponse(code=5001, message=f"处理失败: {str(e)}", data=None, trace_id=trace_id)


@router.get("/document/supported-types")
async def get_supported_types():
    """获取支持的文档类型"""
    return {
        "supported_types": document_service.SUPPORTED_EXTENSIONS,
        "all_extensions": [ext for exts in document_service.SUPPORTED_EXTENSIONS.values() for ext in exts]
    }
