# Hermes Edge Worker 端口拓扑

本文件是当前仓库的端口 SSOT。旧文档中的端口如与本文件冲突，以本文件的“状态”字段区分：`verified` 是当前运行/链路检查已验证；`implemented` 是代码存在但当前未监听；`legacy-doc` 是历史方案口径。

## Verified 当前运行端口

| 端口 | 组件 | 文件 | 状态 | 健康/检查 | 说明 |
|---:|---|---|---|---|---|
| 9001 | Brain/API legacy runtime | 外部/旧 runtime | verified-listening | `lsof` | 当前有 Python 进程监听；不是本轮架构链路检查的核心 9007/9008/9009 三件套。 |
| 9007 | 事件驱动 API | `task_event_driven.py` | verified | `GET /health`, `GET /metrics`, `POST /event` | 事件触发自动认领/执行；已补 event_id/idempotency/retry/dead-letter/local event store。 |
| 9008 | 任务池事件集成 API | `task_pool_event_integration.py` | verified | `GET /health`, `GET /metrics`, `POST /event` | 将 taskpool 状态变化接入事件驱动链路。 |
| 9009 | 多站点管理 API | `multi_site_manager.py` | verified | `GET /health`, `/sites`, `/sites/available` | 站点注册、心跳、健康、负载、故障转移。 |

验证命令：

```bash
lsof -nP -iTCP:9000-9010 -sTCP:LISTEN
/usr/bin/python3 architecture_link_check.py
```

## Implemented 代码实现端口

| 默认端口 | 组件 | 文件 | 状态 | 说明 |
|---:|---|---|---|---|
| 9000 | 统一接口网关 | `unified_gateway.py`, `unified_interface_layer.py`, `hermes_lan.py` | implemented/planned | 统一入口历史口径；当前核心链路未验证监听。 |
| 9002 | Edge Worker | `edge_worker.py` | implemented | 执行面；默认从 `config.yaml` 读取 9002；P0 已加 token/allowlist/sandbox/timeout。 |
| 9003 | Unified API | `unified_api.py` | implemented | 统一任务池 API 历史实现。生产任务状态仍以 Brain/taskpool SSOT 为准。 |
| 9004 | Knowledge API | `knowledge_api.py` | implemented | 知识管理 API。 |
| 9005 | RAG API | `rag_api.py` | implemented | RAG 知识搜索 API。 |
| 9006 | Monitoring/Feedback | `feedback_system.py` / 历史文档 | implemented/legacy-doc | 监控/反馈相关历史口径。 |
| 9007 | Event Driven API | `task_event_driven.py` | verified | 当前事件驱动核心。 |
| 9008 | Task Pool Event Integration API | `task_pool_event_integration.py` | verified | 当前 taskpool 事件集成核心。 |
| 9009 | Multi-Site Manager API | `multi_site_manager.py` | verified | 当前多站点管理核心。 |

## 局域网节点口径

| 地址 | 角色 | 状态 | 说明 |
|---|---|---|---|
| `192.168.31.71` | 主节点/Brain | legacy-doc/current-memory | 历史文档与当前记忆均指向主节点。实际运行以 live health check 为准。 |
| `192.168.31.130` | Edge Worker 节点 | legacy-doc/current-memory | 历史文档和 memory 中存在双节点 71/130 口径。 |
| `192.168.31.131/132` | 扩展示例节点 | legacy-doc | `load_balancer.py` 示例节点。 |

## 端口治理规则

1. 新增监听端口必须先更新本文件，再更新架构文档。
2. `architecture_link_check.py` 只验证当前主链路：9007/9008/9009。
3. 9000-9006 目前按 implemented/legacy 分层，不等同于当前生产运行链路。
4. Edge Worker 对外暴露前必须启用 token、allowed_commands、allowed_paths、max_timeout。
5. 不允许同一端口同时被多个生产组件声明为 verified；若冲突，先改本文件并补链路检查。
