"""
对话消息处理 Handler
"""
from fastapi import WebSocket
from app.core.logger import app_logger as logger
from app.services.aliyun_llm import llm_service
from app.core.connection_manager import manager
import json
from datetime import datetime, timezone
import traceback

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

async def handle_chat_message(websocket: WebSocket, message: dict, client_id: str):
    """
    处理用户发送的文本消息 (Chat)
    
    Flow:
    1. 接收用户输入
    2. 获取当前上下文 (Optional: 可以从前端传来的 context 中获取当前表格数据)
    3. 调用 LLM 进行意图识别和工具调用
    4. 执行工具并返回结果
    5. 推送回复给前端
    """
    try:
        user_content = message.get("content", "")
        # 前端传来的当前表格数据上下文，用于辅助 LLM 理解
        # context 结构示例: { "rows": [...], "selectedCell": ... }
        context = message.get("context", {})
        
        logger.info(f"收到用户消息: {user_content} (Client: {client_id})")
        
        # 1. 发送思考状态
        await manager.send_message(websocket, {
            "type": "agent_thought",
            "content": "正在思考...",
            "status": "thinking",
            "timestamp": _iso_now()
        })
        
        # 2. 构建 Prompt
        # 如果有表格数据，将其作为上下文提供给 LLM
        rows_context = ""
        if context.get("rows"):
            # 只取前几行或简化数据以节省 Token，这里假设数据量不大
            # 简化为: Index | Key | Value
            rows_data = context.get("rows", [])
            rows_desc = []
            for idx, row in enumerate(rows_data):
                row_str = f"Row {idx}: " + ", ".join([f"{item.get('label', item.get('key'))}={item.get('value')}" for item in row])
                rows_desc.append(row_str)
            rows_context = "\n当前表格数据样本:\n" + "\n".join(rows_desc[:10]) # 限制上下文长度
            
        system_prompt = f"""你是一个智能表单助手，可以帮助用户修改和操作表格数据。
你可以使用以下工具：
1. update_cell(row_index: int, key: str, value: Any): 更新指定单元格的值。
   - row_index: 行号，从 0 开始。
   - key: 字段的键名（如 product_name, quantity, price 等）。
   - value: 新的值。
2. update_table(rows: str): 更新整个表格（通常不建议除非是全量替换）。

{rows_context}

用户的指令如果是修改操作，请务必准确识别行号和字段名。
如果用户只是闲聊，请正常回复。
请直接返回工具调用指令（JSON格式），或者直接回复文本。
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        # 3. 调用 LLM (这里使用 Qwen-Max 进行意图识别和工具调用)
        # 注意：为了简化，这里直接用 Prompt Engineering + JSON Output 模拟工具调用
        # 实际生产中建议使用 LangChain 的 bind_tools
        
        tool_prompt = """
请分析用户意图。
如果是修改表格指令，请输出 JSON 格式的工具调用，格式如下：
{
    "tool": "update_cell",
    "params": {
        "row_index": 0,
        "key": "quantity",
        "value": "100"
    }
}

如果是普通对话，请直接输出回复内容（不要 JSON）。
"""
        messages.append({"role": "user", "content": tool_prompt})
        
        response_content = await llm_service.call_main_model(messages)
        
        # 4. 解析响应
        try:
            # 尝试解析是否为 JSON 工具调用
            # 有时候 LLM 会用 ```json ... ``` 包裹
            clean_content = response_content.replace("```json", "").replace("```", "").strip()
            if clean_content.startswith("{") and "tool" in clean_content:
                tool_call = json.loads(clean_content)
                tool_name = tool_call.get("tool")
                params = tool_call.get("params", {})
                
                if tool_name == "update_cell":
                    row_index = params.get("row_index", 0)
                    key = params.get("key", "")
                    value = params.get("value", "")
                    
                    # 直接构造 action 数据发送给前端，不调用 LangChain 工具
                    action_data = {
                        "action": "update_cell",
                        "rowIndex": row_index,
                        "key": key,
                        "value": value,
                        "confidence": 1.0
                    }
                    
                    # 发送 Tool Action 给前端
                    await manager.send_message(websocket, {
                        "type": "tool_action",
                        "content": f"正在修改第 {row_index + 1} 行数据...",
                        "tool": "update_cell",
                        "params": action_data,  # 前端直接使用这个 params
                        "timestamp": _iso_now()
                    })
                    
                    final_reply = f"已将第 {row_index + 1} 行的 {key} 修改为 {value}。"
                    
                else:
                    final_reply = "抱歉，我暂时不支持这个操作。"

                # 发送最终回复
                await manager.send_message(websocket, {
                    "type": "agent_thought",
                    "content": final_reply,
                    "status": "done",
                    "timestamp": _iso_now()
                })
                
            else:
                # 普通对话
                await manager.send_message(websocket, {
                    "type": "agent_thought",
                    "content": response_content,
                    "status": "done",
                    "timestamp": _iso_now()
                })
                
        except json.JSONDecodeError:
            # 解析失败，当作普通文本回复
             await manager.send_message(websocket, {
                "type": "agent_thought",
                "content": response_content,
                "status": "done",
                "timestamp": _iso_now()
            })

    except Exception as e:
        logger.error(f"处理对话消息失败: {str(e)}\n{traceback.format_exc()}")
        await manager.send_message(websocket, {
            "type": "error",
            "message": f"抱歉，我处理您的请求时遇到了问题: {str(e)}",
            "timestamp": _iso_now()
        })
