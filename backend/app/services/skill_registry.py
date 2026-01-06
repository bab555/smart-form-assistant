"""
Skills 注册表系统
将数据库表转换为可匹配的 Skills，用于主控模型判断内容相关性
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from app.core.logger import app_logger as logger


@dataclass
class Skill:
    """技能定义"""
    skill_id: str                           # 技能唯一标识
    name: str                               # 技能名称
    description: str                        # 技能描述
    keywords: List[str]                     # 关键词列表（用于匹配）
    category: str                           # 分类（product/customer/unit/warehouse等）
    table_source: str                       # 来源数据库表名
    sample_values: List[str] = field(default_factory=list)  # 示例值


class SkillRegistry:
    """
    Skills 注册表
    管理所有可用的校准技能，并提供匹配接口
    """
    
    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self._initialized = False
    
    def initialize(self):
        """初始化 Skills 注册表"""
        if self._initialized:
            return
        
        # 从 Mock 数据生成 Skills
        self._register_mock_skills()
        self._initialized = True
        logger.info(f"Skills 注册表初始化完成，共 {len(self.skills)} 个技能")
    
    def _register_mock_skills(self):
        """注册 Mock Skills（实际项目中应从数据库动态生成）"""
        
        # Skill 1: 农产品校准
        self.register_skill(Skill(
            skill_id="agricultural_products",
            name="农产品校准",
            description="校准水果、蔬菜、农产品名称，修正错别字和规范名称",
            keywords=["水果", "蔬菜", "农产品", "苹果", "香蕉", "橙子", "葡萄", "西瓜", 
                      "白菜", "萝卜", "土豆", "番茄", "黄瓜", "生鲜", "果蔬"],
            category="product",
            table_source="products",
            sample_values=["红富士苹果", "黄金香蕉", "脐橙", "巨峰葡萄", "麒麟西瓜"]
        ))
        
        # Skill 2: 客户信息校准
        self.register_skill(Skill(
            skill_id="customers",
            name="客户信息校准",
            description="校准客户姓名、公司名称，修正识别错误",
            keywords=["客户", "买家", "收货人", "公司", "商户", "供应商", "采购商"],
            category="customer",
            table_source="customers",
            sample_values=["张三", "李四", "王五", "赵六", "钱七"]
        ))
        
        # Skill 3: 单位校准
        self.register_skill(Skill(
            skill_id="units",
            name="计量单位校准",
            description="校准计量单位，统一单位表示",
            keywords=["单位", "计量", "公斤", "斤", "千克", "克", "吨", "箱", "件", "个", "份"],
            category="unit",
            table_source="units",
            sample_values=["公斤", "斤", "箱", "件", "个"]
        ))
        
        # Skill 4: 仓库校准
        self.register_skill(Skill(
            skill_id="warehouses",
            name="仓库信息校准",
            description="校准仓库名称和位置信息",
            keywords=["仓库", "库房", "存储", "冷库", "保鲜库", "存放"],
            category="warehouse",
            table_source="warehouses",
            sample_values=["一号仓库", "冷藏库A", "生鲜仓"]
        ))
    
    def register_skill(self, skill: Skill):
        """注册一个 Skill"""
        self.skills[skill.skill_id] = skill
        logger.debug(f"注册 Skill: {skill.skill_id} - {skill.name}")
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """获取指定 Skill"""
        return self.skills.get(skill_id)
    
    def get_all_skills(self) -> List[Skill]:
        """获取所有 Skills"""
        return list(self.skills.values())
    
    def get_skills_summary(self) -> str:
        """
        生成 Skills 摘要，供主控模型参考
        """
        if not self.skills:
            return "当前没有可用的校准技能。"
        
        summary_lines = ["可用的校准技能："]
        for skill in self.skills.values():
            keywords_str = "、".join(skill.keywords[:5])
            samples_str = "、".join(skill.sample_values[:3]) if skill.sample_values else "无"
            summary_lines.append(
                f"- {skill.skill_id}: {skill.name}\n"
                f"  描述: {skill.description}\n"
                f"  关键词: {keywords_str}...\n"
                f"  示例: {samples_str}"
            )
        
        return "\n".join(summary_lines)
    
    def get_skill_categories(self) -> Dict[str, List[str]]:
        """
        获取按类别分组的 Skill IDs
        """
        categories: Dict[str, List[str]] = {}
        for skill in self.skills.values():
            if skill.category not in categories:
                categories[skill.category] = []
            categories[skill.category].append(skill.skill_id)
        return categories
    
    def match_skills_by_keywords(self, text: str) -> List[str]:
        """
        简单关键词匹配（作为 LLM 匹配的备选方案）
        """
        matched = []
        text_lower = text.lower()
        
        for skill in self.skills.values():
            for keyword in skill.keywords:
                if keyword.lower() in text_lower:
                    if skill.skill_id not in matched:
                        matched.append(skill.skill_id)
                    break
        
        return matched


# 全局单例
skill_registry = SkillRegistry()

