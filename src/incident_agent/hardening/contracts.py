"""Typed contracts for production hardening and release control."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class ReadinessStatus(StrEnum):
    """Deployment-readiness status."""

    READY = "READY"
    BLOCKED = "BLOCKED"


class PromotionDecision(StrEnum):
    """Environment-promotion decision."""

    APPROVE = "APPROVE"
    REJECT = "REJECT"


class CircuitState(StrEnum):
    """Circuit-breaker state."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class HardeningErrorCode(StrEnum):
    """Stable production-hardening error codes."""

    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
    INLINE_SECRET_DETECTED = "INLINE_SECRET_DETECTED"
    SECRET_REFERENCE_MISSING = "SECRET_REFERENCE_MISSING"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    CONCURRENCY_LIMIT_EXCEEDED = (
        "CONCURRENCY_LIMIT_EXCEEDED"
    )
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    RELEASE_GATE_FAILED = "RELEASE_GATE_FAILED"
    ATTESTATION_INVALID = "ATTESTATION_INVALID"
    PROMOTION_PATH_INVALID = "PROMOTION_PATH_INVALID"
    ROLLBACK_PLAN_MISSING = "ROLLBACK_PLAN_MISSING"


@dataclass(frozen=True)
class ProductionConfiguration:
    """Validated production configuration."""

    configuration_version: str
    environment: str
    model_provider: str
    model_name: str
    model_version: str
    prompt_version: str
    policy_version: str
    runtime_version: str
    orchestrator_version: str
    evaluation_version: str
    request_timeout_seconds: float
    provider_timeout_seconds: float
    maximum_requests_per_window: int
    rate_limit_window_seconds: float
    maximum_concurrent_workflows: int
    circuit_breaker_failure_threshold: int
    circuit_breaker_recovery_seconds: float
    minimum_release_evidence_artifacts: int
    require_release_gate_pass: bool
    require_signed_attestation: bool
    require_rollback_plan: bool
    allowed_promotion_sources: tuple[str, ...]
    allowed_promotion_targets: tuple[str, ...]
    secret_references: tuple[str, ...]
    prohibited_inline_secret_fields: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)


@dataclass(frozen=True)
class HardeningError:
    """Structured hardening rejection."""

    code: HardeningErrorCode
    message: str


@dataclass(frozen=True)
class StructuredLogEvent:
    """Redacted structured operational event."""

    event_type: str
    trace_id: str
    workflow_id: str
    severity: str
    attributes: dict[str, Any]


@dataclass(frozen=True)
class ReleaseAttestation:
    """Signed release-evidence attestation."""

    release_id: str
    source_environment: str
    target_environment: str
    evidence_sha256: str
    configuration_sha256: str
    rollback_plan_id: str
    signer_id: str
    signature_algorithm: str
    signature: str


@dataclass(frozen=True)
class PromotionEvaluation:
    """Environment-promotion decision."""

    decision: PromotionDecision
    reasons: tuple[str, ...]
    release_id: str
    source_environment: str
    target_environment: str
    evidence_sha256: str
    readiness_status: ReadinessStatus

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)


@dataclass(frozen=True)
class ReadinessCheck:
    """One deployment-readiness check."""

    check_name: str
    passed: bool
    explanation: str


@dataclass(frozen=True)
class DeploymentReadinessReport:
    """Aggregate production-readiness report."""

    release_id: str
    status: ReadinessStatus
    checks: tuple[ReadinessCheck, ...]
    passed_count: int
    failed_count: int
    hardening_version: str
    authority_boundary: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)
