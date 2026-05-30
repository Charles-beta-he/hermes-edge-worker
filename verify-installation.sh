#!/bin/bash
# Hermes Edge Worker 安装验证脚本

echo "╔══════════════════════════════════════════════════╗"
echo "║       Hermes Edge Worker 安装验证                ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}[✓]${NC} $1"; }
fail() { echo -e "${RED}[✗]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

ERRORS=0

# 1. 检查安装目录
echo "1. 检查安装目录..."
if [ -d "$HOME/.hermes/edge-worker" ]; then
    pass "安装目录存在"
else
    fail "安装目录不存在"
    ERRORS=$((ERRORS + 1))
fi

# 2. 检查核心文件
echo ""
echo "2. 检查核心文件..."
for file in edge_worker.py hermes_lan.py config.yaml hermes-edge version.txt; do
    if [ -f "$HOME/.hermes/edge-worker/$file" ]; then
        pass "$file 存在"
    else
        fail "$file 不存在"
        ERRORS=$((ERRORS + 1))
    fi
done

# 3. 检查CLI命令
echo ""
echo "3. 检查CLI命令..."
if command -v hermes-edge &>/dev/null; then
    pass "hermes-edge 命令可用"
    VERSION=$(hermes-edge status 2>/dev/null | grep -o "v[0-9.]*" || echo "未知")
    echo "   版本: $VERSION"
else
    fail "hermes-edge 命令不可用"
    ERRORS=$((ERRORS + 1))
fi

# 4. 检查配置文件
echo ""
echo "4. 检查配置文件..."
if [ -f "$HOME/.hermes/edge-worker/config.yaml" ]; then
    if grep -q "main_node.*192.168.31.71" "$HOME/.hermes/edge-worker/config.yaml"; then
        pass "主节点配置正确"
    else
        warn "主节点配置可能不正确"
        echo "   请检查: main_node: \"http://192.168.31.71:9001\""
    fi
    
    if grep -q "token.*hermes-2024" "$HOME/.hermes/edge-worker/config.yaml"; then
        pass "Token配置正确"
    else
        warn "Token配置可能不正确"
        echo "   请检查: token: \"hermes-2024\""
    fi
else
    fail "配置文件不存在"
    ERRORS=$((ERRORS + 1))
fi

# 5. 测试网络连接
echo ""
echo "5. 测试网络连接..."
if curl -s --connect-timeout 5 http://192.168.31.71:9001/health >/dev/null 2>&1; then
    pass "主节点连接正常"
    echo "   响应: $(curl -s http://192.168.31.71:9001/health)"
else
    fail "无法连接到主节点"
    ERRORS=$((ERRORS + 1))
fi

# 6. 检查端口占用
echo ""
echo "6. 检查端口占用..."
if lsof -i :9002 >/dev/null 2>&1; then
    warn "端口9002已被占用"
    echo "   占用进程: $(lsof -i :9002 | tail -1)"
else
    pass "端口9002可用"
fi

# 7. 检查Python版本
echo ""
echo "7. 检查Python版本..."
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "未安装")
if [ "$PYTHON_VERSION" != "未安装" ]; then
    pass "Python $PYTHON_VERSION"
else
    fail "Python未安装"
    ERRORS=$((ERRORS + 1))
fi

# 总结
echo ""
echo "══════════════════════════════════════════════════"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ 安装验证通过！${NC}"
    echo ""
    echo "下一步："
    echo "  1. 编辑配置: hermes-edge config"
    echo "  2. 启动服务: hermes-edge start --daemon"
    echo "  3. 查看状态: hermes-edge status"
else
    echo -e "${RED}✗ 发现 $ERRORS 个问题${NC}"
    echo ""
    echo "请修复上述问题后重新验证"
fi
echo "══════════════════════════════════════════════════"
