#!/usr/bin/env python3
"""Shared request security tests for event APIs."""

import hashlib
import hmac
import time

from request_security import RequestAuthenticator


class DummyRequest:
    def __init__(self, headers=None, path="/event", command="POST"):
        self.headers = headers or {}
        self.path = path
        self.command = command


def signed_headers(body, token="event-token", secret="event-hmac", nonce="event-nonce", timestamp=None):
    timestamp = str(timestamp or int(time.time()))
    payload = b"POST\n/event\n" + timestamp.encode() + b"\n" + nonce.encode() + b"\n" + body
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return {
        "Authorization": f"Bearer {token}",
        "X-Hermes-Timestamp": timestamp,
        "X-Hermes-Nonce": nonce,
        "X-Hermes-Signature": signature,
    }


def test_request_authenticator_requires_token_when_configured():
    auth = RequestAuthenticator(token="event-token")

    assert auth.authorize_token(DummyRequest()) is False
    assert auth.authorize_token(DummyRequest({"Authorization": "Bearer event-token"})) is True


def test_request_authenticator_validates_hmac_nonce_and_replay_window():
    body = b'{"event_type":"task.created","event_data":{"task_id":"t1"}}'
    auth = RequestAuthenticator(token="event-token", hmac_secret="event-hmac", max_skew_seconds=300)
    request = DummyRequest(signed_headers(body, nonce="n1"))

    assert auth.authorize(request, body) is True
    assert auth.authorize(request, body) is False


def test_request_authenticator_rejects_old_timestamp():
    body = b"{}"
    auth = RequestAuthenticator(token="event-token", hmac_secret="event-hmac", max_skew_seconds=300)
    request = DummyRequest(signed_headers(body, nonce="old", timestamp=int(time.time()) - 3600))

    assert auth.authorize(request, body) is False
