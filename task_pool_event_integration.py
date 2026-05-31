#!/usr/bin/env python3
"""
任务池事件驱动集成
将事件驱动与任务池集成
"""

import json
import os
import sys
import subprocess
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

class TaskPoolEventIntegration:
    """任务池事件驱动集成"""
    
    def __init__(self, event_store_path: Optional[Path] = None, max_retries: int = 2):
        self.orchestrator_path = Path.home() / ".hermes" / "scripts" / "brain_task_orchestrator.py"
        self.dispatch_tick_path = Path.home() / ".hermes" / "scripts" / "brain_task_dispatch_tick.py"
        self.event_driven_path = SCRIPT_DIR / "task_event_driven.py"
        self.event_store_path = Path(event_store_path) if event_store_path else SCRIPT_DIR / "event_store.jsonl"
        self.max_retries = max(0, int(max_retries))
        self.processed_event_ids = set()
        self.dead_letters: List[Dict[str, Any]] = []
        
        self.metrics = {
            "tasks_processed": 0,
            "tasks_auto_claimed": 0,
            "tasks_auto_executed": 0,
            "duplicates": 0,
            "dead_letters": 0,
            "errors": 0
        }
    
    def process_task_event(self, event_type: str, event_data: Dict[str, Any]):
        """处理任务事件，返回与 9007 一致的可靠 envelope。"""
        event_data = event_data or {}
        event_id = event_data.get("event_id") or self._derive_event_id(event_type, event_data)
        task_id = event_data.get("task_id", "")
        print(f"[集成] 处理事件: {event_type}, 任务: {task_id}, event_id: {event_id}")

        if event_id in self.processed_event_ids:
            self.metrics["duplicates"] += 1
            result = {"status": "duplicate", "event_id": event_id, "event_type": event_type, "task_id": task_id}
            self._record_event(event_id, event_type, event_data, "duplicate", 0, None)
            return result

        last_error = None
        for attempt in range(1, self.max_retries + 2):
            try:
                self._dispatch_event(event_type, event_data)
                self.processed_event_ids.add(event_id)
                self.metrics["tasks_processed"] += 1
                self._record_event(event_id, event_type, event_data, "processed", attempt, None)
                return {"status": "processed", "event_id": event_id, "event_type": event_type, "task_id": task_id, "attempts": attempt}
            except Exception as e:
                last_error = str(e)
                self.metrics["errors"] += 1
                print(f"[错误] 处理事件失败: {event_type}, attempt={attempt}, 错误: {e}")
                if attempt <= self.max_retries:
                    self._record_event(event_id, event_type, event_data, "failed_attempt", attempt, last_error)
                    time.sleep(0.01)
                    continue
                dead_letter = {"event_id": event_id, "event_type": event_type, "event_data": event_data, "error": last_error}
                self.dead_letters.append(dead_letter)
                self.metrics["dead_letters"] += 1
                self._record_event(event_id, event_type, event_data, "dead_lettered", attempt, last_error)
                return {"status": "dead_lettered", "event_id": event_id, "event_type": event_type, "task_id": task_id, "error": last_error, "attempts": attempt}

    def _derive_event_id(self, event_type: str, event_data: Dict[str, Any]) -> str:
        task_id = event_data.get("task_id", "unknown")
        key_status = event_data.get("new_status") or event_data.get("new_priority") or event_data.get("priority") or "none"
        return f"{event_type}:{task_id}:{key_status}"

    def _record_event(self, event_id: str, event_type: str, event_data: Dict[str, Any], status: str, attempt: int, error: Optional[str]):
        self.event_store_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_id": event_id,
            "event_type": event_type,
            "event_data": event_data,
            "status": status,
            "attempt": attempt,
            "error": error,
        }
        with self.event_store_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _dispatch_event(self, event_type: str, event_data: Dict[str, Any]):
        if event_type == "task.created":
            self.on_task_created(event_data)
        elif event_type == "task.status_changed":
            self.on_task_status_changed(event_data)
        elif event_type == "task.dependency_met":
            self.on_task_dependency_met(event_data)
        elif event_type == "task.priority_changed":
            self.on_task_priority_changed(event_data)
    
    def on_task_created(self, event_data: Dict[str, Any]):
        """任务创建时触发"""
        task_id = event_data.get("task_id", "")
        priority = event_data.get("priority", "P2")
        
        print(f"[事件] 任务创建: {task_id}, 优先级: {priority}")
        
        # 高优先级任务立即认领
        if priority in ["P0", "P1"]:
            self.auto_claim(task_id)
    
    def on_task_status_changed(self, event_data: Dict[str, Any]):
        """任务状态变更时触发"""
        task_id = event_data.get("task_id", "")
        old_status = event_data.get("old_status")
        new_status = event_data.get("new_status")
        
        print(f"[事件] 任务状态变更: {task_id}, {old_status} -> {new_status}")
        
        # 状态变为pending时自动认领
        if new_status == "pending":
            self.auto_claim(task_id)
        
        # 状态变为claimed时自动执行
        if new_status == "claimed":
            self.auto_execute(task_id)
    
    def on_task_dependency_met(self, event_data: Dict[str, Any]):
        """任务依赖满足时触发"""
        task_id = event_data.get("task_id", "")
        
        print(f"[事件] 任务依赖满足: {task_id}")
        
        # 自动认领
        self.auto_claim(task_id)
    
    def on_task_priority_changed(self, event_data: Dict[str, Any]):
        """任务优先级变更时触发"""
        task_id = event_data.get("task_id", "")
        new_priority = event_data.get("new_priority")
        
        print(f"[事件] 任务优先级变更: {task_id}, 新优先级: {new_priority}")
        
        # 高优先级任务立即认领
        if new_priority in ["P0", "P1"]:
            self.auto_claim(task_id)
    
    def auto_claim(self, task_id: str):
        """自动认领"""
        try:
            # 调用brain_task_orchestrator.py claim
            cmd = [
                sys.executable,
                str(self.orchestrator_path),
                "claim",
                task_id,
                "--json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"[自动] 认领成功: {task_id}")
                self.metrics["tasks_auto_claimed"] += 1
                
                # 触发执行
                self.auto_execute(task_id)
            else:
                print(f"[错误] 认领失败: {task_id}, 错误: {result.stderr}")
                self.metrics["errors"] += 1
        except Exception as e:
            print(f"[错误] 自动认领异常: {task_id}, 错误: {e}")
            self.metrics["errors"] += 1
    
    def auto_execute(self, task_id: str):
        """自动执行"""
        try:
            # 调用brain_task_orchestrator.py autorun-runner
            cmd = [
                sys.executable,
                str(self.orchestrator_path),
                "autorun-runner",
                "--task", task_id,
                "--json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"[自动] 执行成功: {task_id}")
                self.metrics["tasks_auto_executed"] += 1
            else:
                print(f"[错误] 执行失败: {task_id}, 错误: {result.stderr}")
                self.metrics["errors"] += 1
        except Exception as e:
            print(f"[错误] 自动执行异常: {task_id}, 错误: {e}")
            self.metrics["errors"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics

class TaskPoolEventAPI:
    """任务池事件驱动API"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 9008):
        self.host = host
        self.port = port
        self.integration = TaskPoolEventIntegration()
    
    def start(self):
        """启动API"""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        
        class EventHandler(BaseHTTPRequestHandler):
            integration = self.integration
            
            def do_POST(self):
                """处理POST请求"""
                if self.path == "/event":
                    try:
                        content_length = int(self.headers.get("Content-Length", 0))
                        body = self.rfile.read(content_length)
                        data = json.loads(body)
                        
                        event_type = data.get("event_type")
                        event_data = data.get("event_data", {})
                        
                        # 处理事件
                        result = self.integration.process_task_event(event_type, event_data)
                        
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
                    except Exception as e:
                        self.send_response(500)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": str(e)}).encode())
                else:
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Not found"}).encode())
            
            def do_GET(self):
                """处理GET请求"""
                if self.path == "/metrics":
                    metrics = self.integration.get_metrics()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(metrics).encode())
                elif self.path == "/health":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "ok"}).encode())
                else:
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Not found"}).encode())
        
        # 启动服务器
        server = HTTPServer((self.host, self.port), EventHandler)
        print(f"Task Pool Event API running on {self.host}:{self.port}")
        server.serve_forever()

# 使用示例
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="任务池事件驱动集成")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=9008, help="监听端口")
    parser.add_argument("--api", action="store_true", help="启动API模式")
    parser.add_argument("--event", help="事件类型")
    parser.add_argument("--task", help="任务ID")
    
    args = parser.parse_args()
    
    if args.api:
        # 启动API模式
        api = TaskPoolEventAPI(args.host, args.port)
        api.start()
    elif args.event and args.task:
        # 命令行模式
        integration = TaskPoolEventIntegration()
        
        # 处理事件
        event_data = {"task_id": args.task}
        integration.process_task_event(args.event, event_data)
        
        # 打印指标
        print(f"指标: {integration.get_metrics()}")
    else:
        # 测试模式
        integration = TaskPoolEventIntegration()
        
        # 模拟事件
        integration.process_task_event("task.created", {
            "task_id": "task-001",
            "priority": "P1"
        })
        
        integration.process_task_event("task.status_changed", {
            "task_id": "task-001",
            "old_status": "pending",
            "new_status": "claimed"
        })
        
        # 打印指标
        print(f"指标: {integration.get_metrics()}")
