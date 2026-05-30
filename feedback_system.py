#!/usr/bin/env python3
"""
用户反馈机制
中期计划：收集反馈，迭代改进
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class FeedbackCollector:
    """反馈收集器"""
    
    def __init__(self, storage_dir: str = "/tmp/feedback"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.feedback_list = []
    
    def submit_feedback(self, user_id: str, feedback_type: str, 
                       content: str, metadata: Dict[str, Any] = None) -> str:
        """提交反馈"""
        feedback_id = f"feedback-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        feedback = {
            "id": feedback_id,
            "user_id": user_id,
            "type": feedback_type,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }
        
        # 存储反馈
        self.feedback_list.append(feedback)
        self._persist_feedback(feedback)
        
        return feedback_id
    
    def get_feedback(self, feedback_id: str) -> Dict[str, Any]:
        """获取反馈"""
        for feedback in self.feedback_list:
            if feedback["id"] == feedback_id:
                return feedback
        return None
    
    def list_feedback(self, feedback_type: str = None, 
                     status: str = None) -> List[Dict[str, Any]]:
        """列出反馈"""
        results = []
        for feedback in self.feedback_list:
            if feedback_type and feedback["type"] != feedback_type:
                continue
            if status and feedback["status"] != status:
                continue
            results.append(feedback)
        return results
    
    def update_feedback_status(self, feedback_id: str, status: str) -> bool:
        """更新反馈状态"""
        for feedback in self.feedback_list:
            if feedback["id"] == feedback_id:
                feedback["status"] = status
                feedback["updated_at"] = datetime.now().isoformat()
                self._persist_feedback(feedback)
                return True
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self.feedback_list)
        by_type = {}
        by_status = {}
        
        for feedback in self.feedback_list:
            # 按类型统计
            feedback_type = feedback["type"]
            by_type[feedback_type] = by_type.get(feedback_type, 0) + 1
            
            # 按状态统计
            status = feedback["status"]
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total": total,
            "by_type": by_type,
            "by_status": by_status
        }
    
    def _persist_feedback(self, feedback: Dict[str, Any]):
        """持久化反馈"""
        filepath = os.path.join(self.storage_dir, f"{feedback['id']}.json")
        with open(filepath, 'w') as f:
            json.dump(feedback, f, indent=2)

class FeedbackAPIHandler(BaseHTTPRequestHandler):
    """反馈API处理器"""
    
    feedback_collector = None
    
    def do_GET(self):
        """处理GET请求"""
        path = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)
        
        if path == "/feedback":
            self._handle_list_feedback(params)
        elif path.startswith("/feedback/"):
            feedback_id = path.split("/")[-1]
            self._handle_get_feedback(feedback_id)
        elif path == "/feedback/statistics":
            self._handle_statistics()
        else:
            self._send_error(404, "Not found")
    
    def do_POST(self):
        """处理POST请求"""
        path = urlparse(self.path).path
        
        if path == "/feedback":
            self._handle_submit_feedback()
        elif path.startswith("/feedback/") and path.endswith("/status"):
            feedback_id = path.split("/")[-2]
            self._handle_update_status(feedback_id)
        else:
            self._send_error(404, "Not found")
    
    def _handle_list_feedback(self, params: Dict):
        """列出反馈"""
        feedback_type = params.get("type", [None])[0]
        status = params.get("status", [None])[0]
        
        feedback_list = self.feedback_collector.list_feedback(feedback_type, status)
        self._send_json({"feedback": feedback_list})
    
    def _handle_get_feedback(self, feedback_id: str):
        """获取反馈"""
        feedback = self.feedback_collector.get_feedback(feedback_id)
        if feedback:
            self._send_json(feedback)
        else:
            self._send_error(404, "Feedback not found")
    
    def _handle_submit_feedback(self):
        """提交反馈"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            user_id = data.get("user_id", "anonymous")
            feedback_type = data.get("type", "general")
            content = data.get("content", "")
            metadata = data.get("metadata", {})
            
            feedback_id = self.feedback_collector.submit_feedback(
                user_id, feedback_type, content, metadata
            )
            
            self._send_json({"id": feedback_id, "status": "submitted"})
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_update_status(self, feedback_id: str):
        """更新状态"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            status = data.get("status")
            success = self.feedback_collector.update_feedback_status(feedback_id, status)
            
            if success:
                self._send_json({"id": feedback_id, "status": status})
            else:
                self._send_error(404, "Feedback not found")
        except Exception as e:
            self._send_error(400, str(e))
    
    def _handle_statistics(self):
        """获取统计"""
        stats = self.feedback_collector.get_statistics()
        self._send_json(stats)
    
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

class FeedbackAPIServer:
    """反馈API服务器"""
    
    def __init__(self, host: str, port: int, feedback_collector: FeedbackCollector):
        self.host = host
        self.port = port
        self.feedback_collector = feedback_collector
        
        FeedbackAPIHandler.feedback_collector = feedback_collector
    
    def start(self):
        """启动服务器"""
        server = HTTPServer((self.host, self.port), FeedbackAPIHandler)
        print(f"Feedback API running on {self.host}:{self.port}")
        server.serve_forever()

# 使用示例
if __name__ == "__main__":
    # 创建反馈收集器
    collector = FeedbackCollector()
    
    # 提交反馈
    feedback_id = collector.submit_feedback(
        user_id="user-001",
        feedback_type="bug",
        content="系统响应时间过长",
        metadata={"component": "data_layer", "severity": "high"}
    )
    
    print(f"反馈已提交: {feedback_id}")
    
    # 获取统计
    stats = collector.get_statistics()
    print(f"统计: {stats}")
