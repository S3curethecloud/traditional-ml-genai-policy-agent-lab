"""Typed contracts for deterministic policy evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from incident_agent.genai.contracts import ToolRisk


class PolicyDecision(StrEnum):
    """Final deterministic policy outcome."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class PolicyIdentity:
    """Authenticated identity supplied by a trusted gateway."""

    user_id: str
    tenant_id: str
    roles: tuple[str, ...]


@dataclass(frozen=True)
class HumanApproval:
    """Externally issued human-approval evidence."""

    approval_id: str
    approver_id: str
    approver_role: str
    tenant_id: str
    service: str
    environment: str
    tool_name: str


@dataclass(frozen=True)
class ToolPolicy:
    """Deterministic policy for one registered tool."""

    tool_name: str
    risk: ToolRisk
    required_arguments: tuple[str, ...]
    allowed_roles: tuple[str, ...]
    allowed_environments: tuple[str, ...]
    minimum_citations: int
    requires_human_approval: bool
    required_approval_roles: tuple[str, ...]


@dataclass(frozen=True)
class PolicyContext:
    """Runtime context used to evaluate a tool recommendation."""

    identity: PolicyIdentity
    request_tenant_id: str
    service: str
    environment: str
    authorized_citations: tuple[str, ...]
    denied_document_ids: tuple[str, ...]
    classifiers_agree: bool
    ml_probability_margin: float
    approvals: tuple[HumanApproval, ...] = ()


@dataclass(frozen=True)
class PolicyReason:
    """One stable policy reason."""

    rule_id: str
    message: str


@dataclass(frozen=True)
class PolicyEvaluation:
    """Immutable deterministic policy-decision record."""

    decision: PolicyDecision
    tool_name: str | None
    reasons: tuple[PolicyReason, ...]
    policy_version: str
    request_fingerprint: str
    execution_performed: bool
    authority_boundary: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)
