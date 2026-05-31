#!/usr/bin/env python3
"""
Hermes Edge Worker — 本地执行代理

接收 Brain API 的指令，在本地执行，返回结果。

安全原则：
- /health 默认开放；其他端点在配置 token 后必须认证。
- run_command 必须命中 allowed_commands allowlist。
- read_file/write_file/list_dir 必须位于 allowed_paths sandbox 内。
- timeout 被 max_timeout 封顶。

Usage:
  python3 edge_worker.py
  python3 edge_worker.py --brain-url http://localhost:8000
  python3 edge_worker.py --port 9000 --host 0.0.0.0
  HERMES_EDGE_TOKEN=... python3 edge_worker.py --token ...

Endpoints:
  POST /execute    → 执行任务
  POST /command    → 执行单个指令
  GET  /health     → 健康检查
  GET  /info       → 能力信息
"""
import argparse
import hashlib
import hmac
import json
import os
import shlex
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

BRAIN_URL = None
WORKER_NAME = None
SECURITY_TOKEN = None
HMAC_SECRET = None
HMAC_MAX_SKEW_SECONDS = 300
ALLOWED_COMMANDS = []
ALLOWED_PATHS = []
MAX_TIMEOUT = 300


def _is_placeholder_secret(value):
    if not value:
        return True
    normalized = str(value).strip().lower()
    return normalized in {"", "your-secret-token", "changeme", "change-me", "token", "secret"}


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        if value.startswith("[") and value.endswith("]"):
            try:
                parsed = json.loads(value.replace("'", '"'))
                return _as_list(parsed)
            except Exception:
                pass
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value)]


def _safe_resolve(path):
    return Path(path).expanduser().resolve(strict=False)


