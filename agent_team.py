#!/usr/bin/env python3
"""
Agent Team管理器
多节点落地核心组件
"""

import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

class AgentRole(Enum):
    CODE_GENERATOR = "code_generator"
    CODE_REVIEWER = "code_reviewer"
    TEST_RUNNER = "test_runner"
    DOCUMENTATION = "documentation"
    DEPLOYER = "deployer"

class AgentStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    IDLE = "idle"

class Agent:
    def __init__(self, agent_id: str, role: AgentRole, capabilities: List[str]):
        self.id = agent_id
        self.role = role
        self.capabilities = capabilities
        self.status = AgentStatus.IDLE
        self.current_task: Optional[str] = None
        self.node_id: Optional[str] = None
        self.registered_at = datetime.now().isoformat()
        self.last_heartbeat = datetime.now().isoformat()
        self.metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_execution_time": 0
        }

class AgentTeam:
    def __init__(self):
        self.agents = {}  # Agent池
        self.nodes = {}  # 节点池
        self.task_assignments = {}  # 任务分配记录
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

# 使用示例
if __name__ == "__main__":
    team = AgentTeam()
    
    # 注册Agent
    team.register_agent("agent-1", AgentRole.CODE_GENERATOR, 
                       ["python", "javascript"], "node-1")
    team.register_agent("agent-2", AgentRole.CODE_REVIEWER, 
                       ["python", "code_review"], "node-1")
    team.register_agent("agent-3", AgentRole.TEST_RUNNER, 
                       ["testing", "automation"], "node-2")
    
    # 分配任务
    team.assign_task("agent-1", "task-001")
    team.assign_task("agent-2", "task-002")
    
    # 完成任务
    team.complete_task("agent-1", "task-001")
    
    # 获取团队状态
    status = team.get_team_status()
    print(json.dumps(status, indent=2))
