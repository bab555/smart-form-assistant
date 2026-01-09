"""
测试意图分类器
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.intent_classifier import intent_classifier, Intent

# 测试用例
test_cases = [
    # 修改操作
    ('把第一行的价格改成100', Intent.MODIFY),
    ('将第三行商品名称修改为红富士苹果', Intent.MODIFY),
    ('修改一下数量', Intent.MODIFY),
    
    # 添加操作
    ('添加一行，苹果10斤', Intent.ADD),
    ('新增一条记录', Intent.ADD),
    
    # 删除操作
    ('删除第一行', Intent.DELETE),
    ('去掉最后一行', Intent.DELETE),
    
    # 查询操作
    ('有没有猪肉', Intent.QUERY_PRODUCT),
    ('查一下芝麻', Intent.QUERY_PRODUCT),
    
    # 计算操作
    ('总共多少钱', Intent.CALCULATE),
    ('帮我算一下', Intent.CALCULATE),
    
    # 确认/否定
    ('是的', Intent.CONFIRM),
    ('好的', Intent.CONFIRM),
    ('不是', Intent.REJECT),
    ('取消', Intent.REJECT),
    
    # 打招呼
    ('你好', Intent.GREETING),
    
    # 帮助
    ('怎么用', Intent.HELP),
]

print('=' * 60)
print('意图分类器测试')
print('=' * 60)

correct = 0
for text, expected in test_cases:
    result = intent_classifier.classify(text)
    status = '✅' if result.intent == expected else '❌'
    if result.intent == expected:
        correct += 1
    print(f'{status} "{text}"')
    print(f'   预期: {expected.value}, 实际: {result.intent.value} ({result.confidence:.2f})')
    if result.extracted_params:
        print(f'   参数: {result.extracted_params}')
    if result.needs_clarification:
        print(f'   需澄清: {result.clarification_question}')
    print()

print('=' * 60)
print(f'准确率: {correct}/{len(test_cases)} ({correct/len(test_cases)*100:.1f}%)')

