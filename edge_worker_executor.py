#!/usr/bin/env python3
"""
Edge Worker执行器
只负责任务执行，不负责状态管理
"""

import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime

class EdgeWorkerExecutor:
    """Edge Worker执行器"""
    
    def __init__(self, brain_url: str, worker_id: str):
        self.brain_url = brain_url
        self.worker_id = worker_id
        self.current_tasks = {}
        self.metrics = {
            "tasks_executed": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_execution_time": 0.0
        }
    
    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """执行任务"""
        start_time = datetime.now()
        
        try:
            # 从本地大脑获取任务
            task = self._fetch_task(task_id)
            if not task:
                return {"success": False, "error": "Task not found"}
            
            # 执行任务
            result = self._execute(task)
            
            # 返回结果到本地大脑
            self._report_result(task_id, result, "completed")
            
            # 更新指标
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(execution_time, True)
            
            return {"success": True, "result": result}
            
        except Exception as e:
            # 报告失败
            self._report_result(task_id, {"error": str(e)}, "failed")
            
            # 更新指标
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(execution_time, False)
            
            return {"success": False, "error": str(e)}
    
    def _fetch_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """从本地大脑获取任务"""
        try:
            response = requests.get(f"{self.brain_url}/tasks/{task_id}")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Failed to fetch task: {e}")
        
        return None
    
    def _execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        task_type = task.get("type")
        params = task.get("params", {})
        
        # 根据任务类型执行
        if task_type == "code_generation":
            return self._execute_code_generation(params)
        elif task_type == "code_review":
            return self._execute_code_review(params)
        elif task_type == "testing":
            return self._execute_testing(params)
        elif task_type == "documentation":
            return self._execute_documentation(params)
        else:
            return {"error": f"Unknown task type: {task_type}"}
    
    def _execute_code_generation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行代码生成任务"""
        # 这里应该调用实际的代码生成API
        return {
            "output": "Generated code",
            "file": params.get("file", "unknown"),
            "timestamp": datetime.now().isoformat()
        }
    
    def _execute_code_review(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行代码审查任务"""
        # 这里应该调用实际的代码审查API
        return {
            "output": "Code review completed",
            "file": params.get("file", "unknown"),
            "suggestions": ["Suggestion 1", "Suggestion 2"],
            "timestamp": datetime.now().isoformat()
        }
    
    def _execute_testing(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行测试任务"""
        # 这里应该调用实际的测试API
        return {
            "output": "Tests executed",
            "file": params.get("file", "unknown"),
            "passed": 10,
            "failed": 0,
            "timestamp": datetime.now().isoformat()
        }
    
    def _execute_documentation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行文档生成任务"""
        # 这里应该调用实际的文档生成API
        return {
            "output": "Documentation generated",
            "file": params.get("file", "unknown"),
            "timestamp": datetime.now().isoformat()
        }
    
    def _report_result(self, task_id: str, result: Dict[str, Any], status: str):
        """报告结果到本地大脑"""
        try:
            data = {
                "task_id": task_id,
                "worker_id": self.worker_id,
                "result": result,
                "status": status,
                "timestamp": datetime.now().isoformat()
            }
            requests.post(f"{self.brain_url}/tasks/{task_id}/result", json=data)
        except Exception as e:
            print(f"Failed to report result: {e}")
    
    def _update_metrics(self, execution_time: float, success: bool):
        """更新指标"""
        self.metrics["tasks_executed"] += 1
        
        if success:
            self.metrics["tasks_completed"] += 1
        else:
            self.metrics["tasks_failed"] += 1
        
        # 更新平均执行时间
        total_time = self.metrics["average_execution_time"] * (self.metrics["tasks_executed"] - 1)
        self.metrics["average_execution_time"] = (total_time + execution_time) / self.metrics["tasks_executed"]
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics

# 使用示例
if __name__ == "__main__":
    # 创建执行器
    executor = EdgeWorkerExecutor("http://192.168.31.71:9001", "worker-1")
    
    # 执行任务
    result = executor.execute_task("task-001")
    print(result)
    
    # 获取指标
    metrics = executor.get_metrics()
    print(metrics)
