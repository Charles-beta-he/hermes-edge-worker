#!/bin/bash
# 任务池事件驱动部署脚本

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
echo "║       任务池事件驱动部署脚本                     ║"
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
python3 -c "import json, os, sys, subprocess" || error "缺少依赖"

# 3. 创建配置目录
log "创建配置目录..."
mkdir -p ~/.hermes/state
mkdir -p ~/.hermes/logs

# 4. 创建策略文件
log "创建策略文件..."
cat > ~/.hermes/state/auto_run_policy.json << 'EOF'
{
  "enabled": true,
  "allowed_tasks": [],
  "allowed_profiles": ["default"],
  "allowed_commands": ["noop", "py_compile_taskpool"],
  "allowed_workspaces": ["/Users/charles/hermes-edge-worker"]
}
EOF

# 5. 启动事件驱动API
log "启动事件驱动API..."
cd ~/hermes-edge-worker

# 检查是否已经运行
if pgrep -f "task_event_driven.py.*--api" > /dev/null; then
    warn "事件驱动API已经在运行"
else
    # 后台启动
    nohup python3 task_event_driven.py --api --port 9007 > ~/.hermes/logs/task_event_driven.log 2>&1 &
    log "事件驱动API已启动，端口: 9007"
fi

# 6. 启动任务池事件集成API
log "启动任务池事件集成API..."
if pgrep -f "task_pool_event_integration.py.*--api" > /dev/null; then
    warn "任务池事件集成API已经在运行"
else
    # 后台启动
    nohup python3 task_pool_event_integration.py --api --port 9008 > ~/.hermes/logs/task_pool_event_integration.log 2>&1 &
    log "任务池事件集成API已启动，端口: 9008"
fi

# 7. 验证服务
log "验证服务..."
sleep 2

# 检查事件驱动API
if curl -s http://localhost:9007/health > /dev/null 2>&1; then
    log "事件驱动API运行正常"
else
    warn "事件驱动API可能未启动"
fi

# 检查任务池事件集成API
if curl -s http://localhost:9008/health > /dev/null 2>&1; then
    log "任务池事件集成API运行正常"
else
    warn "任务池事件集成API可能未启动"
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║              部署完成！                          ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║                                                  ║"
echo "║  事件驱动API: http://localhost:9007              ║"
echo "║  任务池事件集成API: http://localhost:9008        ║"
echo "║                                                  ║"
echo "║  使用方式:                                       ║"
echo "║  1. 发送事件: curl -X POST http://localhost:9008/event \\"
echo "║     -H 'Content-Type: application/json' \\"
echo "║     -d '{\"event_type\":\"task.created\",\"event_data\":{\"task_id\":\"task-001\",\"priority\":\"P1\"}}'"
echo "║                                                  ║"
echo "║  2. 查看指标: curl http://localhost:9008/metrics"
echo "║                                                  ║"
echo "║  3. 查看日志: tail -f ~/.hermes/logs/task_event_driven.log"
echo "║                                                  ║"
echo "╚══════════════════════════════════════════════════╝"
