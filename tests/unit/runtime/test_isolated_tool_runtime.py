"""Tests for the Phase 7 isolated tool runtime."""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

from incident_agent.evaluation.ambiguity import (
    evaluate_ambiguity_pack,
    load_ambiguity_pack,
)
from incident_agent.genai.contracts import (
    ToolRecommendation,
    ToolRisk,
)
from incident_agent.genai.provider import (
    DeterministicTutorialProvider,
)
from incident_agent.genai.service import (
    build_synthesis_request,
    synthesize_evidence,
)
from incident_agent.ml.inference import (
    IncidentClassifier,
)
from incident_agent.policy.contracts import (
    PolicyDecision,
    PolicyIdentity,
)
from incident_agent.policy.engine import (
    evaluate_tool_recommendation,
)
from incident_agent.policy.service import (
    build_policy_context,
)
from incident_agent.retrieval.contracts import (
    RetrievalIdentity,
    RetrievalQuery,
    RetrievalScope,
)
from incident_agent.retrieval.engine import (
    retrieve_documents,
)
from incident_agent.retrieval.loader import (
    load_knowledge_corpus,
)
from incident_agent.retrieval.planning import (
    build_retrieval_query_text,
)
from incident_agent.runtime.contracts import (
    ExecutionStatus,
    RuntimeErrorCode,
)
from incident_agent.runtime.engine import (
    IsolatedToolRuntime,
)
from incident_agent.runtime.registry import (
    RUNTIME_TOOLS,
    RuntimeToolDefinition,
)
from incident_agent.runtime.service import (
    build_runtime_request,
    execute_authorized_request,
)


KNOWLEDGE_DIRECTORY = Path("data/knowledge")
AMBIGUITY_PACK = Path(
    "data/ambiguity/phase-3b-cases.yaml"
)
MODEL_DIRECTORY = Path(
    "models/incident-classifier"
)


def build_authorized_runtime_inputs():
    documents = load_knowledge_corpus(
        KNOWLEDGE_DIRECTORY
    )
    classifier = IncidentClassifier.load(
        MODEL_DIRECTORY
    )
    cases = load_ambiguity_pack(
        AMBIGUITY_PACK
    )

    ambiguity_result = next(
        result
        for result in evaluate_ambiguity_pack(
            cases,
            classifier,
        )
        if result.case_id
        == "dependency-errors-with-network-loss"
    )

    retrieval_response = retrieve_documents(
        documents=documents,
        query=RetrievalQuery(
            query_text=build_retrieval_query_text(
                ambiguity_result
            ),
            identity=RetrievalIdentity(
                user_id="engineer-42",
                tenant_id="tenant-alpha",
                roles=("incident_responder",),
            ),
            scope=RetrievalScope(
                service="identity-api",
                environment="production",
            ),
            maximum_results=5,
        ),
    )

    synthesis = synthesize_evidence(
        build_synthesis_request(
            ambiguity_result,
            retrieval_response,
        ),
        DeterministicTutorialProvider(),
    )

    synthesis = replace(
        synthesis,
        ignored_untrusted_instructions=(),
    )

    identity = PolicyIdentity(
        user_id="engineer-42",
        tenant_id="tenant-alpha",
        roles=("incident_responder",),
    )

    policy_context = build_policy_context(
        identity=identity,
        request_tenant_id="tenant-alpha",
        service="identity-api",
        environment="production",
        ambiguity_result=ambiguity_result,
        retrieval_response=retrieval_response,
    )

    policy_evaluation = (
        evaluate_tool_recommendation(
            synthesis,
            policy_context,
        )
    )

    assert (
        policy_evaluation.decision
        is PolicyDecision.ALLOW
    )

    request = build_runtime_request(
        synthesis=synthesis,
        policy_evaluation=policy_evaluation,
        policy_identity=identity,
        service="identity-api",
        environment="production",
        idempotency_key="test-runtime-key-1",
        now_epoch_seconds=1000.0,
        lifetime_seconds=60.0,
        dry_run=False,
    )

    return (
        synthesis,
        identity,
        policy_context,
        policy_evaluation,
        request,
    )


