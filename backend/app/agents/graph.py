"""
LangGraph 工作流定义 - ComfyUI 风格

核心原则：
1. 后端是无状态执行器，只处理单次任务
2. 通过 WebSocket 推送所有结果，前端是 SoT
3. 支持行级流式输出 (ROW_COMPLETE)
"""
from typing import TypedDict, List, Optional, Dict, Any, Literal
from langgraph.graph import StateGraph, END
from app.core.logger import app_logger as logger
from app.core.connection_manager import manager
from app.core.protocol import EventType
from app.utils.helpers import generate_trace_id
from app.core.templates import UNSTRUCTURED_EXTRACTION_PROMPT, map_row_to_template
import json


# ========== Agent 状态定义 ==========
class AgentState(TypedDict):
    """Agent 工作流状态 - 单次任务"""
    # 任务标识
    task_id: str
    client_id: str
    task_type: Literal["extract", "audio", "chat"]
    
    # 输入数据
    file_content: Optional[bytes]
    file_name: Optional[str]
    text_content: Optional[str]
    
    # 中间结果
    ocr_text: Optional[str]
    ocr_notes: Optional[List[str]]
    content_type: Optional[str]
    extracted_rows: List[Dict[str, Any]]
    
    # 表格信息
    table_id: Optional[str]
    
    # 表格上下文（前端传递，用于咨询分析）
    table_context: Optional[Dict[str, Any]]  # {title, rows, schema, metadata}
    
    # 控制流
    next_node: Optional[str]
    error: Optional[str]


# ========== 辅助函数 ==========

async def push_event(client_id: str, event_type: EventType, data: dict):
    """推送 WebSocket 事件"""
    await manager.send(client_id, event_type, data)


async def push_row(client_id: str, table_id: str, row: dict, row_index: int):
    """推送单行数据"""
    logger.debug(f"[PushRow] Sending row {row_index}: {row}")
    await push_event(client_id, EventType.ROW_COMPLETE, {
        "table_id": table_id,
        "row": row,
        "row_index": row_index
    })


async def push_error(client_id: str, task_id: str, error_msg: str):
    """推送错误"""
    await manager.send(client_id, EventType.ERROR, {
        "task_id": task_id,
        "code": 500,
        "msg": error_msg
    })


# ========== 节点函数 ==========

async def router_node(state: AgentState) -> AgentState:
    """
    路由节点 - 根据任务类型决定下一步
    """
    task_type = state.get("task_type")
    file_name = state.get("file_name", "")
    
    logger.info(f"[Router] Task: {state['task_id']}, Type: {task_type}, File: {file_name}")
    
    # 推送任务开始
    await push_event(state["client_id"], EventType.TASK_START, {
        "task_id": state["task_id"],
        "type": task_type,
        "message": "开始处理..."
    })
    
    if task_type == "extract":
        if file_name:
            ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
            if ext in ['xlsx', 'xls', 'csv']:
                state["next_node"] = "excel_node"
            elif ext in ['docx', 'doc']:
                state["next_node"] = "word_node"
            elif ext in ['pdf']:
                state["next_node"] = "ocr_node"
            elif ext in ['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp']:
                state["next_node"] = "ocr_node"
            elif ext in ['pptx', 'ppt']:
                state["next_node"] = "ocr_node"
            else:
                state["next_node"] = "ocr_node"
        else:
            state["error"] = "缺少文件"
            state["next_node"] = "end"
    elif task_type == "audio":
        state["next_node"] = "audio_node"
    elif task_type == "chat":
        state["next_node"] = "chat_node"
    else:
        state["error"] = f"未知任务类型: {task_type}"
        state["next_node"] = "end"
    
    logger.info(f"[Router] Next node: {state.get('next_node')}")
    return state


async def ocr_node(state: AgentState) -> AgentState:
    """
    OCR 节点 - 智能视觉识别（自动检测手写/打印体）
    """
    from app.services.aliyun_ocr import ocr_service
    
    logger.info(f"[OCR] Processing task {state['task_id']}")
    
    try:
        file_content = state.get("file_content")
        if not file_content:
            raise ValueError("缺少文件内容")
        
        # 1. 检测内容类型（手写/打印/混合）
        # === 智能分流策略：默认走快速OCR（Fail-fast） ===
        # 原理：传统OCR识别手写体时，置信度(avg_confidence)通常极低。
        # 策略：
        # 1. 先跑快速 OCR (OpenAPI)。
        # 2. 如果 置信度 > 80：判定为印刷体，直接使用。
        # 3. 如果 置信度 <= 80 或 无结果：判定为手写/疑难，回退 VL 模型。
        
        await push_event(state["client_id"], EventType.CHAT_MESSAGE, {
            "role": "agent",
            "content": "📄 正在进行印刷体 OCR（快路径）..."
        })

        ocr_notes = []
        content_type = "printed"
        ocr_text = ""
        avg_confidence = 0.0
        low_conf_ratio = 0.0

        try:
            # 返回值：(文本, 平均置信度, 低分占比)
            ocr_text, avg_confidence, low_conf_ratio = await ocr_service.recognize_general(image_data=file_content)
        except Exception as e:
            logger.warning(f"[OCR] Printed OCR failed, fallback handwriting: {str(e)}")
            ocr_text = ""
            avg_confidence = 0.0
            low_conf_ratio = 1.0

        # === 智能判别逻辑 ===
        # 1. 没认出东西 -> 肯定是疑难杂症/手写
        # 2. 局部低分占比过高 (>5%) -> 说明有手写填空 (即使只有几个字也可能是关键信息)
        # 3. 整体置信度过低 (<80) -> 说明图片整体质量差或全是潦草手写
        
        is_poor_quality = (
            not ocr_text or 
            low_conf_ratio > 0.05 or 
            avg_confidence < 80.0
        )
        
        if is_poor_quality:
            reason = []
            if not ocr_text: reason.append("结果为空")
            if low_conf_ratio > 0.05: reason.append(f"局部低分占比高({low_conf_ratio:.1%})")
            if avg_confidence < 80.0: reason.append(f"整体置信度低({avg_confidence:.1f})")
            
            await push_event(state["client_id"], EventType.CHAT_MESSAGE, {
                "role": "agent",
                "content": f"✍️ 判定为混合/手写单据 ({', '.join(reason)})，切换 VL 模型..."
            })
            content_type = "handwriting"
            ocr_text, ocr_notes = await ocr_service.recognize_order_handwriting(image_data=file_content)
        else:
            logger.info(f"[OCR] High quality (conf={avg_confidence:.1f}, low_ratio={low_conf_ratio:.1%}), skipping VL.")
        
        state["ocr_text"] = ocr_text
        state["ocr_notes"] = ocr_notes  # 保存识别备注供后续校对参考
        state["content_type"] = content_type
        
        # 3. 如果有识别备注，通知前端
        if ocr_notes:
            await push_event(state["client_id"], EventType.CHAT_MESSAGE, {
                "role": "agent",
                "content": f"📋 识别备注: {'; '.join(ocr_notes)}"
            })
        
        logger.info(f"[OCR] Result ({content_type}): {ocr_text[:100] if ocr_text else 'empty'}...")
        
        state["next_node"] = "llm_node"
        
    except Exception as e:
        logger.error(f"[OCR] Failed: {str(e)}")
        state["error"] = str(e)
        state["next_node"] = "end"
    
    return state


