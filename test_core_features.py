#!/usr/bin/env python3
"""简化核心功能测试。"""

from simplified.core_features import AgentRole, AgentStatus, AgentTeam, TaskPool


def test_agent_team_registers_and_counts_idle_agent():
    team = AgentTeam()
    agent = team.register_agent("agent-1", AgentRole.CODE_GENERATOR, ["python"], "node-1")

    assert agent.id == "agent-1"
    assert agent.status == AgentStatus.IDLE
    assert team.get_agent("agent-1") is agent
    assert team.metrics["total_agents"] == 1
    assert team.metrics["idle_agents"] == 1


def test_task_pool_orders_pending_tasks_by_priority():
    pool = TaskPool()
    pool.add_task("low", "build", {"cmd": "test"}, priority=1)
    pool.add_task("high", "build", {"cmd": "deploy"}, priority=5)

    next_task = pool.get_next_task()
    assert next_task is not None
    assert next_task["id"] == "high"
    assert pool.update_task_status("high", "completed") is True
    assert pool.get_metrics()["completed_tasks"] == 1
