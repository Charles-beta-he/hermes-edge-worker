#!/usr/bin/env python3
"""
任务池事件驱动自动执行

事件可靠性边界：
- event_id 幂等：同一事件只触发一次副作用。
- local event store：每次处理写入 JSONL，保留 attempt/status/error。
- retry：瞬时失败在进死信前重试。
- dead-letter：超过重试上限后保留事件和错误，避免静默丢失。
"""

import hashlib
import json
import sys
import time
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))


class TaskEventDriven:
    """任务事件驱动"""

    def __init__(self, event_bus=None, task_pool=None, orchestrator=None, event_store_path=None, max_retries: int = 2, retry_delay: float = 0.0):
        self.event_bus = event_bus
        self.task_pool = task_pool
        self.orchestrator = orchestrator
        self.event_store_path = Path(event_store_path) if event_store_path else SCRIPT_DIR / "event_store.jsonl"
        self.max_retries = max(0, int(max_retries))
        self.retry_delay = max(0.0, float(retry_delay))
        self.handlers = {}
        self.dead_letters = []
        self.processed_event_ids = set()
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
        explicit = event_data.get("event_id") or event_data.get("id")
        if explicit:
            return str(explicit)
        payload = json.dumps({"event_type": event_type, "event_data": event_data}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _load_processed_events(self):
        if not self.event_store_path.exists():
            return
        try:
            for line in self.event_store_path.read_text().splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("status") == "processed" and record.get("event_id"):
                    self.processed_event_ids.add(record["event_id"])
                if record.get("status") == "dead_lettered":
                    self.dead_letters.append(record)
        except Exception:
            # Event store corruption should not prevent process startup; new writes still append.
            pass

    def _store_event(self, event_id: str, event_type: str, event_data: Dict[str, Any], status: str, attempt: int, error: str = ""):
        record = {
            "event_id": event_id,
            "event_type": event_type,
            "event_data": event_data,
            "status": status,
            "attempt": attempt,
            "error": error,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        self.event_store_path.parent.mkdir(parents=True, exist_ok=True)
        with self.event_store_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        return record

    def handle_event(self, event_type: str, event_data: Dict[str, Any]):
        """处理事件。返回结构化状态，供 API/调度器识别重复、成功、死信。"""
        event_data = event_data or {}
        event_id = self._event_id(event_type, event_data)
        self.metrics["events_received"] += 1

        if event_id in self.processed_event_ids:
            self.metrics["duplicates"] += 1
            self._store_event(event_id, event_type, event_data, "duplicate", 0)
            return {"status": "duplicate", "event_id": event_id}

        handler = self.handlers.get(event_type)
        if not handler:
            print(f"未知事件类型: {event_type}")
            self._store_event(event_id, event_type, event_data, "ignored", 0, "unknown_event_type")
            return {"status": "ignored", "event_id": event_id, "error": "unknown_event_type"}

        last_error = ""
        for attempt in range(1, self.max_retries + 2):
            try:
                handler(event_data)
                self.processed_event_ids.add(event_id)
                self._store_event(event_id, event_type, event_data, "processed", attempt)
                return {"status": "processed", "event_id": event_id, "attempt": attempt}
            except Exception as e:
                last_error = str(e)
                self.metrics["errors"] += 1
                self._store_event(event_id, event_type, event_data, "failed_attempt", attempt, last_error)
                if attempt <= self.max_retries:
                    self.metrics["retries"] += 1
                    if self.retry_delay:
                        time.sleep(self.retry_delay)
                    continue
                print(f"事件处理错误: {event_type}, 错误: {e}")
                record = self._store_event(event_id, event_type, event_data, "dead_lettered", attempt, last_error)
                self.dead_letters.append(record)
                self.metrics["dead_lettered"] += 1
                return {"status": "dead_lettered", "event_id": event_id, "attempt": attempt, "error": last_error}

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

    def __init__(self, host: str = "0.0.0.0", port: int = 9007):
        self.host = host
        self.port = port
        self.event_driven = TaskEventDriven()

    def start(self):
        """启动API"""
        from http.server import HTTPServer, BaseHTTPRequestHandler

        class EventHandler(BaseHTTPRequestHandler):
            event_driven = self.event_driven

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
                        result = self.event_driven.handle_event(event_type, event_data)

                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(result).encode())
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
                    metrics = self.event_driven.get_metrics()
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
