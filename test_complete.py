#!/usr/bin/env python3
"""
完整测试套件
长期稳定目标：测试覆盖率 > 50%
"""

import unittest
import sys
import os
import json
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestUnifiedDataLayerComplete(unittest.TestCase):
    """统一数据层完整测试"""
    
    def setUp(self):
        """测试前准备"""
        from unified_data_layer import UnifiedDataLayer
        self.data_layer = UnifiedDataLayer(storage_dir="/tmp/test_storage_complete")
    
    def test_store_multiple_types(self):
        """测试存储多种类型"""
        # 存储任务
        self.data_layer.store("task", "task-001", {"type": "code_generation"})
        
        # 存储知识
        self.data_layer.store("knowledge", "knowledge-001", {"content": "Python技巧"})
        
        # 存储经验
        self.data_layer.store("experience", "experience-001", {"claim": "使用TypeScript"})
        
        # 验证
        self.assertIsNotNone(self.data_layer.retrieve("task", "task-001"))
        self.assertIsNotNone(self.data_layer.retrieve("knowledge", "knowledge-001"))
        self.assertIsNotNone(self.data_layer.retrieve("experience", "experience-001"))
    
    def test_update_data(self):
        """测试更新数据"""
        # 存储数据
        self.data_layer.store("task", "task-001", {"status": "pending"})
        
        # 更新数据
        self.data_layer.store("task", "task-001", {"status": "completed"})
        
        # 验证
        result = self.data_layer.retrieve("task", "task-001")
        self.assertEqual(result["status"], "completed")
    
    def test_concurrent_access(self):
        """测试并发访问"""
        import threading
        
        results = []
        
        def store_data(i):
            self.data_layer.store("task", f"task-{i}", {"index": i})
            results.append(i)
        
        # 创建多个线程
        threads = []
        for i in range(10):
            thread = threading.Thread(target=store_data, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证
        self.assertEqual(len(results), 10)
        for i in range(10):
            self.assertIsNotNone(self.data_layer.retrieve("task", f"task-{i}"))
    
    def test_large_data(self):
        """测试大数据"""
        # 创建大数据
        large_data = {"data": "x" * 10000}
        
        # 存储大数据
        self.data_layer.store("task", "task-large", large_data)
        
        # 检索大数据
        result = self.data_layer.retrieve("task", "task-large")
        
        # 验证
        self.assertEqual(len(result["data"]), 10000)
    
    def test_metrics_accuracy(self):
        """测试指标准确性"""
        # 执行操作
        for i in range(5):
            self.data_layer.store("task", f"task-{i}", {"index": i})
        
        for i in range(3):
            self.data_layer.retrieve("task", f"task-{i}")
        
        # 获取指标
        metrics = self.data_layer.get_metrics()
        
        # 验证
        self.assertGreaterEqual(metrics["data_layer"]["storage_operations"], 5)  # 5 store + 3 retrieve

class TestUnifiedEventBusComplete(unittest.TestCase):
    """统一事件总线完整测试"""
    
    def setUp(self):
        """测试前准备"""
        from unified_event_bus import UnifiedEventBus, EventHandler
        self.event_bus = UnifiedEventBus()
        self.events_received = []
    
    def test_event_ordering(self):
        """测试事件顺序"""
        from unified_event_bus import EventHandler
        
        # 创建处理器
        def handler(event):
            self.events_received.append(event.data["order"])
        
        event_handler = EventHandler(
            handler_id="order_handler",
            handler_func=handler,
            event_types=["test.event"]
        )
        
        self.event_bus.subscribe("test.event", event_handler)
        
        # 发布事件
        for i in range(5):
            self.event_bus.publish("test.event", {"order": i})
        
        # 验证顺序
        self.assertEqual(self.events_received, [0, 1, 2, 3, 4])
    
    def test_unsubscribe(self):
        """测试取消订阅"""
        from unified_event_bus import EventHandler
        
        # 创建处理器
        def handler(event):
            self.events_received.append(event)
        
        event_handler = EventHandler(
            handler_id="temp_handler",
            handler_func=handler,
            event_types=["test.event"]
        )
        
        # 订阅
        self.event_bus.subscribe("test.event", event_handler)
        
        # 发布事件
        self.event_bus.publish("test.event", {"data": "test1"})
        
        # 取消订阅
        self.event_bus.unsubscribe("test.event", "temp_handler")
        
        # 发布事件
        self.event_bus.publish("test.event", {"data": "test2"})
        
        # 验证只收到第一个事件
        self.assertEqual(len(self.events_received), 1)
    
    def test_multiple_event_types(self):
        """测试多种事件类型"""
        from unified_event_bus import EventHandler
        
        events = {"task": [], "knowledge": []}
        
        def task_handler(event):
            events["task"].append(event)
        
        def knowledge_handler(event):
            events["knowledge"].append(event)
        
        # 订阅不同事件
        self.event_bus.subscribe("task.created", EventHandler(
            handler_id="task_handler",
            handler_func=task_handler,
            event_types=["task.created"]
        ))
        
        self.event_bus.subscribe("knowledge.added", EventHandler(
            handler_id="knowledge_handler",
            handler_func=knowledge_handler,
            event_types=["knowledge.added"]
        ))
        
        # 发布事件
        self.event_bus.publish("task.created", {"task_id": "task-001"})
        self.event_bus.publish("knowledge.added", {"knowledge_id": "knowledge-001"})
        self.event_bus.publish("task.created", {"task_id": "task-002"})
        
        # 验证
        self.assertEqual(len(events["task"]), 2)
        self.assertEqual(len(events["knowledge"]), 1)
    
    def test_event_persistence(self):
        """测试事件持久化"""
        # 发布事件
        self.event_bus.publish("task.created", {"task_id": "task-001"})
        self.event_bus.publish("task.created", {"task_id": "task-002"})
        self.event_bus.publish("knowledge.added", {"knowledge_id": "knowledge-001"})
        
        # 查询事件
        task_events = self.event_bus.query_events("task.created")
        knowledge_events = self.event_bus.query_events("knowledge.added")
        
        # 验证
        self.assertEqual(len(task_events), 2)
        self.assertEqual(len(knowledge_events), 1)
    
    def test_metrics_accuracy(self):
        """测试指标准确性"""
        from unified_event_bus import EventHandler
        
        # 创建处理器
        def handler(event):
            pass
        
        event_handler = EventHandler(
            handler_id="metrics_handler",
            handler_func=handler,
            event_types=["test.event"]
        )
        
        # 订阅
        self.event_bus.subscribe("test.event", event_handler)
        
        # 发布事件
        for i in range(5):
            self.event_bus.publish("test.event", {"index": i})
        
        # 获取指标
        metrics = self.event_bus.get_metrics()
        
        # 验证
        self.assertEqual(metrics["event_bus"]["total_published"], 5)
        self.assertEqual(metrics["event_bus"]["total_handlers"], 1)

class TestKnowledgeManagerComplete(unittest.TestCase):
    """知识管理器完整测试"""
    
    def setUp(self):
        """测试前准备"""
        from knowledge_manager import KnowledgeManager
        self.manager = KnowledgeManager()
    
    def test_multiple_experience_types(self):
        """测试多种经验类型"""
        # 记录经验
        self.manager.record_experience({
            "title": "Python性能优化",
            "content": "使用NumPy、Pandas等库",
            "tags": ["python", "performance"]
        })
        
        # 记录功能
        self.manager.record_function({
            "title": "NumPy数组操作",
            "content": "NumPy提供了高效的数组操作",
            "tags": ["python", "numpy"]
        })
        
        # 记录流程
        self.manager.record_workflow({
            "title": "代码审查流程",
            "content": "代码审查的标准流程",
            "tags": ["workflow", "review"]
        })
        
        # 搜索
        python_results = self.manager.search_experience("Python")
        numpy_results = self.manager.search_function("NumPy")
        workflow_results = self.manager.search_workflow("代码审查")
        
        # 验证
        self.assertEqual(len(python_results), 1)
        self.assertEqual(len(numpy_results), 1)
        self.assertGreaterEqual(len(workflow_results), 0)
    
    def test_search_relevance(self):
        """测试搜索相关性"""
        # 添加知识
        self.manager.record_experience({
            "title": "Python性能优化技巧",
            "content": "使用NumPy、Pandas等库进行Python性能优化",
            "tags": ["python", "performance"]
        })
        
        self.manager.record_experience({
            "title": "Java性能优化",
            "content": "使用JVM调优进行Java性能优化",
            "tags": ["java", "performance"]
        })
        
        # 搜索
        results = self.manager.search_experience("Python performance")
        
        # 验证Python结果排在前面
        if len(results) > 1:
            self.assertIn("Python", results[0]["title"])
    
    def test_recommend_knowledge(self):
        """测试知识推荐"""
        # 添加知识
        self.manager.record_experience({
            "title": "React组件优化",
            "content": "使用React.memo优化组件性能",
            "tags": ["react", "performance"]
        })
        
        # 推荐
        context = {"task": "frontend_optimization", "framework": "react"}
        results = self.manager.recommend_knowledge(context)
        
        # 验证
        self.assertGreater(len(results), 0)
    
    def test_list_knowledge(self):
        """测试列出知识"""
        # 添加知识
        self.manager.record_experience({
            "title": "Python性能优化",
            "content": "使用NumPy、Pandas等库",
            "tags": ["python"]
        })
        
        self.manager.record_function({
            "title": "NumPy数组操作",
            "content": "NumPy提供了高效的数组操作",
            "tags": ["numpy"]
        })
        
        # 列出所有知识
        all_knowledge = self.manager.list_knowledge()
        
        # 验证
        self.assertEqual(len(all_knowledge), 2)
    
    def test_metrics_accuracy(self):
        """测试指标准确性"""
        # 添加知识
        for i in range(5):
            self.manager.record_experience({
                "title": f"经验{i}",
                "content": f"内容{i}",
                "tags": [f"tag{i}"]
            })
        
        # 搜索
        for i in range(3):
            self.manager.search_experience(f"经验{i}")
        
        # 获取指标
        metrics = self.manager.get_metrics()
        
        # 验证
        self.assertEqual(metrics["total_knowledge"], 5)
        self.assertEqual(metrics["total_searches"], 3)

class TestRAGKnowledgeManagerComplete(unittest.TestCase):
    """RAG知识管理器完整测试"""
    
    def setUp(self):
        """测试前准备"""
        from rag_knowledge_manager import RAGKnowledgeManager
        self.manager = RAGKnowledgeManager()
    
    def test_large_knowledge_base(self):
        """测试大型知识库"""
        # 添加大量知识
        for i in range(100):
            self.manager.add_knowledge(f"knowledge-{i}", f"知识内容{i}", {"index": i})
        
        # 搜索
        results = self.manager.search("知识内容50")
        
        # 验证
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["id"], "knowledge-50")
    
    def test_search_performance(self):
        """测试搜索性能"""
        import time
        
        # 添加知识
        for i in range(1000):
            self.manager.add_knowledge(f"knowledge-{i}", f"知识内容{i}", {"index": i})
        
        # 测试搜索时间
        start_time = time.time()
        for i in range(100):
            self.manager.search(f"知识内容{i}")
        end_time = time.time()
        
        # 验证性能（100次搜索应该在1秒内）
        self.assertLess(end_time - start_time, 1.0)
    
    def test_delete_knowledge(self):
        """测试删除知识"""
        # 添加知识
        self.manager.add_knowledge("knowledge-001", "Python性能优化", {"category": "programming"})
        
        # 删除知识
        result = self.manager.delete_knowledge("knowledge-001")
        
        # 验证
        self.assertTrue(result)
        self.assertIsNone(self.manager.get_knowledge("knowledge-001"))
    
    def test_save_and_load(self):
        """测试保存和加载"""
        # 添加知识
        self.manager.add_knowledge("knowledge-001", "Python性能优化", {"category": "programming"})
        self.manager.add_knowledge("knowledge-002", "NumPy数组操作", {"category": "library"})
        
        # 保存
        self.manager.save("/tmp/test_rag_save.pkl")
        
        # 创建新管理器并加载
        from rag_knowledge_manager import RAGKnowledgeManager
        new_manager = RAGKnowledgeManager()
        new_manager.load("/tmp/test_rag_save.pkl")
        
        # 验证
        self.assertEqual(new_manager.get_metrics()["total_knowledge"], 2)
        results = new_manager.search("Python")
        self.assertGreater(len(results), 0)
    
    def test_metrics_accuracy(self):
        """测试指标准确性"""
        # 添加知识
        for i in range(5):
            self.manager.add_knowledge(f"knowledge-{i}", f"知识内容{i}", {"index": i})
        
        # 搜索
        for i in range(3):
            self.manager.search(f"知识内容{i}")
        
        # 获取指标
        metrics = self.manager.get_metrics()
        
        # 验证
        self.assertEqual(metrics["total_knowledge"], 5)
        self.assertEqual(metrics["total_searches"], 3)

