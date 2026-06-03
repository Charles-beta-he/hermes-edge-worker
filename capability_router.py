#!/usr/bin/env python3
"""
Capability-Based Task Router for Edge Devices

Routes tasks to edge workers based on capability matching, health scoring,
and load-aware selection. Integrates with multi_site_manager for worker
registration and task_event_driven for event-triggered routing.

Architecture position:
  Local Brain (SSOT) → CapabilityRouter → Edge Worker execution

Usage:
  from capability_router import CapabilityRouter, TaskRequirements

  router = CapabilityRouter()
  router.register_worker("pi-5", {"run_command", "python3"}, "http://192.168.1.5:9002")
  router.register_worker("mac-mini", {"run_command", "docker"}, "http://192.168.1.6:9002")

  reqs = TaskRequirements(required=["run_command"], preferred=["python3"])
  result = router.route(reqs)
  if result:
      print(f"Route to {result.worker_id} (score={result.score})")
"""

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CAPABILITY_PATTERN = re.compile(r"^[a-zA-Z0-9_./-]{1,128}$")
_MAX_CAPABILITIES_PER_WORKER = 256
_MAX_PREFERRED_CAPS = 32

# Scoring weights
_WEIGHT_PREFERRED = 0.2       # per preferred cap matched, capped at 1.0
_WEIGHT_HEALTH = 0.3          # health_score contribution
_WEIGHT_LOAD = 0.3            # (1 - load) contribution
_WEIGHT_AFFINITY = 1.0        # affinity bonus
_PENALTY_RECENT_FAILURE = 0.5 # penalty for recent task-type failure


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class WorkerStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    DRAINING = "draining"


@dataclass
class WorkerProfile:
    """Enriched worker profile with capabilities and health metrics."""
    worker_id: str
    url: str
    capabilities: Set[str]
    platform: str = "unknown"
    arch: str = "unknown"
    status: WorkerStatus = WorkerStatus.ONLINE
    load: float = 0.0            # 0.0 = idle, 1.0 = fully loaded
    health_score: float = 1.0    # 0.0 = unhealthy, 1.0 = perfect
    last_heartbeat: float = field(default_factory=time.time)
    registered_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Track recent failures by task_type
    failure_counts: Dict[str, int] = field(default_factory=dict)


@dataclass
class TaskRequirements:
    """What a task needs from a worker."""
    required: List[str] = field(default_factory=list)
    preferred: List[str] = field(default_factory=list)
    excluded: List[str] = field(default_factory=list)
    affinity: Optional[str] = None   # prefer this worker_id


@dataclass
class RoutingResult:
    """Outcome of a routing decision."""
    worker_id: str
    url: str
    score: float
    reason: str
    capabilities_matched: Set[str]
    capabilities_missing: Set[str]
    candidate_count: int


class RoutingFailureReason(str, Enum):
    NO_WORKERS = "no_workers"
    NO_MATCH = "no_match"
    ALL_OFFLINE = "all_offline"
    INVALID_REQUIREMENTS = "invalid_requirements"


@dataclass
class RoutingFailure:
    """Why routing failed."""
    reason: RoutingFailureReason
    detail: str = ""
    candidate_count: int = 0


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_capability(cap: str) -> bool:
    """Check a single capability string is safe and well-formed."""
    if not cap or not isinstance(cap, str):
        return False
    return bool(_CAPABILITY_PATTERN.match(cap))


def validate_capabilities(caps) -> Set[str]:
    """Validate and normalize a collection of capabilities. Returns clean set."""
    if isinstance(caps, str):
        caps = [caps]
    if not isinstance(caps, (list, set, frozenset)):
        return set()
    result = set()
    for c in caps:
        c = str(c).strip()
        if validate_capability(c):
            result.add(c)
    return result


# ---------------------------------------------------------------------------
# Core Router
# ---------------------------------------------------------------------------

