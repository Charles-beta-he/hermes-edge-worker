#!/usr/bin/env python3
"""
核心组件测试套件
拒绝自嗨，真实验证
"""

import unittest
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestUnifiedDataLayer(unittest.TestCase):
    """统一数据层测试"""
    
    def setUp(self):
        """测试前准备"""
        from unified_data_layer import UnifiedDataLayer
        self.data_layer = UnifiedDataLayer(storage_dir="/tmp/test_storage")
    
    def test_store_and_retrieve(self):
        """测试存储和检索"""
        # 存储数据
        self.data_layer.store("task", "task-001", {
            "type": "code_generation",
            "status": "pending"
        })
        
        # 检索数据
        result = self.data_layer.retrieve("task", "task-001")
        
        # 验证
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "code_generation")
        self.assertEqual(result["status"], "pending")
    
    def test_retrieve_nonexistent(self):
        """测试检索不存在的数据"""
        result = self.data_layer.retrieve("task", "nonexistent")
        self.assertIsNone(result)
    
    def test_list_entities(self):
        """测试列出实体"""
        # 存储多个实体
        self.data_layer.store("task", "task-001", {"type": "code_generation"})
        self.data_layer.store("task", "task-002", {"type": "testing"})
        
        # 列出实体
        tasks = self.data_layer.list_entities("task")
        
        # 验证
        self.assertEqual(len(tasks), 2)
    
    def test_delete(self):
        """测试删除"""
        # 存储数据
        self.data_layer.store("task", "task-001", {"type": "code_generation"})
        
        # 删除数据
        result = self.data_layer.delete("task", "task-001")
        
        # 验证
        self.assertTrue(result)
        self.assertIsNone(self.data_layer.retrieve("task", "task-001"))
    
    def test_metrics(self):
        """测试指标"""
        # 执行一些操作
        self.data_layer.store("task", "task-001", {"type": "code_generation"})
        self.data_layer.retrieve("task", "task-001")
        
        # 获取指标
        metrics = self.data_layer.get_metrics()
        
        # 验证
        self.assertIn("data_layer", metrics)
        self.assertIn("storage", metrics)
        self.assertIn("cache", metrics)

class TestUnifiedEventBus(unittest.TestCase):
    """统一事件总线测试"""
    
    def setUp(self):
        """测试前准备"""
        from unified_event_bus import UnifiedEventBus, EventHandler
        self.event_bus = UnifiedEventBus()
        self.events_received = []
    
    def test_publish_and_subscribe(self):
        """测试发布和订阅"""
        from unified_event_bus import EventHandler
        
        # 创建处理器
        def handler(event):
            self.events_received.append(event)
        
        event_handler = EventHandler(
            handler_id="test_handler",
            handler_func=handler,
            event_types=["task.created"]
        )
        
        # 订阅事件
        self.event_bus.subscribe("task.created", event_handler)
        
        # 发布事件
        self.event_bus.publish("task.created", {"task_id": "task-001"})
        
        # 验证
        self.assertEqual(len(self.events_received), 1)
        self.assertEqual(self.events_received[0].data["task_id"], "task-001")
    
    def test_multiple_subscribers(self):
        """测试多个订阅者"""
        from unified_event_bus import EventHandler
        
        # 创建多个处理器
        handlers_received = [[], []]
        
        for i in range(2):
            def handler(event, idx=i):
                handlers_received[idx].append(event)
            
            event_handler = EventHandler(
                handler_id=f"handler_{i}",
                handler_func=handler,
                event_types=["task.created"]
            )
            
            self.event_bus.subscribe("task.created", event_handler)
        
        # 发布事件
        self.event_bus.publish("task.created", {"task_id": "task-001"})
        
        # 验证
        self.assertEqual(len(handlers_received[0]), 1)
        self.assertEqual(len(handlers_received[1]), 1)
    
    def test_event_store(self):
        """测试事件存储"""
        # 发布事件
        self.event_bus.publish("task.created", {"task_id": "task-001"})
        self.event_bus.publish("task.created", {"task_id": "task-002"})
        
        # 查询事件
        events = self.event_bus.query_events("task.created")
        
        # 验证
        self.assertEqual(len(events), 2)
    
    def test_metrics(self):
        """测试指标"""
        # 发布事件
        self.event_bus.publish("task.created", {"task_id": "task-001"})
        
        # 获取指标
        metrics = self.event_bus.get_metrics()
        
        # 验证
        self.assertIn("event_bus", metrics)
        self.assertEqual(metrics["event_bus"]["total_published"], 1)