async def excel_node(state: AgentState) -> AgentState:
    """
    Excel 节点 - 使用 FastTools 解析 Excel/CSV，转为文本交给 LLM 标准化
    """
    from app.agents.tools.fast_tools import fast_tools
    import json
    
    logger.info(f"[Excel] Processing task {state['task_id']}")
    
    try:
        file_content = state.get("file_content")
        file_name = state.get("file_name", "")
        
        if not file_content:
            raise ValueError("缺少文件内容")
        
        # 使用 FastTools 解析
        result = fast_tools.parse_excel(file_content, file_name)
        
        if result.success and result.rows:
            # 将提取的行转换为 JSON 字符串或 Markdown，交给 LLM 进行标准化清洗
            # 这样能自动处理序号、规格/单位拆分等逻辑
            state["ocr_text"] = json.dumps(result.rows, ensure_ascii=False)
            state["next_node"] = "llm_node"
            logger.info(f"[Excel] Parsed {len(result.rows)} rows, passing to LLM for standardization")
        else:
            state["error"] = result.message or "Excel 解析失败或为空"
            state["next_node"] = "end"
        
    except Exception as e:
        logger.error(f"[Excel] Failed: {str(e)}")
        state["error"] = str(e)
        state["next_node"] = "end"
    
    return state


async def word_node(state: AgentState) -> AgentState:
    """
    Word 节点 - 使用 FastTools 解析 Word 文档，内容交给 LLM
    """
    from app.agents.tools.fast_tools import fast_tools
    import json
    
    logger.info(f"[Word] Processing task {state['task_id']}")
    
    try:
        file_content = state.get("file_content")
        if not file_content:
            raise ValueError("缺少文件内容")
        
        # 使用 FastTools 解析
        result = fast_tools.parse_word(file_content)
        
        if result.success:
            content_for_llm = ""
            if result.rows:
                # 表格内容转 JSON 字符串
                content_for_llm = json.dumps(result.rows, ensure_ascii=False)
                logger.info(f"[Word] Extracted {len(result.rows)} rows from tables")
            elif result.message:
                # 纯文本内容
                content_for_llm = result.message
                logger.info(f"[Word] Extracted text content")
            
            if content_for_llm:
                state["ocr_text"] = content_for_llm
                state["next_node"] = "llm_node"
            else:
                state["error"] = "Word 文档内容为空"
                state["next_node"] = "end"
        else:
            state["error"] = result.message
            state["next_node"] = "end"
        
    except Exception as e:
        logger.error(f"[Word] Failed: {str(e)}")
        state["error"] = str(e)
        state["next_node"] = "end"
    
    return state


async def llm_node(state: AgentState) -> AgentState:
    """
    LLM 节点 - 将文本转换为结构化 JSON
    """
    from app.agents.nodes.llm_node import format_to_json
    
    logger.info(f"[LLM] Processing task {state['task_id']}")
    
    try:
        ocr_text = state.get("ocr_text", "")
        if not ocr_text:
            raise ValueError("没有待处理的文本")
        
        await push_event(state["client_id"], EventType.CHAT_MESSAGE, {
            "role": "agent",
            "content": "正在提取结构化数据..."
        })
        
        # 格式化为 JSON
        rows = []
        async for row in format_to_json(ocr_text):
            if "_error" not in row:
                rows.append(row)
        
        state["extracted_rows"] = rows
        state["next_node"] = "push_rows_node"
        
        logger.info(f"[LLM] Extracted {len(rows)} rows")
        
    except Exception as e:
        logger.error(f"[LLM] Failed: {str(e)}")
        state["error"] = str(e)
        state["next_node"] = "end"
    
    return state


