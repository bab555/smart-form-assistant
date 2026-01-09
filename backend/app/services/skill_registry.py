"""
Skills 注册表系统 (重构版)

功能：
1. 动态创建/删除 Skills
2. 持久化存储（JSON 文件）
3. 提供表格模板
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import os
from pathlib import Path
from app.core.logger import app_logger as logger


@dataclass
class Skill:
    """技能/模板定义"""
    id: str                                     # 唯一标识
    name: str                                   # 名称
    category: str                               # 分类 (product/customer/general)
    schema: List[Dict[str, Any]]                # 表头定义 [{key, title, type}]
    description: str = ""                       # 描述
    keywords: List[str] = field(default_factory=list)  # 关键词
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Skill':
        return Skill(**data)


class SkillRegistry:
    """
    Skills 注册表
    支持动态增删和持久化
    """
    
    def __init__(self, storage_path: str = None):
        self.skills: Dict[str, Skill] = {}
        self._storage_path = storage_path or self._default_storage_path()
        self._initialized = False
    
    def _default_storage_path(self) -> str:
        """默认存储路径"""
        base_dir = Path(__file__).parent.parent.parent / "data"
        base_dir.mkdir(exist_ok=True)
        return str(base_dir / "skills.json")
    
    def initialize(self):
        """初始化：加载持久化数据 + 注册默认 Skills"""
        if self._initialized:
            return
        
        # 尝试加载持久化数据
        self._load_from_file()
        
        # 如果没有数据，注册默认 Skills
        if not self.skills:
            self._register_default_skills()
        
        self._initialized = True
        logger.info(f"SkillRegistry 初始化完成，共 {len(self.skills)} 个技能")
    
    def _register_default_skills(self):
        """注册默认 Skills"""
        # 农产品订单模板
        self.create_skill(
            name="农产品订单",
            category="product",
            schema=[
                {"key": "product", "title": "商品名", "type": "text"},
                {"key": "quantity", "title": "数量", "type": "number"},
                {"key": "unit", "title": "单位", "type": "text"},
                {"key": "price", "title": "单价", "type": "number"},
                {"key": "total", "title": "金额", "type": "number"},
            ],
            description="农产品采购/销售订单",
            keywords=["水果", "蔬菜", "农产品", "生鲜"],
        )
        
        # 通用订单模板
        self.create_skill(
            name="通用订单",
            category="general",
            schema=[
                {"key": "item", "title": "项目", "type": "text"},
                {"key": "quantity", "title": "数量", "type": "number"},
                {"key": "unit", "title": "单位", "type": "text"},
                {"key": "price", "title": "单价", "type": "number"},
                {"key": "remark", "title": "备注", "type": "text"},
            ],
            description="通用订单模板",
            keywords=["订单", "采购", "销售"],
        )
        
        # 客户列表模板
        self.create_skill(
            name="客户列表",
            category="customer",
            schema=[
                {"key": "name", "title": "客户名称", "type": "text"},
                {"key": "contact", "title": "联系人", "type": "text"},
                {"key": "phone", "title": "电话", "type": "text"},
                {"key": "address", "title": "地址", "type": "text"},
            ],
            description="客户信息管理",
            keywords=["客户", "联系人", "商户"],
        )
    
    def create_skill(
        self,
        name: str,
        category: str,
        schema: List[Dict[str, Any]],
        description: str = "",
        keywords: List[str] = None,
    ) -> Skill:
        """创建新 Skill"""
        # 生成唯一 ID
        skill_id = f"skill_{name.lower().replace(' ', '_')}_{len(self.skills)}"
        
        skill = Skill(
            id=skill_id,
            name=name,
            category=category,
            schema=schema,
            description=description,
            keywords=keywords or [],
        )
        
        self.skills[skill_id] = skill
        self._save_to_file()
        
        logger.info(f"创建 Skill: {skill_id} - {name}")
        return skill
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """获取 Skill"""
        return self.skills.get(skill_id)
    
    def list_skills(self, category: str = None) -> List[Skill]:
        """列出 Skills"""
        skills = list(self.skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        return skills
    
    def delete_skill(self, skill_id: str) -> bool:
        """删除 Skill"""
        if skill_id in self.skills:
            del self.skills[skill_id]
            self._save_to_file()
            logger.info(f"删除 Skill: {skill_id}")
            return True
        return False
    
    def get_schema_for_skill(self, skill_id: str) -> Optional[List[Dict[str, Any]]]:
        """获取 Skill 的表头 Schema"""
        skill = self.get_skill(skill_id)
        return skill.schema if skill else None
    
    def match_skills_by_keywords(self, text: str) -> List[str]:
        """通过关键词匹配 Skills"""
        matched = []
        text_lower = text.lower()
        
        for skill in self.skills.values():
            for keyword in skill.keywords:
                if keyword.lower() in text_lower:
                    if skill.id not in matched:
                        matched.append(skill.id)
                    break
        
        return matched
    
    def get_skills_summary(self) -> str:
        """生成 Skills 摘要（供 LLM 参考）"""
        if not self.skills:
            return "当前没有可用的模板。"
        
        lines = ["可用的表格模板："]
        for skill in self.skills.values():
            cols = ", ".join([c["title"] for c in skill.schema[:4]])
            lines.append(f"- {skill.name} ({skill.category}): {cols}...")
        
        return "\n".join(lines)
    
    # ========== 持久化 ==========
    
    def _save_to_file(self):
        """保存到文件"""
        try:
            data = {sid: s.to_dict() for sid, s in self.skills.items()}
            with open(self._storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存 Skills 失败: {str(e)}")
    
    def _load_from_file(self):
        """从文件加载"""
        if not os.path.exists(self._storage_path):
            return
        
        try:
            with open(self._storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for sid, sdata in data.items():
                self.skills[sid] = Skill.from_dict(sdata)
            
            logger.info(f"从文件加载 {len(self.skills)} 个 Skills")
        except Exception as e:
            logger.error(f"加载 Skills 失败: {str(e)}")


# 全局单例
skill_registry = SkillRegistry()
