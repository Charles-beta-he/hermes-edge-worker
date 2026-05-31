# P0 安全边界与 SSOT 收敛推进报告

## 目标

基于 `SYSTEM-ARCHITECTURE-FULL-REVIEW.md` 的 P0 结论，继续推进两条主线：

1. Edge Worker 执行面安全边界：认证、命令 allowlist、文件路径 sandbox、timeout cap。
2. 任务池 SSOT 边界：本地 Brain/brain_task_orchestrator.py 是唯一生产事实源，仓库内内存任务池只能作为 legacy/test harness 或 adapter。

## 已实施

### 1. Edge Worker 安全边界

文件：`edge_worker.py`

新增/收紧：

- `SECURITY_TOKEN`
  - 支持 `Authorization: Bearer <token>`。
  - 支持 `X-Hermes-Token: <token>`。
  - `/health` 默认开放；`/info`、`/execute`、`/command` 在配置 token 后必须认证。
- `HMAC_SECRET`
  - 可选；配置后 POST 请求必须携带 `X-Hermes-Timestamp`、`X-Hermes-Nonce` 与 `X-Hermes-Signature`。
  - 签名 payload: `METHOD\nPATH\nTIMESTAMP\nNONCE\nBODY`，算法 HMAC-SHA256。
  - 默认要求 timestamp 在 ±300 秒窗口内，可通过 `--hmac-max-skew-seconds` / `HERMES_EDGE_HMAC_MAX_SKEW_SECONDS` 调整。
  - `X-Hermes-Nonce` 在有效窗口内只能使用一次，降低窗口内重放风险。
  - 用于防止已认证请求体被中间层篡改。
- `ALLOWED_COMMANDS`
  - `run_command` 必须命中 allowlist。
  - 空 allowlist 默认拒绝 shell 命令。
- `ALLOWED_PATHS`
  - `read_file` / `write_file` / `list_dir` / command cwd 必须位于 sandbox 内。
  - 默认 sandbox 为用户 home；可通过 CLI/config 覆盖。
- `MAX_TIMEOUT`
  - 命令执行 timeout 被配置上限封顶。
- Brain 注册/心跳会携带认证 header。
- `/info` 不再暴露 home 路径，改为暴露安全配置摘要。

### 1.1 Event API 安全边界

文件：`request_security.py`、`task_event_driven.py`、`task_pool_event_integration.py`

新增/收紧：

- 9007 `/event` 与 9008 `/event` 复用 `RequestAuthenticator`。
- 支持 `HERMES_EVENT_API_TOKEN` / `HERMES_EVENT_API_HMAC_SECRET` / `HERMES_EVENT_API_HMAC_MAX_SKEW_SECONDS`。
- 未配置 Event API 专用变量时回退到 Edge Worker 的 `HERMES_EDGE_TOKEN` / `HERMES_EDGE_HMAC_SECRET` / `HERMES_EDGE_HMAC_MAX_SKEW_SECONDS`。
- `/health` 保持开放；`/metrics` 配置 token 后需要 token；`/event` 配置 token/HMAC 后需要 token + 签名。
- Event API HMAC payload 同样为 `METHOD\nPATH\nTIMESTAMP\nNONCE\nBODY`，并要求 nonce 在窗口内不可重放。

CLI 新增：

```bash
python3 edge_worker.py \
  --token "$HERMES_EDGE_TOKEN" \
  --hmac-secret "$HERMES_EDGE_HMAC_SECRET" \
  --hmac-max-skew-seconds 300 \
  --allowed-command git \
  --allowed-command python3 \
  --allowed-path /Users/charles/hermes-edge-worker \
  --max-timeout 120
```

### 2. 安全测试

新增：`test_edge_worker_security.py`

覆盖：

- 未携带 token 时 `_is_authorized()` 返回 False。
- Bearer token 正确时通过。
- 未在 allowlist 内的 shell 命令被拒绝。
- allowlist 内命令可执行。
- 文件读写必须落在 allowed_paths 内。
- timeout 被 max_timeout 封顶。

### 3. SSOT 边界收敛

文件：

- `task_pool.py`
- `unified_task_pool.py`

收敛说明：

- `task_pool.py` 明确标记为 legacy in-memory task pool：
  - 只用于测试夹具、早期 Agent Team 原型兼容、本地算法实验。
  - 禁止在生产链路中把该模块的 COMPLETED/FAILED 当最终任务生命周期状态。
- `unified_task_pool.py` 明确标记为 Brain task pool adapter：
  - 本地 Brain/brain_task_orchestrator.py 是任务状态 SSOT。
  - `metrics/task_assignments` 只作为运行时观测和路由缓存。
  - 生产任务创建、查询、状态更新必须回到 brain_orchestrator。

## 验证结果

### 局部验证

```bash
/usr/bin/python3 -m pytest \
  test_edge_worker_security.py \
  test_request_security.py \
  test_event_reliability_helper.py \
  test_event_reliability.py \
  test_task_event_driven.py \
  test_task_pool_event_integration.py \
  test_task_pool_event_integration_reliability.py \
  test_architecture_event_observability.py \
  test_architecture_event_payload.py \
  test_architecture_link_check.py \
  test_ports_doc_consistency.py \
  -q
```

结果：

```text
34 passed, 1 warning
```

### 全量测试

```bash
/usr/bin/python3 -m pytest test_*.py -q
```

结果：

```text
199 passed, 12 warnings
```

### 自检

```bash
python3 self_check.py
```

结果：

```text
overall_status: PASS
boundary_coverage: 100.0%
security: PASS
architecture_links: PASS
```

### 架构链路

```bash
/usr/bin/python3 architecture_link_check.py
```

结果：

```text
PORTS.md: OK
components: 5/5 OK
API endpoints: 3/3 OK
event reliability: event_driven=ok, task_pool_integration=ok
link tests: 4/4 OK
overall: OK
```

## 当前仍需继续的 P1

1. 事件可靠性：event_id、idempotency key、本地 event store、retry/dead-letter。
2. 端口/运行拓扑收敛：`PORTS.md`、`RUNTIME-TOPOLOGY.md`。
3. simplified 双实现治理：冻结为 reference，或合并回主线并加差异测试。
4. 安全检查策略升级：把 runtime hardcoded token/command 风险从 warning 升级为 fail-closed；安装脚本文档类 warning 单独分级。

## 注意

本次没有修改已有 `install.sh` 脏改动；没有触碰 `install-auto.sh.backup`。