def test_allow_decision_executes_registered_read_only_tool() -> None:
    (
        synthesis,
        _,
        context,
        policy,
        request,
    ) = build_authorized_runtime_inputs()

    record = execute_authorized_request(
        runtime=IsolatedToolRuntime(),
        request=request,
        synthesis=synthesis,
        policy_evaluation=policy,
        policy_context=context,
        now_epoch_seconds=1001.0,
    )

    assert record.status is ExecutionStatus.SUCCEEDED
    assert record.execution_attempted
    assert record.result is not None
    assert not record.result.side_effects_performed
    assert record.error is None


def test_deny_decision_is_rejected_before_execution() -> None:
    (
        synthesis,
        _,
        context,
        policy,
        request,
    ) = build_authorized_runtime_inputs()

    denied_policy = replace(
        policy,
        decision=PolicyDecision.DENY,
    )

    record = execute_authorized_request(
        runtime=IsolatedToolRuntime(),
        request=request,
        synthesis=synthesis,
        policy_evaluation=denied_policy,
        policy_context=context,
        now_epoch_seconds=1001.0,
    )

    assert record.status is ExecutionStatus.REJECTED
    assert not record.execution_attempted
    assert record.error is not None
    assert (
        record.error.code
        is RuntimeErrorCode.POLICY_NOT_ALLOWED
    )


def test_escalate_decision_is_rejected_before_execution() -> None:
    (
        synthesis,
        _,
        context,
        policy,
        request,
    ) = build_authorized_runtime_inputs()

    escalated_policy = replace(
        policy,
        decision=PolicyDecision.ESCALATE,
    )

    record = execute_authorized_request(
        runtime=IsolatedToolRuntime(),
        request=request,
        synthesis=synthesis,
        policy_evaluation=escalated_policy,
        policy_context=context,
        now_epoch_seconds=1001.0,
    )

    assert record.status is ExecutionStatus.REJECTED
    assert not record.execution_attempted
    assert (
        record.error is not None
        and record.error.code
        is RuntimeErrorCode.POLICY_NOT_ALLOWED
    )


def test_copied_or_modified_fingerprint_is_rejected() -> None:
    (
        synthesis,
        _,
        context,
        policy,
        request,
    ) = build_authorized_runtime_inputs()

    invalid_request = replace(
        request,
        policy_fingerprint="0" * 64,
    )

    record = execute_authorized_request(
        runtime=IsolatedToolRuntime(),
        request=invalid_request,
        synthesis=synthesis,
        policy_evaluation=policy,
        policy_context=context,
        now_epoch_seconds=1001.0,
    )

    assert record.status is ExecutionStatus.REJECTED
    assert (
        record.error is not None
        and record.error.code
        is RuntimeErrorCode
        .POLICY_FINGERPRINT_MISMATCH
    )


def test_changed_policy_context_is_rejected() -> None:
    (
        synthesis,
        _,
        context,
        policy,
        request,
    ) = build_authorized_runtime_inputs()

    changed_context = replace(
        context,
        environment="staging",
    )

    record = execute_authorized_request(
        runtime=IsolatedToolRuntime(),
        request=request,
        synthesis=synthesis,
        policy_evaluation=policy,
        policy_context=changed_context,
        now_epoch_seconds=1001.0,
    )

    assert record.status is ExecutionStatus.REJECTED
    assert (
        record.error is not None
        and record.error.code
        is RuntimeErrorCode
        .POLICY_FINGERPRINT_MISMATCH
    )


def test_tool_name_mismatch_is_rejected() -> None:
    (
        synthesis,
        _,
        context,
        policy,
        request,
    ) = build_authorized_runtime_inputs()

    invalid_request = replace(
        request,
        tool_name="inspect_service_health",
    )

    record = execute_authorized_request(
        runtime=IsolatedToolRuntime(),
        request=invalid_request,
        synthesis=synthesis,
        policy_evaluation=policy,
        policy_context=context,
        now_epoch_seconds=1001.0,
    )

    assert record.status is ExecutionStatus.REJECTED
    assert (
        record.error is not None
        and record.error.code
        is RuntimeErrorCode.TOOL_NAME_MISMATCH
    )


