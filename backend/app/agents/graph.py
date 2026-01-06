async def audio_flow_node(state: AgentState) -> AgentState:
    """
    音频流节点 - 处理语音指令
    """
    logger.info("[Audio Flow] 开始处理语音指令")
    
    try:
        # Step 1: ASR 识别
        await notify_step_start(state, "ocr", "正在聆听语音指令...")
        
        audio_data = state.get('audio_data')
        if not audio_data:
            raise ValueError("没有收到音频数据")
            
        asr_text = await asr_service.recognize_audio(audio_data)
        state['asr_text'] = asr_text
        
        await notify_step_end(state, "ocr", f"听到: {asr_text}")
        
        # Step 2: 意图理解与工具调用 (复用 Chat 逻辑)
        state['current_step'] = 'analyzing'
        await notify_step_start(state, "analyzing", "正在理解指令...")
        
        # 构造 LLM 请求
        system_prompt = """你是一个智能表单助手，可以帮助用户修改和操作表格数据。
你可以使用以下工具：
1. update_cell(row_index: int, key: str, value: Any): 更新指定单元格的值。
   - row_index: 行号，从 0 开始。
   - key: 字段的键名（如 product_name, quantity, price 等）。
   - value: 新的值。
2. update_table(rows: str): 更新整个表格。

用户的指令通常是基于当前表格的修改操作。
请准确识别行号和字段名。
请输出 JSON 格式的工具调用。
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"用户语音指令：{asr_text}"}
        ]
        
        # 调用 LLM
        response_content = await llm_service.call_main_model(messages)
        
        # 解析工具调用
        import json
        from app.agents.skills.form_skill import update_cell
        
        # 尝试解析 JSON
        clean_content = response_content.replace("```json", "").replace("```", "").strip()
        
        tool_executed = False
        reply_content = response_content
        
        if clean_content.startswith("{") and "tool" in clean_content:
            try:
                tool_call = json.loads(clean_content)
                tool_name = tool_call.get("tool")
                params = tool_call.get("params", {})
                
                if tool_name == "update_cell":
                    # 发送工具调用通知
                    if state.get('client_id'):
                        await manager.send_to_client(state['client_id'], {
                            "type": "tool_action",
                            "content": f"根据语音指令修改第 {params.get('row_index')+1} 行...",
                            "tool": "update_cell",
                            "params": params,
                            "timestamp": _iso_now()
                        })
                    
                    tool_executed = True
                    reply_content = f"已执行操作：将第 {params.get('row_index')+1} 行的 {params.get('key')} 修改为 {params.get('value')}。"
            except json.JSONDecodeError:
                logger.warning(f"无法解析 LLM 返回的 JSON: {clean_content}")
        
        await notify_step_end(state, "analyzing", "指令处理完成")
        
        # 添加回复消息
        state['messages'].append(AIMessage(content=reply_content))
        
        # 推送最终回复给前端聊天框
        if state.get('client_id'):
            await manager.send_to_client(state['client_id'], {
                "type": "agent_thought",
                "content": reply_content, # 这里的内容会显示在聊天框
                "status": "done",
                "timestamp": _iso_now()
            })

    except Exception as e:
        logger.error(f"[Audio Flow] 处理失败: {str(e)}")
        state['error'] = str(e)
        state['messages'].append(AIMessage(content=f"抱歉，语音处理出错了: {str(e)}"))
        await notify_log(state, "error", f"语音处理异常: {str(e)}")
    
    state['next_action'] = 'end'
    return state
