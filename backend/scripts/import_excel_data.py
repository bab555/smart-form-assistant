"""
Excel 商品数据导入脚本 - 适配现有向量库
用法: python scripts/import_excel_data.py data/商品库.xlsx
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import pickle
import numpy as np
import faiss
import pandas as pd
from pathlib import Path
from app.core.config import settings
from app.core.logger import app_logger as logger
from app.services.aliyun_llm import llm_service


async def import_excel_to_vectorstore(excel_path: str):
    """
    从 Excel 导入数据到向量库
    """
    logger.info(f"开始导入 Excel 数据: {excel_path}")
    
    # 读取 Excel
    df = pd.read_excel(excel_path)
    logger.info(f"读取到 {len(df)} 条记录")
    logger.info(f"Excel 列名: {list(df.columns)}")
    
    # 准备数据
    entities = []
    metadata_list = []
    
    for idx, row in df.iterrows():
        try:
            product_name = str(row.get('商品名称', '')).strip()
            if not product_name or product_name == 'nan':
                continue
            
            # 构建完整的商品描述文本（用于向量化）
            description_parts = [product_name]
            
            spec = str(row.get('商品规格', '')).strip()
            if spec and spec != 'nan':
                description_parts.append(spec)
            
            brand = str(row.get('品牌', '')).strip()
            if brand and brand != 'nan':
                description_parts.append(brand)
            
            full_text = ' '.join(description_parts)
            
            # 分类
            cat3 = str(row.get('三级分类', '')).strip()
            category = cat3 if cat3 and cat3 != 'nan' else 'product'
            
            entities.append(full_text)
            metadata_list.append({
                'text': full_text,
                'product_name': product_name,
                'category': category,
                'spec': spec if spec != 'nan' else '',
                'brand': brand if brand != 'nan' else '',
                'id': len(entities) - 1
            })
                
        except Exception as e:
            logger.warning(f"跳过第 {idx} 行: {str(e)}")
            continue
    
    logger.info(f"准备导入 {len(entities)} 条有效记录")
    
    # 批量获取嵌入向量
    logger.info("正在生成向量嵌入（这可能需要几分钟）...")
    
    # 分批处理，每批 20 条
    batch_size = 20
    all_embeddings = []
    
    for i in range(0, len(entities), batch_size):
        batch = entities[i:i+batch_size]
        logger.info(f"处理第 {i//batch_size + 1}/{(len(entities)-1)//batch_size + 1} 批...")
        
        embeddings = await llm_service.batch_get_embeddings(batch, text_type="document")
        all_embeddings.extend(embeddings)
    
    # 转换为 numpy 数组
    vectors = np.array(all_embeddings, dtype='float32')
    
    # 创建 FAISS 索引
    dimension = 1536  # text-embedding-v2 的维度
    index = faiss.IndexFlatL2(dimension)
    index.add(vectors)
    
    # 保存索引
    index_path = Path(settings.FAISS_INDEX_PATH)
    metadata_path = Path(settings.FAISS_METADATA_PATH)
    
    # 确保目录存在
    index_path.parent.mkdir(parents=True, exist_ok=True)
    
    faiss.write_index(index, str(index_path))
    
    with open(metadata_path, 'wb') as f:
        pickle.dump(metadata_list, f)
    
    logger.info(f"✅ 导入完成！共导入 {len(entities)} 条商品数据")
    logger.info(f"索引保存到: {index_path}")
    logger.info(f"元数据保存到: {metadata_path}")
    
    return len(entities)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='导入 Excel 商品数据到向量库')
    parser.add_argument('excel_file', help='Excel 文件路径')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.excel_file):
        print(f"❌ 文件不存在: {args.excel_file}")
        sys.exit(1)
    
    # 运行异步导入
    asyncio.run(import_excel_to_vectorstore(args.excel_file))
    
    print("\n✅ 数据导入完成！请重启后端服务: sudo systemctl restart smart-form-backend")
