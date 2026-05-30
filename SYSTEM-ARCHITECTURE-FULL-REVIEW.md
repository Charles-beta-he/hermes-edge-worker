# Hermes Edge Worker 系统架构全盘梳理

## 0. 证据来源与当前状态

本报告基于当前仓库 `/Users/charles/hermes-edge-worker` 的代码、架构文档、自检报告和运行链路检查，不从历史记忆直接下结论。

已读取/验证的关键证据：

- 项目 profile: `/Users/charles/.hermes/project-profiles/hermes.json`
- README: `README.md`
- 架构文档：
  - `UNIFIED-ARCHITECTURE-FULL.md`
  - `UNIFIED-TASK-POOL-ARCHITECTURE.md`
  - `TASK-POOL-EVENT-DRIVEN-ARCHITECTURE.md`
  - `MULTI-SITE-MANAGEMENT-ARCHITECTURE.md`
  - `BOUNDARY-COVERAGE-REPORT.md`
- 自检：`python3 self_check.py`
  - overall_status: PASS
  - boundary_coverage: 100.0%
  - file-level test mapping coverage: 100.0%
- 全量测试：`/usr/bin/python3 -m pytest test_*.py -q`
  - 167 passed, 12 warnings
- 架构链路：`/usr/bin/python3 architecture_link_check.py`
  - components: 5/5 OK
  - API endpoints: 3/3 OK
  - link tests: 4/4 OK
- 当前本地监听端口：
  - 9007: task_event_driven API
  - 9008: task_pool_event_integration API
  - 9009: multi_site_manager API

当前 git 注意事项：

- 工作区已有非本次报告相关脏文件：`install.sh`、若干运行报告 JSON、`install-auto.sh.backup`。
- 本报告是新增文档，不包含提交动作。

---

## 1. 一句话架构定位

`hermes-edge-worker` 是 Hermes 本地大脑/任务池的“局域网执行触手 + 分布式站点管理 + 事件驱动触发 + 验证自检”仓库。

它的正确长期定位不是再造一个独立任务池，而是：

> 本地大脑/brain_task_orchestrator.py 作为决策和状态 SSOT；edge-worker 只做执行、站点注册、心跳、能力暴露、结果回传；事件驱动层把任务状态变化转成自动认领/自动执行触发；多站点层负责局域网节点发现、健康、负载均衡和故障转移。

---

## 2. 系统总览图

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         Hermes Local Brain                           │
│  ~/.hermes/scripts/brain_task_orchestrator.py                         │
│  ~/.hermes/scripts/brain_task_dispatch_tick.py                        │
│  kanban.db / Markdown task notes / proof gates                        │
│                                                                       │
│  职责：任务创建、状态机、证据门、调度策略、生命周期收口              │
└───────────────────────────────▲─────────────────────────────────────┘
                                │ subprocess / REST / event trigger
                                │
┌───────────────────────────────┴─────────────────────────────────────┐
│                      Event-driven Integration                         │
│                                                                       │
│  task_event_driven.py              :9007                              │
│  - 接收 task.created/status_changed/dependency_met/priority_changed    │
│  - 根据事件触发 auto_claim / auto_execute                             │
│                                                                       │
│  task_pool_event_integration.py     :9008                              │
│  - 调用 brain_task_orchestrator.py claim / autorun-runner              │
│  - 把任务池状态变化接入自动化链路                                      │
└───────────────────────────────▲─────────────────────────────────────┘
                                │
                                │ site selection / worker registry
                                │
┌───────────────────────────────┴─────────────────────────────────────┐
│                       Multi-site Control Plane                        │
│                                                                       │
│  multi_site_manager.py             :9009                              │
│  - /sites/register                                                     │
│  - /sites/heartbeat                                                    │
│  - /sites /sites/available                                             │
│  - LoadBalancer / FailoverManager                                      │
│                                                                       │
│  site_registrar.py                                                     │
│  - 从节点注册到主节点                                                  │
│  - 周期心跳                                                            │
│  - 系统指标上报                                                        │
└───────────────────────────────▲─────────────────────────────────────┘
                                │
                                │ HTTP / LAN
                                │
