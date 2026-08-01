"""Typed contracts for adversarial validation and compliance evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class AttackOutcome(StrEnum):
    BLOCKED = "BLOCKED"
    DENIED = "DENIED"
    REJECTED = "REJECTED"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    ALLOWED = "ALLOWED"


class ValidationStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class RiskSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AttestationStatus(StrEnum):
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class AdversarialCase:
    case_id: str
    category: str
    target_control: str
    attack_payload: str
    expected_outcome: AttackOutcome
    evidence_reference: str


@dataclass(frozen=True)
class AdversarialResult:
    case_id: str
    category: str
    target_control: str
    expected_outcome: AttackOutcome
    observed_outcome: AttackOutcome
    status: ValidationStatus
    explanation: str
    evidence_reference: str


@dataclass(frozen=True)
class ComplianceControl:
    control_id: str
    control_name: str
    framework_mappings: tuple[str, ...]
    evidence_references: tuple[str, ...]


@dataclass(frozen=True)
class ControlCoverageResult:
    total_controls: int
    covered_controls: int
    coverage_percentage: float
    passed: bool


@dataclass(frozen=True)
class ResidualRisk:
    risk_id: str
    title: str
    severity: RiskSeverity
    status: str
    description: str
    treatment: str
    exception_approved: bool


@dataclass(frozen=True)
class SecurityAttestation:
    attestation_id: str
    policy_version: str
    attack_block_rate_percentage: float
    control_coverage_percentage: float
    open_critical_risks: int
    status: AttestationStatus
    reasons: tuple[str, ...]
    automatic_exception_approval_performed: bool
    automatic_remediation_performed: bool


@dataclass(frozen=True)
class SecurityAuditEvent:
    sequence: int
    event_type: str
    detail: str
    evidence_references: tuple[str, ...] = ()


@dataclass(frozen=True)
class SecurityValidationReport:
    policy_version: str
    suite_id: str
    adversarial_results: tuple[AdversarialResult, ...]
    control_coverage: ControlCoverageResult
    residual_risks: tuple[ResidualRisk, ...]
    attestation: SecurityAttestation
    audit_events: tuple[SecurityAuditEvent, ...]
    automatic_exception_approval_performed: bool
    automatic_remediation_performed: bool
    production_changes_performed: bool
    authority_boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
