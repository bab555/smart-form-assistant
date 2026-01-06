"""
LangGraph 工作流定义
"""
from typing import TypedDict, List, Optional, Dict, Any, Annotated
from operator import add
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from app.core.logger import app_logger as logger
from app.services.aliyun_llm import llm_service
from app.services.aliyun_ocr import ocr_service
from app.services.aliyun_asr import asr_service
from app.services.knowledge_base import vector_store
from app.services.skill_registry import skill_registry
from app.services.content_analyzer import (
    content_analyzer, 
    ContentAnalysisResult, 
    SourceType, 
    ContentType
)
from app.core.connection_manager import manager
from datetime import datetime, timezone
import json


# ========== Agent 状态定义 ==========
class AgentState(TypedDict):
    """Agent 工作流状态"""
    messages: Annotated[List[BaseMessage], add]  # 对话历史（累加）
    input_type: str  # 输入类型：image/audio/excel/word
    current_step: str  # 当前步骤：idle/ocr/calibration/query/fill
    client_id: Optional[str] # 客户端 ID，用于 WebSocket 推送
    
    # 输入数据
    image_data: Optional[bytes]
    audio_data: Optional[bytes]
    
    # 中间结果
    ocr_text: Optional[str]  # OCR 识别结果
    asr_text: Optional[str]  # ASR 识别结果
    
    # 内容分析结果
    source_type: Optional[str]  # excel/word/printed/handwritten
    content_analysis: Optional[Dict]  # 完整分析结果
    
    # 表单数据
    form_data: Dict[str, Any]  # 当前表格数据
    
    # 歧义处理
    ambiguity_flag: bool  # 是否有待确认项
    ambiguous_items: List[Dict]  # 歧义项列表
    
    # 控制流
    next_action: Optional[str]  # 下一步动作
    error: Optional[str]  # 错误信息


# ========== 辅助函数 ==========

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

async def notify_step_start(state: AgentState, step: str, message: str):
    """通知步骤开始"""
    if not state.get('client_id'): return
    await manager.send_to_client(state['client_id'], {
        "type": "step_start",
        "step": step,
        "content": message,
        "status": "running",
        "timestamp": _iso_now()
    })

async def notify_step_end(state: AgentState, step: str, message: str):
    """通知步骤结束"""
    if not state.get('client_id'): return
    await manager.send_to_client(state['client_id'], {
        "type": "step_end",
        "step": step,
        "content": message,
        "status": "success",
        "timestamp": _iso_now()
    })

async def notify_log(state: AgentState, step: str, message: str):
    """发送日志"""
    if not state.get('client_id'): return
    await manager.send_to_client(state['client_id'], {
        "type": "step_log",
        "step": step,
        "message": message,
        "timestamp": _iso_now()
    })


# ========== 节点函数定义 ==========

async def router_node(state: AgentState) -> AgentState:
    """
    路由节点 - 根据输入类型决定工作流
    """
    logger.info(f"[Router] 输入类型: {state['input_type']}")
    
    state['current_step'] = 'routing'
    
    if state['input_type'] == 'image':
        state['next_action'] = 'visual_flow'
    elif state['input_type'] == 'audio':
        state['next_action'] = 'audio_flow'
    elif state['input_type'] in ['excel', 'word', 'document']:
        # Excel/Word 直接进入视觉流程（跳过手写判断）
        state['source_type'] = state['input_type']
        state['next_action'] = 'visual_flow'
    else:
        state['error'] = f"不支持的输入类型: {state['input_type']}"
        state['next_action'] = 'end'
    
    return state


