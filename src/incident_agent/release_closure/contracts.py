"""Typed contracts for final release closure."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class ReleaseClosureDecision(StrEnum):
    READY_FOR_CONTROLLED_DEPLOYMENT = (
        "READY_FOR_CONTROLLED_DEPLOYMENT"
    )
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ReleaseCandidate:
    release_id: str
    release_version: str
    platform_contract_version: str
    source_branch: str
    candidate_status: str
    artifact_digest: str
    configuration_digest: str
    policy_digest: str
    domain_pack_digests: tuple[tuple[str, str], ...]
    target_environment: str
    deployment_performed: bool
    traffic_shift_performed: bool
    production_activation_performed: bool
    human_production_approval_required: bool
    immutable: bool
    manifest_digest: str


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    phase: int
    path: str
    required: bool
    validated: bool
    decision: str


@dataclass(frozen=True)
class ReleaseGate:
    gate_id: str
    passed: bool
    evidence_id: str


@dataclass(frozen=True)
class ResidualRisk:
    risk_id: str
    severity: str
    status: str
    mitigation: str


@dataclass(frozen=True)
class RecoveryCapability:
    capability: str
    verified: bool
    evidence: str
    automatic_execution: bool


@dataclass(frozen=True)
class AuthorityRestriction:
    restriction: str
    preserved: bool


@dataclass(frozen=True)
class ClosureMetrics:
    total_required_gates: int
    passed_required_gates: int
    gate_pass_rate_percentage: float
    total_required_evidence: int
    covered_required_evidence: int
    evidence_coverage_percentage: float
    open_critical_risks: int
    approved_exceptions: int
    verified_recovery_capabilities: int
    required_recovery_capabilities: int
    preserved_authority_restrictions: int
    required_authority_restrictions: int


@dataclass(frozen=True)
class ReleaseClosureReport:
    policy_version: str
    platform_contract_version: str
    release_train: str
    candidate: ReleaseCandidate
    evidence: tuple[EvidenceRecord, ...]
    gates: tuple[ReleaseGate, ...]
    residual_risks: tuple[ResidualRisk, ...]
    recovery_capabilities: tuple[RecoveryCapability, ...]
    authority_restrictions: tuple[AuthorityRestriction, ...]
    metrics: ClosureMetrics
    decision: ReleaseClosureDecision
    reasons: tuple[str, ...]
    automatic_release_approval_performed: bool
    automatic_deployment_performed: bool
    automatic_traffic_shift_performed: bool
    automatic_exception_approval_performed: bool
    automatic_risk_acceptance_performed: bool
    production_authority_transfer_performed: bool
    production_state_changed: bool
    authority_boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
