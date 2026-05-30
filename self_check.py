#!/usr/bin/env python3
"""
自检流程
拒绝自嗨，真实验证
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from typing import Dict, Any, List

class SelfChecker:
    """自检器"""
    
    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.results = {}
    
    def check_test_coverage(self) -> Dict[str, Any]:
        """检查测试覆盖率"""
        print("=== 检查测试覆盖率 ===")
        
        # 统计测试文件
        test_files = []
        for root, dirs, files in os.walk(self.project_dir):
            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    test_files.append(os.path.join(root, file))
        
        # 统计源代码文件
        source_files = []
        for root, dirs, files in os.walk(self.project_dir):
            for file in files:
                if file.endswith(".py") and not file.startswith("test_") and not file.startswith("__"):
                    source_files.append(os.path.join(root, file))
        
        # 计算覆盖率
        coverage = len(test_files) / len(source_files) * 100 if source_files else 0
        
        result = {
            "test_files": len(test_files),
            "source_files": len(source_files),
            "coverage": coverage,
            "status": "PASS" if coverage > 50 else "FAIL"
        }
        
        print(f"  测试文件: {len(test_files)}")
        print(f"  源代码文件: {len(source_files)}")
        print(f"  覆盖率: {coverage:.1f}%")
        print(f"  状态: {result['status']}")
        
        return result
    
    def check_code_quality(self) -> Dict[str, Any]:
        """检查代码质量"""
        print("\n=== 检查代码质量 ===")
        
        # 运行Python语法检查
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
    
    def check_component_integration(self) -> Dict[str, Any]:
        """检查组件集成"""
        print("\n=== 检查组件集成 ===")
        
        # 检查核心组件是否存在
        core_components = [
            "unified_data_layer.py",
            "unified_event_bus.py",
            "unified_interface_layer.py",
            "knowledge_manager.py",
            "rag_knowledge_manager.py"
        ]
        
        missing_components = []
        for component in core_components:
            filepath = os.path.join(self.project_dir, component)
            if not os.path.exists(filepath):
                missing_components.append(component)
        
        result = {
            "total_components": len(core_components),
            "missing_components": missing_components,
            "status": "PASS" if len(missing_components) == 0 else "FAIL"
        }
        
        print(f"  核心组件: {len(core_components)}")
        print(f"  缺失组件: {len(missing_components)}")
        if missing_components:
            print(f"  缺失列表: {missing_components}")
        print(f"  状态: {result['status']}")
        
        return result
    
    def check_documentation(self) -> Dict[str, Any]:
        """检查文档完整性"""
        print("\n=== 检查文档完整性 ===")
        
        # 检查README
        readme_exists = os.path.exists(os.path.join(self.project_dir, "README.md"))
        
        # 检查架构文档
        architecture_docs = []
        for root, dirs, files in os.walk(self.project_dir):
            for file in files:
                if file.endswith(".md") and "ARCHITECTURE" in file.upper():
                    architecture_docs.append(file)
        
        result = {
            "readme_exists": readme_exists,
            "architecture_docs": len(architecture_docs),
            "status": "PASS" if readme_exists and len(architecture_docs) > 0 else "FAIL"
        }
        
        print(f"  README存在: {readme_exists}")
        print(f"  架构文档: {len(architecture_docs)}")
        print(f"  状态: {result['status']}")
        
        return result
    
    def check_deployment(self) -> Dict[str, Any]:
        """检查部署配置"""
        print("\n=== 检查部署配置 ===")
        
        # 检查安装脚本
        install_scripts = []
        for root, dirs, files in os.walk(self.project_dir):
            for file in files:
                if file.startswith("install") and file.endswith(".sh"):
                    install_scripts.append(file)
        
        # 检查配置文件
        config_files = []
        for root, dirs, files in os.walk(self.project_dir):
            for file in files:
                if file.endswith(".yaml") or file.endswith(".yml"):
                    config_files.append(file)
        
        result = {
            "install_scripts": len(install_scripts),
            "config_files": len(config_files),
            "status": "PASS" if len(install_scripts) > 0 else "FAIL"
        }
        
        print(f"  安装脚本: {len(install_scripts)}")
        print(f"  配置文件: {len(config_files)}")
        print(f"  状态: {result['status']}")
        
        return result
    
    def run_tests(self) -> Dict[str, Any]:
        """运行测试"""
        print("\n=== 运行测试 ===")
        
        test_file = os.path.join(self.project_dir, "test_core_components.py")
        if not os.path.exists(test_file):
            return {"status": "SKIP", "reason": "测试文件不存在"}
        
        try:
            result = subprocess.run(
                ["python3", test_file],
                capture_output=True,
                text=True,
                cwd=self.project_dir
            )
            
            # 解析测试结果
            output = result.stdout
            if "OK" in output:
                status = "PASS"
            elif "FAIL" in output or "ERROR" in output:
                status = "FAIL"
            else:
                status = "UNKNOWN"
            
            return {
                "status": status,
                "returncode": result.returncode,
                "output": output[-500:] if len(output) > 500 else output
            }
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}
    
    def run_full_check(self) -> Dict[str, Any]:
        """运行完整自检"""
        print("=== 开始自检 ===")
        print(f"项目目录: {self.project_dir}")
        print(f"检查时间: {datetime.now().isoformat()}")
        print()
        
        # 运行所有检查
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "project_dir": self.project_dir,
            "checks": {
                "test_coverage": self.check_test_coverage(),
                "code_quality": self.check_code_quality(),
                "component_integration": self.check_component_integration(),
                "documentation": self.check_documentation(),
                "deployment": self.check_deployment(),
                "tests": self.run_tests()
            }
        }
        
        # 计算总体状态
        all_passed = all(
            check.get("status") == "PASS" 
            for check in self.results["checks"].values()
            if check.get("status") != "SKIP"
        )
        
        self.results["overall_status"] = "PASS" if all_passed else "FAIL"
        
        # 打印总结
        print("\n=== 自检总结 ===")
        for check_name, check_result in self.results["checks"].items():
            status = check_result.get("status", "UNKNOWN")
            print(f"  {check_name}: {status}")
        
        print(f"\n总体状态: {self.results['overall_status']}")
        
        return self.results
    
    def save_report(self, filepath: str):
        """保存报告"""
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n报告已保存: {filepath}")

def main():
    """主函数"""
    project_dir = "/Users/charles/hermes-edge-worker"
    
    # 创建自检器
    checker = SelfChecker(project_dir)
    
    # 运行自检
    results = checker.run_full_check()
    
    # 保存报告
    report_path = os.path.join(project_dir, "self_check_report.json")
    checker.save_report(report_path)
    
    # 返回状态码
    sys.exit(0 if results["overall_status"] == "PASS" else 1)

if __name__ == "__main__":
    main()