class EdgeWorkerHandler(BaseHTTPRequestHandler):
    """HTTP handler for Edge Worker."""

    def do_GET(self):
        path = urlparse(self.path).path

        if path == '/health':
            self._json({'status': 'ok', 'worker': WORKER_NAME, 'timestamp': datetime.now(timezone.utc).isoformat()})
            return

        if not self._is_authorized():
            self._json({'success': False, 'error': 'Unauthorized'}, 401)
            return

        if path == '/info':
            self._json({
                'name': WORKER_NAME,
                'capabilities': ['run_command', 'read_file', 'write_file', 'list_dir', 'browser_screenshot'],
                'platform': sys.platform,
                'cwd': os.getcwd(),
                'security': {
                    'auth_required': not _is_placeholder_secret(SECURITY_TOKEN),
                    'hmac_required': not _is_placeholder_secret(HMAC_SECRET),
                    'hmac_max_skew_seconds': HMAC_MAX_SKEW_SECONDS,
                    'allowed_commands': ALLOWED_COMMANDS,
                    'allowed_paths': ALLOWED_PATHS,
                    'max_timeout': MAX_TIMEOUT,
                },
            })
        else:
            self._json({'error': 'Not found'}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if not self._is_authorized():
            self._json({'success': False, 'error': 'Unauthorized'}, 401)
            return

        raw_body = self._read_raw_body()
        if not self._is_hmac_authorized(raw_body):
            self._json({'success': False, 'error': 'Invalid signature'}, 401)
            return
        body = json.loads(raw_body.decode() or '{}') if raw_body else {}

        if path == '/execute':
            task = body.get('task', {})
            result = self._execute_task(task)
            self._json(result)
        elif path == '/command':
            result = self._execute_command(body)
            self._json(result)
        else:
            self._json({'error': 'Not found'}, 404)

    def _is_authorized(self, body=b''):
        """Return True when token auth and optional HMAC signature are valid."""
        if not self._is_token_authorized():
            return False
        return self._is_hmac_authorized(body)

    def _is_token_authorized(self):
        """Return True when no production token is configured or request has a valid token."""
        if _is_placeholder_secret(SECURITY_TOKEN):
            return True
        expected = str(SECURITY_TOKEN)
        auth = self.headers.get('Authorization', '') if hasattr(self, 'headers') else ''
        header_token = self.headers.get('X-Hermes-Token', '') if hasattr(self, 'headers') else ''
        if auth.startswith('Bearer '):
            return hmac.compare_digest(auth[len('Bearer '):].strip(), expected)
        return hmac.compare_digest(header_token, expected)

    def _is_hmac_authorized(self, body=b''):
        """Validate optional HMAC signature over method/path/timestamp/body."""
        if _is_placeholder_secret(HMAC_SECRET):
            return True
        if isinstance(body, str):
            body = body.encode()
        timestamp = self.headers.get('X-Hermes-Timestamp', '') if hasattr(self, 'headers') else ''
        signature = self.headers.get('X-Hermes-Signature', '') if hasattr(self, 'headers') else ''
        if not timestamp or not signature:
            return False
        try:
            timestamp_value = float(timestamp)
        except ValueError:
            return False
        if abs(time.time() - timestamp_value) > float(HMAC_MAX_SKEW_SECONDS or 300):
            return False
        method = getattr(self, 'command', 'POST') or 'POST'
        path = urlparse(getattr(self, 'path', '') or '').path
        payload = method.upper().encode() + b'\n' + path.encode() + b'\n' + timestamp.encode() + b'\n' + (body or b'')
        expected = hmac.new(str(HMAC_SECRET).encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)

    def _read_raw_body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length == 0:
            return b''
        return self.rfile.read(length)

    def _read_body(self):
        raw = self._read_raw_body()
        if not raw:
            return {}
        return json.loads(raw)

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode())

    def _execute_task(self, task):
        """Execute a full task. Final lifecycle state remains Brain-owned."""
        task_id = task.get('task_id', 'unknown')
        title = task.get('title', '')
        print(f"[Execute] Task: {task_id} - {title}")

        command = task.get('command')
        if command:
            return self._run_command(command, task.get('cwd'), task.get('timeout', 60))

        return {'success': True, 'task_id': task_id, 'message': 'Task received (no command to execute)'}

    def _execute_command(self, body):
        """Execute a single command."""
        action = body.get('action', '')
        params = body.get('params', body)

        if action == 'run_command':
            return self._run_command(params.get('command'), params.get('cwd'), params.get('timeout', 60))
        if action == 'read_file':
            return self._read_file(params.get('path'))
        if action == 'write_file':
            return self._write_file(params.get('path'), params.get('content'))
        if action == 'list_dir':
            return self._list_dir(params.get('path'))

        command = body.get('command')
        if command:
            return self._run_command(command, body.get('cwd'), body.get('timeout', 60))
        return {'success': False, 'error': f'Unknown action: {action}'}

    def _command_allowed(self, command):
        if not command:
            return False
        allowed = _as_list(ALLOWED_COMMANDS)
        if not allowed:
            return False
        try:
            first_token = shlex.split(command)[0]
        except Exception:
            return False
        for rule in allowed:
            rule = rule.strip()
            if not rule:
                continue
            if command == rule or command.startswith(rule + ' '):
                return True
            if first_token == rule:
                return True
        return False

    def _path_allowed(self, path):
        if not path:
            return False
        allowed_paths = _as_list(ALLOWED_PATHS)
        if not allowed_paths:
            return False
        target = _safe_resolve(path)
        for allowed in allowed_paths:
            base = _safe_resolve(allowed)
            try:
                target.relative_to(base)
                return True
            except ValueError:
                continue
        return False

    def _bounded_timeout(self, timeout):
        try:
            requested = int(timeout or 60)
        except Exception:
            requested = 60
        return max(1, min(requested, int(MAX_TIMEOUT or 300)))

    def _run_command(self, command, cwd=None, timeout=60):
        """Execute an allowlisted shell command."""
        if not command:
            return {'success': False, 'error': 'No command provided'}
        if not self._command_allowed(command):
            return {'success': False, 'error': 'Command not allowed'}
        if cwd and not self._path_allowed(cwd):
            return {'success': False, 'error': 'Path not allowed'}

        bounded_timeout = self._bounded_timeout(timeout)
        run_cwd = cwd or (ALLOWED_PATHS[0] if ALLOWED_PATHS else str(Path.home()))
        print(f"[Command] {command[:80]}...")
        try:
            r = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=bounded_timeout,
                cwd=run_cwd,
            )
            return {
                'success': r.returncode == 0,
                'stdout': r.stdout[-5000:] if len(r.stdout) > 5000 else r.stdout,
                'stderr': r.stderr[-2000:] if len(r.stderr) > 2000 else r.stderr,
                'exit_code': r.returncode,
                'timeout': bounded_timeout,
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': f'Timeout ({bounded_timeout}s)', 'timeout': bounded_timeout}
        except Exception as e:
            return {'success': False, 'error': str(e), 'timeout': bounded_timeout}

    def _read_file(self, path):
        """Read a sandboxed file."""
        if not path:
            return {'success': False, 'error': 'No path provided'}
        if not self._path_allowed(path):
            return {'success': False, 'error': 'Path not allowed'}
        p = _safe_resolve(path)
        if not p.exists():
            return {'success': False, 'error': f'File not found: {path}'}
        if not p.is_file():
            return {'success': False, 'error': f'Not a file: {path}'}
        try:
            content = p.read_text(errors='replace')
            return {'success': True, 'content': content[:100000], 'size': len(content)}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _write_file(self, path, content):
        """Write a sandboxed file."""
        if not path:
            return {'success': False, 'error': 'No path provided'}
        if not self._path_allowed(path):
            return {'success': False, 'error': 'Path not allowed'}
        p = _safe_resolve(path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content or '')
            return {'success': True, 'path': str(p), 'size': len(content or '')}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _list_dir(self, path):
        """List sandboxed directory contents."""
        if not path:
            return {'success': False, 'error': 'No path provided'}
        if not self._path_allowed(path):
            return {'success': False, 'error': 'Path not allowed'}
        p = _safe_resolve(path)
        if not p.exists():
            return {'success': False, 'error': f'Directory not found: {path}'}
        if not p.is_dir():
            return {'success': False, 'error': f'Not a directory: {path}'}
        try:
            entries = []
            for item in sorted(p.iterdir()):
                entries.append({
                    'name': item.name,
                    'type': 'dir' if item.is_dir() else 'file',
                    'size': item.stat().st_size if item.is_file() else 0,
                })
            return {'success': True, 'entries': entries[:200]}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def log_message(self, format, *args):
        pass


def _auth_headers():
    if _is_placeholder_secret(SECURITY_TOKEN):
        return {'Content-Type': 'application/json'}
    return {'Content-Type': 'application/json', 'Authorization': f'Bearer {SECURITY_TOKEN}'}


def heartbeat_loop():
    """Periodically send heartbeat to Brain API."""
    if not BRAIN_URL:
        return
    import urllib.request
    while True:
        try:
            url = f"{BRAIN_URL}/edge/heartbeat"
            data = json.dumps({'name': WORKER_NAME}).encode()
            req = urllib.request.Request(url, data=data, headers=_auth_headers())
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass
        time.sleep(30)


def register_with_brain():
    """Register this worker with Brain API."""
    if not BRAIN_URL:
        print("[Edge] No brain URL, running standalone")
        return

    import urllib.request
    try:
        url = f"{BRAIN_URL}/edge/register"
        data = json.dumps({
            'name': WORKER_NAME,
            'url': f'http://localhost:{args_port}',
            'capabilities': ['run_command', 'read_file', 'write_file', 'list_dir'],
            'security': {
                'auth_required': not _is_placeholder_secret(SECURITY_TOKEN),
                'hmac_required': not _is_placeholder_secret(HMAC_SECRET),
                'hmac_max_skew_seconds': HMAC_MAX_SKEW_SECONDS,
                'allowed_commands': ALLOWED_COMMANDS,
                'allowed_paths': ALLOWED_PATHS,
                'max_timeout': MAX_TIMEOUT,
            },
        }).encode()
        req = urllib.request.Request(url, data=data, headers=_auth_headers())
        resp = urllib.request.urlopen(req, timeout=5)
        result = json.loads(resp.read())
        print(f"[Edge] Registered with Brain: {result}")
    except Exception as e:
        print(f"[Edge] Failed to register: {e}")


args_port = 9000


def load_config():
    """Load config.yaml if it exists."""
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        import yaml
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}
        config = {}
        if 'worker' in raw:
            config.update({k: v for k, v in raw['worker'].items() if v is not None})
        if 'security' in raw:
            config.update({k: v for k, v in raw['security'].items() if v is not None})
        return config
    except Exception:
        config = {}
        current_section = None
        with open(config_path) as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    continue
                if not line.startswith(' ') and stripped.endswith(':'):
                    current_section = stripped[:-1]
                    continue
                if ':' not in stripped:
                    continue
                key, _, val = stripped.partition(':')
                key = key.strip()
                val = val.split('#', 1)[0].strip().strip('"').strip("'")
                if val.lower() == 'true':
                    val = True
                elif val.lower() == 'false':
                    val = False
                elif val.isdigit():
                    val = int(val)
                if current_section in {'worker', 'security'}:
                    config[key] = val
        return config