┌───────────────────────────────┴─────────────────────────────────────┐
│                         Edge Execution Layer                          │
│                                                                       │
│  edge_worker.py                    default :9000 / install :9002       │
│  - POST /execute                                                       │
│  - POST /command                                                       │
│  - GET  /health                                                        │
│  - GET  /info                                                          │
│  - capabilities: run_command/read_file/write_file/list_dir             │
│                                                                       │
│  edge_worker_executor.py                                               │
│  - 从 Brain API 拉任务                                                 │
│  - 执行 code_generation/code_review/testing/documentation              │
│  - 回传 /tasks/<id>/result                                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. 分层架构

### 3.1 决策层：本地大脑 / 任务池 SSOT

仓库内的 `unified_task_pool.py` 明确写了“本地大脑作为唯一事实源”。它本身是适配器，而不是最终任务事实源。

关键职责：

- task id、任务状态、优先级和生命周期由本地大脑掌握。
- edge-worker 不应该自己决定任务生命周期最终状态。
- 自动执行必须经过 brain_task_orchestrator 的 claim / autorun / proof gates。

当前代码落点：

- `unified_task_pool.py`
  - `UnifiedTaskPool.add_task()`：如果传入 brain_orchestrator，则调用 `create_task()`。
  - `UnifiedTaskPool.get_task()`：优先从 brain_orchestrator 获取。
  - `UnifiedTaskPool.update_task_status()`：优先更新 brain_orchestrator。
- `task_pool_event_integration.py`
  - 通过 subprocess 调用 `~/.hermes/scripts/brain_task_orchestrator.py claim <task_id> --json`
  - 通过 subprocess 调用 `brain_task_orchestrator.py autorun-runner --task <task_id> --json`

结论：

- 正确方向已经在代码中体现。
- 仍存在仓库内早期 `task_pool.py` / `UnifiedTaskPool` 的内存任务池模型，需继续维持“适配器/测试夹具/示例”身份，不能变成第二事实源。

### 3.2 事件触发层

目标是替代定时轮询，把任务状态变化转成即时触发。

核心组件：

- `task_event_driven.py`
  - `TaskEventDriven.handle_event()`
  - 支持事件：
    - `task.created`
    - `task.status_changed`
    - `task.dependency_met`
    - `task.priority_changed`
    - `task.assigned`
  - API：`/event` `/metrics` `/health`
  - 默认端口：9007

- `task_pool_event_integration.py`
  - `TaskPoolEventIntegration.process_task_event()`
  - 对 P0/P1 创建事件立即 auto_claim。
  - pending -> auto_claim。
  - claimed -> auto_execute。
  - API：`/event` `/metrics` `/health`
  - 默认端口：9008

事件链路：

```text
task.created / task.status_changed / dependency_met
        ↓
TaskEventDriven / TaskPoolEventIntegration
        ↓
brain_task_orchestrator.py claim
        ↓
brain_task_orchestrator.py autorun-runner
        ↓
proof/lifecycle gates
        ↓
review/done or blocked/retry
```

当前验证：

- `architecture_link_check.py` 验证 9007/9008 端点可用。
- `architecture_link_check_report.json` 显示 task_event link OK。

架构判断：

- 事件驱动方向符合用户偏好和长期目标。
- 目前事件层仍是 HTTP + subprocess 触发，可靠消息队列、幂等键、重放、死信队列尚未成为强约束。

### 3.3 多站点管理层

核心组件：

- `multi_site_manager.py`
  - `MultiSiteManager`
    - register_site
    - unregister_site
    - heartbeat
    - health check
    - get_available_site
    - update_site_metrics
  - `LoadBalancer`
    - round_robin
    - weighted
    - least_connections
    - performance
  - `FailoverManager`
    - handle_failure
    - reassign_task
  - API：
    - `POST /sites/register`
    - `POST /sites/heartbeat`
    - `GET /sites`
    - `GET /sites/available`
    - `GET /metrics`
    - `GET /health`
  - 默认端口：9009