async def visual_flow_node(state: AgentState) -> AgentState:
    """
    视觉流节点 - 处理图片/文档识别
    包含：手写判断 → OCR → 内容分析 → Skill匹配 → 条件校准
    """
    logger.info("[Visual Flow] 开始处理")
    
    # 确保 skill_registry 已初始化
    skill_registry.initialize()
    
    try:
        # 确定来源类型
        source_type_str = state.get('source_type', 'image')
        
        if source_type_str == 'excel':
            source_type = SourceType.EXCEL
        elif source_type_str == 'word':
            source_type = SourceType.WORD
        else:
            source_type = SourceType.PRINTED
        
        # ========== Step 1: OCR 识别 ==========
        ocr_text = state.get('ocr_text')
        
        if not ocr_text and state.get('image_data'):
            state['current_step'] = 'ocr'
            logger.info("[Visual Flow] 执行 OCR 识别...")
            await notify_step_start(state, "ocr", "正在执行 OCR 视觉识别...")
            
            ocr_text = await ocr_service.recognize_general(image_data=state['image_data'])
            state['ocr_text'] = ocr_text
            
            logger.info(f"[Visual Flow] OCR 结果: {ocr_text[:100] if ocr_text else 'empty'}...")
            await notify_step_end(state, "ocr", "OCR 识别完成")
        
        # ========== Step 2: 内容分析 ==========
        state['current_step'] = 'analyzing'
        logger.info("[Visual Flow] 执行内容分析...")
        await notify_step_start(state, "analyzing", "正在分析内容类型与特征...")
        
        analysis_result: ContentAnalysisResult = await content_analyzer.full_analysis(
            source_type=source_type,
            image_data=state.get('image_data'),
            ocr_text=ocr_text
        )
        
        # 保存分析结果
        state['source_type'] = analysis_result.source_type.value
        state['content_analysis'] = {
            "source_type": analysis_result.source_type.value,
            "content_type": analysis_result.content_type.value,
            "has_handwriting": analysis_result.has_handwriting,
            "matched_skills": analysis_result.matched_skills,
            "should_calibrate": analysis_result.should_calibrate,
            "is_article": analysis_result.is_article,
            "reason": analysis_result.analysis_reason
        }
        
        if analysis_result.has_handwriting:
            await notify_log(state, "analyzing", "检测到手写内容")
        if analysis_result.matched_skills:
            await notify_log(state, "analyzing", f"匹配到技能: {', '.join(analysis_result.matched_skills)}")
            
        await notify_step_end(state, "analyzing", "内容分析完成")
        
        # ========== Step 2.5: 处理文章内容 ==========
        if analysis_result.is_article:
            # ... (文章处理逻辑不变)
            logger.info("[Visual Flow] 检测到文章内容，返回特殊提示")
            state['form_data'] = {
                "rows": [[{
                    "key": "content_notice",
                    "label": "内容提示",
                    "value": "（完整文章内容，不适合表格展示）",
                    "original_text": ocr_text[:200] + "...",
                    "confidence": 1.0,
                    "is_ambiguous": False,
                    "candidates": None,
                    "data_type": "notice"
                }]],
                "is_article": True
            }
            state['messages'].append(AIMessage(content="检测到文章内容。"))
            state['next_action'] = 'end'
            return state
        
        # ========== Step 3: 提取结构化数据 ==========
        state['current_step'] = 'extraction'
        logger.info("[Visual Flow] 使用 LLM 提取结构化数据...")
        await notify_step_start(state, "extraction", "正在提取结构化数据...")
        
        # 根据是否需要校准来决定提取策略
        if analysis_result.should_calibrate:
            # 策略 A: 农产品/相关领域 - 使用特定 Schema
            extraction_prompt = f"""
请从以下文本（Markdown 格式）中提取表单数据。

文本内容：
{ocr_text}

请按以下 JSON 格式输出（只输出JSON，不要其他文字）：
{{
  "rows": [
    {{
      "product_name": "商品名称",
      "quantity": "数量",
      "unit": "单位",
      "price": "价格",
      "customer": "客户名称"
    }}
  ]
}}
如果某些字段不存在，请忽略。
"""
        else:
            # 策略 B: 通用领域 - 通用表格提取
            extraction_prompt = f"""
请从以下文本（Markdown 格式）中提取表格数据。

文本内容：
{ocr_text}

任务：将 Markdown 表格或列表转换为 JSON 数据。
规则：
1. 识别每一行，转换为 JSON 对象。
2. 键值对列表（如 `Key | Value`）转换为多行数据：`{{ "key": "...", "value": "..." }}`。
3. 字段命名使用 snake_case。

请按以下 JSON 格式输出（只输出JSON）：
{{
  "rows": [
    {{
      "field_key_1": "value_1",
      "field_key_2": "value_2",
      ...
    }}
  ]
}}
"""
        
        messages = [
            {"role": "system", "content": "你是数据提取专家。"},
            {"role": "user", "content": extraction_prompt}
        ]
        
        extraction_result = await llm_service.call_main_model(messages, temperature=0.3)
        
        # 解析提取结果
        try:
            import re
            json_match = re.search(r'\{.*\}', extraction_result, re.DOTALL)
            if json_match:
                extracted_data = json.loads(json_match.group())
            else:
                extracted_data = json.loads(extraction_result)
            
            logger.info(f"[Visual Flow] 提取到 {len(extracted_data.get('rows', []))} 行数据")
            await notify_step_end(state, "extraction", f"提取到 {len(extracted_data.get('rows', []))} 行数据")
        except json.JSONDecodeError as e:
            logger.error(f"[Visual Flow] JSON 解析失败: {str(e)}")
            extracted_data = {"rows": []}
            await notify_log(state, "extraction", "数据提取格式错误")

        
        # ========== Step 4: 条件校准 ==========
        should_calibrate = analysis_result.should_calibrate
        matched_skills = analysis_result.matched_skills
        
        if should_calibrate:
            state['current_step'] = 'calibration'
            logger.info(f"[Visual Flow] 开始校准，使用 Skills: {matched_skills}")
            await notify_step_start(state, "calibration", "正在进行知识库校准...")
        else:
            await notify_step_start(state, "filling", "正在整理数据...")
        
        # ... (映射和校准逻辑) ...
        label_map = {
            "product_name": "商品名称", "quantity": "数量", "unit": "单位", 
            "price": "单价", "customer": "客户", "stock_quantity": "库存数量", "warehouse": "仓库"
        }
        key_to_category = {
            "product_name": "product", "customer": "customer", "unit": "unit", "warehouse": "warehouse"
        }
        
        calibrated_rows = []
        ambiguous_items = []
        
        raw_rows = extracted_data.get('rows', [])
        total_items = len(raw_rows)
        
        for row_idx, row in enumerate(raw_rows):
            calibrated_row_items: List[Dict[str, Any]] = []
            
            # 简单的进度通知
            if should_calibrate and row_idx % 2 == 0:
                await notify_log(state, "calibration", f"正在校准第 {row_idx + 1}/{total_items} 行...")
            
            for key, value in row.items():
                if not value: continue
                
                calibrated = str(value)
                confidence = 1.0
                is_amb = False
                candidates = None
                
                if should_calibrate:
                    category = key_to_category.get(key)
                    # 只有匹配到对应 Skill 的字段才校准
                    skill_id_for_category = None
                    for sid in matched_skills:
                        skill = skill_registry.get_skill(sid)
                        if skill and skill.category == category:
                            skill_id_for_category = sid
                            break
                    
                    if skill_id_for_category:
                        calibrated, confidence, is_amb, candidates = await vector_store.calibrate_text(
                            str(value), category=category
                        )
                
                label = label_map.get(key, key.replace('_', ' ').title())
                
                calibrated_row_items.append({
                    "key": key,
                    "label": label,
                    "value": calibrated,
                    "original_text": str(value),
                    "confidence": float(confidence),
                    "is_ambiguous": bool(is_amb),
                    "candidates": candidates if is_amb else None,
                    "data_type": "string",
                })
                
                if is_amb and candidates:
                    ambiguous_items.append({
                        "row_index": row_idx,
                        "key": key,
                        "original": value,
                        "candidates": candidates
                    })
            
            if calibrated_row_items:
                calibrated_rows.append(calibrated_row_items)
        
        if should_calibrate:
            await notify_step_end(state, "calibration", "校准完成")
        
        # ========== Step 5: 填充表格 ==========
        state['current_step'] = 'filling'
        await notify_step_start(state, "filling", "正在生成表格...")
        
        state['form_data'] = {"rows": calibrated_rows}
        state['ambiguous_items'] = ambiguous_items
        state['ambiguity_flag'] = len(ambiguous_items) > 0
        
        await notify_step_end(state, "filling", "处理全部完成")
        
        state['messages'].append(AIMessage(content=f"识别完成！共 {len(calibrated_rows)} 行数据。"))
        state['next_action'] = 'end'
        
    except Exception as e:
        logger.error(f"[Visual Flow] 处理失败: {str(e)}")
        state['error'] = str(e)
        state['messages'].append(AIMessage(content=f"处理失败: {str(e)}"))
        state['next_action'] = 'end'
        await notify_log(state, "error", f"处理异常: {str(e)}")
    
    return state


