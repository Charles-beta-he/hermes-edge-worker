#!/usr/bin/env python3
"""Shared reliable event envelope processing for Hermes Edge Worker APIs."""

import gzip
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional


class ReliableEventProcessor:
    """Idempotent event processing with JSONL persistence, retry and dead-letter."""

    def __init__(
        self,
        event_store_path,
        max_retries: int = 2,
        retry_delay: float = 0.0,
        max_store_bytes: int = 5 * 1024 * 1024,
        rotate_generations: int = 1,
        compress_rotated: bool = False,
    ):
        self.event_store_path = Path(event_store_path)
        self.max_retries = max(0, int(max_retries))
        self.retry_delay = max(0.0, float(retry_delay))
        self.max_store_bytes = max(0, int(max_store_bytes or 0))
        self.rotate_generations = max(1, int(rotate_generations or 1))
        self.compress_rotated = bool(compress_rotated)
        self.processed_event_ids = set()
        self.dead_letters = []
        self._load_existing_state()

    def event_id(self, event_type: str, event_data: Dict[str, Any]) -> str:
        event_data = event_data or {}
        explicit = event_data.get("event_id") or event_data.get("id")
        if explicit:
            return str(explicit)
        payload = json.dumps({"event_type": event_type, "event_data": event_data}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode()).hexdigest()

    def process(self, event_type: str, event_data: Dict[str, Any], handler: Callable[[Dict[str, Any]], Any]) -> Dict[str, Any]:
        event_data = event_data or {}
        event_id = self.event_id(event_type, event_data)
        task_id = event_data.get("task_id", "")

        if event_id in self.processed_event_ids:
            self.store_event(event_id, event_type, event_data, "duplicate", 0, None)
            return {"status": "duplicate", "event_id": event_id, "event_type": event_type, "task_id": task_id}

        last_error = None
        for attempt in range(1, self.max_retries + 2):
            try:
                handler(event_data)
                self.processed_event_ids.add(event_id)
                self.store_event(event_id, event_type, event_data, "processed", attempt, None)
                return {"status": "processed", "event_id": event_id, "event_type": event_type, "task_id": task_id, "attempt": attempt, "attempts": attempt}
            except Exception as exc:
                last_error = str(exc)
                if attempt <= self.max_retries:
                    self.store_event(event_id, event_type, event_data, "failed_attempt", attempt, last_error)
                    if self.retry_delay:
                        time.sleep(self.retry_delay)
                    continue
                record = self.store_event(event_id, event_type, event_data, "dead_lettered", attempt, last_error)
                self.dead_letters.append(record)
                return {"status": "dead_lettered", "event_id": event_id, "event_type": event_type, "task_id": task_id, "error": last_error, "attempt": attempt, "attempts": attempt}

    def store_event(self, event_id: str, event_type: str, event_data: Dict[str, Any], status: str, attempt: int, error: Optional[str] = None) -> Dict[str, Any]:
        self._rotate_if_needed()
        self.event_store_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_id": event_id,
            "event_type": event_type,
            "event_data": event_data or {},
            "status": status,
            "attempt": attempt,
            "error": error,
        }
        with self.event_store_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        return record

    def _load_existing_state(self):
        if not self.event_store_path.exists():
            return
        try:
            for line in self.event_store_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("status") == "processed" and record.get("event_id"):
                    self.processed_event_ids.add(record["event_id"])
                if record.get("status") == "dead_lettered":
                    self.dead_letters.append(record)
        except Exception:
            # Corrupt historical logs must not prevent the event API from starting.
            return

    def _rotate_if_needed(self):
        if not self.max_store_bytes or not self.event_store_path.exists():
            return
        try:
            if self.event_store_path.stat().st_size <= self.max_store_bytes:
                return
            if self.compress_rotated:
                self._rotate_compressed()
            else:
                rotated = self.event_store_path.with_name(self.event_store_path.name + ".1")
                if rotated.exists():
                    rotated.unlink()
                self.event_store_path.rename(rotated)
        except OSError:
            return

    def _generation_path(self, generation: int):
        suffix = f".{generation}"
        if self.compress_rotated:
            suffix += ".gz"
        return self.event_store_path.with_name(self.event_store_path.name + suffix)

    def _read_generation_bytes(self, generation: int):
        gz_path = self.event_store_path.with_name(self.event_store_path.name + f".{generation}.gz")
        plain_path = self.event_store_path.with_name(self.event_store_path.name + f".{generation}")
        if gz_path.exists():
            return gzip.decompress(gz_path.read_bytes())
        if plain_path.exists():
            return plain_path.read_bytes()
        return None

    def _remove_generation_files(self, generation: int):
        for suffix in (f".{generation}", f".{generation}.gz"):
            path = self.event_store_path.with_name(self.event_store_path.name + suffix)
            if path.exists():
                path.unlink()

    def _write_generation(self, generation: int, data: bytes):
        self._remove_generation_files(generation)
        path = self._generation_path(generation)
        if self.compress_rotated:
            path.write_bytes(gzip.compress(data))
        else:
            path.write_bytes(data)

    def _rotate_compressed(self):
        for generation in range(self.rotate_generations, 0, -1):
            data = self._read_generation_bytes(generation)
            if data is None:
                continue
            if generation >= self.rotate_generations:
                self._remove_generation_files(generation)
            else:
                self._write_generation(generation + 1, data)
                self._remove_generation_files(generation)
        active = self.event_store_path.read_bytes()
        self._write_generation(1, active)
        self.event_store_path.unlink()
