#!/bin/bash
# Hermes Edge Worker 安装脚本
# SSL 证书异常时默认安全；交互终端可确认临时跳过校验，非交互环境需显式设置 HERMES_EDGE_ALLOW_INSECURE_SSL=1。

set -e

INSTALL_DIR="$HOME/.hermes/edge-worker"
REPO_URL="https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main"

# 检测 SSL 证书链；禁止静默降级 TLS 校验。
CURL_OPTS="-sSL"
if ! curl -sSL --connect-timeout 5 "$REPO_URL/install.sh" >/dev/null 2>&1; then
    echo "[!] 无法验证 GitHub 下载源的 TLS 证书。"
    echo "    常见原因：公司代理、自签 CA、系统 CA 过旧，或网络被劫持。"
    echo "    推荐先修复系统 CA/代理证书，或切换到可信网络后重试。"

    if [ "${HERMES_EDGE_ALLOW_INSECURE_SSL:-0}" = "1" ]; then
        echo "[!] 已检测到 HERMES_EDGE_ALLOW_INSECURE_SSL=1，将按显式要求临时跳过 TLS 校验。"
        CURL_OPTS="-sSLk"
    elif [ -t 0 ]; then
        echo ""
        echo "    临时跳过 TLS 校验可继续安装，但存在下载内容被篡改的风险。"
        printf "    是否仅本次跳过 TLS 校验继续安装？输入 yes 继续: "
        read -r confirm_insecure_ssl
        if [ "$confirm_insecure_ssl" = "yes" ]; then
            echo "[!] 已按用户确认进入不安全下载模式。"
            CURL_OPTS="-sSLk"
        else
            echo "[✗] 已取消安装。请修复系统 CA/代理证书后重试。"
            exit 1
        fi
    else
        echo "[✗] 非交互环境中拒绝自动跳过 TLS 校验。"
        echo "    临时测试可显式设置：HERMES_EDGE_ALLOW_INSECURE_SSL=1"
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
