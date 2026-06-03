# Capability-Based Task Routing for Edge Devices — Design

## 1. Problem Statement

The current `hermes-edge-worker` routing layer has three routing mechanisms, none of which are capability-aware:

| Module | Algorithm | Capability-aware? |
|---|---|---|
| `task_scheduler.py` | Weighted round-robin | No — treats all agents equal |
| `load_balancer.py` | Consistent hash ring | No — routes by task_id hash |
| `agent_team.py` | Role + capability filter | Partial — requires exact role match AND all capabilities present; no scoring |

Meanwhile, edge workers already advertise capabilities via `GET /info`:

```json
{
  "name": "pi-5",
  "capabilities": ["run_command", "read_file", "write_file", "list_dir", "browser_screenshot"],
  "platform": "linux",
  "security": { "allowed_commands": [...], "allowed_paths": [...] }
}
```

**Gap**: No component actually matches task requirements to worker capabilities when routing.

## 2. Goals

1. **Declare** task capability requirements (what a task needs).
2. **Match** requirements against registered worker capabilities.
3. **Score** candidates by match quality, health, and load.
4. **Route** to the best-fit worker, with fallback strategies.
5. **Integrate** with existing multi-site management (`:9009`), event-driven layer (`:9007`/`:9008`), and edge worker registration.

## 3. Non-Goals

- Remote GPU/CPU resource scheduling (out of scope for LAN edge workers).
- Bin-packing or cluster autoscaling.
- Replacing the Local Brain as task lifecycle SSOT.

## 4. Data Model

### 4.1 Capability Descriptor

Each capability is a string tag. Workers declare a set; tasks declare requirements.

```python
# Worker capabilities (from /info or registration)
worker_caps = {
    "run_command", "read_file", "write_file", "list_dir",
    "browser_screenshot", "python3", "node", "docker"
}

# Task requirements
task_requirements = {
    "required": ["run_command", "python3"],      # MUST have all
    "preferred": ["docker"],                       # NICE to have
    "excluded": ["gpu_only"]                       # MUST NOT have (cost/resource guard)
}
```

### 4.2 Worker Profile (enriched)

```python
{
    "worker_id": "pi-5",
    "url": "http://192.168.31.130:9002",
    "capabilities": {"run_command", "read_file", "python3"},
    "platform": "linux",
    "arch": "aarch64",
    "status": "online",
    "load": 0.3,           # 0.0 = idle, 1.0 = fully loaded
    "health_score": 0.95,  # rolling health metric
    "last_heartbeat": "2026-06-03T10:00:00Z",
    "metadata": {}          # extensible tags
}
```

### 4.3 Task Routing Request

```python
{
    "task_id": "task-001",
    "task_type": "code_generation",
    "requirements": {
        "required": ["run_command", "python3"],
        "preferred": ["docker"],
        "excluded": []
    },
    "priority": 3,
    "timeout": 120,
    "affinity": None        # optional: prefer specific worker_id
}
```

## 5. Algorithm: Capability Match Scoring

### 5.1 Filter Pipeline

```
All registered workers
  → filter: status == "online"
  → filter: worker has ALL required capabilities
  → filter: worker has NONE of excluded capabilities
  → score remaining candidates
  → pick highest score
```

### 5.2 Scoring Function

```python
score(worker, task_req) =
    base_match_score           # 1.0 if all required met
  + preferred_bonus            # +0.2 per preferred cap matched (capped at 1.0)
  + health_bonus               # +health_score * 0.3
  + load_bonus                 # +(1.0 - load) * 0.3
  + affinity_bonus             # +1.0 if affinity matches
  - penalty                    # 0 normally; +0.5 if worker recently failed this task type
```

**Tie-breaking**: lowest current load → most recently heartbeated → alphabetical worker_id.

### 5.3 Fallback Strategy

1. **Exact match** (all required + preferred scored).
2. **Degraded match**: relax preferred requirements, re-score.
3. **No match**: return `None` with reason. Caller decides retry/queue/deny.

## 6. Architecture Integration

### 6.1 Component Placement

```
┌──────────────────────────────────────────────────────┐
│                  Local Brain (SSOT)                    │
│         task creation / lifecycle / proof gates         │
└──────────────────────▲────────────────────────────────┘
                       │ task.created / task.assigned
                       │
┌──────────────────────┴────────────────────────────────┐
│              CapabilityRouter (NEW)                     │
│                                                        │
│  register_worker(id, caps, url, metadata)              │
│  unregister_worker(id)                                 │
│  update_worker_health(id, health_score, load)          │
│  route(task_requirements) → worker_id | None           │
│  route_with_reason(task_requirements) → RoutingResult  │
│                                                        │
│  Integrates with:                                      │
│  - multi_site_manager.py (site registration feeds in)  │
│  - task_event_driven.py (event triggers routing)       │
│  - edge_worker.py /info (capability discovery)         │
└──────────────────────────────────────────────────────┘
```

### 6.2 Integration Points

| Consumer | How it uses CapabilityRouter |
|---|---|
| `multi_site_manager.py` | On site registration, calls `register_worker()`. On heartbeat, calls `update_worker_health()`. |
| `task_event_driven.py` | On `task.created`/`task.status_changed`, calls `route()` to pick worker before dispatching. |
| `edge_worker.py` | On startup registration, capabilities are forwarded to router. |
| `task_pool_event_integration.py` | After auto-claim, uses router for worker selection. |
| `unified_gateway.py` | New `/route` endpoint for manual/test routing queries. |

### 6.3 API Additions (future)

```
POST /route
  { requirements: { required: [...], preferred: [...] } }
  → { worker_id, score, reason }

GET /workers
  → { workers: [...], total: N }

GET /workers/{id}/capabilities
  → { capabilities: [...], platform: ... }
```

## 7. Edge Cases & Failure Modes

| Scenario | Behavior |
|---|---|
| No workers registered | `route()` returns `None`, reason: "no_workers" |
| No worker meets required caps | `route()` returns `None`, reason: "no_match" |
| All matching workers offline | Filtered out; same as no_match |
| Worker goes offline mid-task | Multi-site health check marks offline; failover manager reassigns |
| Affinity worker unavailable | Affinity bonus ignored; falls back to best available |
| All workers at max load | Still routes to lowest-load worker; caller can threshold-gate |

## 8. Implementation Plan

### Phase 1: Core Router (this PR)
- `capability_router.py`: CapabilityRouter class with register/unregister/route/score.
- `test_capability_router.py`: Full unit test coverage.
- Integration with existing architecture (no breaking changes).

### Phase 2: Event Integration
- Wire `CapabilityRouter` into `task_event_driven.py` for automatic routing on task events.
- Wire into `multi_site_manager.py` for automatic worker registration.

### Phase 3: API & Observability
- Add `/route`, `/workers` endpoints to unified gateway.
- Add routing metrics (match rate, fallback rate, avg score).

## 9. Security Considerations

- Capability strings are validated (no shell injection, alphanumeric + underscore only).
- Worker registration requires existing auth (token/HMAC).
- Routing decisions are logged for audit.
- No capability escalation: workers cannot self-declare capabilities beyond what the edge worker config allows.

## 10. Verification

- Unit tests: 20+ test cases covering exact match, partial match, no match, scoring, fallback, edge cases.
- Integration: existing `pytest test_*.py` passes (167 tests, no regression).
- Architecture link check: existing checks still pass.