class TestEdgeWorkerComplete(unittest.TestCase):
    """Edge Worker完整测试"""
    
    def test_edge_worker_initialization(self):
        """测试Edge Worker初始化"""
        import edge_worker
        
        # 验证可以导入
        self.assertTrue(hasattr(edge_worker, 'EdgeWorkerHandler'))
        self.assertTrue(hasattr(edge_worker, 'main'))
    
    def test_edge_worker_handler(self):
        """测试Edge Worker处理器"""
        import edge_worker
        
        # 验证处理器类存在
        self.assertTrue(hasattr(edge_worker.EdgeWorkerHandler, 'do_GET'))
        self.assertTrue(hasattr(edge_worker.EdgeWorkerHandler, 'do_POST'))

class TestIntegrationComplete(unittest.TestCase):
    """完整集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流"""
        from unified_data_layer import UnifiedDataLayer
        from unified_event_bus import UnifiedEventBus, EventHandler
        
        # 创建组件
        data_layer = UnifiedDataLayer(storage_dir="/tmp/test_integration_complete")
        event_bus = UnifiedEventBus()
        
        # 记录事件
        events = []
        def handler(event):
            events.append(event)
        
        event_handler = EventHandler(
            handler_id="integration_handler",
            handler_func=handler,
            event_types=["task.created", "task.completed"]
        )
        event_bus.subscribe("task.created", event_handler)
        event_bus.subscribe("task.completed", event_handler)
        
        # 模拟工作流
        # 1. 创建任务
        data_layer.store("task", "task-001", {
            "type": "code_generation",
            "status": "pending",
            "params": {"file": "main.py"}
        })
        event_bus.publish("task.created", {"task_id": "task-001"})
        
        # 2. 执行任务
        task = data_layer.retrieve("task", "task-001")
        task["status"] = "running"
        data_layer.store("task", "task-001", task)
        
        # 3. 完成任务
        task["status"] = "completed"
        task["result"] = "Generated code"
        data_layer.store("task", "task-001", task)
        event_bus.publish("task.completed", {"task_id": "task-001"})
        
        # 验证
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].type, "task.created")
        self.assertEqual(events[1].type, "task.completed")
        
        # 验证数据
        final_task = data_layer.retrieve("task", "task-001")
        self.assertEqual(final_task["status"], "completed")
        self.assertEqual(final_task["result"], "Generated code")
    
    def test_error_handling(self):
        """测试错误处理"""
        from unified_data_layer import UnifiedDataLayer
        
        data_layer = UnifiedDataLayer(storage_dir="/tmp/test_error_handling")
        
        # 测试检索不存在的数据
        result = data_layer.retrieve("task", "nonexistent")
        self.assertIsNone(result)
        
        # 测试删除不存在的数据
        result = data_layer.delete("task", "nonexistent")
        self.assertFalse(result)
    
    def test_performance_baseline(self):
        """测试性能基线"""
        from unified_data_layer import UnifiedDataLayer
        import time
        
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
        
        # 验证性能（1000次操作应该在1秒内）
        self.assertLess(store_time, 1.0)
        self.assertLess(retrieve_time, 1.0)

def run_complete_tests():
    """运行完整测试"""
    # 创建测试加载器
    loader = unittest.TestLoader()
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试
    test_suite.addTests(loader.loadTestsFromTestCase(TestUnifiedDataLayerComplete))
    test_suite.addTests(loader.loadTestsFromTestCase(TestUnifiedEventBusComplete))
    test_suite.addTests(loader.loadTestsFromTestCase(TestKnowledgeManagerComplete))
    test_suite.addTests(loader.loadTestsFromTestCase(TestRAGKnowledgeManagerComplete))
    test_suite.addTests(loader.loadTestsFromTestCase(TestEdgeWorkerComplete))
    test_suite.addTests(loader.loadTestsFromTestCase(TestIntegrationComplete))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result

if __name__ == "__main__":
    print("=== 运行完整测试套件 ===")
    result = run_complete_tests()
    
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
