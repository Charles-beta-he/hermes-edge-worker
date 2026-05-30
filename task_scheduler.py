#!/usr/bin/env python3
"""
任务调度器
基于加权轮询算法
"""

import random
from typing import List, Dict, Any

class TaskScheduler:
    def __init__(self, agents: List[str]):
        self.agents = agents
        self.weights = {agent: 1.0 for agent in agents}
        self.current_index = 0
    
    def schedule(self, task: Dict[str, Any]) -> str:
        """调度任务到下一个Agent"""
        agent = self.select_agent()
        return self.dispatch(agent, task)
    
    def select_agent(self) -> str:
        """选择下一个Agent（加权轮询）"""
        total_weight = sum(self.weights.values())
        r = random.uniform(0, total_weight)
        cumulative = 0
        
        for agent, weight in self.weights.items():
            cumulative += weight
            if r <= cumulative:
                return agent
        
        return self.agents[0]
    
    def dispatch(self, agent: str, task: Dict[str, Any]) -> str:
        """分发任务到Agent"""
        # 这里应该调用实际的Agent API
        return f"Task dispatched to {agent}"
    
    def update_weight(self, agent: str, performance: float):
        """根据性能更新权重"""
        self.weights[agent] = performance

# 使用示例
if __name__ == "__main__":
    agents = ["agent1", "agent2", "agent3", "agent4"]
    scheduler = TaskScheduler(agents)
    
    task = {"type": "code_generation", "file": "main.py"}
    result = scheduler.schedule(task)
    print(result)
