"""Inspection helpers for governed workflow outcomes."""

from __future__ import annotations

from incident_agent.orchestrator.contracts import (
    WorkflowOutcome,
    WorkflowStep,
)
from incident_agent.orchestrator.replay import (
    verify_workflow_replay,
)


REQUIRED_SUCCESS_STEPS = {
    WorkflowStep.RECEIVED,
    WorkflowStep.AMBIGUITY_EVALUATED,
    WorkflowStep.RETRIEVAL_COMPLETED,
    WorkflowStep.SYNTHESIS_COMPLETED,
    WorkflowStep.POLICY_EVALUATED,
    WorkflowStep.RUNTIME_COMPLETED,
    WorkflowStep.COMPLETED,
}


def has_complete_trace(
    outcome: WorkflowOutcome,
) -> bool:
    """Check trace and workflow binding for all records."""

    if not outcome.events or not outcome.checkpoints:
        return False

    return all(
        event.trace_id == outcome.trace_id
        and event.workflow_id == outcome.workflow_id
        for event in outcome.events
    ) and all(
        checkpoint.trace_id == outcome.trace_id
        and checkpoint.workflow_id
        == outcome.workflow_id
        for checkpoint in outcome.checkpoints
    )


def has_valid_checkpoint_chain(
    outcome: WorkflowOutcome,
) -> bool:
    """Check ordered, unique checkpoint sequences."""

    verification = verify_workflow_replay(outcome)

    return (
        verification.checkpoint_sequence_valid
        and verification.event_sequence_valid
        and verification.trace_binding_valid
        and verification.workflow_binding_valid
    )


def runtime_followed_allow(
    outcome: WorkflowOutcome,
) -> bool:
    """Confirm runtime appears only after policy ALLOW."""

    runtime_events = [
        event
        for event in outcome.events
        if event.step is WorkflowStep.RUNTIME_COMPLETED
    ]

    if not runtime_events:
        return True

    return outcome.policy_decision == "ALLOW"


def policy_precedes_runtime(
    outcome: WorkflowOutcome,
) -> bool:
    """Confirm policy sequencing when runtime occurred."""

    policy_events = [
        event
        for event in outcome.events
        if event.step is WorkflowStep.POLICY_EVALUATED
    ]
    runtime_events = [
        event
        for event in outcome.events
        if event.step is WorkflowStep.RUNTIME_COMPLETED
    ]

    if not runtime_events:
        return True

    if not policy_events:
        return False

    return (
        min(event.sequence for event in policy_events)
        < min(event.sequence for event in runtime_events)
    )


def successful_trace_has_required_steps(
    outcome: WorkflowOutcome,
) -> bool:
    """Check required steps for a successful workflow."""

    if outcome.status.value != "COMPLETED":
        return True

    observed_steps = {
        event.step
        for event in outcome.events
    }

    return REQUIRED_SUCCESS_STEPS.issubset(
        observed_steps
    )


def retrieval_citations(
    outcome: WorkflowOutcome,
) -> tuple[str, ...]:
    """Return citations recorded at retrieval."""

    citations: list[str] = []

    for event in outcome.events:
        if event.step is WorkflowStep.RETRIEVAL_COMPLETED:
            citations.extend(
                reference
                for reference
                in event.evidence_references
                if reference.startswith("[")
                and reference.endswith("]")
            )

    return tuple(citations)


def synthesis_citations(
    outcome: WorkflowOutcome,
) -> tuple[str, ...]:
    """Return citations recorded at synthesis."""

    citations: list[str] = []

    for event in outcome.events:
        if event.step is WorkflowStep.SYNTHESIS_COMPLETED:
            citations.extend(
                reference
                for reference
                in event.evidence_references
                if reference.startswith("[")
                and reference.endswith("]")
            )

    return tuple(citations)


def policy_reason_ids(
    outcome: WorkflowOutcome,
) -> tuple[str, ...]:
    """Return policy reason IDs from workflow evidence."""

    reasons: list[str] = []

    for event in outcome.events:
        if event.step is WorkflowStep.POLICY_EVALUATED:
            reasons.extend(
                reference
                for reference
                in event.evidence_references
                if reference.startswith("POL-")
            )

    return tuple(reasons)


def citation_manifest_complete(
    outcome: WorkflowOutcome,
) -> bool:
    """Check synthesis citations against retrieval citations."""

    synthesized = set(
        synthesis_citations(outcome)
    )

    if not synthesized:
        return True

    retrieved = set(
        retrieval_citations(outcome)
    )

    return synthesized.issubset(retrieved)
