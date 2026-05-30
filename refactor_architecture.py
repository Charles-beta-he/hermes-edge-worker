#!/usr/bin/env python3
"""
架构重构脚本
简化架构，移除未使用组件
"""

import os
import shutil
from datetime import datetime

class ArchitectureRefactor:
    """架构重构"""
    
    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.core_components = [
            "unified_data_layer.py",
            "knowledge_manager.py",
            "unified_event_bus.py",
            "rag_knowledge_manager.py",
            "edge_worker.py"
        ]
        self.deprecated_components = [
            "agent_team.py",
            "edge_worker_executor.py",
            "fault_tolerance.py",
            "hermes_lan.py",
            "load_balancer.py",
            "multi_model_analyzer.py",
            "task_pool.py",
            "task_scheduler.py",
            "tree_cache.py",
            "unified_api.py",
            "unified_manager.py"
        ]
    
    def analyze(self):
        """分析架构"""
        print("=== 架构分析 ===")
        
        # 检查核心组件
        print("\n核心组件:")
        for component in self.core_components:
            path = os.path.join(self.project_dir, component)
            if os.path.exists(path):
                size = os.path.getsize(path)
                print(f"  ✓ {component} ({size} bytes)")
            else:
                print(f"  ✗ {component} (缺失)")
        
        # 检查废弃组件
        print("\n废弃组件（可移除）:")
        for component in self.deprecated_components:
            path = os.path.join(self.project_dir, component)
            if os.path.exists(path):
                size = os.path.getsize(path)
                print(f"  - {component} ({size} bytes)")
    
    def create_simplified_architecture(self):
        """创建简化架构"""
        print("\n=== 创建简化架构 ===")
        
        # 创建简化架构目录
        simplified_dir = os.path.join(self.project_dir, "simplified")
        os.makedirs(simplified_dir, exist_ok=True)
        
        # 复制核心组件
        for component in self.core_components:
            src = os.path.join(self.project_dir, component)
            dst = os.path.join(simplified_dir, component)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"  复制: {component}")
        
        # 创建简化网关
        self._create_simplified_gateway(simplified_dir)
        
        # 创建简化API
        self._create_simplified_api(simplified_dir)
        
        # 创建部署脚本
        self._create_deployment_script(simplified_dir)
        
        print(f"\n简化架构已创建: {simplified_dir}")
    
    def _create_simplified_gateway(self, output_dir: str):
        """创建简化网关"""
        gateway_code = '''#!/usr/bin/env python3
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
'''
        
        filepath = os.path.join(output_dir, "simplified_gateway.py")
        with open(filepath, 'w') as f:
            f.write(gateway_code)
        print(f"  创建: simplified_gateway.py")
    
    def _create_simplified_api(self, output_dir: str):
        """创建简化API"""
        api_code = '''#!/usr/bin/env python3
"""
简化API
统一接口
"""

import json
from typing import Dict, Any, List
from datetime import datetime

class SimplifiedAPI:
    """简化API"""
    
    def __init__(self, data_layer, event_bus, knowledge_manager, rag_manager):
        self.data_layer = data_layer
        self.event_bus = event_bus
        self.knowledge_manager = knowledge_manager
        self.rag_manager = rag_manager
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索知识"""
        results = []
        
        # 搜索RAG
        if self.rag_manager:
            rag_results = self.rag_manager.search(query, top_k)
            results.extend(rag_results)
        
        # 搜索知识管理器
        if self.knowledge_manager:
            knowledge_results = self.knowledge_manager.search_experience(query, top_k)
            results.extend(knowledge_results)
        
        return results[:top_k]
    
    def add_knowledge(self, knowledge_id: str, content: str, metadata: Dict[str, Any] = None):
        """添加知识"""
        # 添加到RAG
        if self.rag_manager:
            self.rag_manager.add_knowledge(knowledge_id, content, metadata)
        
        # 添加到数据层
        if self.data_layer:
            self.data_layer.store("knowledge", knowledge_id, {
                "content": content,
                "metadata": metadata or {}
            })
        
        # 发布事件
        if self.event_bus:
            self.event_bus.publish("knowledge.added", {
                "knowledge_id": knowledge_id,
                "content": content
            })
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        metrics = {}
        
        if self.data_layer:
            metrics["data_layer"] = self.data_layer.get_metrics()
        if self.event_bus:
            metrics["event_bus"] = self.event_bus.get_metrics()
        if self.rag_manager:
            metrics["rag_manager"] = self.rag_manager.get_metrics()
        
        return metrics
'''
        
        filepath = os.path.join(output_dir, "simplified_api.py")
        with open(filepath, 'w') as f:
            f.write(api_code)
        print(f"  创建: simplified_api.py")
    
    def _create_deployment_script(self, output_dir: str):
        """创建部署脚本"""
        deploy_script = '''#!/bin/bash
# 简化架构部署脚本

set -e

echo "=== 部署简化架构 ==="

# 1. 检查Python
if ! command -v python3 &>/dev/null; then
    echo "需要Python 3.8+"
    exit 1
fi

# 2. 安装依赖
echo "安装依赖..."
pip3 install scikit-learn --quiet

# 3. 启动服务
echo "启动服务..."
python3 simplified_gateway.py --host 0.0.0.0 --port 9000

echo "部署完成"
'''
        
        filepath = os.path.join(output_dir, "deploy.sh")
        with open(filepath, 'w') as f:
            f.write(deploy_script)
        os.chmod(filepath, 0o755)
        print(f"  创建: deploy.sh")

def main():
    """主函数"""
    project_dir = "/Users/charles/hermes-edge-worker"
    
    # 创建重构器
    refactor = ArchitectureRefactor(project_dir)
    
    # 分析架构
    refactor.analyze()
    
    # 创建简化架构
    refactor.create_simplified_architecture()
    
    print("\n=== 重构完成 ===")

if __name__ == "__main__":
    main()
