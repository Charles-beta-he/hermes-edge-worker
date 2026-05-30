#!/bin/bash
# 简化架构部署脚本

set -e

echo "=== 部署简化架构 ==="

# 1. 检查Python
if ! command -v python3 &>/dev/null; then
    echo "需要Python 3.8+"
    exit 1
fi

# 2. 安装依赖
echo "安装依赖..."
pip3 install scikit-learn --quiet

# 3. 启动服务
echo "启动服务..."
python3 simplified_gateway.py --host 0.0.0.0 --port 9000

echo "部署完成"
