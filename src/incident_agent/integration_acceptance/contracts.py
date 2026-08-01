"""Typed contracts for platform integration acceptance."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class AcceptanceOutcome(StrEnum):
    COMPLETED = "COMPLETED"
    DENIED = "DENIED"
    ESCALATED = "ESCALATED"
    ABSTAINED = "ABSTAINED"
    REJECTED = "REJECTED"


class ScenarioStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class PlatformAcceptanceDecision(StrEnum):
    ACCEPTED_FOR_OPERATIONAL_READINESS = (
        "ACCEPTED_FOR_OPERATIONAL_READINESS"
    )
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class AcceptanceScenario:
    scenario_id: str
    domain: str
    scenario_type: str
    tenant_id: str
    actor_role: str
    incident_category: str
    authorized_evidence_available: bool
    prompt_injection_detected: bool
    cross_tenant_attempt: bool
    policy_fingerprint_valid: bool
    tool_name: str
    tool_mutating: bool
    human_approval_present: bool
    expected_outcome: AcceptanceOutcome


@dataclass(frozen=True)
class StageEvidence:
    stage: str
    executed: bool
    evidence_id: str
    detail: str


@dataclass(frozen=True)
class AcceptanceScenarioResult:
    scenario_id: str
    domain: str
    scenario_type: str
    expected_outcome: AcceptanceOutcome
    observed_outcome: AcceptanceOutcome
    status: ScenarioStatus
    stages: tuple[StageEvidence, ...]
    runtime_executed: bool
    real_side_effect_performed: bool
    explanation: str


@dataclass(frozen=True)
class AcceptanceMetrics:
    total_scenarios: int
    passed_scenarios: int
    scenario_pass_rate_percentage: float
    required_stage_count: int
    covered_stage_count: int
    stage_coverage_percentage: float
    evidence_continuity_percentage: float


@dataclass(frozen=True)
class PlatformAcceptanceReport:
    policy_version: str
    platform_contract_version: str
    suite_id: str
    scenario_results: tuple[AcceptanceScenarioResult, ...]
    metrics: AcceptanceMetrics
    decision: PlatformAcceptanceDecision
    reasons: tuple[str, ...]
    automatic_acceptance_approval_performed: bool
    automatic_exception_approval_performed: bool
    automatic_remediation_performed: bool
    production_execution_performed: bool
    authority_boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
