#!/usr/bin/env python3
"""简化网关测试。"""

import json
from io import BytesIO

from simplified.simplified_gateway import SimplifiedGatewayHandler


class DummyHandler(SimplifiedGatewayHandler):
    def __init__(self):
        self.status = None
        self.headers_sent = []
        self.body = BytesIO()
        self.wfile = self.body

    def send_response(self, code, message=None):
        self.status = code

    def send_header(self, keyword, value):
        self.headers_sent.append((keyword, value))

    def end_headers(self):
        pass


def test_health_response_reports_component_presence():
    handler = DummyHandler()
    DummyHandler.data_layer = object()
    DummyHandler.event_bus = object()
    DummyHandler.knowledge_manager = None
    DummyHandler.rag_manager = object()

    handler._handle_health()

    assert handler.status == 200
    payload = json.loads(handler.body.getvalue().decode("utf-8"))
    assert payload["status"] == "ok"
    assert payload["components"]["data_layer"] is True
    assert payload["components"]["knowledge_manager"] is False


def test_send_error_returns_json_error_body():
    handler = DummyHandler()

    handler._send_error(404, "Not found")

    assert handler.status == 404
    payload = json.loads(handler.body.getvalue().decode("utf-8"))
    assert payload == {"error": "Not found"}