async def push_rows_node(state: AgentState) -> AgentState:
    """
    推送行节点 - 逐行推送数据到前端
    """
    from app.core.templates import DEFAULT_SCHEMA, map_row_to_template
    
    logger.info(f"[PushRows] Task {state['task_id']}")
    
    raw_rows = state.get("extracted_rows", [])
    table_id = state.get("table_id")
    client_id = state["client_id"]
    
    if not raw_rows:
        await push_event(client_id, EventType.CHAT_MESSAGE, {
            "role": "agent",
            "content": "⚠️ 未能提取到有效数据"
        })
        state["next_node"] = "end"
        return state
    
    # 强制使用固定 Schema
    schema = DEFAULT_SCHEMA
    
    # 发送 TABLE_REPLACE 来更新 schema（使用空数据），让前端准备好接收
    if table_id:
        await push_event(client_id, EventType.TABLE_REPLACE, {
            "table_id": table_id,
            "rows": [],  # 先清空，后面逐行添加
            "schema": schema,
        })
    else:
        # 生成一个真实的 table_id
        import time
        table_id = f"sheet_{int(time.time() * 1000)}"
        
        # 创建新表，发送真实的 table_id
        await push_event(client_id, EventType.TABLE_CREATE, {
            "table_id": table_id,
            "title": f"导入数据 - {state.get('file_name', '未命名')}",
            "source": state.get("file_name"),
            "schema": schema,
        })
        # 记录回 state，便于 TASK_FINISH / 后续节点使用
        state["table_id"] = table_id
    
    # 逐行清洗并推送
    valid_rows = []
    for idx, raw_row in enumerate(raw_rows):
        # 调试：打印原始 key 的 hex，检查是否有不可见字符
        if idx == 0:
            logger.debug(f"[PushRows] First row keys hex: {{k: k.encode('utf-8').hex() for k in raw_row.keys()}}")
            
        # 无论数据来源（Excel/OCR），都映射到标准模板
        normalized_row = map_row_to_template(raw_row)
        await push_row(client_id, table_id, normalized_row, idx)
        valid_rows.append(normalized_row)
    
    # 更新 state 中的 extracted_rows 为标准化后的数据，供 calibration_node 使用
    state["extracted_rows"] = valid_rows
    
    await push_event(client_id, EventType.CHAT_MESSAGE, {
        "role": "agent",
        "content": f"✅ 已提取 {len(valid_rows)} 行数据（先填表，后台校对中…）"
    })

    # === 关键改动：校对改为后台异步，不阻塞“填表完成”的视觉反馈 ===
    # 这样前端会更快收到 TASK_FINISH（并停止 isStreaming），校对结果随后逐条推送。
    import asyncio

    async def _run_calibration_background(cal_state: AgentState):
        try:
            # 复用现有校对节点逻辑
            await calibration_node(cal_state)
        except Exception as e:
            logger.error(f"[CalibrationBg] Failed: {str(e)}")
            await push_event(cal_state["client_id"], EventType.CHAT_MESSAGE, {
                "role": "agent",
                "content": f"⚠️ 校对流程异常（不影响填表）：{str(e)}"
            })

    # 仅保留校对所需字段，避免把大文件内容带入后台任务
    cal_state: AgentState = {
        "task_id": state["task_id"],
        "client_id": state["client_id"],
        "task_type": state["task_type"],
        "file_content": None,
        "file_name": state.get("file_name"),
        "text_content": state.get("text_content"),
        "ocr_text": state.get("ocr_text"),
        "ocr_notes": state.get("ocr_notes"),
        "content_type": state.get("content_type"),
        "extracted_rows": valid_rows,
        "table_id": table_id,
        "table_context": state.get("table_context"),
        "next_node": None,
        "error": None,
    }
    asyncio.create_task(_run_calibration_background(cal_state))

    # 直接结束任务（不等校对）
    state["next_node"] = "end"
    return state


