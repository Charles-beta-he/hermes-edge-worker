#!/usr/bin/env python3
"""
统一任务池适配器
唯一事实源原则：本地大脑作为唯一事实源
"""

import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class UnifiedTaskPool:
    """统一任务池适配器"""
    
    def __init__(self, brain_orchestrator=None):
        self.brain_orchestrator = brain_orchestrator
        self.edge_workers = {}
        self.task_assignments = {}
        self.metrics = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "pending_tasks": 0
        }
    
    def add_task(self, task_type: str, params: Dict[str, Any], 
                 priority: TaskPriority = TaskPriority.MEDIUM) -> str:
        """添加任务到统一池"""
        task_id = str(uuid.uuid4())
        
        # 使用本地大脑作为唯一事实源
        if self.brain_orchestrator:
            # 调用本地大脑的任务创建API
            task_data = {
                "id": task_id,
                "type": task_type,
                "params": params,
                "priority": priority.value,
                "status": TaskStatus.PENDING.value,
                "created_at": datetime.now().isoformat()
            }
            self.brain_orchestrator.create_task(task_data)
        
        # 分配给Edge Worker执行
        worker = self._select_worker(task_type)
        if worker:
            self._assign_to_worker(task_id, worker)
        
        self.metrics["total_tasks"] += 1
        self.metrics["pending_tasks"] += 1
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务"""
        # 优先从本地大脑获取
        if self.brain_orchestrator:
            task = self.brain_orchestrator.get_task(task_id)
            if task:
                return task
        
        # 从Edge Worker获取
        for worker_id, worker in self.edge_workers.items():
            task = worker.get_task(task_id)
            if task:
                return task
        
        return None
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          result: Optional[Dict[str, Any]] = None):
        """更新任务状态"""
        # 更新本地大脑
        if self.brain_orchestrator:
            self.brain_orchestrator.update_task_status(task_id, status.value, result)
        
        # 更新Edge Worker
        if task_id in self.task_assignments:
            worker_id = self.task_assignments[task_id]
            if worker_id in self.edge_workers:
                self.edge_workers[worker_id].update_task_status(task_id, status.value, result)
        
        # 更新指标
        if status == TaskStatus.COMPLETED:
            self.metrics["completed_tasks"] += 1
            self.metrics["pending_tasks"] -= 1
        elif status == TaskStatus.FAILED:
            self.metrics["failed_tasks"] += 1
            self.metrics["pending_tasks"] -= 1
    
    def register_edge_worker(self, worker_id: str, worker):
        """注册Edge Worker"""
        self.edge_workers[worker_id] = worker
    
    def _select_worker(self, task_type: str) -> Optional[str]:
        """选择Edge Worker"""
        if not self.edge_workers:
            return None
        
        # 简单轮询选择
        workers = list(self.edge_workers.keys())
        return workers[0] if workers else None
    
    def _assign_to_worker(self, task_id: str, worker_id: str):
        """分配任务给Edge Worker"""
        self.task_assignments[task_id] = worker_id
        
        if worker_id in self.edge_workers:
            self.edge_workers[worker_id].assign_task(task_id)
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics
    
    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Dict[str, Any]]:
        """列出任务"""
        # 从本地大脑获取
        if self.brain_orchestrator:
            tasks = self.brain_orchestrator.list_tasks()
            if status:
                tasks = [t for t in tasks if t.get("status") == status.value]
            return tasks
        
        return []

# 使用示例
if __name__ == "__main__":
    # 创建统一任务池
    pool = UnifiedTaskPool()
    
    # 添加任务
    task_id = pool.add_task("code_generation", {"file": "main.py"}, TaskPriority.HIGH)
    
    # 获取任务
    task = pool.get_task(task_id)
    print(task)
    
    # 获取指标
    metrics = pool.get_metrics()
    print(metrics)
