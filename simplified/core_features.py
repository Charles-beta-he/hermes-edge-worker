#!/usr/bin/env python3
"""
核心功能移植
将废弃组件的核心功能移植到简化架构
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

class AgentRole(Enum):
    """Agent角色"""
    CODE_GENERATOR = "code_generator"
    CODE_REVIEWER = "code_reviewer"
    TEST_RUNNER = "test_runner"
    DOCUMENTATION = "documentation"
    DEPLOYER = "deployer"

class AgentStatus(Enum):
    """Agent状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    IDLE = "idle"

class Agent:
    """Agent实体"""
    
    def __init__(self, agent_id: str, role: AgentRole, capabilities: List[str]):
        self.id = agent_id
        self.role = role
        self.capabilities = capabilities
        self.status = AgentStatus.IDLE
        self.current_task = None
        self.node_id = None
        self.registered_at = datetime.now().isoformat()
        self.last_heartbeat = datetime.now().isoformat()
        self.metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_execution_time": 0.0
        }

class AgentTeam:
    """Agent团队管理"""
    
    def __init__(self):
        self.agents = {}
        self.nodes = {}
        self.task_assignments = {}
        self.metrics = {
            "total_agents": 0,
            "online_agents": 0,
            "busy_agents": 0,
            "idle_agents": 0
        }
    
    def register_agent(self, agent_id: str, role: AgentRole, 
                       capabilities: List[str], node_id: str) -> Agent:
        """注册Agent"""
        agent = Agent(agent_id, role, capabilities)
        agent.node_id = node_id
        self.agents[agent_id] = agent
        
        # 更新节点信息
        if node_id not in self.nodes:
            self.nodes[node_id] = {
                "id": node_id,
                "agents": [],
                "status": "online"
            }
        self.nodes[node_id]["agents"].append(agent_id)
        
        self._update_metrics()
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """获取Agent"""
        return self.agents.get(agent_id)
    
    def get_agents_by_role(self, role: AgentRole) -> List[Agent]:
        """根据角色获取Agent"""
        return [agent for agent in self.agents.values() if agent.role == role]
    
    def get_idle_agents(self) -> List[Agent]:
        """获取空闲Agent"""
        return [agent for agent in self.agents.values() 
                if agent.status == AgentStatus.IDLE]
    
    def assign_task(self, agent_id: str, task_id: str) -> bool:
        """分配任务给Agent"""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        if agent.status != AgentStatus.IDLE:
            return False
        
        agent.status = AgentStatus.BUSY
        agent.current_task = task_id
        self.task_assignments[task_id] = agent_id
        
        self._update_metrics()
        return True
    
    def complete_task(self, agent_id: str, task_id: str) -> bool:
        """完成任务"""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        if agent.current_task != task_id:
            return False
        
        agent.status = AgentStatus.IDLE
        agent.current_task = None
        agent.metrics["tasks_completed"] += 1
        
        if task_id in self.task_assignments:
            del self.task_assignments[task_id]
        
        self._update_metrics()
        return True
    
    def fail_task(self, agent_id: str, task_id: str) -> bool:
        """任务失败"""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        if agent.current_task != task_id:
            return False
        
        agent.status = AgentStatus.IDLE
        agent.current_task = None
        agent.metrics["tasks_failed"] += 1
        
        if task_id in self.task_assignments:
            del self.task_assignments[task_id]
        
        self._update_metrics()
        return True
    
    def update_heartbeat(self, agent_id: str):
        """更新心跳"""
        if agent_id in self.agents:
            self.agents[agent_id].last_heartbeat = datetime.now().isoformat()
    
    def get_available_agent(self, role: AgentRole, 
                           capabilities: List[str]) -> Optional[Agent]:
        """获取可用的Agent"""
        candidates = []
        
        for agent in self.agents.values():
            if (agent.role == role and 
                agent.status == AgentStatus.IDLE and
                all(cap in agent.capabilities for cap in capabilities)):
                candidates.append(agent)
        
        if not candidates:
            return None
        
        # 选择负载最低的Agent
        return min(candidates, key=lambda a: a.metrics["tasks_completed"])
    
    def get_team_status(self) -> Dict[str, Any]:
        """获取团队状态"""
        return {
            "agents": {
                agent_id: {
                    "id": agent.id,
                    "role": agent.role.value,
                    "status": agent.status.value,
                    "node_id": agent.node_id,
                    "current_task": agent.current_task,
                    "metrics": agent.metrics
                }
                for agent_id, agent in self.agents.items()
            },
            "nodes": self.nodes,
            "metrics": self.metrics
        }
    
    def _update_metrics(self):
        """更新指标"""
        self.metrics["total_agents"] = len(self.agents)
        self.metrics["online_agents"] = len([a for a in self.agents.values() 
                                            if a.status != AgentStatus.OFFLINE])
        self.metrics["busy_agents"] = len([a for a in self.agents.values() 
                                          if a.status == AgentStatus.BUSY])
        self.metrics["idle_agents"] = len([a for a in self.agents.values() 
                                          if a.status == AgentStatus.IDLE])

