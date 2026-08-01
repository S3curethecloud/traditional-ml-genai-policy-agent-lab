"""Internal typed state for the agent orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field

from incident_agent.evaluation.ambiguity import (
    AmbiguityResult,
)
from incident_agent.genai.contracts import (
    SynthesisResponse,
)
from incident_agent.orchestrator.contracts import (
    WorkflowEvent,
    WorkflowRequest,
    WorkflowStatus,
    WorkflowStep,
)
from incident_agent.policy.contracts import (
    PolicyContext,
    PolicyEvaluation,
)
from incident_agent.retrieval.contracts import (
    RetrievalResponse,
)
from incident_agent.runtime.contracts import (
    ExecutionRecord,
)


@dataclass
class WorkflowState:
    """Mutable internal state owned by one orchestrator run."""

    request: WorkflowRequest
    status: WorkflowStatus = WorkflowStatus.RUNNING
    current_step: WorkflowStep = WorkflowStep.RECEIVED
    sequence: int = 0
    ambiguity_result: AmbiguityResult | None = None
    retrieval_response: RetrievalResponse | None = None
    synthesis_response: SynthesisResponse | None = None
    policy_context: PolicyContext | None = None
    policy_evaluation: PolicyEvaluation | None = None
    runtime_record: ExecutionRecord | None = None
    events: list[WorkflowEvent] = field(
        default_factory=list
    )