- `site_registrar.py`
  - `SiteRegistrar.register()`
  - `SiteRegistrar.start_heartbeat()`
  - `_get_system_metrics()`
  - `EdgeWorkerWithMultiSite`

站点链路：

```text
Edge Node / site_registrar.py
        ↓ register
multi_site_manager.py :9009
        ↓ heartbeat / metrics
站点状态 online/offline
        ↓
LoadBalancer.get_available_site()
        ↓
Edge Worker execution endpoint
```

当前验证：

- `architecture_link_check_report.json`
  - multi_site_manager.py OK
  - site_registrar.py OK
  - site registration link OK
  - site heartbeat link OK
  - load balancing link OK
- 当前监听：9009 正在监听。
- 当前报告中 `test-site-001` 初始状态 offline，但链路测试执行心跳后 load_balancing 返回该站点。这说明测试会临时修复心跳状态，但持久站点数据里有测试残留。

架构判断：

- 多站点管理骨架完整。
- 真正生产级还需要：租约过期语义、幂等注册、站点能力标签、真实任务重分配、故障隔离和安全认证。

### 3.4 执行层：Edge Worker

核心组件：

- `edge_worker.py`
  - `GET /health`
  - `GET /info`
  - `POST /execute`
  - `POST /command`
  - action:
    - `run_command`
    - `read_file`
    - `write_file`
    - `list_dir`
  - `register_with_brain()` -> `/edge/register`
  - `heartbeat_loop()` -> `/edge/heartbeat`

- `edge_worker_executor.py`
  - 从 Brain API 获取任务：`GET /tasks/<task_id>`
  - 执行模拟任务类型：
    - code_generation
    - code_review
    - testing
    - documentation
  - 回传结果：`POST /tasks/<task_id>/result`

执行链路：

```text
Brain / Unified API
        ↓ assign task
EdgeWorkerExecutor.fetch_task()
        ↓
_execute(task)
        ↓
_report_result()
        ↓
Brain task state/proof lifecycle
```

安全边界：

- `edge_worker.py` 当前允许 shell command，并且 `write_file` 可写任意 expanduser 路径。
- `config.yaml` 有 `allowed_commands` / `max_timeout` 设计，但 `edge_worker.py` 当前未强制读取该 allowlist。
- 这是执行层最大的生产风险。

### 3.5 数据/事件/接口/知识支撑层

这些组件构成“统一架构”支撑面：

- `unified_data_layer.py`
  - `UnifiedStorage`: JSON/pickle 持久化
  - `UnifiedCache`: TTL cache
  - `UnifiedDataLayer`: storage + cache facade

- `unified_event_bus.py`
  - `Event`
  - `EventHandler`
  - `EventStore`
  - `UnifiedEventBus`
  - Task/Knowledge/Experience publishers/subscribers

- `unified_interface_layer.py`
  - Interface registry/gateway
  - TaskInterface / KnowledgeInterface / ExperienceInterface

- `unified_gateway.py`
  - 聚合任务、知识、经验接口
  - API：
    - `/health`
    - `/status`
    - `/tasks`
    - `/tasks/execute`
    - `/knowledge`, `/knowledge/search`
    - `/experience`, `/experience/search`, `/experience/validate`
    - `/search`
    - `/metrics`

- `knowledge_manager.py`
  - 结构化经验、函数、工作流、决策知识管理

- `rag_knowledge_manager.py`
  - 中文 tokenizer + TF-IDF + cosine similarity
  - add/search/delete/save/load

- `knowledge_api.py`, `rag_api.py`
  - 分别包装知识系统和 RAG 系统 HTTP API

架构判断：

- 支撑组件比较完整，但存在“多个 gateway/API 同时存在”的历史演进痕迹。
- 当前需要明确推荐入口，否则调用方容易不知道应该走 `unified_gateway.py`、`unified_api.py`、`knowledge_api.py`、`rag_api.py` 还是 simplified gateway。

