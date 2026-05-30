#!/usr/bin/env python3
"""
API接口测试
提高测试覆盖率到30%
"""

import unittest
import sys
import os
import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class MockAPIHandler(BaseHTTPRequestHandler):
    """模拟API处理器"""
    
    def do_GET(self):
        """处理GET请求"""
        path = urlparse(self.path).path
        
        if path == "/health":
            self._send_json({"status": "ok"})
        elif path == "/tasks":
            self._send_json({"tasks": []})
        elif path == "/knowledge/search":
            self._send_json({"results": []})
        else:
            self._send_error(404, "Not found")
    
    def do_POST(self):
        """处理POST请求"""
        path = urlparse(self.path).path
        
        if path == "/tasks":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            self._send_json({"task_id": "task-001", "status": "created"})
        else:
            self._send_error(404, "Not found")
    
    def _send_json(self, data):
        """发送JSON响应"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _send_error(self, code, message):
        """发送错误响应"""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode())

class TestAPIEndpoints(unittest.TestCase):
    """API端点测试"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试服务器"""
        cls.server = HTTPServer(("localhost", 0), MockAPIHandler)
        cls.port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.1)
    
    @classmethod
    def tearDownClass(cls):
        """关闭测试服务器"""
        cls.server.shutdown()
        cls.server_thread.join()
    
    def test_health_endpoint(self):
        """测试健康检查端点"""
        import urllib.request
        
        response = urllib.request.urlopen(f"http://localhost:{self.port}/health")
        data = json.loads(response.read().decode())
        
        self.assertEqual(data["status"], "ok")
    
    def test_tasks_endpoint(self):
        """测试任务端点"""
        import urllib.request
        
        response = urllib.request.urlopen(f"http://localhost:{self.port}/tasks")
        data = json.loads(response.read().decode())
        
        self.assertIn("tasks", data)
    
    def test_create_task(self):
        """测试创建任务"""
        import urllib.request
        
        data = json.dumps({"type": "code_generation", "params": {"file": "main.py"}}).encode()
        req = urllib.request.Request(
            f"http://localhost:{self.port}/tasks",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        response = urllib.request.urlopen(req)
        result = json.loads(response.read().decode())
        
        self.assertEqual(result["task_id"], "task-001")
        self.assertEqual(result["status"], "created")
    
    def test_not_found(self):
        """测试404端点"""
        import urllib.request
        
        try:
            urllib.request.urlopen(f"http://localhost:{self.port}/nonexistent")
            self.fail("Should have raised exception")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

class TestUnifiedGatewayAPI(unittest.TestCase):
    """统一网关API测试"""
    
    def test_gateway_import(self):
        """测试网关导入"""
        try:
            from unified_gateway import UnifiedGateway, UnifiedGatewayHandler
            self.assertTrue(True)
        except ImportError:
            self.fail("Failed to import unified_gateway")
    
    def test_gateway_initialization(self):
        """测试网关初始化"""
        from unified_gateway import UnifiedGateway
        
        gateway = UnifiedGateway("localhost", 0)
        self.assertIsNotNone(gateway)
    
    def test_gateway_register_component(self):
        """测试网关注册组件"""
        from unified_gateway import UnifiedGateway
        
        gateway = UnifiedGateway("localhost", 0)
        
        # 创建模拟组件
        class MockComponent:
            def get_metrics(self):
                return {}
        
        # 注册组件
        gateway.register_component("test", MockComponent())
        
        # 验证
        self.assertIn("test", gateway.components)

class TestUnifiedInterfaceAPI(unittest.TestCase):
    """统一接口API测试"""
    
    def test_interface_import(self):
        """测试接口导入"""
        try:
            from unified_interface_layer import UnifiedInterface, UnifiedInterfaceRegistry
            self.assertTrue(True)
        except ImportError:
            self.fail("Failed to import unified_interface_layer")
    
    def test_interface_creation(self):
        """测试接口创建"""
        from unified_interface_layer import UnifiedInterface
        
        interface = UnifiedInterface("test", "1.0.0")
        self.assertEqual(interface.name, "test")
        self.assertEqual(interface.version, "1.0.0")
    
    def test_interface_register_endpoint(self):
        """测试接口注册端点"""
        from unified_interface_layer import UnifiedInterface
        
        interface = UnifiedInterface("test", "1.0.0")
        
        # 注册端点
        def handler(params, body):
            return {"result": "ok"}
        
        interface.register_endpoint("GET", "/test", handler)
        
        # 验证
        self.assertIn("GET:/test", interface.endpoints)
    
    def test_interface_handle_request(self):
        """测试接口处理请求"""
        from unified_interface_layer import UnifiedInterface
        
        interface = UnifiedInterface("test", "1.0.0")
        
        # 注册端点
        def handler(params, body):
            return {"result": "ok"}
        
        interface.register_endpoint("GET", "/test", handler)
        
        # 处理请求
        result = interface.handle_request("GET", "/test")
        
        # 验证
        self.assertEqual(result["status"], 200)
        self.assertEqual(result["result"]["result"], "ok")

class TestKnowledgeAPI(unittest.TestCase):
    """知识API测试"""
    
    def test_knowledge_api_import(self):
        """测试知识API导入"""
        try:
            from knowledge_api import KnowledgeAPIHandler, KnowledgeAPIServer
            self.assertTrue(True)
        except ImportError:
            self.fail("Failed to import knowledge_api")
    
    def test_rag_api_import(self):
        """测试RAG API导入"""
        try:
            from rag_api import RAGAPIHandler, RAGAPIServer
            self.assertTrue(True)
        except ImportError:
            self.fail("Failed to import rag_api")

class TestDataLayerAPI(unittest.TestCase):
    """数据层API测试"""
    
    def test_data_layer_store_and_retrieve(self):
        """测试数据层存储和检索"""
        from unified_data_layer import UnifiedDataLayer
        
        data_layer = UnifiedDataLayer(storage_dir="/tmp/test_api")
        
        # 存储数据
        data_layer.store("task", "task-001", {
            "type": "code_generation",
            "status": "pending"
        })
        
        # 检索数据
        result = data_layer.retrieve("task", "task-001")
        
        # 验证
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "code_generation")
    
    def test_data_layer_list(self):
        """测试数据层列表"""
        from unified_data_layer import UnifiedDataLayer
        
        data_layer = UnifiedDataLayer(storage_dir="/tmp/test_api_list")
        
        # 存储多个数据
        for i in range(5):
            data_layer.store("task", f"task-{i}", {"index": i})
        
        # 列出数据
        tasks = data_layer.list_entities("task")
        
        # 验证
        self.assertEqual(len(tasks), 5)
    
    def test_data_layer_delete(self):
        """测试数据层删除"""
        from unified_data_layer import UnifiedDataLayer
        
        data_layer = UnifiedDataLayer(storage_dir="/tmp/test_api_delete")
        
        # 存储数据
        data_layer.store("task", "task-001", {"type": "code_generation"})
        
        # 删除数据
        result = data_layer.delete("task", "task-001")
        
        # 验证
        self.assertTrue(result)
        self.assertIsNone(data_layer.retrieve("task", "task-001"))