def configure_runtime(args, cfg):
    global BRAIN_URL, WORKER_NAME, args_port, SECURITY_TOKEN, HMAC_SECRET, HMAC_MAX_SKEW_SECONDS, ALLOWED_COMMANDS, ALLOWED_PATHS, MAX_TIMEOUT
    BRAIN_URL = args.brain_url
    WORKER_NAME = args.name
    args_port = args.port
    token = args.token or os.environ.get('HERMES_EDGE_TOKEN') or cfg.get('token')
    hmac_secret = args.hmac_secret or os.environ.get('HERMES_EDGE_HMAC_SECRET') or cfg.get('hmac_secret')
    SECURITY_TOKEN = None if _is_placeholder_secret(token) else str(token)
    HMAC_SECRET = None if _is_placeholder_secret(hmac_secret) else str(hmac_secret)
    HMAC_MAX_SKEW_SECONDS = int(args.hmac_max_skew_seconds or os.environ.get('HERMES_EDGE_HMAC_MAX_SKEW_SECONDS') or cfg.get('hmac_max_skew_seconds') or 300)
    ALLOWED_COMMANDS = _as_list(args.allowed_command) or _as_list(cfg.get('allowed_commands'))
    ALLOWED_PATHS = _as_list(args.allowed_path) or _as_list(cfg.get('allowed_paths')) or [str(Path.home())]
    MAX_TIMEOUT = int(args.max_timeout or cfg.get('max_timeout') or 300)


