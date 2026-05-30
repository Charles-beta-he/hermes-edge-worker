#!/usr/bin/env python3
"""simplified/ reference 边界测试。"""

from pathlib import Path


def test_simplified_readme_declares_reference_not_production():
    readme = Path("simplified/README.md").read_text(encoding="utf-8")

    assert "reference implementation" in readme
    assert "不是生产主线" in readme
    assert "禁止将 `simplified/edge_worker.py` 作为生产 Edge Worker 启动入口" in readme
    assert "Brain/taskpool SSOT" in readme


def test_root_runtime_topology_rejects_simplified_as_production_mainline():
    topology = Path("RUNTIME-TOPOLOGY.md").read_text(encoding="utf-8")

    assert "禁止把 simplified/ reference 代码当生产主线直接运行" in topology
