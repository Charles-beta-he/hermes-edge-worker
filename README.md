# Hermes Edge Worker

Hermes Edge Worker 是云端大脑连接局域网设备的边缘触手：安装到从节点电脑后，负责本机执行、局域网发现、心跳、自检和任务回执。

## 一键安装

默认安装命令不跳过 TLS 校验；如果证书链异常，安装脚本会解释原因并在交互终端提供一次性确认逃生口。

```bash
curl -sSL https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install-auto.sh -o install-auto.sh
bash install-auto.sh
```

如需指定主节点认证 token：

```bash
HERMES_EDGE_TOKEN='your-strong-token' bash install-auto.sh
```

## TLS / 代理证书异常

如果看到 GitHub TLS 证书校验失败，优先修复系统 CA、公司代理证书或切换可信网络。

临时测试可显式允许本次安装跳过下载校验：

```bash
HERMES_EDGE_ALLOW_INSECURE_SSL=1 bash install-auto.sh
```

红线：不要把跳过 TLS 校验的管道执行当作默认安装方式；非交互环境不会自动跳过 TLS 校验。

## 自动完成内容

✅ 下载 Edge Worker 文件
✅ 自动生成配置（使用主机名）
✅ 自动创建 CLI 工具
✅ 自动启动服务
✅ 自动注册到主节点
✅ 自动验证连接  

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

默认主节点地址在安装脚本中配置；生产/长期使用应通过环境变量或配置文件提供强 token，避免弱默认值。

## 其他安装方式

### 标准安装（需要手动配置）
```bash
curl -sSL https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install-final.sh -o install-final.sh
bash install-final.sh
```

### 手动安装
参考 [MANUAL-INSTALL.md](MANUAL-INSTALL.md)

### 验证安装
参考 [VERIFY-GUIDE.md](VERIFY-GUIDE.md)

## UX / 安全原则

- 安全默认：不静默跳过 TLS、不默认弱 token、不隐藏风险。
- 显式逃生口：危险路径只能由交互确认或显式环境变量触发。
- 可诊断：失败信息必须包含原因、风险、推荐修复和下一步。
- 可降级：设备可进入 degraded 状态，但高信任任务需要健康设备。

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

### v4.7.3 (2026-05-31)
- 将安装文档默认路径改为安全 TLS 校验。
- 保留交互式/显式环境变量逃生口，禁止静默 insecure 下载。
- 补充 UX / 安全原则。

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
