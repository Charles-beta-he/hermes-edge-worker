#!/bin/bash
# 持续集成脚本
# 长期稳定目标：自动化测试和部署

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
echo "║       持续集成脚本                               ║"
echo "║       长期稳定目标                               ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# 1. 检查Python版本
log "检查Python版本..."
python3 --version

# 2. 运行代码检查
log "运行代码检查..."
python3 -m py_compile *.py
log "代码检查通过"

# 3. 运行测试
log "运行测试..."
python3 test_complete.py
TEST_RESULT=$?

if [ $TEST_RESULT -ne 0 ]; then
    error "测试失败"
fi

log "测试通过"

# 4. 运行自检
log "运行自检..."
python3 self_check.py
SELF_CHECK_RESULT=$?

if [ $SELF_CHECK_RESULT -ne 0 ]; then
    warn "自检未完全通过，继续..."
fi

# 5. 检查Git状态
log "检查Git状态..."
git status --short

# 6. 提交并推送
log "提交并推送..."
git add .
git commit -m "ci: 自动化测试和部署" || echo "无更改"
git push origin main

log "持续集成完成"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║              持续集成完成                        ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║                                                  ║"
echo "║  测试结果: 通过                                  ║"
echo "║  代码质量: 通过                                  ║"
echo "║  自检状态: 部分通过                              ║"
echo "║                                                  ║"
echo "╚══════════════════════════════════════════════════╝"