### 3.6 简化架构 / 历史折叠层

`simplified/` 目录包含折叠版核心：

- `simplified/core_features.py`
  - AgentTeam
  - FaultToleranceManager
  - LoadBalancer
  - TaskPool
  - TaskScheduler
  - MultiModelAnalyzer
- `simplified/simplified_api.py`
- `simplified/simplified_gateway.py`
- simplified copies of edge worker / data layer / event bus / knowledge / rag

用途判断：

- 当前更像参考/迁移产物或轻量运行版本。
- 不能让 simplified 目录和根目录实现长期双写漂移。
- 如果保留，建议定义为“reference compact build”；如果不用，应冻结或合并回主线。

### 3.7 自检与治理层

核心组件：

- `self_check.py`
  - test_coverage
  - code_quality
  - component_integration
  - documentation
  - deployment
  - tests
  - performance
  - security
  - stress
  - compatibility
  - architecture_links

- `architecture_self_check.py`
  - 更偏统一架构内部一致性检查。

- `architecture_link_check.py`
  - 真实检查 9007/9008/9009 和任务/站点/负载链路。

- `ci_automation.py`
  - 代码质量、测试、集成、性能报告。

当前验证状态：

- self_check PASS。
- pytest 167 passed。
- architecture_link_check PASS。

架构判断：

- 自检已从“文件存在/测试文件数量”推进到边界目录。
- 但 security 当前对 hardcoded token / curl|bash 是 warning，不是 fail-closed。是否升级为 fail-closed 需要结合安装体验和局域网安全模型决定。

---

## 4. 核心运行链路

### 4.1 局域网自动发现 / 连接链路

```text
hermes_lan.py start_brain
        ↓
BrainBroadcaster UDP broadcast
        ↓
hermes_lan.py start_edge / discover
        ↓
BrainDiscovery UDP/TCP probe
        ↓
edge_worker.py --brain-url <brain>
        ↓
register_with_brain / heartbeat_loop
```

关键文件：

- `hermes_lan.py`
- `edge_worker.py`
- install scripts

### 4.2 任务创建到自动执行链路

```text
Task created in Local Brain
        ↓ event: task.created
POST /event :9007 or :9008
        ↓
TaskPoolEventIntegration.process_task_event()
        ↓ P0/P1 immediate claim
brain_task_orchestrator.py claim <task_id> --json
        ↓
brain_task_orchestrator.py autorun-runner --task <task_id> --json
        ↓
Edge execution or local runner
        ↓
proof/lifecycle gates
```

### 4.3 多站点注册到负载选择链路

```text
site_registrar.py
        ↓ POST /sites/register
multi_site_manager.py
        ↓ POST /sites/heartbeat
site status online/offline
        ↓ GET /sites/available
LoadBalancer.select()
        ↓
selected site for execution
```

### 4.4 Edge command execution链路

```text
POST /command
  { action: run_command/read_file/write_file/list_dir, params: ... }
        ↓
EdgeWorkerHandler._execute_command()
        ↓
_run_command / _read_file / _write_file / _list_dir
        ↓
JSON result
```

### 4.5 知识/RAG链路

```text
Knowledge API / Unified Gateway
        ↓
KnowledgeManager.record_* / search_*
        ↓
UnifiedDataLayer optional persistence
        ↓
RAGKnowledgeManager.add_knowledge/search
        ↓
TF-IDF vector index + cosine similarity
```

---

## 5. 端口与服务边界

当前文档和代码涉及的主要端口：

