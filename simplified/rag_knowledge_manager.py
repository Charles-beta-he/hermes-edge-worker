#!/usr/bin/env python3
"""
RAG知识管理系统
简化版：使用TF-IDF作为向量化方法（支持中文）
"""

import json
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import re

class ChineseTokenizer:
    """中文分词器（简单实现）"""
    
    def __init__(self):
        # 常用中文词汇
        self.common_words = set([
            "Python", "NumPy", "Pandas", "机器学习", "深度学习", "算法",
            "性能优化", "数组操作", "数据分析", "框架", "库", "技巧"
        ])
    
    def tokenize(self, text: str) -> List[str]:
        """分词"""
        # 简单实现：按空格和标点分词，保留中文词汇
        tokens = []
        
        # 英文单词
        english_words = re.findall(r'[a-zA-Z]+', text)
        tokens.extend(english_words)
        
        # 中文词汇（简单匹配）
        for word in self.common_words:
            if word in text:
                tokens.append(word)
        
        # 数字
        numbers = re.findall(r'\d+', text)
        tokens.extend(numbers)
        
        return tokens

class RAGKnowledgeManager:
    """RAG知识管理器"""
    
    def __init__(self):
        self.knowledge_base = {}  # 知识库
        self.tokenizer = ChineseTokenizer()  # 中文分词器
        self.vectorizer = TfidfVectorizer(tokenizer=self.tokenizer.tokenize)  # TF-IDF向量化器
        self.vectors = None  # 向量矩阵
        self.vector_index = {}  # 向量索引
        self.metrics = {
            "total_knowledge": 0,
            "total_searches": 0,
            "average_search_time": 0.0
        }
    
    def add_knowledge(self, knowledge_id: str, content: str, 
                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """添加知识"""
        # 存储知识
        self.knowledge_base[knowledge_id] = {
            "id": knowledge_id,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }
        
        # 更新向量索引
        self._update_vector_index()
        
        # 更新指标
        self.metrics["total_knowledge"] += 1
        
        return knowledge_id
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """语义搜索"""
        import time
        start_time = time.time()
        
        # 更新指标
        self.metrics["total_searches"] += 1
        
        # 如果没有知识，返回空
        if not self.knowledge_base:
            return []
        
        # 查询向量化
        query_vector = self.vectorizer.transform([query])
        
        # 计算相似度
        similarities = cosine_similarity(query_vector, self.vectors)[0]
        
        # 获取top_k结果
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0:
                knowledge_id = list(self.knowledge_base.keys())[idx]
                knowledge = self.knowledge_base[knowledge_id]
                results.append({
                    "id": knowledge_id,
                    "content": knowledge["content"],
                    "metadata": knowledge["metadata"],
                    "score": float(similarities[idx]),
                    "created_at": knowledge["created_at"]
                })
        
        # 更新搜索时间
        search_time = time.time() - start_time
        self._update_search_time(search_time)
        
        return results
    
    def get_knowledge(self, knowledge_id: str) -> Optional[Dict[str, Any]]:
        """获取知识"""
        return self.knowledge_base.get(knowledge_id)
    
    def list_knowledge(self) -> List[Dict[str, Any]]:
        """列出知识"""
        return list(self.knowledge_base.values())
    
    def delete_knowledge(self, knowledge_id: str) -> bool:
        """删除知识"""
        if knowledge_id in self.knowledge_base:
            del self.knowledge_base[knowledge_id]
            self._update_vector_index()
            self.metrics["total_knowledge"] -= 1
            return True
        return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics
    
    def _update_vector_index(self):
        """更新向量索引"""
        if not self.knowledge_base:
            self.vectors = None
            return
        
        # 获取所有内容
        contents = [knowledge["content"] for knowledge in self.knowledge_base.values()]
        
        # 向量化
        self.vectors = self.vectorizer.fit_transform(contents)
        
        # 更新索引
        self.vector_index = {i: knowledge_id for i, knowledge_id in enumerate(self.knowledge_base.keys())}
    
    def _update_search_time(self, search_time: float):
        """更新搜索时间"""
        total_time = self.metrics["average_search_time"] * (self.metrics["total_searches"] - 1)
        self.metrics["average_search_time"] = (total_time + search_time) / self.metrics["total_searches"]
    
    def save(self, filepath: str):
        """保存知识库"""
        data = {
            "knowledge_base": self.knowledge_base,
            "vectorizer": self.vectorizer,
            "vectors": self.vectors,
            "metrics": self.metrics
        }
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
    
    def load(self, filepath: str):
        """加载知识库"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        self.knowledge_base = data["knowledge_base"]
        self.vectorizer = data["vectorizer"]
        self.vectors = data["vectors"]
        self.metrics = data["metrics"]
        self.vector_index = {i: knowledge_id for i, knowledge_id in enumerate(self.knowledge_base.keys())}

# 使用示例
if __name__ == "__main__":
    manager = RAGKnowledgeManager()
    
    # 添加知识
    manager.add_knowledge("1", "Python性能优化技巧：使用NumPy、Pandas等库", {"category": "programming"})
    manager.add_knowledge("2", "NumPy数组操作指南：创建、索引、切片", {"category": "library"})
    manager.add_knowledge("3", "Pandas数据分析：DataFrame操作", {"category": "library"})
    
    # 搜索
    results = manager.search("Python performance optimization")
    print("搜索结果:")
    for result in results:
        print(f"  - {result['id']}: {result['content'][:50]}... (分数: {result['score']:.3f})")
    
    # 获取指标
    metrics = manager.get_metrics()
    print(f"\n指标: {metrics}")
