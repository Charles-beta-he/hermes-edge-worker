#!/usr/bin/env python3
"""self_check 安全分级测试。"""

from pathlib import Path

from self_check import SelfChecker


def test_runtime_secret_is_fail_closed_but_docs_are_warning(tmp_path):
    (tmp_path / "README.md").write_text("# Demo\nexample: curl https://example.com/install.sh | bash\n", encoding="utf-8")
    (tmp_path / "runtime.py").write_text("API_KEY = 'abcdefghijklmnopqrstuvwxyz'\n", encoding="utf-8")

    result = SelfChecker(str(tmp_path)).check_security()

    assert result["status"] == "FAIL"
    assert result["runtime_critical_count"] == 1
    assert result["doc_warning_count"] == 0
    assert result["doc_example_count"] == 1
    assert result["runtime_critical"][0]["file"] == "runtime.py"


def test_placeholder_tokens_are_not_runtime_critical(tmp_path):
    (tmp_path / "config.yaml").write_text("token: your-secret-token\n", encoding="utf-8")
    (tmp_path / "script.sh").write_text("curl https://example.com/bootstrap.sh | bash\n", encoding="utf-8")

    result = SelfChecker(str(tmp_path)).check_security()

    assert result["status"] == "PASS"
    assert result["runtime_critical_count"] == 0
    assert result["runtime_warning_count"] >= 1


def test_scanner_rule_definitions_do_not_self_report(tmp_path):
    (tmp_path / "self_check.py").write_text(
        'warning_patterns = [re.compile(r"hermes-2024"), re.compile(r"your-secret-token|changeme|change-me")]\n',
        encoding="utf-8",
    )
    (tmp_path / "edge_worker.py").write_text(
        'return normalized in {"", "your-secret-token", "changeme", "change-me", "token", "secret"}\n',
        encoding="utf-8",
    )

    result = SelfChecker(str(tmp_path)).check_security()

    assert result["runtime_warning_count"] == 0
    assert result["warning_count"] == 0


def test_dynamic_secret_assignments_are_not_hardcoded_secrets(tmp_path):
    (tmp_path / "install.sh").write_text(
        'TOKEN="${HERMES_EDGE_TOKEN:-$(python3 - <<\'PY\'\nprint("generated")\nPY\n)}"\n',
        encoding="utf-8",
    )

    result = SelfChecker(str(tmp_path)).check_security()

    assert result["runtime_critical_count"] == 0
    assert result["status"] == "PASS"
