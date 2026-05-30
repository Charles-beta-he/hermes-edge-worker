#!/usr/bin/env python3
"""
架构自检工具
缺陷识别与论点分析
"""

import os
import sys
import json
import ast
from datetime import datetime
from typing import Dict, Any, List

class ArchitectureSelfCheck:
    """架构自检"""
    
    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.defects = []
        self.warnings = []
        self.passed = []
    
    def check_code_quality(self) -> Dict[str, Any]:
        """检查代码质量"""
        print("=== 代码质量检查 ===")
        
        # 检查Python语法
        syntax_errors = 0
        for root, dirs, files in os.walk(self.project_dir):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r') as f:
                            ast.parse(f.read())
                    except SyntaxError as e:
                        syntax_errors += 1
                        self.defects.append(f"语法错误: {filepath}: {e}")
                        print(f"  ✗ 语法错误: {filepath}")
        
        if syntax_errors == 0:
            self.passed.append("代码质量检查")
            print("  ✓ 代码质量检查通过")
        
        return {
            "syntax_errors": syntax_errors,
            "status": "PASS" if syntax_errors == 0 else "FAIL"
        }
    
    def check_component_integration(self) -> Dict[str, Any]:
        """检查组件集成"""
        print("\n=== 组件集成检查 ===")
        
        core_components = [
            "unified_data_layer.py",
            "unified_event_bus.py",
            "knowledge_manager.py",
            "rag_knowledge_manager.py",
            "edge_worker.py"
        ]
        
        missing_components = []
        for component in core_components:
            filepath = os.path.join(self.project_dir, component)
            if not os.path.exists(filepath):
                missing_components.append(component)
                self.defects.append(f"缺失组件: {component}")
                print(f"  ✗ 缺失: {component}")
            else:
                print(f"  ✓ 存在: {component}")
        
        if not missing_components:
            self.passed.append("组件集成检查")
            print("  ✓ 组件集成检查通过")
        
        return {
            "total_components": len(core_components),
            "missing_components": missing_components,
            "status": "PASS" if not missing_components else "FAIL"
        }
    
    def check_dependency_chain(self) -> Dict[str, Any]:
        """检查依赖链"""
        print("\n=== 依赖链检查 ===")
        
        # 检查核心依赖
        dependencies = {
            "scikit-learn": "sklearn",
            "numpy": "numpy"
        }
        
        missing_deps = []
        for dep_name, import_name in dependencies.items():
            try:
                __import__(import_name)
                print(f"  ✓ {dep_name}")
            except ImportError:
                missing_deps.append(dep_name)
                self.defects.append(f"缺失依赖: {dep_name}")
                print(f"  ✗ 缺失: {dep_name}")
        
        if not missing_deps:
            self.passed.append("依赖链检查")
            print("  ✓ 依赖链检查通过")
        
        return {
            "total_dependencies": len(dependencies),
            "missing_dependencies": missing_deps,
            "status": "PASS" if not missing_deps else "FAIL"
        }
    
    def check_data_consistency(self) -> Dict[str, Any]:
        """检查数据一致性"""
        print("\n=== 数据一致性检查 ===")
        
        # 检查数据层
        try:
            sys.path.insert(0, self.project_dir)
            from unified_data_layer import UnifiedDataLayer
            
            data_layer = UnifiedDataLayer(storage_dir="/tmp/test_consistency")
            
            # 测试存储和检索
            test_data = {"type": "test", "value": 123}
            data_layer.store("test", "test-001", test_data)
            retrieved = data_layer.retrieve("test", "test-001")
            
            if retrieved == test_data:
                self.passed.append("数据一致性检查")
                print("  ✓ 数据一致性检查通过")
                return {"status": "PASS"}
            else:
                self.defects.append("数据不一致: 存储和检索结果不同")
                print("  ✗ 数据不一致")
                return {"status": "FAIL"}
        except Exception as e:
            self.defects.append(f"数据层错误: {e}")
            print(f"  ✗ 数据层错误: {e}")
            return {"status": "FAIL"}
    
    def check_event_bus(self) -> Dict[str, Any]:
        """检查事件总线"""
        print("\n=== 事件总线检查 ===")
        
        try:
            sys.path.insert(0, self.project_dir)
            from unified_event_bus import UnifiedEventBus, EventHandler
            
            event_bus = UnifiedEventBus()
            
            # 测试事件发布和订阅
            events_received = []
            def handler(event):
                events_received.append(event)
            
            event_handler = EventHandler(
                handler_id="test_handler",
                handler_func=handler,
                event_types=["test.event"]
            )
            
            event_bus.subscribe("test.event", event_handler)
            event_bus.publish("test.event", {"data": "test"})
            
            if len(events_received) == 1:
                self.passed.append("事件总线检查")
                print("  ✓ 事件总线检查通过")
                return {"status": "PASS"}
            else:
                self.defects.append("事件总线异常: 事件未正确接收")
                print("  ✗ 事件总线异常")
                return {"status": "FAIL"}
        except Exception as e:
            self.defects.append(f"事件总线错误: {e}")
            print(f"  ✗ 事件总线错误: {e}")
            return {"status": "FAIL"}
    
    def check_knowledge_manager(self) -> Dict[str, Any]:
        """检查知识管理器"""
        print("\n=== 知识管理器检查 ===")
        
        try:
            sys.path.insert(0, self.project_dir)
            from knowledge_manager import KnowledgeManager
            
            manager = KnowledgeManager()
            
            # 测试知识记录和搜索
            manager.record_experience({
                "title": "测试知识",
                "content": "测试内容",
                "tags": ["test"]
            })
            
            results = manager.search_experience("测试")
            
            if len(results) > 0:
                self.passed.append("知识管理器检查")
                print("  ✓ 知识管理器检查通过")
                return {"status": "PASS"}
            else:
                self.defects.append("知识管理器异常: 搜索无结果")
                print("  ✗ 知识管理器异常")
                return {"status": "FAIL"}
        except Exception as e:
            self.defects.append(f"知识管理器错误: {e}")
            print(f"  ✗ 知识管理器错误: {e}")
            return {"status": "FAIL"}
    
    def check_rag_system(self) -> Dict[str, Any]:
        """检查RAG系统"""
        print("\n=== RAG系统检查 ===")
        
        try:
            sys.path.insert(0, self.project_dir)
            from rag_knowledge_manager import RAGKnowledgeManager
            
            manager = RAGKnowledgeManager()
            
            # 测试知识添加和搜索
            manager.add_knowledge("1", "测试内容", {"category": "test"})
            results = manager.search("测试")
            
            if len(results) > 0:
                self.passed.append("RAG系统检查")
                print("  ✓ RAG系统检查通过")
                return {"status": "PASS"}
            else:
                self.defects.append("RAG系统异常: 搜索无结果")
                print("  ✗ RAG系统异常")
                return {"status": "FAIL"}
        except Exception as e:
            self.defects.append(f"RAG系统错误: {e}")
            print(f"  ✗ RAG系统错误: {e}")
            return {"status": "FAIL"}
    
    def check_performance(self) -> Dict[str, Any]:
        """检查性能"""
        print("\n=== 性能检查 ===")
        
        try:
            sys.path.insert(0, self.project_dir)
            from unified_data_layer import UnifiedDataLayer
            import time
            
            data_layer = UnifiedDataLayer(storage_dir="/tmp/test_performance")
            
            # 测试存储性能
            start_time = time.time()
            for i in range(100):
                data_layer.store("task", f"task-{i}", {"index": i})
            store_time = time.time() - start_time
            
            # 测试检索性能
            start_time = time.time()
            for i in range(100):
                data_layer.retrieve("task", f"task-{i}")
            retrieve_time = time.time() - start_time
            
            if store_time < 1.0 and retrieve_time < 1.0:
                self.passed.append("性能检查")
                print(f"  ✓ 性能检查通过 (存储: {store_time:.3f}s, 检索: {retrieve_time:.3f}s)")
                return {"status": "PASS", "store_time": store_time, "retrieve_time": retrieve_time}
            else:
                self.warnings.append(f"性能警告: 存储{store_time:.3f}s, 检索{retrieve_time:.3f}s")
                print(f"  ⚠ 性能警告 (存储: {store_time:.3f}s, 检索: {retrieve_time:.3f}s)")
                return {"status": "WARN", "store_time": store_time, "retrieve_time": retrieve_time}
        except Exception as e:
            self.defects.append(f"性能检查错误: {e}")
            print(f"  ✗ 性能检查错误: {e}")
            return {"status": "FAIL"}
    
    def run_full_check(self) -> Dict[str, Any]:
        """运行完整自检"""
        print("=== 开始架构自检 ===")
        print(f"项目目录: {self.project_dir}")
        print(f"检查时间: {datetime.now().isoformat()}")
        print()
        
        # 运行所有检查
        results = {
            "timestamp": datetime.now().isoformat(),
            "project_dir": self.project_dir,
            "checks": {
                "code_quality": self.check_code_quality(),
                "component_integration": self.check_component_integration(),
                "dependency_chain": self.check_dependency_chain(),
                "data_consistency": self.check_data_consistency(),
                "event_bus": self.check_event_bus(),
                "knowledge_manager": self.check_knowledge_manager(),
                "rag_system": self.check_rag_system(),
                "performance": self.check_performance()
            }
        }
        
        # 计算总体状态
        all_passed = all(
            check.get("status") == "PASS" 
            for check in results["checks"].values()
        )
        
        results["overall_status"] = "PASS" if all_passed else "FAIL"
        results["defects"] = self.defects
        results["warnings"] = self.warnings
        results["passed"] = self.passed
        
        # 打印总结
        print("\n=== 自检总结 ===")
        print(f"通过: {len(self.passed)}")
        print(f"警告: {len(self.warnings)}")
        print(f"缺陷: {len(self.defects)}")
        
        if self.defects:
            print("\n=== 缺陷详情 ===")
            for defect in self.defects:
                print(f"  ✗ {defect}")
        
        if self.warnings:
            print("\n=== 警告详情 ===")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
        
        print(f"\n总体状态: {results['overall_status']}")
        
        return results

def main():
    """主函数"""
    project_dir = "/Users/charles/hermes-edge-worker"
    
    # 创建自检器
    checker = ArchitectureSelfCheck(project_dir)
    
    # 运行自检
    results = checker.run_full_check()
    
    # 保存报告
    report_path = os.path.join(project_dir, "architecture_self_check.json")
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n报告已保存: {report_path}")
    
    # 返回状态码
    sys.exit(0 if results["overall_status"] == "PASS" else 1)

if __name__ == "__main__":
    main()
