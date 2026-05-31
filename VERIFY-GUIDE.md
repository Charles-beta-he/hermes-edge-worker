# Edge Worker 安装验证指南

## 快速验证（在从节点电脑上运行）

### 方式1：下载并运行验证脚本

默认验证脚本不跳过 TLS 校验：

```bash
curl -sSL https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/verify-installation.sh -o verify-installation.sh
bash verify-installation.sh
```

如果 TLS 证书校验失败，请优先修复系统 CA、公司代理证书或切换可信网络；不要把跳过 TLS 校验的管道执行当作默认验证路径。

### 方式2：手动验证

#### 1. 检查 CLI 命令
```bash
hermes-edge status
```

预期输出包含运行状态，例如：
```text
运行中 PID: xxxxx
```
或：
```text
未运行
```

#### 2. 检查配置文件
```bash
cat ~/.hermes/edge-worker/config.yaml
```

应该包含 worker/main_node/security 等配置。生产或长期使用时，token 应通过 `HERMES_EDGE_TOKEN` 或配置文件设置为强随机值，不应使用弱默认值。

#### 3. 测试主节点连接
```bash
curl http://192.168.31.71:9001/health
```

#### 4. 启动服务
```bash
hermes-edge start --daemon
```

#### 5. 再次检查状态
```bash
hermes-edge status
```

## 常见问题

### 问题1：无法连接主节点
症状：`curl http://192.168.31.71:9001/health` 失败

解决方案：
1. 检查网络连接：`ping 192.168.31.71`
2. 检查防火墙设置
3. 确认主节点正在运行
4. 确认 worker 配置中的 main_node 地址正确

### 问题2：CLI 命令不可用
症状：`hermes-edge: command not found`

解决方案：
1. 确认 `~/.local/bin` 在 PATH 中
2. 直接运行 `~/.local/bin/hermes-edge status`
3. 重新建立软链接：
   ```bash
   ln -sf ~/.hermes/edge-worker/hermes-edge ~/.local/bin/hermes-edge
   ```

### 问题3：TLS 证书校验失败
症状：GitHub raw 下载报证书错误

推荐：
1. 修复系统 CA
2. 导入公司代理 CA
3. 切换可信网络
4. 已下载脚本且仅临时测试时，显式使用：
   ```bash
   HERMES_EDGE_ALLOW_INSECURE_SSL=1 bash install.sh
   ```

红线：非交互自动化环境不应自动跳过 TLS 校验。
