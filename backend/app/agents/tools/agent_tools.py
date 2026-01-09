"""
Agent Tools - LLM 调用的工具

特点：
1. 需要 LLM 推理才能决定参数
2. 用于用户指令解析、修改操作、校对等
3. 返回结构化的工具调用指令

使用场景：
- 表格增删改操作
- 数据校对与确认
- 计算与统计
- 知识库查询
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json

from app.core.logger import app_logger as logger


class ToolName(str, Enum):
    """工具名称枚举"""
    # 表格操作
    UPDATE_CELL = "update_cell"
    ADD_ROW = "add_row"
    DELETE_ROW = "delete_row"
    CREATE_TABLE = "create_table"
    CLEAR_TABLE = "clear_table"
    
    # 校对操作
    CALIBRATE = "calibrate"
    CONFIRM_CALIBRATION = "confirm_calibration"
    REJECT_CALIBRATION = "reject_calibration"
    
    # 查询操作
    QUERY_PRODUCT = "query_product"
    QUERY_TABLE = "query_table"
    CALCULATE = "calculate"
    
    # 特殊
    UNKNOWN = "unknown"
    CLARIFY = "clarify"  # 需要用户澄清


@dataclass
class ToolCall:
    """工具调用结构"""
    tool: str
    params: Dict[str, Any]
    confidence: float = 1.0
    message: Optional[str] = None  # 给用户的说明
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ========== 工具定义（给 LLM 参考）==========

AGENT_TOOL_DEFINITIONS = {
    ToolName.UPDATE_CELL: {
        "name": "update_cell",
        "description": "更新表格中的单个单元格",
        "params": {
            "table_id": {"type": "string", "description": "表格ID，默认为当前表格", "required": False},
            "row_index": {"type": "integer", "description": "行号，从0开始。用户说'第一行'对应0", "required": True},
            "col_key": {"type": "string", "description": "列名/字段名", "required": True},
            "value": {"type": "any", "description": "新值", "required": True},
        },
        "examples": [
            {"user": "把第一行的价格改成100", "call": {"tool": "update_cell", "params": {"row_index": 0, "col_key": "价格", "value": 100}}},
            {"user": "将第三行商品名称修改为红富士苹果", "call": {"tool": "update_cell", "params": {"row_index": 2, "col_key": "商品名称", "value": "红富士苹果"}}},
        ]
    },
    
    ToolName.ADD_ROW: {
        "name": "add_row",
        "description": "向表格添加新行",
        "params": {
            "table_id": {"type": "string", "description": "表格ID", "required": False},
            "data": {"type": "object", "description": "行数据，键值对形式", "required": True},
            "position": {"type": "integer", "description": "插入位置，默认末尾", "required": False},
        },
        "examples": [
            {"user": "添加一行，商品是苹果，数量10斤，单价5元", "call": {"tool": "add_row", "params": {"data": {"商品名称": "苹果", "数量": 10, "单位": "斤", "单价": 5}}}},
            {"user": "新增一条记录，香蕉20斤", "call": {"tool": "add_row", "params": {"data": {"商品名称": "香蕉", "数量": 20, "单位": "斤"}}}},
        ]
    },
    
    ToolName.DELETE_ROW: {
        "name": "delete_row",
        "description": "删除表格中的行",
        "params": {
            "table_id": {"type": "string", "description": "表格ID", "required": False},
            "row_index": {"type": "integer", "description": "要删除的行号，从0开始", "required": True},
        },
        "examples": [
            {"user": "删除第一行", "call": {"tool": "delete_row", "params": {"row_index": 0}}},
            {"user": "去掉最后一行", "call": {"tool": "delete_row", "params": {"row_index": -1}}},
            {"user": "移除第5行", "call": {"tool": "delete_row", "params": {"row_index": 4}}},
        ]
    },
    
    ToolName.CREATE_TABLE: {
        "name": "create_table",
        "description": "创建新表格",
        "params": {
            "title": {"type": "string", "description": "表格标题", "required": False},
            "template": {"type": "string", "description": "模板名称，如'农产品订单'", "required": False},
            "schema": {"type": "array", "description": "列定义", "required": False},
            "data": {"type": "array", "description": "初始数据", "required": False},
        },
        "examples": [
            {"user": "帮我新建一个订单表", "call": {"tool": "create_table", "params": {"title": "新订单", "template": "农产品订单"}}},
            {"user": "创建一个表格记录今天的采购", "call": {"tool": "create_table", "params": {"title": "今日采购"}}},
        ]
    },
    
    ToolName.QUERY_PRODUCT: {
        "name": "query_product",
        "description": "查询商品库中的商品信息",
        "params": {
            "query": {"type": "string", "description": "查询关键词", "required": True},
            "category": {"type": "string", "description": "分类筛选", "required": False},
        },
        "examples": [
            {"user": "有没有苹果这个商品", "call": {"tool": "query_product", "params": {"query": "苹果"}}},
            {"user": "查一下猪肉的价格", "call": {"tool": "query_product", "params": {"query": "猪肉"}}},
        ]
    },
    
    ToolName.CALCULATE: {
        "name": "calculate",
        "description": "计算表格统计数据",
        "params": {
            "table_id": {"type": "string", "description": "表格ID", "required": False},
            "operation": {"type": "string", "description": "操作类型：total/sum/average/count", "required": True},
            "field": {"type": "string", "description": "字段名", "required": False},
        },
        "examples": [
            {"user": "这个订单总共多少钱", "call": {"tool": "calculate", "params": {"operation": "total"}}},
            {"user": "帮我算一下总金额", "call": {"tool": "calculate", "params": {"operation": "sum", "field": "金额"}}},
            {"user": "一共有多少行", "call": {"tool": "calculate", "params": {"operation": "count"}}},
        ]
    },
    
    ToolName.CLARIFY: {
        "name": "clarify",
        "description": "需要用户提供更多信息",
        "params": {
            "question": {"type": "string", "description": "向用户询问的问题", "required": True},
            "options": {"type": "array", "description": "可选项", "required": False},
        },
        "examples": [
            {"user": "把价格改成100", "call": {"tool": "clarify", "params": {"question": "请问是修改哪一行的价格？"}}},
        ]
    },
}


class AgentTools:
    """
    Agent 工具调用执行器
    
    负责解析 LLM 的工具调用指令并执行
    """
    
    @staticmethod
    def generate_tools_prompt() -> str:
        """
        生成工具定义 Prompt（给 LLM）
        """
        lines = ["你可以使用以下工具来帮助用户操作表格：\n"]
        
        for tool_name, definition in AGENT_TOOL_DEFINITIONS.items():
            lines.append(f"### {definition['name']}")
            lines.append(f"描述: {definition['description']}")
            lines.append("参数:")
            for param_name, param_info in definition['params'].items():
                required = "必填" if param_info.get('required') else "可选"
                lines.append(f"  - {param_name} ({param_info['type']}, {required}): {param_info['description']}")
            
            if definition.get('examples'):
                lines.append("示例:")
                for ex in definition['examples'][:2]:
                    lines.append(f'  用户: "{ex["user"]}"')
                    lines.append(f'  调用: {json.dumps(ex["call"], ensure_ascii=False)}')
            lines.append("")
        
        lines.append("""