def test_argument_tampering_is_rejected() -> None:
    (
        synthesis,
        _,
        context,
        policy,
        request,
    ) = build_authorized_runtime_inputs()

    invalid_request = replace(
        request,
        arguments={
            "service": "payments-api",
            "environment": "production",
        },
    )

    record = execute_authorized_request(
        runtime=IsolatedToolRuntime(),
        request=invalid_request,
        synthesis=synthesis,
        policy_evaluation=policy,
        policy_context=context,
        now_epoch_seconds=1001.0,
    )

    assert record.status is ExecutionStatus.REJECTED
    assert (
        record.error is not None
        and record.error.code
        is RuntimeErrorCode
        .ARGUMENT_SCHEMA_INVALID
    )


def test_risk_tampering_is_rejected() -> None:
    (
        synthesis,
        _,
        context,
        policy,
        request,
    ) = build_authorized_runtime_inputs()

    invalid_request = replace(
        request,
        declared_risk=ToolRisk.HIGH_IMPACT,
    )

    record = execute_authorized_request(
        runtime=IsolatedToolRuntime(),
        request=invalid_request,
        synthesis=synthesis,
        policy_evaluation=policy,
        policy_context=context,
        now_epoch_seconds=1001.0,
    )

    assert record.status is ExecutionStatus.REJECTED
    assert (
        record.error is not None
        and record.error.code
        is RuntimeErrorCode.RISK_MISMATCH
    )


def test_expired_request_is_rejected() -> None:
    (
        synthesis,
        _,
        context,
        policy,
        request,
    ) = build_authorized_runtime_inputs()

    record = execute_authorized_request(
        runtime=IsolatedToolRuntime(),
        request=request,
        synthesis=synthesis,
        policy_evaluation=policy,
        policy_context=context,
        now_epoch_seconds=1061.0,
    )

    assert record.status is ExecutionStatus.REJECTED
    assert (
        record.error is not None
        and record.error.code
        is RuntimeErrorCode.REQUEST_EXPIRED
    )


def test_reused_idempotency_key_does_not_execute_again() -> None:
    (
        synthesis,
        _,
        context,
        policy,
        request,
    ) = build_authorized_runtime_inputs()

    runtime = IsolatedToolRuntime()

    first = execute_authorized_request(
        runtime=runtime,
        request=request,
        synthesis=synthesis,
        policy_evaluation=policy,
        policy_context=context,
        now_epoch_seconds=1001.0,
    )

    second = execute_authorized_request(
        runtime=runtime,
        request=request,
        synthesis=synthesis,
        policy_evaluation=policy,
        policy_context=context,
        now_epoch_seconds=1002.0,
    )

    assert first.status is ExecutionStatus.SUCCEEDED
    assert second.status is ExecutionStatus.REPLAYED
    assert not second.execution_attempted
    assert (
        second.error is not None
        and second.error.code
        is RuntimeErrorCode.IDEMPOTENCY_KEY_REUSED
    )


def test_mutating_tool_requires_dry_run() -> None:
    (
        synthesis,
        identity,
        context,
        policy,
        request,
    ) = build_authorized_runtime_inputs()

    mutating_recommendation = ToolRecommendation(
        tool_name="restart_service",
        arguments={
            "service": "identity-api",
            "environment": "production",
        },
        rationale="Controlled dry-run proposal.",
        risk=ToolRisk.MUTATING,
    )

    mutating_synthesis = replace(
        synthesis,
        tool_recommendation=mutating_recommendation,
    )

    mutating_policy = replace(
        policy,
        tool_name="restart_service",
    )

    mutating_request = replace(
        request,
        tool_name="restart_service",
        arguments=dict(
            mutating_recommendation.arguments
        ),
        declared_risk=ToolRisk.MUTATING,
        dry_run=False,
        policy_fingerprint=(
            mutating_policy.request_fingerprint
        ),
    )

    record = execute_authorized_request(
        runtime=IsolatedToolRuntime(),
        request=mutating_request,
        synthesis=mutating_synthesis,
        policy_evaluation=mutating_policy,
        policy_context=context,
        now_epoch_seconds=1001.0,
    )

    assert record.status is ExecutionStatus.REJECTED
    assert (
        record.error is not None
        and record.error.code
        in {
            RuntimeErrorCode
            .POLICY_FINGERPRINT_MISMATCH,
            RuntimeErrorCode.DRY_RUN_REQUIRED,
        }
    )


