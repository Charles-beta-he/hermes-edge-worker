#!/usr/bin/env python3
"""
统一管理器
整合所有组件的统一管理
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

class UnifiedManager:
    """统一管理器"""
    
    def __init__(self):
        self.components = {}
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0
        }
    
    def register_component(self, name: str, component):
        """注册组件"""
        self.components[name] = component
        print(f"Component registered: {name}")
    
    def get_component(self, name: str):
        """获取组件"""
        return self.components.get(name)
    
    def list_components(self) -> List[str]:
        """列出组件"""
        return list(self.components.keys())
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        status = {
            "system": "unified_manager",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        for name, component in self.components.items():
            if hasattr(component, 'get_metrics'):
                status["components"][name] = {
                    "status": "active",
                    "metrics": component.get_metrics()
                }
            else:
                status["components"][name] = {
                    "status": "active"
                }
        
        return status
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics
    
    def update_metrics(self, success: bool, response_time: float):
        """更新指标"""
        self.metrics["total_requests"] += 1
        
        if success:
            self.metrics["successful_requests"] += 1
        else:
            self.metrics["failed_requests"] += 1
        
        # 更新平均响应时间
        total_time = self.metrics["average_response_time"] * (self.metrics["total_requests"] - 1)
        self.metrics["average_response_time"] = (total_time + response_time) / self.metrics["total_requests"]

class TaskSchedulerComponent:
    """任务调度器组件"""
    
    def __init__(self):
        self.tasks = {}
        self.metrics = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0
        }
    
    def create_task(self, task_type: str, params: Dict[str, Any], priority: int = 2) -> str:
        """创建任务"""
        import uuid
        task_id = str(uuid.uuid4())
        
        self.tasks[task_id] = {
            "id": task_id,
            "type": task_type,
            "params": params,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        self.metrics["total_tasks"] += 1
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        """列出任务"""
        return list(self.tasks.values())
    
    def execute_task(self, task_id: str, experience: Optional[Dict] = None) -> Dict[str, Any]:
        """执行任务"""
        task = self.tasks.get(task_id)
        if not task:
            return {"error": "Task not found"}
        
        # 模拟执行
        result = {
            "task_id": task_id,
            "status": "completed",
            "result": f"Executed {task['type']}",
            "experience_applied": experience is not None,
            "timestamp": datetime.now().isoformat()
        }
        
        task["status"] = "completed"
        self.metrics["completed_tasks"] += 1
        
        return result
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics

class KnowledgeManagerComponent:
    """知识管理器组件"""
    
    def __init__(self):
        self.knowledge_base = {}
        self.metrics = {
            "total_knowledge": 0,
            "total_searches": 0
        }
    
    def add_knowledge(self, knowledge_id: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """添加知识"""
        self.knowledge_base[knowledge_id] = {
            "id": knowledge_id,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }
        self.metrics["total_knowledge"] += 1
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索知识"""
        self.metrics["total_searches"] += 1
        
        # 简单搜索实现
        results = []
        for knowledge in self.knowledge_base.values():
            if query.lower() in knowledge["content"].lower():
                results.append({
                    "id": knowledge["id"],
                    "content": knowledge["content"],
                    "metadata": knowledge["metadata"],
                    "score": 1.0
                })
        
        return results[:top_k]
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics

class ExperienceRatchetComponent:
    """经验积累器组件"""
    
    def __init__(self):
        self.experiences = {}
        self.metrics = {
            "total_experiences": 0,
            "validated_experiences": 0
        }
    
    def create_experience(self, data: Dict[str, Any]) -> str:
        """创建经验"""
        import uuid
        experience_id = str(uuid.uuid4())
        
        self.experiences[experience_id] = {
            "id": experience_id,
            "project": data.get("project", ""),
            "claim": data.get("claim", ""),
            "pattern_type": data.get("pattern_type", ""),
            "status": "captured",
            "created_at": datetime.now().isoformat()
        }
        
        self.metrics["total_experiences"] += 1
        return experience_id
    
    def query_experience(self, project: str, task_type: str) -> Optional[Dict[str, Any]]:
        """查询经验"""
        for experience in self.experiences.values():
            if (experience["project"] == project and 
                experience["status"] in ["validated", "promoted"]):
                return experience
        return None
    
    def search_experience(self, query: str, project: Optional[str] = None) -> List[Dict[str, Any]]:
        """搜索经验"""
        results = []
        for experience in self.experiences.values():
            if query.lower() in experience["claim"].lower():
                if project is None or experience["project"] == project:
                    results.append(experience)
        return results
    
    def list_experience(self, project: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出经验"""
        results = []
        for experience in self.experiences.values():
            if project and experience["project"] != project:
                continue
            if status and experience["status"] != status:
                continue
            results.append(experience)
        return results
    
    def validate_experience(self, experience_id: str, evidence: str) -> bool:
        """验证经验"""
        if experience_id in self.experiences:
            self.experiences[experience_id]["status"] = "validated"
            self.experiences[experience_id]["evidence"] = evidence
            self.metrics["validated_experiences"] += 1
            return True
        return False
    
    def record_experience(self, task_id: str, result: Dict[str, Any]):
        """记录经验"""
        # 简单实现：创建一个经验记录
        self.create_experience({
            "project": "auto-recorded",
            "claim": f"Task {task_id} execution result",
            "pattern_type": "execution"
        })
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics

class RAGEngineComponent:
    """RAG引擎组件"""
    
    def __init__(self):
        self.knowledge_base = {}
        self.metrics = {
            "total_searches": 0,
            "average_search_time": 0.0
        }
    
    def add_knowledge(self, knowledge_id: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """添加知识"""
        self.knowledge_base[knowledge_id] = {
            "id": knowledge_id,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索知识"""
        import time
        start_time = time.time()
        
        self.metrics["total_searches"] += 1
        
        # 简单搜索实现
        results = []
        for knowledge in self.knowledge_base.values():
            if query.lower() in knowledge["content"].lower():
                results.append({
                    "id": knowledge["id"],
                    "content": knowledge["content"],
                    "metadata": knowledge["metadata"],
                    "score": 1.0
                })
        
        # 更新搜索时间
        search_time = time.time() - start_time
        total_time = self.metrics["average_search_time"] * (self.metrics["total_searches"] - 1)
        self.metrics["average_search_time"] = (total_time + search_time) / self.metrics["total_searches"]
        
        return results[:top_k]
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics

# 使用示例
if __name__ == "__main__":
    # 创建统一管理器
    manager = UnifiedManager()
    
    # 注册组件
    manager.register_component("task_scheduler", TaskSchedulerComponent())
    manager.register_component("knowledge_manager", KnowledgeManagerComponent())
    manager.register_component("experience_ratchet", ExperienceRatchetComponent())
    manager.register_component("rag_engine", RAGEngineComponent())
    
    # 获取状态
    status = manager.get_status()
    print(json.dumps(status, indent=2))