def main():
    cfg = load_config()

    parser = argparse.ArgumentParser(description='Hermes Edge Worker')
    parser.add_argument('--host', default=cfg.get('host', '0.0.0.0'))
    parser.add_argument('--port', type=int, default=int(cfg.get('port', 9002)))
    parser.add_argument('--brain-url', default=cfg.get('main_node') or cfg.get('brain_url'), help='Brain API URL')
    parser.add_argument('--name', default=cfg.get('name', 'local-worker'), help='Worker name')
    parser.add_argument('--token', default=None, help='Bearer token required by /info, /execute and /command')
    parser.add_argument('--hmac-secret', default=None, help='Optional HMAC secret required for POST body signatures')
    parser.add_argument('--hmac-max-skew-seconds', type=int, default=None, help='Maximum allowed HMAC timestamp skew; default 300 seconds')
    parser.add_argument('--allowed-command', action='append', default=[], help='Allowed shell command prefix/token; repeatable')
    parser.add_argument('--allowed-path', action='append', default=[], help='Allowed filesystem sandbox path; repeatable')
    parser.add_argument('--max-timeout', type=int, default=None, help='Maximum command timeout seconds')
    args = parser.parse_args()

    configure_runtime(args, cfg)

    register_with_brain()

    if BRAIN_URL:
        t = threading.Thread(target=heartbeat_loop, daemon=True)
        t.start()

    server = HTTPServer((args.host, args.port), EdgeWorkerHandler)
    print(f"Hermes Edge Worker '{WORKER_NAME}' running on {args.host}:{args.port}")
    if BRAIN_URL:
        print(f"Connected to Brain: {BRAIN_URL}")
    print("Capabilities: run_command, read_file, write_file, list_dir")
    print(f"Security: auth_required={not _is_placeholder_secret(SECURITY_TOKEN)}, hmac_required={not _is_placeholder_secret(HMAC_SECRET)}, hmac_max_skew_seconds={HMAC_MAX_SKEW_SECONDS}, allowed_commands={ALLOWED_COMMANDS}, allowed_paths={ALLOWED_PATHS}, max_timeout={MAX_TIMEOUT}")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == '__main__':
    main()
