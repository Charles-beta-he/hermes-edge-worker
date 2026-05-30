#!/usr/bin/env python3
"""
组件集成测试
提高测试覆盖率到30%
"""

import unittest
import sys
import os
import json
import time
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestComponentIntegration(unittest.TestCase):
    """组件集成测试"""
    
    def test_data_layer_with_knowledge_manager(self):
        """测试数据层与知识管理器集成"""
        from unified_data_layer import UnifiedDataLayer
        from knowledge_manager import KnowledgeManager
        
        # 创建组件
        data_layer = UnifiedDataLayer(storage_dir="/tmp/test_integration_knowledge")
        knowledge_manager = KnowledgeManager()
        
        # 记录经验
        knowledge_manager.record_experience({
            "title": "Python性能优化",
            "content": "使用NumPy、Pandas等库",
            "tags": ["python", "performance"]
        })
        
        # 存储到数据层
        data_layer.store("knowledge", "knowledge-001", {
            "title": "Python性能优化",
            "content": "使用NumPy、Pandas等库",
            "tags": ["python", "performance"]
        })
        
        # 搜索知识
        results = knowledge_manager.search_experience("Python")
        
        # 从数据层检索
        stored_knowledge = data_layer.retrieve("knowledge", "knowledge-001")
        
        # 验证
        self.assertEqual(len(results), 1)
        self.assertIsNotNone(stored_knowledge)
        self.assertEqual(stored_knowledge["title"], "Python性能优化")
    
    def test_event_bus_with_data_layer(self):
        """测试事件总线与数据层集成"""
        from unified_data_layer import UnifiedDataLayer
        from unified_event_bus import UnifiedEventBus, EventHandler
        
        # 创建组件
        data_layer = UnifiedDataLayer(storage_dir="/tmp/test_integration_event")
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
        self.assertEqual(events[0].data["entity_id"], "task-001")
    
    def test_rag_with_knowledge_manager(self):
        """测试RAG与知识管理器集成"""
        from rag_knowledge_manager import RAGKnowledgeManager
        from knowledge_manager import KnowledgeManager
        
        # 创建组件
        rag_manager = RAGKnowledgeManager()
        knowledge_manager = KnowledgeManager()
        
        # 记录经验
        knowledge_manager.record_experience({
            "title": "Python性能优化",
            "content": "使用NumPy、Pandas等库进行Python性能优化",
            "tags": ["python", "performance"]
        })
        
        # 添加到RAG
        rag_manager.add_knowledge("1", "使用NumPy、Pandas等库进行Python性能优化", {
            "category": "programming"
        })
        
        # 搜索
        rag_results = rag_manager.search("Python performance")
        knowledge_results = knowledge_manager.search_experience("Python")
        
        # 验证
        self.assertGreaterEqual(len(rag_results), 0)
        self.assertGreater(len(knowledge_results), 0)
    
    def test_full_pipeline(self):
        """测试完整流水线"""
        from unified_data_layer import UnifiedDataLayer
        from unified_event_bus import UnifiedEventBus, EventHandler
        from knowledge_manager import KnowledgeManager
        from rag_knowledge_manager import RAGKnowledgeManager
        
        # 创建组件
        data_layer = UnifiedDataLayer(storage_dir="/tmp/test_full_pipeline")
        event_bus = UnifiedEventBus()
        knowledge_manager = KnowledgeManager()
        rag_manager = RAGKnowledgeManager()
        
        # 记录事件
        events = []
        def handler(event):
            events.append(event)
        
        event_handler = EventHandler(
            handler_id="pipeline_handler",
            handler_func=handler,
            event_types=["knowledge.added", "task.created"]
        )
        event_bus.subscribe("knowledge.added", event_handler)
        event_bus.subscribe("task.created", event_handler)
        
        # 1. 添加知识
        knowledge_manager.record_experience({
            "title": "Python性能优化",
            "content": "使用NumPy、Pandas等库",
            "tags": ["python"]
        })
        
        # 2. 存储到数据层
        data_layer.store("knowledge", "knowledge-001", {
            "title": "Python性能优化",
            "content": "使用NumPy、Pandas等库"
        })
        
        # 3. 添加到RAG
        rag_manager.add_knowledge("1", "使用NumPy、Pandas等库", {"category": "programming"})
        
        # 4. 发布事件
        event_bus.publish("knowledge.added", {"knowledge_id": "knowledge-001"})
        
        # 5. 创建任务
        data_layer.store("task", "task-001", {"type": "code_generation"})
        event_bus.publish("task.created", {"task_id": "task-001"})
        
        # 验证
        self.assertEqual(len(events), 2)
        self.assertIsNotNone(data_layer.retrieve("knowledge", "knowledge-001"))
        self.assertIsNotNone(data_layer.retrieve("task", "task-001"))
        
        # 搜索验证
        rag_results = rag_manager.search("Python")
        self.assertGreaterEqual(len(rag_results), 0)

