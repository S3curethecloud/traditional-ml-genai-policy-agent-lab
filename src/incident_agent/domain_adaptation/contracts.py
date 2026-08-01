"""Typed contracts for reusable domain adaptation packs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class PackValidationStatus(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"


class AdaptationDecision(StrEnum):
    READY_FOR_INTEGRATION = "READY_FOR_INTEGRATION"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class IncidentCategory:
    category_id: str
    display_name: str
    default_severity: str


@dataclass(frozen=True)
class EvidenceSource:
    source_id: str
    source_type: str
    tenant_scoped: bool
    required_roles: tuple[str, ...]


@dataclass(frozen=True)
class DomainTool:
    tool_name: str
    risk: str
    mutating: bool
    allowed_environments: tuple[str, ...]
    required_approval: bool


@dataclass(frozen=True)
class DomainPack:
    pack_id: str
    pack_version: str
    platform_contract_version: str
    status: str
    owner: str
    domain_name: str
    description: str
    tenant_isolation_required: bool
    regulated_data: bool
    supported_capabilities: tuple[str, ...]
    incident_categories: tuple[IncidentCategory, ...]
    evidence_sources: tuple[EvidenceSource, ...]
    tools: tuple[DomainTool, ...]
    may_narrow_platform_policy: bool
    may_expand_platform_policy: bool
    deny_cross_tenant_access: bool
    deny_unapproved_production_mutation: bool
    deny_direct_genai_tool_execution: bool
    required_evaluation_cases: tuple[str, ...]
    minimum_pass_rate_percentage: float
    allowed_deployment_environments: tuple[str, ...]
    production_activation_requires_human_approval: bool
    automatic_activation: bool
    domain_pack_can_execute_tools: bool
    domain_pack_can_modify_platform_policy: bool
    domain_pack_can_approve_exceptions: bool
    domain_pack_can_activate_itself: bool
    digest: str


@dataclass(frozen=True)
class PackFinding:
    rule_id: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class PackValidationResult:
    pack_id: str
    status: PackValidationStatus
    findings: tuple[PackFinding, ...]
    digest: str


@dataclass(frozen=True)
class DomainComparison:
    reference_pack_id: str
    candidate_pack_id: str
    shared_capabilities: tuple[str, ...]
    reference_only_capabilities: tuple[str, ...]
    candidate_only_capabilities: tuple[str, ...]
    shared_tool_names: tuple[str, ...]
    isolated_taxonomies: bool
    isolated_evidence_sources: bool


@dataclass(frozen=True)
class AdaptationReport:
    policy_version: str
    platform_contract_version: str
    packs: tuple[DomainPack, ...]
    validation_results: tuple[PackValidationResult, ...]
    comparison: DomainComparison
    decision: AdaptationDecision
    reasons: tuple[str, ...]
    automatic_pack_activation_performed: bool
    automatic_policy_mutation_performed: bool
    automatic_tool_registration_performed: bool
    production_changes_performed: bool
    authority_boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
