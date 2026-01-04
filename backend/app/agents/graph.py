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
from app.agents.prompts import (
    MASTER_AGENT_SYSTEM_PROMPT,
    VISUAL_AGENT_PROMPT,
    AUDIO_AGENT_PROMPT
)
import json


# ========== Agent 状态定义 ==========
class AgentState(TypedDict):
    """Agent 工作流状态"""
    messages: Annotated[List[BaseMessage], add]  # 对话历史（累加）
    input_type: str  # 输入类型：image/audio
    current_step: str  # 当前步骤：idle/ocr/calibration/query/fill
    
    # 输入数据
    image_data: Optional[bytes]
    audio_data: Optional[bytes]
    
    # 中间结果
    ocr_text: Optional[str]  # OCR 识别结果
    asr_text: Optional[str]  # ASR 识别结果
    
    # 表单数据
    form_data: Dict[str, Any]  # 当前表格数据
    
    # 歧义处理
    ambiguity_flag: bool  # 是否有待确认项
    ambiguous_items: List[Dict]  # 歧义项列表
    
    # 控制流
    next_action: Optional[str]  # 下一步动作
    error: Optional[str]  # 错误信息


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
    else:
        state['error'] = f"不支持的输入类型: {state['input_type']}"
        state['next_action'] = 'end'
    
    return state


async def visual_flow_node(state: AgentState) -> AgentState:
    """
    视觉流节点 - 处理图片识别
    """
    logger.info("[Visual Flow] 开始处理图片")
    
    try:
        # Step 1: OCR 识别
        state['current_step'] = 'ocr'
        logger.info("[Visual Flow] 执行 OCR 识别...")
        
        ocr_text = await ocr_service.recognize_general(image_data=state['image_data'])
        state['ocr_text'] = ocr_text
        
        logger.info(f"[Visual Flow] OCR 结果: {ocr_text[:100]}...")
        
        # Step 2: 使用 LLM 提取结构化数据
        state['current_step'] = 'extraction'
        logger.info("[Visual Flow] 提取结构化数据...")
        
        extraction_prompt = f"""
请从以下 OCR 识别的文本中提取表单数据。

OCR文本：
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

如果某些字段不存在，请忽略。每一行数据作为一个对象。
"""
        
        messages = [
            {"role": "system", "content": "你是数据提取专家，擅长从文本中提取结构化信息。"},
            {"role": "user", "content": extraction_prompt}
        ]
        
        extraction_result = await llm_service.call_main_model(messages, temperature=0.3)
        
        # 解析提取结果
        try:
            # 尝试提取 JSON
            import re
            json_match = re.search(r'\{.*\}', extraction_result, re.DOTALL)
            if json_match:
                extracted_data = json.loads(json_match.group())
            else:
                extracted_data = json.loads(extraction_result)
            
            logger.info(f"[Visual Flow] 提取到 {len(extracted_data.get('rows', []))} 行数据")
        except json.JSONDecodeError as e:
            logger.error(f"[Visual Flow] JSON 解析失败: {str(e)}")
            extracted_data = {"rows": []}
        
        # Step 3: 校准数据
        state['current_step'] = 'calibration'
        logger.info("[Visual Flow] 开始校准数据...")
        
        calibrated_rows = []
        ambiguous_items = []

        # key -> label 映射（用于表格列头显示；后续可从 template/配置加载）
        label_map = {
            "product_name": "商品名称",
            "quantity": "数量",
            "unit": "单位",
            "price": "单价",
            "customer": "客户",
            "stock_quantity": "库存数量",
            "warehouse": "仓库",
        }
        
        for row_idx, row in enumerate(extracted_data.get('rows', [])):
            calibrated_row_items: List[Dict[str, Any]] = []
            
            for key, value in row.items():
                if not value or value == "":
                    continue
                
                # 确定类别
                category = None
                if 'product' in key or 'name' in key:
                    category = 'product'
                elif 'customer' in key:
                    category = 'customer'
                elif 'unit' in key:
                    category = 'unit'
                
                # 校准
                calibrated, confidence, is_amb, candidates = await vector_store.calibrate_text(
                    str(value), category=category
                )

                # 构造成前端期望的 FormItem（数组元素）
                calibrated_row_items.append(
                    {
                        "key": key,
                        "label": label_map.get(key, key),
                        "value": calibrated,
                        "original_text": str(value),
                        "confidence": float(confidence),
                        "is_ambiguous": bool(is_amb),
                        "candidates": candidates if is_amb else None,
                        "data_type": "string",
                    }
                )
                
                # 记录歧义项
                if is_amb and candidates:
                    ambiguous_items.append({
                        "row_index": row_idx,
                        "key": key,
                        "original": value,
                        "candidates": candidates
                    })
            
            if calibrated_row_items:
                calibrated_rows.append(calibrated_row_items)
        
        # 更新状态
        state['form_data'] = {"rows": calibrated_rows}
        state['ambiguous_items'] = ambiguous_items
        state['ambiguity_flag'] = len(ambiguous_items) > 0
        
        logger.info(f"[Visual Flow] 校准完成，共 {len(calibrated_rows)} 行，{len(ambiguous_items)} 个歧义项")
        
        # 生成回复消息
        if ambiguous_items:
            amb_text = "\n".join([
                f"{i+1}. 第{item['row_index']+1}行的'{item['key']}': {item['candidates']}"
                for i, item in enumerate(ambiguous_items[:3])  # 只显示前3个
            ])
            reply = f"图片识别完成！共提取 {len(calibrated_rows)} 行数据。\n\n检测到 {len(ambiguous_items)} 个歧义项需要确认：\n{amb_text}"
        else:
            reply = f"图片识别完成！共提取 {len(calibrated_rows)} 行数据，所有字段均已自动校准。"
        
        state['messages'].append(AIMessage(content=reply))
        state['next_action'] = 'end'
        
    except Exception as e:
        logger.error(f"[Visual Flow] 处理失败: {str(e)}")
        state['error'] = str(e)
        state['messages'].append(AIMessage(content=f"图片处理失败: {str(e)}"))
        state['next_action'] = 'end'
    
    return state


