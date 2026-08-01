"""Typed runtime-operations and incident-response contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class ComparisonOperator(StrEnum):
    """Supported SLI threshold comparisons."""

    GTE = "gte"
    LTE = "lte"
    EQ = "eq"


class AlertType(StrEnum):
    """Operational alert classifications."""

    AVAILABILITY_DEGRADATION = "AVAILABILITY_DEGRADATION"
    LATENCY_DEGRADATION = "LATENCY_DEGRADATION"
    AUTHORIZATION_VIOLATION = "AUTHORIZATION_VIOLATION"
    RECOVERY_OBJECTIVE_BREACH = "RECOVERY_OBJECTIVE_BREACH"
    DEPLOYMENT_REGRESSION = "DEPLOYMENT_REGRESSION"
    UNKNOWN = "UNKNOWN"


class IncidentSeverity(StrEnum):
    """Operational incident severity."""

    SEV_1 = "SEV_1"
    SEV_2 = "SEV_2"
    SEV_3 = "SEV_3"


class IncidentStatus(StrEnum):
    """Incident lifecycle state."""

    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    MITIGATION_RECOMMENDED = "MITIGATION_RECOMMENDED"
    ESCALATED = "ESCALATED"
    RECOVERED = "RECOVERED"


class ErrorBudgetStatus(StrEnum):
    """Error-budget state."""

    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    EXHAUSTED = "EXHAUSTED"


@dataclass(frozen=True)
class SLODefinition:
    """One service-level objective."""

    slo_id: str
    metric_name: str
    description: str
    comparison: ComparisonOperator
    threshold: float
    target_percentage: float


@dataclass(frozen=True)
class MetricSample:
    """One measured runtime signal."""

    metric_name: str
    value: float
    timestamp: str
    trace_id: str


@dataclass(frozen=True)
class SLOResult:
    """Evaluated SLI and error-budget result."""

    slo_id: str
    metric_name: str
    sample_count: int
    compliant_samples: int
    compliance_percentage: float
    target_percentage: float
    passed: bool
    error_budget_consumed: float
    error_budget_remaining: float
    error_budget_status: ErrorBudgetStatus


@dataclass(frozen=True)
class OperationalAlert:
    """Alert derived from runtime evidence."""

    alert_id: str
    alert_type: AlertType
    severity: IncidentSeverity
    slo_id: str
    metric_name: str
    summary: str
    evidence_references: tuple[str, ...]


@dataclass(frozen=True)
class IncidentRecord:
    """Operational incident record."""

    incident_id: str
    release_id: str
    environment: str
    severity: IncidentSeverity
    status: IncidentStatus
    alert_ids: tuple[str, ...]
    summary: str
    deployment_correlation: str
    human_escalation_required: bool


@dataclass(frozen=True)
class RunbookRecommendation:
    """Evidence-bound runbook recommendation."""

    incident_id: str
    runbook_path: str
    rationale: str
    automatic_execution_allowed: bool


@dataclass(frozen=True)
class MitigationRecommendation:
    """Recommended incident mitigation."""

    incident_id: str
    rollback_recommended: bool
    human_approval_required: bool
    rationale: str


@dataclass(frozen=True)
class RecoveryVerification:
    """Post-mitigation recovery evaluation."""

    incident_id: str
    recovered: bool
    recovered_slo_ids: tuple[str, ...]
    failed_slo_ids: tuple[str, ...]
    status: IncidentStatus


@dataclass(frozen=True)
class OperationsAuditEvent:
    """Immutable operations audit event."""

    sequence: int
    event_type: str
    incident_id: str
    detail: str
    evidence_references: tuple[str, ...] = ()


@dataclass(frozen=True)
class OperationsReport:
    """Complete runtime-operations report."""

    policy_version: str
    release_id: str
    environment: str
    normal_slo_results: tuple[SLOResult, ...]
    degraded_slo_results: tuple[SLOResult, ...]
    alerts: tuple[OperationalAlert, ...]
    incident: IncidentRecord | None
    runbook: RunbookRecommendation | None
    mitigation: MitigationRecommendation | None
    recovery: RecoveryVerification | None
    audit_events: tuple[OperationsAuditEvent, ...]
    automatic_remediation_performed: bool
    production_side_effects_performed: bool
    authority_boundary: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the report into a JSON-compatible mapping."""

        return asdict(self)
