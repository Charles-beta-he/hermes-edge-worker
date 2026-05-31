#!/usr/bin/env python3
"""
自检流程
拒绝自嗨，真实验证。

边界定义：自检不只统计测试文件数量，还覆盖代码、组件、文档、部署、
测试执行、性能、安全、压力、兼容性、架构链路等工程边界。
"""

import json
import os
import py_compile
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class SelfChecker:
    """自检器。"""

    BOUNDARY_CHECKS = [
        "test_coverage",
        "code_quality",
        "component_integration",
        "documentation",
        "deployment",
        "tests",
        "performance",
        "security",
        "stress",
        "compatibility",
        "architecture_links",
    ]

    CORE_COMPONENTS = [
        "unified_data_layer.py",
        "unified_event_bus.py",
        "unified_interface_layer.py",
        "knowledge_manager.py",
        "rag_knowledge_manager.py",
    ]

    ARCHITECTURE_CHAIN_COMPONENTS = [
        "multi_site_manager.py",
        "site_registrar.py",
        "task_event_driven.py",
        "task_pool_event_integration.py",
        "edge_worker.py",
    ]

    def __init__(self, project_dir: str):
        self.project_dir = os.path.abspath(project_dir)
        self.project_path = Path(self.project_dir)
        self.results: Dict[str, Any] = {}

    def get_boundary_catalog(self) -> List[str]:
        """返回自检应覆盖的工程边界。"""
        return list(self.BOUNDARY_CHECKS)

    def _iter_files(self, suffixes: tuple[str, ...]) -> List[Path]:
        ignored_dirs = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", "htmlcov"}
        files: List[Path] = []
        for root, dirs, names in os.walk(self.project_dir):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for name in names:
                path = Path(root) / name
                if path.suffix in suffixes:
                    files.append(path)
        return sorted(files)

    def _source_files(self) -> List[Path]:
        return [
            path
            for path in self._iter_files((".py",))
            if not path.name.startswith("test_") and not path.name.startswith("__")
        ]

    def _test_files(self) -> List[Path]:
        return [path for path in self._iter_files((".py",)) if path.name.startswith("test_")]

    def check_test_coverage(self) -> Dict[str, Any]:
        """检查源文件是否有测试边界覆盖。"""
        print("=== 检查测试覆盖率 ===")
        test_files = self._test_files()
        source_files = self._source_files()
        test_names = {p.name for p in test_files}
        excluded = {"create_test_files.py", "conftest.py"}
        mapped_source_files = [p for p in source_files if p.name not in excluded]
        missing_tests = []
        for source in mapped_source_files:
            expected = f"test_{source.stem}.py"
            if expected not in test_names:
                missing_tests.append(source.name)

        coverage = (
            (len(mapped_source_files) - len(missing_tests)) / len(mapped_source_files) * 100
            if mapped_source_files
            else 100.0
        )
        result = {
            "test_files": len(test_files),
            "source_files": len(source_files),
            "mapped_source_files": len(mapped_source_files),
            "missing_tests": missing_tests,
            "coverage": coverage,
            "status": "PASS" if coverage >= 90.0 else "FAIL",
        }
        print(f"  测试文件: {len(test_files)}")
        print(f"  源代码文件: {len(source_files)}")
        print(f"  映射源文件: {len(mapped_source_files)}")
        print(f"  缺失测试: {len(missing_tests)}")
        print(f"  覆盖率: {coverage:.1f}%")
        print(f"  状态: {result['status']}")
        return result

    def check_code_quality(self) -> Dict[str, Any]:
        """检查 Python 语法质量。"""
        print("\n=== 检查代码质量 ===")
        errors = []
        for filepath in self._iter_files((".py",)):
            try:
                py_compile.compile(str(filepath), doraise=True)
            except Exception as exc:  # pragma: no cover - defensive reporting
                errors.append({"file": str(filepath), "error": str(exc)})
                print(f"  语法错误: {filepath}")
        result = {"syntax_errors": len(errors), "errors": errors, "status": "PASS" if not errors else "FAIL"}
        print(f"  语法错误: {len(errors)}")
        print(f"  状态: {result['status']}")
        return result

    def check_component_integration(self) -> Dict[str, Any]:
        """检查核心组件是否完整。"""
        print("\n=== 检查组件集成 ===")
        missing_components = [name for name in self.CORE_COMPONENTS if not (self.project_path / name).exists()]
        result = {
            "total_components": len(self.CORE_COMPONENTS),
            "missing_components": missing_components,
            "status": "PASS" if not missing_components else "FAIL",
        }
        print(f"  核心组件: {len(self.CORE_COMPONENTS)}")
        print(f"  缺失组件: {len(missing_components)}")
        if missing_components:
            print(f"  缺失列表: {missing_components}")
        print(f"  状态: {result['status']}")
        return result

    def check_documentation(self) -> Dict[str, Any]:
        """检查文档完整性。"""
        print("\n=== 检查文档完整性 ===")
        readme_exists = (self.project_path / "README.md").exists()
        architecture_docs = [p.name for p in self._iter_files((".md",)) if "ARCHITECTURE" in p.name.upper()]
        result = {
            "readme_exists": readme_exists,
            "architecture_docs": len(architecture_docs),
            "status": "PASS" if readme_exists and architecture_docs else "FAIL",
        }
        print(f"  README存在: {readme_exists}")
        print(f"  架构文档: {len(architecture_docs)}")
        print(f"  状态: {result['status']}")
        return result

    def check_deployment(self) -> Dict[str, Any]:
        """检查部署配置。"""
        print("\n=== 检查部署配置 ===")
        install_scripts = [p.name for p in self._iter_files((".sh",)) if p.name.startswith("install")]
        config_files = [p.name for p in self._iter_files((".yaml", ".yml"))]
        result = {
            "install_scripts": len(install_scripts),
            "config_files": len(config_files),
            "status": "PASS" if install_scripts else "FAIL",
        }
        print(f"  安装脚本: {len(install_scripts)}")
        print(f"  配置文件: {len(config_files)}")
        print(f"  状态: {result['status']}")
        return result

    def _python_with_pytest(self) -> str:
        """选择可运行 pytest 的 Python；当前解释器不可用时回退到系统 Python。"""
        candidates = [sys.executable, "/usr/bin/python3", "python3"]
        for candidate in candidates:
            try:
                probe = subprocess.run([candidate, "-m", "pytest", "--version"], capture_output=True, text=True, timeout=10)
                if probe.returncode == 0:
                    return candidate
            except Exception:
                continue
        return sys.executable

    def run_tests(self) -> Dict[str, Any]:
        """运行测试。优先运行 pytest 全量测试；无 pytest 时回退为失败信号。"""
        print("\n=== 运行测试 ===")
        test_files = self._test_files()
        if not test_files:
            return {"status": "SKIP", "reason": "测试文件不存在"}
        rel_test_files = [str(path.relative_to(self.project_path)) for path in test_files]
        python_bin = self._python_with_pytest()
        command = [python_bin, "-m", "pytest", *rel_test_files, "-q"]
        env = os.environ.copy()
        existing_warnings = env.get("PYTHONWARNINGS", "")
        urllib3_filter = "ignore:urllib3 v2 only supports OpenSSL"
        env["PYTHONWARNINGS"] = (
            f"{existing_warnings},{urllib3_filter}" if existing_warnings else urllib3_filter
        )
        try:
            result = subprocess.run(command, capture_output=True, text=True, cwd=self.project_dir, timeout=120, env=env)
        except Exception as exc:
            return {"status": "ERROR", "error": str(exc), "command": command}
        output = f"{result.stdout}\n{result.stderr}"
        passed = result.returncode == 0 and ("passed" in output or "OK" in output)
        failed = result.returncode != 0 or any(token in output for token in ("FAILED", "ERROR", "Traceback"))
        status = "PASS" if passed and not failed else "FAIL"
        return {
            "status": status,
            "returncode": result.returncode,
            "command": " ".join(command),
            "test_files": len(test_files),
            "output": output[-1200:] if len(output) > 1200 else output,
        }

    def check_performance(self) -> Dict[str, Any]:
        """轻量性能边界：文件枚举和核心静态检查应在短时间内完成。"""
        print("\n=== 检查性能边界 ===")
        start = time.perf_counter()
        source_count = len(self._source_files())
        test_count = len(self._test_files())
        duration_ms = (time.perf_counter() - start) * 1000
        result = {
            "source_files": source_count,
            "test_files": test_count,
            "duration_ms": round(duration_ms, 3),
            "threshold_ms": 500.0,
            "status": "PASS" if duration_ms <= 500.0 else "FAIL",
        }
        print(f"  文件枚举耗时: {duration_ms:.3f}ms")
        print(f"  状态: {result['status']}")
        return result

    def check_security(self) -> Dict[str, Any]:
        """安全边界：runtime 高危 fail-closed，文档/测试/安装示例只计 warning。"""
        print("\n=== 检查安全边界 ===")
        critical_patterns = [
            re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{12,}['\"]"),
            re.compile(r"(?i)bearer\s+[a-z0-9._\-]{20,}"),
        ]
        warning_patterns = [
            re.compile(r"curl\s+[^\n]*\|\s*bash"),
            re.compile(r"hermes-2024"),
            re.compile(r"your-secret-token|changeme|change-me", re.IGNORECASE),
        ]
        placeholder_re = re.compile(r"your-secret-token|changeme|change-me|<token>|\*\*\*", re.IGNORECASE)
        doc_suffixes = {".md", ".txt"}
        runtime_suffixes = {".py", ".sh", ".bash", ".yaml", ".yml"}

        def bucket_for(path: Path) -> str:
            rel_parts = set(path.relative_to(self.project_path).parts)
            if path.suffix in doc_suffixes or path.name.startswith("test_") or "tests" in rel_parts:
                return "doc"
            return "runtime"

        runtime_critical = []
        runtime_warnings = []
        doc_examples = []

        def line_for(text: str, offset: int) -> str:
            start = text.rfind("\n", 0, offset) + 1
            end = text.find("\n", offset)
            if end == -1:
                end = len(text)
            return text[start:end]

        def is_scanner_rule_definition(path: Path, text: str, offset: int) -> bool:
            if path.name != "self_check.py":
                return False
            line = line_for(text, offset)
            return "re.compile" in line or "placeholder_re" in line

        def is_placeholder_allowlist_definition(path: Path, text: str, offset: int) -> bool:
            line = line_for(text, offset)
            return path.name in {"edge_worker.py", "request_security.py"} and (
                "_PLACEHOLDERS" in line or "normalized in" in line
            )

        def is_dynamic_secret_assignment(text: str, offset: int) -> bool:
            line = line_for(text, offset)
            return "${" in line or "$HA256_PLACEHOLDER" in line or "$(" in line

        for path in self._iter_files(tuple(runtime_suffixes | doc_suffixes)):
            text = path.read_text(encoding="utf-8", errors="ignore")
            rel = str(path.relative_to(self.project_path))
            bucket = bucket_for(path)
            for pattern in critical_patterns:
                for match in pattern.finditer(text):
                    if is_scanner_rule_definition(path, text, match.start()) or is_dynamic_secret_assignment(text, match.start()):
                        continue
                    snippet = text[match.start():match.end()]
                    finding = {"file": rel, "pattern": pattern.pattern, "offset": match.start()}
                    if placeholder_re.search(snippet) or bucket == "doc":
                        doc_examples.append(finding)
                    else:
                        runtime_critical.append(finding)
            for pattern in warning_patterns:
                for match in pattern.finditer(text):
                    if is_scanner_rule_definition(path, text, match.start()) or is_placeholder_allowlist_definition(path, text, match.start()):
                        continue
                    finding = {"file": rel, "pattern": pattern.pattern, "offset": match.start()}
                    if bucket == "runtime":
                        runtime_warnings.append(finding)
                    else:
                        doc_examples.append(finding)
        warnings = runtime_warnings
        result = {
            "runtime_critical_count": len(runtime_critical),
            "runtime_warning_count": len(runtime_warnings),
            "doc_warning_count": 0,
            "doc_example_count": len(doc_examples),
            "critical_count": len(runtime_critical),
            "warning_count": len(warnings),
            "runtime_critical": runtime_critical[:20],
            "runtime_warnings": runtime_warnings[:20],
            "doc_warnings": [],
            "doc_examples": doc_examples[:20],
            "critical": runtime_critical[:20],
            "warnings": warnings[:20],
            "status": "PASS" if not runtime_critical else "FAIL",
        }
        print(f"  Runtime高危问题: {len(runtime_critical)}")
        print(f"  Runtime警告项: {len(runtime_warnings)}")
        print(f"  文档/测试示例项: {len(doc_examples)}")
        print(f"  状态: {result['status']}")
        return result

    def check_stress(self) -> Dict[str, Any]:
        """轻量压力边界：验证多站点管理器可承受批量注册。"""
        print("\n=== 检查压力边界 ===")
        try:
            sys.path.insert(0, self.project_dir)
            from multi_site_manager import MultiSiteManager  # type: ignore

            manager = MultiSiteManager()
            start = time.perf_counter()
            for index in range(100):
                manager.register_site(f"stress-site-{index}", {"name": f"stress-{index}", "ip": "127.0.0.1"})
            duration_ms = (time.perf_counter() - start) * 1000
            metrics = manager.get_metrics()
            ok = metrics.get("total_sites") == 100 and duration_ms <= 1000.0
            result = {
                "registered_sites": metrics.get("total_sites"),
                "duration_ms": round(duration_ms, 3),
                "threshold_ms": 1000.0,
                "status": "PASS" if ok else "FAIL",
            }
        except Exception as exc:
            result = {"status": "FAIL", "error": str(exc)}
        print(f"  状态: {result['status']}")
        return result

    def check_compatibility(self) -> Dict[str, Any]:
        """兼容性边界：Python 版本和关键 stdlib/可选依赖可用。"""
        print("\n=== 检查兼容性边界 ===")
        required_modules = ["json", "pathlib", "subprocess", "threading", "http.server"]
        missing_modules = []
        for module in required_modules:
            try:
                __import__(module)
            except Exception:
                missing_modules.append(module)
        version_ok = sys.version_info >= (3, 8)
        result = {
            "python_version": sys.version.split()[0],
            "minimum_python": "3.8",
            "missing_modules": missing_modules,
            "status": "PASS" if version_ok and not missing_modules else "FAIL",
        }
        print(f"  Python版本: {result['python_version']}")
        print(f"  缺失模块: {len(missing_modules)}")
        print(f"  状态: {result['status']}")
        return result

    def check_architecture_links(self) -> Dict[str, Any]:
        """架构链路边界：静态验证关键链路组件和入口方法存在。"""
        print("\n=== 检查架构链路边界 ===")
        missing_files = [name for name in self.ARCHITECTURE_CHAIN_COMPONENTS if not (self.project_path / name).exists()]
        method_expectations = {
            "multi_site_manager.py": [["register_site"], ["heartbeat"], ["get_available_site"]],
            "task_event_driven.py": [["handle_event"], ["auto_claim"], ["auto_execute"]],
            "task_pool_event_integration.py": [["process_task_event"]],
            # Edge Worker exposes public capability names through action routing and private handler methods.
            "edge_worker.py": [
                ["run_command", "_run_command"],
                ["read_file", "_read_file"],
                ["write_file", "_write_file"],
                ["list_dir", "_list_dir"],
            ],
        }
        missing_methods = []
        for filename, method_groups in method_expectations.items():
            path = self.project_path / filename
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for alternatives in method_groups:
                if not any(f"def {method}" in text or f"'{method}'" in text or f'"{method}"' in text for method in alternatives):
                    missing_methods.append(f"{filename}:{'/'.join(alternatives)}")
        result = {
            "components": len(self.ARCHITECTURE_CHAIN_COMPONENTS),
            "missing_files": missing_files,
            "missing_methods": missing_methods,
            "status": "PASS" if not missing_files and not missing_methods else "FAIL",
        }
        print(f"  链路组件: {len(self.ARCHITECTURE_CHAIN_COMPONENTS)}")
        print(f"  缺失文件: {len(missing_files)}")
        print(f"  缺失方法: {len(missing_methods)}")
        print(f"  状态: {result['status']}")
        return result

    def _calculate_boundary_coverage(self, checks: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        catalog = self.get_boundary_catalog()
        present = [name for name in catalog if name in checks]
        missing = [name for name in catalog if name not in checks]
        coverage = len(present) / len(catalog) * 100 if catalog else 100.0
        return {
            "required": catalog,
            "present": present,
            "missing": missing,
            "coverage": coverage,
            "status": "PASS" if coverage == 100.0 and not missing else "FAIL",
        }

    def run_full_check(self) -> Dict[str, Any]:
        """运行完整自检。"""
        print("=== 开始自检 ===")
        print(f"项目目录: {self.project_dir}")
        print(f"检查时间: {datetime.now().isoformat()}\n")
        checks = {
            "test_coverage": self.check_test_coverage(),
            "code_quality": self.check_code_quality(),
            "component_integration": self.check_component_integration(),
            "documentation": self.check_documentation(),
            "deployment": self.check_deployment(),
            "tests": self.run_tests(),
            "performance": self.check_performance(),
            "security": self.check_security(),
            "stress": self.check_stress(),
            "compatibility": self.check_compatibility(),
            "architecture_links": self.check_architecture_links(),
        }
        boundary_coverage = self._calculate_boundary_coverage(checks)
        all_passed = all(check.get("status") == "PASS" for check in checks.values()) and boundary_coverage["status"] == "PASS"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "project_dir": self.project_dir,
            "checks": checks,
            "boundary_coverage": boundary_coverage,
            "overall_status": "PASS" if all_passed else "FAIL",
        }
        print("\n=== 自检总结 ===")
        for check_name, check_result in checks.items():
            print(f"  {check_name}: {check_result.get('status', 'UNKNOWN')}")
        print(f"  boundary_coverage: {boundary_coverage['coverage']:.1f}%")
        print(f"\n总体状态: {self.results['overall_status']}")
        return self.results

    def save_report(self, filepath: str):
        """保存报告。"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n报告已保存: {filepath}")


def main():
    """主函数。"""
    project_dir = os.environ.get("HERMES_EDGE_WORKER_DIR", "/Users/charles/hermes-edge-worker")
    checker = SelfChecker(project_dir)
    results = checker.run_full_check()
    report_path = os.path.join(project_dir, "self_check_report.json")
    checker.save_report(report_path)
    sys.exit(0 if results["overall_status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
