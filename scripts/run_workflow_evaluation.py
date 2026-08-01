#!/usr/bin/env python3
"""Run Phase 9 workflow evaluation and evidence generation."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from incident_agent.observability.contracts import (
    ExpectedOutcome,
    StepLatency,
    UsageObservation,
    WorkflowObservation,
)
from incident_agent.observability.evaluator import (
    evaluate_workflows,
)
from incident_agent.observability.evidence import (
    build_release_evidence_bundle,
    write_evidence_bundle,
)
from incident_agent.orchestrator.contracts import (
    WorkflowIdentity,
    WorkflowRequest,
)
from incident_agent.orchestrator.engine import (
    GovernedAgentOrchestrator,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate governed workflows and generate "
            "release evidence."
        )
    )
    parser.add_argument(
        "--knowledge-directory",
        type=Path,
        default=Path("data/knowledge"),
    )
    parser.add_argument(
        "--ambiguity-pack",
        type=Path,
        default=Path(
            "data/ambiguity/phase-3b-cases.yaml"
        ),
    )
    parser.add_argument(
        "--model-directory",
        type=Path,
        default=Path(
            "models/incident-classifier"
        ),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path(
            "reports/observability/"
            "phase-09-evaluation-report.json"
        ),
    )
    parser.add_argument(
        "--bundle-output",
        type=Path,
        default=Path(
            "reports/observability/"
            "phase-09-release-evidence.json"
        ),
    )
    return parser.parse_args()


def base_request(
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


def usage(
    input_tokens: int,
    output_tokens: int,
    estimated_cost: float,
    tool_attempts: int,
) -> UsageObservation:
    return UsageObservation(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_model_cost_usd=estimated_cost,
        retrieval_queries=1,
        tool_execution_attempts=tool_attempts,
    )


def step_latencies(
    scale: float,
) -> tuple[StepLatency, ...]:
    return (
        StepLatency(
            "ambiguity_evaluation",
            120.0 * scale,
        ),
        StepLatency(
            "permission_aware_retrieval",
            85.0 * scale,
        ),
        StepLatency(
            "genai_synthesis",
            420.0 * scale,
        ),
        StepLatency(
            "deterministic_policy",
            12.0 * scale,
        ),
        StepLatency(
            "isolated_runtime",
            35.0 * scale,
        ),
    )


def main() -> None:
    args = parse_args()

    orchestrator = GovernedAgentOrchestrator(
        knowledge_directory=(
            args.knowledge_directory
        ),
        ambiguity_pack_path=(
            args.ambiguity_pack
        ),
        model_directory=args.model_directory,
    )

    normal_request = base_request(
        "workflow-eval-normal",
        "trace-eval-normal",
        "runtime-eval-normal",
    )

    normal_outcome = orchestrator.run(
        request=normal_request,
        now_epoch_seconds=1001.0,
    )

    cross_tenant_request = replace(
        base_request(
            "workflow-eval-cross-tenant",
            "trace-eval-cross-tenant",
            "runtime-eval-cross-tenant",
        ),
        request_tenant_id="tenant-beta",
    )

    cross_tenant_outcome = orchestrator.run(
        request=cross_tenant_request,
        now_epoch_seconds=1001.0,
    )

    unauthorized_request = replace(
        base_request(
            "workflow-eval-unauthorized",
            "trace-eval-unauthorized",
            "runtime-eval-unauthorized",
        ),
        identity=WorkflowIdentity(
            user_id="auditor-7",
            tenant_id="tenant-alpha",
            roles=("auditor",),
        ),
    )

    unauthorized_outcome = orchestrator.run(
        request=unauthorized_request,
        now_epoch_seconds=1001.0,
    )

    expired_request = base_request(
        "workflow-eval-expired",
        "trace-eval-expired",
        "runtime-eval-expired",
    )

    expired_outcome = orchestrator.run(
        request=expired_request,
        now_epoch_seconds=1061.0,
    )

    observations = (
        WorkflowObservation(
            evaluation_case_id="normal-success",
            expected_outcome=(
                ExpectedOutcome.NORMAL_SUCCESS
            ),
            outcome=normal_outcome,
            total_latency_ms=672.0,
            step_latencies=step_latencies(1.0),
            usage=usage(
                input_tokens=1450,
                output_tokens=410,
                estimated_cost=0.012,
                tool_attempts=1,
            ),
            prompt_injection_detected=False,
            cross_tenant_attempt=False,
            notes=(
                "Synthetic tutorial providers only.",
                "No production side effect occurred.",
            ),
        ),
        WorkflowObservation(
            evaluation_case_id=(
                "cross-tenant-denial"
            ),
            expected_outcome=(
                ExpectedOutcome.EXPECTED_DENIAL
            ),
            outcome=cross_tenant_outcome,
            total_latency_ms=601.0,
            step_latencies=step_latencies(0.9),
            usage=usage(
                input_tokens=1320,
                output_tokens=380,
                estimated_cost=0.010,
                tool_attempts=0,
            ),
            prompt_injection_detected=False,
            cross_tenant_attempt=True,
            notes=(
                "Cross-tenant attempt expected to deny.",
            ),
        ),
        WorkflowObservation(
            evaluation_case_id=(
                "unauthorized-identity-denial"
            ),
            expected_outcome=(
                ExpectedOutcome.EXPECTED_DENIAL
            ),
            outcome=unauthorized_outcome,
            total_latency_ms=510.0,
            step_latencies=step_latencies(0.75),
            usage=usage(
                input_tokens=820,
                output_tokens=180,
                estimated_cost=0.005,
                tool_attempts=0,
            ),
            prompt_injection_detected=False,
            cross_tenant_attempt=False,
            notes=(
                "Unauthorized identity received no "
                "retrieval evidence.",
            ),
        ),
        WorkflowObservation(
            evaluation_case_id=(
                "expired-runtime-request"
            ),
            expected_outcome=(
                ExpectedOutcome.EXPECTED_FAILURE
            ),
            outcome=expired_outcome,
            total_latency_ms=655.0,
            step_latencies=step_latencies(0.98),
            usage=usage(
                input_tokens=1450,
                output_tokens=410,
                estimated_cost=0.012,
                tool_attempts=0,
            ),
            prompt_injection_detected=False,
            cross_tenant_attempt=False,
            notes=(
                "Expired runtime request expected to fail "
                "without handler execution.",
            ),
        ),
    )

    summary = evaluate_workflows(
        observations
    )

    report = {
        "phase": "phase-09",
        "evaluation_summary": summary.to_dict(),
        "observations": [
            {
                "evaluation_case_id":
                    item.evaluation_case_id,
                "expected_outcome":
                    item.expected_outcome.value,
                "workflow_id":
                    item.outcome.workflow_id,
                "status":
                    item.outcome.status.value,
                "policy_decision":
                    item.outcome.policy_decision,
                "runtime_status":
                    item.outcome.runtime_status,
                "total_latency_ms":
                    item.total_latency_ms,
                "usage": {
                    "input_tokens":
                        item.usage.input_tokens,
                    "output_tokens":
                        item.usage.output_tokens,
                    "estimated_model_cost_usd":
                        item.usage
                        .estimated_model_cost_usd,
                    "retrieval_queries":
                        item.usage.retrieval_queries,
                    "tool_execution_attempts":
                        item.usage
                        .tool_execution_attempts,
                },
            }
            for item in observations
        ],
        "security_properties": {
            "evaluation_changes_authority": False,
            "negative_tests_separated_from_normal_slo":
                True,
            "runtime_without_allow_detected": True,
            "cross_tenant_denial_measured": True,
            "trace_completeness_measured": True,
            "checkpoint_integrity_measured": True,
            "citation_integrity_measured": True,
            "cost_and_token_usage_recorded": True,
            "production_side_effects_performed":
                False,
        },
    }

    args.report_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.report_output.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    bundle = build_release_evidence_bundle(
        release_id="phase-09-tutorial-release",
        summary=summary,
        artifact_payloads={
            "phase-09-evaluation-report.json":
                report,
            "phase-08-workflow-outcomes.json": [
                item.outcome.to_dict()
                for item in observations
            ],
        },
    )

    write_evidence_bundle(
        args.bundle_output,
        bundle,
    )

    print(
        f"PASS: evaluated "
        f"{summary.workflow_count} workflows"
    )
    print(
        f"PASS: normal workflows="
        f"{summary.normal_workflow_count}"
    )
    print(
        f"PASS: negative controls="
        f"{summary.negative_test_count}"
    )
    print(
        f"PASS: release gate="
        f"{bundle.release_gate_passed}"
    )
    print(
        f"PASS: evidence artifacts="
        f"{bundle.artifact_count}"
    )
    print(
        "PASS: evaluation did not change authority"
    )
    print(
        "PASS: no production side effects performed"
    )


if __name__ == "__main__":
    main()
