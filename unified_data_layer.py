#!/usr/bin/env python3
"""
统一数据层
解决孤岛逻辑：统一数据源
"""

import json
import pickle
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

class UnifiedStorage:
    """统一存储"""
    
    def __init__(self, storage_dir: str = "/tmp/unified_storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.data = {}
        self.metadata = {}
    
    def store(self, entity_type: str, entity_id: str, data: Dict[str, Any]):
        """存储数据"""
        key = f"{entity_type}:{entity_id}"
        self.data[key] = data
        self.metadata[key] = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "stored_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # 持久化存储
        self._persist(key, data)
    
    def retrieve(self, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """检索数据"""
        key = f"{entity_type}:{entity_id}"
        
        # 先查内存
        if key in self.data:
            return self.data[key]
        
        # 再查持久化存储
        data = self._load(key)
        if data:
            self.data[key] = data
            return data
        
        return None
    
    def list_entities(self, entity_type: str) -> List[Dict[str, Any]]:
        """列出实体"""
        results = []
        for key, data in self.data.items():
            if key.startswith(f"{entity_type}:"):
                results.append(data)
        return results
    
    def delete(self, entity_type: str, entity_id: str) -> bool:
        """删除数据"""
        key = f"{entity_type}:{entity_id}"
        
        if key in self.data:
            del self.data[key]
            del self.metadata[key]
            self._delete_persisted(key)
            return True
        
        return False
    
    def _persist(self, key: str, data: Dict[str, Any]):
        """持久化存储"""
        file_path = self.storage_dir / f"{key.replace(':', '_')}.json"
        with open(file_path, 'w') as f:
            json.dump(data, f)
    
    def _load(self, key: str) -> Optional[Dict[str, Any]]:
        """加载数据"""
        file_path = self.storage_dir / f"{key.replace(':', '_')}.json"
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return None
    
    def _delete_persisted(self, key: str):
        """删除持久化数据"""
        file_path = self.storage_dir / f"{key.replace(':', '_')}.json"
        if file_path.exists():
            file_path.unlink()

class UnifiedCache:
    """统一缓存"""
    
    def __init__(self, default_ttl: int = 3600):
        self.cache = {}
        self.default_ttl = default_ttl
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key in self.cache:
            entry = self.cache[key]
            if entry["expires_at"] > datetime.now().timestamp():
                self.metrics["hits"] += 1
                return entry["value"]
            else:
                del self.cache[key]
        
        self.metrics["misses"] += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存"""
        ttl = ttl or self.default_ttl
        self.cache[key] = {
            "value": value,
            "expires_at": datetime.now().timestamp() + ttl,
            "created_at": datetime.now().isoformat()
        }
        self.metrics["sets"] += 1
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self.cache:
            del self.cache[key]
            self.metrics["deletes"] += 1
            return True
        return False
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        total_requests = self.metrics["hits"] + self.metrics["misses"]
        hit_rate = self.metrics["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            **self.metrics,
            "total_requests": total_requests,
            "hit_rate": hit_rate
        }

class UnifiedDataLayer:
    """统一数据层"""
    
    def __init__(self, storage_dir: str = "/tmp/unified_storage"):
        self.storage = UnifiedStorage(storage_dir)
        self.cache = UnifiedCache()
        self.metrics = {
            "total_operations": 0,
            "storage_operations": 0,
            "cache_operations": 0
        }
    
    def store(self, entity_type: str, entity_id: str, data: Dict[str, Any]):
        """存储数据"""
        # 存储到统一存储
        self.storage.store(entity_type, entity_id, data)
        
        # 更新缓存
        cache_key = f"{entity_type}:{entity_id}"
        self.cache.set(cache_key, data)
        
        # 更新指标
        self.metrics["total_operations"] += 1
        self.metrics["storage_operations"] += 1
        self.metrics["cache_operations"] += 1
    
    def retrieve(self, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """检索数据"""
        cache_key = f"{entity_type}:{entity_id}"
        
        # 先查缓存
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # 再查存储
        data = self.storage.retrieve(entity_type, entity_id)
        if data:
            # 更新缓存
            self.cache.set(cache_key, data)
        
        # 更新指标
        self.metrics["total_operations"] += 1
        self.metrics["storage_operations"] += 1
        
        return data
    
    def list_entities(self, entity_type: str) -> List[Dict[str, Any]]:
        """列出实体"""
        return self.storage.list_entities(entity_type)
    
    def delete(self, entity_type: str, entity_id: str) -> bool:
        """删除数据"""
        cache_key = f"{entity_type}:{entity_id}"
        
        # 删除缓存
        self.cache.delete(cache_key)
        
        # 删除存储
        result = self.storage.delete(entity_type, entity_id)
        
        # 更新指标
        self.metrics["total_operations"] += 1
        self.metrics["storage_operations"] += 1
        self.metrics["cache_operations"] += 1
        
        return result
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return {
            "data_layer": self.metrics,
            "storage": {
                "total_entities": len(self.storage.data)
            },
            "cache": self.cache.get_metrics()
        }

# 使用示例
if __name__ == "__main__":
    # 创建统一数据层
    data_layer = UnifiedDataLayer()
    
    # 存储任务
    data_layer.store("task", "task-001", {
        "type": "code_generation",
        "params": {"file": "main.py"},
        "status": "pending"
    })
    
    # 检索任务
    task = data_layer.retrieve("task", "task-001")
    print(f"Task: {task}")
    
    # 存储知识
    data_layer.store("knowledge", "knowledge-001", {
        "content": "Python性能优化技巧",
        "metadata": {"category": "programming"}
    })
    
    # 检索知识
    knowledge = data_layer.retrieve("knowledge", "knowledge-001")
    print(f"Knowledge: {knowledge}")
    
    # 获取指标
    metrics = data_layer.get_metrics()
    print(f"Metrics: {metrics}")