| 端口 | 组件 | 证据 | 当前状态 |
|---:|---|---|---|
| 9000 | edge_worker.py 默认端口 / unified gateway docs | edge_worker.py, UNIFIED docs | 未在本次监听检查中确认 |
| 9001 | 主节点 Brain / install config | README, install scripts, config | 文档配置口径 |
| 9002 | 从节点 Edge Worker 安装端口 | install-auto.sh, docs | 文档配置口径 |
| 9003 | unified_api.py | UNIFIED-TASK-POOL-ARCHITECTURE.md | 文档配置口径 |
| 9004 | knowledge API | KNOWLEDGE-MANAGEMENT-ARCHITECTURE.md | 文档配置口径 |
| 9005 | RAG API | RAG-KNOWLEDGE-MANAGEMENT-ARCHITECTURE.md | 文档配置口径 |
| 9007 | task_event_driven.py | architecture_link_check | 当前监听 OK |
| 9008 | task_pool_event_integration.py | architecture_link_check | 当前监听 OK |
| 9009 | multi_site_manager.py | architecture_link_check | 当前监听 OK |

端口风险：

- 文档中 9000/9001/9002/9003/9004/9005/9007/9008/9009 并存，需形成一份唯一端口注册表。
- README 的主节点端口为 9001，但多站点管理文档主节点为 9009，任务池事件集成为 9008。建议拆成“Brain API / Edge Worker / Site Manager / Event Trigger / Unified API”五类明确语义。

---

## 6. 模块清单与职责

### P0 主链路模块

| 模块 | 职责 | 状态 |
|---|---|---|
| `edge_worker.py` | 局域网执行代理，HTTP command/task endpoint | 可运行，需加强安全边界 |
| `site_registrar.py` | 从节点注册、心跳、指标上报 | 已实现 |
| `multi_site_manager.py` | 站点注册、健康、负载均衡、故障转移 | 已实现，当前 :9009 OK |
| `task_event_driven.py` | 事件接收与自动触发 | 已实现，当前 :9007 OK |
| `task_pool_event_integration.py` | 事件到 brain_task_orchestrator 的 subprocess 桥接 | 已实现，当前 :9008 OK |
| `unified_task_pool.py` | 本地大脑 SSOT 适配器 | 已实现，注意不要变成第二池 |
| `edge_worker_executor.py` | 从 Brain 拉任务并回传结果 | 已实现，任务执行为模拟/占位型 |

### P1 支撑模块

| 模块 | 职责 |
|---|---|
| `unified_data_layer.py` | 存储 + 缓存 facade |
| `unified_event_bus.py` | 事件发布/订阅/存储 |
| `unified_interface_layer.py` | 多接口注册和路由 |
| `unified_gateway.py` | 聚合任务/知识/经验 API |
| `knowledge_manager.py` | 结构化经验/函数/工作流/决策知识 |
| `rag_knowledge_manager.py` | TF-IDF RAG 检索 |
| `knowledge_api.py` / `rag_api.py` | HTTP API 包装 |

### P2 运维/治理模块

| 模块 | 职责 |
|---|---|
| `self_check.py` | 全边界自检 |
| `architecture_link_check.py` | 本地运行链路检查 |
| `architecture_self_check.py` | 架构内部一致性自检 |
| `ci_automation.py` | CI 报告生成 |
| `verify-installation.sh` | 安装验证 |
| `deploy_event_driven.sh` | 事件服务部署 |
| `deploy_multi_site.sh` | 多站点服务部署 |

### P3 历史/实验/折叠模块

| 模块 | 判断 |
|---|---|
| `simplified/*` | 简化版/参考版，需防止与根实现漂移 |
| `task_pool.py` | 早期内存任务池，不应成为 SSOT |
| `agent_team.py`, `task_scheduler.py`, `load_balancer.py`, `fault_tolerance.py`, `multi_model_analyzer.py` | 能力原型/支撑组件，可被 simplified/core_features 折叠引用 |
| `refactor_architecture.py` | 架构重构生成器/历史迁移工具 |

---

## 7. 理论基础映射