async def calibration_node(state: AgentState) -> AgentState:
    """
    校准节点 - 分流处理打印体/手写体
    
    【打印体】纯程序处理（极快）：
    - 精确匹配 → 直接填入"订单商品"
    - 模糊匹配 → 显示多个候选
    
    【手写体】程序 + Turbo：
    - 精确匹配 → 直接填入"订单商品"
    - 模糊候选 + Turbo 推断 → 智能推断结果
    """
    from app.services.knowledge_base import vector_store
    from app.services.aliyun_llm import llm_service
    from app.core.templates import HANDWRITING_CALIBRATION_PROMPT
    
    logger.info(f"[Calibration] Task {state['task_id']}")
    
    rows = state.get("extracted_rows", [])
    client_id = state["client_id"]
    table_id = state.get("table_id", "new")
    content_type = state.get("content_type", "printed")  # 默认为打印体
    
    if not rows:
        state["next_node"] = "end"
        return state
    
    # 判断是否为手写体
    is_handwriting = content_type in ["handwriting", "mixed"]
    
    await push_event(client_id, EventType.CHAT_MESSAGE, {
        "role": "agent",
        "content": f"🔍 正在校对... ({'手写识别模式' if is_handwriting else '打印识别模式'})"
    })
    
    product_field = "识别商品"
    exact_match_count = 0
    fuzzy_match_count = 0
    need_llm_items = []  # 手写体需要 LLM 推断的项
    
    # === 程序快速匹配（打印体和手写体都先执行）===
    for idx, row in enumerate(rows):
        product_name = str(row.get(product_field, "")).strip()
        order_product = ""
        note = ""
        
        if not product_name:
            continue
        
        try:
            # 尝试从知识库匹配
            result = await vector_store.calibrate(product_name)
            
            # 精确匹配（置信度 > 0.95）
            if result.confidence >= 0.95:
                order_product = result.calibrated
                exact_match_count += 1
                if result.product and result.product.price == 0:
                    note = "⚠️ 无价格"
            
            # 高置信度模糊匹配（0.8 - 0.95）
            elif result.confidence >= 0.8:
                order_product = result.calibrated
                fuzzy_match_count += 1
            
            # 中等置信度（0.5 - 0.8）
            elif result.confidence >= 0.5:
                if is_handwriting:
                    # 手写体：收集候选，交给 LLM 推断
                    candidates = [result.calibrated] + (result.candidates or [])[:4]
                    need_llm_items.append({
                        "idx": idx,
                        "original": product_name,
                        "candidates": candidates
                    })
                    order_product = f"⏳ AI分析中..."
                else:
                    # 打印体：直接显示候选
                    candidates = [result.calibrated] + (result.candidates or [])[:2]
                    order_product = f"❓ 可能: {' / '.join(candidates)}"
                    fuzzy_match_count += 1
            
            # 低置信度（0.3 - 0.5）
            elif result.confidence >= 0.3:
                if is_handwriting and result.candidates:
                    # 手写体：收集候选，交给 LLM
                    need_llm_items.append({
                        "idx": idx,
                        "original": product_name,
                        "candidates": result.candidates[:5]
                    })
                    order_product = f"⏳ AI分析中..."
                elif result.candidates:
                    # 打印体：显示多个候选
                    order_product = f"❓ 可能: {' / '.join(result.candidates[:3])}"
                else:
                    order_product = "❌ 未找到匹配"
            
            # 极低置信度（< 0.3）
            else:
                if is_handwriting:
                    # 手写体：即使没有候选也尝试让 LLM 分析
                    need_llm_items.append({
                        "idx": idx,
                        "original": product_name,
                        "candidates": result.candidates[:5] if result.candidates else []
                    })
                    order_product = f"⏳ AI分析中..."
                else:
                    order_product = "❌ 库中未找到"
                    
        except Exception as e:
            logger.debug(f"[Calibration] Match failed for row {idx}: {str(e)}")
            order_product = "❓ 匹配异常"
        
        # 推送校对结果
        if order_product:
            await push_event(client_id, EventType.CELL_UPDATE, {
                "table_id": table_id,
                "row_index": idx,
                "col_key": "订单商品",
                "value": order_product
            })
        
        if note:
            await push_event(client_id, EventType.CELL_UPDATE, {
                "table_id": table_id,
                "row_index": idx,
                "col_key": "_calibration_note",
                "value": note
            })
    
    # === 手写体：LLM 智能推断 ===
    if need_llm_items and is_handwriting:
        await push_event(client_id, EventType.CHAT_MESSAGE, {
            "role": "agent",
            "content": f"🤖 AI 正在分析 {len(need_llm_items)} 个手写商品名..."
        })
        
        for item in need_llm_items:
            try:
                candidates_str = "\n".join([f"- {c}" for c in item['candidates']]) if item['candidates'] else "（无候选）"
                
                prompt = HANDWRITING_CALIBRATION_PROMPT.format(
                    recognized_name=item['original'],
                    candidates=candidates_str
                )
                
                # 调用 Turbo 模型推断
                llm_result = await llm_service.call_turbo_model(
                    messages=[
                        {"role": "system", "content": "你是商品名称校对专家，擅长分析手写字迹。只输出 JSON。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1
                )
                
                # 解析 LLM 结果
                order_product = _parse_calibration_result(llm_result, item['original'])
                
                await push_event(client_id, EventType.CELL_UPDATE, {
                    "table_id": table_id,
                    "row_index": item['idx'],
                    "col_key": "订单商品",
                    "value": order_product
                })
                
            except Exception as e:
                logger.error(f"[Calibration] LLM failed for row {item['idx']}: {str(e)}")
                await push_event(client_id, EventType.CELL_UPDATE, {
                    "table_id": table_id,
                    "row_index": item['idx'],
                    "col_key": "订单商品",
                    "value": "❌ AI分析失败"
                })
    
    # 汇总通知
    total_rows = len(rows)
    summary_parts = []
    if exact_match_count > 0:
        summary_parts.append(f"精确匹配 {exact_match_count} 项")
    if fuzzy_match_count > 0:
        summary_parts.append(f"模糊匹配 {fuzzy_match_count} 项")
    if need_llm_items:
        summary_parts.append(f"AI推断 {len(need_llm_items)} 项")
    
    summary = "、".join(summary_parts) if summary_parts else "无匹配"
    
    await push_event(client_id, EventType.CHAT_MESSAGE, {
        "role": "agent",
        "content": f"✅ 校对完成: {total_rows} 行数据 ({summary})"
    })
    
    state["next_node"] = "end"
    return state


def _parse_calibration_result(llm_result: str, original: str) -> str:
    """解析 LLM 校对结果"""
    import json
    
    try:
        # 尝试解析 JSON
        result = llm_result.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        
        data = json.loads(result)
        
        if data.get("match"):
            confidence = data.get("confidence", "中")
            if confidence == "高":
                return data["match"]
            else:
                return f"✅ {data['match']}"
        elif data.get("candidates"):
            return f"❓ 可能: {' / '.join(data['candidates'][:3])}"
        elif data.get("note"):
            return f"❌ {data['note']}"
        else:
            return f"❓ {original}"
            
    except Exception:
        # JSON 解析失败，尝试直接使用文本
        if "✅" in llm_result or "→" in llm_result:
            return llm_result.strip()[:50]
        elif "❓" in llm_result:
            return llm_result.strip()[:50]
        elif "❌" in llm_result:
            return llm_result.strip()[:50]
        else:
            return f"❓ {original}"


async def audio_node(state: AgentState) -> AgentState:
    """
    音频节点 - 语音识别和指令处理
    """
    from app.services.aliyun_asr import asr_service
    from app.services.aliyun_llm import llm_service
    
    logger.info(f"[Audio] Processing task {state['task_id']}")
    
    try:
        file_content = state.get("file_content")
        if not file_content:
            raise ValueError("缺少音频内容")
        
        # ASR 识别
        asr_text = await asr_service.recognize_audio(file_content)
        logger.info(f"[Audio] ASR result: {asr_text}")
        
        # 推送用户语音文本
        await push_event(state["client_id"], EventType.CHAT_MESSAGE, {
            "role": "user",
            "content": asr_text,
            "is_voice": True
        })
        
        # LLM 理解指令
        system_prompt = """你是智能表单助手。分析用户指令，输出 JSON 工具调用。

可用工具：
- update_cell: {"tool": "update_cell", "params": {"row_index": 0, "key": "字段名", "value": "新值"}}
- add_row: {"tool": "add_row", "params": {"data": {"product": "商品", "quantity": 10}}}
- delete_row: {"tool": "delete_row", "params": {"row_index": 0}}

如果不是操作指令，直接回复文本。"""
        
        response = await llm_service.call_main_model([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": asr_text}
        ])
        
        # 解析响应
        clean = response.strip().replace("```json", "").replace("```", "").strip()
        
        if clean.startswith("{") and "tool" in clean:
            try:
                tool_call = json.loads(clean)
                tool_name = tool_call.get("tool")
                params = tool_call.get("params", {})
                
                await push_event(state["client_id"], EventType.TOOL_CALL, {
                    "tool": tool_name,
                    "params": params
                })
                
                await push_event(state["client_id"], EventType.CHAT_MESSAGE, {
                    "role": "agent",
                    "content": f"已执行: {tool_name}"
                })
            except json.JSONDecodeError:
                await push_event(state["client_id"], EventType.CHAT_MESSAGE, {
                    "role": "agent",
                    "content": response
                })
        else:
            await push_event(state["client_id"], EventType.CHAT_MESSAGE, {
                "role": "agent",
                "content": response
            })
        
    except Exception as e:
        logger.error(f"[Audio] Failed: {str(e)}")
        state["error"] = str(e)
    
    state["next_node"] = "end"
    return state


async def chat_node(state: AgentState) -> AgentState:
    """
    聊天节点 - 使用 Function Calling 让大模型决定调用工具
    
    流程：
    1. 所有用户消息 + 工具定义 发给主控大模型
    2. 大模型决定：调用工具 or 直接回复
    3. 如果调用工具，执行后返回结果给用户
    """
    from app.services.aliyun_llm import llm_service
    from app.agents.context_manager import context_manager
    from app.agents.tools.fast_tools import fast_tools
    
    logger.info(f"[Chat] Processing task {state['task_id']}")
    
    client_id = state["client_id"]
    text = state.get("text_content", "")
    table_context = state.get("table_context")
    table_id = state.get("table_id")
    
    try:
        if not text:
            raise ValueError("缺少聊天内容")
        
        # 获取会话上下文
        ctx = context_manager.get_context(client_id)
        ctx.add_user_message(text)
        
        # 构建表格上下文描述
        table_info = "【当前画布上的表格】\n"
        if table_context and table_context.get("tables"):
            tables = table_context.get("tables", {})
            active_table_id = table_context.get("activeTableId")
            
            if not tables:
                table_info += "暂无表格\n"
            else:
                for idx, (tid, table) in enumerate(tables.items()):
                    rows = table.get("rows", [])
                    is_active = "(当前激活)" if tid == active_table_id else ""
                    table_info += f"{idx+1}. ID: {tid} | 标题: {table.get('title', '未命名')} | {len(rows)} 行数据 {is_active}\n"
                    
                    # 如果是激活的表格，展示部分数据作为参考
                    if tid == active_table_id and rows:
                        sample_rows = rows[:3]
                        table_info += f"   示例数据: {json.dumps(sample_rows, ensure_ascii=False)[:500]}\n"
        else:
            table_info += "暂无表格信息\n"
        
        # 系统提示词
        system_prompt = f"""你是智能订单助手，帮助用户处理订单和商品数据。

【对话历史】
{ctx.get_context_for_llm(n=5)}
{table_info}

【重要规则】
- **默认表格**：用户未明确指定表格时，所有操作默认在"当前激活"的表格上执行，无需询问用户。
- **行号规则**："第一行"对应 row_index=1，"第二行"对应 row_index=2，以此类推。

【你可以做的】
- **智能填表**：如果用户发来一段包含商品和数量的文本（如"土豆 50斤，白菜 20斤"），请直接调用 `smart_fill` 工具，将用户输入的原始文本原样传进去，不要自行提取。
- **查询商品**：如果用户问"有没有土豆"或"土豆多少钱"，请调用 `query_product`。
- **操作表格**：新建表格、添加行、删除行、修改单元格（不用传 table_id，默认操作当前表格）。
- **统计计算**：计算总价、数量合计等。
- 闲聊咨询直接回复即可。

【暂不支持的操作】
以下操作需要用户手动在界面上完成，如果用户尝试这些操作，请友好提示：
- 导出表格/下载订单 → 请点击顶部"导出全部"按钮，或右键菜单"导出此 Sheet"
- 关闭/删除表格 → 请点击 Tab 页签上的 X 按钮
- 修改订单日期/时间 → 请在表格上方的时间输入框中修改
- 选择客户/餐厅/订单类型 → 请使用表格上方的下拉框选择

用简洁友好的中文回复。"""

        # 定义可用工具
        tools = _get_chat_tools()
        
        # 调用带工具的主控大模型
        result = await llm_service.call_with_tools(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            tools=tools
        )
        
        # 处理结果
        if result.get("tool_calls"):
            # 大模型决定调用工具
            tool_responses = []
            for tool_call in result["tool_calls"]:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("arguments", {})
                
                # 解析参数（可能是 JSON 字符串）
                if isinstance(tool_args, str):
                    try:
                        tool_args = json.loads(tool_args)
                    except:
                        tool_args = {}
                
                logger.info(f"[Chat] Executing tool: {tool_name} with args: {tool_args}")
                
                # 执行工具
                tool_result = await _execute_tool(
                    tool_name, tool_args, client_id, table_id, table_context, fast_tools
                )
                tool_responses.append(tool_result)
            
            # 合并工具结果作为回复
            final_response = "\n\n".join(tool_responses)
        else:
            # 直接使用文本回复
            final_response = result.get("content", "")
        
        if final_response:
            await push_event(client_id, EventType.CHAT_MESSAGE, {
                "role": "agent",
                "content": final_response
            })
            ctx.add_agent_message(final_response)
        
    except Exception as e:
        logger.error(f"[Chat] Failed: {str(e)}")
        await push_event(client_id, EventType.CHAT_MESSAGE, {
            "role": "agent",
            "content": f"抱歉，处理消息时出错了：{str(e)}"
        })
        state["error"] = str(e)
    
    state["next_node"] = "end"
    return state


def _get_chat_tools() -> List[Dict]:
    """获取聊天可用的工具定义"""
    return [
        {
            "type": "function",
            "function": {
                "name": "create_table",
                "description": "创建一个新的表格。当用户说'新建表格'、'创建表格'、'建一个表'时调用",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "表格标题，如'商品订单'、'采购清单'"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "smart_fill",
                "description": "智能填表工具。当用户在对话中发送一段包含订单信息的文本（如'我要土豆50斤，白菜30斤...'）时调用。请将用户的原始文本直接传给此工具，不要自行提取。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "用户输入的原始订单文本"
                        },
                        "table_id": {
                            "type": "string",
                            "description": "目标表格ID（可选）"
                        }
                    },
                    "required": ["text"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_product",
                "description": "从商品库中查询商品信息。当用户问'有没有XX'、'查一下XX'、'XX多少钱'时调用",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_name": {
                            "type": "string",
                            "description": "要查询的商品名称"
                        }
                    },
                    "required": ["product_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "calculate_total",
                "description": "计算表格数据的统计信息。当用户问'总共多少钱'、'合计'、'统计'时调用",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["total", "count", "average"],
                            "description": "计算类型：total(总价), count(数量), average(平均)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "modify_cell",
                "description": "修改表格中的某个单元格。当用户说'把XX改成YY'、'修改第X行'时调用",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table_id": {
                            "type": "string",
                            "description": "目标表格ID。如果不指定，默认操作当前激活的表格；如果用户指定了特定表格（如'采购单'），请传入对应的ID"
                        },
                        "row_index": {
                            "type": "integer",
                            "description": "行号（从1开始）"
                        },
                        "column": {
                            "type": "string",
                            "description": "列名，如'商品名称'、'数量'、'单价'"
                        },
                        "value": {
                            "type": "string",
                            "description": "新的值"
                        }
                    },
                    "required": ["row_index", "column", "value"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "add_row",
                "description": "向表格添加一行数据。当用户说'添加一行'、'加上XX'时调用",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table_id": {
                            "type": "string",
                            "description": "目标表格ID。如果不指定，默认操作当前激活的表格"
                        },
                        "data": {
                            "type": "object",
                            "description": "行数据，如 {\"商品名称\": \"苹果\", \"数量\": 10}"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_row",
                "description": "删除表格中的一行。当用户说'删除第X行'、'去掉最后一行'时调用",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table_id": {
                            "type": "string",
                            "description": "目标表格ID。如果不指定，默认操作当前激活的表格"
                        },
                        "row_index": {
                            "type": "integer",
                            "description": "行号（从1开始），-1表示最后一行"
                        }
                    },
                    "required": ["row_index"]
                }
            }
        }
    ]


