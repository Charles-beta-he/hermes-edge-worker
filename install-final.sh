#!/bin/bash
# Hermes Edge Worker 最终安装脚本
# 解决：SSL问题、路径解析、用户体验

set -e

INSTALL_DIR="$HOME/.hermes/edge-worker"
REPO_URL="https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main"
LINK_DIR="$HOME/.local/bin"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }
info() { echo -e "${BLUE}[i]${NC} $1"; }

echo "╔══════════════════════════════════════════════════╗"
echo "║       Hermes Edge Worker 安装                    ║"
echo "║       (最终优化版本)                             ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# 检查Python
if ! command -v python3 &>/dev/null; then
    error "需要Python 3.8+，请先安装"
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
log "Python $PYTHON_VERSION"

# 创建目录
info "创建目录结构..."
mkdir -p "$INSTALL_DIR"/{logs,backups,src}
mkdir -p "$LINK_DIR"

# 检测SSL问题
info "检测网络环境..."
CURL_OPTS="-sSL"
if ! curl -sSL --connect-timeout 5 "$REPO_URL/install-final.sh" >/dev/null 2>&1; then
    warn "检测到SSL问题，使用不安全模式..."
    CURL_OPTS="-sSLk"
fi

# 下载文件
info "下载Edge Worker组件..."
curl $CURL_OPTS "$REPO_URL/edge_worker.py" -o "$INSTALL_DIR/edge_worker.py" || error "下载edge_worker.py失败"
curl $CURL_OPTS "$REPO_URL/hermes_lan.py" -o "$INSTALL_DIR/hermes_lan.py" || error "下载hermes_lan.py失败"
curl $CURL_OPTS "$REPO_URL/config.yaml" -o "$INSTALL_DIR/config.yaml" || error "下载config.yaml失败"

log "文件下载完成"

# 创建CLI包装器（关键：正确解析实际路径）
info "创建CLI工具..."
cat > "$INSTALL_DIR/hermes-edge" << 'CLI_EOF'
#!/bin/bash
# Hermes Edge Worker CLI
# 正确解析实际文件路径（处理符号链接）

# 获取脚本的实际路径（不是符号链接路径）
get_script_dir() {
    local source="${BASH_SOURCE[0]}"
    while [ -L "$source" ]; do
        local dir
        dir="$(cd -P "$(dirname "$source")" && pwd)"
        source="$(readlink "$source")"
        [[ $source != /* ]] && source="$dir/$source"
    done
    cd -P "$(dirname "$source")" && pwd
}

SCRIPT_DIR="$(get_script_dir)"
PYTHON="python3"
WORKER_SCRIPT="$SCRIPT_DIR/edge_worker.py"

# 检查Python脚本是否存在
if [ ! -f "$WORKER_SCRIPT" ]; then
    echo "错误: 找不到 $WORKER_SCRIPT"
    echo "请重新运行安装脚本"
    exit 1
fi

case "${1:-help}" in
    start)
        if [ "$2" = "--daemon" ] || [ "$2" = "-d" ]; then
            echo "启动Edge Worker（后台模式）..."
            nohup $PYTHON "$WORKER_SCRIPT" > "$SCRIPT_DIR/logs/worker.log" 2>&1 &
            WORKER_PID=$!
            echo $WORKER_PID > "$SCRIPT_DIR/worker.pid"
            sleep 1
            if kill -0 $WORKER_PID 2>/dev/null; then
                echo "✓ 已启动 (PID: $WORKER_PID)"
                echo "  日志: $SCRIPT_DIR/logs/worker.log"
                echo "  停止: hermes-edge stop"
            else
                echo "✗ 启动失败，查看日志: $SCRIPT_DIR/logs/worker.log"
                exit 1
            fi
        else
            echo "启动Edge Worker（前台模式）..."
            echo "按 Ctrl+C 停止"
            echo ""
            $PYTHON "$WORKER_SCRIPT"
        fi
        ;;
    stop)
        if [ -f "$SCRIPT_DIR/worker.pid" ]; then
            PID=$(cat "$SCRIPT_DIR/worker.pid")
            if kill -0 $PID 2>/dev/null; then
                kill $PID
                rm -f "$SCRIPT_DIR/worker.pid"
                echo "✓ 已停止 (PID: $PID)"
            else
                rm -f "$SCRIPT_DIR/worker.pid"
                echo "进程已不存在"
            fi
        else
            echo "未找到运行中的进程"
        fi
        ;;
    restart)
        $0 stop
        sleep 1
        $0 start --daemon
        ;;
    status)
        if [ -f "$SCRIPT_DIR/worker.pid" ]; then
            PID=$(cat "$SCRIPT_DIR/worker.pid")
            if kill -0 $PID 2>/dev/null; then
                echo "✓ 运行中 (PID: $PID)"
                echo "  启动时间: $(ps -o lstart= -p $PID 2>/dev/null || echo '未知')"
                echo "  日志: $SCRIPT_DIR/logs/worker.log"
            else
                echo "✗ 进程已退出"
                rm -f "$SCRIPT_DIR/worker.pid"
            fi
        else
            echo "✗ 未运行"
        fi
        ;;
    logs)
        if [ -f "$SCRIPT_DIR/logs/worker.log" ]; then
            tail -f "$SCRIPT_DIR/logs/worker.log"
        else
            echo "日志文件不存在"
        fi
        ;;
    config)
        ${EDITOR:-nano} "$SCRIPT_DIR/config.yaml"
        ;;
    update)
        echo "更新Edge Worker..."
        curl -sSLk "https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install-final.sh" | bash
        ;;
    uninstall)
        read -p "确定要卸载Edge Worker吗？(y/N) " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            $0 stop 2>/dev/null
            rm -rf "$SCRIPT_DIR"
            rm -f "$HOME/.local/bin/hermes-edge"
            echo "✓ 已卸载"
        fi
        ;;
    help|*)
        echo "Hermes Edge Worker CLI"
        echo ""
        echo "用法: hermes-edge <command>"
        echo ""
        echo "命令:"
        echo "  start [--daemon]  启动服务（--daemon后台运行）"
        echo "  stop              停止服务"
        echo "  restart           重启服务"
        echo "  status            查看状态"
        echo "  logs              查看日志"
        echo "  config            编辑配置"
        echo "  update            更新到最新版本"
        echo "  uninstall         卸载"
        echo "  help              显示此帮助"
        ;;
esac
CLI_EOF

chmod +x "$INSTALL_DIR/hermes-edge"

# 创建符号链接
ln -sf "$INSTALL_DIR/hermes-edge" "$LINK_DIR/hermes-edge"

# 验证安装
info "验证安装..."
if [ -f "$INSTALL_DIR/edge_worker.py" ] && [ -f "$INSTALL_DIR/hermes-edge" ]; then
    log "安装验证通过"
else
    error "安装验证失败"
fi

# 显示完成信息
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║                   安装完成！                      ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║ 安装目录: $INSTALL_DIR"
echo "║ 命令位置: $LINK_DIR/hermes-edge"
echo "╠══════════════════════════════════════════════════╣"
echo "║ 快速开始:                                        ║"
echo "║   1. 编辑配置: hermes-edge config                ║"
echo "║   2. 启动服务: hermes-edge start --daemon        ║"
echo "║   3. 查看状态: hermes-edge status                ║"
echo "║   4. 查看日志: hermes-edge logs                  ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║ 主节点信息:                                      ║"
echo "║   IP: 192.168.31.71                              ║"
echo "║   端口: 9001                                     ║"
echo "║   Token: hermes-2024                             ║"
echo "╚══════════════════════════════════════════════════╝"
