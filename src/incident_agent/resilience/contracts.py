"""Typed resilience, chaos, and disaster-recovery contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class FailureType(StrEnum):
    """Supported controlled failure scenarios."""

    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    RETRIEVAL_UNAVAILABLE = "RETRIEVAL_UNAVAILABLE"
    POLICY_ENGINE_UNAVAILABLE = "POLICY_ENGINE_UNAVAILABLE"
    RUNTIME_SATURATION = "RUNTIME_SATURATION"
    REGIONAL_FAILURE = "REGIONAL_FAILURE"
    CHECKPOINT_CORRUPTION = "CHECKPOINT_CORRUPTION"


class FailureImpact(StrEnum):
    """Operational impact classification."""

    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    DISASTER = "DISASTER"


class ResilienceDecision(StrEnum):
    """Resilience decision result."""

    CONTINUE_DEGRADED = "CONTINUE_DEGRADED"
    STOP_SAFELY = "STOP_SAFELY"
    REQUIRE_FAILOVER_APPROVAL = "REQUIRE_FAILOVER_APPROVAL"
    FAILOVER_ALLOWED = "FAILOVER_ALLOWED"
    RESTORE_REQUIRED = "RESTORE_REQUIRED"


class RecoveryStatus(StrEnum):
    """Recovery lifecycle result."""

    NOT_STARTED = "NOT_STARTED"
    RECOVERED = "RECOVERED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ChaosScenario:
    """One deterministic chaos scenario."""

    scenario_id: str
    failure_type: FailureType
    target_component: str
    affected_region: str | None
    injected: bool


@dataclass(frozen=True)
class FailureAssessment:
    """Classified failure impact."""

    failure_type: FailureType
    impact: FailureImpact
    safe_to_continue: bool
    authority_expansion_detected: bool
    explanation: str


@dataclass(frozen=True)
class FailoverAuthorization:
    """Human authorization for failover."""

    authorization_id: str
    release_id: str
    source_region: str
    target_region: str
    approved: bool
    approver_id: str
    evidence_sha256: str


@dataclass(frozen=True)
class ResilienceAction:
    """Governed resilience action."""

    decision: ResilienceDecision
    action_name: str
    human_authorization_required: bool
    automatic_execution_allowed: bool
    explanation: str


@dataclass(frozen=True)
class CheckpointRecord:
    """Recoverable workflow checkpoint."""

    checkpoint_id: str
    workflow_id: str
    sequence: int
    state_sha256: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class BackupRecord:
    """Backup evidence record."""

    backup_id: str
    release_id: str
    created_epoch_seconds: int
    source_state_sha256: str
    backup_sha256: str
    path: str


@dataclass(frozen=True)
class RPOResult:
    """Recovery-point-objective result."""

    observed_seconds: int
    objective_seconds: int
    passed: bool


@dataclass(frozen=True)
class RTOResult:
    """Recovery-time-objective result."""

    observed_seconds: int
    objective_seconds: int
    passed: bool


@dataclass(frozen=True)
class RecoveryVerification:
    """Post-recovery consistency evidence."""

    status: RecoveryStatus
    source_state_sha256: str
    restored_state_sha256: str
    state_consistent: bool
    replay_verified: bool
    authority_boundary_preserved: bool


@dataclass(frozen=True)
class ResilienceAuditEvent:
    """Immutable resilience audit event."""

    sequence: int
    event_type: str
    scenario_id: str
    detail: str
    evidence_references: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResilienceReport:
    """Complete Phase 14 evidence report."""

    policy_version: str
    release_id: str
    scenarios: tuple[ChaosScenario, ...]
    assessments: tuple[FailureAssessment, ...]
    actions: tuple[ResilienceAction, ...]
    backup: BackupRecord
    rpo: RPOResult
    rto: RTOResult
    recovery: RecoveryVerification
    audit_events: tuple[ResilienceAuditEvent, ...]
    automatic_failover_performed: bool
    real_infrastructure_changes_performed: bool
    authority_boundary: str

    def to_dict(self) -> dict[str, Any]:
        """Convert report to JSON-compatible form."""

        return asdict(self)
