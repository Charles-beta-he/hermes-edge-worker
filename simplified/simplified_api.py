#!/usr/bin/env python3
"""
简化API
统一接口
"""

import json
from typing import Dict, Any, List
from datetime import datetime

class SimplifiedAPI:
    """简化API"""
    
    def __init__(self, data_layer, event_bus, knowledge_manager, rag_manager):
        self.data_layer = data_layer
        self.event_bus = event_bus
        self.knowledge_manager = knowledge_manager
        self.rag_manager = rag_manager
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索知识"""
        results = []
        
        # 搜索RAG
        if self.rag_manager:
            rag_results = self.rag_manager.search(query, top_k)
            results.extend(rag_results)
        
        # 搜索知识管理器
        if self.knowledge_manager:
            knowledge_results = self.knowledge_manager.search_experience(query, top_k)
            results.extend(knowledge_results)
        
        return results[:top_k]
    
    def add_knowledge(self, knowledge_id: str, content: str, metadata: Dict[str, Any] = None):
        """添加知识"""
        # 添加到RAG
        if self.rag_manager:
            self.rag_manager.add_knowledge(knowledge_id, content, metadata)
        
        # 添加到数据层
        if self.data_layer:
            self.data_layer.store("knowledge", knowledge_id, {
                "content": content,
                "metadata": metadata or {}
            })
        
        # 发布事件
        if self.event_bus:
            self.event_bus.publish("knowledge.added", {
                "knowledge_id": knowledge_id,
                "content": content
            })
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        metrics = {}
        
        if self.data_layer:
            metrics["data_layer"] = self.data_layer.get_metrics()
        if self.event_bus:
            metrics["event_bus"] = self.event_bus.get_metrics()
        if self.rag_manager:
            metrics["rag_manager"] = self.rag_manager.get_metrics()
        
        return metrics
