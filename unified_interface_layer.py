#!/usr/bin/env python3
"""
统一接口层
解决孤岛逻辑：统一接口标准化
"""

import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class UnifiedInterface:
    """统一接口"""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.endpoints = {}
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0
        }
    
    def register_endpoint(self, method: str, path: str, handler: Callable):
        """注册端点"""
        key = f"{method}:{path}"
        self.endpoints[key] = handler
    
    def handle_request(self, method: str, path: str, params: Optional[Dict] = None, body: Optional[Dict] = None) -> Dict[str, Any]:
        """处理请求"""
        import time
        start_time = time.time()
        
        # 更新指标
        self.metrics["total_requests"] += 1
        
        # 查找处理器
        key = f"{method}:{path}"
        handler = self.endpoints.get(key)
        
        if not handler:
            self.metrics["failed_requests"] += 1
            return {"error": "Endpoint not found", "status": 404}
        
        try:
            # 执行处理器
            result = handler(params or {}, body or {})
            
            # 更新指标
            response_time = time.time() - start_time
            self._update_response_time(response_time)
            self.metrics["successful_requests"] += 1
            
            return {"result": result, "status": 200}
            
        except Exception as e:
            self.metrics["failed_requests"] += 1
            return {"error": str(e), "status": 500}
    
    def _update_response_time(self, response_time: float):
        """更新响应时间"""
        total_time = self.metrics["average_response_time"] * (self.metrics["total_requests"] - 1)
        self.metrics["average_response_time"] = (total_time + response_time) / self.metrics["total_requests"]
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics

class UnifiedInterfaceRegistry:
    """统一接口注册表"""
    
    def __init__(self):
        self.interfaces = {}
        self.metrics = {
            "total_interfaces": 0,
            "total_endpoints": 0
        }
    
    def register_interface(self, interface: UnifiedInterface):
        """注册接口"""
        self.interfaces[interface.name] = interface
        self.metrics["total_interfaces"] += 1
        self.metrics["total_endpoints"] += len(interface.endpoints)
    
    def get_interface(self, name: str) -> Optional[UnifiedInterface]:
        """获取接口"""
        return self.interfaces.get(name)
    
    def list_interfaces(self) -> List[str]:
        """列出接口"""
        return list(self.interfaces.keys())
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics

class UnifiedInterfaceGateway:
    """统一接口网关"""
    
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.registry = UnifiedInterfaceRegistry()
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0
        }
    
    def register_interface(self, interface: UnifiedInterface):
        """注册接口"""
        self.registry.register_interface(interface)
    
    def start(self):
        """启动网关"""
        server = HTTPServer((self.host, self.port), UnifiedInterfaceHandler)
        print(f"Unified Interface Gateway running on {self.host}:{self.port}")
        server.serve_forever()
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return {
            "gateway": self.metrics,
            "registry": self.registry.get_metrics()
        }

class UnifiedInterfaceHandler(BaseHTTPRequestHandler):
    """统一接口处理器"""
    
    registry = None  # 接口注册表
    
    def do_GET(self):
        """处理GET请求"""
        path = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)
        
        # 路由到相应接口
        interface_name = path.split("/")[1] if len(path.split("/")) > 1 else ""
        interface = self.registry.get_interface(interface_name)
        
        if interface:
            result = interface.handle_request("GET", path, params)
            self._send_response(result)
        else:
            self._send_error(404, "Interface not found")
    
    def do_POST(self):
        """处理POST请求"""
        path = urlparse(self.path).path
        
        # 读取请求体
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        body_data = json.loads(body) if body else {}
        
        # 路由到相应接口
        interface_name = path.split("/")[1] if len(path.split("/")) > 1 else ""
        interface = self.registry.get_interface(interface_name)
        
        if interface:
            result = interface.handle_request("POST", path, body=body_data)
            self._send_response(result)
        else:
            self._send_error(404, "Interface not found")
    
    def _send_response(self, result: Dict[str, Any]):
        """发送响应"""
        status = result.get("status", 200)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
    
    def _send_error(self, code: int, message: str):
        """发送错误响应"""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode())

