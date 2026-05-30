#!/usr/bin/env python3
"""自检边界覆盖测试。"""

import tempfile
import unittest
from pathlib import Path

from self_check import SelfChecker


class TestSelfCheckBoundaryCoverage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        (self.project / "README.md").write_text("# Demo\n", encoding="utf-8")
        (self.project / "SYSTEM-ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
        (self.project / "install.sh").write_text("#!/bin/bash\necho install\n", encoding="utf-8")
        (self.project / "config.yaml").write_text("host: 0.0.0.0\n", encoding="utf-8")
        (self.project / "unified_data_layer.py").write_text("class UnifiedDataLayer: pass\n", encoding="utf-8")
        (self.project / "unified_event_bus.py").write_text("class UnifiedEventBus: pass\n", encoding="utf-8")
        (self.project / "unified_interface_layer.py").write_text("class UnifiedInterfaceLayer: pass\n", encoding="utf-8")
        (self.project / "knowledge_manager.py").write_text("class KnowledgeManager: pass\n", encoding="utf-8")
        (self.project / "rag_knowledge_manager.py").write_text("class RAGKnowledgeManager: pass\n", encoding="utf-8")
        (self.project / "site_registrar.py").write_text("class SiteRegistrar: pass\n", encoding="utf-8")
        (self.project / "multi_site_manager.py").write_text(
            "class MultiSiteManager:\n"
            "    def __init__(self): self.sites = {}\n"
            "    def register_site(self, site_id, info): self.sites[site_id] = info; return True\n"
            "    def heartbeat(self, site_id): return site_id in self.sites\n"
            "    def get_available_site(self): return next(iter(self.sites), None)\n"
            "    def get_metrics(self): return {'total_sites': len(self.sites)}\n",
            encoding="utf-8",
        )
        (self.project / "task_event_driven.py").write_text(
            "class TaskEventDriven:\n"
            "    def handle_event(self, *a, **k): return True\n"
            "    def auto_claim(self, *a, **k): return True\n"
            "    def auto_execute(self, *a, **k): return True\n",
            encoding="utf-8",
        )
        (self.project / "task_pool_event_integration.py").write_text(
            "class TaskPoolEventIntegration:\n"
            "    def process_task_event(self, *a, **k): return True\n",
            encoding="utf-8",
        )
        (self.project / "edge_worker.py").write_text(
            "def run_command(*a, **k): return {}\n"
            "def read_file(*a, **k): return ''\n"
            "def write_file(*a, **k): return True\n"
            "def list_dir(*a, **k): return []\n",
            encoding="utf-8",
        )
        for source in self.project.glob("*.py"):
            if source.name.startswith("test_"):
                continue
            test_path = self.project / f"test_{source.stem}.py"
            test_path.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
        (self.project / "test_complete.py").write_text("def test_complete_ok():\n    assert True\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_boundary_check_catalog_includes_quality_edges(self):
        checker = SelfChecker(str(self.project))
        catalog = checker.get_boundary_catalog()
        required = {
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
        }
        self.assertTrue(required.issubset(set(catalog)), catalog)

    def test_full_check_reports_boundary_coverage_and_all_required_edges(self):
        checker = SelfChecker(str(self.project))
        results = checker.run_full_check()
        checks = results["checks"]
        for name in checker.get_boundary_catalog():
            self.assertIn(name, checks)
        self.assertIn("boundary_coverage", results)
        self.assertEqual(results["boundary_coverage"]["coverage"], 100.0)
        self.assertEqual(checks["tests"]["status"], "PASS")
        self.assertEqual(results["overall_status"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
