#!/usr/bin/env python3
"""事件驱动可靠性边界测试。"""

import json

from task_event_driven import TaskEventDriven


class FakeOrchestrator:
    def __init__(self, fail_claim_times=0, fail_execute_times=0):
        self.claim_calls = []
        self.execute_calls = []
        self.fail_claim_times = fail_claim_times
        self.fail_execute_times = fail_execute_times

    def claim(self, task_id):
        self.claim_calls.append(task_id)
        if len(self.claim_calls) <= self.fail_claim_times:
            raise RuntimeError("claim transient failure")
        return {"ok": True}

    def autorun_runner(self, task_id):
        self.execute_calls.append(task_id)
        if len(self.execute_calls) <= self.fail_execute_times:
            raise RuntimeError("execute transient failure")
        return {"ok": True}


def test_event_id_makes_event_processing_idempotent(tmp_path):
    orchestrator = FakeOrchestrator()
    event_driven = TaskEventDriven(orchestrator=orchestrator, event_store_path=tmp_path / "events.jsonl")

    event = {"event_id": "evt-1", "task_id": "task-1", "priority": "P1"}
    first = event_driven.handle_event("task.created", event)
    second = event_driven.handle_event("task.created", event)

    assert first["status"] == "processed"
    assert second["status"] == "duplicate"
    assert orchestrator.claim_calls == ["task-1"]
    assert event_driven.metrics["duplicates"] == 1


def test_transient_failure_retries_then_succeeds(tmp_path):
    orchestrator = FakeOrchestrator(fail_claim_times=1)
    event_driven = TaskEventDriven(orchestrator=orchestrator, event_store_path=tmp_path / "events.jsonl", max_retries=2)

    result = event_driven.handle_event("task.created", {"event_id": "evt-2", "task_id": "task-2", "priority": "P1"})

    assert result["status"] == "processed"
    assert orchestrator.claim_calls == ["task-2", "task-2"]
    assert event_driven.metrics["retries"] == 1
    assert event_driven.metrics["dead_lettered"] == 0


def test_permanent_failure_goes_to_dead_letter(tmp_path):
    orchestrator = FakeOrchestrator(fail_claim_times=3)
    event_driven = TaskEventDriven(orchestrator=orchestrator, event_store_path=tmp_path / "events.jsonl", max_retries=1)

    result = event_driven.handle_event("task.created", {"event_id": "evt-3", "task_id": "task-3", "priority": "P1"})

    assert result["status"] == "dead_lettered"
    assert len(orchestrator.claim_calls) == 2
    assert event_driven.metrics["dead_lettered"] == 1
    assert event_driven.dead_letters[0]["event_id"] == "evt-3"


def test_event_store_persists_attempt_and_status(tmp_path):
    store_path = tmp_path / "events.jsonl"
    event_driven = TaskEventDriven(orchestrator=FakeOrchestrator(), event_store_path=store_path)

    event_driven.handle_event("task.created", {"event_id": "evt-4", "task_id": "task-4", "priority": "P1"})

    records = [json.loads(line) for line in store_path.read_text().splitlines()]
    assert records[-1]["event_id"] == "evt-4"
    assert records[-1]["status"] == "processed"
    assert records[-1]["attempt"] == 1
