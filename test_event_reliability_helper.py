#!/usr/bin/env python3
"""共享事件可靠性 helper 测试。"""

import gzip
import json

from event_reliability import ReliableEventProcessor


def test_reliable_event_processor_handles_idempotency_retry_and_dead_letter(tmp_path):
    calls = []
    processor = ReliableEventProcessor(event_store_path=tmp_path / "events.jsonl", max_retries=1)

    processed = processor.process(
        "task.created",
        {"event_id": "evt-ok", "task_id": "task-1"},
        lambda event_data: calls.append(event_data["task_id"]),
    )
    duplicate = processor.process(
        "task.created",
        {"event_id": "evt-ok", "task_id": "task-1"},
        lambda event_data: calls.append("duplicate-side-effect"),
    )

    assert processed["status"] == "processed"
    assert duplicate["status"] == "duplicate"
    assert calls == ["task-1"]

    failed = processor.process(
        "task.created",
        {"event_id": "evt-dead", "task_id": "task-dead"},
        lambda event_data: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert failed["status"] == "dead_lettered"
    assert processor.dead_letters[-1]["event_id"] == "evt-dead"
    statuses = [json.loads(line)["status"] for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert statuses == ["processed", "duplicate", "failed_attempt", "dead_lettered"]


def test_reliable_event_processor_rotates_event_store_when_size_limit_exceeded(tmp_path):
    store = tmp_path / "events.jsonl"
    store.write_text("x" * 200, encoding="utf-8")
    processor = ReliableEventProcessor(event_store_path=store, max_store_bytes=100)

    result = processor.process(
        "task.created",
        {"event_id": "evt-rotate", "task_id": "task-rotate"},
        lambda event_data: None,
    )

    assert result["status"] == "processed"
    assert store.exists()
    rotated = tmp_path / "events.jsonl.1"
    assert rotated.exists()
    assert rotated.read_text(encoding="utf-8") == "x" * 200
    assert "evt-rotate" in store.read_text(encoding="utf-8")


def test_reliable_event_processor_keeps_multiple_generations_and_compresses_older_logs(tmp_path):
    store = tmp_path / "events.jsonl"
    store.write_text("active", encoding="utf-8")
    (tmp_path / "events.jsonl.1").write_text("gen1", encoding="utf-8")
    (tmp_path / "events.jsonl.2.gz").write_bytes(gzip.compress(b"gen2"))

    processor = ReliableEventProcessor(event_store_path=store, max_store_bytes=1, rotate_generations=3, compress_rotated=True)
    processor.process("task.created", {"event_id": "evt-retain", "task_id": "task-retain"}, lambda event_data: None)

    assert gzip.decompress((tmp_path / "events.jsonl.1.gz").read_bytes()) == b"active"
    assert gzip.decompress((tmp_path / "events.jsonl.2.gz").read_bytes()) == b"gen1"
    assert gzip.decompress((tmp_path / "events.jsonl.3.gz").read_bytes()) == b"gen2"
    assert "evt-retain" in store.read_text(encoding="utf-8")
