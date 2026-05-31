#!/usr/bin/env python3
"""PORTS.md 与架构链路检查一致性测试。"""

from pathlib import Path

import architecture_link_check
from architecture_link_check import ArchitectureLinkCheck


def test_verified_ports_are_parsed_from_ports_doc(tmp_path, monkeypatch):
    ports = tmp_path / "PORTS.md"
    ports.write_text(
        "| 9007 | 事件驱动 API | `task_event_driven.py` | verified | `GET /health` | 当前事件驱动核心。 |\n"
        "| 9008 | 任务池事件集成 API | `task_pool_event_integration.py` | verified | `GET /health` | 当前 taskpool 事件集成核心。 |\n"
        "| 9009 | 多站点管理 API | `multi_site_manager.py` | verified | `GET /health` | 当前多站点管理核心。 |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(architecture_link_check, "SCRIPT_DIR", tmp_path)

    check = ArchitectureLinkCheck()
    parsed = check._verified_ports_from_ports_doc()

    assert parsed == {9007, 9008, 9009}


def test_ports_doc_consistency_fails_when_verified_port_missing(tmp_path, monkeypatch):
    (tmp_path / "PORTS.md").write_text(
        "| 9007 | 事件驱动 API | `task_event_driven.py` | verified | `GET /health` | 当前事件驱动核心。 |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(architecture_link_check, "SCRIPT_DIR", tmp_path)

    check = ArchitectureLinkCheck()
    check._check_ports_doc_consistency()

    assert check.results["ports_doc"]["status"] == "mismatch"
    assert check.results["ports_doc"]["missing_verified_ports"] == [9008, 9009]


def test_ports_doc_consistency_passes_for_expected_verified_ports(tmp_path, monkeypatch):
    source_ports = Path("PORTS.md").read_text(encoding="utf-8")
    (tmp_path / "PORTS.md").write_text(source_ports, encoding="utf-8")
    monkeypatch.setattr(architecture_link_check, "SCRIPT_DIR", tmp_path)

    check = ArchitectureLinkCheck()
    check._check_ports_doc_consistency()

    assert check.results["ports_doc"]["status"] == "ok"
    assert check.results["ports_doc"]["verified_ports"] == [9007, 9008, 9009]
