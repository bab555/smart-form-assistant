import sys
import os
from pathlib import Path

# 将 backend 目录添加到 Python 路径，以便导入 app 模块
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import pytest
from app.services.skill_registry import SkillRegistry

@pytest.fixture
def temp_skill_registry(tmp_path):
    """
    创建一个使用临时文件的 SkillRegistry
    """
    temp_file = tmp_path / "test_skills.json"
    registry = SkillRegistry(storage_path=str(temp_file))
    return registry

