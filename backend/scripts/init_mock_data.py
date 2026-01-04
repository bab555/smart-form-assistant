"""
初始化 Mock 数据和向量索引
"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.knowledge_base import vector_store
from app.core.logger import app_logger as logger


async def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始初始化 Mock 数据和向量索引")
    logger.info("=" * 60)
    
    try:
        # 强制重建索引
        await vector_store.initialize(force_rebuild=True)
        
        logger.info("=" * 60)
        logger.info("✅ 初始化完成！")
        logger.info("=" * 60)
        
        # 测试检索
        logger.info("\n测试检索功能:")
        test_queries = [
            ("红富土苹果", "product"),  # 模拟 OCR 错误
            ("张散", "customer"),  # 模拟识别错误
            ("公斤", "unit")
        ]
        
        for query, category in test_queries:
            results = await vector_store.search(query, top_k=3, category=category)
            logger.info(f"\n查询: '{query}' (类别: {category})")
            for i, result in enumerate(results, 1):
                logger.info(f"  {i}. {result['text']} (分数: {result['combined_score']:.3f})")
        
        # 测试校准
        logger.info("\n测试校准功能:")
        calibrated, confidence, is_amb, candidates = await vector_store.calibrate_text(
            "红富土苹果", category="product"
        )
        logger.info(f"原文: 红富土苹果")
        logger.info(f"校准: {calibrated}")
        logger.info(f"置信度: {confidence:.2f}")
        logger.info(f"歧义: {is_amb}")
        if candidates:
            logger.info(f"候选: {candidates}")
        
    except Exception as e:
        logger.error(f"❌ 初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

