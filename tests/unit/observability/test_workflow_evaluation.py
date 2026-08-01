"""Tests for Phase 9 evaluation and release evidence."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from incident_agent.observability.contracts import (
    ExpectedOutcome,
    MetricStatus,
    StepLatency,
    UsageObservation,
    WorkflowObservation,
)
from incident_agent.observability.evaluator import (
    EVALUATION_VERSION,
    evaluate_workflows,
    failed_metric_names,
    release_gate_passed,
)
from incident_agent.observability.evidence import (
    BUNDLE_VERSION,
    build_release_evidence_bundle,
)
from incident_agent.observability.inspection import (
    citation_manifest_complete,
    has_complete_trace,
    has_valid_checkpoint_chain,
    policy_precedes_runtime,
    runtime_followed_allow,
)
from incident_agent.orchestrator.contracts import (
    WorkflowIdentity,
    WorkflowRequest,
)
from incident_agent.orchestrator.engine import (
    GovernedAgentOrchestrator,
)


KNOWLEDGE_DIRECTORY = Path("data/knowledge")
AMBIGUITY_PACK = Path(
    "data/ambiguity/phase-3b-cases.yaml"
)
MODEL_DIRECTORY = Path(
    "models/incident-classifier"
)


def build_orchestrator():
    return GovernedAgentOrchestrator(
        knowledge_directory=(
            KNOWLEDGE_DIRECTORY
        ),
        ambiguity_pack_path=AMBIGUITY_PACK,
        model_directory=MODEL_DIRECTORY,
    )


def build_request(
    workflow_id: str,
    trace_id: str,
    idempotency_key: str,
) -> WorkflowRequest:
    return WorkflowRequest(
        workflow_id=workflow_id,
        trace_id=trace_id,
        case_id=(
            "dependency-errors-with-network-loss"
        ),
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


def observe(
    case_id,
    expected,
    outcome,
    latency=700.0,
    cross_tenant=False,
    injection=False,
):
    return WorkflowObservation(
        evaluation_case_id=case_id,
        expected_outcome=expected,
        outcome=outcome,
        total_latency_ms=latency,
        step_latencies=(
            StepLatency("retrieval", 80.0),
            StepLatency("synthesis", 400.0),
            StepLatency("policy", 10.0),
            StepLatency("runtime", 30.0),
        ),
        usage=UsageObservation(
            input_tokens=1200,
            output_tokens=350,
            estimated_model_cost_usd=0.01,
            retrieval_queries=1,
            tool_execution_attempts=(
                1
                if outcome.runtime_status
                == "SUCCEEDED"
                else 0
            ),
        ),
        prompt_injection_detected=injection,
        cross_tenant_attempt=cross_tenant,
        notes=("No production side effect occurred.",),
    )


def build_observations():
    orchestrator = build_orchestrator()

    normal = orchestrator.run(
        build_request(
            "workflow-observe-normal",
            "trace-observe-normal",
            "key-observe-normal",
        ),
        now_epoch_seconds=1001.0,
    )

    cross_request = replace(
        build_request(
            "workflow-observe-cross",
            "trace-observe-cross",
            "key-observe-cross",
        ),
        request_tenant_id="tenant-beta",
    )

    cross = orchestrator.run(
        cross_request,
        now_epoch_seconds=1001.0,
    )

    expired = orchestrator.run(
        build_request(
            "workflow-observe-expired",
            "trace-observe-expired",
            "key-observe-expired",
        ),
        now_epoch_seconds=1061.0,
    )

    return (
        observe(
            "normal-success",
            ExpectedOutcome.NORMAL_SUCCESS,
            normal,
        ),
        observe(
            "cross-tenant",
            ExpectedOutcome.EXPECTED_DENIAL,
            cross,
            cross_tenant=True,
        ),
        observe(
            "expired-runtime",
            ExpectedOutcome.EXPECTED_FAILURE,
            expired,
        ),
    )


def metric(summary, name):
    return next(
        item
        for item in summary.metrics
        if item.metric_name == name
    )


def test_empty_observation_set_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="At least one",
    ):
        evaluate_workflows(())


def test_evaluation_version_is_recorded() -> None:
    summary = evaluate_workflows(
        build_observations()
    )

    assert (
        summary.evaluation_version
        == EVALUATION_VERSION
    )


def test_normal_and_negative_cases_are_separated() -> None:
    summary = evaluate_workflows(
        build_observations()
    )

    assert summary.workflow_count == 3
    assert summary.normal_workflow_count == 1
    assert summary.negative_test_count == 2


def test_normal_success_rate_passes() -> None:
    summary = evaluate_workflows(
        build_observations()
    )

    result = metric(
        summary,
        "normal_workflow_success_rate",
    )

    assert result.value == 1.0
    assert result.status is MetricStatus.PASS


def test_expected_negative_controls_pass() -> None:
    summary = evaluate_workflows(
        build_observations()
    )

    result = metric(
        summary,
        "expected_negative_outcome_rate",
    )

    assert result.value == 1.0
    assert result.status is MetricStatus.PASS


def test_trace_completeness_passes() -> None:
    observations = build_observations()
    summary = evaluate_workflows(observations)

    assert all(
        has_complete_trace(item.outcome)
        for item in observations
    )

    assert (
        metric(
            summary,
            "trace_completeness_rate",
        ).status
        is MetricStatus.PASS
    )


def test_checkpoint_integrity_passes() -> None:
    observations = build_observations()

    assert all(
        has_valid_checkpoint_chain(item.outcome)
        for item in observations
    )


def test_runtime_requires_allow() -> None:
    observations = build_observations()
    summary = evaluate_workflows(observations)

    assert all(
        runtime_followed_allow(item.outcome)
        for item in observations
    )

    assert (
        metric(
            summary,
            "runtime_after_allow_rate",
        ).value
        == 1.0
    )


def test_policy_precedes_runtime() -> None:
    observations = build_observations()

    assert all(
        policy_precedes_runtime(item.outcome)
        for item in observations
    )


def test_cross_tenant_attempt_is_denied() -> None:
    summary = evaluate_workflows(
        build_observations()
    )

    result = metric(
        summary,
        "cross_tenant_denial_rate",
    )

    assert result.value == 1.0
    assert result.status is MetricStatus.PASS


def test_unauthorized_runtime_rate_is_zero() -> None:
    summary = evaluate_workflows(
        build_observations()
    )

    result = metric(
        summary,
        "unauthorized_runtime_attempt_rate",
    )

    assert result.value == 0.0
    assert result.status is MetricStatus.PASS


def test_citation_manifest_is_complete() -> None:
    observations = build_observations()

    assert all(
        citation_manifest_complete(
            item.outcome
        )
        for item in observations
    )


def test_token_budget_metrics_pass() -> None:
    summary = evaluate_workflows(
        build_observations()
    )

    assert (
        metric(
            summary,
            "average_input_tokens",
        ).status
        is MetricStatus.PASS
    )
    assert (
        metric(
            summary,
            "average_output_tokens",
        ).status
        is MetricStatus.PASS
    )


def test_cost_budget_metric_passes() -> None:
    summary = evaluate_workflows(
        build_observations()
    )

    result = metric(
        summary,
        "average_model_cost_usd",
    )

    assert result.value == 0.01
    assert result.status is MetricStatus.PASS


def test_latency_slo_passes() -> None:
    summary = evaluate_workflows(
        build_observations()
    )

    result = metric(
        summary,
        "workflow_latency_p95_ms",
    )

    assert result.value == 700.0
    assert result.status is MetricStatus.PASS


def test_failed_metric_blocks_release_gate() -> None:
    observations = list(
        build_observations()
    )

    observations[0] = replace(
        observations[0],
        total_latency_ms=6000.0,
    )

    summary = evaluate_workflows(
        tuple(observations)
    )

    assert not release_gate_passed(summary)
    assert (
        "workflow_latency_p95_ms"
        in failed_metric_names(summary)
    )


def test_evidence_bundle_is_reproducible() -> None:
    summary = evaluate_workflows(
        build_observations()
    )

    first = build_release_evidence_bundle(
        release_id="release-test",
        summary=summary,
        artifact_payloads={
            "test-artifact.json": {
                "value": 1,
            }
        },
    )

    second = build_release_evidence_bundle(
        release_id="release-test",
        summary=summary,
        artifact_payloads={
            "test-artifact.json": {
                "value": 1,
            }
        },
    )

    assert (
        first.aggregate_sha256
        == second.aggregate_sha256
    )
    assert len(first.aggregate_sha256) == 64


def test_evidence_bundle_records_release_gate() -> None:
    summary = evaluate_workflows(
        build_observations()
    )

    bundle = build_release_evidence_bundle(
        release_id="release-test",
        summary=summary,
        artifact_payloads={
            "workflow-evidence.json": {
                "workflow_count":
                    summary.workflow_count,
            }
        },
    )

    assert bundle.bundle_version == BUNDLE_VERSION
    assert bundle.release_gate_passed
    assert not bundle.failed_metric_names
    assert bundle.artifact_count == 2


def test_evaluation_cannot_expand_authority() -> None:
    summary = evaluate_workflows(
        build_observations()
    )

    assert "cannot authorize" in (
        summary.authority_boundary
    )
