# Hermes Edge Worker 运行拓扑

## 1. 当前主链路

```text
Human / Brain Taskpool SSOT
        |
        | task.created / task.status_changed / dependency_met
        v
9008 task_pool_event_integration.py
        |
        | normalized event envelope
        v
9007 task_event_driven.py
        |
        | event_id + idempotency + retry + dead-letter
        v
Brain orchestrator claim / autorun_runner
        |
        | execution assignment
        v
9009 multi_site_manager.py
        |
        | site selection / heartbeat / failover
        v
Edge Worker execution-only nodes
        |
        | result/proof back to Brain lifecycle gates
        v
Brain task state / proof gates / review/done decision
```

核心原则：

- Brain/taskpool 是唯一生产事实源。
- Edge Worker 只执行，不拥有最终任务生命周期。
- 自动化优先事件触发，不用定时轮询作为主机制。
- 所有完成态必须回到 Brain lifecycle/proof gate。

## 2. 组件角色

### Brain/taskpool SSOT

外部于本仓库的 `brain_task_orchestrator.py` / kanban.db 是任务状态 SSOT。

职责：

- 任务创建、依赖、优先级、认领、运行、review、done/blocked/retry。
- lifecycle gate / proof gate / multimodel gate。
- 判断任务是否 dispatchable。

### 事件接入层：9008

文件：`task_pool_event_integration.py`

职责：

- 接收 taskpool 侧事件。
- 将任务创建、状态变更、依赖满足等事件转交给事件驱动层。
- 不做最终生命周期判断。

### 事件驱动层：9007

文件：`task_event_driven.py`

职责：

- 事件类型分发。
- 高优先级任务自动认领。
- claimed/assigned 后自动执行。
- P1 已具备可靠性边界：
  - event_id 幂等
  - local JSONL event store
  - retry
  - dead-letter

### 多站点管理层：9009

文件：`multi_site_manager.py`

职责：

- 站点注册。
- 心跳检测。
- 健康评分。
- 负载均衡。
- 故障转移。

### Edge Worker 执行层：9002/节点端口

文件：`edge_worker.py`

职责：

- 执行 Brain/调度层发来的受控命令。
- 文件读写和目录列表受 sandbox 限制。
- 不创建第二任务池，不直接决定 done。

安全边界：

- token auth。
- command allowlist。
- path sandbox。
- timeout cap。

## 3. 数据流

### task.created

```text
Task created in Brain
  -> task.created event
  -> 9008 integration
  -> 9007 event driven
  -> if priority P0/P1: orchestrator.claim(task_id)
  -> autorun_runner(task_id)
  -> result returns to Brain proof/lifecycle gates
```

### task.status_changed: pending -> claimed

```text
status_changed event
  -> 9007 handler
  -> claimed triggers auto_execute(task_id)
  -> autorun_runner(task_id)
```

### dependency_met

```text
dependency_met event
  -> 9007 handler
  -> auto_claim(task_id)
  -> auto_execute(task_id)
```

## 4. 可靠性边界

| 边界 | 当前实现 | 文件/测试 |
|---|---|---|
| 幂等 | event_id processed set + persisted processed records | `task_event_driven.py`, `test_event_reliability.py` |
| 重试 | max_retries + failed_attempt records | `task_event_driven.py`, `test_event_reliability.py` |
| 死信 | dead_letters list + JSONL `dead_lettered` record | `task_event_driven.py`, `test_event_reliability.py` |
| 本地事件存储 | `event_store.jsonl` 或注入路径 | `task_event_driven.py` |
| 执行安全 | auth/allowlist/sandbox/timeout | `edge_worker.py`, `test_edge_worker_security.py` |
| 架构链路 | 5 components / 3 APIs / 4 link tests | `architecture_link_check.py` |

## 5. 验证命令

```bash
/usr/bin/python3 -m pytest test_event_reliability.py test_event_driven.py test_task_event_driven.py -q
/usr/bin/python3 -m pytest test_edge_worker_security.py test_edge_worker.py -q
python3 self_check.py
/usr/bin/python3 architecture_link_check.py
```

## 6. 禁止事项

- 禁止新增常驻 cron 轮询来替代事件触发主链路。
- 禁止 Edge Worker 持有生产任务状态。
- 禁止绕过 Brain lifecycle gate 直接把任务标 done。
- 禁止在没有 token/allowlist/sandbox 的情况下暴露 Edge Worker 到局域网。
- 禁止把 simplified/ reference 代码当生产主线直接运行。
