#!/usr/bin/env python3
"""
统一API接口
唯一事实源原则：本地大脑作为唯一事实源
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class UnifiedAPIHandler(BaseHTTPRequestHandler):
    """统一API处理器"""
    
    unified_pool: Optional['UnifiedTaskPool'] = None  # 统一任务池
    
    def do_GET(self):
        """处理GET请求"""
        path = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)
        
        if path == "/health":
            self._handle_health()
        elif path == "/tasks":
            self._handle_list_tasks(params)
        elif path.startswith("/tasks/"):
            task_id = path.split("/")[-1]
            self._handle_get_task(task_id)
        elif path == "/metrics":
            self._handle_get_metrics()
        else:
            self._send_error(404, "Not found")
    
    def do_POST(self):
        """处理POST请求"""
        path = urlparse(self.path).path
        
        if path == "/tasks":
            self._handle_create_task()
        elif path.startswith("/tasks/") and path.endswith("/result"):
            task_id = path.split("/")[-2]
            self._handle_update_task_result(task_id)
        else:
            self._send_error(404, "Not found")
    
    def _handle_health(self):
        """健康检查"""
        self._send_json({"status": "ok", "timestamp": datetime.now().isoformat()})
    
    def _handle_list_tasks(self, params: Dict):
        """列出任务"""
        if not self.unified_pool:
            self._send_error(500, "Unified pool not initialized")
            return
        
        status = params.get("status", [None])[0]
        tasks = self.unified_pool.list_tasks()
        
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        
        self._send_json({"tasks": tasks})
    
    def _handle_get_task(self, task_id: str):
        """获取任务"""
        if not self.unified_pool:
            self._send_error(500, "Unified pool not initialized")
            return
        
        task = self.unified_pool.get_task(task_id)
        if task:
            self._send_json(task)
        else:
            self._send_error(404, "Task not found")
    
    def _handle_create_task(self):
        """创建任务"""
        if not self.unified_pool:
            self._send_error(500, "Unified pool not initialized")
            return
        
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            task_type = data.get("type")
            params = data.get("params", {})
            priority = data.get("priority", 2)
            
            from unified_task_pool import TaskPriority
            priority_enum = TaskPriority(priority)
            
            task_id = self.unified_pool.add_task(task_type, params, priority_enum)
            
            self._send_json({"task_id": task_id, "status": "created"})
            
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_update_task_result(self, task_id: str):
        """更新任务结果"""
        if not self.unified_pool:
            self._send_error(500, "Unified pool not initialized")
            return
        
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            result = data.get("result")
            status = data.get("status", "completed")
            
            from unified_task_pool import TaskStatus
            status_enum = TaskStatus(status)
            
            self.unified_pool.update_task_status(task_id, status_enum, result)
            
            self._send_json({"status": "updated"})
            
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_get_metrics(self):
        """获取指标"""
        if not self.unified_pool:
            self._send_error(500, "Unified pool not initialized")
            return
        
        metrics = self.unified_pool.get_metrics()
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

class UnifiedAPIServer:
    """统一API服务器"""
    
    def __init__(self, host: str, port: int, unified_pool):
        self.host = host
        self.port = port
        self.unified_pool = unified_pool
        
        # 设置处理器
        UnifiedAPIHandler.unified_pool = unified_pool
    
    def start(self):
        """启动服务器"""
        server = HTTPServer((self.host, self.port), UnifiedAPIHandler)
        print(f"Unified API server running on {self.host}:{self.port}")
        server.serve_forever()

# 使用示例
if __name__ == "__main__":
    from unified_task_pool import UnifiedTaskPool
    
    # 创建统一任务池
    pool = UnifiedTaskPool()
    
    # 创建API服务器
    server = UnifiedAPIServer("0.0.0.0", 9003, pool)
    
    # 启动服务器
    server.start()
