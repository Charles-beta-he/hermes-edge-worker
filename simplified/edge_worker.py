#!/usr/bin/env python3
"""
Hermes Edge Worker — 本地执行代理

接收 Brain API 的指令，在本地执行，返回结果。

Usage:
  python3 edge_worker.py                         # 启动在 localhost:9000
  python3 edge_worker.py --brain-url http://localhost:8000
  python3 edge_worker.py --port 9000 --host 0.0.0.0  # 局域网可访问

Endpoints:
  POST /execute    → 执行任务
  POST /command    → 执行单个指令
  GET  /health     → 健康检查
  GET  /info       → 能力信息
"""
import json
import os
import subprocess
import sys
import time
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

BRAIN_URL = None
WORKER_NAME = None


class EdgeWorkerHandler(BaseHTTPRequestHandler):
    """HTTP handler for Edge Worker."""
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == '/health':
            self._json({'status': 'ok', 'worker': WORKER_NAME, 'timestamp': datetime.now(timezone.utc).isoformat()})
        elif path == '/info':
            self._json({
                'name': WORKER_NAME,
                'capabilities': ['run_command', 'read_file', 'write_file', 'list_dir', 'browser_screenshot'],
                'platform': sys.platform,
                'cwd': os.getcwd(),
                'home': str(Path.home()),
            })
        else:
            self._json({'error': 'Not found'}, 404)
    
    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()
        
        if path == '/execute':
            task = body.get('task', {})
            result = self._execute_task(task)
            self._json(result)
        
        elif path == '/command':
            result = self._execute_command(body)
            self._json(result)
        
        else:
            self._json({'error': 'Not found'}, 404)
    
    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))
    
    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode())
    
    def _execute_task(self, task):
        """Execute a full task."""
        task_id = task.get('task_id', 'unknown')
        title = task.get('title', '')
        print(f"[Execute] Task: {task_id} - {title}")
        
        # Simple task execution: run a command if provided
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
        elif action == 'read_file':
            return self._read_file(params.get('path'))
        elif action == 'write_file':
            return self._write_file(params.get('path'), params.get('content'))
        elif action == 'list_dir':
            return self._list_dir(params.get('path'))
        else:
            # Try as a direct command
            command = body.get('command')
            if command:
                return self._run_command(command, body.get('cwd'), body.get('timeout', 60))
            return {'success': False, 'error': f'Unknown action: {action}'}
    
    def _run_command(self, command, cwd=None, timeout=60):
        """Execute a shell command."""
        if not command:
            return {'success': False, 'error': 'No command provided'}
        
        print(f"[Command] {command[:80]}...")
        try:
            r = subprocess.run(
                command, shell=True,
                capture_output=True, text=True,
                timeout=timeout,
                cwd=cwd or str(Path.home()),
            )
            return {
                'success': r.returncode == 0,
                'stdout': r.stdout[-5000:] if len(r.stdout) > 5000 else r.stdout,
                'stderr': r.stderr[-2000:] if len(r.stderr) > 2000 else r.stderr,
                'exit_code': r.returncode,
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': f'Timeout ({timeout}s)'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _read_file(self, path):
        """Read a file."""
        if not path:
            return {'success': False, 'error': 'No path provided'}
        p = Path(path).expanduser()
        if not p.exists():
            return {'success': False, 'error': f'File not found: {path}'}
        try:
            content = p.read_text(errors='replace')
            return {'success': True, 'content': content[:100000], 'size': len(content)}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _write_file(self, path, content):
        """Write a file."""
        if not path:
            return {'success': False, 'error': 'No path provided'}
        p = Path(path).expanduser()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
            return {'success': True, 'path': str(p), 'size': len(content)}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _list_dir(self, path):
        """List directory contents."""
        if not path:
            return {'success': False, 'error': 'No path provided'}
        p = Path(path).expanduser()
        if not p.exists():
            return {'success': False, 'error': f'Directory not found: {path}'}
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


def heartbeat_loop():
    """Periodically send heartbeat to Brain API."""
    if not BRAIN_URL:
        return
    import urllib.request
    while True:
        try:
            url = f"{BRAIN_URL}/edge/heartbeat"
            data = json.dumps({'name': WORKER_NAME}).encode()
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
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
        }).encode()
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req, timeout=5)
        result = json.loads(resp.read())
        print(f"[Edge] Registered with Brain: {result}")
    except Exception as e:
        print(f"[Edge] Failed to register: {e}")


args_port = 9000


def load_config():
    """Load config.yaml if it exists (stdlib only, no pyyaml dependency)."""
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        return {}
    config = {}
    try:
        import yaml
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}
        # Flatten nested config
        if 'worker' in raw:
            config.update({k: v for k, v in raw['worker'].items() if v is not None})
        if 'security' in raw and 'token' in raw['security']:
            config.setdefault('token', raw['security']['token'])
    except ImportError:
        # Fallback: simple regex parser for flat YAML
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or ':' not in line:
                    continue
                key, _, val = line.partition(':')
                key, val = key.strip(), val.strip().strip('"').strip("'")
                if val.lower() == 'true':
                    val = True
                elif val.lower() == 'false':
                    val = False
                elif val.isdigit():
                    val = int(val)
                config[key] = val
    except Exception:
        pass
    return config


def main():
    global BRAIN_URL, WORKER_NAME, args_port
    
    # Load config.yaml first (provides defaults)
    cfg = load_config()
    
    import argparse
    parser = argparse.ArgumentParser(description='Hermes Edge Worker')
    parser.add_argument('--host', default=cfg.get('host', '0.0.0.0'))
    parser.add_argument('--port', type=int, default=int(cfg.get('port', 9002)))
    parser.add_argument('--brain-url', default=cfg.get('main_node'), help='Brain API URL (e.g., http://localhost:8000)')
    parser.add_argument('--name', default=cfg.get('name', 'local-worker'), help='Worker name')
    args = parser.parse_args()
    
    BRAIN_URL = args.brain_url
    WORKER_NAME = args.name
    args_port = args.port
    
    # Register with brain
    register_with_brain()
    
    # Start heartbeat thread
    if BRAIN_URL:
        t = threading.Thread(target=heartbeat_loop, daemon=True)
        t.start()
    
    # Start server
    server = HTTPServer((args.host, args.port), EdgeWorkerHandler)
    print(f"Hermes Edge Worker '{WORKER_NAME}' running on {args.host}:{args.port}")
    if BRAIN_URL:
        print(f"Connected to Brain: {BRAIN_URL}")
    print(f"Capabilities: run_command, read_file, write_file, list_dir")
    print(f"Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == '__main__':
    main()
