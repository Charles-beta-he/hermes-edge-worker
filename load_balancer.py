#!/usr/bin/env python3
"""
负载均衡器
基于一致性哈希算法
"""

import hashlib
from typing import List, Dict, Any

class ConsistentHashRing:
    def __init__(self, nodes: List[str], virtual_nodes: int = 100):
        self.ring = {}
        self.sorted_keys = []
        
        for node in nodes:
            for i in range(virtual_nodes):
                key = self.hash(f"{node}:{i}")
                self.ring[key] = node
                self.sorted_keys.append(key)
        
        self.sorted_keys.sort()
    
    def hash(self, key: str) -> int:
        """计算哈希值"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)
    
    def get_node(self, key: str) -> str:
        """获取节点"""
        if not self.ring:
            return ""
        
        hash_key = self.hash(key)
        
        # 二分查找
        left, right = 0, len(self.sorted_keys) - 1
        while left < right:
            mid = (left + right) // 2
            if self.sorted_keys[mid] < hash_key:
                left = mid + 1
            else:
                right = mid
        
        return self.ring[self.sorted_keys[left]]

class LoadBalancer:
    def __init__(self, nodes: List[str]):
        self.ring = ConsistentHashRing(nodes)
    
    def get_node(self, key: str) -> str:
        """获取节点"""
        return self.ring.get_node(key)

# 使用示例
if __name__ == "__main__":
    nodes = ["192.168.31.130:9002", "192.168.31.131:9002", "192.168.31.132:9002"]
    balancer = LoadBalancer(nodes)
    
    task_id = "task-001"
    node = balancer.get_node(task_id)
    print(f"Task {task_id} assigned to {node}")
