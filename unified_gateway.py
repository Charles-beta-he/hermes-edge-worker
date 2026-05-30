#!/usr/bin/env python3
"""
统一网关
整合所有组件的统一入口
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class UnifiedGatewayHandler(BaseHTTPRequestHandler):
    """统一网关处理器"""
    
    # 组件引用
    task_scheduler = None
    knowledge_manager = None
    experience_ratchet = None
    rag_engine = None
    
    def do_GET(self):
        """处理GET请求"""
        path = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)
        
        if path == "/health":
            self._handle_health()
        elif path == "/status":
            self._handle_status()
        elif path == "/tasks":
            self._handle_list_tasks(params)
        elif path.startswith("/tasks/"):
            task_id = path.split("/")[-1]
            self._handle_get_task(task_id)
        elif path == "/knowledge/search":
            self._handle_search_knowledge(params)
        elif path == "/experience/search":
            self._handle_search_experience(params)
        elif path == "/experience/list":
            self._handle_list_experience(params)
        elif path == "/metrics":
            self._handle_get_metrics()
        else:
            self._send_error(404, "Not found")
    
    def do_POST(self):
        """处理POST请求"""
        path = urlparse(self.path).path
        
        if path == "/tasks":
            self._handle_create_task()
        elif path == "/tasks/execute":
            self._handle_execute_task()
        elif path == "/knowledge":
            self._handle_add_knowledge()
        elif path == "/experience":
            self._handle_add_experience()
        elif path == "/experience/validate":
            self._handle_validate_experience()
        elif path == "/search":
            self._handle_unified_search()
        else:
            self._send_error(404, "Not found")
    
    def _handle_health(self):
        """健康检查"""
        self._send_json({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "task_scheduler": self.task_scheduler is not None,
                "knowledge_manager": self.knowledge_manager is not None,
                "experience_ratchet": self.experience_ratchet is not None,
                "rag_engine": self.rag_engine is not None
            }
        })
    
    def _handle_status(self):
        """系统状态"""
        status = {
            "system": "unified_gateway",
            "version": "1.0.0",
            "uptime": datetime.now().isoformat(),
            "components": {}
        }
        
        # 任务调度器状态
        if self.task_scheduler:
            status["components"]["task_scheduler"] = {
                "status": "active",
                "metrics": self.task_scheduler.get_metrics() if hasattr(self.task_scheduler, 'get_metrics') else {}
            }
        
        # 知识管理器状态
        if self.knowledge_manager:
            status["components"]["knowledge_manager"] = {
                "status": "active",
                "metrics": self.knowledge_manager.get_metrics() if hasattr(self.knowledge_manager, 'get_metrics') else {}
            }
        
        # 经验积累器状态
        if self.experience_ratchet:
            status["components"]["experience_ratchet"] = {
                "status": "active",
                "metrics": self.experience_ratchet.get_metrics() if hasattr(self.experience_ratchet, 'get_metrics') else {}
            }
        
        # RAG引擎状态
        if self.rag_engine:
            status["components"]["rag_engine"] = {
                "status": "active",
                "metrics": self.rag_engine.get_metrics() if hasattr(self.rag_engine, 'get_metrics') else {}
            }
        
        self._send_json(status)
    
    def _handle_list_tasks(self, params: Dict):
        """列出任务"""
        if not self.task_scheduler:
            self._send_error(500, "Task scheduler not initialized")
            return
        
        status = params.get("status", [None])[0]
        tasks = self.task_scheduler.list_tasks() if hasattr(self.task_scheduler, 'list_tasks') else []
        
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        
        self._send_json({"tasks": tasks})
    
    def _handle_get_task(self, task_id: str):
        """获取任务"""
        if not self.task_scheduler:
            self._send_error(500, "Task scheduler not initialized")
            return
        
        task = self.task_scheduler.get_task(task_id)
        if task:
            self._send_json(task)
        else:
            self._send_error(404, "Task not found")
    
    def _handle_create_task(self):
        """创建任务"""
        if not self.task_scheduler:
            self._send_error(500, "Task scheduler not initialized")
            return
        
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            task_type = data.get("type")
            params = data.get("params", {})
            priority = data.get("priority", 2)
            
            task_id = self.task_scheduler.create_task(task_type, params, priority)
            self._send_json({"task_id": task_id, "status": "created"})
            
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_execute_task(self):
        """执行任务"""
        if not self.task_scheduler:
            self._send_error(500, "Task scheduler not initialized")
            return
        
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            task_id = data.get("task_id")
            if not task_id:
                self._send_error(400, "Missing task_id")
                return
            
            # 查询相关经验
            experience = None
            if self.experience_ratchet:
                task = self.task_scheduler.get_task(task_id)
                if task:
                    experience = self.experience_ratchet.query_experience(
                        task.get("project", ""),
                        task.get("type", "")
                    )
            
            # 执行任务
            result = self.task_scheduler.execute_task(task_id, experience)
            
            # 记录经验
            if self.experience_ratchet and result:
                self.experience_ratchet.record_experience(task_id, result)
            
            self._send_json({"task_id": task_id, "result": result})
            
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_search_knowledge(self, params: Dict):
        """搜索知识"""
        if not self.knowledge_manager:
            self._send_error(500, "Knowledge manager not initialized")
            return
        
        query = params.get("q", [""])[0]
        top_k = int(params.get("top_k", ["5"])[0])
        
        results = self.knowledge_manager.search(query, top_k)
        self._send_json({"results": results, "query": query})
    
    def _handle_search_experience(self, params: Dict):
        """搜索经验"""
        if not self.experience_ratchet:
            self._send_error(500, "Experience ratchet not initialized")
            return
        
        query = params.get("q", [""])[0]
        project = params.get("project", [None])[0]
        
        results = self.experience_ratchet.search_experience(query, project)
        self._send_json({"results": results, "query": query})
    
    def _handle_list_experience(self, params: Dict):
        """列出经验"""
        if not self.experience_ratchet:
            self._send_error(500, "Experience ratchet not initialized")
            return
        
        project = params.get("project", [None])[0]
        status = params.get("status", [None])[0]
        
        results = self.experience_ratchet.list_experience(project, status)
        self._send_json({"results": results})
    
    def _handle_add_knowledge(self):
        """添加知识"""
        if not self.knowledge_manager:
            self._send_error(500, "Knowledge manager not initialized")
            return
        
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            knowledge_id = data.get("id")
            content = data.get("content")
            metadata = data.get("metadata", {})
            
            if not knowledge_id or not content:
                self._send_error(400, "Missing id or content")
                return
            
            self.knowledge_manager.add_knowledge(knowledge_id, content, metadata)
            self._send_json({"id": knowledge_id, "status": "added"})
            
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_add_experience(self):
        """添加经验"""
        if not self.experience_ratchet:
            self._send_error(500, "Experience ratchet not initialized")
            return
        
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            experience_id = self.experience_ratchet.create_experience(data)
            self._send_json({"id": experience_id, "status": "created"})
            
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_validate_experience(self):
        """验证经验"""
        if not self.experience_ratchet:
            self._send_error(500, "Experience ratchet not initialized")
            return
        
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            experience_id = data.get("id")
            evidence = data.get("evidence", "")
            
            if not experience_id:
                self._send_error(400, "Missing id")
                return
            
            success = self.experience_ratchet.validate_experience(experience_id, evidence)
            self._send_json({"id": experience_id, "validated": success})
            
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_unified_search(self):
        """统一搜索"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            query = data.get("query", "")
            search_type = data.get("type", "all")
            top_k = data.get("top_k", 5)
            
            results = {}
            
            # 搜索知识
            if search_type in ["all", "knowledge"] and self.knowledge_manager:
                results["knowledge"] = self.knowledge_manager.search(query, top_k)
            
            # 搜索经验
            if search_type in ["all", "experience"] and self.experience_ratchet:
                results["experience"] = self.experience_ratchet.search_experience(query)
            
            # RAG搜索
            if search_type in ["all", "rag"] and self.rag_engine:
                results["rag"] = self.rag_engine.search(query, top_k)
            
            self._send_json({"results": results, "query": query})
            
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_get_metrics(self):
        """获取指标"""
        metrics = {
            "system": {
                "timestamp": datetime.now().isoformat(),
                "components": {}
            }
        }
        
        # 任务调度器指标
        if self.task_scheduler and hasattr(self.task_scheduler, 'get_metrics'):
            metrics["system"]["components"]["task_scheduler"] = self.task_scheduler.get_metrics()
        
        # 知识管理器指标
        if self.knowledge_manager and hasattr(self.knowledge_manager, 'get_metrics'):
            metrics["system"]["components"]["knowledge_manager"] = self.knowledge_manager.get_metrics()
        
        # 经验积累器指标
        if self.experience_ratchet and hasattr(self.experience_ratchet, 'get_metrics'):
            metrics["system"]["components"]["experience_ratchet"] = self.experience_ratchet.get_metrics()
        
        # RAG引擎指标
        if self.rag_engine and hasattr(self.rag_engine, 'get_metrics'):
            metrics["system"]["components"]["rag_engine"] = self.rag_engine.get_metrics()
        
        self._send_json(metrics)
    
    def _send_json(self, data: Dict):
        """发送JSON响应"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _send_error(self, code: int, message: str):
        """发送错误响应"""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode())

class UnifiedGateway:
    """统一网关"""
    
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.components = {}
    
    def register_component(self, name: str, component):
        """注册组件"""
        self.components[name] = component
        
        # 设置处理器组件
        if name == "task_scheduler":
            UnifiedGatewayHandler.task_scheduler = component
        elif name == "knowledge_manager":
            UnifiedGatewayHandler.knowledge_manager = component
        elif name == "experience_ratchet":
            UnifiedGatewayHandler.experience_ratchet = component
        elif name == "rag_engine":
            UnifiedGatewayHandler.rag_engine = component
    
    def start(self):
        """启动网关"""
        server = HTTPServer((self.host, self.port), UnifiedGatewayHandler)
        print(f"Unified Gateway running on {self.host}:{self.port}")
        print(f"Registered components: {list(self.components.keys())}")
        server.serve_forever()

# 使用示例
if __name__ == "__main__":
    # 创建网关
    gateway = UnifiedGateway("0.0.0.0", 9000)
    
    # 注册组件（这里需要实际的组件实例）
    # gateway.register_component("task_scheduler", task_scheduler)
    # gateway.register_component("knowledge_manager", knowledge_manager)
    # gateway.register_component("experience_ratchet", experience_ratchet)
    # gateway.register_component("rag_engine", rag_engine)
    
    # 启动网关
    gateway.start()
