"""
知识库服务 - 统一入口

整合:
1. 商品快速索引 (FastProductIndex)
2. 分类管理
3. Excel 导入导出
4. 向量检索（兜底，可选）
"""
import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from io import BytesIO
from datetime import datetime

from app.core.config import settings
from app.core.logger import app_logger as logger
from app.services.product_index import (
    FastProductIndex, Product, SearchResult, CalibrationResult, product_index
)

# 尝试导入 FAISS（可选，用于语义检索兜底）
try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False
    logger.warning("FAISS 未安装，语义检索功能不可用")


class KnowledgeBaseService:
    """
    知识库统一服务
    
    提供:
    - 商品检索 (快速索引优先)
    - 商品校对
    - 分类管理
    - Excel 导入导出
    """
    
    def __init__(self):
        self.product_index = product_index
        self.initialized = False
        
        # 数据目录
        self.data_dir = Path("./data")
        self.data_dir.mkdir(exist_ok=True)
        
        # 持久化路径
        self.index_path = self.data_dir / "product_index.pkl"
        self.excel_path = self.data_dir / "商品库.xlsx"
    
    async def initialize(self, force_rebuild: bool = False):
        """
        初始化知识库
        
        Args:
            force_rebuild: 是否强制重建索引
        """
        if self.initialized and not force_rebuild:
            logger.info("知识库已初始化，跳过")
            return
        
        # 优先从持久化文件加载
        if not force_rebuild and self.index_path.exists():
            try:
                self._load_index()
                self.initialized = True
                logger.info(f"✅ 知识库从缓存加载，共 {self.product_index.total_count} 条商品")
                return
            except Exception as e:
                logger.warning(f"加载缓存失败: {str(e)}，将重建索引")
        
        # 从 Excel 构建索引
        if self.excel_path.exists():
            await self.import_from_excel(str(self.excel_path))
        else:
            # 尝试从项目根目录加载
            root_excel = Path("./商品库.xlsx")
            if root_excel.exists():
                await self.import_from_excel(str(root_excel))
            else:
                logger.warning("未找到商品库 Excel 文件，知识库为空")
        
        self.initialized = True
    
    async def import_from_excel(
        self,
        excel_path: str,
        save_cache: bool = True
    ) -> Dict[str, Any]:
        """
        从 Excel 导入商品数据
        
        Args:
            excel_path: Excel 文件路径
            save_cache: 是否保存缓存
            
        Returns:
            导入统计信息
        """
        logger.info(f"开始从 Excel 导入: {excel_path}")
        start_time = datetime.now()
        
        try:
            df = pd.read_excel(excel_path)
            
            # 清空现有索引
            self.product_index = FastProductIndex()
            
            # 统计
            total = 0
            skipped = 0
            
            for _, row in df.iterrows():
                # 跳过没有商品名称的行
                name = row.get('商品名称')
                if pd.isna(name) or not str(name).strip():
                    skipped += 1
                    continue
                
                # 构建商品对象
                product = Product(
                    id=int(row.get('商品ID', 0)),
                    code=str(row.get('商品编号', '')),
                    name=str(name).strip(),
                    category=str(row.get('一级分类', '')) if pd.notna(row.get('一级分类')) else "未分类",
                    category2=str(row.get('二级分类', '')) if pd.notna(row.get('二级分类')) else "",
                    category3=str(row.get('三级分类', '')) if pd.notna(row.get('三级分类')) else "",
                    unit=str(row.get('单位', '个')) if pd.notna(row.get('单位')) else "个",
                    price=float(row.get('单价', 0)) if pd.notna(row.get('单价')) else 0.0,
                    spec=str(row.get('商品规格', '')) if pd.notna(row.get('商品规格')) else "",
                    brand=str(row.get('品牌', '')) if pd.notna(row.get('品牌')) else "",
                    manufacturer=str(row.get('生产厂家', '')) if pd.notna(row.get('生产厂家')) else "",
                    status=str(row.get('上下架', '上架')) if pd.notna(row.get('上下架')) else "上架",
                )
                
                # 添加到索引
                self.product_index.add_product(product)
                total += 1
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # 保存缓存
            if save_cache:
                self._save_index()
            
            # 更新全局实例
            global product_index
            product_index = self.product_index
            
            stats = {
                "total_imported": total,
                "skipped": skipped,
                "categories": self.product_index.get_categories(),
                "elapsed_seconds": round(elapsed, 2),
            }
            
            logger.info(f"✅ 导入完成: {total} 条商品, 跳过 {skipped} 条, 耗时 {elapsed:.2f}s")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Excel 导入失败: {str(e)}")
            raise
    
    async def import_from_bytes(
        self,
        file_bytes: bytes,
        file_name: str = "upload.xlsx"
    ) -> Dict[str, Any]:
        """
        从上传的文件字节导入
        """
        # 保存到临时文件
        temp_path = self.data_dir / f"temp_{file_name}"
        with open(temp_path, 'wb') as f:
            f.write(file_bytes)
        
        try:
            result = await self.import_from_excel(str(temp_path))
            # 复制为正式文件
            import shutil
            shutil.copy(temp_path, self.excel_path)
            return result
        finally:
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
    
    def _save_index(self):
        """保存索引到缓存文件"""
        try:
            with open(self.index_path, 'wb') as f:
                pickle.dump(self.product_index, f)
            logger.info(f"索引已保存到 {self.index_path}")
        except Exception as e:
            logger.error(f"保存索引失败: {str(e)}")
    
    def _load_index(self):
        """从缓存加载索引"""
        with open(self.index_path, 'rb') as f:
            self.product_index = pickle.load(f)
        
        # 更新全局实例
        global product_index
        product_index = self.product_index
    
    # ========== 检索接口 ==========
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        category: str = None
    ) -> List[Dict]:
        """
        商品检索
        
        Args:
            query: 查询文本
            top_k: 返回数量
            category: 分类过滤
            
        Returns:
            商品列表
        """
        results = self.product_index.search(query, limit=top_k, category=category)
        
        return [
            {
                "id": r.product.id,
                "name": r.product.name,
                "code": r.product.code,
                "category": r.product.category,
                "unit": r.product.unit,
                "price": r.product.price,
                "spec": r.product.spec,
                "score": r.score,
                "match_type": r.match_type,
            }
            for r in results
        ]
    
    async def calibrate_text(
        self,
        raw_text: str,
        category: str = None
    ) -> Tuple[str, float, bool, Optional[List[str]]]:
        """
        校准文本（兼容旧接口）
        
        Args:
            raw_text: 原始文本
            category: 分类提示
            
        Returns:
            (校准后文本, 置信度, 是否歧义, 候选列表)
        """
        result = self.product_index.calibrate(raw_text, category)
        
        return (
            result.calibrated,
            result.confidence,
            result.is_ambiguous,
            result.candidates if result.candidates else None
        )
    
    async def calibrate(
        self,
        raw_text: str,
        category: str = None
    ) -> CalibrationResult:
        """
        校准商品名称（新接口）
        """
        return self.product_index.calibrate(raw_text, category)
    
    async def batch_calibrate(
        self,
        texts: List[str],
        category: str = None
    ) -> List[CalibrationResult]:
        """批量校准"""
        return self.product_index.batch_calibrate(texts, category)
    
    # ========== 分类管理 ==========
    
    def get_categories(self) -> List[str]:
        """获取所有分类"""
        return self.product_index.get_categories()
    
    def get_products_by_category(
        self,
        category: str,
        limit: int = 100
    ) -> List[Dict]:
        """获取分类下的商品"""
        products = self.product_index.get_by_category(category, limit)
        return [p.to_dict() for p in products]
    
    # ========== 商品管理 ==========
    
    def get_product(self, product_id: int) -> Optional[Dict]:
        """获取单个商品"""
        product = self.product_index.get_by_id(product_id)
        return product.to_dict() if product else None
    
    def get_product_by_name(self, name: str) -> Optional[Dict]:
        """通过名称获取商品"""
        product = self.product_index.get_by_name(name)
        return product.to_dict() if product else None
    
    # ========== 统计 ==========
    
    def stats(self) -> Dict:
        """获取统计信息"""
        return self.product_index.stats()


# ========== 全局实例 ==========

vector_store = KnowledgeBaseService()


# ========== 兼容旧代码 ==========

class VectorStoreService:
    """兼容旧代码的包装类"""
    
    def __init__(self):
        self._kb = vector_store
    
    async def initialize(self, force_rebuild: bool = False):
        await self._kb.initialize(force_rebuild)
    
    async def search(self, query: str, top_k: int = 5, category: str = None) -> List[Dict]:
        results = await self._kb.search(query, top_k, category)
        # 转换为旧格式
        return [
            {
                "text": r["name"],
                "category": r["category"],
                "combined_score": r["score"],
                "vector_distance": 0,
                "text_similarity": r["score"],
            }
            for r in results
        ]
    
    async def calibrate_text(
        self,
        raw_text: str,
        category: str = None
    ) -> Tuple[str, float, bool, Optional[List[str]]]:
        return await self._kb.calibrate_text(raw_text, category)
