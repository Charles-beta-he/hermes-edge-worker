# Hermes Edge Worker

## 安装

```bash
# 从GitHub安装
curl -sSL https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install.sh | bash
```

## 使用

```bash
# 启动
hermes-edge start

# 后台启动
hermes-edge start --daemon

# 查看状态
hermes-edge status

# 查看日志
hermes-edge logs
```

## 配置

编辑 `~/.hermes/edge-worker/config.yaml`

## 更新

```bash
# 重新运行安装脚本
curl -sSL https://raw.githubusercontent.com/Charles-beta-he/hermes-edge-worker/main/install.sh | bash
```

## 主节点信息

- **IP**: 192.168.31.71
- **端口**: 9001
- **Token**: hermes-2024

## 从节点部署

在其他电脑上运行安装脚本即可自动连接主节点。
