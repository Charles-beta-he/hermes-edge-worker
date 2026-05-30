#!/usr/bin/env python3
"""
简化网关
整合核心组件
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class SimplifiedGatewayHandler(BaseHTTPRequestHandler):
    """简化网关处理器"""
    
    data_layer = None
    event_bus = None
    knowledge_manager = None
    rag_manager = None
    
    def do_GET(self):
        """处理GET请求"""
        path = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)
        
        if path == "/health":
            self._handle_health()
        elif path == "/search":
            self._handle_search(params)
        elif path == "/metrics":
            self._handle_metrics()
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
    
    def _handle_health(self):
        """健康检查"""
        self._send_json({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "data_layer": self.data_layer is not None,
                "event_bus": self.event_bus is not None,
                "knowledge_manager": self.knowledge_manager is not None,
                "rag_manager": self.rag_manager is not None
            }
        })
    
    def _handle_search(self, params: Dict):
        """搜索知识"""
        query = params.get("q", [""])[0]
        top_k = int(params.get("top_k", ["5"])[0])
        
        results = []
        if self.rag_manager:
            results = self.rag_manager.search(query, top_k)
        
        self._send_json({"results": results, "query": query})
    
    def _handle_search_post(self):
        """POST搜索"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            query = data.get("query", "")
            top_k = data.get("top_k", 5)
            
            results = []
            if self.rag_manager:
                results = self.rag_manager.search(query, top_k)
            
            self._send_json({"results": results, "query": query})
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_add_knowledge(self):
        """添加知识"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            knowledge_id = data.get("id")
            content = data.get("content")
            metadata = data.get("metadata", {})
            
            if self.rag_manager:
                self.rag_manager.add_knowledge(knowledge_id, content, metadata)
            
            self._send_json({"id": knowledge_id, "status": "added"})
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_metrics(self):
        """获取指标"""
        metrics = {}
        if self.data_layer:
            metrics["data_layer"] = self.data_layer.get_metrics()
        if self.event_bus:
            metrics["event_bus"] = self.event_bus.get_metrics()
        if self.rag_manager:
            metrics["rag_manager"] = self.rag_manager.get_metrics()
        
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

class SimplifiedGateway:
    """简化网关"""
    
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.components = {}
    
    def register_component(self, name: str, component):
        """注册组件"""
        self.components[name] = component
        
        if name == "data_layer":
            SimplifiedGatewayHandler.data_layer = component
        elif name == "event_bus":
            SimplifiedGatewayHandler.event_bus = component
        elif name == "knowledge_manager":
            SimplifiedGatewayHandler.knowledge_manager = component
        elif name == "rag_manager":
            SimplifiedGatewayHandler.rag_manager = component
    
    def start(self):
        """启动网关"""
        server = HTTPServer((self.host, self.port), SimplifiedGatewayHandler)
        print(f"Simplified Gateway running on {self.host}:{self.port}")
        server.serve_forever()
