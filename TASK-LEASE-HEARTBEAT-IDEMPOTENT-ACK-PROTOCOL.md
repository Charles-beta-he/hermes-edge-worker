# Task Lease + Heartbeat + Idempotent Ack Protocol

**Design target**: hermes-edge-worker taskpool reliability for continuous operation
**Status**: Design spec v0.1 (not yet multi-model certified)
**Created**: 2026-05-31
**Based on**: UX-SAFETY-BOUNDARY.md §5, brain_task_orchestrator.py lifecycle state machine, brain_task_dispatch_tick.py reconcile logic
**Risk**: high (per UX-SAFETY-BOUNDARY.md taskpool candidate #5)
**Evidence artifact**: /Users/charles/hermes-edge-worker/TASK-LEASE-HEARTBEAT-IDEMPOTENT-ACK-PROTOCOL.md (proposed location)

---

## Table of Contents

1. Current State Baseline
2. Gap Analysis
3. Lease Protocol
4. Heartbeat Protocol
5. Idempotent Ack Protocol
6. Idempotency Key Design
7. Crash / Network Split Scenario Table
8. Rollback / Re-dispatch Standards
9. Implementation Checklist
10. Verification Scenarios

---

## 1. Current State Baseline

The existing Hermes taskpool already has a basic claim/lease mechanism:

| Feature | Current state |
|---|---|
| `claimed_by` + `claim_expires_at` + `run_id` frontmatter | Present in every task note via lifecycle transition |
| Lease TTL | Hardcoded default `ttl_minutes=60`, configurable via `--ttl-minutes` on claim |
| `has_active_claim()` | Checks `claimed_by` + `run_id` + non-expired `claim_expires_at` |
| `is_stale_claim()` | Detects expired claims but performs no auto-recovery |
| `lifecycle_gate()` | Enforces claim ownership before `running → review → done` |
| `stale_claim_reclaim_enabled` | Present in dispatch_tick config but defaults to `False` (dry-run only) |
| `run_id` as unique identifier | Present, format: `{actor}-{timestamp}` |
| Retry mechanism | `retry_count` increment, `next_attempt_at` delay, configurable base/max delay |

**Source evidence**:
- `brain_task_orchestrator.py` line 2325: `Task.claim_expires_at()` property
- `brain_task_orchestrator.py` line 2342: `Task.is_stale_claim()` method
- `brain_task_orchestrator.py` line 3938: `has_active_claim()` standalone function
- `brain_task_orchestrator.py` line 4022: `apply_lifecycle_status()` with lease TTL and `run_id` generation
- `brain_task_orchestrator.py` line 3944: `lifecycle_gate()` with claim ownership enforcement
- `brain_task_dispatch_tick.py` lines 358-360: `stale_claim_reclaim_enabled: False`, `stale_claim_reclaim_dry_run: True`

## 2. Gap Analysis

| Gap | Impact |
|---|---|
| **No heartbeat** — worker crash leaves `running` wedge until claim_expires_at, then only manual reconciliation | Tasks hang for up to 60 min TTL, then require manual force-retry |
| **No idempotent ack** — same task dispatched to multiple workers after network split → duplicate side effects | Data corruption, double-completion, broken proof chain |
| **No formal re-dispatch protocol** — stale claims detected but not auto-resolved | Operator must intervene, automation gap |
| **No rollback standard** — no record of what happened before a crash | Post-crash diagnosis requires log spelunking |
| **run_id is time-based** — `{actor}-{timestamp}` format lacks global uniqueness | Idempotency dedup fragile across partition boundaries |

## 3. Lease Protocol

### 3.1 Lease Lifecycle (extended state machine)

```
pending --[dispatch]--> claimed --[heartbeat-ok]--> running --[work-complete]--> review --[proof-pass]--> done
                           |                     |                              |
                    [lease-expiry]          [lease-expiry]                  [lease-expiry]
                           |                     |                              |
                        retry                 retry                          blocked
```

### 3.2 Lease Fields (extended frontmatter)

```yaml
# Existing fields
claimed_by: "worker-hermes-parallel"
claim_expires_at: "2026-05-31T18:00:00+08:00"
run_id: "f1a2b3c4-1234-5678-9abc-def012345678"  # UUID v4 (changed from timestamp-based)

# New fields
lease_version: 1                          # monotonic counter for lease renewal
lease_seen_at: "2026-05-31T17:30:00+08:00" # last heartbeat timestamp
lease_epoch: "2026-05-31T17:00:00+08:00"  # original claim epoch (set on first claim)
lease_extension_count: 0                  # how many times lease was extended via heartbeat
lease_proof_hashes: []                    # heartbeat proof chain (optional)
```

### 3.3 Default Lease Parameters

```yaml
lease:
  initial_ttl_minutes: 15       # shorter than current 60 for faster crash detection
  max_ttl_minutes: 60           # ceiling on extensions (absolute from lease_epoch)
  heartbeat_interval_seconds: 60
  stale_grace_seconds: 30       # extra time after TTL expires before reclaim
  reclaim_cooldown_seconds: 120 # minimum time between re-dispatch of same task
  stale_claim_reclaim_enabled: True   # changed from False
  stale_claim_reclaim_dry_run: False  # changed from True
```

### 3.4 Lease Renewal Rules

1. Lease is renewed by heartbeat, not by claim re-entry.
2. Each successful heartbeat increments `lease_version` by 1.
3. `claim_expires_at` = min(`lease_epoch` + `max_ttl_minutes`, `lease_seen_at` + `initial_ttl_minutes`)
4. Once `lease_epoch` + `max_ttl_minutes` is reached, no further renewal allowed without explicit re-claim.
5. Re-claim requires the task to first transition to `retry` (with evidence of original lease expiry).

### 3.5 Lease Expiry Detection (state machine)

```
if status in (claimed, running) and now() > claim_expires_at:
    if now() < claim_expires_at + stale_grace_seconds:
        classify: "stale_grace"  # can still receive heartbeat if it arrives in time
    elif now() < claim_expires_at + stale_grace_seconds + reclaim_cooldown_seconds:
        classify: "reclaim_cooldown"
        action: transition to retry with evidence "lease_expired"
        generate idempotency_key for the reclaim event
    else:
        classify: "available_for_reclaim"
        action: dispatch as normal (first check idempotency against prior run_id)
```

## 4. Heartbeat Protocol

### 4.1 Heartbeat Contract

A heartbeat is a lightweight, idempotent PATCH-level lifecycle event from a running worker to the taskpool control plane.

**CLI syntax**: `brainctl heartbeat <task_id> --run-id <run_id> --lease-version <N> --actor <actor>`

**Effect**: Updates `lease_seen_at`, extends `claim_expires_at`, increments `lease_version`.

### 4.2 Heartbeat Timing

- **Normal**: every 60 seconds (configurable per task via `heartbeat_interval_seconds`)
- **Slowed**: if no CPU activity in interval, heartbeat TTL decays 50% faster
- **Accelerated**: during final work (review preparation), heartbeat every 30 seconds
- **Missed threshold**: 2x heartbeat interval with no heartbeat → classify as `suspected_dead`

### 4.3 Heartbeat Message Schema

```json
{
  "type": "heartbeat",
  "version": 1,
  "task_id": "task-identifier",
  "run_id": "f1a2b3c4-1234-5678-9abc-def012345678",
  "lease_version": 3,
  "timestamp": "2026-05-31T17:30:00+08:00",
  "actor": "hermes-parallel-worker-7",
  "status": "running",
  "progress": "implementing_phase_2_of_4",
  "proof_hash": "sha256:a1b2c3d4e5..."
}
```

### 4.4 Heartbeat Receiver Logic

```
on_heartbeat(task_id, run_id, lease_version, timestamp):
    task = read_task(task_id)
    if task.run_id != run_id:
        return {status: "rejected", reason: "run_id_mismatch", task_run_id: task.run_id}
    if task.lease_version > lease_version:
        return {status: "rejected", reason: "lease_version_stale"}
    if task.status not in (claimed, running):
        return {status: "rejected", reason: "invalid_status"}
    if task.claim_expires_at + max_ttl_minutes < timestamp:
        return {status: "rejected", reason: "lease_epoch_expired"}

    new_expires_at = min(
        task.lease_epoch + max_ttl_minutes,
        timestamp + initial_ttl_minutes
    )
    update_task(task_id, {
        "lease_seen_at": timestamp,
        "claim_expires_at": new_expires_at,
        "lease_version": lease_version + 1,
        "lease_extension_count": task.lease_extension_count + 1,
    })
    return {status: "accepted", new_expires_at: new_expires_at}
```

### 4.5 Heartbeat Failure Classification

| Symptom | Classification | Recovery |
|---|---|---|
| 1 miss (within 2x interval) | `heartbeat_late` | No action; log warning |
| 2 consecutive misses | `suspected_dead` | Transition to `retry` with `next_attempt_at = now + reclaim_cooldown` |
| 3 consecutive misses | `presumed_dead` | Force transition to `blocked` with `reason:worker_presumed_dead`; requires human review |
| Heartbeat with stale `lease_version` | `split_brain_detected` | Evict old worker to `retry` with evidence `split_brain:run_id={run_id}:lease_version={stale}` |
| Heartbeat after `reclaim_cooldown` begins | `zombie_worker` | Log evidence; ignore heartbeat; mark in proof log |

## 5. Idempotent Ack Protocol

### 5.1 Ack Types

| Type | Trigger | Effect |
|---|---|---|
| `ack:work-progress` | Heartbeat with progress field | Informational; no state change |
| `ack:work-complete` | Worker finishes work, submits proof | Transition `running → review` with evidence |
| `ack:work-failed` | Worker encounters unrecoverable error | Transition `running → retry` with structured failure |
| `ack:lease-release` | Worker voluntarily releases lease | Transition back to `pending` (not retry) |
| `ack:preempted` | Worker receives preemption signal | Transition `running → retry` with `reason:preempted` |

### 5.2 Idempotent Ack via Idempotency Key

Every ack carries a nonce-based idempotency key derived from (task_id, run_id, ack_type, ack_count, actor).

```
idempotency_key = sha256(f"HERMES_ACK:v1:{task_id}:{run_id}:{ack_type}:{ack_count}:{actor}")
```

The control plane tracks `idempotency_keys_seen`. If the same key arrives twice, the second ack is silently accepted (same result returned) but the task state is not changed.

### 5.3 Ack Lifecycle

```
Worker produces ack:
    key = derive_key(task_id, run_id, ack_type, ack_count, actor)
    evidence = ["ack:{key}:{ack_type}:{ack_count}:{proof_hash}"]

Control plane receives ack:
    if key in idempotency_keys_seen:
        return {"status": "already_applied", "existing_state": task.status}
    else:
        apply lifecycle transition
        append key to idempotency_keys_seen
        return {"status": "applied", "new_state": task.status}
```

## 6. Idempotency Key Design

### 6.1 Key Derivation Function

```python
import hashlib

def idempotency_key(
    task_id: str,
    run_id: str,
    ack_type: str,    # work-complete, work-failed, lease-release, preempted, reclaim
    ack_count: int,   # monotonic counter within this run_id
    actor: str        # the worker's identity
) -> str:
    raw = f"HERMES_ACK:v1:{task_id}:{run_id}:{ack_type}:{ack_count}:{actor}"
    return hashlib.sha256(raw.encode()).hexdigest()
```

### 6.2 Run ID Format Change

**Current**: `{actor}-{YYMMDDHHmmss}` (collision risk, no global uniqueness)

**Proposed**: `{uuid4}` with actor stored separately as `claimed_by`

Rationale:
- UUID v4 provides probabilistic uniqueness across workers, processes, network partitions
- Decouples identity (who claimed) from identifier (what run)
- Enables split-brain detection: two workers claiming same task will have different run_ids
- Simpler to validate

### 6.3 Idempotency Key Storage

**Primary storage**: Append-only JSONL file per task at `~/.hermes/state/ack-keys/{task_id}.jsonl`

```json
{"idempotency_key": "sha256...", "run_id": "...", "ack_type": "work-complete", "ack_count": 1, "applied_at": "2026-05-31T17:30:00+08:00", "actor": "hermes-parallel-worker-7"}
```

**TTL**: Keys retained for `max_lease_epoch` + 7 days after task enters `done` or `archived`.

**Lightweight alternative**: Store as frontmatter field `idempotency_keys_seen: [key1, key2, ...]`. Acceptable for low-volume tasks.

### 6.4 Idempotency Scope

| Scope | Key includes | Dedup window |
|---|---|---|
| Per-task-per-run_id | `task_id:run_id:ack_type:ack_count` | Until task done/archived + 7d |
| Per-ack-type | `task_id:run_id:work-complete:*` | Single ack type per run_id |
| Global | Full key | Applies across all retries of same task |

## 7. Crash / Network Split Scenario Table

| # | Scenario | Detection | Recovery | Idempotency Gate |
|---|---|---|---|---|
| 1 | Worker crashes; no heartbeat sent | Heartbeat timeout 2x interval → `suspected_dead` | Auto-retry after `reclaim_cooldown` | New `run_id` prevents ack collision |
| 2 | Worker crashes; 1 heartbeat sent then stops | Same as #1; at most one stale ack possible | Auto-retry; stale ack rejected via `run_id` mismatch | `work-complete` ack from old `run_id` rejected |
| 3 | Network partition; worker alive, control plane unreachable | Worker cannot send heartbeat → `suspected_dead` | New worker dispatched; old worker finds `retry` status | Old worker's transition rejected (`status != running`) |
| 4 | Network partition recovers; both workers alive | Old worker's heartbeat triggers `split_brain_detected` | Old worker evicted; new worker continues | `idempotency_keys_seen` prevents duplicate completion |
| 5 | Worker sends `work-complete` ack, control plane crashes before persisting | No ack record survives; worker retries | Worker resends same ack; same `ack_count` → idempotent | `idempotency_key` matches → `already_applied` |
| 6 | Worker sends `work-complete` ack, network drops it | Control plane never sees ack; timeout | New dispatch with new `run_id`; old worker finds `retry` | Old worker's ack arrives later → rejected via `run_id` mismatch |
| 7 | Double dispatch to two workers simultaneously | Both claim with different `run_id`; first claim wins | Second worker's claim rejected via `lifecycle_gate()` | Already gated at claim level |
| 8 | Worker receives preemption signal | Heartbeat carries `status:preempting` | Control plane transitions to `retry` with `reason:preempted` | `idempotency_key` = `{run_id}:preempted:1` prevents replay |
| 9 | Manual operator force-retries running task | `--force --reason` bypasses `lifecycle_gate()` | New worker dispatched; old worker's next heartbeat → `zombie_worker` | Evidence records operator override for audit |
| 10 | Control plane itself crashes mid-transition | Task in partial state; no heartbeat | On restart, reconcile pass detects stale claims | At-most-once: no duplicate transition without re-delivery |

### 7.1 Split-Brain Resolution Protocol

When `split_brain_detected` is raised:

1. Old worker's lease immediately revoked via transition to `retry`.
2. New worker's lease preserved.
3. Evidence logged: `split_brain:old_run_id={old_run_id}:new_run_id={new_run_id}:decision=keep_new_lease`.
4. If old worker committed partial proof, it is retained as `proof_stash_{old_run_id}.jsonl` in state dir.

## 8. Rollback / Re-dispatch Standards

### 8.1 When to Re-dispatch vs Rollback

| Condition | Action |
|---|---|
| Worker crash, no evidence of side effects | Re-dispatch (safe to retry) |
| Worker crash with partial file writes | Re-dispatch + workspace cleanup + log `rollback_signal` |
| Worker crash with idempotent API calls | Re-dispatch (REST idempotency is caller's responsibility) |
| Worker crash with non-idempotent API calls | **ROLLBACK** required first; mark `blocked` for human audit |
| Network split, no side effects logged | Re-dispatch |
| Network split, `work-complete` ack received but task still `running` | Re-dispatch; idempotent ack prevents double-completion |
| Manual force-retry of running task | Re-dispatch; `zombie_worker` evidence logged |

### 8.2 Rollback Standard

When a rollback is required:

1. Set task status to `blocked` with reason `rollback_required:non_idempotent_side_effects`.
2. Populate `rollback_signal` frontmatter:
   ```yaml
   rollback_signal:
     reason: "non_idempotent_api_call_before_crash"
     run_id: "f1a2b3c4-1234-5678-9abc-def012345678"
     side_effects:
       - type: "api:create_resource"
         target: "/api/orders/123"
         idempotent: false
       - type: "file:write"
         target: "/tmp/output/data.csv"
         cleanup_strategy: "rm"
   ```
3. Rollback executed by human or separate `rollback-executor` tool (separate design needed).
4. After rollback confirmed, task may be force-retried with `--reason "rollback_confirmed"`.

### 8.3 Re-dispatch Decision Matrix

```
                | No side effects | Idempotent side effects | Non-idempotent side effects
----------------|-----------------|-------------------------|---------------------------
Worker crash     | Re-dispatch     | Re-dispatch             | ROLLBACK + blocked
Network split    | Re-dispatch     | Re-dispatch             | ROLLBACK + blocked
Heartbeat miss   | Re-dispatch     | Re-dispatch             | ROLLBACK + blocked
Operator force   | Re-dispatch     | Re-dispatch             | Re-dispatch (operator override, audited)
Preemption       | Re-dispatch     | Re-dispatch             | Re-dispatch with reduced cooldown
```

### 8.4 Stale Claim Reclaim Procedure (automated)

```
for each task with status in (claimed, running) and claim_expires_at < now():
    if claim_expires_at + stale_grace_seconds < now():
        actor = task.claimed_by
        run_id = task.run_id
        transition task to "retry" with:
            reason = "stale_claim_reclaimed"
            evidence = [
                "stale_claim_detected:claim_expires_at={claim_expires_at}",
                "stale_claim_detected:actor={actor}",
                "stale_claim_detected:run_id={run_id}",
                "stale_claim_detected:lease_version={lease_version}",
            ]
        set next_attempt_at = now() + reclaim_cooldown_seconds
        generate and store idempotency key to prevent duplicate reclaim
```

## 9. Implementation Checklist

### Phase 1: Frontmatter schema + compatibility (low risk)
- [ ] Add `lease_version`, `lease_seen_at`, `lease_epoch`, `lease_extension_count`, `lease_proof_hashes` to task frontmatter directly (no code whitelist needed — `split_frontmatter()` accepts arbitrary YAML keys)
- [ ] Change `run_id` from timestamp-based to UUID v4 (backward-compat accept old format)
- [ ] Add `idempotency_keys_seen` as optional frontmatter field
- [ ] Add `rollback_signal` as optional structured frontmatter field
- [ ] Update `has_active_claim()` to accept old-format run_ids

### Phase 2: Heartbeat command (medium risk)
- [ ] Add `command_heartbeat()` to orchestrator with receiver logic from §4.4
- [ ] Add CLI: `brainctl heartbeat <task_id> --run-id <run_id> --lease-version <N>`
- [ ] Update `lifecycle_gate()` to accept heartbeat as pseudo-status
- [ ] Integrate heartbeat into dispatch tick state machine

### Phase 3: Idempotent ack (medium risk)
- [ ] Add `ack_count` tracking per run_id in task frontmatter
- [ ] Implement idempotency key derivation and storage (JSONL store)
- [ ] Update `apply_lifecycle_status()` to check `idempotency_keys_seen`
- [ ] Add `--ack-count` and `--idempotency-key` to `transition` CLI

### Phase 4: Reclaim + crash recovery (high risk)
- [ ] Set `stale_claim_reclaim_enabled = True` and `stale_claim_reclaim_dry_run = False`
- [ ] Implement stale grace window logic
- [ ] Implement split-brain detection in heartbeat receiver
- [ ] Update reconcile pass for full scenario table recovery
- [ ] Add `zombie_worker` detection and rejection

### Phase 5: Rollback standard (high risk)
- [ ] Design `rollback-executor` tool (separate task)
- [ ] Integrate `rollback_signal` into lifecycle gate for blocked status
- [ ] Add rollback confirmation as evidence type

## 10. Verification Scenarios

### 10.1 Unit Test Cases

| Test | Input | Expected |
|---|---|---|
| Heartbeat accepted | Valid run_id + lease_version match | `status: accepted` |
| Heartbeat rejected (stale run_id) | Old run_id on re-dispatched task | `status: rejected`, reason `run_id_mismatch` |
| Heartbeat rejected (stale lease_version) | Concurrent heartbeat with lower version | `status: rejected`, reason `lease_version_stale` |
| Idempotent ack dedup | Same idempotency_key sent twice | Second `status: already_applied` |
| Idempotent ack applied | New idempotency_key | `status: applied`, state changed |
| Stale claim reclaim | Task in running with expired claim | Transitioned to retry with evidence |
| Split brain detection | Heartbeat after new worker claimed | Detected, old worker evicted |
| Zombie worker rejection | Heartbeat during reclaim_cooldown | Logged and ignored |
| Rollback gate | Non-idempotent side effects + crash | Status set to `blocked`, not `retry` |

### 10.2 Integration Test Scenarios

1. **Crash recovery loop**: Dispatch → claim → worker crash (simulated) → TTL + grace → reclaim → new worker completes → proof verified.
2. **Network partition loop**: Worker running → heartbeat lost → new worker dispatched → partition heals → old worker heartbeat triggers split-brain → old worker evicted → new worker completes.
3. **Duplicate ack test**: Worker sends `work-complete` ack twice → second ack is `already_applied` → task does not double-complete.
4. **Force-retry safety**: Operator force-retries running task → new worker works → old worker's late ack rejected → proof chain intact.

---

## Appendix A: Key Code Changes

### brain_task_orchestrator.py

- `Task` class: add `lease_version`, `lease_seen_at`, `lease_epoch`, `lease_extension_count` properties
- **Frontmatter**: no whitelist validation needed — `split_frontmatter()` accepts arbitrary YAML keys. Add fields directly to task note frontmatter.
- `apply_lifecycle_status()`: update `run_id` generation to UUID v4; check `idempotency_keys_seen` before transitions; set `lease_epoch` on first claim
- `lifecycle_gate()`: accept heartbeat pseudo-status; allow `heartbeat → heartbeat` renewals
- `has_active_claim()`: optionally check `lease_epoch + max_ttl_minutes`
- `command_heartbeat()`: new function implementing §4.4 receiver logic

### brain_task_dispatch_tick.py

- Default config: `stale_claim_reclaim_enabled = True`, `stale_claim_reclaim_dry_run = False`
- Reconcile pass: add split-brain detection, zombie worker detection, reclaim cooldown enforcement

## Appendix B: Proof Chain Integration

The heartbeat and ack protocol produces structured evidence for the autorun proof chain:

```
proof:heartbeat:v1:{task_id}:{run_id}:{lease_version}:{timestamp}
proof:ack:v1:{task_id}:{run_id}:{ack_type}:{ack_count}:{idempotency_key_prefix}
proof:reclaim:v1:{task_id}:{old_run_id}:{new_run_id}
proof:split_brain:v1:{task_id}:{old_run_id}:{new_run_id}:{decision}
proof:zombie:v1:{task_id}:{run_id}:{lease_version}:{timestamp}
```
