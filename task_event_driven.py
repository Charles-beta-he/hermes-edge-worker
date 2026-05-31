#!/usr/bin/env python3
"""
任务池事件驱动自动执行

事件可靠性边界：
- event_id 幂等：同一事件只触发一次副作用。
- local event store：每次处理写入 JSONL，保留 attempt/status/error。
- retry：瞬时失败在进死信前重试。
- dead-letter：超过重试上限后保留事件和错误，避免静默丢失。
"""

import json
import os
import sys
from typing import Dict, Any
from pathlib import Path

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from event_reliability import ReliableEventProcessor
from request_security import RequestAuthenticator


class TaskEventDriven:
    """任务事件驱动"""

    def __init__(self, event_bus=None, task_pool=None, orchestrator=None, event_store_path=None, max_retries: int = 2, retry_delay: float = 0.0, max_store_bytes: int = 5 * 1024 * 1024):
        self.event_bus = event_bus
        self.task_pool = task_pool
        self.orchestrator = orchestrator
        self.event_store_path = Path(event_store_path) if event_store_path else SCRIPT_DIR / "event_store.jsonl"
        self.max_retries = max(0, int(max_retries))
        self.retry_delay = max(0.0, float(retry_delay))
        self.event_processor = ReliableEventProcessor(
            self.event_store_path,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            max_store_bytes=max_store_bytes,
        )
        self.handlers = {}
        self.dead_letters = self.event_processor.dead_letters
        self.processed_event_ids = self.event_processor.processed_event_ids
        self.metrics = {
            "events_received": 0,
            "tasks_auto_claimed": 0,
            "tasks_auto_executed": 0,
            "errors": 0,
            "duplicates": 0,
            "retries": 0,
            "dead_lettered": 0,
        }
        self._load_processed_events()

        # 注册事件处理器
        self._register_handlers()

    def _register_handlers(self):
        """注册事件处理器"""
        self.handlers = {
            "task.created": self.on_task_created,
            "task.status_changed": self.on_task_status_changed,
            "task.dependency_met": self.on_task_dependency_met,
            "task.priority_changed": self.on_task_priority_changed,
            "task.assigned": self.on_task_assigned,
        }

    def _event_id(self, event_type: str, event_data: Dict[str, Any]) -> str:
        return self.event_processor.event_id(event_type, event_data)

    def _load_processed_events(self):
        return None

    def _store_event(self, event_id: str, event_type: str, event_data: Dict[str, Any], status: str, attempt: int, error: str = ""):
        return self.event_processor.store_event(event_id, event_type, event_data, status, attempt, error or None)

    def handle_event(self, event_type: str, event_data: Dict[str, Any]):
        """处理事件。返回结构化状态，供 API/调度器识别重复、成功、死信。"""
        event_data = event_data or {}
        event_id = self._event_id(event_type, event_data)
        self.metrics["events_received"] += 1

        handler = self.handlers.get(event_type)
        if not handler:
            print(f"未知事件类型: {event_type}")
            self._store_event(event_id, event_type, event_data, "ignored", 0, "unknown_event_type")
            return {"status": "ignored", "event_id": event_id, "error": "unknown_event_type"}

        result = self.event_processor.process(event_type, event_data, handler)
        status = result.get("status")
        if status == "duplicate":
            self.metrics["duplicates"] += 1
        elif status == "dead_lettered":
            self.metrics["dead_lettered"] += 1
            self.metrics["errors"] += int(result.get("attempts") or result.get("attempt") or 1)
        elif status == "processed":
            attempts = int(result.get("attempts") or result.get("attempt") or 1)
            if attempts > 1:
                self.metrics["retries"] += attempts - 1
                self.metrics["errors"] += attempts - 1
        return result

    def on_task_created(self, event_data: Dict[str, Any]):
        """任务创建时触发"""
        task_id = str(event_data.get("task_id", ""))
        priority = event_data.get("priority", "P2")

        print(f"[事件] 任务创建: {task_id}, 优先级: {priority}")

        # 高优先级任务立即认领
        if priority in ["P0", "P1"] and task_id:
            self.auto_claim(task_id)

    def on_task_status_changed(self, event_data: Dict[str, Any]):
        """任务状态变更时触发"""
        task_id = str(event_data.get("task_id", ""))
        old_status = event_data.get("old_status")
        new_status = event_data.get("new_status")

        print(f"[事件] 任务状态变更: {task_id}, {old_status} -> {new_status}")

        # 状态变为pending时自动认领
        if new_status == "pending" and task_id:
            self.auto_claim(task_id)

        # 状态变为claimed时自动执行
        if new_status == "claimed" and task_id:
            self.auto_execute(task_id)

    def on_task_dependency_met(self, event_data: Dict[str, Any]):
        """任务依赖满足时触发"""
        task_id = str(event_data.get("task_id", ""))

        print(f"[事件] 任务依赖满足: {task_id}")

        # 自动认领
        if task_id:
            self.auto_claim(task_id)

    def on_task_priority_changed(self, event_data: Dict[str, Any]):
        """任务优先级变更时触发"""
        task_id = str(event_data.get("task_id", ""))
        new_priority = event_data.get("new_priority")

        print(f"[事件] 任务优先级变更: {task_id}, 新优先级: {new_priority}")

        # 高优先级任务立即认领
        if new_priority in ["P0", "P1"] and task_id:
            self.auto_claim(task_id)

    def on_task_assigned(self, event_data: Dict[str, Any]):
        """任务分配时触发"""
        task_id = str(event_data.get("task_id", ""))
        agent_id = event_data.get("agent_id")

        print(f"[事件] 任务分配: {task_id} -> {agent_id}")

        # 自动执行
        if task_id:
            self.auto_execute(task_id)

    def auto_claim(self, task_id: str):
        """自动认领"""
        try:
            # 认领任务
            if self.orchestrator:
                self.orchestrator.claim(task_id)
                print(f"[自动] 认领成功: {task_id}")
                self.metrics["tasks_auto_claimed"] += 1

                # 触发执行
                self.auto_execute(task_id)
            else:
                print(f"[警告] 编排器未初始化，无法认领: {task_id}")
        except Exception as e:
            print(f"[错误] 自动认领失败: {task_id}, 错误: {e}")
            raise

    def auto_execute(self, task_id: str):
        """自动执行"""
        try:
            # 执行任务
            if self.orchestrator:
                self.orchestrator.autorun_runner(task_id)
                print(f"[自动] 执行成功: {task_id}")
                self.metrics["tasks_auto_executed"] += 1
            else:
                print(f"[警告] 编排器未初始化，无法执行: {task_id}")
        except Exception as e:
            print(f"[错误] 自动执行失败: {task_id}, 错误: {e}")
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics


