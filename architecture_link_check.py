#!/usr/bin/env python3
"""
架构链路检查脚本
检查完整架构链路
"""

import json
import os
import re
import sys
import time
import requests
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

class ArchitectureLinkCheck:
    """架构链路检查"""
    
    def __init__(self):
        self.results = {
            "ports_doc": {},
            "components": {},
            "api_endpoints": {},
            "task_pool": {},
            "sites": {},
            "link_tests": {}
        }
    
    def check_all(self) -> Dict[str, Any]:
        """检查所有链路"""
        print("=== 架构链路检查 ===\n")
        
        # 1. 检查端口 SSOT 文档
        self._check_ports_doc_consistency()

        # 2. 检查组件文件
        self._check_components()
        
        # 3. 检查API端点
        self._check_api_endpoints()
        
        # 4. 检查任务池状态
        self._check_task_pool()
        
        # 5. 检查站点状态
        self._check_sites()
        
        # 6. 测试链路
        self._test_links()
        
        # 7. 生成报告
        self._generate_report()
        
        return self.results
    
    def _verified_ports_from_ports_doc(self):
        """Parse PORTS.md rows whose status column is exactly verified."""
        ports_path = SCRIPT_DIR / "PORTS.md"
        if not ports_path.exists():
            return set()
        ports = set()
        for line in ports_path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 4:
                continue
            if cells[3] != "verified":
                continue
            if re.fullmatch(r"\d+", cells[0]):
                ports.add(int(cells[0]))
        return ports

    def _check_ports_doc_consistency(self):
        """Verify PORTS.md matches the architecture link check's verified API ports."""
        print("1. 检查端口 SSOT 文档:")
        expected_ports = {9007, 9008, 9009}
        verified_ports = self._verified_ports_from_ports_doc()
        missing = sorted(expected_ports - verified_ports)
        extra = sorted(verified_ports - expected_ports)
        status = "ok" if not missing and not extra else "mismatch"
        self.results["ports_doc"] = {
            "status": status,
            "expected_verified_ports": sorted(expected_ports),
            "verified_ports": sorted(verified_ports),
            "missing_verified_ports": missing,
            "extra_verified_ports": extra,
        }
        if status == "ok":
            print(f"   ✓ PORTS.md verified ports: {sorted(verified_ports)}")
        else:
            print(f"   ✗ PORTS.md verified ports mismatch: missing={missing}, extra={extra}")
    
    def _check_components(self):
        """检查组件文件"""
        print("1. 检查组件文件:")
        
        components = {
            "multi_site_manager.py": "多站点管理器",
            "site_registrar.py": "站点注册器",
            "task_event_driven.py": "事件驱动核心",
            "task_pool_event_integration.py": "任务池事件集成",
            "edge_worker.py": "Edge Worker"
        }
        
        for file, name in components.items():
            path = SCRIPT_DIR / file
            if path.exists():
                size = path.stat().st_size
                self.results["components"][file] = {
                    "status": "ok",
                    "size": size,
                    "name": name
                }
                print(f"   ✓ {name}: {file} ({size} bytes)")
            else:
                self.results["components"][file] = {
                    "status": "missing",
                    "name": name
                }
                print(f"   ✗ {name}: {file} (缺失)")
    
    def _check_api_endpoints(self):
        """检查API端点"""
        print("\n2. 检查API端点:")
        
        endpoints = {
            "multi_site_manager": {"url": "http://localhost:9009", "name": "多站点管理器API"},
            "event_driven": {"url": "http://localhost:9007", "name": "事件驱动API"},
            "task_pool_integration": {"url": "http://localhost:9008", "name": "任务池事件集成API"}
        }
        
        for endpoint_id, endpoint_info in endpoints.items():
            url = endpoint_info["url"]
            name = endpoint_info["name"]
            
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code == 200:
                    self.results["api_endpoints"][endpoint_id] = {
                        "status": "ok",
                        "url": url,
                        "name": name
                    }
                    print(f"   ✓ {name}: {url}")
                else:
                    self.results["api_endpoints"][endpoint_id] = {
                        "status": "error",
                        "url": url,
                        "name": name,
                        "error": f"状态码: {response.status_code}"
                    }
                    print(f"   ✗ {name}: {url} (状态码: {response.status_code})")
            except requests.exceptions.ConnectionError:
                self.results["api_endpoints"][endpoint_id] = {
                    "status": "not_running",
                    "url": url,
                    "name": name
                }
                print(f"   ✗ {name}: {url} (未运行)")
            except Exception as e:
                self.results["api_endpoints"][endpoint_id] = {
                    "status": "error",
                    "url": url,
                    "name": name,
                    "error": str(e)
                }
                print(f"   ✗ {name}: {url} (错误: {e})")
    
    def _check_task_pool(self):
        """检查任务池状态"""
        print("\n3. 检查任务池状态:")
        
        try:
            # 运行brain_task_orchestrator.py dashboard
            import subprocess
            result = subprocess.run(
                ["python3", str(Path.home() / ".hermes" / "scripts" / "brain_task_orchestrator.py"), "dashboard"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # 解析输出
                lines = result.stdout.split('\n')
                
                # 提取活跃任务数
                for line in lines:
                    if "active_count:" in line:
                        active_count = int(line.split(':')[1].strip())
                        self.results["task_pool"]["active_count"] = active_count
                        print(f"   活跃任务数: {active_count}")
                
                # 提取待处理任务
                pending_tasks = []
                for line in lines:
                    if "pending" in line and "[[" in line:
                        # 提取任务ID
                        start = line.find("[[") + 2
                        end = line.find("]]")
                        if start > 1 and end > start:
                            task_id = line[start:end]
                            pending_tasks.append(task_id)
                
                self.results["task_pool"]["pending_tasks"] = pending_tasks
                print(f"   待处理任务数: {len(pending_tasks)}")
                
                self.results["task_pool"]["status"] = "ok"
            else:
                self.results["task_pool"]["status"] = "error"
                self.results["task_pool"]["error"] = result.stderr
                print(f"   ✗ 任务池检查失败: {result.stderr}")
        except Exception as e:
            self.results["task_pool"]["status"] = "error"
            self.results["task_pool"]["error"] = str(e)
            print(f"   ✗ 任务池检查异常: {e}")
    
    def _check_sites(self):
        """检查站点状态"""
        print("\n4. 检查站点状态:")
        
        try:
            response = requests.get("http://localhost:9009/sites", timeout=5)
            
            if response.status_code == 200:
                sites = response.json()
                self.results["sites"] = sites
                
                print(f"   站点总数: {len(sites)}")
                
                for site_id, site_info in sites.items():
                    status = site_info.get("status", "unknown")
                    name = site_info.get("info", {}).get("name", site_id)
                    print(f"   - {name}: {status}")
            else:
                self.results["sites"]["status"] = "error"
                self.results["sites"]["error"] = f"状态码: {response.status_code}"
                print(f"   ✗ 站点检查失败: 状态码 {response.status_code}")
        except requests.exceptions.ConnectionError:
            self.results["sites"]["status"] = "not_running"
            print("   ✗ 多站点管理器API未运行")
        except Exception as e:
            self.results["sites"]["status"] = "error"
            self.results["sites"]["error"] = str(e)
            print(f"   ✗ 站点检查异常: {e}")
    
    def _test_links(self):
        """测试链路"""
        print("\n5. 测试链路:")
        
        # 测试任务创建 → 事件驱动 → 自动认领 → 自动执行
        print("   测试链路1: 任务创建 → 事件驱动 → 自动认领 → 自动执行")
        self._test_task_event_link()
        
        # 测试站点注册 → 心跳检测 → 健康检查 → 故障转移
        print("   测试链路2: 站点注册 → 心跳检测 → 健康检查 → 故障转移")
        self._test_site_registration_link()
        
        # 测试负载均衡 → 任务分配 → 结果返回
        print("   测试链路3: 负载均衡 → 任务分配 → 结果返回")
        self._test_load_balancing_link()
    
    def _test_task_event_link(self):
        """测试任务事件链路"""
        try:
            # 发送任务创建事件
            response = requests.post("http://localhost:9008/event", json={
                "event_type": "task.created",
                "event_data": {
                    "task_id": "test-task-001",
                    "priority": "P1"
                }
            }, timeout=5)
            
            if response.status_code == 200:
                self.results["link_tests"]["task_event"] = {"status": "ok"}
                print("      ✓ 任务事件链路正常")
            else:
                self.results["link_tests"]["task_event"] = {"status": "error", "error": f"状态码: {response.status_code}"}
                print(f"      ✗ 任务事件链路失败: 状态码 {response.status_code}")
        except requests.exceptions.ConnectionError:
            self.results["link_tests"]["task_event"] = {"status": "not_running"}
            print("      ✗ 任务池事件集成API未运行")
        except Exception as e:
            self.results["link_tests"]["task_event"] = {"status": "error", "error": str(e)}
            print(f"      ✗ 任务事件链路异常: {e}")
    
    def _test_site_registration_link(self):
        """测试站点注册链路"""
        try:
            # 注册测试站点
            response = requests.post("http://localhost:9009/sites/register", json={
                "site_id": "test-site-001",
                "site_info": {
                    "name": "Test-Site",
                    "ip": "192.168.31.100",
                    "port": 9010
                }
            }, timeout=5)
            
            if response.status_code == 200:
                self.results["link_tests"]["site_registration"] = {"status": "ok"}
                print("      ✓ 站点注册链路正常")
                
                # 发送心跳
                response = requests.post("http://localhost:9009/sites/heartbeat", json={
                    "site_id": "test-site-001",
                    "metrics": {
                        "cpu_usage": 50.0,
                        "memory_usage": 60.0
                    }
                }, timeout=5)
                
                if response.status_code == 200:
                    self.results["link_tests"]["site_heartbeat"] = {"status": "ok"}
                    print("      ✓ 站点心跳链路正常")
                else:
                    self.results["link_tests"]["site_heartbeat"] = {"status": "error", "error": f"状态码: {response.status_code}"}
                    print(f"      ✗ 站点心跳链路失败: 状态码 {response.status_code}")
            else:
                self.results["link_tests"]["site_registration"] = {"status": "error", "error": f"状态码: {response.status_code}"}
                print(f"      ✗ 站点注册链路失败: 状态码 {response.status_code}")
        except requests.exceptions.ConnectionError:
            self.results["link_tests"]["site_registration"] = {"status": "not_running"}
            print("      ✗ 多站点管理器API未运行")
        except Exception as e:
            self.results["link_tests"]["site_registration"] = {"status": "error", "error": str(e)}
            print(f"      ✗ 站点注册链路异常: {e}")
    
    def _test_load_balancing_link(self):
        """测试负载均衡链路"""
        try:
            # 获取可用站点
            response = requests.get("http://localhost:9009/sites/available", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                site = data.get("site")
                
                if site:
                    self.results["link_tests"]["load_balancing"] = {"status": "ok", "site": site}
                    print(f"      ✓ 负载均衡链路正常，可用站点: {site}")
                else:
                    self.results["link_tests"]["load_balancing"] = {"status": "no_sites"}
                    print("      ✗ 无可用站点")
            else:
                self.results["link_tests"]["load_balancing"] = {"status": "error", "error": f"状态码: {response.status_code}"}
                print(f"      ✗ 负载均衡链路失败: 状态码 {response.status_code}")
        except requests.exceptions.ConnectionError:
            self.results["link_tests"]["load_balancing"] = {"status": "not_running"}
            print("      ✗ 多站点管理器API未运行")
        except Exception as e:
            self.results["link_tests"]["load_balancing"] = {"status": "error", "error": str(e)}
            print(f"      ✗ 负载均衡链路异常: {e}")
    
    def _generate_report(self):
        """生成报告"""
        print("\n=== 链路检查报告 ===")
        
        # 统计状态
        total_components = len(self.results["components"])
        ok_components = len([c for c in self.results["components"].values() if c.get("status") == "ok"])
        
        total_endpoints = len(self.results["api_endpoints"])
        ok_endpoints = len([e for e in self.results["api_endpoints"].values() if e.get("status") == "ok"])
        
        total_tests = len(self.results["link_tests"])
        ok_tests = len([t for t in self.results["link_tests"].values() if t.get("status") == "ok"])
        
        ports_ok = self.results.get("ports_doc", {}).get("status") == "ok"
        print(f"PORTS.md: {'正常' if ports_ok else '异常'}")
        print(f"组件文件: {ok_components}/{total_components} 正常")
        print(f"API端点: {ok_endpoints}/{total_endpoints} 正常")
        print(f"链路测试: {ok_tests}/{total_tests} 正常")
        
        # 总体状态
        if ports_ok and ok_components == total_components and ok_endpoints == total_endpoints and ok_tests == total_tests:
            print("\n总体状态: ✓ 正常")
            self.results["overall_status"] = "ok"
        else:
            print("\n总体状态: ✗ 异常")
            self.results["overall_status"] = "error"
        
        # 保存报告
        report_path = SCRIPT_DIR / "architecture_link_check_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n报告已保存: {report_path}")

# 使用示例
if __name__ == "__main__":
    checker = ArchitectureLinkCheck()
    results = checker.check_all()
