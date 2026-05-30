#!/usr/bin/env python3
"""
Hermes LAN Auto-Connect — 局域网自动发现与连接

Brain 启动后自动广播自己的位置。
Edge Worker 启动后自动发现 Brain 并连接。
无需手动配置 IP 地址。

Usage:
  # Brain 端（启动后自动广播）
  python3 hermes_lan.py brain --port 8000

  # Edge 端（启动后自动发现 Brain）
  python3 hermes_lan.py edge --port 9000

  # 仅发现（不启动服务）
  python3 hermes_lan.py discover

Protocol:
  Brain 每 5 秒通过 UDP 广播: {"type":"hermes-brain","port":8000,"name":"...","ts":"..."}
  Edge 监听 UDP 9999 端口，收到广播后自动注册
"""
import json
import os
import socket
import sys
import time
import threading
import signal
from datetime import datetime, timezone
from pathlib import Path

BROADCAST_PORT = 9999
BROADCAST_INTERVAL = 5  # 秒
DISCOVERY_TIMEOUT = 10  # 秒


def get_local_ip():
    """获取本机局域网 IP。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_broadcast_addr():
    """获取广播地址。"""
    ip = get_local_ip()
    parts = ip.split('.')
    return f'{parts[0]}.{parts[1]}.{parts[2]}.255'


def get_hostname():
    """获取主机名。"""
    return socket.gethostname()


# === Brain 端：广播自己的位置 ===

class BrainBroadcaster:
    """Brain 通过 UDP 广播自己的位置。"""
    
    def __init__(self, port: int, name: str = None):
        self.port = port
        self.name = name or get_hostname()
        self.local_ip = get_local_ip()
        self.running = False
    
    def start(self):
        """启动广播。"""
        self.running = True
        
        # 启动广播线程
        t = threading.Thread(target=self._broadcast_loop, daemon=True)
        t.start()
        
        print(f"[Brain] Broadcasting on LAN: {self.local_ip}:{self.port}")
        print(f"[Brain] Name: {self.name}")
        print(f"[Brain] Edge Workers can auto-discover this Brain")
    
    def stop(self):
        self.running = False
    
    def _broadcast_loop(self):
        """循环广播。"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        broadcast_addr = get_broadcast_addr()
        
        message = json.dumps({
            'type': 'hermes-brain',
            'ip': self.local_ip,
            'port': self.port,
            'name': self.name,
            'hostname': get_hostname(),
            'ts': datetime.now(timezone.utc).isoformat(),
        }).encode()
        
        while self.running:
            try:
                # 广播到局域网
                sock.sendto(message, (broadcast_addr, BROADCAST_PORT))
                # 也发到 localhost（同机 Edge Worker）
                sock.sendto(message, ('127.0.0.1', BROADCAST_PORT))
            except Exception as e:
                pass
            time.sleep(BROADCAST_INTERVAL)
        
        sock.close()


# === Edge 端：发现 Brain ===

