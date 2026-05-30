# Edge Worker 安装验证指南

## 快速验证（在从节点电脑上运行）

### 方式1：运行验证脚本
```bash
curl -sSLk https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/verify-installation.sh | bash
```

### 方式2：手动验证

#### 1. 检查CLI命令
```bash
hermes-edge status
```

预期输出：
```
Hermes Edge Worker v1.1.0

✗ 未运行
```

#### 2. 检查配置文件
```bash
cat ~/.hermes/edge-worker/config.yaml
```

应该包含：
```yaml
worker:
  name: "your-hostname"
  port: 9001
  main_node: "http://192.168.31.71:9001"

security:
  token: "hermes-2024"
```

#### 3. 测试主节点连接
```bash
curl http://192.168.31.71:9001/health
```

预期输出：
```json
{"status":"ok","worker":"charlesdeMacBook-Pro","timestamp":"..."}
```

#### 4. 启动服务
```bash
hermes-edge start --daemon
```

#### 5. 再次检查状态
```bash
hermes-edge status
```

预期输出：
```
Hermes Edge Worker v1.1.0

✓ 运行中 (PID: xxxxx)
  启动时间: ...
  日志: ~/.hermes/edge-worker/logs/worker.log
```

## 常见问题

### 问题1：无法连接主节点
**症状**：`curl http://192.168.31.71:9001/health` 失败

**解决方案**：
1. 检查网络连接：`ping 192.168.31.71`
2. 检查防火墙设置
3. 确认主节点正在运行

### 问题2：CLI命令不可用
**症状**：`hermes-edge: command not found`

**解决方案**：
```bash
# 检查PATH
echo $PATH | grep -q "$HOME/.local/bin" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 问题3：配置文件错误
**症状**：启动失败

**解决方案**：
```bash
# 编辑配置
hermes-edge config

# 确保以下配置正确：
# main_node: "http://192.168.31.71:9001"
# token: "hermes-2024"
```

### 问题4：端口占用
**症状**：`OSError: [Errno 48] Address already in use`

**解决方案**：
```bash
# 检查端口占用
lsof -i :9002

# 修改配置使用其他端口
hermes-edge config
# 将 port: 9001 改为 port: 9003
```

## 验证检查清单

- [ ] CLI命令 `hermes-edge` 可用
- [ ] 配置文件存在且正确
- [ ] 主节点连接正常
- [ ] 端口未被占用
- [ ] 服务可以启动
- [ ] 服务可以停止

## 下一步

验证完成后：

1. **启动服务**：
   ```bash
   hermes-edge start --daemon
   ```

2. **查看日志**：
   ```bash
   hermes-edge logs
   ```

3. **测试执行命令**：
   ```bash
   curl -X POST http://localhost:9002/command \
     -H "Content-Type: application/json" \
     -d '{"action":"run_command","params":{"command":"whoami"}}'
   ```

4. **从主节点测试**：
   ```bash
   curl -X POST http://192.168.31.71:9001/edge/execute \
     -H "Content-Type: application/json" \
     -d '{"worker":"your-hostname","action":"run_command","params":{"command":"hostname"}}'
   ```

---

**主节点信息**：
- IP: 192.168.31.71
- 端口: 9001
- Token: hermes-2024

**仓库**：https://github.com/Charles-beta-he/hermes-edge-worker