async def audio_flow_node(state: AgentState) -> AgentState:
    """
    音频流节点
    """
    await notify_step_start(state, "ocr", "正在处理语音...") # 音频流暂复用 ocr 步骤显示
    # ... (音频逻辑保持简单，暂不详细修改) ...
    return state


# ========== 条件边函数 ==========

def route_by_action(state: AgentState) -> str:
    """根据 next_action 路由"""
    action = state.get('next_action', 'end')
    if action == 'visual_flow':
        return 'visual_flow'
    elif action == 'audio_flow':
        return 'audio_flow'
    else:
        return 'end'


# ========== 构建工作流图 ==========

def create_workflow() -> StateGraph:
    """创建 LangGraph 工作流"""
    
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("router", router_node)
    workflow.add_node("visual_flow", visual_flow_node)
    workflow.add_node("audio_flow", audio_flow_node)
    
    # 设置入口点
    workflow.set_entry_point("router")
    
    # 添加条件边
    workflow.add_conditional_edges(
        "router",
        route_by_action,
        {
            "visual_flow": "visual_flow",
            "audio_flow": "audio_flow",
            "end": END
        }
    )
    
    # 添加结束边
    workflow.add_edge("visual_flow", END)
    workflow.add_edge("audio_flow", END)
    
    logger.info("LangGraph 工作流已创建")
    
    return workflow


# 编译工作流
agent_graph = create_workflow().compile()