class TestKnowledgeManager(unittest.TestCase):
    """知识管理器测试"""
    
    def setUp(self):
        """测试前准备"""
        from knowledge_manager import KnowledgeManager
        self.manager = KnowledgeManager()
    
    def test_record_and_search_experience(self):
        """测试记录和搜索经验"""
        # 记录经验
        self.manager.record_experience({
            "title": "Python性能优化技巧",
            "content": "使用NumPy、Pandas等库进行Python性能优化",
            "tags": ["python", "performance"]
        })
        
        # 搜索经验
        results = self.manager.search_experience("Python")
        
        # 验证
        self.assertGreater(len(results), 0)
    
    def test_search_no_results(self):
        """测试搜索无结果"""
        results = self.manager.search_experience("nonexistent")
        self.assertEqual(len(results), 0)
    
    def test_metrics(self):
        """测试指标"""
        # 记录经验
        self.manager.record_experience({
            "title": "Python性能优化技巧",
            "content": "使用NumPy、Pandas等库",
            "tags": ["python", "performance"]
        })
        
        # 搜索经验
        self.manager.search_experience("Python")
        
        # 获取指标
        metrics = self.manager.get_metrics()
        
        # 验证
        self.assertEqual(metrics["total_knowledge"], 1)
        self.assertEqual(metrics["total_searches"], 1)

class TestRAGKnowledgeManager(unittest.TestCase):
    """RAG知识管理器测试"""
    
    def setUp(self):
        """测试前准备"""
        from rag_knowledge_manager import RAGKnowledgeManager
        self.manager = RAGKnowledgeManager()
    
    def test_add_and_search(self):
        """测试添加和搜索"""
        # 添加知识
        self.manager.add_knowledge("1", "Python性能优化技巧", {"category": "programming"})
        self.manager.add_knowledge("2", "NumPy数组操作指南", {"category": "library"})
        
        # 搜索知识
        results = self.manager.search("Python performance")
        
        # 验证
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["id"], "1")
    
    def test_search_relevance(self):
        """测试搜索相关性"""
        # 添加知识
        self.manager.add_knowledge("1", "Python性能优化技巧", {"category": "programming"})
        self.manager.add_knowledge("2", "NumPy数组操作指南", {"category": "library"})
        
        # 搜索
        results = self.manager.search("Python performance")
        
        # 验证相关性排序
        if len(results) > 1:
            self.assertGreaterEqual(results[0]["score"], results[1]["score"])
    
    def test_metrics(self):
        """测试指标"""
        # 添加知识
        self.manager.add_knowledge("1", "Python性能优化技巧", {"category": "programming"})
        
        # 搜索
        self.manager.search("Python")
        
        # 获取指标
        metrics = self.manager.get_metrics()
        
        # 验证
        self.assertEqual(metrics["total_knowledge"], 1)
        self.assertEqual(metrics["total_searches"], 1)

class TestEdgeWorker(unittest.TestCase):
    """Edge Worker测试"""
    
    def test_edge_worker_import(self):
        """测试Edge Worker导入"""
        try:
            import edge_worker
            self.assertTrue(True)
        except ImportError:
            self.fail("Failed to import edge_worker")
    
    def test_edge_worker_version(self):
        """测试Edge Worker版本"""
        import edge_worker
        # Edge Worker可能没有__version__，但应该有其他标识
        self.assertTrue(hasattr(edge_worker, 'EdgeWorkerHandler') or hasattr(edge_worker, 'main'))

class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_data_layer_with_event_bus(self):
        """测试数据层与事件总线集成"""
        from unified_data_layer import UnifiedDataLayer
        from unified_event_bus import UnifiedEventBus, EventHandler
        
        # 创建组件
        data_layer = UnifiedDataLayer(storage_dir="/tmp/test_integration")
        event_bus = UnifiedEventBus()
        
        # 记录事件
        events = []
        def handler(event):
            events.append(event)
        
        event_handler = EventHandler(
            handler_id="integration_handler",
            handler_func=handler,
            event_types=["data.stored"]
        )
        event_bus.subscribe("data.stored", event_handler)
        
        # 存储数据并发布事件
        data_layer.store("task", "task-001", {"type": "code_generation"})
        event_bus.publish("data.stored", {"entity_type": "task", "entity_id": "task-001"})
        
        # 验证
        self.assertEqual(len(events), 1)
        self.assertIsNotNone(data_layer.retrieve("task", "task-001"))

def run_tests():
    """运行测试"""
    # 创建测试加载器
    loader = unittest.TestLoader()
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试
    test_suite.addTests(loader.loadTestsFromTestCase(TestUnifiedDataLayer))
    test_suite.addTests(loader.loadTestsFromTestCase(TestUnifiedEventBus))
    test_suite.addTests(loader.loadTestsFromTestCase(TestKnowledgeManager))
    test_suite.addTests(loader.loadTestsFromTestCase(TestRAGKnowledgeManager))
    test_suite.addTests(loader.loadTestsFromTestCase(TestEdgeWorker))
    test_suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result

if __name__ == "__main__":
    print("=== 运行核心组件测试 ===")
    result = run_tests()
    
    print(f"\n=== 测试结果 ===")
    print(f"运行测试: {result.testsRun}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"成功率: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    
    if result.failures:
        print(f"\n=== 失败详情 ===")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")
    
    if result.errors:
        print(f"\n=== 错误详情 ===")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")
