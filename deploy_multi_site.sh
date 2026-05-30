#!/bin/bash
# 多站点管理架构部署脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo "╔══════════════════════════════════════════════════╗"
echo "║       多站点管理架构部署脚本                     ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# 1. 检查Python
log "检查Python..."
if ! command -v python3 &>/dev/null; then
    error "需要Python 3.8+"
fi
python3 --version

# 2. 检查依赖
log "检查依赖..."
python3 -c "import json, os, sys, threading, requests" || error "缺少依赖"

# 3. 创建配置目录
log "创建配置目录..."
mkdir -p ~/.hermes/state
mkdir -p ~/.hermes/logs

# 4. 启动多站点管理器API
log "启动多站点管理器API..."
cd ~/hermes-edge-worker

# 检查是否已经运行
if pgrep -f "multi_site_manager.py.*--api" > /dev/null; then
    warn "多站点管理器API已经在运行"
else
    # 后台启动
    nohup python3 multi_site_manager.py --api --port 9009 > ~/.hermes/logs/multi_site_manager.log 2>&1 &
    log "多站点管理器API已启动，端口: 9009"
fi

# 5. 验证服务
log "验证服务..."
sleep 2

# 检查多站点管理器API
if curl -s http://localhost:9009/health > /dev/null 2>&1; then
    log "多站点管理器API运行正常"
else
    warn "多站点管理器API可能未启动"
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║              部署完成！                          ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║                                                  ║"
echo "║  多站点管理器API: http://localhost:9009          ║"
echo "║                                                  ║"
echo "║  使用方式:                                       ║"
echo "║  1. 注册站点: curl -X POST http://localhost:9009/sites/register \\"
echo "║     -H 'Content-Type: application/json' \\"
echo "║     -d '{\"site_id\":\"site-001\",\"site_info\":{\"name\":\"MacBook-Pro-1\"}}'"
echo "║                                                  ║"
echo "║  2. 查看站点: curl http://localhost:9009/sites"
echo "║                                                  ║"
echo "║  3. 获取可用站点: curl http://localhost:9009/sites/available"
echo "║                                                  ║"
echo "║  4. 查看指标: curl http://localhost:9009/metrics"
echo "║                                                  ║"
echo "║  5. 启动从节点: python3 site_registrar.py \\"
echo "║     --brain-url http://192.168.31.71:9009 \\"
echo "║     --site-id site-002 \\"
echo "║     --site-name MacBook-Pro-2 \\"
echo "║     --site-ip 192.168.31.130 \\"
echo "║     --site-port 9002"
echo "║                                                  ║"
echo "╚══════════════════════════════════════════════════╝"
