"""Typed progressive-delivery and rollback-governance contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class GateStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class PromotionDecision(StrEnum):
    ALLOW = "ALLOW"
    PAUSE = "PAUSE"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    ROLLBACK = "ROLLBACK"


class ReleaseStatus(StrEnum):
    REGISTERED = "REGISTERED"
    CANARY = "CANARY"
    PROGRESSING = "PROGRESSING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ROLLED_BACK = "ROLLED_BACK"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ReleaseCandidate:
    release_id: str
    application_name: str
    candidate_version: str
    previous_version: str
    source_revision: str
    image_digest: str
    target_environment: str
    deployment_report_path: str
    operations_report_path: str
    resilience_report_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromotionApproval:
    approval_id: str
    release_id: str
    from_percentage: int
    to_percentage: int
    approver_id: str
    approved: bool
    evidence_sha256: str


@dataclass(frozen=True)
class ReleaseGate:
    gate_name: str
    status: GateStatus
    explanation: str
    evidence_reference: str


@dataclass(frozen=True)
class PromotionEvaluation:
    from_percentage: int
    to_percentage: int
    decision: PromotionDecision
    gates: tuple[ReleaseGate, ...]
    reasons: tuple[str, ...]
    human_approval_required: bool


@dataclass(frozen=True)
class TrafficState:
    release_id: str
    candidate_version: str
    previous_version: str
    candidate_percentage: int
    previous_percentage: int
    real_traffic_shift_performed: bool


@dataclass(frozen=True)
class RollbackRecord:
    release_id: str
    from_version: str
    restored_version: str
    reason: str
    authorized: bool
    completed: bool
    real_traffic_shift_performed: bool


@dataclass(frozen=True)
class ReleaseAuditEvent:
    sequence: int
    event_type: str
    release_id: str
    detail: str
    evidence_references: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProgressiveDeliveryReport:
    policy_version: str
    release_candidate: ReleaseCandidate
    evaluations: tuple[PromotionEvaluation, ...]
    traffic_states: tuple[TrafficState, ...]
    rollback: RollbackRecord
    audit_events: tuple[ReleaseAuditEvent, ...]
    final_status: ReleaseStatus
    automatic_progression_performed: bool
    automatic_rollback_performed: bool
    real_traffic_shift_performed: bool
    authority_boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
