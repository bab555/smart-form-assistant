"""
极简 Agent v4.0 - 纯 JSON 驱动架构

架构：
- VL模型：仅用于图片→文字
- 中控模型（qwen-max, enable_thinking）：所有处理
- 纯 JSON 输出：不用 Function Calling，更稳定
- 流式：文本→聊天框，JSON→执行操作
"""
import json
import re
import logging
from typing import Optional, Dict, Any, AsyncGenerator, List
from collections import defaultdict
from app.services.aliyun_llm import llm_service
from app.core.file_parser import parse_file_content
from app.core.templates import map_row_to_template
from app.utils.helpers import generate_trace_id
from app.services.knowledge_base import vector_store
from app.services.preference_store import preference_store

logger = logging.getLogger(__name__)


class SimpleAgent:
    """
    极简 Agent v4.0 - 纯 JSON 驱动
    
    模型输出两种内容：
    1. 普通文本 → 显示在聊天框
    2. JSON 对象 → 解析执行操作
    """

    async def process_request(
        self, 
        user_input: str, 
        context: Dict,
        file_data: Optional[bytes] = None, 
        filename: Optional[str] = None
    ) -> AsyncGenerator[Dict, None]:
        """统一入口"""
        active_table_id = context.get("activeTableId")
        tables_ctx = context.get("tables") or {}
        active_table_ctx = tables_ctx.get(active_table_id, {}) if active_table_id else {}
        inherited_metadata = active_table_ctx.get("metadata") or {}
        customer_id = inherited_metadata.get("customerId") or inherited_metadata.get("customer_id")

        # ==================== 准备输入内容 ====================
        content_to_process = user_input
        new_table_id = None

        def _new_table_id() -> str:
            # generate_trace_id() = trace_YYYYMMDDHHMMSS_xxxxxxxx
            # 不能用 [:8]，否则永远是 trace_20 导致 id 冲突
            return f"table_{generate_trace_id().split('_')[-1]}"

        def _is_table_effectively_empty(rows: list) -> bool:
            if not rows:
                return True
            if len(rows) != 1:
                return False
            first = rows[0] or {}
            return not any(
                str(v).strip()
                for k, v in first.items()
                if not str(k).startswith("_") and str(k) not in ("id", "序号")
            )
        
        if file_data and filename:
            # 1. 文件上传：若当前表格是空表则复用（避免默认表残留）；否则新建
            table_title = filename.rsplit('.', 1)[0]
            active_rows = active_table_ctx.get("rows", []) or []
            reuse_active = bool(active_table_id) and _is_table_effectively_empty(active_rows)
            new_table_id = active_table_id if reuse_active else _new_table_id()
            
            yield {
                "type": "tool_call",
                "tool": "create_table",
                "params": {
                    "table_id": new_table_id,
                    "title": table_title,
                    "rows": [],
                    "metadata": inherited_metadata,
                },
            }
            
            # 2. 解析文件内容
            yield {"type": "state", "state": "reading_file"}
            
            if filename.lower().endswith(('.jpg', '.png', '.jpeg', '.gif', '.webp')):
                # 图片走 VL 模型
                vl_prompt = """请提取图片中的所有订单/采购信息。
输出要求：每行一个JSON对象，字段：识别商品、数量、单位、规格、备注。不要markdown代码块。"""
                parsed_content = await llm_service.call_vl_model(image_data=file_data, prompt=vl_prompt)
                content_to_process = f"【图片识别结果】\n{parsed_content}\n\n请分析并提取订单数据。"
            else:
                # 文档走本地解析
                parsed_content = parse_file_content(file_data, filename)
                # 调试日志：打印解析后的前500字符，确保 Excel/Word 内容被正确读取
                preview = parsed_content[:500].replace('\n', '\\n')
                print(f"==== [Agent DEBUG] Parsed Content Len: {len(parsed_content)} ====")
                print(f"==== [Agent DEBUG] Preview: {preview} ====")
                logger.info(f"[Agent] Parsed Content ({len(parsed_content)} chars): {preview}...")
                
                content_to_process = f"【文件内容】\n{parsed_content}\n\n{user_input if user_input else '请分析并提取订单数据。'}"

        # ==================== 中控模型统一处理 ====================
        yield {"type": "state", "state": "thinking"}
        
        # 构建当前表格信息
        current_table_id = new_table_id or active_table_id
        all_tables_info = []
        active_table_rows = []
        for tid, tinfo in tables_ctx.items():
            title = tinfo.get("title", tid)
            rows = tinfo.get("rows", [])
            row_count = len(rows)
            is_active = "【当前】" if tid == current_table_id else ""
            all_tables_info.append(f"- {title} (id={tid}, {row_count}行) {is_active}")
            if tid == current_table_id:
                active_table_rows = rows
        tables_list_str = "\n".join(all_tables_info) if all_tables_info else "（暂无表格）"
        
        # 当前表格内容
        table_content = ""
        if active_table_rows:
            lines = []
            for i, row in enumerate(active_table_rows[:20]):
                name = row.get("识别商品", row.get("商品名称", ""))
                qty = row.get("数量", "")
                unit = row.get("单位", "")
                lines.append(f"{i+1}. {name} {qty}{unit}")
            table_content = "\n".join(lines)
            if len(active_table_rows) > 20:
                table_content += f"\n... 共 {len(active_table_rows)} 行"

        # 获取商品库名称列表
        product_names = []
        try:
            product_names = vector_store.product_index.get_all_names(limit=100)
        except Exception:
            pass
        product_list_str = "、".join(product_names[:30]) if product_names else "（商品库为空）"
        if len(product_names) > 30:
            product_list_str += f"... 等共{len(product_names)}种"

        # ==================== 构建提示词 ====================
        
        # 1. 基础 Prompt (所有场景通用)
        base_prompt = f"""你是智能订单录入助手。

═══════════════════════════════════════════════════
【当前状态】
- 当前表格ID: {current_table_id or '无'}
- 所有表格:
{tables_list_str}
- 当前表格内容:
{table_content if table_content else "（空表格）"}
═══════════════════════════════════════════════════

【商品库参考】
{product_list_str}
"""

        # 2. 场景化 Prompt
        if file_data and filename:
            # 场景 A: 文件分析 (FileAnalyze)
            scenario_prompt = """
【任务】
这是一份用户上传的文件内容（见下文）。请分析用户的订单需求。

【处理规则】
1. **智能拆分**：如果内容包含多个日期或多个客户的订单，请拆分成多个表格。
2. **内容解析**：
   - 识别“食谱”：如“红烧肉”，需拆解为食材（五花肉、酱油等）。
   - 识别“口语”：如“明天要十斤土豆”，提取为 {"识别商品": "土豆", "数量": 10, "单位": "斤"}。
3. **合并同类项**：相同商品请合并数量。

【输出格式】
严格使用 JSON Lines 格式，每行一个对象：

1. 新建表格：{"__new_table__": "表名（如：1月1日张三）"}
2. 添加商品：{"识别商品": "xx", "数量": 1, "单位": "xx", "规格": "xx", "备注": "xx"}
"""
        else:
            # 场景 B: 对话/操作 (Chat / Edit)
            scenario_prompt = """
【任务】
根据用户的输入，进行对话、分析、生成菜单/订单，并在需要时直接填表或修改表格。

【能力】
1. **闲聊/建议/规划**：可以直接与用户对话，分析菜谱/菜单，给出建议或帮用户设计菜单。
2. **聊天也可“抽取/生成订单”**：用户在聊天框里输入的内容也可能包含“口语订单/菜单/食谱/计划”。当用户意图是“生成订单/采购清单/做成订单表”，你应该像处理上传文件一样，进行分析、拆分、合并同类项，并用 JSON Lines 直接填表。
3. **操作已有表格**：当用户明确要求修改当前表格（增/删/改某一行某一列），输出 Action JSON。

【输出格式】
- 对话：直接输出文字（可先解释你将如何处理）。
- 生成/抽取订单并填表：输出 JSON Lines（每行一个 JSON 对象），用于直接写入表格：
  - 新建表格：{"__new_table__": "表名（如：1月1日张三）"}
  - 添加商品：{"识别商品": "xx", "数量": 1, "单位": "xx", "规格": "xx", "备注": "xx"}
- 操作已有表格：输出 JSON Action（每行一个对象也可以，但必须是合法 JSON）：
  - 修改：{"action": "update", "row": 1, "col": "识别商品", "value": "xx"}
  - 删除：{"action": "delete", "row": 2}
  - 新增：{"action": "add", "data": {"识别商品": "xx", ...}}

【重要提醒】
- 当用户说“根据前几天菜单设计新一天菜单并做成订单/采购单”，你需要：先设计菜单（文字），再把对应采购清单用 JSON Lines 输出以便自动填表。
"""

        # 3. 最终组合
        system_prompt = base_prompt + scenario_prompt + """
═══════════════════════════════════════════════════
【重要规则】
1. JSON 必须单独一行，不要放在代码块里
2. 不要输出 ```json``` 代码块
3. 语气友好自然
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content_to_process}
        ]

        # 流式调用（不带 tools）
        yield {"type": "state", "state": "processing"}
        
        try:
            stream = llm_service.stream_chat_with_thinking(
                messages=messages,
                tools=None,  # 不使用 Function Calling
                thinking_budget=200
            )

            # 数据收集：支持多表格
            row_buffer = []  # 存储 {"table_id": "xxx", "row_index": 0, "data": {...}}
            table_row_counts = defaultdict(int) # table_id -> next_row_index
            text_buffer = ""
            
            # 初始化当前表格的行计数
            if current_table_id:
                table_row_counts[current_table_id] = len(active_table_rows)

            # 判断初始表格是否为空（用于复用决策）
            # 空表判定：行数为0，或者行数为1且除了内部字段外没有有效值
            is_original_table_empty = False
            if not active_table_rows:
                is_original_table_empty = True
            elif len(active_table_rows) == 1:
                first_row = active_table_rows[0]
                has_content = any(
                    str(v).strip() 
                    for k, v in first_row.items() 
                    if not k.startswith('_') and k != 'id' and k != '序号'
                )
                if not has_content:
                    is_original_table_empty = True

            # 标记是否已经处理过 __new_table__
            has_renamed_first_table = False

            async for chunk in stream:
                chunk_type = chunk.get("type")
                
                if chunk_type == "thinking":
                    yield {"type": "thinking", "content": chunk["content"]}
                
                elif chunk_type == "content":
                    content = chunk["content"]
                    text_buffer += content
                    
                    # 逐行解析
                    while '\n' in text_buffer:
                        line, text_buffer = text_buffer.split('\n', 1)
                        line = line.strip()
                        if not line:
                            continue
                        
                        # 尝试解析 JSON
                        parsed = self._try_parse_json(line)
                        if parsed:
                            # 1. 检查是否新建表格
                            if "__new_table__" in parsed:
                                title = parsed.get("__new_table__", "新表格")
                                
                                # 策略：如果是流中的第一个新建表格指令，且初始表格为空，则复用初始表格
                                # 否则新建表格
                                should_reuse = False
                                if not has_renamed_first_table and current_table_id and is_original_table_empty:
                                    should_reuse = True
                                
                                if should_reuse:
                                    target_table_id = current_table_id
                                    has_renamed_first_table = True
                                else:
                                    target_table_id = _new_table_id()
                                    current_table_id = target_table_id # 切换当前操作的表ID

                                yield {
                                    "type": "tool_call",
                                    "tool": "create_table",
                                    "params": {
                                        "table_id": target_table_id,
                                        "title": title,
                                        "rows": [], # 新建/复用时都重置rows（复用时清空空行）
                                        "metadata": inherited_metadata,
                                    },
                                }
                                # 初始化/重置该表的行计数
                                table_row_counts[target_table_id] = 0
                                continue

                            # 2. 执行其他 JSON 指令
                            async for event in self._execute_json(parsed, current_table_id, row_buffer, table_row_counts):
                                yield event
                        else:
                            # 普通文本，显示在聊天框
                            yield {"type": "message_delta", "content": line + "\n"}
                
                elif chunk_type == "error":
                    yield {"type": "message", "content": f"出错: {chunk['content']}"}
                
                elif chunk_type == "finish":
                    pass
            
            # 处理剩余 buffer
            if text_buffer.strip():
                line = text_buffer.strip()
                parsed = self._try_parse_json(line)
                if parsed:
                    if "__new_table__" in parsed:
                        title = parsed.get("__new_table__", "新表格")
                        
                        should_reuse = False
                        if not has_renamed_first_table and current_table_id and is_original_table_empty:
                            should_reuse = True
                        
                        if should_reuse:
                            target_table_id = current_table_id
                            has_renamed_first_table = True
                        else:
                            target_table_id = _new_table_id()
                            current_table_id = target_table_id

                        yield {
                            "type": "tool_call",
                            "tool": "create_table",
                            "params": {
                                "table_id": target_table_id,
                                "title": title,
                                "rows": [],
                                "metadata": inherited_metadata,
                            },
                        }
                        table_row_counts[target_table_id] = 0
                    else:
                        async for event in self._execute_json(parsed, current_table_id, row_buffer, table_row_counts):
                            yield event
                else:
                    yield {"type": "message_delta", "content": line + "\n"}

            # ==================== 校对逻辑 (支持多表) ====================
            if row_buffer:
                yield {"type": "state", "state": "calibrating"}
                
                # 批量提取名称用于校对
                raw_names = [item["data"].get("识别商品", "") for item in row_buffer]
                calibration_results = await vector_store.batch_calibrate(raw_names)

                stats = {"exact": 0, "fuzzy": 0, "not_found": 0}

                for i, res in enumerate(calibration_results):
                    # 获取该行对应的表格ID和行号
                    item = row_buffer[i]
                    tid = item["table_id"]
                    rid = item["row_index"]
                    recognized = (raw_names[i] or "").strip()
                    
                    # 偏好增强
                    preferred = await preference_store.get(str(customer_id) if customer_id else None, recognized)
                    if preferred:
                        prod = vector_store.product_index.get_by_name(preferred)
                        if prod:
                            stats["exact"] += 1
                            yield self._update_cell(tid, rid, "订单商品", preferred)
                            yield self._update_cell(tid, rid, "规格", prod.spec or "")
                            yield self._update_cell(tid, rid, "单位", prod.unit or "")
                            yield self._update_cell(tid, rid, "__order_status", "exact")
                            continue
                    
                    # 无法匹配
                    if res.match_type == "not_found" or not res.product:
                        stats["not_found"] += 1
                        yield self._update_cell(tid, rid, "__order_status", "not_found")
                        yield self._update_cell(tid, rid, "__calibration_hint", "库中没有该商品")
                        continue
                    
                    # 精确匹配
                    is_exact = res.match_type == "exact" and res.confidence >= 0.99
                    if is_exact:
                        stats["exact"] += 1
                        yield self._update_cell(tid, rid, "订单商品", res.calibrated)
                        yield self._update_cell(tid, rid, "规格", res.product.spec or "")
                        yield self._update_cell(tid, rid, "单位", res.product.unit or "")
                        yield self._update_cell(tid, rid, "__order_status", "exact")
                        continue
                    
                    # 模糊匹配
                    stats["fuzzy"] += 1
                    closest_match = res.calibrated if res.calibrated else ""
                    yield self._update_cell(tid, rid, "__order_status", "fuzzy")
                    yield self._update_cell(tid, rid, "__fuzzy_match", closest_match)
                    try:
                        search_results = await vector_store.search(recognized, top_k=5)
                        candidates = [r["name"] for r in search_results if r.get("name")]
                    except Exception:
                        candidates = [closest_match] if closest_match else []
                    yield self._update_cell(tid, rid, "__order_candidates", candidates)

                total = len(row_buffer)
                yield {
                    "type": "message",
                    "content": f"✅ 校对完成：精确 {stats['exact']}/{total}，模糊 {stats['fuzzy']}，未找到 {stats['not_found']}",
                }
                
                if stats["fuzzy"] > 0:
                    yield {
                        "type": "message",
                        "content": "💡 标有 ⚠️ 的商品需要确认，点击感叹号可以从商品库中选择。",
                    }

        except Exception as e:
            logger.error(f"处理异常: {e}", exc_info=True)
            yield {"type": "message", "content": f"处理出错: {str(e)}"}
        
        yield {"type": "state", "state": "idle"}

    def _try_parse_json(self, line: str) -> Optional[Dict]:
        """尝试解析 JSON"""
        line = line.strip()
        if not line.startswith('{') or not line.endswith('}'):
            return None
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None

    async def _execute_json(
        self, 
        data: Dict, 
        table_id: str, 
        row_buffer: List,
        table_row_counts: Dict[str, int]
    ) -> AsyncGenerator[Dict, None]:
        """执行 JSON 指令"""
        
        if not table_id and "action" not in data: 
            # 如果没有 table_id 且不是通用操作，无法填表
            return

        # 操作类 JSON
        if "action" in data:
            action = data["action"]
            
            if action == "update":
                row_idx = data.get("row", 1) - 1  # 转 0-based
                col = data.get("col", "")
                value = data.get("value", "")
                if row_idx >= 0 and col and table_id:
                    yield self._update_cell(table_id, row_idx, col, value)
                    yield {"type": "message", "content": f"✅ 已修改第 {row_idx + 1} 行的「{col}」"}
            
            elif action == "delete":
                row_idx = data.get("row", 1) - 1
                if row_idx >= 0 and table_id:
                    yield {
                        "type": "tool_call",
                        "tool": "delete_row",
                        "params": {"table_id": table_id, "row_index": row_idx},
                    }
                    yield {"type": "message", "content": f"✅ 已删除第 {row_idx + 1} 行"}
            
            elif action == "add":
                row_data = data.get("data", {})
                if row_data and table_id:
                    normalized = map_row_to_template(row_data)
                    # 计算该行的 index
                    current_idx = table_row_counts[table_id]
                    normalized["序号"] = str(current_idx + 1)
                    
                    # 记录到 buffer 用于校对
                    row_buffer.append({
                        "table_id": table_id,
                        "row_index": current_idx,
                        "data": normalized
                    })
                    table_row_counts[table_id] += 1
                    
                    yield {
                        "type": "tool_call",
                        "tool": "add_row",
                        "params": {"table_id": table_id, "data": normalized}
                    }
            
            return
        
        # 填表类 JSON（包含 识别商品 字段）
        if "识别商品" in data or "商品" in data or "名称" in data:
            normalized = map_row_to_template(data)
            
            # 计算该行的 index
            current_idx = table_row_counts[table_id]
            normalized["序号"] = str(current_idx + 1)
            
            # 记录到 buffer 用于校对
            row_buffer.append({
                "table_id": table_id,
                "row_index": current_idx,
                "data": normalized
            })
            table_row_counts[table_id] += 1

            yield {
                "type": "tool_call",
                "tool": "add_row",
                "params": {"table_id": table_id, "data": normalized}
            }

    def _update_cell(self, table_id: str, row_index: int, key: str, value: Any) -> Dict:
        """生成 update_cell 事件"""
        return {
            "type": "tool_call",
            "tool": "update_cell",
            "params": {
                "table_id": table_id,
                "row_index": row_index,
                "key": key,
                "value": value,
            },
        }