class BrainDiscovery:
    """Edge Worker 自动发现 Brain。"""
    
    def __init__(self):
        self.discovered = {}  # ip -> brain info
    
    def discover(self, timeout: float = DISCOVERY_TIMEOUT) -> list:
        """发现 Brain：先尝试 UDP 广播，再尝试 TCP 探测。"""
        # 方法 1: UDP 广播
        brains = self._discover_udp(timeout=min(timeout, 3))
        if brains:
            return brains
        
        # 方法 2: TCP 探测本地子网
        brains = self._discover_tcp_probe(timeout=timeout)
        return brains
    
    def _discover_udp(self, timeout: float = 3) -> list:
        """通过 UDP 广播发现。"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass
        
        try:
            sock.bind(('0.0.0.0', BROADCAST_PORT))
        except OSError:
            return []
        
        sock.settimeout(timeout)
        
        brains = []
        start = time.time()
        
        while time.time() - start < timeout:
            try:
                data, addr = sock.recvfrom(4096)
                msg = json.loads(data.decode())
                if msg.get('type') == 'hermes-brain':
                    brain_ip = msg.get('ip', addr[0])
                    brain_port = msg.get('port', 8000)
                    key = f"{brain_ip}:{brain_port}"
                    if key not in self.discovered:
                        self.discovered[key] = msg
                        brains.append(msg)
            except socket.timeout:
                break
            except Exception:
                break
        
        sock.close()
        return brains
    
    def _discover_tcp_probe(self, timeout: float = 8) -> list:
        """通过 TCP 探测本地子网发现 Brain API。"""
        import urllib.request
        
        local_ip = get_local_ip()
        parts = local_ip.split('.')
        base = f'{parts[0]}.{parts[1]}.{parts[2]}'
        
        brains = []
        
        # 探测 localhost 和本机 IP
        candidates = ['127.0.0.1', local_ip]
        
        # 扫描子网常见端口 (8000)
        # 只探测前 20 个和后 5 个 IP（减少扫描时间）
        for i in list(range(1, 21)) + list(range(250, 256)):
            candidates.append(f'{base}.{i}')
        
        for ip in candidates:
            try:
                url = f'http://{ip}:8000/health'
                req = urllib.request.Request(url)
                resp = urllib.request.urlopen(req, timeout=0.5)
                data = json.loads(resp.read())
                if data.get('status') == 'ok':
                    brain = {'ip': ip, 'port': 8000, 'name': ip, 'type': 'hermes-brain'}
                    brains.append(brain)
                    self.discovered[f'{ip}:8000'] = brain
                    break  # 找到一个就够了
            except Exception:
                pass
        
        return brains
    
    def find_brain(self, timeout: float = DISCOVERY_TIMEOUT) -> str:
        """发现 Brain 并返回 URL。"""
        brains = self.discover(timeout)
        if brains:
            brain = brains[0]
            return f"http://{brain['ip']}:{brain['port']}"
        return None


# === 一键启动 ===

def start_brain(port: int, name: str = None):
    """启动 Brain API + 自动广播。"""
    # 导入 Brain API
    sys.path.insert(0, str(Path(__file__).parent))
    
    # 启动广播
    broadcaster = BrainBroadcaster(port, name)
    broadcaster.start()
    
    # 启动 Brain API
    from brain_api import BrainAPIHandler
    from http.server import HTTPServer
    
    server = HTTPServer(('0.0.0.0', port), BrainAPIHandler)
    print(f"[Brain] API running on 0.0.0.0:{port}")
    print(f"[Brain] LAN access: http://{get_local_ip()}:{port}")
    print()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Brain] Shutting down...")
        broadcaster.stop()
        server.shutdown()


def start_edge(port: int, brain_url: str = None, name: str = None):
    """启动 Edge Worker + 自动发现 Brain。"""
    sys.path.insert(0, str(Path(__file__).parent))
    
    # 自动发现 Brain
    if not brain_url:
        print("[Edge] Auto-discovering Brain on LAN...")
        discovery = BrainDiscovery()
        brain_url = discovery.find_brain(timeout=10)
        
        if brain_url:
            print(f"[Edge] Found Brain: {brain_url}")
        else:
            print("[Edge] No Brain found on LAN. Running standalone.")
            print("[Edge] Start Brain first: python3 hermes_lan.py brain --port 8000")
            brain_url = None
    
    # 启动 Edge Worker
    from edge_worker import EdgeWorkerHandler, register_with_brain, heartbeat_loop
    
    # 设置全局变量
    import edge_worker
    edge_worker.BRAIN_URL = brain_url
    edge_worker.WORKER_NAME = name or get_hostname()
    edge_worker.args_port = port
    
    # 注册到 Brain
    if brain_url:
        register_with_brain()
        t = threading.Thread(target=heartbeat_loop, daemon=True)
        t.start()
    
    from http.server import HTTPServer
    server = HTTPServer(('0.0.0.0', port), EdgeWorkerHandler)
    print(f"[Edge] Worker '{name or get_hostname()}' running on 0.0.0.0:{port}")
    if brain_url:
        print(f"[Edge] Connected to Brain: {brain_url}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Edge] Shutting down...")
        server.shutdown()


def discover_only():
    """仅发现，不启动服务。"""
    discovery = BrainDiscovery()
    brains = discovery.discover(timeout=10)
    
    if not brains:
        print("\nNo Hermes Brain found on LAN.")
        print("Start one: python3 hermes_lan.py brain --port 8000")
    else:
        print(f"\nFound {len(brains)} Brain(s):")
        for b in brains:
            print(f"  {b['name']} at {b['ip']}:{b['port']} (hostname: {b.get('hostname', '?')})")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Hermes LAN Auto-Connect')
    sub = parser.add_subparsers(dest='command')
    
    brain_cmd = sub.add_parser('brain', help='Start Brain with auto-broadcast')
    brain_cmd.add_argument('--port', type=int, default=8000)
    brain_cmd.add_argument('--name', default=None)
    
    edge_cmd = sub.add_parser('edge', help='Start Edge Worker with auto-discovery')
    edge_cmd.add_argument('--port', type=int, default=9000)
    edge_cmd.add_argument('--brain-url', default=None, help='Manual Brain URL (skip auto-discovery)')
    edge_cmd.add_argument('--name', default=None)
    
    sub.add_parser('discover', help='Discover Brains on LAN (no startup)')
    
    args = parser.parse_args()
    
    if args.command == 'brain':
        start_brain(args.port, args.name)
    elif args.command == 'edge':
        start_edge(args.port, args.brain_url, args.name)
    elif args.command == 'discover':
        discover_only()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
