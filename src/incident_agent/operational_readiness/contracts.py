"""Typed contracts for operational readiness and handoff."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class ReadinessDecision(StrEnum):
    READY_FOR_CONTROLLED_RELEASE_CLOSURE = (
        "READY_FOR_CONTROLLED_RELEASE_CLOSURE"
    )
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class OwnershipAssignment:
    capability: str
    accountable_role: str
    responsible_role: str
    consulted_roles: tuple[str, ...]
    informed_roles: tuple[str, ...]


@dataclass(frozen=True)
class SupportTier:
    tier: str
    role: str
    responsibility: str
    may_execute_production_tools: bool


@dataclass(frozen=True)
class Runbook:
    runbook_id: str
    owner_role: str
    trigger: str
    first_action: str
    escalation_role: str
    production_mutation_allowed: bool


@dataclass(frozen=True)
class AccessControl:
    control_id: str
    implemented: bool
    detail: str


@dataclass(frozen=True)
class HandoffCheck:
    check_id: str
    category: str
    required: bool
    passed: bool
    evidence_id: str


@dataclass(frozen=True)
class ReadinessMetrics:
    total_required_checks: int
    passed_required_checks: int
    check_pass_rate_percentage: float
    required_owner_count: int
    covered_owner_count: int
    owner_coverage_percentage: float
    required_runbook_count: int
    covered_runbook_count: int
    runbook_coverage_percentage: float
    required_evidence_count: int
    covered_evidence_count: int
    evidence_coverage_percentage: float


@dataclass(frozen=True)
class OperationalReadinessReport:
    policy_version: str
    platform_contract_version: str
    ownership_model_id: str
    runbook_catalog_id: str
    checklist_id: str
    ownership_assignments: tuple[OwnershipAssignment, ...]
    support_tiers: tuple[SupportTier, ...]
    runbooks: tuple[Runbook, ...]
    access_controls: tuple[AccessControl, ...]
    handoff_checks: tuple[HandoffCheck, ...]
    metrics: ReadinessMetrics
    decision: ReadinessDecision
    reasons: tuple[str, ...]
    automatic_handoff_performed: bool
    automatic_access_provisioning_performed: bool
    automatic_owner_assignment_performed: bool
    automatic_production_activation_performed: bool
    credentials_created: bool
    access_granted: bool
    production_authority_transferred: bool
    authority_boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
