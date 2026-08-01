"""Tests for the governed Phase 8 orchestrator."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from incident_agent.orchestrator.checkpoints import (
    InMemoryCheckpointStore,
    build_state_digest,
)
from incident_agent.orchestrator.contracts import (
    StopReason,
    WorkflowIdentity,
    WorkflowRequest,
    WorkflowStatus,
    WorkflowStep,
)
from incident_agent.orchestrator.engine import (
    GovernedAgentOrchestrator,
    ORCHESTRATOR_VERSION,
)
from incident_agent.orchestrator.replay import (
    verify_workflow_replay,
)
from incident_agent.runtime.engine import (
    IsolatedToolRuntime,
)


KNOWLEDGE_DIRECTORY = Path("data/knowledge")
AMBIGUITY_PACK = Path(
    "data/ambiguity/phase-3b-cases.yaml"
)
MODEL_DIRECTORY = Path(
    "models/incident-classifier"
)


def build_orchestrator(
    checkpoint_store=None,
    runtime=None,
):
    return GovernedAgentOrchestrator(
        knowledge_directory=(
            KNOWLEDGE_DIRECTORY
        ),
        ambiguity_pack_path=AMBIGUITY_PACK,
        model_directory=MODEL_DIRECTORY,
        checkpoint_store=checkpoint_store,
        runtime=runtime,
    )


def build_request(
    workflow_id: str = "workflow-test-001",
    trace_id: str = "trace-test-001",
    case_id: str = (
        "dependency-errors-with-network-loss"
    ),
    idempotency_key: str = (
        "orchestrator-runtime-key-001"
    ),
) -> WorkflowRequest:
    return WorkflowRequest(
        workflow_id=workflow_id,
        trace_id=trace_id,
        case_id=case_id,
        identity=WorkflowIdentity(
            user_id="engineer-42",
            tenant_id="tenant-alpha",
            roles=("incident_responder",),
        ),
        request_tenant_id="tenant-alpha",
        service="identity-api",
        environment="production",
        maximum_retrieval_results=5,
        idempotency_key=idempotency_key,
        dry_run=False,
        created_at_epoch_seconds=1000.0,
    )


def test_end_to_end_workflow_completes() -> None:
    outcome = build_orchestrator().run(
        request=build_request(),
        now_epoch_seconds=1001.0,
    )

    assert (
        outcome.status
        is WorkflowStatus.COMPLETED
    )
    assert (
        outcome.final_step
        is WorkflowStep.COMPLETED
    )
    assert outcome.policy_decision == "ALLOW"
    assert outcome.runtime_status == "SUCCEEDED"
    assert outcome.stop_reason is StopReason.NONE


def test_workflow_steps_are_ordered() -> None:
    outcome = build_orchestrator().run(
        request=build_request(),
        now_epoch_seconds=1001.0,
    )

    sequences = [
        event.sequence
        for event in outcome.events
    ]

    assert sequences == sorted(sequences)
    assert len(sequences) == len(set(sequences))


def test_required_steps_are_present() -> None:
    outcome = build_orchestrator().run(
        request=build_request(),
        now_epoch_seconds=1001.0,
    )

    steps = {
        event.step
        for event in outcome.events
    }

    assert WorkflowStep.RECEIVED in steps
    assert (
        WorkflowStep.AMBIGUITY_EVALUATED
        in steps
    )
    assert (
        WorkflowStep.RETRIEVAL_COMPLETED
        in steps
    )
    assert (
        WorkflowStep.SYNTHESIS_COMPLETED
        in steps
    )
    assert (
        WorkflowStep.POLICY_EVALUATED
        in steps
    )
    assert (
        WorkflowStep.RUNTIME_COMPLETED
        in steps
    )
    assert WorkflowStep.COMPLETED in steps


def test_checkpoint_created_after_each_step() -> None:
    store = InMemoryCheckpointStore()
    orchestrator = build_orchestrator(
        checkpoint_store=store
    )
    request = build_request()

    outcome = orchestrator.run(
        request=request,
        now_epoch_seconds=1001.0,
    )

    assert outcome.checkpoints
    assert (
        outcome.checkpoints
        == store.list_for_workflow(
            request.workflow_id
        )
    )

    checkpoint_steps = {
        checkpoint.step
        for checkpoint in outcome.checkpoints
    }

    assert WorkflowStep.RECEIVED in checkpoint_steps
    assert (
        WorkflowStep.POLICY_EVALUATED
        in checkpoint_steps
    )
    assert (
        WorkflowStep.RUNTIME_COMPLETED
        in checkpoint_steps
    )
    assert WorkflowStep.COMPLETED in checkpoint_steps


def test_checkpoints_have_stable_digests() -> None:
    first = build_state_digest(
        {
            "step": "retrieval",
            "citations": ["a", "b"],
        }
    )
    second = build_state_digest(
        {
            "citations": ["a", "b"],
            "step": "retrieval",
        }
    )

    assert first == second
    assert len(first) == 64


def test_all_events_bind_trace_and_workflow() -> None:
    request = build_request()

    outcome = build_orchestrator().run(
        request=request,
        now_epoch_seconds=1001.0,
    )

    assert all(
        event.trace_id == request.trace_id
        for event in outcome.events
    )
    assert all(
        event.workflow_id
        == request.workflow_id
        for event in outcome.events
    )


def test_policy_occurs_before_runtime() -> None:
    outcome = build_orchestrator().run(
        request=build_request(),
        now_epoch_seconds=1001.0,
    )

    policy_sequence = next(
        event.sequence
        for event in outcome.events
        if event.step
        is WorkflowStep.POLICY_EVALUATED
    )

    runtime_sequence = next(
        event.sequence
        for event in outcome.events
        if event.step
        is WorkflowStep.RUNTIME_COMPLETED
    )

    assert policy_sequence < runtime_sequence
    assert outcome.policy_decision == "ALLOW"


def test_cross_tenant_request_stops_at_policy() -> None:
    request = build_request()

    invalid_request = replace(
        request,
        request_tenant_id="tenant-beta",
    )

    outcome = build_orchestrator().run(
        request=invalid_request,
        now_epoch_seconds=1001.0,
    )

    assert (
        outcome.status
        is WorkflowStatus.DENIED
    )
    assert (
        outcome.stop_reason
        is StopReason.POLICY_DENIED
    )
    assert outcome.policy_decision == "DENY"
    assert outcome.runtime_status is None

    assert not any(
        event.step
        is WorkflowStep.RUNTIME_COMPLETED
        for event in outcome.events
    )


def test_unauthorized_identity_cannot_reach_runtime() -> None:
    request = replace(
        build_request(),
        identity=WorkflowIdentity(
            user_id="auditor-7",
            tenant_id="tenant-alpha",
            roles=("auditor",),
        ),
    )

    outcome = build_orchestrator().run(
        request=request,
        now_epoch_seconds=1001.0,
    )

    assert (
        outcome.status
        is WorkflowStatus.DENIED
    )
    assert (
        outcome.stop_reason
        is StopReason.SYNTHESIS_ABSTAINED
    )
    assert outcome.policy_decision is None
    assert outcome.runtime_status is None
    assert (
        outcome.final_step
        is WorkflowStep.DENIED
    )

    assert not any(
        event.step
        is WorkflowStep.POLICY_EVALUATED
        for event in outcome.events
    )

    assert not any(
        event.step
        is WorkflowStep.RUNTIME_COMPLETED
        for event in outcome.events
    )


def test_expired_runtime_request_fails_safely() -> None:
    outcome = build_orchestrator().run(
        request=build_request(
            workflow_id="workflow-expired",
            idempotency_key="expired-key",
        ),
        now_epoch_seconds=1061.0,
    )

    assert (
        outcome.status
        is WorkflowStatus.FAILED
    )
    assert (
        outcome.stop_reason
        is StopReason.RUNTIME_REJECTED
    )
    assert outcome.policy_decision == "ALLOW"
    assert outcome.runtime_status == "REJECTED"


def test_runtime_replay_does_not_execute_twice() -> None:
    runtime = IsolatedToolRuntime()
    orchestrator = build_orchestrator(
        runtime=runtime
    )

    first = orchestrator.run(
        request=build_request(
            workflow_id="workflow-replay-1",
            trace_id="trace-replay-1",
            idempotency_key="shared-runtime-key",
        ),
        now_epoch_seconds=1001.0,
    )

    second = orchestrator.run(
        request=build_request(
            workflow_id="workflow-replay-2",
            trace_id="trace-replay-2",
            idempotency_key="shared-runtime-key",
        ),
        now_epoch_seconds=1002.0,
    )

    assert first.runtime_status == "SUCCEEDED"
    assert second.runtime_status == "REPLAYED"
    assert (
        second.status
        is WorkflowStatus.COMPLETED
    )


def test_replay_verification_passes() -> None:
    outcome = build_orchestrator().run(
        request=build_request(),
        now_epoch_seconds=1001.0,
    )

    verification = verify_workflow_replay(
        outcome
    )

    assert verification.valid
    assert verification.event_sequence_valid
    assert (
        verification.checkpoint_sequence_valid
    )
    assert verification.trace_binding_valid
    assert verification.workflow_binding_valid
    assert verification.runtime_after_allow_only


def test_replay_detects_runtime_without_allow() -> None:
    outcome = build_orchestrator().run(
        request=build_request(),
        now_epoch_seconds=1001.0,
    )

    tampered = replace(
        outcome,
        policy_decision="DENY",
    )

    verification = verify_workflow_replay(
        tampered
    )

    assert not verification.valid
    assert not verification.runtime_after_allow_only


def test_unknown_case_fails_without_runtime() -> None:
    outcome = build_orchestrator().run(
        request=build_request(
            workflow_id="workflow-unknown",
            trace_id="trace-unknown",
            case_id="case-does-not-exist",
            idempotency_key="unknown-case-key",
        ),
        now_epoch_seconds=1001.0,
    )

    assert (
        outcome.status
        is WorkflowStatus.FAILED
    )
    assert (
        outcome.stop_reason
        is StopReason.STEP_FAILURE
    )
    assert outcome.runtime_status is None


def test_evidence_references_exist_after_retrieval() -> None:
    outcome = build_orchestrator().run(
        request=build_request(),
        now_epoch_seconds=1001.0,
    )

    retrieval_event = next(
        event
        for event in outcome.events
        if event.step
        is WorkflowStep.RETRIEVAL_COMPLETED
    )

    assert retrieval_event.evidence_references
    assert all(
        citation.startswith("[")
        and citation.endswith("]")
        for citation
        in retrieval_event.evidence_references
    )


def test_policy_checkpoint_contains_fingerprint() -> None:
    outcome = build_orchestrator().run(
        request=build_request(),
        now_epoch_seconds=1001.0,
    )

    checkpoint = next(
        item
        for item in outcome.checkpoints
        if item.step
        is WorkflowStep.POLICY_EVALUATED
    )

    assert any(
        len(reference) == 64
        for reference
        in checkpoint.evidence_references
    )


def test_orchestrator_version_and_boundary_recorded() -> None:
    outcome = build_orchestrator().run(
        request=build_request(),
        now_epoch_seconds=1001.0,
    )

    assert (
        outcome.orchestrator_version
        == ORCHESTRATOR_VERSION
    )
    assert "cannot bypass" in (
        outcome.authority_boundary
    )


def test_no_direct_genai_to_runtime_transition() -> None:
    outcome = build_orchestrator().run(
        request=build_request(),
        now_epoch_seconds=1001.0,
    )

    ordered_steps = [
        event.step
        for event in outcome.events
    ]

    synthesis_index = ordered_steps.index(
        WorkflowStep.SYNTHESIS_COMPLETED
    )
    policy_index = ordered_steps.index(
        WorkflowStep.POLICY_EVALUATED
    )
    runtime_index = ordered_steps.index(
        WorkflowStep.RUNTIME_COMPLETED
    )

    assert synthesis_index < policy_index
    assert policy_index < runtime_index
