#!/usr/bin/env python3
"""architecture_link_check event observability tests."""

from architecture_link_check import ArchitectureLinkCheck


class DummyResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_event_reliability_metrics_are_collected(monkeypatch):
    calls = []

    def fake_get(url, timeout=5):
        calls.append(url)
        if url == "http://localhost:9007/metrics":
            return DummyResponse(200, {"duplicates": 2, "dead_lettered": 1, "retries": 3, "security": {"auth_required": True}})
        if url == "http://localhost:9008/metrics":
            return DummyResponse(200, {"duplicates": 4, "dead_letters": 5, "errors": 6, "security": {"hmac_required": True}})
        raise AssertionError(url)

    monkeypatch.setattr("architecture_link_check.requests.get", fake_get)
    check = ArchitectureLinkCheck()
    check._check_event_reliability_metrics()

    assert check.results["event_reliability"]["event_driven"]["duplicates"] == 2
    assert check.results["event_reliability"]["event_driven"]["dead_letters"] == 1
    assert check.results["event_reliability"]["task_pool_integration"]["dead_letters"] == 5
    assert check.results["event_reliability"]["task_pool_integration"]["security"]["hmac_required"] is True
    assert calls == ["http://localhost:9007/metrics", "http://localhost:9008/metrics"]
