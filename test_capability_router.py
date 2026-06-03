#!/usr/bin/env python3
"""
Tests for capability_router.py — Capability-Based Task Router.

Covers:
- Worker registration and lifecycle
- Capability validation
- Routing: exact match, partial match, no match, fallback
- Scoring: preferred caps, health, load, affinity, failure penalty
- Edge cases: empty registry, all offline, excluded caps, degraded match
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from capability_router import (
    CapabilityRouter,
    TaskRequirements,
    RoutingResult,
    RoutingFailure,
    RoutingFailureReason,
    WorkerProfile,
    WorkerStatus,
    validate_capability,
    validate_capabilities,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def router():
    return CapabilityRouter()


@pytest.fixture
def populated_router():
    """Router with 3 workers with different capabilities."""
    r = CapabilityRouter()
    r.register_worker("pi-5", {"run_command", "read_file", "write_file", "python3"}, url="http://192.168.1.5:9002", platform="linux", arch="aarch64")
    r.register_worker("mac-mini", {"run_command", "read_file", "write_file", "docker", "node", "python3"}, url="http://192.168.1.6:9002", platform="darwin", arch="x86_64")
    r.register_worker("ubuntu-box", {"run_command", "read_file", "docker", "gpu_inference"}, url="http://192.168.1.7:9002", platform="linux", arch="x86_64")
    return r


# ============================================================================
# Validation tests
# ============================================================================

class TestValidation:
    def test_valid_capability(self):
        assert validate_capability("run_command") is True
        assert validate_capability("python3") is True
        assert validate_capability("docker") is True
        assert validate_capability("gpu_inference") is True
        assert validate_capability("node/v18") is True
        assert validate_capability("path.to.module") is True

    def test_invalid_capability(self):
        assert validate_capability("") is False
        assert validate_capability(None) is False
        assert validate_capability(123) is False
        assert validate_capability("a" * 200) is False  # too long
        assert validate_capability("cap with spaces") is False
        assert validate_capability("cap;injection") is False
        assert validate_capability("cap$(cmd)") is False

    def test_validate_capabilities_list(self):
        caps = validate_capabilities(["run_command", "python3", "bad;cap", ""])
        assert caps == {"run_command", "python3"}

    def test_validate_capabilities_string(self):
        caps = validate_capabilities("run_command")
        assert caps == {"run_command"}

    def test_validate_capabilities_set(self):
        caps = validate_capabilities({"docker", "node"})
        assert caps == {"docker", "node"}

    def test_validate_capabilities_none(self):
        assert validate_capabilities(None) == set()

    def test_validate_capabilities_invalid_type(self):
        assert validate_capabilities(123) == set()


# ============================================================================
# Worker registration tests
# ============================================================================

class TestWorkerRegistration:
    def test_register_new_worker(self, router):
        profile = router.register_worker("w1", {"run_command"}, url="http://localhost:9002")
        assert profile.worker_id == "w1"
        assert profile.capabilities == {"run_command"}
        assert profile.url == "http://localhost:9002"
        assert profile.status == WorkerStatus.ONLINE

    def test_register_updates_existing(self, router):
        router.register_worker("w1", {"run_command"}, url="http://localhost:9002")
        profile = router.register_worker("w1", {"run_command", "docker"}, url="http://localhost:9003")
        assert profile.capabilities == {"run_command", "docker"}
        assert profile.url == "http://localhost:9003"

    def test_register_too_many_capabilities(self, router):
        caps = {f"cap_{i}" for i in range(300)}
        with pytest.raises(ValueError, match="Too many capabilities"):
            router.register_worker("w1", caps)

    def test_unregister(self, router):
        router.register_worker("w1", {"run_command"})
        assert router.unregister_worker("w1") is True
        assert router.get_worker("w1") is None

    def test_unregister_nonexistent(self, router):
        assert router.unregister_worker("nope") is False

    def test_update_status(self, router):
        router.register_worker("w1", {"run_command"})
        assert router.update_worker_status("w1", "offline") is True
        assert router.get_worker("w1").status == WorkerStatus.OFFLINE

    def test_update_status_invalid(self, router):
        router.register_worker("w1", {"run_command"})
        assert router.update_worker_status("w1", "bogus") is False

    def test_update_status_nonexistent(self, router):
        assert router.update_worker_status("nope", "online") is False

    def test_update_health(self, router):
        router.register_worker("w1", {"run_command"})
        assert router.update_worker_health("w1", health_score=0.8, load=0.5) is True
        w = router.get_worker("w1")
        assert w.health_score == 0.8
        assert w.load == 0.5

    def test_update_health_clamps_values(self, router):
        router.register_worker("w1", {"run_command"})
        router.update_worker_health("w1", health_score=2.0, load=-0.5)
        w = router.get_worker("w1")
        assert w.health_score == 1.0
        assert w.load == 0.0

    def test_update_health_nonexistent(self, router):
        assert router.update_worker_health("nope", health_score=1.0) is False


# ============================================================================
# Query tests
# ============================================================================

class TestQuery:
    def test_list_workers_all(self, populated_router):
        assert len(populated_router.list_workers()) == 3

    def test_list_workers_by_status(self, populated_router):
        populated_router.update_worker_status("pi-5", "offline")
        online = populated_router.list_workers(status="online")
        assert len(online) == 2
        offline = populated_router.list_workers(status="offline")
        assert len(offline) == 1

    def test_get_capabilities(self, populated_router):
        caps = populated_router.get_capabilities("mac-mini")
        assert "docker" in caps
        assert "python3" in caps

    def test_get_capabilities_nonexistent(self, populated_router):
        assert populated_router.get_capabilities("nope") is None

    def test_all_capabilities(self, populated_router):
        all_caps = populated_router.all_capabilities()
        assert "run_command" in all_caps
        assert "docker" in all_caps
        assert "gpu_inference" in all_caps


# ============================================================================
# Routing tests
# ============================================================================

class TestRouting:
    def test_route_empty_registry(self, router):
        reqs = TaskRequirements(required=["run_command"])
        result = router.route(reqs)
        assert result is None

    def test_route_exact_match_single(self, router):
        router.register_worker("w1", {"run_command", "python3"}, url="http://w1:9002")
        reqs = TaskRequirements(required=["run_command", "python3"])
        result = router.route(reqs)
        assert result is not None
        assert result.worker_id == "w1"
        assert "exact_match" in result.reason

    def test_route_picks_correct_worker(self, populated_router):
        """Only mac-mini and ubuntu-box have docker."""
        reqs = TaskRequirements(required=["run_command", "docker"])
        result = populated_router.route(reqs)
        assert result is not None
        assert result.worker_id in ("mac-mini", "ubuntu-box")

    def test_route_no_match_missing_capability(self, populated_router):
        reqs = TaskRequirements(required=["run_command", "gpu_inference", "quantum_computing"])
        result = populated_router.route(reqs)
        assert result is None

    def test_route_all_offline(self, populated_router):
        for w in populated_router.list_workers():
            populated_router.update_worker_status(w.worker_id, "offline")
        reqs = TaskRequirements(required=["run_command"])
        result = populated_router.route(reqs)
        assert result is None

    def test_route_excluded_capability(self, populated_router):
        """ubuntu-box has gpu_inference; if excluded, it should not be selected."""
        reqs = TaskRequirements(
            required=["run_command", "docker"],
            excluded=["gpu_inference"],
        )
        result = populated_router.route(reqs)
        assert result is not None
        assert result.worker_id == "mac-mini"  # only mac-mini has docker without gpu_inference

    def test_route_with_affinity(self, populated_router):
        reqs = TaskRequirements(required=["run_command"], affinity="pi-5")
        result = populated_router.route(reqs)
        assert result is not None
        assert result.worker_id == "pi-5"

    def test_route_affinity_worker_unavailable(self, populated_router):
        """If affinity worker is offline, fall back to best available."""
        populated_router.update_worker_status("pi-5", "offline")
        reqs = TaskRequirements(required=["run_command"], affinity="pi-5")
        result = populated_router.route(reqs)
        assert result is not None
        assert result.worker_id != "pi-5"

    def test_route_preferred_caps_boost_score(self, populated_router):
        """mac-mini has python3 + docker; ubuntu-box has docker but not python3.
        Task prefers python3 → mac-mini should win."""
        reqs = TaskRequirements(required=["run_command", "docker"], preferred=["python3"])
        result = populated_router.route(reqs)
        assert result is not None
        assert result.worker_id == "mac-mini"

    def test_route_no_required_caps(self, populated_router):
        """No required caps → all online workers are candidates."""
        reqs = TaskRequirements(preferred=["docker"])
        result = populated_router.route(reqs)
        assert result is not None

    def test_route_with_reason_no_workers(self, router):
        reqs = TaskRequirements(required=["run_command"])
        result = router.route_with_reason(reqs)
        assert isinstance(result, RoutingFailure)
        assert result.reason == RoutingFailureReason.NO_WORKERS

    def test_route_with_reason_no_match(self, populated_router):
        reqs = TaskRequirements(required=["nonexistent_cap"])
        result = populated_router.route_with_reason(reqs)
        assert isinstance(result, RoutingFailure)
        assert result.reason == RoutingFailureReason.NO_MATCH

    def test_route_with_reason_all_offline(self, populated_router):
        for w in populated_router.list_workers():
            populated_router.update_worker_status(w.worker_id, "offline")
        reqs = TaskRequirements(required=["run_command"])
        result = populated_router.route_with_reason(reqs)
        assert isinstance(result, RoutingFailure)
        assert result.reason == RoutingFailureReason.ALL_OFFLINE

    def test_route_result_fields(self, populated_router):
        reqs = TaskRequirements(required=["run_command", "docker"])
        result = populated_router.route(reqs)
        assert isinstance(result, RoutingResult)
        assert result.candidate_count >= 1
        assert "run_command" in result.capabilities_matched
        assert "docker" in result.capabilities_matched
        assert len(result.capabilities_missing) == 0


# ============================================================================
# Scoring tests
# ============================================================================

class TestScoring:
    def test_health_affects_score(self, populated_router):
        """Lower health → lower score."""
        populated_router.update_worker_health("mac-mini", health_score=0.1)
        populated_router.update_worker_health("ubuntu-box", health_score=0.9)
        reqs = TaskRequirements(required=["run_command", "docker"])
        result = populated_router.route(reqs)
        assert result is not None
        assert result.worker_id == "ubuntu-box"

    def test_load_affects_score(self, populated_router):
        """Higher load → lower score."""
        populated_router.update_worker_health("mac-mini", load=0.9)
        populated_router.update_worker_health("ubuntu-box", load=0.1)
        reqs = TaskRequirements(required=["run_command", "docker"])
        result = populated_router.route(reqs)
        assert result is not None
        assert result.worker_id == "ubuntu-box"

    def test_failure_penalty(self, populated_router):
        """Recent failure → penalty applied."""
        populated_router.record_task_failure("mac-mini", "code_generation")
        populated_router.update_worker_health("mac-mini", health_score=1.0, load=0.0)
        populated_router.update_worker_health("ubuntu-box", health_score=1.0, load=0.0)
        reqs = TaskRequirements(required=["run_command", "docker"])
        result = populated_router.route(reqs, task_type="code_generation")
        assert result is not None
        assert result.worker_id == "ubuntu-box"

    def test_clear_failures(self, populated_router):
        populated_router.record_task_failure("mac-mini", "code_generation")
        populated_router.clear_task_failures("mac-mini", "code_generation")
        w = populated_router.get_worker("mac-mini")
        assert w.failure_counts.get("code_generation", 0) == 0

    def test_clear_all_failures(self, populated_router):
        populated_router.record_task_failure("mac-mini", "t1")
        populated_router.record_task_failure("mac-mini", "t2")
        populated_router.clear_task_failures("mac-mini")
        w = populated_router.get_worker("mac-mini")
        assert len(w.failure_counts) == 0

    def test_score_never_negative(self, populated_router):
        """Even with heavy penalties, score should not go below 0."""
        for _ in range(100):
            populated_router.record_task_failure("mac-mini", "t")
        reqs = TaskRequirements(required=["run_command", "docker"])
        result = populated_router.route(reqs, task_type="t")
        assert result is not None
        assert result.score >= 0.0


# ============================================================================
# Edge case tests
# ============================================================================

class TestEdgeCases:
    def test_busy_worker_is_routable(self, populated_router):
        """Busy workers should still be candidates (for queueing)."""
        populated_router.update_worker_status("mac-mini", "busy")
        populated_router.update_worker_status("ubuntu-box", "offline")
        reqs = TaskRequirements(required=["run_command", "docker"])
        result = populated_router.route(reqs)
        assert result is not None
        assert result.worker_id == "mac-mini"

    def test_draining_worker_excluded(self, populated_router):
        """Draining workers should not be routed to."""
        populated_router.update_worker_status("mac-mini", "draining")
        populated_router.update_worker_status("ubuntu-box", "offline")
        reqs = TaskRequirements(required=["run_command", "docker"])
        result = populated_router.route(reqs)
        assert result is None

    def test_routing_summary(self, populated_router):
        summary = populated_router.get_routing_summary()
        assert summary["total_workers"] == 3
        assert summary["online_workers"] == 3
        assert "run_command" in summary["all_capabilities"]

    def test_register_worker_with_string_caps(self, router):
        """Capabilities can be passed as a single string."""
        profile = router.register_worker("w1", "run_command")
        assert "run_command" in profile.capabilities

    def test_route_empty_requirements(self, populated_router):
        """Empty requirements should route to any online worker."""
        reqs = TaskRequirements()
        result = populated_router.route(reqs)
        assert result is not None

    def test_route_too_many_preferred(self, populated_router):
        """Should reject requests with too many preferred caps."""
        reqs = TaskRequirements(
            required=["run_command"],
            preferred=[f"cap_{i}" for i in range(50)],
        )
        result = populated_router.route_with_reason(reqs)
        assert isinstance(result, RoutingFailure)
        assert result.reason == RoutingFailureReason.INVALID_REQUIREMENTS

    def test_tie_breaking_by_load(self, router):
        """When scores are equal, lower load wins."""
        router.register_worker("w1", {"run_command"}, url="http://w1:9002")
        router.register_worker("w2", {"run_command"}, url="http://w2:9002")
        router.update_worker_health("w1", load=0.8)
        router.update_worker_health("w2", load=0.2)
        reqs = TaskRequirements(required=["run_command"])
        result = router.route(reqs)
        assert result is not None
        assert result.worker_id == "w2"
