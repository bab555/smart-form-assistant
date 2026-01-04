"""
知识库服务 - Mock数据 + FAISS向量检索
"""
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import faiss
from app.core.config import settings
from app.core.logger import app_logger as logger
from app.services.aliyun_llm import llm_service
from app.utils.helpers import calculate_text_similarity


class MockKnowledgeBase:
    """Mock 知识库数据"""
    
    # 商品数据库（Mock）
    PRODUCTS = [
        "红富士苹果", "黄金富士苹果", "嘎啦苹果", "红蛇果", "青苹果",
        "香蕉", "进口香蕉", "国产香蕉", "芭蕉", "小米蕉",
        "橙子", "脐橙", "血橙", "冰糖橙", "贡橙",
        "西瓜", "无籽西瓜", "麒麟西瓜", "8424西瓜", "黑美人西瓜",
        "草莓", "奶油草莓", "红颜草莓", "章姬草莓",
        "葡萄", "巨峰葡萄", "夏黑葡萄", "阳光玫瑰葡萄", "红提", "青提",
        "芒果", "台芒", "贵妃芒", "澳芒", "小台芒",
        "榴莲", "金枕榴莲", "猫山王榴莲", "干尧榴莲",
        "车厘子", "智利车厘子", "加拿大车厘子", "国产车厘子",
        "火龙果", "红心火龙果", "白心火龙果", "黄心火龙果",
        "猕猴桃", "红心猕猴桃", "绿心猕猴桃", "金果猕猴桃",
        "梨", "雪花梨", "皇冠梨", "鸭梨", "香梨", "丰水梨",
        "桃子", "水蜜桃", "油桃", "黄桃", "蟠桃",
        "荔枝", "妃子笑荔枝", "桂味荔枝", "糯米糍荔枝",
        "龙眼", "桂圆", "鲜龙眼",
        "山竹", "进口山竹", "泰国山竹",
        "菠萝", "凤梨", "台湾凤梨", "海南菠萝",
        "椰子", "椰青", "老椰子", "海南椰子",
        "柚子", "红心柚", "白心柚", "沙田柚", "蜜柚",
        "石榴", "软籽石榴", "突尼斯石榴", "红石榴"
    ]
    
    # 客户信息（Mock）
    CUSTOMERS = [
        "张三", "李四", "王五", "赵六", "刘七",
        "北京水果批发商行", "上海鲜果汇", "广州果园", "深圳鲜果店",
        "杭州水果超市", "成都果蔬市场", "武汉鲜果批发",
        "南京果品公司", "重庆水果行", "西安鲜果汇"
    ]
    
    # 单位（Mock）
    UNITS = ["斤", "公斤", "箱", "件", "个", "袋", "筐"]
    
    # 供应商（Mock）
    SUPPLIERS = [
        "山东水果基地", "云南果园", "海南农场", "新疆果业",
        "广西水果批发", "四川果蔬", "福建果园", "浙江农产品",
        "进口水果直采", "智利水果进口商", "泰国水果供应商"
    ]
    
    @classmethod
    def get_all_entities(cls, category: Optional[str] = None) -> List[str]:
        """
        获取所有实体数据
        
        Args:
            category: 类别筛选（product/customer/unit/supplier）
            
        Returns:
            List[str]: 实体列表
        """
        if category == "product":
            return cls.PRODUCTS
        elif category == "customer":
            return cls.CUSTOMERS
        elif category == "unit":
            return cls.UNITS
        elif category == "supplier":
            return cls.SUPPLIERS
        else:
            # 返回所有类别
            return cls.PRODUCTS + cls.CUSTOMERS + cls.UNITS + cls.SUPPLIERS


