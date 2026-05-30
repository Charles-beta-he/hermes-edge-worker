#!/usr/bin/env python3
"""
事件驱动测试
提升测试覆盖率
"""

import unittest
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from task_event_driven import TaskEventDriven

class TestTaskEventDriven(unittest.TestCase):
    """事件驱动测试"""
    
    def setUp(self):
        """测试前准备"""
        self.event_driven = TaskEventDriven()
    
    def test_handle_event(self):
        """测试事件处理"""
        self.event_driven.handle_event("task.created", {
            "task_id": "task-001",
            "priority": "P1"
        })
        
        self.assertEqual(self.event_driven.metrics["events_received"], 1)
    
    def test_handle_unknown_event(self):
        """测试处理未知事件"""
        self.event_driven.handle_event("unknown.event", {
            "task_id": "task-001"
        })
        
        self.assertEqual(self.event_driven.metrics["events_received"], 1)
    
    def test_on_task_created(self):
        """测试任务创建事件"""
        self.event_driven.on_task_created({
            "task_id": "task-001",
            "priority": "P1"
        })
        
        # 高优先级任务会触发自动认领
        # 由于编排器未初始化，会记录警告
    
    def test_on_task_status_changed(self):
        """测试任务状态变更事件"""
        self.event_driven.on_task_status_changed({
            "task_id": "task-001",
            "old_status": "pending",
            "new_status": "claimed"
        })
        
        # 状态变为claimed会触发自动执行
        # 由于编排器未初始化，会记录警告
    
    def test_on_task_dependency_met(self):
        """测试任务依赖满足事件"""
        self.event_driven.on_task_dependency_met({
            "task_id": "task-001"
        })
        
        # 依赖满足会触发自动认领
        # 由于编排器未初始化，会记录警告
    
    def test_on_task_priority_changed(self):
        """测试任务优先级变更事件"""
        self.event_driven.on_task_priority_changed({
            "task_id": "task-001",
            "new_priority": "P0"
        })
        
        # 优先级变为P0会触发自动认领
        # 由于编排器未初始化，会记录警告
    
    def test_on_task_assigned(self):
        """测试任务分配事件"""
        self.event_driven.on_task_assigned({
            "task_id": "task-001",
            "agent_id": "agent-001"
        })
        
        # 任务分配会触发自动执行
        # 由于编排器未初始化，会记录警告
    
    def test_auto_claim(self):
        """测试自动认领"""
        # 由于编排器未初始化，会记录警告
        self.event_driven.auto_claim("task-001")
        
        # 验证指标（编排器未初始化时不会增加错误计数）
        self.assertEqual(self.event_driven.metrics["errors"], 0)
    
    def test_auto_execute(self):
        """测试自动执行"""
        # 由于编排器未初始化，会记录警告
        self.event_driven.auto_execute("task-001")
        
        # 验证指标（编排器未初始化时不会增加错误计数）
        self.assertEqual(self.event_driven.metrics["errors"], 0)
    
    def test_get_metrics(self):
        """测试获取指标"""
        metrics = self.event_driven.get_metrics()
        
        self.assertIn("events_received", metrics)
        self.assertIn("tasks_auto_claimed", metrics)
        self.assertIn("tasks_auto_executed", metrics)
        self.assertIn("errors", metrics)

def run_tests():
    """运行测试"""
    # 创建测试加载器
    loader = unittest.TestLoader()
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试
    test_suite.addTests(loader.loadTestsFromTestCase(TestTaskEventDriven))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result

if __name__ == "__main__":
    print("=== 运行事件驱动测试 ===")
    result = run_tests()
    
    print(f"\n=== 测试结果 ===")
    print(f"运行测试: {result.testsRun}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"成功率: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
