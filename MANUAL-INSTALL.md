# Hermes Edge Worker 手动安装指南

## 适用场景

当一键安装失败、网络环境受限、公司代理/自签 CA 导致 TLS 校验失败，或需要逐步排查时，使用本指南。

## 推荐方法：下载脚本后执行

```bash
curl -sSL https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install.sh -o install.sh
bash install.sh
```

如果需要自动生成配置并启动服务：

```bash
curl -sSL https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install-auto.sh -o install-auto.sh
bash install-auto.sh
```

## TLS 证书错误处理

如果遇到类似错误：

```text
curl: (60) SSL certificate problem
```

优先处理：
1. 修复系统 CA 证书。
2. 导入公司代理/自签 CA。
3. 切换可信网络。
4. 使用浏览器从 GitHub 下载脚本后本地执行。

仅临时测试、且你理解下载内容可能被篡改的风险时，允许对已下载脚本显式打开逃生口：

```bash
HERMES_EDGE_ALLOW_INSECURE_SSL=1 bash install.sh
```

不要把跳过 TLS 校验的管道执行作为默认安装路径。

## 手动下载安装

### 步骤1：下载文件

在浏览器中访问以下 URL，下载文件：

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

### 步骤4：创建 CLI 包装器

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
            echo "已启动（后台）"
        else
            python3 "$SCRIPT_DIR/edge_worker.py"
        fi
        ;;
    stop)
        if [ -f "$SCRIPT_DIR/worker.pid" ]; then
            kill $(cat "$SCRIPT_DIR/worker.pid") 2>/dev/null
            rm "$SCRIPT_DIR/worker.pid"
            echo "已停止"
        fi
        ;;
    status)
        if [ -f "$SCRIPT_DIR/worker.pid" ] && kill -0 $(cat "$SCRIPT_DIR/worker.pid") 2>/dev/null; then
            PID=$(cat "$SCRIPT_DIR/worker.pid")
            echo "运行中 PID: $PID"
        else
            echo "未运行"
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

## 使用代理

```bash
export http_proxy=http://your-proxy:port
export https_proxy=http://your-proxy:port
curl -sSL https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install.sh -o install.sh
bash install.sh
```

## 使用 gh CLI

如果安装了 GitHub CLI：

```bash
gh api repos/Charles-beta-he/hermes-edge-worker/contents/install.sh --jq '.content' | base64 -d > install.sh
bash install.sh
```

## 配置说明

安装后编辑配置文件：

```bash
nano ~/.hermes/edge-worker/config.yaml
```

生产/长期使用时，`security.token` 应为强随机值；推荐通过 `HERMES_EDGE_TOKEN` 注入或手动写入配置。

## 故障排查

### Python 版本

```bash
python3 --version
```

### 主节点连通

```bash
curl http://192.168.31.71:9001/health
```

### 日志

```bash
hermes-edge logs
```
