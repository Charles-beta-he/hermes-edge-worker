"""Install script TLS fallback UX and safety guards."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INSTALL = ROOT / "install.sh"
INSTALL_AUTO = ROOT / "install-auto.sh"
INSTALL_FINAL = ROOT / "install-final.sh"


def _fake_curl(tmp_path: Path, fail_tls_probe: bool) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    curl = bin_dir / "curl"
    curl.write_text(
        f"""#!/usr/bin/env python3
import pathlib
import sys

args = sys.argv[1:]
has_insecure = any(a in ("-k", "--insecure") or (a.startswith("-") and "k" in a) for a in args)
fail_tls_probe = {str(fail_tls_probe)}
url = next((a for a in args if a.startswith("http")), "")

if fail_tls_probe and not has_insecure and (url.endswith("install.sh") or url.endswith("version.txt")):
    print("curl: (60) SSL certificate problem", file=sys.stderr)
    sys.exit(60)

if "-o" in args:
    out = pathlib.Path(args[args.index("-o") + 1])
    out.parent.mkdir(parents=True, exist_ok=True)
    if url.endswith(".py"):
        out.write_text("print('ok')\\n")
    elif url.endswith(".yaml"):
        out.write_text("security:\\n  token: ''\\n")
    else:
        out.write_text("4.7.3\\n")
else:
    sys.stdout.write("ok\\n")
sys.exit(0)
""",
        encoding="utf-8",
    )
    curl.chmod(curl.stat().st_mode | stat.S_IXUSR)
    return bin_dir


def _run_install(tmp_path: Path, fail_tls_probe: bool, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    bin_dir = _fake_curl(tmp_path, fail_tls_probe=fail_tls_probe)
    home = tmp_path / "home"
    home.mkdir()
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "PATH": f"{bin_dir}:{env['PATH']}",
        }
    )
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(INSTALL)],
        text=True,
        capture_output=True,
        env=env,
        timeout=30,
        check=False,
    )


def test_install_succeeds_with_valid_tls(tmp_path: Path) -> None:
    result = _run_install(tmp_path, fail_tls_probe=False)
    assert result.returncode == 0, result.stderr + result.stdout
    assert (tmp_path / "home/.hermes/edge-worker/edge_worker.py").exists()
    assert "安装完成" in result.stdout


def test_install_refuses_noninteractive_tls_failure_without_explicit_escape(tmp_path: Path) -> None:
    result = _run_install(tmp_path, fail_tls_probe=True)
    assert result.returncode != 0
    assert "非交互环境中拒绝自动跳过 TLS 校验" in result.stdout
    assert "HERMES_EDGE_ALLOW_INSECURE_SSL=1" in result.stdout
    assert not (tmp_path / "home/.hermes/edge-worker/edge_worker.py").exists()


def test_install_allows_explicit_insecure_escape_hatch(tmp_path: Path) -> None:
    result = _run_install(
        tmp_path,
        fail_tls_probe=True,
        extra_env={"HERMES_EDGE_ALLOW_INSECURE_SSL": "1"},
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "显式要求临时跳过 TLS 校验" in result.stdout
    assert (tmp_path / "home/.hermes/edge-worker/edge_worker.py").exists()


def test_install_scripts_do_not_silently_enable_insecure_tls() -> None:
    for script in (INSTALL, INSTALL_AUTO, INSTALL_FINAL):
        text = script.read_text(encoding="utf-8")
        assert "CURL_OPTS=\"-sSLk\"" in text
        assert "HERMES_EDGE_ALLOW_INSECURE_SSL" in text
        assert "confirm_insecure_ssl" in text
        assert "非交互环境中拒绝自动跳过 TLS 校验" in text
        assert text.index("HERMES_EDGE_ALLOW_INSECURE_SSL") < text.index('CURL_OPTS="-sSLk"')


def test_default_docs_do_not_recommend_insecure_pipe_execution() -> None:
    checked = [ROOT / "README.md", ROOT / "MANUAL-INSTALL.md", ROOT / "VERIFY-GUIDE.md"]
    forbidden_commands = ("curl -sSLk", "curl -k", "--insecure")
    for path in checked:
        text = path.read_text(encoding="utf-8")
        for command in forbidden_commands:
            assert command not in text
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("curl "):
                assert "| bash" not in stripped
