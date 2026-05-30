#!/usr/bin/env python3
"""
知识管理系统
本地大脑的知识层
"""

import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

class KnowledgeType(Enum):
    EXPERIENCE = "experience"  # 经验
    FUNCTION = "function"  # 功能
    WORKFLOW = "workflow"  # 流程
    DECISION = "decision"  # 决策

class Knowledge:
    """知识实体"""
    
    def __init__(self, knowledge_type: KnowledgeType, title: str, content: str, 
                 tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None):
        self.id = str(uuid.uuid4())
        self.type = knowledge_type
        self.title = title
        self.content = content
        self.tags = tags or []
        self.metadata = metadata or {}
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.access_count = 0
        self.relevance_score = 0.0

class KnowledgeManager:
    """知识管理器"""
    
    def __init__(self):
        self.knowledge_base = {}  # 知识库
        self.search_index = {}  # 搜索索引
        self.access_log = []  # 访问日志
        self.metrics = {
            "total_knowledge": 0,
            "total_searches": 0,
            "total_accesses": 0,
            "average_relevance": 0.0
        }
    
    def record_experience(self, experience: Dict[str, Any]) -> str:
        """记录经验"""
        knowledge = Knowledge(
            knowledge_type=KnowledgeType.EXPERIENCE,
            title=experience.get("title", ""),
            content=experience.get("content", ""),
            tags=experience.get("tags", []),
            metadata=experience.get("metadata", {})
        )
        
        # 存储知识
        self.knowledge_base[knowledge.id] = knowledge
        
        # 更新索引
        self._update_index(knowledge)
        
        # 更新指标
        self.metrics["total_knowledge"] += 1
        
        return knowledge.id
    
    def record_function(self, function: Dict[str, Any]) -> str:
        """记录功能"""
        knowledge = Knowledge(
            knowledge_type=KnowledgeType.FUNCTION,
            title=function.get("title", ""),
            content=function.get("content", ""),
            tags=function.get("tags", []),
            metadata=function.get("metadata", {})
        )
        
        # 存储知识
        self.knowledge_base[knowledge.id] = knowledge
        
        # 更新索引
        self._update_index(knowledge)
        
        # 更新指标
        self.metrics["total_knowledge"] += 1
        
        return knowledge.id
    
    def record_workflow(self, workflow: Dict[str, Any]) -> str:
        """记录流程"""
        knowledge = Knowledge(
            knowledge_type=KnowledgeType.WORKFLOW,
            title=workflow.get("title", ""),
            content=workflow.get("content", ""),
            tags=workflow.get("tags", []),
            metadata=workflow.get("metadata", {})
        )
        
        # 存储知识
        self.knowledge_base[knowledge.id] = knowledge
        
        # 更新索引
        self._update_index(knowledge)
        
        # 更新指标
        self.metrics["total_knowledge"] += 1
        
        return knowledge.id
    
    def record_decision(self, decision: Dict[str, Any]) -> str:
        """记录决策"""
        knowledge = Knowledge(
            knowledge_type=KnowledgeType.DECISION,
            title=decision.get("title", ""),
            content=decision.get("content", ""),
            tags=decision.get("tags", []),
            metadata=decision.get("metadata", {})
        )
        
        # 存储知识
        self.knowledge_base[knowledge.id] = knowledge
        
        # 更新索引
        self._update_index(knowledge)
        
        # 更新指标
        self.metrics["total_knowledge"] += 1
        
        return knowledge.id
    
    def search_experience(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索经验"""
        # 更新指标
        self.metrics["total_searches"] += 1
        
        # 搜索知识
        results = self._search(query, KnowledgeType.EXPERIENCE, top_k)
        
        # 记录访问日志
        self._log_access("search", query, len(results))
        
        return results
    
    def search_function(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索功能"""
        # 更新指标
        self.metrics["total_searches"] += 1
        
        # 搜索知识
        results = self._search(query, KnowledgeType.FUNCTION, top_k)
        
        # 记录访问日志
        self._log_access("search", query, len(results))
        
        return results
    
    def search_workflow(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索流程"""
        # 更新指标
        self.metrics["total_searches"] += 1
        
        # 搜索知识
        results = self._search(query, KnowledgeType.WORKFLOW, top_k)
        
        # 记录访问日志
        self._log_access("search", query, len(results))
        
        return results
    
    def search_decision(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索决策"""
        # 更新指标
        self.metrics["total_searches"] += 1
        
        # 搜索知识
        results = self._search(query, KnowledgeType.DECISION, top_k)
        
        # 记录访问日志
        self._log_access("search", query, len(results))
        
        return results
    
    def search_all(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """搜索所有知识"""
        # 更新指标
        self.metrics["total_searches"] += 1
        
        # 搜索知识
        results = self._search(query, None, top_k)
        
        # 记录访问日志
        self._log_access("search", query, len(results))
        
        return results
    
    def get_knowledge(self, knowledge_id: str) -> Optional[Dict[str, Any]]:
        """获取知识"""
        knowledge = self.knowledge_base.get(knowledge_id)
        
        if knowledge:
            # 更新访问次数
            knowledge.access_count += 1
            
            # 更新指标
            self.metrics["total_accesses"] += 1
            
            # 记录访问日志
            self._log_access("get", knowledge_id, 1)
            
            return {
                "id": knowledge.id,
                "type": knowledge.type.value,
                "title": knowledge.title,
                "content": knowledge.content,
                "tags": knowledge.tags,
                "metadata": knowledge.metadata,
                "created_at": knowledge.created_at,
                "updated_at": knowledge.updated_at,
                "access_count": knowledge.access_count,
                "relevance_score": knowledge.relevance_score
            }
        
        return None
    
    def recommend_knowledge(self, context: Dict[str, Any], top_k: int = 5) -> List[Dict[str, Any]]:
        """推荐知识"""
        # 基于上下文推荐
        results = self._context_based_recommendation(context, top_k)
        
        # 记录访问日志
        self._log_access("recommend", str(context), len(results))
        
        return results
    
    def list_knowledge(self, knowledge_type: Optional[KnowledgeType] = None, 
                       tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """列出知识"""
        results = []
        
        for knowledge in self.knowledge_base.values():
            # 类型过滤
            if knowledge_type and knowledge.type != knowledge_type:
                continue
            
            # 标签过滤
            if tags and not any(tag in knowledge.tags for tag in tags):
                continue
            
            results.append({
                "id": knowledge.id,
                "type": knowledge.type.value,
                "title": knowledge.title,
                "tags": knowledge.tags,
                "created_at": knowledge.created_at,
                "access_count": knowledge.access_count
            })
        
        return results
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics
    
    def _update_index(self, knowledge: Knowledge):
        """更新索引"""
        # 关键词索引
        keywords = self._extract_keywords(knowledge.title + " " + knowledge.content)
        for keyword in keywords:
            if keyword not in self.search_index:
                self.search_index[keyword] = []
            self.search_index[keyword].append(knowledge.id)
        
        # 标签索引
        for tag in knowledge.tags:
            if tag not in self.search_index:
                self.search_index[tag] = []
            self.search_index[tag].append(knowledge.id)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        import re
        
        # 英文单词
        english_words = re.findall(r'[a-zA-Z]+', text.lower())
        
        # 中文字符（每个字符作为一个词）
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        
        # 合并
        keywords = english_words + chinese_chars
        
        return keywords
    
    def _search(self, query: str, knowledge_type: Optional[KnowledgeType], 
                top_k: int) -> List[Dict[str, Any]]:
        """搜索知识"""
        keywords = self._extract_keywords(query)
        results = []
        
        for knowledge in self.knowledge_base.values():
            # 类型过滤
            if knowledge_type and knowledge.type != knowledge_type:
                continue
            
            # 计算相关性分数
            score = self._calculate_relevance(knowledge, keywords)
            
            if score > 0:
                results.append({
                    "id": knowledge.id,
                    "type": knowledge.type.value,
                    "title": knowledge.title,
                    "content": knowledge.content[:200] + "..." if len(knowledge.content) > 200 else knowledge.content,
                    "tags": knowledge.tags,
                    "score": score,
                    "created_at": knowledge.created_at,
                    "access_count": knowledge.access_count
                })
        
        # 按分数排序
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results[:top_k]
    
    def _calculate_relevance(self, knowledge: Knowledge, keywords: List[str]) -> float:
        """计算相关性分数"""
        score = 0.0
        
        # 标题匹配
        title_keywords = self._extract_keywords(knowledge.title)
        for keyword in keywords:
            if keyword in title_keywords:
                score += 2.0
        
        # 内容匹配
        content_keywords = self._extract_keywords(knowledge.content)
        for keyword in keywords:
            if keyword in content_keywords:
                score += 1.0
        
        # 标签匹配
        for keyword in keywords:
            if keyword in knowledge.tags:
                score += 3.0
        
        # 访问次数加权
        score += knowledge.access_count * 0.1
        
        return score
    
    def _context_based_recommendation(self, context: Dict[str, Any], 
                                      top_k: int) -> List[Dict[str, Any]]:
        """基于上下文的推荐"""
        # 提取上下文关键词
        context_text = " ".join([str(v) for v in context.values()])
        keywords = self._extract_keywords(context_text)
        
        # 搜索相关知识
        results = []
        for knowledge in self.knowledge_base.values():
            score = self._calculate_relevance(knowledge, keywords)
            if score > 0:
                results.append({
                    "id": knowledge.id,
                    "type": knowledge.type.value,
                    "title": knowledge.title,
                    "content": knowledge.content[:200] + "..." if len(knowledge.content) > 200 else knowledge.content,
                    "tags": knowledge.tags,
                    "score": score,
                    "created_at": knowledge.created_at,
                    "access_count": knowledge.access_count
                })
        
        # 按分数排序
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results[:top_k]
    
    def _log_access(self, action: str, query: str, results_count: int):
        """记录访问日志"""
        self.access_log.append({
            "action": action,
            "query": query,
            "results_count": results_count,
            "timestamp": datetime.now().isoformat()
        })

# 使用示例
if __name__ == "__main__":
    manager = KnowledgeManager()
    
    # 记录经验
    experience_id = manager.record_experience({
        "title": "如何优化Python性能",
        "content": "使用NumPy、Pandas等库可以显著提高性能...",
        "tags": ["python", "performance", "optimization"],
        "metadata": {"difficulty": "medium", "category": "programming"}
    })
    
    # 搜索经验
    results = manager.search_experience("Python performance")
    print(results)
    
    # 获取指标
    metrics = manager.get_metrics()
    print(metrics)
