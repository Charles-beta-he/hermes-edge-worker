#!/usr/bin/env python3
"""
多站点管理器
分布式多站点管理核心组件
"""

import json
import os
import sys
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

class MultiSiteManager:
    """多站点管理器"""
    
    def __init__(self, heartbeat_interval: int = 30, health_check_interval: int = 60):
        self.sites = {}
        self.heartbeat_interval = heartbeat_interval
        self.health_check_interval = health_check_interval
        self.load_balancer = LoadBalancer()
        self.failover_manager = FailoverManager(self)
        
        self.metrics = {
            "total_sites": 0,
            "online_sites": 0,
            "offline_sites": 0,
            "total_tasks_assigned": 0,
            "failover_count": 0
        }
        
        # 启动健康检查线程
        self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_check_thread.start()
    
    def register_site(self, site_id: str, site_info: Dict[str, Any]) -> bool:
        """注册站点"""
        try:
            self.sites[site_id] = {
                "id": site_id,
                "info": site_info,
                "status": "online",
                "last_heartbeat": datetime.now().isoformat(),
                "registered_at": datetime.now().isoformat(),
                "metrics": {
                    "tasks_completed": 0,
                    "tasks_failed": 0,
                    "average_execution_time": 0.0,
                    "cpu_usage": 0.0,
                    "memory_usage": 0.0,
                    "disk_usage": 0.0
                }
            }
            
            self._update_metrics()
            print(f"[注册] 站点注册成功: {site_id}")
            return True
        except Exception as e:
            print(f"[注册] 站点注册失败: {site_id}, 错误: {e}")
            return False
    
    def unregister_site(self, site_id: str) -> bool:
        """注销站点"""
        try:
            if site_id in self.sites:
                del self.sites[site_id]
                self._update_metrics()
                print(f"[注销] 站点注销成功: {site_id}")
                return True
            return False
        except Exception as e:
            print(f"[注销] 站点注销失败: {site_id}, 错误: {e}")
            return False
    
    def heartbeat(self, site_id: str, metrics: Dict[str, Any] = None) -> bool:
        """心跳检测"""
        try:
            if site_id in self.sites:
                self.sites[site_id]["last_heartbeat"] = datetime.now().isoformat()
                
                if metrics:
                    self.sites[site_id]["metrics"].update(metrics)
                
                return True
            return False
        except Exception as e:
            print(f"[心跳] 心跳更新失败: {site_id}, 错误: {e}")
            return False
    
    def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                self._check_health()
                time.sleep(self.health_check_interval)
            except Exception as e:
                print(f"[健康检查] 错误: {e}")
                time.sleep(10)
    
    def _check_health(self):
        """健康检查"""
        for site_id, site in self.sites.items():
            try:
                last_heartbeat = datetime.fromisoformat(site["last_heartbeat"])
                time_since_heartbeat = (datetime.now() - last_heartbeat).seconds
                
                if time_since_heartbeat > self.heartbeat_interval * 2:
                    if site["status"] == "online":
                        site["status"] = "offline"
                        print(f"[健康检查] 站点离线: {site_id}")
                        self._update_metrics()
            except Exception as e:
                print(f"[健康检查] 检查失败: {site_id}, 错误: {e}")
    
    def get_available_site(self, task_type: str = None) -> Optional[str]:
        """获取可用站点"""
        self._check_health()
        
        available_sites = [
            site_id for site_id, site in self.sites.items()
            if site["status"] == "online"
        ]
        
        if not available_sites:
            return None
        
        return self.load_balancer.select(available_sites, task_type)
    
    def get_site_info(self, site_id: str) -> Optional[Dict[str, Any]]:
        """获取站点信息"""
        return self.sites.get(site_id)
    
    def get_all_sites(self) -> Dict[str, Any]:
        """获取所有站点"""
        return self.sites
    
    def update_site_metrics(self, site_id: str, metrics: Dict[str, Any]) -> bool:
        """更新站点指标"""
        try:
            if site_id in self.sites:
                self.sites[site_id]["metrics"].update(metrics)
                return True
            return False
        except Exception as e:
            print(f"[指标更新] 失败: {site_id}, 错误: {e}")
            return False
    
    def _update_metrics(self):
        """更新指标"""
        self.metrics["total_sites"] = len(self.sites)
        self.metrics["online_sites"] = len([s for s in self.sites.values() if s["status"] == "online"])
        self.metrics["offline_sites"] = len([s for s in self.sites.values() if s["status"] == "offline"])
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        self._update_metrics()
        return self.metrics

