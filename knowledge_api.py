#!/usr/bin/env python3
"""
知识管理系统API
本地大脑的知识层
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class KnowledgeAPIHandler(BaseHTTPRequestHandler):
    """知识API处理器"""
    
    knowledge_manager = None  # 知识管理器
    
    def do_GET(self):
        """处理GET请求"""
        path = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)
        
        if path == "/health":
            self._handle_health()
        elif path == "/search":
            self._handle_search(params)
        elif path == "/recommend":
            self._handle_recommend(params)
        elif path == "/list":
            self._handle_list(params)
        elif path.startswith("/knowledge/"):
            knowledge_id = path.split("/")[-1]
            self._handle_get_knowledge(knowledge_id)
        elif path == "/metrics":
            self._handle_get_metrics()
        else:
            self._send_error(404, "Not found")
    
    def do_POST(self):
        """处理POST请求"""
        path = urlparse(self.path).path
        
        if path == "/experience":
            self._handle_record_experience()
        elif path == "/function":
            self._handle_record_function()
        elif path == "/workflow":
            self._handle_record_workflow()
        elif path == "/decision":
            self._handle_record_decision()
        else:
            self._send_error(404, "Not found")
    
    def _handle_health(self):
        """健康检查"""
        self._send_json({"status": "ok", "timestamp": datetime.now().isoformat()})
    
    def _handle_search(self, params: Dict):
        """搜索知识"""
        if not self.knowledge_manager:
            self._send_error(500, "Knowledge manager not initialized")
            return
        
        query = params.get("q", [""])[0]
        knowledge_type = params.get("type", [None])[0]
        top_k = int(params.get("top_k", ["5"])[0])
        
        if knowledge_type == "experience":
            results = self.knowledge_manager.search_experience(query, top_k)
        elif knowledge_type == "function":
            results = self.knowledge_manager.search_function(query, top_k)
        elif knowledge_type == "workflow":
            results = self.knowledge_manager.search_workflow(query, top_k)
        elif knowledge_type == "decision":
            results = self.knowledge_manager.search_decision(query, top_k)
        else:
            results = self.knowledge_manager.search_all(query, top_k)
        
        self._send_json({"results": results, "query": query})
    
    def _handle_recommend(self, params: Dict):
        """推荐知识"""
        if not self.knowledge_manager:
            self._send_error(500, "Knowledge manager not initialized")
            return
        
        context = params.get("context", ["{}"])[0]
        top_k = int(params.get("top_k", ["5"])[0])
        
        try:
            context_dict = json.loads(context)
            results = self.knowledge_manager.recommend_knowledge(context_dict, top_k)
            self._send_json({"results": results, "context": context_dict})
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_list(self, params: Dict):
        """列出知识"""
        if not self.knowledge_manager:
            self._send_error(500, "Knowledge manager not initialized")
            return
        
        knowledge_type = params.get("type", [None])[0]
        tags = params.get("tags", [None])[0]
        
        from knowledge_manager import KnowledgeType
        
        if knowledge_type == "experience":
            type_enum = KnowledgeType.EXPERIENCE
        elif knowledge_type == "function":
            type_enum = KnowledgeType.FUNCTION
        elif knowledge_type == "workflow":
            type_enum = KnowledgeType.WORKFLOW
        elif knowledge_type == "decision":
            type_enum = KnowledgeType.DECISION
        else:
            type_enum = None
        
        tags_list = tags.split(",") if tags else None
        
        results = self.knowledge_manager.list_knowledge(type_enum, tags_list)
        self._send_json({"results": results})
    
    def _handle_get_knowledge(self, knowledge_id: str):
        """获取知识"""
        if not self.knowledge_manager:
            self._send_error(500, "Knowledge manager not initialized")
            return
        
        knowledge = self.knowledge_manager.get_knowledge(knowledge_id)
        if knowledge:
            self._send_json(knowledge)
        else:
            self._send_error(404, "Knowledge not found")
    
    def _handle_get_metrics(self):
        """获取指标"""
        if not self.knowledge_manager:
            self._send_error(500, "Knowledge manager not initialized")
            return
        
        metrics = self.knowledge_manager.get_metrics()
        self._send_json(metrics)
    
    def _handle_record_experience(self):
        """记录经验"""
        if not self.knowledge_manager:
            self._send_error(500, "Knowledge manager not initialized")
            return
        
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            knowledge_id = self.knowledge_manager.record_experience(data)
            self._send_json({"id": knowledge_id, "status": "recorded"})
            
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_record_function(self):
        """记录功能"""
        if not self.knowledge_manager:
            self._send_error(500, "Knowledge manager not initialized")
            return
        
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            knowledge_id = self.knowledge_manager.record_function(data)
            self._send_json({"id": knowledge_id, "status": "recorded"})
            
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_record_workflow(self):
        """记录流程"""
        if not self.knowledge_manager:
            self._send_error(500, "Knowledge manager not initialized")
            return
        
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            knowledge_id = self.knowledge_manager.record_workflow(data)
            self._send_json({"id": knowledge_id, "status": "recorded"})
            
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_record_decision(self):
        """记录决策"""
        if not self.knowledge_manager:
            self._send_error(500, "Knowledge manager not initialized")
            return
        
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            knowledge_id = self.knowledge_manager.record_decision(data)
            self._send_json({"id": knowledge_id, "status": "recorded"})
            
        except Exception as e:
            self._send_error(400, str(e))
    
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

class KnowledgeAPIServer:
    """知识API服务器"""
    
    def __init__(self, host: str, port: int, knowledge_manager):
        self.host = host
        self.port = port
        self.knowledge_manager = knowledge_manager
        
        # 设置处理器
        KnowledgeAPIHandler.knowledge_manager = knowledge_manager
    
    def start(self):
        """启动服务器"""
        server = HTTPServer((self.host, self.port), KnowledgeAPIHandler)
        print(f"Knowledge API server running on {self.host}:{self.port}")
        server.serve_forever()

# 使用示例
if __name__ == "__main__":
    from knowledge_manager import KnowledgeManager
    
    # 创建知识管理器
    manager = KnowledgeManager()
    
    # 创建API服务器
    server = KnowledgeAPIServer("0.0.0.0", 9004, manager)
    
    # 启动服务器
    server.start()
