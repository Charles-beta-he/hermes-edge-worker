#!/usr/bin/env python3
"""architecture_link_check event payload contract tests."""

from architecture_link_check import ArchitectureLinkCheck


def test_task_event_link_payload_has_explicit_unique_event_id():
    check = ArchitectureLinkCheck()

    first = check._task_event_link_payload()
    second = check._task_event_link_payload()

    assert first["event_type"] == "task.created"
    assert first["event_data"]["task_id"] == "test-task-001"
    assert first["event_data"]["event_id"].startswith("architecture-link-check-")
    assert first["event_data"]["event_id"] != second["event_data"]["event_id"]