class LoadBalancer:
    """负载均衡器"""
    
    def __init__(self):
        self.strategies = {
            "round_robin": self.round_robin,
            "weighted": self.weighted,
            "least_connections": self.least_connections,
            "performance": self.performance
        }
        self.current_strategy = "round_robin"
        self.current_index = 0
    
    def select(self, sites: List[str], task_type: str = None) -> str:
        """选择站点"""
        strategy = self.strategies.get(self.current_strategy)
        if strategy:
            return strategy(sites, task_type)
        return sites[0]
    
    def round_robin(self, sites: List[str], task_type: str = None) -> str:
        """轮询策略"""
        site = sites[self.current_index % len(sites)]
        self.current_index += 1
        return site
    
    def weighted(self, sites: List[str], task_type: str = None) -> str:
        """加权策略"""
        # 根据站点性能加权
        weights = []
        for site in sites:
            # 这里应该获取站点的实际性能指标
            weights.append(1.0)
        
        total_weight = sum(weights)
        r = random.uniform(0, total_weight)
        cumulative = 0
        
        for i, weight in enumerate(weights):
            cumulative += weight
            if r <= cumulative:
                return sites[i]
        
        return sites[0]
    
    def least_connections(self, sites: List[str], task_type: str = None) -> str:
        """最小连接数策略"""
        # 这里应该获取站点的实际连接数
        return sites[0]
    
    def performance(self, sites: List[str], task_type: str = None) -> str:
        """性能策略"""
        # 根据任务类型和站点性能选择
        return sites[0]

class FailoverManager:
    """故障转移管理器"""
    
    def __init__(self, multi_site_manager: MultiSiteManager):
        self.multi_site_manager = multi_site_manager
        self.failover_history = []
    
    def handle_failure(self, site_id: str, task_id: str) -> Optional[str]:
        """处理故障"""
        # 记录故障
        self.failover_history.append({
            "site_id": site_id,
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "action": "failover"
        })
        
        # 标记站点为离线
        if site_id in self.multi_site_manager.sites:
            self.multi_site_manager.sites[site_id]["status"] = "offline"
        
        # 获取新的可用站点
        new_site = self.multi_site_manager.get_available_site()
        
        if new_site:
            # 重新分配任务
            self.reassign_task(task_id, new_site)
            self.multi_site_manager.metrics["failover_count"] += 1
            print(f"[故障转移] 任务 {task_id} 从 {site_id} 转移到 {new_site}")
            return new_site
        
        print(f"[故障转移] 无可用站点，任务 {task_id} 无法转移")
        return None
    
    def reassign_task(self, task_id: str, new_site: str):
        """重新分配任务"""
        # 这里应该调用任务池重新分配任务
        pass
    
    def get_failover_history(self) -> List[Dict[str, Any]]:
        """获取故障转移历史"""
        return self.failover_history

# 使用示例
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="多站点管理器")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=9009, help="监听端口")
    parser.add_argument("--api", action="store_true", help="启动API模式")
    
    args = parser.parse_args()
    
    if args.api:
        # 启动API模式
        from http.server import HTTPServer, BaseHTTPRequestHandler
        
        class MultiSiteHandler(BaseHTTPRequestHandler):
            multi_site_manager = MultiSiteManager()
            
            def do_POST(self):
                """处理POST请求"""
                if self.path == "/sites/register":
                    try:
                        content_length = int(self.headers.get("Content-Length", 0))
                        body = self.rfile.read(content_length)
                        data = json.loads(body)
                        
                        site_id = data.get("site_id")
                        site_info = data.get("site_info", {})
                        
                        success = self.multi_site_manager.register_site(site_id, site_info)
                        
                        self.send_response(200 if success else 400)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": success}).encode())
                    except Exception as e:
                        self.send_response(500)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": str(e)}).encode())
                
                elif self.path == "/sites/heartbeat":
                    try:
                        content_length = int(self.headers.get("Content-Length", 0))
                        body = self.rfile.read(content_length)
                        data = json.loads(body)
                        
                        site_id = data.get("site_id")
                        metrics = data.get("metrics", {})
                        
                        success = self.multi_site_manager.heartbeat(site_id, metrics)
                        
                        self.send_response(200 if success else 400)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": success}).encode())
                    except Exception as e:
                        self.send_response(500)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": str(e)}).encode())
                
                else:
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Not found"}).encode())
            
            def do_GET(self):
                """处理GET请求"""
                if self.path == "/sites":
                    sites = self.multi_site_manager.get_all_sites()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(sites).encode())
                
                elif self.path == "/sites/available":
                    site = self.multi_site_manager.get_available_site()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"site": site}).encode())
                
                elif self.path == "/metrics":
                    metrics = self.multi_site_manager.get_metrics()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(metrics).encode())
                
                elif self.path == "/health":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "ok"}).encode())
                
                else:
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Not found"}).encode())
        
        # 启动服务器
        server = HTTPServer((args.host, args.port), MultiSiteHandler)
        print(f"Multi-Site Manager API running on {args.host}:{args.port}")
        server.serve_forever()
    
    else:
        # 测试模式
        manager = MultiSiteManager()
        
        # 注册站点
        manager.register_site("site-001", {
            "name": "MacBook-Pro-1",
            "ip": "192.168.31.71",
            "port": 9001
        })
        
        manager.register_site("site-002", {
            "name": "MacBook-Pro-2",
            "ip": "192.168.31.130",
            "port": 9002
        })
        
        # 获取可用站点
        site = manager.get_available_site()
        print(f"可用站点: {site}")
        
        # 获取指标
        metrics = manager.get_metrics()
        print(f"指标: {metrics}")
