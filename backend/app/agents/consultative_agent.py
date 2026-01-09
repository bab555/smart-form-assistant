"""
咨询分析 Agent

功能：
1. 基于表格数据的计算统计
2. 订单合理性分析
3. 采购建议
4. 数据问答

使用主控 LLM (Qwen-Max) 进行分析
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

from app.core.logger import app_logger as logger
from app.services.aliyun_llm import llm_service
from app.agents.tools.fast_tools import fast_tools


@dataclass
class AnalysisResult:
    """分析结果"""
    success: bool
    answer: str
    data: Optional[Dict] = None  # 附加数据（如计算结果）
    suggestions: Optional[List[str]] = None  # 建议列表


class ConsultativeAgent:
    """
    咨询分析 Agent
    
    基于表格数据进行分析和对话
    """
    
    def __init__(self):
        self.system_prompt = """你是一个专业的订单分析助手，帮助用户分析和理解表格数据。

你的能力：
1. 📊 **数据统计**：计算总金额、数量、平均价格等
2. 🔍 **合理性分析**：检查订单是否合理，价格是否正常
3. 💡 **采购建议**：基于数据给出采购建议
4. ❓ **数据问答**：回答关于表格数据的问题

回答要求：
- 简洁明了，重点突出
- 如果涉及计算，展示计算过程
- 如果发现问题，主动提醒
- 使用友好的语气

当前时间：{current_time}
"""
    
    async def analyze(
        self,
        query: str,
        table_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> AnalysisResult:
        """
        分析表格数据并回答问题
        
        Args:
            query: 用户问题
            table_data: 表格数据 {
                "title": "表格标题",
                "rows": [...],
                "schema": [...],
                "metadata": {...}
            }
            context: 额外上下文
            
        Returns:
            AnalysisResult
        """
        try:
            # 1. 预处理表格数据
            rows = table_data.get("rows", [])
            schema = table_data.get("schema", [])
            title = table_data.get("title", "订单")
            
            if not rows:
                return AnalysisResult(
                    success=True,
                    answer="当前表格没有数据，请先添加数据后再分析。"
                )
            
            # 2. 计算基础统计（使用 FastTools）
            stats = fast_tools.calculate_total(rows)
            
            # 3. 格式化表格数据为文本
            table_text = self._format_table_for_llm(rows, schema, title)
            
            # 4. 构建 Prompt
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            system = self.system_prompt.format(current_time=current_time)
            
            user_prompt = f"""## 表格数据

{table_text}

## 基础统计
- 总行数：{stats['row_count']}
- 总金额：{stats['total_amount']} 元
- 总数量：{stats['total_quantity']}

## 用户问题
{query}

