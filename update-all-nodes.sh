#!/bin/bash
# 节点自动更新脚本
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
echo "║       节点自动更新脚本                           ║"
echo "║       三模型优化版                               ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# 主节点信息
MAIN_NODE="192.168.31.71:9001"
MAIN_REPO="https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main"

# 从节点列表
NODES=(
    "192.168.31.130:9002"
    # 添加更多节点...
)

# 1. 更新主节点
info "1. 更新主节点..."
cd ~/hermes-edge-worker
git pull origin main
log "主节点代码已更新"

# 重启主节点服务
info "重启主节点服务..."
hermes-edge restart
log "主节点服务已重启"

# 2. 更新从节点
info "2. 更新从节点..."
for node in "${NODES[@]}"; do
    info "更新节点: $node"
    
    # 测试连接
    if curl -s --connect-timeout 5 "http://$node/health" >/dev/null 2>&1; then
        # 发送更新命令
        curl -s -X POST "http://$node/command" \
          -H "Content-Type: application/json" \
          -d '{"action":"run_command","params":{"command":"hermes-edge update"}}' || warn "更新命令发送失败"
        
        log "节点 $node 更新命令已发送"
    else
        warn "节点 $node 无法连接"
    fi
done

# 3. 验证更新
info "3. 验证更新..."
sleep 5

echo -e "\n=== 主节点状态 ==="
curl -s "http://$MAIN_NODE/health"

for node in "${NODES[@]}"; do
    echo -e "\n=== 节点 $node 状态 ==="
    curl -s "http://$node/health" || warn "无法获取状态"
done

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║              更新完成！                          ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║                                                  ║"
echo "║  主节点: $MAIN_NODE"
echo "║  从节点数: ${#NODES[@]}"
echo "║                                                  ║"
echo "╚══════════════════════════════════════════════════╝"
