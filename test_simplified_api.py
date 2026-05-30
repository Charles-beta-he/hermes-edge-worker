#!/usr/bin/env python3
"""简化 API 测试。"""

from simplified.simplified_api import SimplifiedAPI


class FakeRag:
    def __init__(self):
        self.items = []

    def add_knowledge(self, knowledge_id, content, metadata=None):
        self.items.append({"id": knowledge_id, "content": content, "metadata": metadata or {}})

    def search(self, query, top_k=5):
        return [item for item in self.items if query in item["content"]][:top_k]

    def get_metrics(self):
        return {"items": len(self.items)}


class FakeDataLayer:
    def __init__(self):
        self.storage = {}

    def store(self, namespace, key, value):
        self.storage[(namespace, key)] = value

    def get_metrics(self):
        return {"items": len(self.storage)}


class FakeEventBus:
    def __init__(self):
        self.events = []

    def publish(self, event_type, data):
        self.events.append((event_type, data))

    def get_metrics(self):
        return {"events": len(self.events)}


def test_add_knowledge_writes_to_rag_data_layer_and_event_bus():
    rag = FakeRag()
    data_layer = FakeDataLayer()
    event_bus = FakeEventBus()
    api = SimplifiedAPI(data_layer, event_bus, None, rag)

    api.add_knowledge("k1", "hello edge worker", {"source": "test"})

    assert api.search("edge") == [{"id": "k1", "content": "hello edge worker", "metadata": {"source": "test"}}]
    assert data_layer.storage[("knowledge", "k1")]["content"] == "hello edge worker"
    assert event_bus.events[0][0] == "knowledge.added"


def test_get_metrics_aggregates_component_metrics():
    api = SimplifiedAPI(FakeDataLayer(), FakeEventBus(), None, FakeRag())

    metrics = api.get_metrics()

    assert metrics["data_layer"] == {"items": 0}
    assert metrics["event_bus"] == {"events": 0}
    assert metrics["rag_manager"] == {"items": 0}
