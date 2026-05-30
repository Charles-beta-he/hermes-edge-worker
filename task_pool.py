#!/usr/bin/env python3
"""
Legacy in-memory task pool.

生产 SSOT 不是本文件。生产任务状态、生命周期、proof gates 必须以
Hermes Local Brain / brain_task_orchestrator.py 为唯一事实源。

本模块只保留为：
- 单元测试夹具
- 早期 Agent Team 原型兼容
- 本地内存算法实验

禁止在生产链路中把这里的 COMPLETED/FAILED 当作最终任务生命周期状态。
"""

import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
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

class TaskPool:
    def __init__(self):
        self.tasks = {}  # 任务队列
        self.results = {}  # 结果存储
        self.queue = []  # 优先级队列
        self.workers = {}  # 工作节点
        self.metrics = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "average_execution_time": 0
        }
    
    def add_task(self, task_type: str, params: Dict[str, Any], 
                 priority: TaskPriority = TaskPriority.MEDIUM) -> str:
        """添加任务到池"""
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "type": task_type,
            "params": params,
            "status": TaskStatus.PENDING.value,
            "priority": priority.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "assigned_worker": None,
            "retry_count": 0,
            "max_retries": 3
        }
        self.tasks[task_id] = task
        self.queue.append((priority.value, task_id))
        self.queue.sort(reverse=True)  # 高优先级在前
        self.metrics["total_tasks"] += 1
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """获取下一个待执行任务"""
        for priority, task_id in self.queue:
            task = self.tasks[task_id]
            if task["status"] == TaskStatus.PENDING.value:
                return task
        return None
    
    def assign_task(self, task_id: str, worker_id: str) -> bool:
        """分配任务给工作节点"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        if task["status"] != TaskStatus.PENDING.value:
            return False
        
        task["status"] = TaskStatus.RUNNING.value
        task["assigned_worker"] = worker_id
        task["started_at"] = datetime.now().isoformat()
        task["updated_at"] = datetime.now().isoformat()
        
        # 从队列中移除
        self.queue = [(p, t) for p, t in self.queue if t != task_id]
        
        return True
    
    def complete_task(self, task_id: str, result: Dict[str, Any]) -> bool:
        """完成任务"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task["status"] = TaskStatus.COMPLETED.value
        task["completed_at"] = datetime.now().isoformat()
        task["updated_at"] = datetime.now().isoformat()
        
        # 存储结果
        self.results[task_id] = {
            "task_id": task_id,
            "result": result,
            "stored_at": datetime.now().isoformat()
        }
        
        # 更新指标
        self.metrics["completed_tasks"] += 1
        self._update_average_execution_time(task)
        
        return True
    
    def fail_task(self, task_id: str, error: str) -> bool:
        """任务失败"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task["retry_count"] += 1
        
        if task["retry_count"] < task["max_retries"]:
            # 重试
            task["status"] = TaskStatus.PENDING.value
            task["assigned_worker"] = None
            task["updated_at"] = datetime.now().isoformat()
            self.queue.append((task["priority"], task_id))
            self.queue.sort(reverse=True)
        else:
            # 失败
            task["status"] = TaskStatus.FAILED.value
            task["updated_at"] = datetime.now().isoformat()
            self.metrics["failed_tasks"] += 1
        
        return True
    
    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        return self.results.get(task_id)
    
    def list_tasks(self, status: Optional[TaskStatus] = None, 
                   task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出任务"""
        tasks = list(self.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t["status"] == status.value]
        
        if task_type:
            tasks = [t for t in tasks if t["type"] == task_type]
        
        return tasks
    
    def register_worker(self, worker_id: str, capabilities: List[str]):
        """注册工作节点"""
        self.workers[worker_id] = {
            "id": worker_id,
            "capabilities": capabilities,
            "status": "online",
            "current_task": None,
            "registered_at": datetime.now().isoformat()
        }
    
    def get_worker(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """获取工作节点"""
        return self.workers.get(worker_id)
    
    def list_workers(self) -> List[Dict[str, Any]]:
        """列出工作节点"""
        return list(self.workers.values())
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics
    
    def _update_average_execution_time(self, task: Dict[str, Any]):
        """更新平均执行时间"""
        if task["started_at"] and task["completed_at"]:
            start = datetime.fromisoformat(task["started_at"])
            end = datetime.fromisoformat(task["completed_at"])
            execution_time = (end - start).total_seconds()
            
            total_time = self.metrics["average_execution_time"] * (self.metrics["completed_tasks"] - 1)
            self.metrics["average_execution_time"] = (total_time + execution_time) / self.metrics["completed_tasks"]

# 使用示例
if __name__ == "__main__":
    pool = TaskPool()
    
    # 注册工作节点
    pool.register_worker("worker-1", ["code_generation", "code_review"])
    pool.register_worker("worker-2", ["testing", "documentation"])
    
    # 添加任务
    task_id = pool.add_task("code_generation", {"file": "main.py"}, TaskPriority.HIGH)
    
    # 分配任务
    pool.assign_task(task_id, "worker-1")
    
    # 完成任务
    pool.complete_task(task_id, {"output": "Generated code"})
    
    # 获取结果
    result = pool.get_result(task_id)
    print(result)
