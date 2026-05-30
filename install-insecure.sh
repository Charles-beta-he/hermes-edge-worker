#!/bin/bash
# Hermes Edge Worker 安装脚本（SSL问题专用版本）
# 所有curl调用都使用 -k 跳过SSL验证

set -e

INSTALL_DIR="$HOME/.hermes/edge-worker"
REPO_URL="https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main"

echo "╔══════════════════════════════════════════════════╗"
echo "║       Hermes Edge Worker 安装                    ║"
echo "║       (SSL问题专用版本)                          ║"
echo "╚══════════════════════════════════════════════════╝"

if ! command -v python3 &>/dev/null; then
    echo "[✗] 需要Python 3.8+"
    exit 1
fi

echo "[✓] Python $(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

mkdir -p "$INSTALL_DIR"/{logs,backups}

echo "[*] 下载Edge Worker（跳过SSL验证）..."
curl -sSLk "$REPO_URL/edge_worker.py" -o "$INSTALL_DIR/edge_worker.py"
curl -sSLk "$REPO_URL/hermes_lan.py" -o "$INSTALL_DIR/hermes_lan.py"
curl -sSLk "$REPO_URL/config.yaml" -o "$INSTALL_DIR/config.yaml"

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
