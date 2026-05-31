# Hermes Edge Worker UX / Safety Boundary SSOT

Created: 2026-05-31
Status: advisory SSOT, not multi-model certified
Scope: Hermes Edge Worker install, pairing, diagnosis, cloud-brain/device UX

## Evidence

- `install.sh` now uses safe defaults with explicit escape hatches:
  - TLS OK: install proceeds.
  - TLS failure + interactive TTY: user may type `yes` for a one-time insecure download mode.
  - TLS failure + non-interactive: fail closed.
  - `HERMES_EDGE_ALLOW_INSECURE_SSL=1`: explicit opt-in insecure mode.
- `consult_models.py` T2 discussion timed out.
- T1 advisory degraded below quorum: Claude produced an architecture plan; GPT timed out.
- Direct DeepSeek advisory succeeded and emphasized tests/docs/smoke-test/diagnose.
- Direct MiMo advisory succeeded and emphasized low-friction onboarding, red/yellow/green self-check, retry before notification, and locked-down defaults.

Therefore this document is an evidence-grounded advisory boundary, not a certified multi-model architecture decision.

## North Star

Hermes should not merely control multiple machines; every edge device should join the cloud brain in a way that is understandable, diagnosable, degradable, recoverable, and safe by default.

## Product / Architecture Principles

1. Safe default, explicit escape.
   - No silent `curl -k`.
   - No weak default tokens for production/long-lived use.
   - Non-interactive automation must fail closed unless an explicit env override is present.
   - Interactive flows may offer a one-time escape hatch with risk explanation.

2. Progressive trust.
   - Devices can be discovered before fully trusted.
   - Device states should include `discovered`, `paired`, `degraded`, `healthy`, `quarantined`, and `offline`.
   - Degraded devices may remain visible but should not receive high-trust tasks.

3. Structured failures.
   - Every install/self-check/taskpool failure should include stage, severity, code, likely causes, recommended action, escape hatch, and whether it is safe to continue.
   - Human-readable Chinese output and machine-readable JSON should share one underlying status contract.

4. DeviceTwin as cloud-brain UX primitive.
   - The cloud brain needs a per-device state record: id, name, host, last_seen, install_phase, auth_status, health, capabilities, degraded_reasons, escape_hatches_used, and taskpool_eligibility.

5. Capability-based task routing.
   - Dispatch should consider device health/capabilities/trust, not only online/offline.
   - Leases, heartbeats, and idempotent acks are required for recoverable task UX.

6. Recovery path over raw logs.
   - User-facing output should answer: what happened, why it likely happened, whether it is dangerous, what Hermes tried automatically, and what command/action comes next.

## Immediate Landing Boundary

Safe to implement now:
- Tests for TLS fallback branches and default-doc safety.
- Remove default documentation that recommends `curl -k | bash`.
- Deprecate `install-insecure.sh` as a silent insecure entrypoint.
- Patch reusable CLI installation skill with safe-default/escape-hatch pattern.
- Save compact durable user preference only if it prevents future over-hardening.

## Requires Design Before Code

Do not directly implement in core routing/auth without a separate design task:
- DeviceTwin schema and persistence.
- Pairing flow using one-time code / short-lived token / cloud confirmation.
- `hermes-edge diagnose --json` status contract.
- Capability-based taskpool routing.
- Lease + heartbeat + idempotent ack protocol.
- Red/yellow/green device health UI.

## Prohibited

- Silent TLS downgrade.
- Default docs using insecure install commands.
- Non-interactive insecure fallback without explicit env opt-in.
- Claiming multi-model certification when quorum failed or timed out.
- Letting unpaired/untrusted/degraded devices receive high-trust tasks.
- Infinite task retries without reason codes and visible recovery state.

## Taskpool Candidates

1. Edge Worker diagnose command
   - Artifact: `hermes-edge diagnose --json` plus human summary.
   - Verification: simulated DNS/TLS/token/port/main-node failures produce stable reason codes.
   - Risk: low/medium.

2. DeviceTwin design
   - Artifact: schema document and migration plan.
   - Verification: sample device lifecycle from discovered to healthy/degraded/offline.
   - Risk: medium.

3. Capability-based dispatch
   - Artifact: eligibility rules and taskpool routing proof.
   - Verification: degraded/insecure devices are visible but skipped for high-trust tasks.
   - Risk: medium/high.

4. Pairing UX
   - Artifact: one-time pairing code or short-lived token design.
   - Verification: pair/revoke/re-pair flows and audit events.
   - Risk: medium/high.

5. Task lease/heartbeat/idempotent ack
   - Artifact: protocol spec and executor changes.
   - Verification: worker crash/network split recovers without duplicate side effects.
   - Risk: high.

## Validation for This Boundary Landing

- `bash -n install.sh install-auto.sh install-final.sh install-insecure.sh verify-installation.sh`
- `PYTHONWARNINGS='ignore:urllib3 v2 only supports OpenSSL' /usr/bin/python3 -m pytest test_*.py -q`
- `python3 self_check.py`
- `/usr/bin/python3 architecture_link_check.py`
