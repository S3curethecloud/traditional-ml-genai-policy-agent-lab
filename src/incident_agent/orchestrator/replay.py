"""Workflow replay and timeline verification."""

from __future__ import annotations

from dataclasses import dataclass

from incident_agent.orchestrator.contracts import (
    WorkflowOutcome,
)


@dataclass(frozen=True)
class ReplayVerification:
    """Result of verifying an orchestrator outcome."""

    valid: bool
    event_sequence_valid: bool
    checkpoint_sequence_valid: bool
    trace_binding_valid: bool
    workflow_binding_valid: bool
    runtime_after_allow_only: bool
    errors: tuple[str, ...]


def verify_workflow_replay(
    outcome: WorkflowOutcome,
) -> ReplayVerification:
    """Verify ordering and authority properties."""

    errors: list[str] = []

    event_sequences = [
        event.sequence
        for event in outcome.events
    ]

    event_sequence_valid = (
        event_sequences
        == sorted(event_sequences)
        and len(event_sequences)
        == len(set(event_sequences))
    )

    if not event_sequence_valid:
        errors.append(
            "Event sequence is invalid"
        )

    checkpoint_sequences = [
        checkpoint.sequence
        for checkpoint in outcome.checkpoints
    ]

    checkpoint_sequence_valid = (
        checkpoint_sequences
        == sorted(checkpoint_sequences)
        and len(checkpoint_sequences)
        == len(set(checkpoint_sequences))
    )

    if not checkpoint_sequence_valid:
        errors.append(
            "Checkpoint sequence is invalid"
        )

    trace_binding_valid = all(
        event.trace_id == outcome.trace_id
        for event in outcome.events
    ) and all(
        checkpoint.trace_id == outcome.trace_id
        for checkpoint in outcome.checkpoints
    )

    if not trace_binding_valid:
        errors.append(
            "Trace binding is invalid"
        )

    workflow_binding_valid = all(
        event.workflow_id == outcome.workflow_id
        for event in outcome.events
    ) and all(
        checkpoint.workflow_id
        == outcome.workflow_id
        for checkpoint in outcome.checkpoints
    )

    if not workflow_binding_valid:
        errors.append(
            "Workflow binding is invalid"
        )

    runtime_events = [
        event
        for event in outcome.events
        if event.event_type
        == "runtime_completed"
    ]

    runtime_after_allow_only = (
        not runtime_events
        or outcome.policy_decision == "ALLOW"
    )

    if not runtime_after_allow_only:
        errors.append(
            "Runtime occurred without ALLOW"
        )

    return ReplayVerification(
        valid=not errors,
        event_sequence_valid=(
            event_sequence_valid
        ),
        checkpoint_sequence_valid=(
            checkpoint_sequence_valid
        ),
        trace_binding_valid=(
            trace_binding_valid
        ),
        workflow_binding_valid=(
            workflow_binding_valid
        ),
        runtime_after_allow_only=(
            runtime_after_allow_only
        ),
        errors=tuple(errors),
    )
