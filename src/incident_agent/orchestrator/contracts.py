"""Typed contracts for the governed agent orchestrator."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class WorkflowStep(StrEnum):
    """Ordered workflow steps."""

    RECEIVED = "RECEIVED"
    AMBIGUITY_EVALUATED = "AMBIGUITY_EVALUATED"
    RETRIEVAL_COMPLETED = "RETRIEVAL_COMPLETED"
    SYNTHESIS_COMPLETED = "SYNTHESIS_COMPLETED"
    POLICY_EVALUATED = "POLICY_EVALUATED"
    RUNTIME_COMPLETED = "RUNTIME_COMPLETED"
    HUMAN_ESCALATION_REQUIRED = (
        "HUMAN_ESCALATION_REQUIRED"
    )
    DENIED = "DENIED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class WorkflowStatus(StrEnum):
    """Overall workflow status."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    DENIED = "DENIED"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"


class StopReason(StrEnum):
    """Stable orchestrator stop reasons."""

    NONE = "NONE"
    POLICY_DENIED = "POLICY_DENIED"
    POLICY_ESCALATED = "POLICY_ESCALATED"
    SYNTHESIS_ABSTAINED = "SYNTHESIS_ABSTAINED"
    RUNTIME_REJECTED = "RUNTIME_REJECTED"
    RUNTIME_FAILED = "RUNTIME_FAILED"
    STEP_FAILURE = "STEP_FAILURE"


@dataclass(frozen=True)
class WorkflowIdentity:
    """Identity entering the governed workflow."""

    user_id: str
    tenant_id: str
    roles: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowRequest:
    """Typed request accepted by the orchestrator."""

    workflow_id: str
    trace_id: str
    case_id: str
    identity: WorkflowIdentity
    request_tenant_id: str
    service: str
    environment: str
    maximum_retrieval_results: int
    idempotency_key: str
    dry_run: bool
    created_at_epoch_seconds: float


@dataclass(frozen=True)
class WorkflowEvent:
    """One ordered event in the workflow timeline."""

    sequence: int
    step: WorkflowStep
    event_type: str
    trace_id: str
    workflow_id: str
    detail: str
    evidence_references: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowCheckpoint:
    """Serializable checkpoint after a completed step."""

    workflow_id: str
    trace_id: str
    step: WorkflowStep
    sequence: int
    state_digest: str
    evidence_references: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowOutcome:
    """Final end-to-end workflow result."""

    workflow_id: str
    trace_id: str
    case_id: str
    status: WorkflowStatus
    final_step: WorkflowStep
    stop_reason: StopReason
    policy_decision: str | None
    recommended_tool: str | None
    runtime_status: str | None
    checkpoints: tuple[WorkflowCheckpoint, ...]
    events: tuple[WorkflowEvent, ...]
    authority_boundary: str
    orchestrator_version: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)
