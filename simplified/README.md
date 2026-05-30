# simplified/ 治理说明

`simplified/` 是 reference implementation / architectural specimen，不是生产主线。

## 定位

保留目的：

1. 展示统一数据层、事件总线、接口层、RAG、网关的最小形态。
2. 为架构文档、教学、对比测试提供可读参考。
3. 作为 refactor/spike 的输入，而不是直接替代根目录生产组件。

## 禁止事项

- 禁止将 `simplified/edge_worker.py` 作为生产 Edge Worker 启动入口。
- 禁止将 `simplified/core_features.py` 的 TaskPool 作为生产任务 SSOT。
- 禁止在 simplified/ 内修功能后声称生产主链路已修复。
- 禁止让 simplified/ 与根目录实现各自演进同一生产职责。

## 生产主线对应关系

| simplified reference | 生产/主线对应 | 说明 |
|---|---|---|
| `simplified/core_features.py::TaskPool` | Brain/taskpool SSOT + `unified_task_pool.py` adapter | simplified 仅用于参考/测试。 |
| `simplified/edge_worker.py` | `edge_worker.py` | 生产入口必须使用根目录 P0 安全边界实现。 |
| `simplified/unified_event_bus.py` | `unified_event_bus.py` + `task_event_driven.py` | 事件可靠性以根目录实现为准。 |
| `simplified/simplified_api.py` | `unified_api.py` / Brain API | reference API，不是生命周期事实源。 |
| `simplified/simplified_gateway.py` | `unified_gateway.py` / `unified_interface_layer.py` | reference gateway。 |

## 变更规则

1. 如果需求影响生产行为，优先修改根目录主线组件。
2. 如果只是在 simplified/ 中改 reference，提交信息必须包含 `reference` 或 `simplified`，不能写成生产能力已上线。
3. 主线安全边界必须有测试；simplified/ 不作为安全验证依据。
4. 若未来决定合并 simplified/，必须先写迁移计划并逐项替换根目录入口。
