#!/usr/bin/env python3
"""9008 task pool event integration 可靠 envelope 测试。"""

import json

from task_pool_event_integration import TaskPoolEventIntegration


class ReliableIntegration(TaskPoolEventIntegration):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.claimed = []
        self.executed = []

    def auto_claim(self, task_id: str):
        self.claimed.append(task_id)
        self.metrics["tasks_auto_claimed"] += 1
        self.auto_execute(task_id)

    def auto_execute(self, task_id: str):
        self.executed.append(task_id)
        self.metrics["tasks_auto_executed"] += 1


class FailingIntegration(TaskPoolEventIntegration):
    def on_task_created(self, event_data):
        raise RuntimeError("boom")


def test_9008_process_event_returns_processed_envelope_and_persists_event(tmp_path):
    store = tmp_path / "integration-events.jsonl"
    integration = ReliableIntegration(event_store_path=store, max_retries=1)

    result = integration.process_task_event(
        "task.created",
        {"event_id": "evt-9008-1", "task_id": "task-1", "priority": "P1"},
    )

    assert result["status"] == "processed"
    assert result["event_id"] == "evt-9008-1"
    assert integration.claimed == ["task-1"]
    assert integration.executed == ["task-1"]
    records = [json.loads(line) for line in store.read_text().splitlines()]
    assert records[-1]["status"] == "processed"
    assert records[-1]["event_id"] == "evt-9008-1"


def test_9008_duplicate_event_id_does_not_repeat_side_effects(tmp_path):
    integration = ReliableIntegration(event_store_path=tmp_path / "events.jsonl")
    event_data = {"event_id": "evt-dup", "task_id": "task-dup", "priority": "P1"}

    first = integration.process_task_event("task.created", event_data)
    second = integration.process_task_event("task.created", event_data)

    assert first["status"] == "processed"
    assert second["status"] == "duplicate"
    assert integration.claimed == ["task-dup"]
    assert integration.metrics["duplicates"] == 1


def test_9008_dead_letters_after_retry_exhaustion(tmp_path):
    integration = FailingIntegration(event_store_path=tmp_path / "events.jsonl", max_retries=1)

    result = integration.process_task_event(
        "task.created",
        {"event_id": "evt-dead", "task_id": "task-dead", "priority": "P1"},
    )

    assert result["status"] == "dead_lettered"
    assert result["event_id"] == "evt-dead"
    assert len(integration.dead_letters) == 1
    records = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert [record["status"] for record in records] == ["failed_attempt", "dead_lettered"]
