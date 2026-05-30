#!/usr/bin/env python3
"""
树状KV缓存
Agent Team多节点落地核心组件
"""

import json
import time
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta

class TreeCache:
    def __init__(self, default_ttl: int = 3600):
        self.root = {}
        self.ttl = {}  # 过期时间
        self.default_ttl = default_ttl
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
    
    def set(self, path: str, value: Any, ttl: Optional[int] = None):
        """设置值（支持路径）"""
        keys = path.split("/")
        node = self.root
        
        # 创建路径
        for key in keys[:-1]:
            if key not in node:
                node[key] = {}
            node = node[key]
        
        # 设置值
        node[keys[-1]] = value
        
        # 设置TTL
        if ttl:
            self.ttl[path] = datetime.now() + timedelta(seconds=ttl)
        elif self.default_ttl:
            self.ttl[path] = datetime.now() + timedelta(seconds=self.default_ttl)
        
        self.metrics["sets"] += 1
    
    def get(self, path: str) -> Optional[Any]:
        """获取值（支持路径）"""
        # 检查是否过期
        if self._is_expired(path):
            self.delete(path)
            self.metrics["misses"] += 1
            return None
        
        keys = path.split("/")
        node = self.root
        
        # 遍历路径
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                self.metrics["misses"] += 1
                return None
            node = node[key]
        
        self.metrics["hits"] += 1
        return node
    
    def delete(self, path: str):
        """删除值"""
        keys = path.split("/")
        node = self.root
        
        # 遍历到父节点
        for key in keys[:-1]:
            if not isinstance(node, dict) or key not in node:
                return
            node = node[key]
        
        # 删除值
        if isinstance(node, dict) and keys[-1] in node:
            del node[keys[-1]]
            self.metrics["deletes"] += 1
        
        # 删除TTL
        if path in self.ttl:
            del self.ttl[path]
    
    def exists(self, path: str) -> bool:
        """检查路径是否存在"""
        return self.get(path) is not None
    
    def list_paths(self, prefix: str = "") -> List[str]:
        """列出路径"""
        result = []
        node = self.root
        
        if prefix:
            keys = prefix.split("/")
            for key in keys:
                if not isinstance(node, dict) or key not in node:
                    return []
                node = node[key]
        
        # 递归收集路径
        self._collect_paths(node, prefix, result)
        return result
    
    def _collect_paths(self, node: Any, prefix: str, result: List[str]):
        """递归收集路径"""
        if isinstance(node, dict):
            for key, value in node.items():
                path = f"{prefix}/{key}" if prefix else key
                result.append(path)
                self._collect_paths(value, path, result)
    
    def _is_expired(self, path: str) -> bool:
        """检查是否过期"""
        if path not in self.ttl:
            return False
        return datetime.now() > self.ttl[path]
    
    def cleanup_expired(self):
        """清理过期的缓存"""
        expired_paths = []
        for path, expiry in self.ttl.items():
            if datetime.now() > expiry:
                expired_paths.append(path)
        
        for path in expired_paths:
            self.delete(path)
        
        return len(expired_paths)
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        total_requests = self.metrics["hits"] + self.metrics["misses"]
        hit_rate = self.metrics["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            **self.metrics,
            "total_requests": total_requests,
            "hit_rate": hit_rate
        }
    
    def clear(self):
        """清空缓存"""
        self.root = {}
        self.ttl = {}
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }

# 使用示例
if __name__ == "__main__":
    cache = TreeCache(default_ttl=3600)
    
    # 设置值
    cache.set("users/user1/name", "Alice")
    cache.set("users/user1/email", "alice@example.com")
    cache.set("users/user2/name", "Bob")
    
    # 获取值
    print(cache.get("users/user1/name"))  # Alice
    print(cache.get("users/user2/name"))  # Bob
    
    # 列出路径
    print(cache.list_paths("users"))  # ['users/user1/name', 'users/user1/email', 'users/user2/name']
    
    # 获取指标
    print(cache.get_metrics())