| 架构面 | 当前实现 | 理论基础 | 主要缺口 |
|---|---|---|---|
| 任务生命周期 | brain_task_orchestrator 外部 SSOT + event integration | 状态机 / workflow nets / evidence-based lifecycle | 仓库内适配器和内存池仍需明确非 SSOT 身份 |
| 事件驱动 | HTTP /event + subprocess claim/autorun | Event Sourcing / Pub-Sub / reactive systems | 缺幂等、重放、顺序、死信队列 |
| 多站点 | 注册、心跳、健康、LB、failover | distributed leases / failure detectors / load balancing | 心跳租约和网络分区语义不够严格 |
| 执行代理 | HTTP command endpoint | capability-based security / sandboxing | command/write_file 权限过宽 |
| 自检治理 | 11 类边界自检 | proof-carrying code / CI quality gates | 部分 security warning 还未 fail-closed |
| RAG/知识 | TF-IDF + cosine + keyword index | IR / vector-space model | 缺 embedding/版本化/证据溯源 |
| 简化层 | simplified 复制实现 | strangler fig / modular refactor | 长期双实现漂移风险 |

---

## 8. 主要风险与优先级

### P0：执行层安全边界不足

证据：

- `edge_worker.py` 支持 shell command。
- `edge_worker.py` 支持任意路径 `write_file`。
- `config.yaml` 有 `allowed_commands` 设计，但当前 `edge_worker.py` 未强制执行。
- `self_check_report.json` 安全检查存在 7 个 warning，包括 hardcoded token 和 curl|bash。

风险：

- 局域网内服务若未鉴权/未限权，等价于远程命令执行面。

建议：

1. Edge Worker 强制 token / HMAC / mTLS 至少一种认证。
2. command action 必须经过 allowlist + cwd allowlist + timeout cap。
3. write_file/read_file 限制到配置允许目录。
4. `/info` 不暴露过多本机路径，或仅认证后开放。
5. 安全 warning 升级策略分级：install 文档 warning 可保留，运行时 token/command 风险 fail-closed。

### P0：任务 SSOT 边界需要继续压实

证据：

- `unified_task_pool.py` 声称 Brain 是 SSOT。
- 仓库仍存在 `task_pool.py`、`UnifiedTaskPool` 内存 metrics、simplified TaskPool。

风险：

- 未来修改容易把内存任务池当真实池，造成 brain/edge 状态双写。

建议：

1. 文档中明确：`brain_task_orchestrator.py + kanban.db + markdown task notes` 是唯一生产任务池。
2. `task_pool.py` 标注为 legacy/in-memory test harness。
3. `UnifiedTaskPool` 改名或注释为 `BrainTaskPoolAdapter` 更清晰。
4. 所有状态变更必须回到 brain_task_orchestrator lifecycle API。

### P1：事件可靠性不足

证据：

- `task_pool_event_integration.py` 直接处理 HTTP 事件并 subprocess 调用。
- 未看到 event id / idempotency key / retry store / dead-letter。

风险：

- 重复事件会重复 claim/execute。
- subprocess 成功但响应丢失会产生未知状态。
- 服务重启期间事件丢失。

建议：

1. 每个事件带 `event_id` 和 `task_id + event_type + version` 幂等键。
2. 增加本地 event store，至少 JSONL/SQLite。
3. 增加 retry/dead-letter 状态。
4. auto_claim 前先查询 task 当前状态和 claim lease。

### P1：端口/入口口径不统一

证据：

- README 主节点 9001。
- Edge Worker 默认 9000，安装常用 9002。
- unified API 9003。
- event 9007/9008。
- multi-site 9009。

风险：

- 部署、排障、脚本容易错连。

建议：

- 增加 `PORTS.md` 或 `docs/runtime-topology.md`，明确：
  - Brain API
  - Edge Worker API
  - Unified API
  - Knowledge/RAG API
  - Event API
  - TaskPool Integration API
  - MultiSite API

### P1：simplified 双实现漂移

证据：

- `simplified/` 下复制了 edge_worker、data_layer、event_bus、knowledge、rag。
- 根目录也有同名主实现。

风险：

- 修 bug 只修一边。
- 测试覆盖会误以为两边都健康，但行为不一致。

建议：