class CapabilityRouter:
    """
    Routes tasks to edge workers based on capability matching.

    Thread-safety: all public methods are safe for single-threaded use.
    For multi-threaded deployment, wrap with a lock.
    """

    def __init__(self):
        self._workers: Dict[str, WorkerProfile] = {}

    # -- Worker lifecycle ---------------------------------------------------

    def register_worker(
        self,
        worker_id: str,
        capabilities,
        url: str = "",
        platform: str = "unknown",
        arch: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkerProfile:
        """
        Register or update a worker with its capabilities.
        If worker_id already exists, updates capabilities and metadata.
        """
        caps = validate_capabilities(capabilities)
        if len(caps) > _MAX_CAPABILITIES_PER_WORKER:
            raise ValueError(
                f"Too many capabilities ({len(caps)} > {_MAX_CAPABILITIES_PER_WORKER})"
            )

        if worker_id in self._workers:
            profile = self._workers[worker_id]
            profile.capabilities = caps
            profile.url = url or profile.url
            profile.platform = platform
            profile.arch = arch
            profile.status = WorkerStatus.ONLINE
            profile.last_heartbeat = time.time()
            if metadata:
                profile.metadata.update(metadata)
            return profile

        profile = WorkerProfile(
            worker_id=worker_id,
            url=url,
            capabilities=caps,
            platform=platform,
            arch=arch,
            metadata=metadata or {},
        )
        self._workers[worker_id] = profile
        return profile

    def unregister_worker(self, worker_id: str) -> bool:
        """Remove a worker from the registry. Returns True if existed."""
        return self._workers.pop(worker_id, None) is not None

    def update_worker_status(self, worker_id: str, status: str) -> bool:
        """Update worker status (online/offline/busy/draining)."""
        profile = self._workers.get(worker_id)
        if not profile:
            return False
        try:
            profile.status = WorkerStatus(status)
        except ValueError:
            return False
        return True

    def update_worker_health(
        self,
        worker_id: str,
        health_score: Optional[float] = None,
        load: Optional[float] = None,
    ) -> bool:
        """Update health/load metrics from heartbeat data."""
        profile = self._workers.get(worker_id)
        if not profile:
            return False
        if health_score is not None:
            profile.health_score = max(0.0, min(1.0, float(health_score)))
        if load is not None:
            profile.load = max(0.0, min(1.0, float(load)))
        profile.last_heartbeat = time.time()
        return True

    def record_task_failure(self, worker_id: str, task_type: str) -> None:
        """Record that a task type failed on this worker (for scoring penalty)."""
        profile = self._workers.get(worker_id)
        if profile:
            profile.failure_counts[task_type] = (
                profile.failure_counts.get(task_type, 0) + 1
            )

    def clear_task_failures(self, worker_id: str, task_type: str = None) -> None:
        """Clear failure counts (after successful execution)."""
        profile = self._workers.get(worker_id)
        if not profile:
            return
        if task_type:
            profile.failure_counts.pop(task_type, None)
        else:
            profile.failure_counts.clear()

    # -- Query --------------------------------------------------------------

    def get_worker(self, worker_id: str) -> Optional[WorkerProfile]:
        return self._workers.get(worker_id)

    def list_workers(self, status: Optional[str] = None) -> List[WorkerProfile]:
        workers = list(self._workers.values())
        if status:
            workers = [w for w in workers if w.status.value == status]
        return workers

    def get_capabilities(self, worker_id: str) -> Optional[Set[str]]:
        profile = self._workers.get(worker_id)
        return set(profile.capabilities) if profile else None

    def all_capabilities(self) -> Set[str]:
        """Union of all registered worker capabilities."""
        result = set()
        for w in self._workers.values():
            result.update(w.capabilities)
        return result

    # -- Routing ------------------------------------------------------------

    def route(
        self,
        requirements: TaskRequirements,
        task_type: str = "",
    ) -> Optional[RoutingResult]:
        """
        Route a task to the best-fit worker.

        Returns RoutingResult on success, None on failure.
        Call route_with_reason() for detailed failure info.
        """
        result = self.route_with_reason(requirements, task_type)
        return result if isinstance(result, RoutingResult) else None

    def route_with_reason(
        self,
        requirements: TaskRequirements,
        task_type: str = "",
    ) -> Any:  # RoutingResult | RoutingFailure
        """
        Route with detailed failure information.

        Algorithm:
        1. Filter to online workers with ALL required caps and NONE excluded caps.
        2. Score each candidate.
        3. If no exact match, try degraded match (ignore preferred, re-score).
        4. Return best or failure reason.
        """
        # Validate requirements
        req_caps = validate_capabilities(requirements.required)
        pref_caps = validate_capabilities(requirements.preferred)
        excl_caps = validate_capabilities(requirements.excluded)

        if len(pref_caps) > _MAX_PREFERRED_CAPS:
            return RoutingFailure(
                reason=RoutingFailureReason.INVALID_REQUIREMENTS,
                detail=f"Too many preferred capabilities ({len(pref_caps)})",
            )

        if not self._workers:
            return RoutingFailure(
                reason=RoutingFailureReason.NO_WORKERS,
                detail="No workers registered",
            )

        # Step 1: Filter candidates
        candidates = self._filter_candidates(req_caps, excl_caps)

        if not candidates:
            online_count = sum(
                1 for w in self._workers.values()
                if w.status in (WorkerStatus.ONLINE, WorkerStatus.BUSY)
            )
            if online_count == 0:
                return RoutingFailure(
                    reason=RoutingFailureReason.ALL_OFFLINE,
                    detail="No workers are online",
                    candidate_count=0,
                )
            return RoutingFailure(
                reason=RoutingFailureReason.NO_MATCH,
                detail=f"No worker has required capabilities: {req_caps}",
                candidate_count=0,
            )

        # Step 2: Score with preferred
        scored = [
            (w, self._score(w, req_caps, pref_caps, requirements.affinity, task_type))
            for w in candidates
        ]
        scored.sort(key=lambda x: (-x[1], x[0].load, -x[0].last_heartbeat, x[0].worker_id))

        best_worker, best_score = scored[0]
        best_caps = best_worker.capabilities

        return RoutingResult(
            worker_id=best_worker.worker_id,
            url=best_worker.url,
            score=round(best_score, 4),
            reason="exact_match" if req_caps and req_caps.issubset(best_caps) else "matched",
            capabilities_matched=req_caps & best_caps if req_caps else set(),
            capabilities_missing=req_caps - best_caps if req_caps else set(),
            candidate_count=len(candidates),
        )

    # -- Internal -----------------------------------------------------------

    def _filter_candidates(
        self,
        required_caps: Set[str],
        excluded_caps: Set[str],
    ) -> List[WorkerProfile]:
        """Filter workers by status, required caps, and excluded caps."""
        candidates = []
        for w in self._workers.values():
            # Must be online or busy (busy workers can still be routed to for queueing)
            if w.status not in (WorkerStatus.ONLINE, WorkerStatus.BUSY):
                continue
            # Must have ALL required capabilities
            if not required_caps.issubset(w.capabilities):
                continue
            # Must have NONE of excluded capabilities
            if excluded_caps and excluded_caps & w.capabilities:
                continue
            candidates.append(w)
        return candidates

    def _score(
        self,
        worker: WorkerProfile,
        required_caps: Set[str],
        preferred_caps: Set[str],
        affinity: Optional[str] = None,
        task_type: str = "",
    ) -> float:
        """
        Compute routing score for a worker.

        score = base_match
              + preferred_bonus (capped at 1.0)
              + health_bonus
              + load_bonus
              + affinity_bonus
              - failure_penalty
        """
        # Base: 1.0 if all required met (they should be, since we filtered)
        score = 1.0

        # Preferred bonus: +0.2 per preferred cap matched, capped at 1.0
        if preferred_caps:
            matched_preferred = len(preferred_caps & worker.capabilities)
            score += min(matched_preferred * _WEIGHT_PREFERRED, 1.0)

        # Health bonus
        score += worker.health_score * _WEIGHT_HEALTH

        # Load bonus (lower load = higher bonus)
        score += (1.0 - worker.load) * _WEIGHT_LOAD

        # Affinity bonus
        if affinity and worker.worker_id == affinity:
            score += _WEIGHT_AFFINITY

        # Failure penalty
        if task_type and worker.failure_counts.get(task_type, 0) > 0:
            score -= _PENALTY_RECENT_FAILURE

        return max(0.0, score)

    def get_routing_summary(self) -> Dict[str, Any]:
        """Return a summary of the routing state for observability."""
        workers = list(self._workers.values())
        return {
            "total_workers": len(workers),
            "online_workers": sum(1 for w in workers if w.status == WorkerStatus.ONLINE),
            "busy_workers": sum(1 for w in workers if w.status == WorkerStatus.BUSY),
            "offline_workers": sum(1 for w in workers if w.status == WorkerStatus.OFFLINE),
            "all_capabilities": sorted(self.all_capabilities()),
            "workers": {
                w.worker_id: {
                    "status": w.status.value,
                    "capabilities": sorted(w.capabilities),
                    "load": w.load,
                    "health_score": w.health_score,
                    "failure_counts": dict(w.failure_counts),
                }
                for w in workers
            },
        }
