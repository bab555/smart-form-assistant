import pytest
from app.services.skill_registry import Skill

def test_create_skill(temp_skill_registry):
    """测试创建 Skill"""
    schema = [{"key": "test", "title": "Test", "type": "text"}]
    skill = temp_skill_registry.create_skill(
        name="Test Skill",
        category="general",
        schema=schema,
        description="A test skill"
    )
    
    assert skill.name == "Test Skill"
    assert skill.category == "general"
    assert len(temp_skill_registry.skills) == 1
    
    # 验证持久化
    # 重新加载 Registry
    new_registry = temp_skill_registry.__class__(storage_path=temp_skill_registry._storage_path)
    new_registry.initialize()
    assert len(new_registry.skills) == 1
    assert new_registry.get_skill(skill.id).name == "Test Skill"

def test_delete_skill(temp_skill_registry):
    """测试删除 Skill"""
    schema = [{"key": "test", "title": "Test", "type": "text"}]
    skill = temp_skill_registry.create_skill("To Delete", "general", schema)
    
    assert len(temp_skill_registry.skills) == 1
    
    success = temp_skill_registry.delete_skill(skill.id)
    assert success is True
    assert len(temp_skill_registry.skills) == 0
    
    # 删除不存在的 Skill
    success = temp_skill_registry.delete_skill("non_existent")
    assert success is False

def test_list_skills(temp_skill_registry):
    """测试列出 Skills"""
    schema = [{"key": "test", "title": "Test", "type": "text"}]
    temp_skill_registry.create_skill("Skill A", "cat1", schema)
    temp_skill_registry.create_skill("Skill B", "cat2", schema)
    temp_skill_registry.create_skill("Skill C", "cat1", schema)
    
    all_skills = temp_skill_registry.list_skills()
    assert len(all_skills) == 3
    
    cat1_skills = temp_skill_registry.list_skills(category="cat1")
    assert len(cat1_skills) == 2
    assert all(s.category == "cat1" for s in cat1_skills)

def test_match_skills(temp_skill_registry):
    """测试关键词匹配"""
    schema = [{"key": "test", "title": "Test", "type": "text"}]
    temp_skill_registry.create_skill(
        "Apple Skill", "fruit", schema, keywords=["apple", "fruit"]
    )
    temp_skill_registry.create_skill(
        "Car Skill", "vehicle", schema, keywords=["car", "vehicle"]
    )
    
    matched = temp_skill_registry.match_skills_by_keywords("I like apple pie")
    assert len(matched) == 1
    assert "apple" in temp_skill_registry.get_skill(matched[0]).keywords
    
    matched_none = temp_skill_registry.match_skills_by_keywords("sky is blue")
    assert len(matched_none) == 0

