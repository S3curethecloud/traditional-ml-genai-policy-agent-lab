"""Typed deployment-runtime and promotion contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class DeploymentEnvironment(StrEnum):
    """Supported deployment environments."""

    STAGING = "staging"
    PRODUCTION = "production"


class DeploymentStatus(StrEnum):
    """Deployment lifecycle status."""

    PENDING = "PENDING"
    PREFLIGHT_PASSED = "PREFLIGHT_PASSED"
    DEPLOYED = "DEPLOYED"
    HEALTHY = "HEALTHY"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class DeploymentDecision(StrEnum):
    """Deployment authorization result."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class DriftStatus(StrEnum):
    """Configuration-drift status."""

    IN_SYNC = "IN_SYNC"
    DRIFTED = "DRIFTED"


@dataclass(frozen=True)
class DeploymentIdentity:
    """Identity requesting deployment execution."""

    subject_id: str
    roles: tuple[str, ...]
    allowed_environments: tuple[str, ...]


@dataclass(frozen=True)
class EnvironmentConfiguration:
    """Validated environment overlay."""

    environment: DeploymentEnvironment
    replica_count: int
    maximum_concurrent_workflows: int
    request_timeout_seconds: float
    provider_timeout_seconds: float
    health_failure_threshold: int
    require_human_approval: bool
    allow_deployment_simulation: bool
    production_side_effects_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DeploymentManifest:
    """Immutable deployment intent."""

    manifest_version: str
    release_id: str
    application_name: str
    image_repository: str
    image_digest: str
    source_revision: str
    model_version: str
    prompt_version: str
    policy_version: str
    runtime_version: str
    orchestrator_version: str
    evaluation_version: str
    supply_chain_policy_version: str
    required_handoff_path: str
    rollback_plan_path: str
    health_endpoint: str
    readiness_endpoint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DeploymentApproval:
    """Explicit environment deployment approval."""

    approval_id: str
    release_id: str
    environment: DeploymentEnvironment
    approver_id: str
    approved: bool
    evidence_sha256: str


@dataclass(frozen=True)
class PreflightCheck:
    """One deployment preflight check."""

    check_name: str
    passed: bool
    explanation: str


@dataclass(frozen=True)
class DeploymentAuthorization:
    """Authorization decision before runtime execution."""

    decision: DeploymentDecision
    checks: tuple[PreflightCheck, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeState:
    """Simulated deployed runtime state."""

    environment: DeploymentEnvironment
    release_id: str
    image_digest: str
    source_revision: str
    replica_count: int
    configuration_sha256: str
    deployed_by: str
    healthy: bool
    ready: bool


@dataclass(frozen=True)
class DriftReport:
    """Desired-versus-observed runtime comparison."""

    status: DriftStatus
    differences: tuple[str, ...]


@dataclass(frozen=True)
class DeploymentAuditEvent:
    """Immutable deployment audit event."""

    sequence: int
    event_type: str
    release_id: str
    environment: str
    actor_id: str
    detail: str
    evidence_references: tuple[str, ...] = ()


@dataclass(frozen=True)
class DeploymentOutcome:
    """Complete deployment execution outcome."""

    release_id: str
    environment: DeploymentEnvironment
    status: DeploymentStatus
    authorization_decision: DeploymentDecision
    runtime_state: RuntimeState | None
    drift_report: DriftReport | None
    audit_events: tuple[DeploymentAuditEvent, ...]
    rollback_performed: bool
    production_side_effects_performed: bool
    authority_boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
