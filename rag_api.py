#!/usr/bin/env python3
"""
RAG知识管理系统API
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class RAGAPIHandler(BaseHTTPRequestHandler):
    """RAG API处理器"""
    
    rag_manager = None  # RAG管理器
    
    def do_GET(self):
        """处理GET请求"""
        path = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)
        
        if path == "/health":
            self._handle_health()
        elif path == "/search":
            self._handle_search(params)
        elif path == "/knowledge":
            self._handle_list_knowledge()
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
        
        if path == "/knowledge":
            self._handle_add_knowledge()
        elif path == "/search":
            self._handle_search_post()
        else:
            self._send_error(404, "Not found")
    
    def do_DELETE(self):
        """处理DELETE请求"""
        path = urlparse(self.path).path
        
        if path.startswith("/knowledge/"):
            knowledge_id = path.split("/")[-1]
            self._handle_delete_knowledge(knowledge_id)
        else:
            self._send_error(404, "Not found")
    
    def _handle_health(self):
        """健康检查"""
        self._send_json({"status": "ok", "timestamp": datetime.now().isoformat()})
    
    def _handle_search(self, params: Dict):
        """搜索知识"""
        if not self.rag_manager:
            self._send_error(500, "RAG manager not initialized")
            return
        
        query = params.get("q", [""])[0]
        top_k = int(params.get("top_k", ["5"])[0])
        
        results = self.rag_manager.search(query, top_k)
        self._send_json({"results": results, "query": query})
    
    def _handle_search_post(self):
        """POST搜索知识"""
        if not self.rag_manager:
            self._send_error(500, "RAG manager not initialized")
            return
        
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            query = data.get("query", "")
            top_k = data.get("top_k", 5)
            
            results = self.rag_manager.search(query, top_k)
            self._send_json({"results": results, "query": query})
            
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_list_knowledge(self):
        """列出知识"""
        if not self.rag_manager:
            self._send_error(500, "RAG manager not initialized")
            return
        
        knowledge_list = self.rag_manager.list_knowledge()
        self._send_json({"knowledge": knowledge_list})
    
    def _handle_get_knowledge(self, knowledge_id: str):
        """获取知识"""
        if not self.rag_manager:
            self._send_error(500, "RAG manager not initialized")
            return
        
        knowledge = self.rag_manager.get_knowledge(knowledge_id)
        if knowledge:
            self._send_json(knowledge)
        else:
            self._send_error(404, "Knowledge not found")
    
    def _handle_add_knowledge(self):
        """添加知识"""
        if not self.rag_manager:
            self._send_error(500, "RAG manager not initialized")
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
            
            self.rag_manager.add_knowledge(knowledge_id, content, metadata)
            self._send_json({"id": knowledge_id, "status": "added"})
            
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_delete_knowledge(self, knowledge_id: str):
        """删除知识"""
        if not self.rag_manager:
            self._send_error(500, "RAG manager not initialized")
            return
        
        success = self.rag_manager.delete_knowledge(knowledge_id)
        if success:
            self._send_json({"id": knowledge_id, "status": "deleted"})
        else:
            self._send_error(404, "Knowledge not found")
    
    def _handle_get_metrics(self):
        """获取指标"""
        if not self.rag_manager:
            self._send_error(500, "RAG manager not initialized")
            return
        
        metrics = self.rag_manager.get_metrics()
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

class RAGAPIServer:
    """RAG API服务器"""
    
    def __init__(self, host: str, port: int, rag_manager):
        self.host = host
        self.port = port
        self.rag_manager = rag_manager
        
        # 设置处理器
        RAGAPIHandler.rag_manager = rag_manager
    
    def start(self):
        """启动服务器"""
        server = HTTPServer((self.host, self.port), RAGAPIHandler)
        print(f"RAG API server running on {self.host}:{self.port}")
        server.serve_forever()

# 使用示例
if __name__ == "__main__":
    from rag_knowledge_manager import RAGKnowledgeManager
    
    # 创建RAG管理器
    manager = RAGKnowledgeManager()
    
    # 创建API服务器
    server = RAGAPIServer("0.0.0.0", 9005, manager)
    
    # 启动服务器
    server.start()
