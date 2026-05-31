#!/bin/bash
# Hermes Edge Worker 安装脚本
# SSL 证书异常时默认 fail-closed；确需跳过校验时显式设置 HERMES_EDGE_ALLOW_INSECURE_SSL=1。

set -e

INSTALL_DIR="$HOME/.hermes/edge-worker"
REPO_URL="https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main"

# 检测 SSL 证书链；禁止静默降级 TLS 校验。
CURL_OPTS="-sSL"
if ! curl -sSL --connect-timeout 5 "$REPO_URL/install.sh" >/dev/null 2>&1; then
    if [ "${HERMES_EDGE_ALLOW_INSECURE_SSL:-0}" = "1" ]; then
        echo "[!] 检测到 SSL 问题；按 HERMES_EDGE_ALLOW_INSECURE_SSL=1 显式要求使用不安全模式..."
        CURL_OPTS="-sSLk"
    else
        echo "[✗] SSL 证书校验失败，已拒绝继续下载。"
        echo "    请先修复系统 CA/代理证书；临时测试可设置 HERMES_EDGE_ALLOW_INSECURE_SSL=1。"
        exit 1
    fi
fi

echo "╔══════════════════════════════════════════════════╗"
echo "║       Hermes Edge Worker 安装                    ║"
echo "╚══════════════════════════════════════════════════╝"

if ! command -v python3 &>/dev/null; then
    echo "[✗] 需要Python 3.8+"
    exit 1
fi

echo "[✓] Python $(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

mkdir -p "$INSTALL_DIR"/{logs,backups}

echo "[*] 下载Edge Worker..."
curl $CURL_OPTS "$REPO_URL/edge_worker.py" -o "$INSTALL_DIR/edge_worker.py"
curl $CURL_OPTS "$REPO_URL/hermes_lan.py" -o "$INSTALL_DIR/hermes_lan.py"
curl $CURL_OPTS "$REPO_URL/config.yaml" -o "$INSTALL_DIR/config.yaml"

cat > "$INSTALL_DIR/hermes-edge" << 'CLI_EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "$1" in
    start)
        if [ "$2" = "--daemon" ]; then
            nohup python3 "$SCRIPT_DIR/edge_worker.py" > "$SCRIPT_DIR/logs/worker.log" 2>&1 &
            echo $! > "$SCRIPT_DIR/worker.pid"
            echo "✓ 已启动（后台）"
        else
            python3 "$SCRIPT_DIR/edge_worker.py"
        fi
        ;;
    stop)
        if [ -f "$SCRIPT_DIR/worker.pid" ]; then
            kill $(cat "$SCRIPT_DIR/worker.pid") 2>/dev/null
            rm "$SCRIPT_DIR/worker.pid"
            echo "✓ 已停止"
        fi
        ;;
    status)
        if [ -f "$SCRIPT_DIR/worker.pid" ] && kill -0 $(cat "$SCRIPT_DIR/worker.pid") 2>/dev/null; then
            echo "✓ 运行中 (PID: $(cat $SCRIPT_DIR/worker.pid))"
        else
            echo "✗ 未运行"
        fi
        ;;
    logs)
        tail -f "$SCRIPT_DIR/logs/worker.log"
        ;;
    *)
        echo "用法: hermes-edge {start|stop|status|logs}"
        ;;
esac
CLI_EOF
chmod +x "$INSTALL_DIR/hermes-edge"

mkdir -p "$HOME/.local/bin"
ln -sf "$INSTALL_DIR/hermes-edge" "$HOME/.local/bin/hermes-edge"

echo "[✓] 安装完成"
echo ""
echo "使用方法:"
echo "  hermes-edge start        # 前台启动"
echo "  hermes-edge start --daemon  # 后台启动"
echo "  hermes-edge status       # 查看状态"
echo "  hermes-edge logs         # 查看日志"
