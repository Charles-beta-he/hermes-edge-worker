#!/usr/bin/env python3
"""Edge Worker 安全边界测试。"""

from pathlib import Path

import edge_worker


class DummyHandler(edge_worker.EdgeWorkerHandler):
    def __init__(self):
        pass


def configure_security(tmp_path):
    edge_worker.SECURITY_TOKEN = "secret-token"
    edge_worker.ALLOWED_COMMANDS = ["echo", "python3 -V"]
    edge_worker.ALLOWED_PATHS = [str(tmp_path)]
    edge_worker.MAX_TIMEOUT = 2


def test_bearer_token_is_required_for_mutating_requests(tmp_path):
    configure_security(tmp_path)
    handler = DummyHandler()
    handler.headers = {}

    assert handler._is_authorized() is False

    handler.headers = {"Authorization": "Bearer secret-token"}
    assert handler._is_authorized() is True


def test_command_allowlist_blocks_unapproved_shell(tmp_path):
    configure_security(tmp_path)
    handler = DummyHandler()

    denied = handler._run_command("rm -rf /tmp/not-real", cwd=str(tmp_path), timeout=1)
    assert denied["success"] is False
    assert denied["error"] == "Command not allowed"

    allowed = handler._run_command("echo ok", cwd=str(tmp_path), timeout=1)
    assert allowed["success"] is True
    assert "ok" in allowed["stdout"]


def test_file_access_is_sandboxed_to_allowed_paths(tmp_path):
    configure_security(tmp_path)
    handler = DummyHandler()
    allowed_file = tmp_path / "allowed.txt"

    write_result = handler._write_file(str(allowed_file), "ok")
    assert write_result["success"] is True
    assert allowed_file.read_text() == "ok"

    read_result = handler._read_file(str(allowed_file))
    assert read_result["success"] is True
    assert read_result["content"] == "ok"

    outside = Path("/tmp/hermes-edge-worker-outside.txt")
    denied = handler._write_file(str(outside), "no")
    assert denied["success"] is False
    assert denied["error"] == "Path not allowed"


def test_timeout_is_capped_by_configuration(tmp_path):
    configure_security(tmp_path)
    handler = DummyHandler()

    result = handler._run_command("echo capped", cwd=str(tmp_path), timeout=999)
    assert result["success"] is True
    assert result["timeout"] == 2