async def _execute_tool(
    tool_name: str,
    args: Dict,
    client_id: str,
    table_id: str,
    table_context: dict,
    fast_tools
) -> str:
    """执行工具并返回结果"""
    
    if tool_name == "create_table":
        title = args.get("title", "新表格")
        # 推送创建表格事件
        await push_event(client_id, EventType.TOOL_CALL, {
            "tool": "create_table",
            "params": {"title": title}
        })
        return f"✅ 已为你创建表格「{title}」"
    
    elif tool_name == "query_product":
        product_name = args.get("product_name", "")
        if not product_name:
            return "❓ 请告诉我要查询什么商品"
        
        products = fast_tools.quick_product_lookup(product_name, limit=5)
        
        if products:
            result_lines = [f"🔍 关于「{product_name}」的查询结果：\n"]
            for p in products[:5]:
                price_info = f"¥{p['price']}" if p['price'] > 0 else "无价格信息"
                result_lines.append(f"• **{p['name']}** - {p['unit']} - {price_info}")
                if p.get('spec'):
                    result_lines[-1] += f" ({p['spec']})"
            return "\n".join(result_lines)
        else:
            return f"🔍 在商品库中未找到「{product_name}」相关商品"
    
    elif tool_name == "calculate_total":
        if not table_context or not table_context.get("rows"):
            return "📊 当前没有表格数据可供计算。请先选择一个表格。"
        
        from app.agents.consultative_agent import consultative_agent
        operation = args.get("operation", "total")
        calc_result = await consultative_agent.calculate(operation, table_context)
        return calc_result.answer
    
    elif tool_name == "modify_cell":
        row_index = args.get("row_index", 1) - 1  # 转为 0-based
        column = args.get("column", "")
        value = args.get("value", "")
        target_table_id = args.get("table_id")
        
        # 优先使用工具参数中的 table_id，其次使用上下文中的表格ID，最后使用 table_id 参数
        context_table_id = None
        if table_context:
            context_table_id = table_context.get("activeTableId") or table_context.get("id")
            
        final_table_id = target_table_id or context_table_id or table_id
        
        if not final_table_id:
            return "❓ 请先选择要修改的表格"
        
        # 推送修改事件
        await push_event(client_id, EventType.TOOL_CALL, {
            "tool": "update_cell",
            "params": {
                "table_id": final_table_id,
                "row_index": row_index,
                "key": column,
                "value": value
            }
        })
        return f"✅ 已将第 {row_index + 1} 行的「{column}」改为「{value}」"
    
    elif tool_name == "smart_fill":
        from app.services.aliyun_llm import llm_service
        
        text = args.get("text", "")
        target_table_id = args.get("table_id")
        
        context_table_id = None
        if table_context:
            context_table_id = table_context.get("activeTableId") or table_context.get("id")
            
        final_table_id = target_table_id or context_table_id or table_id
        
        if not final_table_id:
            # 如果没有表格，生成一个临时的 ID
            final_table_id = f"table_{generate_trace_id()[:8]}"
            
        # 1. 调用提取模型 (Turbo)
        logger.info(f"[SmartFill] Extracting from text: {text[:50]}...")
        extraction_prompt = UNSTRUCTURED_EXTRACTION_PROMPT.format(text=text)
        
        try:
            # 使用 Turbo 模型进行提取
            extracted_json_str = await llm_service.call_turbo_model(
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.1
            )
            import json
            extracted_rows = json.loads(extracted_json_str)
            
            if not isinstance(extracted_rows, list):
                extracted_rows = [extracted_rows]
                
            logger.info(f"[SmartFill] Extracted {len(extracted_rows)} rows")
            
            if not extracted_rows:
                return "⚠️ 未能从文本中提取到有效数据"

            # 2. 逐行推送
            valid_count = 0
            for idx, raw_row in enumerate(extracted_rows):
                # 映射到模板
                normalized_row = map_row_to_template(raw_row)
                if "识别商品" not in normalized_row and "品名" in raw_row:
                    normalized_row["识别商品"] = raw_row["品名"]
                
                # 推送
                await push_row(client_id, final_table_id, normalized_row, idx)
                valid_count += 1
                
                # 3. 触发轻量级校对
                try:
                    product_name = normalized_row.get("识别商品", "")
                    if product_name:
                        from app.services.knowledge_base import vector_store
                        from app.services.handwriting_hints import CalibrationThresholds
                        
                        result = await vector_store.calibrate(str(product_name))
                        confidence_level = CalibrationThresholds.get_level(result.confidence)
                        
                        calibrated_field = "订单商品"
                        note = ""
                        
                        if confidence_level == 'high':
                            await push_event(client_id, EventType.CELL_UPDATE, {
                                "table_id": final_table_id,
                                "row_index": idx,
                                "col_key": calibrated_field,
                                "value": result.calibrated
                            })
                        elif confidence_level == 'medium':
                            if result.suggestion:
                                note = result.suggestion
                        elif confidence_level == 'low':
                            note = f"❓建议: {', '.join(result.candidates[:3])}" if result.candidates else "❓未找到"
                        
                        if note:
                            await push_event(client_id, EventType.CELL_UPDATE, {
                                "table_id": final_table_id,
                                "row_index": idx,
                                "col_key": calibrated_field,
                                "value": note
                            })
                            await push_event(client_id, EventType.CALIBRATION_NOTE, {
                                "table_id": final_table_id,
                                "row_index": idx,
                                "note": note,
                                "severity": "warning"
                            })
                except Exception as e:
                    logger.warning(f"[SmartFill] Calibration error for row {idx}: {e}")

            return f"✅ 已成功提取并录入 {valid_count} 条数据"
            
        except Exception as e:
            logger.error(f"[SmartFill] Failed: {e}")
            return f"❌ 提取失败: {str(e)}"

    elif tool_name == "add_row":
        data = args.get("data", {})
        target_table_id = args.get("table_id")
        
        context_table_id = None
        if table_context:
            context_table_id = table_context.get("activeTableId") or table_context.get("id")
            
        final_table_id = target_table_id or context_table_id or table_id
        
        if not final_table_id:
            return "❓ 请先选择要添加数据的表格"
        
        await push_event(client_id, EventType.TOOL_CALL, {
            "tool": "add_row",
            "params": {
                "table_id": final_table_id,
                "data": data
            }
        })
        return f"✅ 已添加一行数据"
    
    elif tool_name == "delete_row":
        row_index = args.get("row_index", -1)
        if row_index > 0:
            row_index -= 1  # 转为 0-based
        
        target_table_id = args.get("table_id")
        context_table_id = None
        if table_context:
            context_table_id = table_context.get("activeTableId") or table_context.get("id")
            
        final_table_id = target_table_id or context_table_id or table_id
        
        if not final_table_id:
            return "❓ 请先选择要删除数据的表格"
        
        await push_event(client_id, EventType.TOOL_CALL, {
            "tool": "delete_row",
            "params": {
                "table_id": final_table_id,
                "row_index": row_index
            }
        })
        row_desc = "最后一行" if row_index == -1 else f"第 {row_index + 1} 行"
        return f"✅ 已删除{row_desc}"
    
    else:
        return f"❓ 未知工具: {tool_name}"