1. 如果 simplified 是发布裁剪版：自动从主实现生成或有差异测试。
2. 如果不是主线：冻结为 archive/reference。
3. 新功能只落根实现，simplified 仅做兼容 facade。

### P2：架构文档有“计划/性能宣称”与当前实现混合

证据：

- 多篇文档含“提升 100x/∞/99.9%”等目标性表达。
- 当前自检和链路检查证明功能可用，但不证明这些性能数字。

风险：

- 后续读者把设计目标当已验证事实。

建议：

- 文档区分：
  - verified
  - implemented but simulated
  - designed
  - planned
- 性能数字必须有 benchmark artifact 才可写入“已验证”。

---

## 9. 推荐主线架构收敛方案

### 9.1 推荐唯一生产入口

生产运行入口建议收敛为：

```text
Brain taskpool SSOT
  ↓
TaskPool Event Integration (:9008)
  ↓
MultiSite Manager (:9009)
  ↓
Edge Worker (:9002 per node)
  ↓
Result callback to Brain
```

辅助入口：

- `task_event_driven.py :9007` 保留为纯事件核心/轻量触发器。
- `unified_gateway.py` 作为统一业务 API，但不要绕过任务池生命周期。
- `knowledge_api.py` / `rag_api.py` 可作为独立知识服务，或由 `unified_gateway.py` 聚合。

### 9.2 推荐目录/模块角色声明

```text
production/
  edge_worker.py
  site_registrar.py
  multi_site_manager.py
  task_event_driven.py
  task_pool_event_integration.py
  unified_task_pool.py  # adapter only

support/
  unified_data_layer.py
  unified_event_bus.py
  unified_gateway.py
  knowledge_manager.py
  rag_knowledge_manager.py

ops/
  self_check.py
  architecture_link_check.py
  ci_automation.py
  deploy_*.sh

legacy_or_reference/
  task_pool.py
  simplified/*
  refactor_architecture.py
```

不一定要立即移动文件，但文档中应明确这些角色，避免未来误改。

### 9.3 下一步实施顺序

P0：安全与 SSOT

1. Edge Worker token/auth + command/file allowlist。
2. `UnifiedTaskPool` 文档/命名压实为 Brain adapter。
3. 禁止 edge-worker 直接产生最终 done 状态；只回传 execution result，由 brain lifecycle 决定。

P1：事件可靠性

1. event_id/idempotency key。
2. 本地 event store + retry/dead-letter。
3. auto_claim 前状态确认。

P1：运行拓扑文档

1. 写 `RUNTIME-TOPOLOGY.md`。
2. 写 `PORTS.md`。
3. 标注 verified/planned/simulated。

P2：简化层治理

1. 定义 simplified 的生命周期。
2. 增加主实现 vs simplified 差异测试，或将其冻结。

P2：性能真实性

1. 将 performance claims 改为 benchmark-backed。
2. 增加真实多节点 benchmark，而不是只测 100 个内存注册。

---

## 10. 当前健康结论

当前系统已经具备完整骨架：

- 局域网 Edge Worker 执行代理。
- 多站点注册/心跳/负载均衡 API。
- 事件驱动任务触发层。
- Brain taskpool 的 subprocess 集成。
- 统一数据/事件/接口/知识/RAG 支撑层。
- 自检和链路验证体系。

当前已验证：

- 自检 PASS。
- 全量测试 PASS。
- 9007/9008/9009 运行链路 PASS。

最核心的架构判断：

> 这个仓库已经从“单机 edge worker 脚本”演化成“本地大脑的分布式执行控制面”。下一阶段不应继续横向加组件，而应收敛边界：SSOT、认证授权、事件可靠性、端口拓扑、simplified 双实现治理。

最终建议：

- 主线继续保留“Brain 决策 + Edge 执行”的大脑-触手分离。
- 自动化触发坚持事件驱动，不回退到定时轮询。
- 所有生产状态变更必须回 Brain/taskpool proof gates。
- Edge Worker 只做可审计、可限权、可回传的执行器。
