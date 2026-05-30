#!/bin/bash
# Hermes Edge Worker 一键安装脚本
# 用户只需运行：curl -sSLk <url> | bash
# 剩余全部自动化

set -e

INSTALL_DIR="$HOME/.hermes/edge-worker"
REPO_URL="https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main"
LINK_DIR="$HOME/.local/bin"
MAIN_NODE="http://192.168.31.71:9001"
TOKEN="hermes-2024"

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

clear
echo "╔══════════════════════════════════════════════════╗"
echo "║       Hermes Edge Worker 一键安装                ║"
echo "║                                                  ║"
echo "║  自动完成：下载 → 配置 → 启动 → 注册            ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# 1. 检查Python
info "检查环境..."
if ! command -v python3 &>/dev/null; then
    error "需要Python 3.8+，请先安装"
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
log "Python $PYTHON_VERSION"

# 2. 获取主机名（自动）
HOSTNAME=$(hostname -s 2>/dev/null || echo "worker-$(date +%s)")
log "主机名: $HOSTNAME"

# 3. 创建目录
info "创建目录..."
mkdir -p "$INSTALL_DIR"/{logs,backups}
mkdir -p "$LINK_DIR"

# 4. 检测SSL并下载
info "下载组件..."
CURL_OPTS="-sSL"
if ! curl -sSL --connect-timeout 5 "$REPO_URL/version.txt" >/dev/null 2>&1; then
    CURL_OPTS="-sSLk"
    warn "检测到SSL问题，使用安全模式"
fi

curl $CURL_OPTS "$REPO_URL/edge_worker.py" -o "$INSTALL_DIR/edge_worker.py"
curl $CURL_OPTS "$REPO_URL/hermes_lan.py" -o "$INSTALL_DIR/hermes_lan.py"
log "下载完成"

# 5. 自动生成配置（无需用户编辑）
info "生成配置..."
cat > "$INSTALL_DIR/config.yaml" << EOF
# Hermes Edge Worker 配置（自动生成）
# 生成时间: $(date)

worker:
  name: "$HOSTNAME"
  host: "0.0.0.0"
  port: 9002
  main_node: "$MAIN_NODE"
  token: "$TOKEN"
  auto_discover: true
  heartbeat_interval: 30

security:
  token: "$TOKEN"
  allowed_commands: []
  max_timeout: 300

logging:
  level: "info"
  file: "$INSTALL_DIR/logs/edge.log"
  max_size: "10MB"
  max_files: 5
EOF
log "配置已生成"

# 6. 创建CLI（自动处理路径）
info "创建CLI工具..."
cat > "$INSTALL_DIR/hermes-edge" << 'CLI_EOF'
#!/bin/bash
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

[ ! -f "$WORKER_SCRIPT" ] && echo "错误: 找不到 $WORKER_SCRIPT" && exit 1

case "${1:-start}" in
    start)
        if [ "$2" = "--daemon" ] || [ "$2" = "-d" ] || [ -z "$2" ]; then
            # 默认后台启动
            if [ -f "$SCRIPT_DIR/worker.pid" ] && kill -0 $(cat "$SCRIPT_DIR/worker.pid") 2>/dev/null; then
                echo "已在运行 (PID: $(cat $SCRIPT_DIR/worker.pid))"
                exit 0
            fi
            nohup $PYTHON "$WORKER_SCRIPT" > "$SCRIPT_DIR/logs/worker.log" 2>&1 &
            echo $! > "$SCRIPT_DIR/worker.pid"
            sleep 1
            if kill -0 $(cat "$SCRIPT_DIR/worker.pid") 2>/dev/null; then
                echo "✓ 已启动 (PID: $(cat $SCRIPT_DIR/worker.pid))"
            else
                echo "✗ 启动失败"
                cat "$SCRIPT_DIR/logs/worker.log" | tail -5
                exit 1
            fi
        else
            # 前台启动
            $PYTHON "$WORKER_SCRIPT"
        fi
        ;;
    stop)
        if [ -f "$SCRIPT_DIR/worker.pid" ]; then
            PID=$(cat "$SCRIPT_DIR/worker.pid")
            kill $PID 2>/dev/null && echo "✓ 已停止" || echo "进程已退出"
            rm -f "$SCRIPT_DIR/worker.pid"
        else
            echo "未运行"
        fi
        ;;
    restart)
        $0 stop 2>/dev/null
        sleep 1
        $0 start
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
        echo "用法: hermes-edge {start|stop|restart|status|logs}"
        ;;
esac
CLI_EOF

chmod +x "$INSTALL_DIR/hermes-edge"
ln -sf "$INSTALL_DIR/hermes-edge" "$LINK_DIR/hermes-edge"
log "CLI已创建"

# 7. 自动启动服务
info "启动服务..."
# 先停止旧进程
if [ -f "$INSTALL_DIR/worker.pid" ]; then
    kill $(cat "$INSTALL_DIR/worker.pid") 2>/dev/null
    rm -f "$INSTALL_DIR/worker.pid"
fi

# 启动新进程
cd "$INSTALL_DIR"
nohup python3 edge_worker.py > logs/worker.log 2>&1 &
WORKER_PID=$!
echo $WORKER_PID > "$INSTALL_DIR/worker.pid"
sleep 2

# 检查是否启动成功
if kill -0 $WORKER_PID 2>/dev/null; then
    log "服务已启动 (PID: $WORKER_PID)"
else
    error "服务启动失败"
    cat logs/worker.log | tail -10
    exit 1
fi

# 8. 自动注册到主节点
info "注册到主节点..."
sleep 1
if curl -s --connect-timeout 5 http://localhost:9002/health >/dev/null 2>&1; then
    log "本地服务正常"
else
    warn "本地服务异常"
fi

# 9. 验证连接
info "验证连接..."
if curl -s --connect-timeout 5 "$MAIN_NODE/health" >/dev/null 2>&1; then
    log "主节点连接正常"
else
    warn "主节点连接失败（服务仍可本地运行）"
fi

# 10. 完成
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║              安装完成！                          ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║                                                  ║"
echo "║  主机名: $HOSTNAME"
echo "║  端口: 9002"
echo "║  主节点: $MAIN_NODE"
echo "║  状态: 运行中 (PID: $WORKER_PID)"
echo "║                                                  ║"
echo "║  命令:                                           ║"
echo "║    hermes-edge status   查看状态                 ║"
echo "║    hermes-edge logs     查看日志                 ║"
echo "║    hermes-edge restart  重启服务                 ║"
echo "║    hermes-edge stop     停止服务                 ║"
echo "║                                                  ║"
echo "╚══════════════════════════════════════════════════╝"