class VectorStoreService:
    """FAISS 向量存储服务"""
    
    def __init__(self):
        """初始化向量存储"""
        self.index: Optional[faiss.IndexFlatL2] = None
        self.metadata: List[Dict] = []
        self.dimension: int = 1536  # text-embedding-v2 的维度
        
        # 确保数据目录存在
        self.data_dir = Path("./data")
        self.data_dir.mkdir(exist_ok=True)
        
        self.index_path = Path(settings.FAISS_INDEX_PATH)
        self.metadata_path = Path(settings.FAISS_METADATA_PATH)
    
    async def initialize(self, force_rebuild: bool = False):
        """
        初始化向量库
        
        Args:
            force_rebuild: 是否强制重建索引
        """
        if force_rebuild or not self._index_exists():
            logger.info("开始构建向量索引...")
            await self._build_index()
        else:
            logger.info("加载已有向量索引...")
            self._load_index()
    
    def _index_exists(self) -> bool:
        """检查索引文件是否存在"""
        return self.index_path.exists() and self.metadata_path.exists()
    
    async def _build_index(self):
        """构建向量索引"""
        try:
            # 获取所有实体
            entities = MockKnowledgeBase.get_all_entities()
            logger.info(f"准备构建索引，共 {len(entities)} 条数据")
            
            # 批量获取嵌入向量
            embeddings = await llm_service.batch_get_embeddings(
                entities,
                text_type="document"
            )
            
            # 转换为 numpy 数组
            vectors = np.array(embeddings, dtype='float32')
            
            # 创建 FAISS 索引
            self.index = faiss.IndexFlatL2(self.dimension)
            self.index.add(vectors)
            
            # 构建元数据
            self.metadata = [
                {
                    "text": entity,
                    "category": self._classify_entity(entity),
                    "id": idx
                }
                for idx, entity in enumerate(entities)
            ]
            
            # 保存索引
            self._save_index()
            
            logger.info(f"向量索引构建完成，共 {self.index.ntotal} 条记录")
            
        except Exception as e:
            logger.error(f"构建向量索引失败: {str(e)}")
            raise
    
    def _classify_entity(self, entity: str) -> str:
        """分类实体"""
        if entity in MockKnowledgeBase.PRODUCTS:
            return "product"
        elif entity in MockKnowledgeBase.CUSTOMERS:
            return "customer"
        elif entity in MockKnowledgeBase.UNITS:
            return "unit"
        elif entity in MockKnowledgeBase.SUPPLIERS:
            return "supplier"
        else:
            return "unknown"
    
    def _save_index(self):
        """保存索引到文件"""
        try:
            # 保存 FAISS 索引
            faiss.write_index(self.index, str(self.index_path))
            
            # 保存元数据
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)
            
            logger.info("向量索引已保存到文件")
            
        except Exception as e:
            logger.error(f"保存索引失败: {str(e)}")
            raise
    
    def _load_index(self):
        """从文件加载索引"""
        try:
            # 加载 FAISS 索引
            self.index = faiss.read_index(str(self.index_path))
            
            # 加载元数据
            with open(self.metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            
            logger.info(f"向量索引加载完成，共 {self.index.ntotal} 条记录")
            
        except Exception as e:
            logger.error(f"加载索引失败: {str(e)}")
            raise
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None
    ) -> List[Dict]:
        """
        向量检索
        
        Args:
            query: 查询文本
            top_k: 返回前K个结果
            category: 类别筛选
            
        Returns:
            List[Dict]: 检索结果列表
        """
        try:
            if self.index is None:
                raise Exception("向量索引未初始化")
            
            # 获取查询向量
            query_embedding = await llm_service.get_embedding(query, text_type="query")
            query_vector = np.array([query_embedding], dtype='float32')
            
            # 向量检索
            distances, indices = self.index.search(query_vector, top_k * 2)  # 多检索一些，后续筛选
            
            # 构建结果
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx >= len(self.metadata):
                    continue
                
                meta = self.metadata[idx]
                
                # 类别筛选
                if category and meta['category'] != category:
                    continue
                
                # 计算文本相似度（二次排序）
                text_similarity = calculate_text_similarity(query, meta['text'])
                
                # 计算综合分数（向量距离越小越好，文本相似度越大越好）
                # 归一化距离分数
                vector_score = 1.0 / (1.0 + dist)
                combined_score = 0.6 * vector_score + 0.4 * text_similarity
                
                results.append({
                    "text": meta['text'],
                    "category": meta['category'],
                    "vector_distance": float(dist),
                    "text_similarity": float(text_similarity),
                    "combined_score": float(combined_score)
                })
                
                if len(results) >= top_k:
                    break
            
            # 按综合分数排序
            results.sort(key=lambda x: x['combined_score'], reverse=True)
            
            logger.debug(f"检索完成，查询: {query}, 返回 {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"向量检索失败: {str(e)}")
            raise
    
    async def calibrate_text(
        self,
        raw_text: str,
        category: Optional[str] = None
    ) -> Tuple[str, float, bool, Optional[List[str]]]:
        """
        校准文本 - 核心功能
        
        Args:
            raw_text: OCR/ASR识别的原始文本
            category: 类别提示
            
        Returns:
            Tuple[标准文本, 置信度, 是否歧义, 候选列表]
        """
        try:
            # 向量检索
            results = await self.search(raw_text, top_k=5, category=category)
            
            if not results:
                # 没有找到匹配项
                return raw_text, 0.0, False, None
            
            # 获取最佳匹配
            best_match = results[0]
            best_score = best_match['combined_score']
            
            # 检查歧义
            is_ambiguous = False
            candidates = None
            
            if len(results) >= 2:
                second_match = results[1]
                score_diff = best_score - second_match['combined_score']
                
                # 如果Top2的分数差异很小，认为存在歧义
                if score_diff < settings.AMBIGUITY_THRESHOLD:
                    is_ambiguous = True
                    candidates = [r['text'] for r in results[:3]]  # 返回前3个候选
                    logger.info(f"检测到歧义: {raw_text} -> {candidates}")
            
            # 计算置信度
            confidence = min(best_score, 1.0)
            
            logger.info(f"校准结果: {raw_text} -> {best_match['text']} (置信度: {confidence:.2f})")
            
            return best_match['text'], confidence, is_ambiguous, candidates
            
        except Exception as e:
            logger.error(f"文本校准失败: {str(e)}")
            # 失败时返回原文
            return raw_text, 0.5, False, None


# 全局单例
vector_store = VectorStoreService()

