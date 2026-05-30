# Hermes Edge Worker

## 快速安装（推荐）

```bash
curl -sSLk https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install-final.sh | bash
```

**特性**：
- ✅ 自动检测SSL问题
- ✅ 正确处理符号链接
- ✅ 完整的CLI工具
- ✅ 友好的用户提示
- ✅ **兼容现有安装**
- ✅ **自动升级**
- ✅ **配置保留**

## 兼容性和升级

### 自动升级
- 运行安装脚本时自动检测现有安装
- 比较版本号，只在有新版本时升级
- 自动备份现有文件
- 保留用户配置

### 升级流程
```bash
# 检查当前版本
hermes-edge status

# 升级到最新版本
hermes-edge update

# 或重新运行安装脚本
curl -sSLk https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install-final.sh | bash
```

### 回滚功能
```bash
# 查看可用备份
hermes-edge rollback

# 选择备份版本回滚
```

### 配置保留
- 升级时自动备份配置文件
- 新配置保存为 `config.yaml.new`
- 用户可选择是否使用新配置

## 其他安装方式

### 标准安装（无SSL问题）
```bash
curl -sSL https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install.sh | bash
```

### SSL问题专用
```bash
curl -sSLk https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install-insecure.sh | bash
```

### 手动安装
参考 [MANUAL-INSTALL.md](MANUAL-INSTALL.md)

## 使用方法

### 基本命令

```bash
# 启动（前台）
hermes-edge start

# 启动（后台）
hermes-edge start --daemon

# 停止
hermes-edge stop

# 重启
hermes-edge restart

# 查看状态
hermes-edge status

# 查看日志
hermes-edge logs

# 编辑配置
hermes-edge config

# 更新
hermes-edge update

# 回滚
hermes-edge rollback

# 卸载
hermes-edge uninstall
```

### 配置说明

编辑配置文件：
```bash
hermes-edge config
```

主要配置项：
```yaml
worker:
  name: "your-hostname"  # 修改为你的主机名
  port: 9001
  main_node: "http://192.168.31.71:9001"  # 主节点地址

security:
  token: "hermes-2024"  # 认证token
```

## 主节点信息

- **IP**: 192.168.31.71
- **端口**: 9001
- **Token**: hermes-2024

## 验证安装

```bash
# 检查状态
hermes-edge status

# 测试主节点连接
curl http://192.168.31.71:9001/health
```

## 故障排除

### 问题1：SSL证书错误
使用 `install-final.sh`（自动检测并处理）。

### 问题2：命令找不到
检查 `~/.local/bin` 是否在PATH中：
```bash
echo $PATH | grep -q "$HOME/.local/bin" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

### 问题3：启动失败
查看日志：
```bash
hermes-edge logs
```

### 问题4：升级后配置丢失
配置文件已备份到 `~/.hermes/edge-worker/backups/` 目录。

## 文件结构

```
~/.hermes/edge-worker/
├── edge_worker.py      # 主程序
├── hermes_lan.py       # 局域网发现
├── config.yaml         # 配置文件
├── hermes-edge         # CLI工具
├── version.txt         # 版本号
├── worker.pid          # 进程ID（运行时）
├── logs/               # 日志目录
│   └── worker.log
└── backups/            # 备份目录
    └── backup-YYYYMMDDHHMMSS/
```

## 更新日志

### v1.1.0 (2026-05-30)
- 添加兼容性和自动升级支持
- 自动备份现有文件
- 保留用户配置
- 版本检查和升级
- 回滚功能

### v1.0.0 (2026-05-30)
- 初始版本
- 基本功能实现

## 许可证

MIT License

## 仓库

https://github.com/Charles-beta-he/hermes-edge-worker