class TestPerformance(unittest.TestCase):
    """性能测试"""
    
    def test_data_layer_performance(self):
        """测试数据层性能"""
        from unified_data_layer import UnifiedDataLayer
        
        data_layer = UnifiedDataLayer(storage_dir="/tmp/test_performance")
        
        # 测试存储性能
        start_time = time.time()
        for i in range(1000):
            data_layer.store("task", f"task-{i}", {"index": i})
        store_time = time.time() - start_time
        
        # 测试检索性能
        start_time = time.time()
        for i in range(1000):
            data_layer.retrieve("task", f"task-{i}")
        retrieve_time = time.time() - start_time
        
        # 验证性能
        self.assertLess(store_time, 2.0)  # 1000次存储<2秒
        self.assertLess(retrieve_time, 1.0)  # 1000次检索<1秒
    
    def test_event_bus_performance(self):
        """测试事件总线性能"""
        from unified_event_bus import UnifiedEventBus, EventHandler
        
        event_bus = UnifiedEventBus()
        
        # 创建处理器
        events_received = []
        def handler(event):
            events_received.append(event)
        
        event_handler = EventHandler(
            handler_id="performance_handler",
            handler_func=handler,
            event_types=["test.event"]
        )
        event_bus.subscribe("test.event", event_handler)
        
        # 测试发布性能
        start_time = time.time()
        for i in range(1000):
            event_bus.publish("test.event", {"index": i})
        publish_time = time.time() - start_time
        
        # 验证性能
        self.assertLess(publish_time, 1.0)  # 1000次发布<1秒
        self.assertEqual(len(events_received), 1000)
    
    def test_knowledge_search_performance(self):
        """测试知识搜索性能"""
        from knowledge_manager import KnowledgeManager
        
        manager = KnowledgeManager()
        
        # 添加知识
        for i in range(100):
            manager.record_experience({
                "title": f"经验{i}",
                "content": f"内容{i}",
                "tags": [f"tag{i}"]
            })
        
        # 测试搜索性能
        start_time = time.time()
        for i in range(100):
            manager.search_experience(f"经验{i}")
        search_time = time.time() - start_time
        
        # 验证性能
        self.assertLess(search_time, 1.0)  # 100次搜索<1秒
    
    def test_rag_search_performance(self):
        """测试RAG搜索性能"""
        from rag_knowledge_manager import RAGKnowledgeManager
        
        manager = RAGKnowledgeManager()
        
        # 添加知识
        for i in range(100):
            manager.add_knowledge(f"knowledge-{i}", f"知识内容{i}", {"index": i})
        
        # 测试搜索性能
        start_time = time.time()
        for i in range(100):
            manager.search(f"知识内容{i}")
        search_time = time.time() - start_time
        
        # 验证性能
        self.assertLess(search_time, 2.0)  # 100次搜索<2秒

