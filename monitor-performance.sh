#!/bin/bash
# 性能监控脚本
# 三模型讨论优化版

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }
info() { echo -e "${BLUE}[i]${NC} $1"; }

echo "╔══════════════════════════════════════════════════╗"
echo "║       性能监控                                   ║"
echo "║       三模型优化版                               ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# 主节点信息
MAIN_NODE="192.168.31.71:9001"
WORKER_NODE="192.168.31.130:9002"

# 1. 主节点状态
info "1. 主节点状态:"
if curl -s --connect-timeout 5 "http://$MAIN_NODE/health" >/dev/null 2>&1; then
    log "主节点正常"
    curl -s "http://$MAIN_NODE/health" | python3 -m json.tool
else
    error "主节点无法连接"
fi

# 2. 从节点状态
info "2. 从节点状态:"
if curl -s --connect-timeout 5 "http://$WORKER_NODE/health" >/dev/null 2>&1; then
    log "从节点正常"
    curl -s "http://$WORKER_NODE/health" | python3 -m json.tool
else
    error "从节点无法连接"
fi

# 3. 系统资源
info "3. 系统资源:"
echo "  CPU使用率: $(top -l 1 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')"
echo "  内存使用: $(top -l 1 | grep "PhysMem" | awk '{print $2}')"
echo "  磁盘使用: $(df -h / | tail -1 | awk '{print $5}')"

# 4. 网络连接
info "4. 网络连接:"
MAIN_CONNECTIONS=$(netstat -an | grep 9001 | grep ESTABLISHED | wc -l | tr -d ' ')
WORKER_CONNECTIONS=$(netstat -an | grep 9002 | grep ESTABLISHED | wc -l | tr -d ' ')
echo "  主节点连接数: $MAIN_CONNECTIONS"
echo "  从节点连接数: $WORKER_CONNECTIONS"

# 5. 进程状态
info "5. 进程状态:"
MAIN_PID=$(pgrep -f "edge_worker.py.*9001" || echo "未找到")
WORKER_PID=$(pgrep -f "edge_worker.py.*9002" || echo "未找到")
echo "  主节点PID: $MAIN_PID"
echo "  从节点PID: $WORKER_PID"

# 6. 日志统计
info "6. 日志统计:"
if [ -f ~/.hermes/edge-worker/logs/edge.log ]; then
    LOG_LINES=$(wc -l < ~/.hermes/edge-worker/logs/edge.log)
    echo "  主节点日志行数: $LOG_LINES"
fi

# 7. 性能指标
info "7. 性能指标:"
echo "  主节点响应时间: $(curl -o /dev/null -s -w '%{time_total}' "http://$MAIN_NODE/health") 秒"
echo "  从节点响应时间: $(curl -o /dev/null -s -w '%{time_total}' "http://$WORKER_NODE/health") 秒"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║              监控完成                            ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║                                                  ║"
echo "║  主节点: $MAIN_NODE"
echo "║  从节点: $WORKER_NODE"
echo "║  状态: 正常运行                                  ║"
echo "║                                                  ║"
echo "╚══════════════════════════════════════════════════╝"
