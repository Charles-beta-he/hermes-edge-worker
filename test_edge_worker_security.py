#!/usr/bin/env python3
"""Edge Worker 安全边界测试。"""

import hashlib
import hmac
import json
import time
from pathlib import Path

import edge_worker


class DummyHandler(edge_worker.EdgeWorkerHandler):
    def __init__(self):
        pass


def configure_security(tmp_path):
    edge_worker.SECURITY_TOKEN = "secret-token"
    edge_worker.HMAC_SECRET = None
    edge_worker.HMAC_NONCE_CACHE.clear()
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


def test_hmac_signature_is_required_when_secret_is_configured(tmp_path):
    configure_security(tmp_path)
    edge_worker.HMAC_SECRET = "hmac-secret"
    body = json.dumps({"action": "run_command", "params": {"command": "echo ok"}}, sort_keys=True).encode()
    timestamp = str(int(time.time()))
    handler = DummyHandler()
    handler.path = "/command"
    handler.command = "POST"
    handler.headers = {"Authorization": "Bearer secret-token", "X-Hermes-Timestamp": timestamp, "X-Hermes-Nonce": "nonce-required"}

    assert handler._is_authorized(body) is False

    payload = b"POST\n/command\n" + timestamp.encode() + b"\nnonce-required\n" + body
    signature = hmac.new(b"hmac-secret", payload, hashlib.sha256).hexdigest()
    handler.headers["X-Hermes-Signature"] = signature

    assert handler._is_authorized(body) is True


def _signed_headers(body, timestamp, nonce="nonce-1"):
    payload = b"POST\n/command\n" + str(timestamp).encode() + b"\n" + str(nonce).encode() + b"\n" + body
    signature = hmac.new(b"hmac-secret", payload, hashlib.sha256).hexdigest()
    return {
        "Authorization": "Bearer secret-token",
        "X-Hermes-Timestamp": str(timestamp),
        "X-Hermes-Nonce": str(nonce),
        "X-Hermes-Signature": signature,
    }


def test_hmac_signature_rejects_tampered_body(tmp_path):
    configure_security(tmp_path)
    edge_worker.HMAC_SECRET = "hmac-secret"
    timestamp = "1700000000"
    original_body = b'{"action":"run_command","params":{"command":"echo ok"}}'
    tampered_body = b'{"action":"run_command","params":{"command":"echo hacked"}}'
    payload = b"POST\n/command\n" + timestamp.encode() + b"\nnonce-tamper\n" + original_body
    signature = hmac.new(b"hmac-secret", payload, hashlib.sha256).hexdigest()
    handler = DummyHandler()
    handler.path = "/command"
    handler.command = "POST"
    handler.headers = {
        "Authorization": "Bearer secret-token",
        "X-Hermes-Timestamp": timestamp,
        "X-Hermes-Nonce": "nonce-tamper",
        "X-Hermes-Signature": signature,
    }

    assert handler._is_authorized(tampered_body) is False


def test_hmac_signature_rejects_timestamp_outside_replay_window(tmp_path):
    configure_security(tmp_path)
    edge_worker.HMAC_SECRET = "hmac-secret"
    edge_worker.HMAC_MAX_SKEW_SECONDS = 300
    body = b'{"action":"run_command","params":{"command":"echo ok"}}'
    handler = DummyHandler()
    handler.path = "/command"
    handler.command = "POST"
    handler.headers = _signed_headers(body, int(time.time()) - 3600)

    assert handler._is_authorized(body) is False


def test_hmac_signature_accepts_timestamp_inside_replay_window(tmp_path):
    configure_security(tmp_path)
    edge_worker.HMAC_SECRET = "hmac-secret"
    edge_worker.HMAC_MAX_SKEW_SECONDS = 300
    body = b'{"action":"run_command","params":{"command":"echo ok"}}'
    handler = DummyHandler()
    handler.path = "/command"
    handler.command = "POST"
    handler.headers = _signed_headers(body, int(time.time()), nonce="inside-window")

    assert handler._is_authorized(body) is True


def test_hmac_signature_rejects_reused_nonce_inside_window(tmp_path):
    configure_security(tmp_path)
    edge_worker.HMAC_SECRET = "hmac-secret"
    edge_worker.HMAC_MAX_SKEW_SECONDS = 300
    body = b'{"action":"run_command","params":{"command":"echo ok"}}'
    timestamp = int(time.time())
    handler = DummyHandler()
    handler.path = "/command"
    handler.command = "POST"
    handler.headers = _signed_headers(body, timestamp, nonce="replay-once")

    assert handler._is_authorized(body) is True
    assert handler._is_authorized(body) is False


def test_hmac_signature_rejects_missing_nonce_when_hmac_enabled(tmp_path):
    configure_security(tmp_path)
    edge_worker.HMAC_SECRET = "hmac-secret"
    body = b'{"action":"run_command","params":{"command":"echo ok"}}'
    timestamp = int(time.time())
    payload = b"POST\n/command\n" + str(timestamp).encode() + b"\n\n" + body
    signature = hmac.new(b"hmac-secret", payload, hashlib.sha256).hexdigest()
    handler = DummyHandler()
    handler.path = "/command"
    handler.command = "POST"
    handler.headers = {
        "Authorization": "Bearer secret-token",
        "X-Hermes-Timestamp": str(timestamp),
        "X-Hermes-Signature": signature,
    }

    assert handler._is_authorized(body) is False
