"""
快速商品索引服务

提供多层检索能力：
- Layer 1: 精确匹配 (Dict, O(1))
- Layer 2: 前缀匹配 (Trie 树)
- Layer 3: 包含匹配 (倒排索引)
- Layer 4: 拼音匹配
- Layer 5: 模糊匹配 (编辑距离)

设计原则：速度优先，语义检索仅作兜底
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import re
from app.core.logger import app_logger as logger

# 尝试导入 pypinyin，如果没有则使用简单映射
try:
    import pypinyin
    HAS_PYPINYIN = True
except ImportError:
    HAS_PYPINYIN = False
    logger.warning("pypinyin 未安装，拼音检索功能将受限")


# ========== 数据结构 ==========

@dataclass
class Product:
    """商品实体"""
    id: int
    code: str
    name: str
    category: str       # 一级分类
    category2: str      # 二级分类
    category3: str      # 三级分类
    unit: str
    price: float
    spec: str
    brand: str
    manufacturer: str   # 生产厂家
    status: str         # 上下架状态
    
    # 预计算的检索字段
    name_lower: str = ""
    name_pinyin: str = ""       # 完整拼音: "zhudu"
    name_initials: str = ""     # 首字母: "zd"
    
    def __post_init__(self):
        """初始化后计算检索字段"""
        self.name_lower = self.name.lower() if self.name else ""
        if HAS_PYPINYIN and self.name:
            try:
                # 完整拼音
                self.name_pinyin = ''.join(
                    pypinyin.lazy_pinyin(self.name, style=pypinyin.Style.NORMAL)
                )
                # 首字母
                self.name_initials = ''.join(
                    p[0] for p in pypinyin.lazy_pinyin(self.name, style=pypinyin.Style.NORMAL)
                    if p
                )
            except Exception:
                pass
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "category": self.category,
            "category2": self.category2,
            "category3": self.category3,
            "unit": self.unit,
            "price": self.price,
            "spec": self.spec,
            "brand": self.brand,
            "manufacturer": self.manufacturer,
            "status": self.status,
        }


@dataclass
class SearchResult:
    """检索结果"""
    product: Product
    score: float            # 匹配分数 0-1
    match_type: str         # 匹配类型: exact/prefix/contains/pinyin/fuzzy
    matched_field: str      # 匹配字段: name/id/code/pinyin


@dataclass
class CalibrationResult:
    """校对结果"""
    original: str                      # 原始输入
    calibrated: str                    # 校正后名称
    product: Optional[Product]         # 匹配的商品
    confidence: float                  # 置信度 0-1
    match_type: str                    # 匹配类型
    suggestion: Optional[str] = None   # 校对建议
    is_ambiguous: bool = False         # 是否有歧义
    candidates: List[str] = field(default_factory=list)  # 候选列表


# ========== Trie 树 ==========

class TrieNode:
    """Trie 树节点"""
    
    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}
        self.is_end: bool = False
        self.product_ids: Set[int] = set()  # 存储商品 ID


class Trie:
    """Trie 树实现"""
    
    def __init__(self):
        self.root = TrieNode()
    
    def insert(self, word: str, product_id: int):
        """插入词"""
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
            # 每个前缀节点都记录包含它的商品
            node.product_ids.add(product_id)
        node.is_end = True
    
    def search_prefix(self, prefix: str) -> Set[int]:
        """前缀搜索，返回商品 ID 集合"""
        node = self.root
        for char in prefix:
            if char not in node.children:
                return set()
            node = node.children[char]
        return node.product_ids
    
    def exact_match(self, word: str) -> Set[int]:
        """精确匹配"""
        node = self.root
        for char in word:
            if char not in node.children:
                return set()
            node = node.children[char]
        return node.product_ids if node.is_end else set()


# ========== 快速索引 ==========

class FastProductIndex:
    """
    快速商品索引
    
    支持多层检索，速度优先
    """
    
    def __init__(self):
        # === Layer 1: 精确匹配索引 (O(1)) ===
        self.by_name: Dict[str, Product] = {}       # 名称 → 商品
        self.by_name_lower: Dict[str, Product] = {} # 小写名称 → 商品
        self.by_id: Dict[int, Product] = {}         # ID → 商品
        self.by_code: Dict[str, Product] = {}       # 编号 → 商品
        
        # === Layer 2: Trie 树索引 ===
        self.name_trie = Trie()                     # 名称 Trie
        self.pinyin_trie = Trie()                   # 拼音 Trie
        self.initials_trie = Trie()                 # 首字母 Trie
        
        # === Layer 3: 倒排索引 ===
        self.char_index: Dict[str, Set[int]] = defaultdict(set)  # 单字符 → ID集合
        self.bigram_index: Dict[str, Set[int]] = defaultdict(set)  # 二字组合 → ID集合
        
        # === 分类索引 ===
        self.by_category: Dict[str, List[int]] = defaultdict(list)  # 分类 → ID列表
        
        # 所有商品
        self.products: Dict[int, Product] = {}
        
        # 统计
        self.total_count: int = 0
    
    def add_product(self, product: Product):
        """添加商品到索引"""
        pid = product.id
        
        # Layer 1: 精确索引
        self.by_name[product.name] = product
        self.by_name_lower[product.name_lower] = product
        self.by_id[pid] = product
        if product.code:
            self.by_code[product.code] = product
        
        # Layer 2: Trie 索引
        self.name_trie.insert(product.name, pid)
        if product.name_pinyin:
            self.pinyin_trie.insert(product.name_pinyin, pid)
        if product.name_initials:
            self.initials_trie.insert(product.name_initials, pid)
        
        # Layer 3: 倒排索引
        for char in product.name:
            self.char_index[char].add(pid)
        # 二字组合
        for i in range(len(product.name) - 1):
            bigram = product.name[i:i+2]
            self.bigram_index[bigram].add(pid)
        
        # 分类索引
        if product.category:
            self.by_category[product.category].append(pid)
        
        # 存储
        self.products[pid] = product
        self.total_count += 1
    
    def search(
        self,
        query: str,
        limit: int = 5,
        category: str = None
    ) -> List[SearchResult]:
        """
        多层检索
        
        Args:
            query: 查询文本
            limit: 返回数量限制
            category: 分类过滤
            
        Returns:
            SearchResult 列表，按分数降序
        """
        if not query:
            return []
        
        query_lower = query.lower()
        results: List[SearchResult] = []
        seen_ids: Set[int] = set()
        
        # 分类过滤集合
        category_filter = None
        if category and category in self.by_category:
            category_filter = set(self.by_category[category])
        
        def add_result(product: Product, score: float, match_type: str, field: str):
            """添加结果（去重）"""
            if product.id in seen_ids:
                return
            if category_filter and product.id not in category_filter:
                return
            seen_ids.add(product.id)
            results.append(SearchResult(
                product=product,
                score=score,
                match_type=match_type,
                matched_field=field
            ))
        
        # === Layer 1: 精确匹配 ===
        
        # 名称精确匹配
        if query in self.by_name:
            add_result(self.by_name[query], 1.0, "exact", "name")
        elif query_lower in self.by_name_lower:
            add_result(self.by_name_lower[query_lower], 0.99, "exact", "name")
        
        # ID/编号精确匹配
        if query.isdigit():
            qid = int(query)
            if qid in self.by_id:
                add_result(self.by_id[qid], 1.0, "exact", "id")
        if query in self.by_code:
            add_result(self.by_code[query], 1.0, "exact", "code")
        
        if len(results) >= limit:
            return results[:limit]
        
        # === Layer 2: 前缀匹配 ===
        
        prefix_ids = self.name_trie.search_prefix(query)
        for pid in prefix_ids:
            if len(results) >= limit:
                break
            if pid in self.products:
                product = self.products[pid]
                # 计算前缀匹配分数
                score = len(query) / len(product.name) if product.name else 0
                add_result(product, min(0.95, 0.7 + score * 0.25), "prefix", "name")
        
        if len(results) >= limit:
            return results[:limit]
        
        # === Layer 3: 包含匹配 ===
        
        # 使用倒排索引找包含所有字符的商品
        if len(query) >= 2:
            # 二字组合匹配
            bigram_sets = []
            for i in range(len(query) - 1):
                bigram = query[i:i+2]
                if bigram in self.bigram_index:
                    bigram_sets.append(self.bigram_index[bigram])
            
            if bigram_sets:
                # 取交集
                common_ids = bigram_sets[0]
                for s in bigram_sets[1:]:
                    common_ids = common_ids & s
                
                for pid in common_ids:
                    if len(results) >= limit:
                        break
                    if pid in self.products:
                        product = self.products[pid]
                        # 计算包含匹配分数
                        if query in product.name:
                            score = len(query) / len(product.name)
                            add_result(product, min(0.9, 0.5 + score * 0.4), "contains", "name")
        
        # 单字符交集（更宽松）
        if len(results) < limit:
            char_sets = [self.char_index.get(c, set()) for c in query]
            if char_sets and all(char_sets):
                common_ids = char_sets[0]
                for s in char_sets[1:]:
                    common_ids = common_ids & s
                
                for pid in list(common_ids)[:limit * 2]:
                    if len(results) >= limit:
                        break
                    if pid in self.products:
                        product = self.products[pid]
                        score = len(query) / len(product.name) * 0.6
                        add_result(product, min(0.7, score), "contains", "name")
        
        if len(results) >= limit:
            return results[:limit]
        
        # === Layer 4: 拼音匹配 ===
        
        if HAS_PYPINYIN:
            query_pinyin = ''.join(
                pypinyin.lazy_pinyin(query, style=pypinyin.Style.NORMAL)
            )
            
            # 拼音前缀匹配
            pinyin_ids = self.pinyin_trie.search_prefix(query_pinyin)
            for pid in pinyin_ids:
                if len(results) >= limit:
                    break
                if pid in self.products:
                    product = self.products[pid]
                    score = len(query_pinyin) / len(product.name_pinyin) if product.name_pinyin else 0
                    add_result(product, min(0.8, 0.4 + score * 0.4), "pinyin", "pinyin")
            
            # 首字母匹配
            if len(results) < limit and len(query) <= 6:
                query_initials = query_pinyin[:len(query)]  # 取前几个字母作为首字母
                initials_ids = self.initials_trie.search_prefix(query_initials)
                for pid in initials_ids:
                    if len(results) >= limit:
                        break
                    if pid in self.products:
                        product = self.products[pid]
                        add_result(product, 0.5, "pinyin", "initials")
        
        if len(results) >= limit:
            return results[:limit]
        
        # === Layer 5: 模糊匹配（编辑距离）===
        
        if len(results) < limit and len(query) >= 2:
            fuzzy_results = self._fuzzy_search(query, limit - len(results), category_filter)
            for product, score in fuzzy_results:
                add_result(product, score, "fuzzy", "name")
        
        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
    def _fuzzy_search(
        self,
        query: str,
        limit: int,
        category_filter: Set[int] = None
    ) -> List[Tuple[Product, float]]:
        """
        模糊搜索（编辑距离）
        
        为了性能，只在候选集中搜索
        """
        results = []
        
        # 先用字符交集缩小范围
        candidates = set()
        for char in query:
            if char in self.char_index:
                candidates.update(self.char_index[char])
        
        if category_filter:
            candidates = candidates & category_filter
        
        # 限制候选数量
        candidates = list(candidates)[:500]
        
        for pid in candidates:
            if pid not in self.products:
                continue
            product = self.products[pid]
            
            # 计算编辑距离
            distance = self._levenshtein_distance(query, product.name)
            max_len = max(len(query), len(product.name))
            
            if max_len > 0:
                similarity = 1 - (distance / max_len)
                if similarity > 0.5:  # 至少 50% 相似
                    results.append((product, similarity * 0.7))  # 模糊匹配打折
        
        # 按相似度排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """计算编辑距离"""
        if len(s1) < len(s2):
            s1, s2 = s2, s1
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def get_by_id(self, product_id: int) -> Optional[Product]:
        """通过 ID 获取商品"""
        return self.products.get(product_id)
    
    def get_by_name(self, name: str) -> Optional[Product]:
        """通过名称获取商品"""
        return self.by_name.get(name)
    
    def get_categories(self) -> List[str]:
        """获取所有分类"""
        return list(self.by_category.keys())
    
    def get_by_category(self, category: str, limit: int = 100) -> List[Product]:
        """获取分类下的商品"""
        ids = self.by_category.get(category, [])[:limit]
        return [self.products[pid] for pid in ids if pid in self.products]
    
    def calibrate(self, raw_text: str, category: str = None) -> CalibrationResult:
        """
        校对商品名称
        
        Args:
            raw_text: 原始输入（可能有 OCR 错误）
            category: 分类提示
            
        Returns:
            CalibrationResult
        """
        if not raw_text or not raw_text.strip():
            return CalibrationResult(
                original=raw_text,
                calibrated=raw_text,
                product=None,
                confidence=0,
                match_type="none",
                suggestion="输入为空"
            )
        
        raw_text = raw_text.strip()
        
        # 检索
        results = self.search(raw_text, limit=5, category=category)
        
        if not results:
            return CalibrationResult(
                original=raw_text,
                calibrated=raw_text,
                product=None,
                confidence=0,
                match_type="not_found",
                suggestion=f"「{raw_text}」未在商品库中找到"
            )
        
        top1 = results[0]
        product = top1.product
        
        # 生成校对建议
        suggestion = None
        is_ambiguous = False
        candidates = []
        
        # 精确匹配
        if top1.match_type == "exact" and top1.score >= 0.99:
            # 检查价格
            if product.price == 0:
                suggestion = f"⚠️ 商品「{product.name}」无价格"
            # 名称完全一致，无需校对建议
            
        else:
            # 非精确匹配，需要校对建议
            if raw_text != product.name:
                suggestion = f"「{raw_text}」→「{product.name}」"
                if product.price == 0:
                    suggestion += " (无价格)"
                elif product.price > 0:
                    suggestion += f" ({product.unit}/¥{product.price})"
            
            # 检查歧义
            if len(results) > 1:
                top2 = results[1]
                if top1.score - top2.score < 0.15:  # 分数接近
                    is_ambiguous = True
                    candidates = [r.product.name for r in results[:3]]
                    suggestion = f"「{raw_text}」可能是: {', '.join(candidates)}"
        
        return CalibrationResult(
            original=raw_text,
            calibrated=product.name,
            product=product,
            confidence=top1.score,
            match_type=top1.match_type,
            suggestion=suggestion,
            is_ambiguous=is_ambiguous,
            candidates=candidates
        )
    
    def batch_calibrate(
        self,
        texts: List[str],
        category: str = None
    ) -> List[CalibrationResult]:
        """批量校对"""
        return [self.calibrate(text, category) for text in texts]
    
    def stats(self) -> dict:
        """统计信息"""
        return {
            "total_products": self.total_count,
            "categories": len(self.by_category),
            "category_counts": {k: len(v) for k, v in self.by_category.items()},
            "unique_chars": len(self.char_index),
            "bigrams": len(self.bigram_index),
        }


# ========== 全局实例 ==========

product_index = FastProductIndex()