请根据用户意图，输出 JSON 格式的工具调用：
```json
{"tool": "工具名", "params": {参数}}
```

如果无法确定参数（如行号），使用 clarify 工具询问用户。
如果是普通对话，直接回复文本，不要输出 JSON。
""")
        
        return "\n".join(lines)
    
    @staticmethod
    def parse_tool_call(response: str) -> Optional[ToolCall]:
        """
        解析 LLM 响应中的工具调用
        
        Args:
            response: LLM 响应文本
            
        Returns:
            ToolCall 或 None（如果不是工具调用）
        """
        # 清理响应
        clean = response.strip()
        
        # 移除 markdown 代码块
        if "```json" in clean:
            start = clean.find("```json") + 7
            end = clean.find("```", start)
            if end > start:
                clean = clean[start:end].strip()
        elif "```" in clean:
            start = clean.find("```") + 3
            end = clean.find("```", start)
            if end > start:
                clean = clean[start:end].strip()
        
        # 尝试解析 JSON
        if clean.startswith("{") and "tool" in clean:
            try:
                data = json.loads(clean)
                tool_name = data.get("tool")
                params = data.get("params", {})
                
                if tool_name:
                    return ToolCall(
                        tool=tool_name,
                        params=params,
                        confidence=data.get("confidence", 1.0),
                        message=data.get("message")
                    )
            except json.JSONDecodeError:
                pass
        
        return None
    
    @staticmethod
    async def execute_tool(
        tool_call: ToolCall,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        执行工具调用
        
        Args:
            tool_call: 工具调用
            context: 执行上下文（当前表格数据等）
            
        Returns:
            执行结果
        """
        tool_name = tool_call.tool
        params = tool_call.params
        context = context or {}
        
        logger.info(f"[AgentTools] 执行工具: {tool_name}, 参数: {params}")
        
        try:
            if tool_name == ToolName.UPDATE_CELL.value:
                return {
                    "success": True,
                    "action": "update_cell",
                    "table_id": params.get("table_id", context.get("current_table_id")),
                    "row_index": params.get("row_index"),
                    "col_key": params.get("col_key"),
                    "value": params.get("value"),
                }
            
            elif tool_name == ToolName.ADD_ROW.value:
                return {
                    "success": True,
                    "action": "add_row",
                    "table_id": params.get("table_id", context.get("current_table_id")),
                    "data": params.get("data", {}),
                    "position": params.get("position"),
                }
            
            elif tool_name == ToolName.DELETE_ROW.value:
                return {
                    "success": True,
                    "action": "delete_row",
                    "table_id": params.get("table_id", context.get("current_table_id")),
                    "row_index": params.get("row_index"),
                }
            
            elif tool_name == ToolName.CREATE_TABLE.value:
                return {
                    "success": True,
                    "action": "create_table",
                    "title": params.get("title", "新表格"),
                    "template": params.get("template"),
                    "schema": params.get("schema"),
                    "data": params.get("data"),
                }
            
            elif tool_name == ToolName.QUERY_PRODUCT.value:
                from app.agents.tools.fast_tools import fast_tools
                
                results = fast_tools.quick_product_lookup(
                    params.get("query", ""),
                    params.get("category")
                )
                
                return {
                    "success": True,
                    "action": "query_result",
                    "results": results,
                    "message": f"找到 {len(results)} 个匹配商品" if results else "未找到匹配商品"
                }
            
            elif tool_name == ToolName.CALCULATE.value:
                from app.agents.tools.fast_tools import fast_tools
                
                rows = context.get("current_rows", [])
                result = fast_tools.calculate_total(rows)
                
                return {
                    "success": True,
                    "action": "calculate_result",
                    "result": result,
                    "message": f"共 {result['row_count']} 行，总金额 {result['total_amount']} 元"
                }
            
            elif tool_name == ToolName.CLARIFY.value:
                return {
                    "success": True,
                    "action": "clarify",
                    "question": params.get("question", "请提供更多信息"),
                    "options": params.get("options"),
                }
            
            else:
                return {
                    "success": False,
                    "action": "unknown",
                    "message": f"未知工具: {tool_name}"
                }
                
        except Exception as e:
            logger.error(f"[AgentTools] 执行失败: {str(e)}")
            return {
                "success": False,
                "action": "error",
                "message": str(e)
            }
    
    @staticmethod
    def generate_confirm_message(tool_call: ToolCall, result: Dict) -> str:
        """
        生成操作确认消息
        """
        tool_name = tool_call.tool
        params = tool_call.params
        
        if tool_name == ToolName.UPDATE_CELL.value:
            row = params.get("row_index", 0) + 1
            col = params.get("col_key", "")
            value = params.get("value", "")
            return f"✅ 已将第 {row} 行的「{col}」修改为「{value}」"
        
        elif tool_name == ToolName.ADD_ROW.value:
            data = params.get("data", {})
            summary = ", ".join([f"{k}={v}" for k, v in list(data.items())[:3]])
            return f"✅ 已添加新行: {summary}"
        
        elif tool_name == ToolName.DELETE_ROW.value:
            row = params.get("row_index", 0)
            if row == -1:
                return "✅ 已删除最后一行"
            return f"✅ 已删除第 {row + 1} 行"
        
        elif tool_name == ToolName.CREATE_TABLE.value:
            title = params.get("title", "新表格")
            return f"✅ 已创建表格「{title}」"
        
        elif tool_name == ToolName.QUERY_PRODUCT.value:
            return result.get("message", "查询完成")
        
        elif tool_name == ToolName.CALCULATE.value:
            return result.get("message", "计算完成")
        
        elif tool_name == ToolName.CLARIFY.value:
            return params.get("question", "请提供更多信息")
        
        return "✅ 操作完成"


# 全局实例
agent_tools = AgentTools()

