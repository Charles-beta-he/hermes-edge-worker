#!/bin/bash
# Hermes Edge Worker 安装脚本
# 从私人仓库安装

set -e

INSTALL_DIR="$HOME/.hermes/edge-worker"
REPO_URL="https://raw.githubusercontent.com/Charles-beta-he/personal-hermes-brain/main/hermes/scripts/edge-worker"

echo "╔══════════════════════════════════════════════════╗"
echo "║       Hermes Edge Worker 安装                    ║"
echo "╚══════════════════════════════════════════════════╝"

# 检查Python
if ! command -v python3 &>/dev/null; then
    echo "[✗] 需要Python 3.8+"
    exit 1
fi

echo "[✓] Python $(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

# 创建目录
mkdir -p "$INSTALL_DIR"/{logs,backups}

# 下载文件
echo "[*] 下载Edge Worker..."
curl -sSL "$REPO_URL/edge_worker.py" -o "$INSTALL_DIR/edge_worker.py"
curl -sSL "$REPO_URL/hermes_lan.py" -o "$INSTALL_DIR/hermes_lan.py"
curl -sSL "$REPO_URL/config.yaml" -o "$INSTALL_DIR/config.yaml"

# 创建CLI包装器
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

# 创建符号链接
mkdir -p "$HOME/.local/bin"
ln -sf "$INSTALL_DIR/hermes-edge" "$HOME/.local/bin/hermes-edge"

echo "[✓] 安装完成"
echo ""
echo "使用方法:"
echo "  hermes-edge start        # 前台启动"
echo "  hermes-edge start --daemon  # 后台启动"
echo "  hermes-edge status       # 查看状态"
echo "  hermes-edge logs         # 查看日志"