async def audio_flow_node(state: AgentState) -> AgentState:
    """
    音频流节点 - 处理语音命令
    """
    logger.info("[Audio Flow] 开始处理语音")
    
    try:
        # Step 1: ASR 识别
        state['current_step'] = 'asr'
        logger.info("[Audio Flow] 执行 ASR 识别...")
        
        asr_text = await asr_service.recognize_audio(state['audio_data'])
        state['asr_text'] = asr_text
        
        logger.info(f"[Audio Flow] ASR 结果: {asr_text}")
        
        # Step 2: 意图识别和命令执行
        state['current_step'] = 'intent_recognition'
        logger.info("[Audio Flow] 识别意图...")
        
        intent_prompt = f"""
用户语音命令：{asr_text}

当前表格有 {len(state['form_data'].get('rows', []))} 行数据。

请分析用户的意图并执行相应操作：
1. 修改数据（update）- 提取行号、字段、新值
2. 删除数据（delete）- 提取行号
3. 添加数据（add）- 提取所有字段值
4. 查询数据（query）- 提取查询条件
5. 清空数据（clear）

请以 JSON 格式返回（只输出JSON）：
{{
  "intent": "update/delete/add/query/clear",
  "row_index": 0,
  "field": "product_name",
  "value": "红富士苹果",
  "reply": "已将第1行的商品名称改为红富士苹果"
}}
"""
        
        messages = [
            {"role": "system", "content": "你是智能表单助手，擅长理解用户的语音命令。"},
            {"role": "user", "content": intent_prompt}
        ]
        
        intent_result = await llm_service.call_main_model(messages, temperature=0.3)
        
        # 解析意图
        try:
            import re
            json_match = re.search(r'\{.*\}', intent_result, re.DOTALL)
            if json_match:
                intent_data = json.loads(json_match.group())
            else:
                intent_data = json.loads(intent_result)
            
            logger.info(f"[Audio Flow] 意图识别: {intent_data.get('intent')}")
            
            # 生成回复
            reply = intent_data.get('reply', '命令已执行')
            
            # 这里简化处理，实际应该修改 form_data
            # 真实场景中会通过 WebSocket 将指令发送给前端
            
            state['messages'].append(AIMessage(content=reply))
            state['next_action'] = 'end'
            
        except json.JSONDecodeError as e:
            logger.error(f"[Audio Flow] 意图解析失败: {str(e)}")
            state['messages'].append(AIMessage(content="抱歉，我没有理解您的命令，请再说一次。"))
            state['next_action'] = 'end'
        
    except Exception as e:
        logger.error(f"[Audio Flow] 处理失败: {str(e)}")
        state['error'] = str(e)
        state['messages'].append(AIMessage(content=f"语音处理失败: {str(e)}"))
        state['next_action'] = 'end'
    
    return state


# ========== 条件边函数 ==========

def route_by_action(state: AgentState) -> str:
    """根据 next_action 路由"""
    action = state.get('next_action', 'end')
    logger.info(f"[Route] 下一步动作: {action}")
    
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