async def action_agent(state: AgentState) -> AgentState:
    """
    操作 Agent - 使用 AgentTools 处理增删改操作
    
    流程：
    1. 使用意图分类器提取的参数（如果有）
    2. 参数不完整时调用 LLM 补充
    3. 执行工具并推送结果
    """
    from app.services.aliyun_llm import llm_service
    from app.agents.tools.agent_tools import AgentTools, agent_tools, ToolCall
    from app.agents.context_manager import context_manager
    
    logger.info(f"[ActionAgent] Processing task {state['task_id']}")
    
    text = state.get("text_content", "")
    client_id = state["client_id"]
    
    try:
        # 获取上下文
        ctx = context_manager.get_context(client_id)
        
        # 生成工具定义 Prompt
        tools_prompt = agent_tools.generate_tools_prompt()
        
        # 添加上下文信息
        context_info = ""
        if ctx.current_table_id:
            context_info += f"\n当前表格: {ctx.current_table_id}"
        if ctx.current_row_index is not None:
            context_info += f"\n当前选中行: 第{ctx.current_row_index + 1}行"
        
        system_prompt = f"""你是智能表单操作助手。分析用户指令，输出 JSON 工具调用。

{tools_prompt}

{context_info}

重要规则：
1. "第一行"对应 row_index=0，"第二行"对应 row_index=1
2. 如果缺少必要信息，使用 clarify 工具询问
3. 字段名使用中文（如"商品名称"、"数量"、"单价"）"""
        
        # 调用 LLM 获取工具调用
        response = await llm_service.call_main_model([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ])
        
        # 解析工具调用
        tool_call = agent_tools.parse_tool_call(response)
        
        if tool_call:
            logger.info(f"[ActionAgent] Tool call: {tool_call.tool}, params: {tool_call.params}")
            
            # 检查是否是 clarify（需要澄清）
            if tool_call.tool == "clarify":
                question = tool_call.params.get("question", "请提供更多信息")
                await push_event(client_id, EventType.CHAT_MESSAGE, {
                    "role": "agent",
                    "content": question
                })
                ctx.add_agent_message(question)
            else:
                # 执行工具
                execution_context = {
                    "current_table_id": ctx.current_table_id,
                    "current_row_index": ctx.current_row_index,
                }
                result = await agent_tools.execute_tool(tool_call, execution_context)
                
                if result.get("success"):
                    # 推送工具调用给前端
                    await push_event(client_id, EventType.TOOL_CALL, {
                        "tool": tool_call.tool,
                        "params": tool_call.params
                    })
                    
                    # 生成确认消息
                    confirm_msg = agent_tools.generate_confirm_message(tool_call, result)
                    await push_event(client_id, EventType.CHAT_MESSAGE, {
                        "role": "agent",
                        "content": confirm_msg
                    })
                    ctx.add_agent_message(confirm_msg, tool_call=tool_call.to_dict())
                else:
                    # 执行失败
                    error_msg = result.get("message", "操作执行失败")
                    await push_event(client_id, EventType.CHAT_MESSAGE, {
                        "role": "agent",
                        "content": f"❌ {error_msg}"
                    })
        else:
            # 不是工具调用，直接返回 LLM 响应
            await push_event(client_id, EventType.CHAT_MESSAGE, {
                "role": "agent",
                "content": response
            })
            ctx.add_agent_message(response)
        
    except Exception as e:
        logger.error(f"[ActionAgent] Failed: {str(e)}")
        state["error"] = str(e)
        await push_event(client_id, EventType.CHAT_MESSAGE, {
            "role": "agent",
            "content": f"抱歉，操作执行出错: {str(e)}"
        })
    
    state["next_node"] = "end"
    return state


