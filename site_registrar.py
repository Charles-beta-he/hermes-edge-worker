#!/usr/bin/env python3
"""
站点注册器
从节点注册到主节点
"""

import json
import os
import sys
import time
import threading
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

class SiteRegistrar:
    """站点注册器"""
    
    def __init__(self, brain_url: str, site_id: str, site_info: Dict[str, Any] = None):
        self.brain_url = brain_url
        self.site_id = site_id
        self.site_info = site_info or {}
        self.heartbeat_interval = 30  # 秒
        self.running = False
        self.heartbeat_thread = None
        
        self.metrics = {
            "registrations": 0,
            "heartbeats_sent": 0,
            "heartbeats_failed": 0,
            "last_heartbeat": None
        }
    
    def register(self) -> bool:
        """注册到主节点"""
        try:
            response = requests.post(f"{self.brain_url}/sites/register", json={
                "site_id": self.site_id,
                "site_info": self.site_info
            }, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"[注册] 成功: {self.site_id}")
                    self.metrics["registrations"] += 1
                    return True
                else:
                    print(f"[注册] 失败: {self.site_id}, 错误: {data}")
                    return False
            else:
                print(f"[注册] 失败: {self.site_id}, 状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"[注册] 异常: {self.site_id}, 错误: {e}")
            return False
    
    def start_heartbeat(self):
        """启动心跳"""
        self.running = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        print(f"[心跳] 启动: {self.site_id}, 间隔: {self.heartbeat_interval}秒")
    
    def stop_heartbeat(self):
        """停止心跳"""
        self.running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        print(f"[心跳] 停止: {self.site_id}")
    
    def _heartbeat_loop(self):
        """心跳循环"""
        while self.running:
            try:
                self.send_heartbeat()
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                print(f"[心跳] 异常: {self.site_id}, 错误: {e}")
                time.sleep(5)
    
    def send_heartbeat(self) -> bool:
        """发送心跳"""
        try:
            # 获取系统指标
            metrics = self._get_system_metrics()
            
            response = requests.post(f"{self.brain_url}/sites/heartbeat", json={
                "site_id": self.site_id,
                "metrics": metrics
            }, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.metrics["heartbeats_sent"] += 1
                    self.metrics["last_heartbeat"] = datetime.now().isoformat()
                    return True
                else:
                    self.metrics["heartbeats_failed"] += 1
                    return False
            else:
                self.metrics["heartbeats_failed"] += 1
                return False
        except Exception as e:
            self.metrics["heartbeats_failed"] += 1
            print(f"[心跳] 发送失败: {self.site_id}, 错误: {e}")
            return False
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        try:
            import psutil
            
            return {
                "cpu_usage": psutil.cpu_percent(interval=1),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "timestamp": datetime.now().isoformat()
            }
        except ImportError:
            # 如果psutil不可用，返回模拟数据
            return {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "disk_usage": 0.0,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics

class EdgeWorkerWithMultiSite:
    """支持多站点的Edge Worker"""
    
    def __init__(self, brain_url: str, site_id: str, site_info: Dict[str, Any] = None):
        self.brain_url = brain_url
        self.site_id = site_id
        self.site_info = site_info or {}
        self.registrar = SiteRegistrar(brain_url, site_id, site_info)
    
    def start(self):
        """启动Edge Worker"""
        # 注册到主节点
        if self.registrar.register():
            # 启动心跳
            self.registrar.start_heartbeat()
            print(f"[Edge Worker] 启动成功: {self.site_id}")
        else:
            print(f"[Edge Worker] 启动失败: {self.site_id}")
    
    def stop(self):
        """停止Edge Worker"""
        self.registrar.stop_heartbeat()
        print(f"[Edge Worker] 停止: {self.site_id}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.registrar.get_metrics()

# 使用示例
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="站点注册器")
    parser.add_argument("--brain-url", default="http://192.168.31.71:9009", help="主节点URL")
    parser.add_argument("--site-id", required=True, help="站点ID")
    parser.add_argument("--site-name", help="站点名称")
    parser.add_argument("--site-ip", help="站点IP")
    parser.add_argument("--site-port", type=int, help="站点端口")
    
    args = parser.parse_args()
    
    # 构建站点信息
    site_info = {
        "name": args.site_name or args.site_id,
        "ip": args.site_ip or "localhost",
        "port": args.site_port or 9002
    }
    
    # 创建Edge Worker
    edge_worker = EdgeWorkerWithMultiSite(args.brain_url, args.site_id, site_info)
    
    # 启动
    edge_worker.start()
    
    # 保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        edge_worker.stop()