def test_registered_mutating_handler_has_no_side_effects() -> None:
    definition = RUNTIME_TOOLS["restart_service"]

    result = definition.handler(
        {
            "service": "identity-api",
            "environment": "production",
        },
        True,
    )

    assert definition.dry_run_required
    assert not result.side_effects_performed
    assert result.data["dry_run"] is True


def test_handler_timeout_is_structured(
    monkeypatch,
) -> None:
    (
        synthesis,
        _,
        context,
        policy,
        request,
    ) = build_authorized_runtime_inputs()

    original = RUNTIME_TOOLS[
        "inspect_incident_telemetry"
    ]

    def slow_handler(arguments, dry_run):
        del arguments
        del dry_run
        time.sleep(0.05)
        return original.handler(
            {
                "service": "identity-api",
                "environment": "production",
            },
            False,
        )

    monkeypatch.setitem(
        RUNTIME_TOOLS,
        "inspect_incident_telemetry",
        RuntimeToolDefinition(
            tool_name=original.tool_name,
            risk=original.risk,
            required_arguments=(
                original.required_arguments
            ),
            timeout_seconds=0.001,
            maximum_attempts=1,
            dry_run_required=False,
            handler=slow_handler,
        ),
    )

    record = execute_authorized_request(
        runtime=IsolatedToolRuntime(),
        request=request,
        synthesis=synthesis,
        policy_evaluation=policy,
        policy_context=context,
        now_epoch_seconds=1001.0,
    )

    assert record.status is ExecutionStatus.TIMED_OUT
    assert record.execution_attempted
    assert (
        record.error is not None
        and record.error.code
        is RuntimeErrorCode.EXECUTION_TIMEOUT
    )


def test_handler_failure_is_structured(
    monkeypatch,
) -> None:
    (
        synthesis,
        _,
        context,
        policy,
        request,
    ) = build_authorized_runtime_inputs()

    original = RUNTIME_TOOLS[
        "inspect_incident_telemetry"
    ]

    def failing_handler(arguments, dry_run):
        del arguments
        del dry_run
        raise RuntimeError("sensitive internal failure")

    monkeypatch.setitem(
        RUNTIME_TOOLS,
        "inspect_incident_telemetry",
        RuntimeToolDefinition(
            tool_name=original.tool_name,
            risk=original.risk,
            required_arguments=(
                original.required_arguments
            ),
            timeout_seconds=1.0,
            maximum_attempts=1,
            dry_run_required=False,
            handler=failing_handler,
        ),
    )

    record = execute_authorized_request(
        runtime=IsolatedToolRuntime(),
        request=request,
        synthesis=synthesis,
        policy_evaluation=policy,
        policy_context=context,
        now_epoch_seconds=1001.0,
    )

    assert record.status is ExecutionStatus.FAILED
    assert record.execution_attempted
    assert (
        record.error is not None
        and record.error.code
        is RuntimeErrorCode.HANDLER_FAILURE
    )
    assert (
        "sensitive internal failure"
        not in record.error.message
    )


def test_audit_events_bind_request_and_policy() -> None:
    (
        synthesis,
        _,
        context,
        policy,
        request,
    ) = build_authorized_runtime_inputs()

    record = execute_authorized_request(
        runtime=IsolatedToolRuntime(),
        request=request,
        synthesis=synthesis,
        policy_evaluation=policy,
        policy_context=context,
        now_epoch_seconds=1001.0,
    )

    assert record.audit_events

    for event in record.audit_events:
        assert event.request_id == request.request_id
        assert (
            event.idempotency_key
            == request.idempotency_key
        )
        assert (
            event.policy_fingerprint
            == policy.request_fingerprint
        )


def test_runtime_version_and_authority_boundary_recorded() -> None:
    (
        synthesis,
        _,
        context,
        policy,
        request,
    ) = build_authorized_runtime_inputs()

    record = execute_authorized_request(
        runtime=IsolatedToolRuntime(),
        request=request,
        synthesis=synthesis,
        policy_evaluation=policy,
        policy_context=context,
        now_epoch_seconds=1001.0,
    )

    assert (
        record.runtime_version
        == "isolated-tool-runtime-v1"
    )
    assert "policy" in (
        record.authority_boundary.lower()
    )
