#!/usr/bin/env python3
"""Shared token + HMAC request authentication for Hermes local APIs."""

import hashlib
import hmac
import time
from urllib.parse import urlparse


_PLACEHOLDERS = {"", "your-secret-token", "changeme", "change-me", "token", "secret"}


def is_placeholder_secret(value) -> bool:
    if not value:
        return True
    return str(value).strip().lower() in _PLACEHOLDERS


class RequestAuthenticator:
    def __init__(self, token=None, hmac_secret=None, max_skew_seconds: int = 300, nonce_cache_max: int = 10000):
        self.token = None if is_placeholder_secret(token) else str(token)
        self.hmac_secret = None if is_placeholder_secret(hmac_secret) else str(hmac_secret)
        self.max_skew_seconds = int(max_skew_seconds or 300)
        self.nonce_cache_max = int(nonce_cache_max or 10000)
        self.nonce_cache = {}

    @property
    def token_required(self):
        return not is_placeholder_secret(self.token)

    @property
    def hmac_required(self):
        return not is_placeholder_secret(self.hmac_secret)

    def authorize(self, request, body=b'') -> bool:
        return self.authorize_token(request) and self.authorize_hmac(request, body)

    def authorize_token(self, request) -> bool:
        if not self.token_required:
            return True
        expected = str(self.token)
        headers = getattr(request, "headers", {}) or {}
        auth = headers.get("Authorization", "")
        header_token = headers.get("X-Hermes-Token", "")
        if auth.startswith("Bearer "):
            return hmac.compare_digest(auth[len("Bearer "):].strip(), expected)
        return hmac.compare_digest(header_token, expected)

    def authorize_hmac(self, request, body=b'') -> bool:
        if not self.hmac_required:
            return True
        if isinstance(body, str):
            body = body.encode()
        headers = getattr(request, "headers", {}) or {}
        timestamp = headers.get("X-Hermes-Timestamp", "")
        nonce = headers.get("X-Hermes-Nonce", "")
        signature = headers.get("X-Hermes-Signature", "")
        if not timestamp or not nonce or not signature:
            return False
        try:
            timestamp_value = float(timestamp)
        except ValueError:
            return False
        if abs(time.time() - timestamp_value) > float(self.max_skew_seconds):
            return False
        self.prune_nonce_cache()
        if nonce in self.nonce_cache:
            return False
        method = (getattr(request, "command", "POST") or "POST").upper()
        path = urlparse(getattr(request, "path", "") or "").path
        payload = method.encode() + b"\n" + path.encode() + b"\n" + timestamp.encode() + b"\n" + nonce.encode() + b"\n" + (body or b"")
        expected = hmac.new(str(self.hmac_secret).encode(), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False
        self.nonce_cache[nonce] = timestamp_value
        return True

    def prune_nonce_cache(self):
        now = time.time()
        expired = [nonce for nonce, seen_at in self.nonce_cache.items() if abs(now - float(seen_at)) > float(self.max_skew_seconds)]
        for nonce in expired:
            self.nonce_cache.pop(nonce, None)
        if len(self.nonce_cache) <= self.nonce_cache_max:
            return
        overflow = len(self.nonce_cache) - self.nonce_cache_max
        for nonce, _seen_at in sorted(self.nonce_cache.items(), key=lambda item: item[1])[:overflow]:
            self.nonce_cache.pop(nonce, None)

    def security_summary(self):
        return {
            "auth_required": self.token_required,
            "hmac_required": self.hmac_required,
            "hmac_max_skew_seconds": self.max_skew_seconds,
            "hmac_nonce_cache_size": len(self.nonce_cache),
            "hmac_nonce_cache_max": self.nonce_cache_max,
        }