async def end_node(state: AgentState) -> AgentState:
    """
    结束节点 - 发送任务完成/失败事件
    """
    task_id = state["task_id"]
    client_id = state["client_id"]
    error = state.get("error")
    table_id = state.get("table_id")
    
    if error:
        await push_error(client_id, task_id, error)
        await push_event(client_id, EventType.TASK_FINISH, {
            "task_id": task_id,
            "status": "error",
            "error": error,
            "table_id": table_id,
        })
    else:
        await push_event(client_id, EventType.TASK_FINISH, {
            "task_id": task_id,
            "status": "success",
            "table_id": table_id,
        })
    
    logger.info(f"[End] Task {task_id} finished, error={error}")
    return state


# ========== 条件路由 ==========

def route_by_next_node(state: AgentState) -> str:
    """根据 next_node 路由"""
    return state.get("next_node", "end")


# ========== 构建工作流 ==========

def create_workflow() -> StateGraph:
    """创建 LangGraph 工作流"""
    
    workflow = StateGraph(AgentState)
    
    # 添加所有节点
    workflow.add_node("router", router_node)
    workflow.add_node("ocr_node", ocr_node)
    workflow.add_node("excel_node", excel_node)
    workflow.add_node("word_node", word_node)
    workflow.add_node("llm_node", llm_node)
    workflow.add_node("push_rows_node", push_rows_node)
    workflow.add_node("calibration_node", calibration_node)
    workflow.add_node("audio_node", audio_node)
    workflow.add_node("action_agent", action_agent)
    workflow.add_node("chat_node", chat_node)
    workflow.add_node("end", end_node)
    
    # 设置入口
    workflow.set_entry_point("router")
    
    # Router 的条件边
    workflow.add_conditional_edges(
        "router",
        route_by_next_node,
        {
            "ocr_node": "ocr_node",
            "excel_node": "excel_node",
            "word_node": "word_node",
            "audio_node": "audio_node",
            "chat_node": "chat_node",
            "end": "end"
        }
    )
    
    # OCR -> LLM
    workflow.add_conditional_edges(
        "ocr_node",
        route_by_next_node,
        {"llm_node": "llm_node", "end": "end"}
    )
    
    # Excel -> LLM (统一清洗)
    workflow.add_conditional_edges(
        "excel_node",
        route_by_next_node,
        {"llm_node": "llm_node", "end": "end"}
    )
    
    # Word -> LLM (统一清洗)
    workflow.add_conditional_edges(
        "word_node",
        route_by_next_node,
        {"llm_node": "llm_node", "end": "end"}
    )
    
    # LLM -> Push
    workflow.add_conditional_edges(
        "llm_node",
        route_by_next_node,
        {"push_rows_node": "push_rows_node", "end": "end"}
    )
    
    # Push -> Calibration
    workflow.add_conditional_edges(
        "push_rows_node",
        route_by_next_node,
        {"calibration_node": "calibration_node", "end": "end"}
    )
    
    # Calibration -> End
    workflow.add_edge("calibration_node", "end")
    
    # Audio -> End
    workflow.add_edge("audio_node", "end")
    
    # Chat -> Action Agent or End
    workflow.add_conditional_edges(
        "chat_node",
        route_by_next_node,
        {"action_agent": "action_agent", "end": "end"}
    )
    
    # Action Agent -> End
    workflow.add_edge("action_agent", "end")
    
    # End -> END
    workflow.add_edge("end", END)
    
    logger.info("LangGraph workflow created (ComfyUI style)")
    return workflow


