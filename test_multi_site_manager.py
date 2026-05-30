#!/usr/bin/env python3
"""
多站点管理器测试
提升测试覆盖率
"""

import unittest
import sys
import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from multi_site_manager import MultiSiteManager, LoadBalancer, FailoverManager

class TestMultiSiteManager(unittest.TestCase):
    """多站点管理器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.manager = MultiSiteManager()
    
    def test_register_site(self):
        """测试站点注册"""
        result = self.manager.register_site("site-001", {
            "name": "Test-Site",
            "ip": "192.168.31.100",
            "port": 9002
        })
        
        self.assertTrue(result)
        self.assertIn("site-001", self.manager.sites)
        self.assertEqual(self.manager.sites["site-001"]["status"], "online")
    
    def test_unregister_site(self):
        """测试站点注销"""
        self.manager.register_site("site-001", {"name": "Test"})
        result = self.manager.unregister_site("site-001")
        
        self.assertTrue(result)
        self.assertNotIn("site-001", self.manager.sites)
    
    def test_heartbeat(self):
        """测试心跳检测"""
        self.manager.register_site("site-001", {"name": "Test"})
        
        # 更新心跳
        result = self.manager.heartbeat("site-001", {
            "cpu_usage": 50.0,
            "memory_usage": 60.0
        })
        
        self.assertTrue(result)
        self.assertIn("site-001", self.manager.sites)
    
    def test_health_check(self):
        """测试健康检查"""
        self.manager.register_site("site-001", {"name": "Test"})
        
        # 模拟心跳超时
        self.manager.sites["site-001"]["last_heartbeat"] = (
            datetime.now() - timedelta(seconds=120)
        ).isoformat()
        
        # 健康检查
        self.manager._check_health()
        
        self.assertEqual(self.manager.sites["site-001"]["status"], "offline")
    
    def test_get_available_site(self):
        """测试获取可用站点"""
        self.manager.register_site("site-001", {"name": "Test1"})
        self.manager.register_site("site-002", {"name": "Test2"})
        
        site = self.manager.get_available_site()
        
        self.assertIsNotNone(site)
        self.assertIn(site, ["site-001", "site-002"])
    
    def test_get_available_site_offline(self):
        """测试获取可用站点（全部离线）"""
        self.manager.register_site("site-001", {"name": "Test"})
        
        # 模拟离线
        self.manager.sites["site-001"]["status"] = "offline"
        
        site = self.manager.get_available_site()
        
        self.assertIsNone(site)
    
    def test_update_site_metrics(self):
        """测试更新站点指标"""
        self.manager.register_site("site-001", {"name": "Test"})
        
        result = self.manager.update_site_metrics("site-001", {
            "cpu_usage": 75.0,
            "memory_usage": 80.0
        })
        
        self.assertTrue(result)
        self.assertEqual(self.manager.sites["site-001"]["metrics"]["cpu_usage"], 75.0)
    
    def test_get_metrics(self):
        """测试获取指标"""
        self.manager.register_site("site-001", {"name": "Test1"})
        self.manager.register_site("site-002", {"name": "Test2"})
        
        metrics = self.manager.get_metrics()
        
        self.assertEqual(metrics["total_sites"], 2)
        self.assertEqual(metrics["online_sites"], 2)
        self.assertEqual(metrics["offline_sites"], 0)

class TestLoadBalancer(unittest.TestCase):
    """负载均衡器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.balancer = LoadBalancer()
    
    def test_round_robin(self):
        """测试轮询策略"""
        sites = ["site-001", "site-002", "site-003"]
        
        # 测试轮询
        results = []
        for _ in range(6):
            site = self.balancer.round_robin(sites)
            results.append(site)
        
        # 验证轮询
        self.assertEqual(results[0], "site-001")
        self.assertEqual(results[1], "site-002")
        self.assertEqual(results[2], "site-003")
        self.assertEqual(results[3], "site-001")
    
    def test_select(self):
        """测试选择策略"""
        sites = ["site-001", "site-002"]
        
        site = self.balancer.select(sites)
        
        self.assertIn(site, sites)

class TestFailoverManager(unittest.TestCase):
    """故障转移管理器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.manager = MultiSiteManager()
        self.failover = FailoverManager(self.manager)
    
    def test_handle_failure(self):
        """测试处理故障"""
        self.manager.register_site("site-001", {"name": "Test1"})
        self.manager.register_site("site-002", {"name": "Test2"})
        
        new_site = self.failover.handle_failure("site-001", "task-001")
        
        self.assertIsNotNone(new_site)
        self.assertEqual(new_site, "site-002")
        self.assertEqual(self.manager.sites["site-001"]["status"], "offline")
    
    def test_handle_failure_no_alternative(self):
        """测试处理故障（无备用站点）"""
        self.manager.register_site("site-001", {"name": "Test"})
        
        new_site = self.failover.handle_failure("site-001", "task-001")
        
        self.assertIsNone(new_site)
    
    def test_failover_history(self):
        """测试故障转移历史"""
        self.manager.register_site("site-001", {"name": "Test1"})
        self.manager.register_site("site-002", {"name": "Test2"})
        
        self.failover.handle_failure("site-001", "task-001")
        
        history = self.failover.get_failover_history()
        
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["site_id"], "site-001")
        self.assertEqual(history[0]["task_id"], "task-001")

def run_tests():
    """运行测试"""
    # 创建测试加载器
    loader = unittest.TestLoader()
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试
    test_suite.addTests(loader.loadTestsFromTestCase(TestMultiSiteManager))
    test_suite.addTests(loader.loadTestsFromTestCase(TestLoadBalancer))
    test_suite.addTests(loader.loadTestsFromTestCase(TestFailoverManager))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result

if __name__ == "__main__":
    print("=== 运行多站点管理器测试 ===")
    result = run_tests()
    
    print(f"\n=== 测试结果 ===")
    print(f"运行测试: {result.testsRun}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"成功率: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
