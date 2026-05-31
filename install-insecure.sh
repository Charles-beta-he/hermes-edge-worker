#!/bin/bash
# Deprecated compatibility entrypoint.
# Historical versions of this file skipped TLS verification by default. That is no longer allowed.

set -e

REPO_URL="https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main"

echo "[!] install-insecure.sh 已废弃：Hermes Edge Worker 不再提供静默跳过 TLS 的安装入口。"
echo "    推荐使用安全安装入口："
echo "      curl -sSL $REPO_URL/install.sh -o install.sh && bash install.sh"
echo ""
echo "    如果你已经下载了 install.sh，且只是临时测试，可显式运行："
echo "      HERMES_EDGE_ALLOW_INSECURE_SSL=1 bash install.sh"
echo ""
echo "    当前脚本将尝试安全下载 install.sh；如 TLS 仍失败，请先修复系统 CA/代理证书。"

tmp_install="$(mktemp)"
trap 'rm -f "$tmp_install"' EXIT
curl -sSL "$REPO_URL/install.sh" -o "$tmp_install"
bash "$tmp_install"
