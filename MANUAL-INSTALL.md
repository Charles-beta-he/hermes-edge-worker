# Hermes Edge Worker 手动安装指南

## 问题描述

如果遇到SSL证书错误：
```
curl: (60) SSL: no alternative certificate subject name matches target host name 'raw.githubusercontent.com'
```

请使用以下方法之一安装。

## 方法1：使用insecure版本安装脚本

```bash
curl -sSLk https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install-insecure.sh | bash
```

注意：`-k` 选项跳过SSL验证，仅在信任网络环境使用。

## 方法2：手动下载安装

### 步骤1：下载文件

在浏览器中访问以下URL，下载文件：

1. https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/edge_worker.py
2. https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/hermes_lan.py
3. https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/config.yaml

### 步骤2：创建目录

```bash
mkdir -p ~/.hermes/edge-worker/{logs,backups}
mkdir -p ~/.local/bin
```

### 步骤3：复制文件

将下载的文件复制到 `~/.hermes/edge-worker/` 目录。

### 步骤4：创建CLI包装器

创建文件 `~/.hermes/edge-worker/hermes-edge`：

```bash
cat > ~/.hermes/edge-worker/hermes-edge << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "$1" in
    start)
        if [ "$2" = "--daemon" ]; then
            nohup python3 "$SCRIPT_DIR/edge_worker.py" > "$SCRIPT_DIR/logs/worker.log" 2>&1 &
            echo $! > "$SCRIPT_DIR/worker.pid"
            echo "✓ 已启动（后台）"
        else
            python3 "$SCRIPT_DIR/edge_worker.py"
        fi
        ;;
    stop)
        if [ -f "$SCRIPT_DIR/worker.pid" ]; then
            kill $(cat "$SCRIPT_DIR/worker.pid") 2>/dev/null
            rm "$SCRIPT_DIR/worker.pid"
            echo "✓ 已停止"
        fi
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
        echo "用法: hermes-edge {start|stop|status|logs}"
        ;;
esac
EOF
chmod +x ~/.hermes/edge-worker/hermes-edge
```

### 步骤5：创建符号链接

```bash
ln -sf ~/.hermes/edge-worker/hermes-edge ~/.local/bin/hermes-edge
```

### 步骤6：验证安装

```bash
hermes-edge status
```

## 方法3：使用wget代替curl

```bash
wget -qO- https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install.sh | bash
```

或跳过SSL验证：
```bash
wget --no-check-certificate -qO- https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install.sh | bash
```

## 方法4：使用代理

如果网络环境需要代理：

```bash
export http_proxy=http://your-proxy:port
export https_proxy=http://your-proxy:port
curl -sSL https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install.sh | bash
```

## 方法5：使用gh CLI

如果安装了GitHub CLI：

```bash
gh api repos/Charles-beta-he/hermes-edge-worker/contents/install.sh --jq '.content' | base64 -d | bash
```

## 配置说明

安装后编辑配置文件：
```bash
nano ~/.hermes/edge-worker/config.yaml
```

修改以下内容：
```yaml
worker:
  name: "your-hostname"  # 修改为你的主机名
  port: 9001
  main_node: "http://192.168.31.71:9001"  # 主节点地址

security:
  token: "hermes-2024"  # 认证token
```

## 验证连接

```bash
# 测试本地
hermes-edge status

# 测试主节点
curl http://192.168.31.71:9001/health
```

## 常见问题

### Q: SSL错误怎么办？
A: 使用 `install-insecure.sh` 或手动下载安装。

### Q: 无法访问GitHub怎么办？
A: 使用代理或手动下载文件。

### Q: Python版本太低怎么办？
A: 升级到Python 3.8+。

---

**最后更新**: 2026-05-30
