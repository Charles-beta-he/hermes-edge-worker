#!/usr/bin/env python3
"""
统一事件总线
解决孤岛逻辑：统一通信机制
"""

import json
import uuid
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from collections import defaultdict

class Event:
    """事件"""
    
    def __init__(self, event_type: str, data: Dict[str, Any], source: str = ""):
        self.id = str(uuid.uuid4())
        self.type = event_type
        self.data = data
        self.source = source
        self.timestamp = datetime.now().isoformat()
        self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }

class EventHandler:
    """事件处理器"""
    
    def __init__(self, handler_id: str, handler_func: Callable, event_types: Optional[List[str]] = None):
        self.id = handler_id
        self.func = handler_func
        self.event_types = event_types or []
        self.metrics = {
            "total_handled": 0,
            "successful": 0,
            "failed": 0
        }
    
    def handle(self, event: Event) -> bool:
        """处理事件"""
        try:
            self.func(event)
            self.metrics["total_handled"] += 1
            self.metrics["successful"] += 1
            return True
        except Exception as e:
            self.metrics["total_handled"] += 1
            self.metrics["failed"] += 1
            print(f"Event handler error: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics

class EventStore:
    """事件存储"""
    
    def __init__(self, storage_dir: str = "/tmp/event_store"):
        self.storage_dir = storage_dir
        self.events = []
        self.metrics = {
            "total_events": 0,
            "total_stored": 0
        }
    
    def store(self, event: Event):
        """存储事件"""
        self.events.append(event)
        self.metrics["total_events"] += 1
        self.metrics["total_stored"] += 1
        
        # 持久化存储
        self._persist(event)
    
    def query(self, event_type: Optional[str] = None, source: Optional[str] = None, 
              start_time: Optional[str] = None, end_time: Optional[str] = None) -> List[Event]:
        """查询事件"""
        results = []
        
        for event in self.events:
            # 类型过滤
            if event_type and event.type != event_type:
                continue
            
            # 来源过滤
            if source and event.source != source:
                continue
            
            # 时间过滤
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            
            results.append(event)
        
        return results
    
    def _persist(self, event: Event):
        """持久化存储"""
        import os
        os.makedirs(self.storage_dir, exist_ok=True)
        
        file_path = f"{self.storage_dir}/{event.id}.json"
        with open(file_path, 'w') as f:
            json.dump(event.to_dict(), f)
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics

class UnifiedEventBus:
    """统一事件总线"""
    
    def __init__(self):
        self.handlers = defaultdict(list)  # event_type -> [handler]
        self.event_store = EventStore()
        self.metrics = {
            "total_published": 0,
            "total_subscriptions": 0,
            "total_handlers": 0
        }
    
    def publish(self, event_type: str, data: Dict[str, Any], source: str = ""):
        """发布事件"""
        event = Event(event_type, data, source)
        
        # 存储事件
        self.event_store.store(event)
        
        # 通知订阅者
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                handler.handle(event)
        
        # 更新指标
        self.metrics["total_published"] += 1
        
        return event.id
    
    def subscribe(self, event_type: str, handler: EventHandler):
        """订阅事件"""
        self.handlers[event_type].append(handler)
        
        # 更新指标
        self.metrics["total_subscriptions"] += 1
        self.metrics["total_handlers"] += 1
    
    def unsubscribe(self, event_type: str, handler_id: str) -> bool:
        """取消订阅"""
        if event_type in self.handlers:
            for i, handler in enumerate(self.handlers[event_type]):
                if handler.id == handler_id:
                    self.handlers[event_type].pop(i)
                    self.metrics["total_handlers"] -= 1
                    return True
        return False
    
    def query_events(self, event_type: Optional[str] = None, source: Optional[str] = None) -> List[Event]:
        """查询事件"""
        return self.event_store.query(event_type, source)
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return {
            "event_bus": self.metrics,
            "event_store": self.event_store.get_metrics(),
            "handlers": {
                event_type: len(handlers) 
                for event_type, handlers in self.handlers.items()
            }
        }

class TaskEventPublisher:
    """任务事件发布者"""
    
    def __init__(self, event_bus: UnifiedEventBus):
        self.event_bus = event_bus
    
    def publish_task_created(self, task_id: str, task_type: str, params: Dict[str, Any]):
        """发布任务创建事件"""
        self.event_bus.publish("task.created", {
            "task_id": task_id,
            "task_type": task_type,
            "params": params
        }, "task_scheduler")
    
    def publish_task_executed(self, task_id: str, result: Dict[str, Any]):
        """发布任务执行事件"""
        self.event_bus.publish("task.executed", {
            "task_id": task_id,
            "result": result
        }, "task_scheduler")
    
    def publish_task_completed(self, task_id: str, result: Dict[str, Any]):
        """发布任务完成事件"""
        self.event_bus.publish("task.completed", {
            "task_id": task_id,
            "result": result
        }, "task_scheduler")

class KnowledgeEventPublisher:
    """知识事件发布者"""
    
    def __init__(self, event_bus: UnifiedEventBus):
        self.event_bus = event_bus
    
    def publish_knowledge_added(self, knowledge_id: str, content: str, metadata: Dict[str, Any]):
        """发布知识添加事件"""
        self.event_bus.publish("knowledge.added", {
            "knowledge_id": knowledge_id,
            "content": content,
            "metadata": metadata
        }, "knowledge_manager")
    
    def publish_knowledge_searched(self, query: str, results: List[Dict[str, Any]]):
        """发布知识搜索事件"""
        self.event_bus.publish("knowledge.searched", {
            "query": query,
            "results_count": len(results)
        }, "knowledge_manager")

class ExperienceEventPublisher:
    """经验事件发布者"""
    
    def __init__(self, event_bus: UnifiedEventBus):
        self.event_bus = event_bus
    
    def publish_experience_created(self, experience_id: str, data: Dict[str, Any]):
        """发布经验创建事件"""
        self.event_bus.publish("experience.created", {
            "experience_id": experience_id,
            "data": data
        }, "experience_ratchet")
    
    def publish_experience_validated(self, experience_id: str, evidence: str):
        """发布经验验证事件"""
        self.event_bus.publish("experience.validated", {
            "experience_id": experience_id,
            "evidence": evidence
        }, "experience_ratchet")

class EventSubscriber:
    """事件订阅者"""
    
    def __init__(self, event_bus: UnifiedEventBus):
        self.event_bus = event_bus
    
    def subscribe_to_task_events(self, handler_func: Callable):
        """订阅任务事件"""
        handler = EventHandler(
            handler_id="task_handler",
            handler_func=handler_func,
            event_types=["task.created", "task.executed", "task.completed"]
        )
        
        self.event_bus.subscribe("task.created", handler)
        self.event_bus.subscribe("task.executed", handler)
        self.event_bus.subscribe("task.completed", handler)
    
    def subscribe_to_knowledge_events(self, handler_func: Callable):
        """订阅知识事件"""
        handler = EventHandler(
            handler_id="knowledge_handler",
            handler_func=handler_func,
            event_types=["knowledge.added", "knowledge.searched"]
        )
        
        self.event_bus.subscribe("knowledge.added", handler)
        self.event_bus.subscribe("knowledge.searched", handler)
    
    def subscribe_to_experience_events(self, handler_func: Callable):
        """订阅经验事件"""
        handler = EventHandler(
            handler_id="experience_handler",
            handler_func=handler_func,
            event_types=["experience.created", "experience.validated"]
        )
        
        self.event_bus.subscribe("experience.created", handler)
        self.event_bus.subscribe("experience.validated", handler)

# 使用示例
if __name__ == "__main__":
    # 创建事件总线
    event_bus = UnifiedEventBus()
    
    # 创建发布者
    task_publisher = TaskEventPublisher(event_bus)
    knowledge_publisher = KnowledgeEventPublisher(event_bus)
    experience_publisher = ExperienceEventPublisher(event_bus)
    
    # 创建订阅者
    def task_handler(event):
        print(f"Task event: {event.type} - {event.data}")
    
    def knowledge_handler(event):
        print(f"Knowledge event: {event.type} - {event.data}")
    
    subscriber = EventSubscriber(event_bus)
    subscriber.subscribe_to_task_events(task_handler)
    subscriber.subscribe_to_knowledge_events(knowledge_handler)
    
    # 发布事件
    task_publisher.publish_task_created("task-001", "code_generation", {"file": "main.py"})
    knowledge_publisher.publish_knowledge_added("knowledge-001", "Python性能优化", {"category": "programming"})
    
    # 获取指标
    metrics = event_bus.get_metrics()
    print(f"Metrics: {metrics}")