# 编译工作流
agent_graph = create_workflow().compile()


# ========== 执行入口 ==========

async def run_task(
    task_id: str,
    client_id: str,
    task_type: str,
    file_content: bytes = None,
    file_name: str = None,
    text_content: str = None,
    table_id: str = None,
    table_context: Dict[str, Any] = None,  # 表格上下文（用于咨询分析）
) -> None:
    """
    执行任务 - 供 endpoints 调用
    
    Args:
        task_id: 任务 ID
        client_id: 客户端 ID
        task_type: 任务类型 (extract/audio/chat)
        file_content: 文件内容
        file_name: 文件名
        text_content: 文本内容
        table_id: 目标表格 ID
        table_context: 表格上下文（用于咨询分析）{title, rows, schema, metadata}
    """
    initial_state: AgentState = {
        "task_id": task_id,
        "client_id": client_id,
        "task_type": task_type,
        "file_content": file_content,
        "file_name": file_name,
        "text_content": text_content,
        "ocr_text": None,
        "ocr_notes": [],
        "content_type": None,
        "extracted_rows": [],
        "table_id": table_id,
        "table_context": table_context,  # 传递表格上下文
        "next_node": None,
        "error": None
    }
    
    try:
        await agent_graph.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"[RunTask] Task {task_id} failed: {str(e)}")
        await push_error(client_id, task_id, str(e))