class TaskEventDrivenAPI:
    """任务事件驱动API"""

    def __init__(self, host: str = "0.0.0.0", port: int = 9007, authenticator=None):
        self.host = host
        self.port = port
        self.event_driven = TaskEventDriven()
        self.authenticator = authenticator or RequestAuthenticator(
            token=os.environ.get("HERMES_EVENT_API_TOKEN") or os.environ.get("HERMES_EDGE_TOKEN"),
            hmac_secret=os.environ.get("HERMES_EVENT_API_HMAC_SECRET") or os.environ.get("HERMES_EDGE_HMAC_SECRET"),
            max_skew_seconds=int(os.environ.get("HERMES_EVENT_API_HMAC_MAX_SKEW_SECONDS") or os.environ.get("HERMES_EDGE_HMAC_MAX_SKEW_SECONDS") or 300),
        )

    def start(self):
        """启动API"""
        from http.server import HTTPServer, BaseHTTPRequestHandler

        class EventHandler(BaseHTTPRequestHandler):
            event_driven = self.event_driven
            authenticator = self.authenticator

            def _json(self, payload, status=200):
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(payload, ensure_ascii=False).encode())

            def do_POST(self):
                """处理POST请求"""
                if self.path == "/event":
                    try:
                        content_length = int(self.headers.get("Content-Length", 0))
                        body = self.rfile.read(content_length)
                        if not self.authenticator.authorize(self, body):
                            self._json({"error": "Unauthorized"}, 401)
                            return
                        data = json.loads(body)

                        event_type = data.get("event_type")
                        event_data = data.get("event_data", {})

                        # 处理事件
                        result = self.event_driven.handle_event(event_type, event_data)
                        self._json(result)
                    except Exception as e:
                        self._json({"error": str(e)}, 500)
                else:
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Not found"}).encode())

            def do_GET(self):
                """处理GET请求"""
                if self.path == "/metrics":
                    if not self.authenticator.authorize_token(self):
                        self._json({"error": "Unauthorized"}, 401)
                        return
                    metrics = dict(self.event_driven.get_metrics())
                    metrics["security"] = self.authenticator.security_summary()
                    self._json(metrics)
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
        print(f"Task Event Driven API running on {self.host}:{self.port}")
        server.serve_forever()


# 使用示例
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="任务池事件驱动自动执行")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=9007, help="监听端口")
    parser.add_argument("--api", action="store_true", help="启动API模式")

    args = parser.parse_args()

    if args.api:
        # 启动API模式
        api = TaskEventDrivenAPI(args.host, args.port)
        api.start()
    else:
        # 命令行模式
        event_driven = TaskEventDriven()

        # 模拟事件
        event_driven.handle_event("task.created", {
            "task_id": "task-001",
            "priority": "P1"
        })

        event_driven.handle_event("task.status_changed", {
            "task_id": "task-001",
            "old_status": "pending",
            "new_status": "claimed"
        })

        # 打印指标
        print(f"指标: {event_driven.get_metrics()}")
