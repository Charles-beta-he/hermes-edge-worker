#!/usr/bin/env python3
"""
自动化测试和持续集成
中期计划：质量保证
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from typing import Dict, Any, List

class ContinuousIntegration:
    """持续集成"""
    
    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.results = {}
    
    def run_code_quality_check(self) -> Dict[str, Any]:
        """运行代码质量检查"""
        print("=== 代码质量检查 ===")
        
        # 检查Python语法
        syntax_errors = 0
        for root, dirs, files in os.walk(self.project_dir):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    try:
                        result = subprocess.run(
                            ["python3", "-m", "py_compile", filepath],
                            capture_output=True,
                            text=True
                        )
                        if result.returncode != 0:
                            syntax_errors += 1
                            print(f"  语法错误: {filepath}")
                    except Exception:
                        syntax_errors += 1
        
        result = {
            "syntax_errors": syntax_errors,
            "status": "PASS" if syntax_errors == 0 else "FAIL"
        }
        
        print(f"  语法错误: {syntax_errors}")
        print(f"  状态: {result['status']}")
        
        return result
    
    def run_tests(self) -> Dict[str, Any]:
        """运行测试"""
        print("\n=== 运行测试 ===")
        
        test_files = [
            "test_complete.py",
            "test_integration.py",
            "test_api.py"
        ]
        
        total_tests = 0
        total_failures = 0
        total_errors = 0
        
        for test_file in test_files:
            filepath = os.path.join(self.project_dir, test_file)
            if os.path.exists(filepath):
                print(f"\n运行 {test_file}...")
                try:
                    result = subprocess.run(
                        ["python3", filepath],
                        capture_output=True,
                        text=True,
                        cwd=self.project_dir
                    )
                    
                    # 解析结果
                    output = result.stdout
                    if "Ran" in output:
                        # 提取测试数量
                        import re
                        match = re.search(r'Ran (\d+) tests', output)
                        if match:
                            tests = int(match.group(1))
                            total_tests += tests
                    
                    if "FAILED" in output:
                        total_failures += 1
                    elif "OK" in output:
                        pass  # 测试通过
                    
                except Exception as e:
                    total_errors += 1
                    print(f"  错误: {e}")
        
        result = {
            "total_tests": total_tests,
            "total_failures": total_failures,
            "total_errors": total_errors,
            "success_rate": (total_tests - total_failures - total_errors) / total_tests * 100 if total_tests > 0 else 0,
            "status": "PASS" if total_failures == 0 and total_errors == 0 else "FAIL"
        }
        
        print(f"\n总计: {total_tests} 测试")
        print(f"失败: {total_failures}")
        print(f"错误: {total_errors}")
        print(f"成功率: {result['success_rate']:.1f}%")
        print(f"状态: {result['status']}")
        
        return result
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """运行集成测试"""
        print("\n=== 集成测试 ===")
        
        # 测试组件导入
        components = [
            "unified_data_layer",
            "unified_event_bus",
            "knowledge_manager",
            "rag_knowledge_manager",
            "edge_worker"
        ]
        
        import_errors = []
        for component in components:
            try:
                __import__(component)
                print(f"  ✓ {component}")
            except ImportError as e:
                import_errors.append(component)
                print(f"  ✗ {component}: {e}")
        
        result = {
            "total_components": len(components),
            "import_errors": import_errors,
            "status": "PASS" if len(import_errors) == 0 else "FAIL"
        }
        
        print(f"\n导入错误: {len(import_errors)}")
        print(f"状态: {result['status']}")
        
        return result
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """运行性能测试"""
        print("\n=== 性能测试 ===")
        
        # 测试数据层性能
        try:
            from unified_data_layer import UnifiedDataLayer
            import time
            
            data_layer = UnifiedDataLayer(storage_dir="/tmp/test_performance_ci")
            
            # 存储性能
            start_time = time.time()
            for i in range(100):
                data_layer.store("task", f"task-{i}", {"index": i})
            store_time = time.time() - start_time
            
            # 检索性能
            start_time = time.time()
            for i in range(100):
                data_layer.retrieve("task", f"task-{i}")
            retrieve_time = time.time() - start_time
            
            result = {
                "store_time": store_time,
                "retrieve_time": retrieve_time,
                "status": "PASS" if store_time < 1.0 and retrieve_time < 1.0 else "FAIL"
            }
            
            print(f"  存储时间: {store_time:.3f}s")
            print(f"  检索时间: {retrieve_time:.3f}s")
            print(f"  状态: {result['status']}")
            
        except Exception as e:
            result = {"status": "ERROR", "error": str(e)}
            print(f"  错误: {e}")
        
        return result
    
    def generate_report(self) -> Dict[str, Any]:
        """生成报告"""
        print("\n=== 生成报告 ===")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "project_dir": self.project_dir,
            "checks": {
                "code_quality": self.run_code_quality_check(),
                "tests": self.run_tests(),
                "integration": self.run_integration_tests(),
                "performance": self.run_performance_tests()
            }
        }
        
        # 计算总体状态
        all_passed = all(
            check.get("status") == "PASS" 
            for check in report["checks"].values()
        )
        
        report["overall_status"] = "PASS" if all_passed else "FAIL"
        
        # 保存报告
        report_path = os.path.join(self.project_dir, "ci_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n报告已保存: {report_path}")
        print(f"总体状态: {report['overall_status']}")
        
        return report

def main():
    """主函数"""
    project_dir = "/Users/charles/hermes-edge-worker"
    
    # 创建持续集成
    ci = ContinuousIntegration(project_dir)
    
    # 生成报告
    report = ci.generate_report()
    
    # 返回状态码
    sys.exit(0 if report["overall_status"] == "PASS" else 1)

if __name__ == "__main__":
    main()
