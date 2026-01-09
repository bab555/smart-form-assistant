import pytest
from app.agents.intent_classifier import classify_intent, Intent

@pytest.mark.asyncio
async def test_classify_intent_keywords():
    """测试基于关键词的意图分类"""
    
    # 咨询类
    intent, conf = await classify_intent("这个多少钱？")
    assert intent == Intent.CONSULTATIVE
    assert conf >= 0.9
    
    intent, conf = await classify_intent("总共多少钱")
    assert intent == Intent.CONSULTATIVE
    
    # 操作类
    intent, conf = await classify_intent("修改第一行为100")
    assert intent == Intent.OPERATIONAL
    assert conf >= 0.9
    
    intent, conf = await classify_intent("删除这一行")
    assert intent == Intent.OPERATIONAL
    
    # 提取类
    intent, conf = await classify_intent("提取数据", task_type="extract")
    assert intent == Intent.EXTRACTION
    assert conf == 1.0

@pytest.mark.asyncio
async def test_classify_default():
    """测试默认分类"""
    intent, conf = await classify_intent("今天天气不错")
    # 应该默认为咨询，或者低置信度
    assert intent == Intent.CONSULTATIVE
    assert conf <= 0.5