class TaskInterface:
    """任务接口"""
    
    def __init__(self, task_scheduler):
        self.task_scheduler = task_scheduler
        self.interface = UnifiedInterface("tasks", "1.0.0")
        self._register_endpoints()
    
    def _register_endpoints(self):
        """注册端点"""
        self.interface.register_endpoint("GET", "/tasks", self._list_tasks)
        self.interface.register_endpoint("POST", "/tasks", self._create_task)
        self.interface.register_endpoint("GET", "/tasks/{id}", self._get_task)
        self.interface.register_endpoint("POST", "/tasks/{id}/execute", self._execute_task)
    
    def _list_tasks(self, params: Dict, body: Dict) -> Dict[str, Any]:
        """列出任务"""
        tasks = self.task_scheduler.list_tasks()
        return {"tasks": tasks}
    
    def _create_task(self, params: Dict, body: Dict) -> Dict[str, Any]:
        """创建任务"""
        task_type = body.get("type")
        task_params = body.get("params", {})
        priority = body.get("priority", 2)
        
        task_id = self.task_scheduler.create_task(task_type, task_params, priority)
        return {"task_id": task_id, "status": "created"}
    
    def _get_task(self, params: Dict, body: Dict) -> Dict[str, Any]:
        """获取任务"""
        task_id = params.get("id", [None])[0]
        task = self.task_scheduler.get_task(task_id)
        
        if task:
            return task
        else:
            raise Exception("Task not found")
    
    def _execute_task(self, params: Dict, body: Dict) -> Dict[str, Any]:
        """执行任务"""
        task_id = params.get("id", [None])[0]
        result = self.task_scheduler.execute_task(task_id)
        return {"task_id": task_id, "result": result}

class KnowledgeInterface:
    """知识接口"""
    
    def __init__(self, knowledge_manager):
        self.knowledge_manager = knowledge_manager
        self.interface = UnifiedInterface("knowledge", "1.0.0")
        self._register_endpoints()
    
    def _register_endpoints(self):
        """注册端点"""
        self.interface.register_endpoint("GET", "/knowledge/search", self._search_knowledge)
        self.interface.register_endpoint("POST", "/knowledge", self._add_knowledge)
        self.interface.register_endpoint("GET", "/knowledge/{id}", self._get_knowledge)
    
    def _search_knowledge(self, params: Dict, body: Dict) -> Dict[str, Any]:
        """搜索知识"""
        query = params.get("q", [""])[0]
        top_k = int(params.get("top_k", ["5"])[0])
        
        results = self.knowledge_manager.search(query, top_k)
        return {"results": results, "query": query}
    
    def _add_knowledge(self, params: Dict, body: Dict) -> Dict[str, Any]:
        """添加知识"""
        knowledge_id = body.get("id")
        content = body.get("content")
        metadata = body.get("metadata", {})
        
        self.knowledge_manager.add_knowledge(knowledge_id, content, metadata)
        return {"id": knowledge_id, "status": "added"}
    
    def _get_knowledge(self, params: Dict, body: Dict) -> Dict[str, Any]:
        """获取知识"""
        knowledge_id = params.get("id", [None])[0]
        knowledge = self.knowledge_manager.get_knowledge(knowledge_id)
        
        if knowledge:
            return knowledge
        else:
            raise Exception("Knowledge not found")

class ExperienceInterface:
    """经验接口"""
    
    def __init__(self, experience_ratchet):
        self.experience_ratchet = experience_ratchet
        self.interface = UnifiedInterface("experience", "1.0.0")
        self._register_endpoints()
    
    def _register_endpoints(self):
        """注册端点"""
        self.interface.register_endpoint("GET", "/experience/search", self._search_experience)
        self.interface.register_endpoint("POST", "/experience", self._add_experience)
        self.interface.register_endpoint("GET", "/experience/{id}", self._get_experience)
        self.interface.register_endpoint("POST", "/experience/{id}/validate", self._validate_experience)
    
    def _search_experience(self, params: Dict, body: Dict) -> Dict[str, Any]:
        """搜索经验"""
        query = params.get("q", [""])[0]
        project = params.get("project", [None])[0]
        
        results = self.experience_ratchet.search_experience(query, project)
        return {"results": results, "query": query}
    
    def _add_experience(self, params: Dict, body: Dict) -> Dict[str, Any]:
        """添加经验"""
        experience_id = self.experience_ratchet.create_experience(body)
        return {"id": experience_id, "status": "created"}
    
    def _get_experience(self, params: Dict, body: Dict) -> Dict[str, Any]:
        """获取经验"""
        experience_id = params.get("id", [None])[0]
        experience = self.experience_ratchet.get_experience(experience_id)
        
        if experience:
            return experience
        else:
            raise Exception("Experience not found")
    
    def _validate_experience(self, params: Dict, body: Dict) -> Dict[str, Any]:
        """验证经验"""
        experience_id = params.get("id", [None])[0]
        evidence = body.get("evidence", "")
        
        success = self.experience_ratchet.validate_experience(experience_id, evidence)
        return {"id": experience_id, "validated": success}

# 使用示例
if __name__ == "__main__":
    # 创建接口网关
    gateway = UnifiedInterfaceGateway("0.0.0.0", 9000)
    
    # 注册接口（需要实际的组件实例）
    # task_interface = TaskInterface(task_scheduler)
    # knowledge_interface = KnowledgeInterface(knowledge_manager)
    # experience_interface = ExperienceInterface(experience_ratchet)
    
    # gateway.register_interface(task_interface.interface)
    # gateway.register_interface(knowledge_interface.interface)
    # gateway.register_interface(experience_interface.interface)
    
    # 启动网关
    gateway.start()