class TestEventBusAPI(unittest.TestCase):
    """事件总线API测试"""
    
    def test_event_bus_publish_subscribe(self):
        """测试事件总线发布订阅"""
        from unified_event_bus import UnifiedEventBus, EventHandler
        
        event_bus = UnifiedEventBus()
        
        # 记录事件
        events_received = []
        def handler(event):
            events_received.append(event)
        
        event_handler = EventHandler(
            handler_id="test_handler",
            handler_func=handler,
            event_types=["test.event"]
        )
        
        # 订阅
        event_bus.subscribe("test.event", event_handler)
        
        # 发布
        event_bus.publish("test.event", {"data": "test"})
        
        # 验证
        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0].data["data"], "test")
    
    def test_event_bus_query(self):
        """测试事件总线查询"""
        from unified_event_bus import UnifiedEventBus
        
        event_bus = UnifiedEventBus()
        
        # 发布事件
        event_bus.publish("task.created", {"task_id": "task-001"})
        event_bus.publish("task.created", {"task_id": "task-002"})
        event_bus.publish("knowledge.added", {"knowledge_id": "knowledge-001"})
        
        # 查询事件
        task_events = event_bus.query_events("task.created")
        knowledge_events = event_bus.query_events("knowledge.added")
        
        # 验证
        self.assertEqual(len(task_events), 2)
        self.assertEqual(len(knowledge_events), 1)

def run_api_tests():
    """运行API测试"""
    # 创建测试加载器
    loader = unittest.TestLoader()
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试
    test_suite.addTests(loader.loadTestsFromTestCase(TestAPIEndpoints))
    test_suite.addTests(loader.loadTestsFromTestCase(TestUnifiedGatewayAPI))
    test_suite.addTests(loader.loadTestsFromTestCase(TestUnifiedInterfaceAPI))
    test_suite.addTests(loader.loadTestsFromTestCase(TestKnowledgeAPI))
    test_suite.addTests(loader.loadTestsFromTestCase(TestDataLayerAPI))
    test_suite.addTests(loader.loadTestsFromTestCase(TestEventBusAPI))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result

if __name__ == "__main__":
    print("=== 运行API测试 ===")
    result = run_api_tests()
    
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