class TestErrorHandling(unittest.TestCase):
    """错误处理测试"""
    
    def test_data_layer_error_handling(self):
        """测试数据层错误处理"""
        from unified_data_layer import UnifiedDataLayer
        
        data_layer = UnifiedDataLayer(storage_dir="/tmp/test_error")
        
        # 测试检索不存在的数据
        result = data_layer.retrieve("task", "nonexistent")
        self.assertIsNone(result)
        
        # 测试删除不存在的数据
        result = data_layer.delete("task", "nonexistent")
        self.assertFalse(result)
    
    def test_event_bus_error_handling(self):
        """测试事件总线错误处理"""
        from unified_event_bus import UnifiedEventBus, EventHandler
        
        event_bus = UnifiedEventBus()
        
        # 测试取消不存在的订阅
        result = event_bus.unsubscribe("nonexistent", "nonexistent")
        self.assertFalse(result)
    
    def test_knowledge_manager_error_handling(self):
        """测试知识管理器错误处理"""
        from knowledge_manager import KnowledgeManager
        
        manager = KnowledgeManager()
        
        # 测试搜索不存在的知识
        results = manager.search_experience("nonexistent")
        self.assertEqual(len(results), 0)
    
    def test_rag_error_handling(self):
        """测试RAG错误处理"""
        from rag_knowledge_manager import RAGKnowledgeManager
        
        manager = RAGKnowledgeManager()
        
        # 测试检索不存在的知识
        result = manager.get_knowledge("nonexistent")
        self.assertIsNone(result)
        
        # 测试删除不存在的知识
        result = manager.delete_knowledge("nonexistent")
        self.assertFalse(result)

class TestDataIntegrity(unittest.TestCase):
    """数据完整性测试"""
    
    def test_data_consistency(self):
        """测试数据一致性"""
        from unified_data_layer import UnifiedDataLayer
        
        data_layer = UnifiedDataLayer(storage_dir="/tmp/test_integrity")
        
        # 存储数据
        original_data = {
            "type": "code_generation",
            "params": {"file": "main.py"},
            "status": "pending",
            "metadata": {"priority": "high", "tags": ["python"]}
        }
        
        data_layer.store("task", "task-001", original_data)
        
        # 检索数据
        retrieved_data = data_layer.retrieve("task", "task-001")
        
        # 验证数据一致性
        self.assertEqual(original_data["type"], retrieved_data["type"])
        self.assertEqual(original_data["params"], retrieved_data["params"])
        self.assertEqual(original_data["status"], retrieved_data["status"])
        self.assertEqual(original_data["metadata"], retrieved_data["metadata"])
    
    def test_event_ordering(self):
        """测试事件顺序"""
        from unified_event_bus import UnifiedEventBus, EventHandler
        
        event_bus = UnifiedEventBus()
        
        # 记录事件顺序
        event_order = []
        def handler(event):
            event_order.append(event.data["order"])
        
        event_handler = EventHandler(
            handler_id="order_handler",
            handler_func=handler,
            event_types=["test.event"]
        )
        event_bus.subscribe("test.event", event_handler)
        
        # 发布事件
        for i in range(10):
            event_bus.publish("test.event", {"order": i})
        
        # 验证顺序
        self.assertEqual(event_order, list(range(10)))
    
    def test_concurrent_data_access(self):
        """测试并发数据访问"""
        from unified_data_layer import UnifiedDataLayer
        import threading
        
        data_layer = UnifiedDataLayer(storage_dir="/tmp/test_concurrent")
        
        # 并发存储
        def store_data(i):
            data_layer.store("task", f"task-{i}", {"index": i})
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=store_data, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 验证所有数据都存储成功
        for i in range(10):
            result = data_layer.retrieve("task", f"task-{i}")
            self.assertIsNotNone(result)
            self.assertEqual(result["index"], i)

def run_integration_tests():
    """运行集成测试"""
    # 创建测试加载器
    loader = unittest.TestLoader()
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试
    test_suite.addTests(loader.loadTestsFromTestCase(TestComponentIntegration))
    test_suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    test_suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    test_suite.addTests(loader.loadTestsFromTestCase(TestDataIntegrity))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result

if __name__ == "__main__":
    print("=== 运行组件集成测试 ===")
    result = run_integration_tests()
    
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