请基于以上数据回答用户问题。"""
            
            # 5. 调用主控 LLM
            response = await llm_service.call_main_model([
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt}
            ])
            
            return AnalysisResult(
                success=True,
                answer=response,
                data=stats
            )
            
        except Exception as e:
            logger.error(f"[ConsultativeAgent] 分析失败: {str(e)}")
            return AnalysisResult(
                success=False,
                answer=f"分析时出错: {str(e)}"
            )
    
    async def calculate(
        self,
        operation: str,
        table_data: Dict[str, Any],
        field: str = None
    ) -> AnalysisResult:
        """
        执行计算操作
        
        Args:
            operation: 操作类型 (total/sum/average/count/max/min)
            table_data: 表格数据
            field: 指定字段（可选）
            
        Returns:
            AnalysisResult
        """
        try:
            rows = table_data.get("rows", [])
            
            if not rows:
                return AnalysisResult(
                    success=True,
                    answer="表格没有数据，无法计算。"
                )
            
            # 使用 FastTools 计算
            stats = fast_tools.calculate_total(rows)
            
            if operation in ["total", "sum"]:
                answer = f"📊 **统计结果**\n\n"
                answer += f"• 总行数：{stats['row_count']} 行\n"
                answer += f"• 总金额：**¥{stats['total_amount']}**\n"
                answer += f"• 总数量：{stats['total_quantity']}\n"
                
                if stats['total_amount'] > 0 and stats['row_count'] > 0:
                    avg = stats['total_amount'] / stats['row_count']
                    answer += f"• 平均每行：¥{avg:.2f}"
                
            elif operation == "count":
                answer = f"表格共有 **{stats['row_count']}** 行数据"
                
            elif operation == "average":
                if stats['row_count'] > 0:
                    avg = stats['total_amount'] / stats['row_count']
                    answer = f"平均每行金额：**¥{avg:.2f}**"
                else:
                    answer = "没有数据，无法计算平均值"
            else:
                answer = f"总金额：**¥{stats['total_amount']}**，共 {stats['row_count']} 行"
            
            return AnalysisResult(
                success=True,
                answer=answer,
                data=stats
            )
            
        except Exception as e:
            logger.error(f"[ConsultativeAgent] 计算失败: {str(e)}")
            return AnalysisResult(
                success=False,
                answer=f"计算时出错: {str(e)}"
            )
    
    async def check_reasonability(
        self,
        table_data: Dict[str, Any]
    ) -> AnalysisResult:
        """
        检查订单合理性
        
        检查项：
        1. 价格是否异常（过高/过低）
        2. 数量是否合理
        3. 商品是否在知识库中
        4. 总金额是否异常
        """
        try:
            rows = table_data.get("rows", [])
            
            if not rows:
                return AnalysisResult(
                    success=True,
                    answer="表格没有数据，无法进行合理性检查。"
                )
            
            issues = []
            suggestions = []
            
            # 1. 计算统计
            stats = fast_tools.calculate_total(rows)
            
            # 2. 检查每行数据
            for idx, row in enumerate(rows):
                row_issues = []
                
                # 获取字段（兼容多种命名）
                product = self._get_field(row, ["商品名称", "商品名", "品名", "product", "name"])
                quantity = self._get_field(row, ["数量", "数目", "qty", "quantity"])
                price = self._get_field(row, ["单价", "价格", "price"])
                total = self._get_field(row, ["金额", "总价", "total", "amount"])
                
                # 检查数量
                if quantity is not None:
                    try:
                        qty = float(quantity)
                        if qty < 0:
                            row_issues.append(f"数量为负数 ({qty})")
                        elif qty > 1000:
                            row_issues.append(f"数量较大 ({qty})，请确认")
                    except (ValueError, TypeError):
                        pass
                
                # 检查价格
                if price is not None:
                    try:
                        p = float(price)
                        if p < 0:
                            row_issues.append(f"价格为负数 ({p})")
                        elif p > 10000:
                            row_issues.append(f"单价较高 ({p})")
                        elif p == 0:
                            row_issues.append("单价为0")
                    except (ValueError, TypeError):
                        pass
                
                # 检查商品（使用快速校准）
                if product:
                    result = fast_tools.quick_calibrate(str(product))
                    if result.confidence < 0.5:
                        row_issues.append(f"商品「{product}」未在商品库中")
                    elif result.is_ambiguous:
                        row_issues.append(f"商品「{product}」可能有多个匹配")
                
                if row_issues:
                    issues.append(f"第 {idx + 1} 行: {'; '.join(row_issues)}")
            
            # 3. 检查总体
            if stats['total_amount'] > 50000:
                suggestions.append("订单金额较大（超过5万），建议核对")
            
            if stats['row_count'] > 50:
                suggestions.append("订单条目较多，建议分批处理")
            
            # 4. 生成回复
            if not issues and not suggestions:
                answer = "✅ **订单检查通过**\n\n"
                answer += f"• 共 {stats['row_count']} 行数据\n"
                answer += f"• 总金额 ¥{stats['total_amount']}\n"
                answer += "\n未发现明显问题。"
            else:
                answer = "⚠️ **订单检查发现以下问题**\n\n"
                
                if issues:
                    answer += "**数据问题：**\n"
                    for issue in issues[:10]:  # 最多显示10条
                        answer += f"• {issue}\n"
                    if len(issues) > 10:
                        answer += f"• ...还有 {len(issues) - 10} 条问题\n"
                
                if suggestions:
                    answer += "\n**建议：**\n"
                    for sug in suggestions:
                        answer += f"• {sug}\n"
            
            return AnalysisResult(
                success=True,
                answer=answer,
                data=stats,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"[ConsultativeAgent] 合理性检查失败: {str(e)}")
            return AnalysisResult(
                success=False,
                answer=f"检查时出错: {str(e)}"
            )
    
    async def suggest(
        self,
        query: str,
        table_data: Dict[str, Any]
    ) -> AnalysisResult:
        """
        给出采购/订单建议
        """
        # 调用通用分析，但加上建议导向的提示
        suggestion_query = f"""用户问题：{query}

请基于订单数据给出专业的建议，包括：
1. 数据分析
2. 潜在问题
3. 优化建议"""
        
        return await self.analyze(suggestion_query, table_data)
    
    def _format_table_for_llm(
        self,
        rows: List[Dict],
        schema: List[Dict],
        title: str
    ) -> str:
        """
        将表格格式化为 LLM 可读的文本
        """
        if not rows:
            return "（空表格）"
        
        # 获取列名
        if schema:
            headers = [col.get("title", col.get("key", f"列{i}")) for i, col in enumerate(schema)]
        else:
            headers = list(rows[0].keys())
        
        # 构建 Markdown 表格
        lines = [f"**{title}**\n"]
        
        # 表头
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        
        # 数据行（限制显示数量）
        max_rows = 20
        for i, row in enumerate(rows[:max_rows]):
            values = []
            for h in headers:
                # 尝试多种键名
                val = row.get(h) or row.get(h.lower()) or row.get(h.replace(" ", "_")) or ""
                values.append(str(val) if val else "-")
            lines.append("| " + " | ".join(values) + " |")
        
        if len(rows) > max_rows:
            lines.append(f"\n（...共 {len(rows)} 行，显示前 {max_rows} 行）")
        
        return "\n".join(lines)
    
    def _get_field(self, row: Dict, candidates: List[str]) -> Any:
        """
        从行数据中获取字段值（支持多种命名）
        """
        for key in candidates:
            if key in row:
                return row[key]
            # 尝试小写
            for rk in row.keys():
                if rk.lower() == key.lower():
                    return row[rk]
        return None


# 全局实例
consultative_agent = ConsultativeAgent()

