"""
商品库导入脚本

用法:
    python scripts/import_products.py [excel_path]
    
默认读取项目根目录的 商品库.xlsx
"""
import sys
import asyncio
from pathlib import Path
import time

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.knowledge_base import vector_store
from app.core.logger import app_logger as logger


async def main():
    """主函数"""
    # 确定 Excel 路径
    if len(sys.argv) > 1:
        excel_path = sys.argv[1]
    else:
        # 默认路径
        excel_path = Path(__file__).parent.parent.parent / "商品库.xlsx"
        if not excel_path.exists():
            excel_path = Path(__file__).parent.parent / "data" / "商品库.xlsx"
    
    excel_path = Path(excel_path)
    
    if not excel_path.exists():
        print(f"❌ 文件不存在: {excel_path}")
        print("用法: python scripts/import_products.py [excel_path]")
        sys.exit(1)
    
    print(f"📦 开始导入商品库: {excel_path}")
    print("-" * 50)
    
    # 导入
    start = time.time()
    result = await vector_store.import_from_excel(str(excel_path))
    elapsed = time.time() - start
    
    # 获取实际的索引引用
    idx = vector_store.product_index
    
    # 输出结果
    print(f"\n✅ 导入完成!")
    print(f"   - 总商品数: {result['total_imported']}")
    print(f"   - 跳过行数: {result['skipped']}")
    print(f"   - 分类数量: {len(result['categories'])}")
    print(f"   - 耗时: {elapsed:.2f}s")
    print(f"\n📁 分类列表:")
    for cat in result['categories']:
        count = idx.by_category.get(cat, [])
        print(f"   - {cat}: {len(count)} 条")
    
    # 测试检索
    print(f"\n🔍 检索测试:")
    test_queries = ["猪肚", "芝麻", "土豆", "可乐", "zhud", "鸡爪"]
    
    for query in test_queries:
        start = time.time()
        results = idx.search(query, limit=3)
        elapsed_ms = (time.time() - start) * 1000
        
        if results:
            top = results[0]
            print(f"   「{query}」→「{top.product.name}」")
            print(f"      分数: {top.score:.2f}, 类型: {top.match_type}, 耗时: {elapsed_ms:.1f}ms")
        else:
            print(f"   「{query}」→ 未找到 ({elapsed_ms:.1f}ms)")
    
    # 测试校对
    print(f"\n📝 校对测试:")
    test_calibrations = ["猪读", "芝麻先料", "鸡抓", "xigua"]
    
    for text in test_calibrations:
        start = time.time()
        cal_result = idx.calibrate(text)
        elapsed_ms = (time.time() - start) * 1000
        
        print(f"   「{text}」→「{cal_result.calibrated}」")
        print(f"      置信度: {cal_result.confidence:.2f}, 建议: {cal_result.suggestion or '无'} ({elapsed_ms:.1f}ms)")
    
    # 统计信息
    print(f"\n📊 索引统计:")
    stats = idx.stats()
    print(f"   - 总商品: {stats['total_products']}")
    print(f"   - 字符索引: {stats['unique_chars']} 个字符")
    print(f"   - 二字组合: {stats['bigrams']} 个")
    
    print("\n" + "=" * 50)
    print("导入完成! 索引已保存到 data/product_index.pkl")


if __name__ == "__main__":
    asyncio.run(main())

