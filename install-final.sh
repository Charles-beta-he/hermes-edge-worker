#!/bin/bash
# Hermes Edge Worker 最终安装脚本
# 支持：兼容现有安装、自动升级、配置保留

set -e

INSTALL_DIR="$HOME/.hermes/edge-worker"
REPO_URL="https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main"
LINK_DIR="$HOME/.local/bin"
BACKUP_DIR="$INSTALL_DIR/backups"
VERSION_FILE="$INSTALL_DIR/version.txt"

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
echo "║       (最终优化版本 - 支持升级)                  ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# 检查Python
if ! command -v python3 &>/dev/null; then
    error "需要Python 3.8+，请先安装"
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
log "Python $PYTHON_VERSION"

# 检测现有安装
EXISTING_INSTALL=false
CURRENT_VERSION=""
if [ -d "$INSTALL_DIR" ] && [ -f "$INSTALL_DIR/edge_worker.py" ]; then
    EXISTING_INSTALL=true
    if [ -f "$VERSION_FILE" ]; then
        CURRENT_VERSION=$(cat "$VERSION_FILE")
    else
        CURRENT_VERSION="unknown"
    fi
    info "检测到现有安装（版本: $CURRENT_VERSION）"
fi

# 创建目录
info "创建目录结构..."
mkdir -p "$INSTALL_DIR"/{logs,backups,src}
mkdir -p "$LINK_DIR"

# 备份现有文件（如果是升级）
if [ "$EXISTING_INSTALL" = true ]; then
    BACKUP_TIMESTAMP=$(date '+%Y%m%d%H%M%S')
    BACKUP_PATH="$BACKUP_DIR/backup-$BACKUP_TIMESTAMP"
    info "备份现有文件到: $BACKUP_PATH"
    mkdir -p "$BACKUP_PATH"
    
    # 备份关键文件
    [ -f "$INSTALL_DIR/edge_worker.py" ] && cp "$INSTALL_DIR/edge_worker.py" "$BACKUP_PATH/"
    [ -f "$INSTALL_DIR/hermes_lan.py" ] && cp "$INSTALL_DIR/hermes_lan.py" "$BACKUP_PATH/"
    [ -f "$INSTALL_DIR/config.yaml" ] && cp "$INSTALL_DIR/config.yaml" "$BACKUP_PATH/"
    [ -f "$INSTALL_DIR/hermes-edge" ] && cp "$INSTALL_DIR/hermes-edge" "$BACKUP_PATH/"
    
    log "备份完成"
fi

# 检测SSL问题
info "检测网络环境..."
CURL_OPTS="-sSL"
if ! curl -sSL --connect-timeout 5 "$REPO_URL/install-final.sh" >/dev/null 2>&1; then
    warn "检测到SSL问题，使用不安全模式..."
    CURL_OPTS="-sSLk"
fi

# 下载新版本号
info "检查最新版本..."
LATEST_VERSION=$(curl $CURL_OPTS "$REPO_URL/version.txt" 2>/dev/null || echo "1.0.0")
log "最新版本: $LATEST_VERSION"

# 检查是否需要升级
if [ "$EXISTING_INSTALL" = true ] && [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    log "已是最新版本，跳过升级"
    echo ""
    echo "如需强制重新安装，请先删除 $INSTALL_DIR"
    exit 0
fi

# 下载文件
if [ "$EXISTING_INSTALL" = true ]; then
    info "升级Edge Worker ($CURRENT_VERSION -> $LATEST_VERSION)..."
else
    info "安装Edge Worker ($LATEST_VERSION)..."
fi

curl $CURL_OPTS "$REPO_URL/edge_worker.py" -o "$INSTALL_DIR/edge_worker.py" || error "下载edge_worker.py失败"
curl $CURL_OPTS "$REPO_URL/hermes_lan.py" -o "$INSTALL_DIR/hermes_lan.py" || error "下载hermes_lan.py失败"

# 配置文件处理（保留用户配置）
if [ "$EXISTING_INSTALL" = true ] && [ -f "$INSTALL_DIR/config.yaml" ]; then
    # 下载新配置到临时文件
    curl $CURL_OPTS "$REPO_URL/config.yaml" -o "$INSTALL_DIR/config.yaml.new" || error "下载config.yaml失败"
    
    # 比较配置文件
    if diff -q "$INSTALL_DIR/config.yaml" "$INSTALL_DIR/config.yaml.new" >/dev/null 2>&1; then
        rm "$INSTALL_DIR/config.yaml.new"
        log "配置文件无变化"
    else
        warn "检测到配置文件更新"
        info "现有配置已保留，新配置保存为: config.yaml.new"
        info "如需使用新配置，请运行: mv $INSTALL_DIR/config.yaml.new $INSTALL_DIR/config.yaml"
    fi
else
    curl $CURL_OPTS "$REPO_URL/config.yaml" -o "$INSTALL_DIR/config.yaml" || error "下载config.yaml失败"
fi

# 更新版本号
echo "$LATEST_VERSION" > "$VERSION_FILE"

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

# 版本信息
VERSION="unknown"
[ -f "$SCRIPT_DIR/version.txt" ] && VERSION=$(cat "$SCRIPT_DIR/version.txt")

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
        echo "Hermes Edge Worker v$VERSION"
        echo ""
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
        echo "当前版本: $VERSION"
        echo "检查更新..."
        curl -sSLk "https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install-final.sh" | bash
        ;;
    rollback)
        if [ -d "$SCRIPT_DIR/backups" ]; then
            echo "可用备份:"
            ls -lt "$SCRIPT_DIR/backups" | head -5
            echo ""
            read -p "输入备份目录名（或留空取消）: " backup_name
            if [ -n "$backup_name" ] && [ -d "$SCRIPT_DIR/backups/$backup_name" ]; then
                echo "回滚到: $backup_name"
                cp "$SCRIPT_DIR/backups/$backup_name"/*.py "$SCRIPT_DIR/" 2>/dev/null || true
                cp "$SCRIPT_DIR/backups/$backup_name"/config.yaml "$SCRIPT_DIR/" 2>/dev/null || true
                echo "✓ 回滚完成"
            fi
        else
            echo "没有可用的备份"
        fi
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
        echo "Hermes Edge Worker CLI v$VERSION"
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
        echo "  rollback          回滚到备份版本"
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
if [ "$EXISTING_INSTALL" = true ]; then
    echo "╔══════════════════════════════════════════════════╗"
    echo "║                   升级完成！                      ║"
    echo "╠══════════════════════════════════════════════════╣"
    echo "║ 版本: $CURRENT_VERSION -> $LATEST_VERSION"
    echo "║ 备份: $BACKUP_PATH"
else
    echo "╔══════════════════════════════════════════════════╗"
    echo "║                   安装完成！                      ║"
    echo "╠══════════════════════════════════════════════════╣"
    echo "║ 版本: $LATEST_VERSION"
fi

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
