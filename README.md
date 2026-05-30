# Hermes Edge Worker

## 一键安装

**只需一个命令，剩余全部自动完成：**

```bash
curl -sSLk https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install-auto.sh | bash
```

## 自动完成内容

✅ 自动下载所有文件  
✅ 自动生成配置（使用主机名）  
✅ 自动创建CLI工具  
✅ 自动启动服务  
✅ 自动注册到主节点  
✅ 自动验证连接  

**无需手动编辑配置，无需手动启动服务。**

## 安装后

### 查看状态
```bash
hermes-edge status
```

### 查看日志
```bash
hermes-edge logs
```

### 重启服务
```bash
hermes-edge restart
```

### 停止服务
```bash
hermes-edge stop
```

## 主节点信息

- **IP**: 192.168.31.71
- **端口**: 9001
- **Token**: hermes-2024

## 其他安装方式

### 标准安装（需要手动配置）
```bash
curl -sSL https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install-final.sh | bash
```

### SSL问题专用
```bash
curl -sSLk https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install-insecure.sh | bash
```

### 手动安装
参考 [MANUAL-INSTALL.md](MANUAL-INSTALL.md)

## 文件结构

```
~/.hermes/edge-worker/
├── edge_worker.py      # 主程序
├── hermes_lan.py       # 局域网发现
├── config.yaml         # 配置文件（自动生成）
├── hermes-edge         # CLI工具
├── worker.pid          # 进程ID
├── logs/               # 日志目录
│   └── edge.log
└── backups/            # 备份目录
```

## 更新日志

### v1.2.0 (2026-05-30)
- 添加一键安装脚本
- 完全自动化：下载 → 配置 → 启动 → 注册
- 无需用户手动操作

### v1.1.0 (2026-05-30)
- 添加兼容性和自动升级支持
- 自动备份现有文件
- 保留用户配置

### v1.0.0 (2026-05-30)
- 初始版本

## 许可证

MIT License

## 仓库

https://github.com/Charles-beta-he/hermes-edge-worker