class FaultToleranceManager:
    """容错管理器"""
    
    def __init__(self, redundancy: int = 3):
        self.redundancy = redundancy
        self.metrics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0
        }
    
    def execute_with_redundancy(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """冗余执行任务"""
        results = []
        
        for _ in range(self.redundancy):
            result = self.execute(task)
            results.append(result)
        
        return self.majority_vote(results)
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        # 这里应该调用实际的执行器
        return {"status": "completed", "result": "success"}
    
    def majority_vote(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """多数投票"""
        if not results:
            return {"status": "failed", "error": "No results"}
        
        # 统计投票
        votes = {}
        for result in results:
            status = result.get("status")
            votes[status] = votes.get(status, 0) + 1
        
        # 获取多数结果
        majority_status = max(votes.items(), key=lambda x: x[1])[0]
        
        # 返回多数结果
        for result in results:
            if result.get("status") == majority_status:
                return result
        
        return results[0]
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics

class LoadBalancer:
    """负载均衡器"""
    
    def __init__(self, nodes: List[str]):
        self.nodes = nodes
        self.current_index = 0
        self.node_metrics = {node: {"requests": 0, "errors": 0} for node in nodes}
    
    def get_node(self) -> str:
        """获取节点（轮询）"""
        if not self.nodes:
            return None
        
        node = self.nodes[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.nodes)
        
        self.node_metrics[node]["requests"] += 1
        return node
    
    def get_node_by_weight(self, weights: Dict[str, float]) -> str:
        """根据权重获取节点"""
        if not self.nodes:
            return None
        
        # 计算总权重
        total_weight = sum(weights.get(node, 1.0) for node in self.nodes)
        
        # 随机选择
        import random
        r = random.uniform(0, total_weight)
        cumulative = 0
        
        for node in self.nodes:
            cumulative += weights.get(node, 1.0)
            if r <= cumulative:
                self.node_metrics[node]["requests"] += 1
                return node
        
        # 默认返回第一个节点
        self.node_metrics[self.nodes[0]]["requests"] += 1
        return self.nodes[0]
    
    def report_error(self, node: str):
        """报告错误"""
        if node in self.node_metrics:
            self.node_metrics[node]["errors"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return {
            "nodes": self.nodes,
            "metrics": self.node_metrics
        }

class TaskPool:
    """任务池"""
    
    def __init__(self):
        self.tasks = {}
        self.queue = []
        self.metrics = {
            "total_tasks": 0,
            "pending_tasks": 0,
            "running_tasks": 0,
            "completed_tasks": 0
        }
    
    def add_task(self, task_id: str, task_type: str, params: Dict[str, Any], 
                 priority: int = 2) -> str:
        """添加任务"""
        self.tasks[task_id] = {
            "id": task_id,
            "type": task_type,
            "params": params,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        self.queue.append((priority, task_id))
        self.queue.sort(reverse=True)
        
        self.metrics["total_tasks"] += 1
        self.metrics["pending_tasks"] += 1
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """获取下一个任务"""
        for priority, task_id in self.queue:
            task = self.tasks[task_id]
            if task["status"] == "pending":
                return task
        return None
    
    def update_task_status(self, task_id: str, status: str) -> bool:
        """更新任务状态"""
        if task_id not in self.tasks:
            return False
        
        old_status = self.tasks[task_id]["status"]
        self.tasks[task_id]["status"] = status
        self.tasks[task_id]["updated_at"] = datetime.now().isoformat()
        
        # 更新指标
        if old_status == "pending":
            self.metrics["pending_tasks"] -= 1
        elif old_status == "running":
            self.metrics["running_tasks"] -= 1
        
        if status == "pending":
            self.metrics["pending_tasks"] += 1
        elif status == "running":
            self.metrics["running_tasks"] += 1
        elif status == "completed":
            self.metrics["completed_tasks"] += 1
        
        return True
    
    def list_tasks(self, status: str = None) -> List[Dict[str, Any]]:
        """列出任务"""
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        return tasks
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics

class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, task_pool: TaskPool, agent_team: AgentTeam):
        self.task_pool = task_pool
        self.agent_team = agent_team
        self.metrics = {
            "total_scheduled": 0,
            "successful_scheduled": 0,
            "failed_scheduled": 0
        }
    
    def schedule_task(self, task_id: str) -> bool:
        """调度任务"""
        task = self.task_pool.get_task(task_id)
        if not task:
            return False
        
        # 获取可用Agent
        agent = self.agent_team.get_available_agent(
            AgentRole.CODE_GENERATOR,  # 默认角色
            []  # 默认能力
        )
        
        if not agent:
            return False
        
        # 分配任务
        success = self.agent_team.assign_task(agent.id, task_id)
        if success:
            self.task_pool.update_task_status(task_id, "running")
            self.metrics["total_scheduled"] += 1
            self.metrics["successful_scheduled"] += 1
        
        return success
    
    def complete_task(self, task_id: str) -> bool:
        """完成任务"""
        # 获取任务分配的Agent
        agent_id = self.agent_team.task_assignments.get(task_id)
        if not agent_id:
            return False
        
        # 完成任务
        success = self.agent_team.complete_task(agent_id, task_id)
        if success:
            self.task_pool.update_task_status(task_id, "completed")
        
        return success
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics

class MultiModelAnalyzer:
    """多模型分析器"""
    
    def __init__(self):
        self.models = {}
        self.metrics = {
            "total_analyses": 0,
            "successful_analyses": 0,
            "failed_analyses": 0
        }
    
    def register_model(self, model_id: str, model_type: str, 
                       capabilities: List[str]):
        """注册模型"""
        self.models[model_id] = {
            "id": model_id,
            "type": model_type,
            "capabilities": capabilities,
            "status": "available",
            "metrics": {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0
            }
        }
    
    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取模型"""
        return self.models.get(model_id)
    
    def get_available_models(self, capability: str) -> List[Dict[str, Any]]:
        """获取可用模型"""
        return [
            model for model in self.models.values()
            if (model["status"] == "available" and 
                capability in model["capabilities"])
        ]
    
    def select_best_model(self, capability: str) -> Optional[Dict[str, Any]]:
        """选择最佳模型"""
        available_models = self.get_available_models(capability)
        
        if not available_models:
            return None
        
        # 选择成功率最高的模型
        return max(available_models, 
                  key=lambda m: m["metrics"]["successful_requests"] / 
                               max(m["metrics"]["total_requests"], 1))
    
    def analyze(self, model_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """分析任务"""
        model = self.get_model(model_id)
        if not model:
            return {"error": "Model not found"}
        
        # 更新指标
        model["metrics"]["total_requests"] += 1
        self.metrics["total_analyses"] += 1
        
        # 模拟分析
        result = {
            "model_id": model_id,
            "task": task,
            "analysis": "Analysis result",
            "timestamp": datetime.now().isoformat()
        }
        
        model["metrics"]["successful_requests"] += 1
        self.metrics["successful_analyses"] += 1
        
        return result
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return {
            "analyzer": self.metrics,
            "models": {
                model_id: model["metrics"]
                for model_id, model in self.models.items()
            }
        }

# 使用示例
if __name__ == "__main__":
    # 创建组件
    agent_team = AgentTeam()
    fault_tolerance = FaultToleranceManager()
    load_balancer = LoadBalancer(["node1", "node2", "node3"])
    task_pool = TaskPool()
    task_scheduler = TaskScheduler(task_pool, agent_team)
    multi_model_analyzer = MultiModelAnalyzer()
    
    # 注册Agent
    agent_team.register_agent("agent-1", AgentRole.CODE_GENERATOR, 
                             ["python", "javascript"], "node1")
    agent_team.register_agent("agent-2", AgentRole.CODE_REVIEWER, 
                             ["python", "code_review"], "node2")
    
    # 注册模型
    multi_model_analyzer.register_model("model-1", "code_generation", 
                                       ["python", "javascript"])
    multi_model_analyzer.register_model("model-2", "code_review", 
                                       ["python", "code_review"])
    
    # 添加任务
    task_pool.add_task("task-001", "code_generation", {"file": "main.py"})
    
    # 调度任务
    task_scheduler.schedule_task("task-001")
    
    # 获取状态
    print("Agent团队状态:", agent_team.get_team_status())
    print("任务池指标:", task_pool.get_metrics())
    print("调度器指标:", task_scheduler.get_metrics())
