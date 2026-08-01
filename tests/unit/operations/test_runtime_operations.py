"""Tests for Phase 13 runtime operations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from incident_agent.operations.contracts import (
    AlertType,
    ComparisonOperator,
    ErrorBudgetStatus,
    IncidentSeverity,
    IncidentStatus,
    MetricSample,
    SLODefinition,
)
from incident_agent.operations.incident_response import (
    create_incident,
    recommend_mitigation,
    select_runbook,
    verify_recovery,
)
from incident_agent.operations.loading import (
    load_operations_policy,
    parse_slo_definitions,
    policy_sha256,
)
from incident_agent.operations.monitoring import (
    classify_severity,
    create_alerts,
)
from incident_agent.operations.slo import (
    evaluate_all_slos,
    evaluate_slo,
    sample_is_compliant,
)


POLICY_PATH = Path(
    "config/runtime-operations-policy.json"
)
DEPLOYMENT_REPORT_PATH = Path(
    "reports/deployment/"
    "phase-12-deployment-report.json"
)


def policy():
    return load_operations_policy(POLICY_PATH)


def deployment_report():
    return json.loads(
        DEPLOYMENT_REPORT_PATH.read_text(
            encoding="utf-8"
        )
    )


def definition(
    slo_id: str = "availability-slo",
    metric_name: str = "request_success",
    comparison: ComparisonOperator = (
        ComparisonOperator.GTE
    ),
    threshold: float = 1.0,
    target: float = 75.0,
) -> SLODefinition:
    return SLODefinition(
        slo_id=slo_id,
        metric_name=metric_name,
        description="Test objective",
        comparison=comparison,
        threshold=threshold,
        target_percentage=target,
    )


def samples(
    metric_name: str,
    values: tuple[float, ...],
) -> tuple[MetricSample, ...]:
    return tuple(
        MetricSample(
            metric_name=metric_name,
            value=value,
            timestamp=f"timestamp-{index}",
            trace_id=f"trace-{index}",
        )
        for index, value in enumerate(
            values,
            start=1,
        )
    )


def evaluate(
    slo_definition: SLODefinition,
    metric_samples: tuple[MetricSample, ...],
):
    return evaluate_slo(
        definition=slo_definition,
        samples=metric_samples,
        minimum_samples=4,
        warning_threshold=0.5,
        exhausted_threshold=1.0,
    )


def test_operations_policy_loads() -> None:
    loaded = policy()

    assert (
        loaded["policy_version"]
        == "runtime-operations-policy-v1"
    )


def test_automatic_remediation_is_disabled() -> None:
    loaded = policy()

    assert not loaded[
        "automatic_remediation_allowed"
    ]
    assert not loaded[
        "automatic_rollback_allowed"
    ]


def test_policy_digest_is_reproducible() -> None:
    loaded = policy()

    assert policy_sha256(loaded) == policy_sha256(
        loaded
    )


def test_four_slo_definitions_load() -> None:
    definitions = parse_slo_definitions(policy())

    assert len(definitions) == 4
    assert len(
        {item.slo_id for item in definitions}
    ) == 4


def test_gte_comparison_passes() -> None:
    item = samples(
        "request_success",
        (1.0,),
    )[0]

    assert sample_is_compliant(
        definition(),
        item,
    )


def test_lte_comparison_passes() -> None:
    latency = definition(
        slo_id="latency-slo",
        metric_name="request_latency_ms",
        comparison=ComparisonOperator.LTE,
        threshold=200.0,
        target=95.0,
    )

    item = samples(
        "request_latency_ms",
        (150.0,),
    )[0]

    assert sample_is_compliant(latency, item)


def test_eq_comparison_passes() -> None:
    authorization = definition(
        slo_id="authorization-slo",
        metric_name=(
            "unauthorized_runtime_execution"
        ),
        comparison=ComparisonOperator.EQ,
        threshold=0.0,
        target=100.0,
    )

    item = samples(
        "unauthorized_runtime_execution",
        (0.0,),
    )[0]

    assert sample_is_compliant(
        authorization,
        item,
    )


def test_insufficient_samples_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Insufficient samples",
    ):
        evaluate(
            definition(),
            samples(
                "request_success",
                (1.0, 1.0, 1.0),
            ),
        )


def test_passing_slo_has_healthy_budget() -> None:
    result = evaluate(
        definition(target=75.0),
        samples(
            "request_success",
            (1.0, 1.0, 1.0, 1.0),
        ),
    )

    assert result.passed
    assert (
        result.error_budget_status
        is ErrorBudgetStatus.HEALTHY
    )


def test_failed_slo_exhausts_budget() -> None:
    result = evaluate(
        definition(target=99.0),
        samples(
            "request_success",
            (1.0, 0.0, 0.0, 0.0),
        ),
    )

    assert not result.passed
    assert (
        result.error_budget_status
        is ErrorBudgetStatus.EXHAUSTED
    )


def test_all_slos_are_evaluated() -> None:
    definitions = parse_slo_definitions(policy())

    metric_samples = []

    for index in range(4):
        metric_samples.extend(
            (
                MetricSample(
                    "request_success",
                    1.0,
                    str(index),
                    f"a-{index}",
                ),
                MetricSample(
                    "request_latency_ms",
                    100.0,
                    str(index),
                    f"b-{index}",
                ),
                MetricSample(
                    "unauthorized_runtime_execution",
                    0.0,
                    str(index),
                    f"c-{index}",
                ),
                MetricSample(
                    "recovery_time_seconds",
                    200.0,
                    str(index),
                    f"d-{index}",
                ),
            )
        )

    results = evaluate_all_slos(
        definitions=definitions,
        samples=tuple(metric_samples),
        minimum_samples=4,
        warning_threshold=0.5,
        exhausted_threshold=1.0,
    )

    assert len(results) == 4
    assert all(result.passed for result in results)


def test_only_failed_slos_create_alerts() -> None:
    passing = evaluate(
        definition(target=75.0),
        samples(
            "request_success",
            (1.0, 1.0, 1.0, 1.0),
        ),
    )
    failing = evaluate(
        definition(
            slo_id="latency-slo",
            metric_name="request_latency_ms",
            comparison=ComparisonOperator.LTE,
            threshold=200.0,
            target=95.0,
        ),
        samples(
            "request_latency_ms",
            (100.0, 300.0, 300.0, 300.0),
        ),
    )

    alerts = create_alerts(
        release_id="release-test",
        environment="production",
        results=(passing, failing),
    )

    assert len(alerts) == 1
    assert (
        alerts[0].alert_type
        is AlertType.LATENCY_DEGRADATION
    )


def test_authorization_violation_is_sev_1() -> None:
    result = evaluate(
        definition(
            slo_id="authorization-slo",
            metric_name=(
                "unauthorized_runtime_execution"
            ),
            comparison=ComparisonOperator.EQ,
            threshold=0.0,
            target=100.0,
        ),
        samples(
            "unauthorized_runtime_execution",
            (0.0, 0.0, 1.0, 0.0),
        ),
    )

    assert (
        classify_severity(result)
        is IncidentSeverity.SEV_1
    )


def test_no_alerts_create_no_incident() -> None:
    incident = create_incident(
        release_id="release-test",
        environment="production",
        alerts=(),
        deployment_report=deployment_report(),
    )

    assert incident is None


def test_failed_alerts_create_incident() -> None:
    failed = evaluate(
        definition(target=99.0),
        samples(
            "request_success",
            (1.0, 0.0, 0.0, 0.0),
        ),
    )

    alerts = create_alerts(
        release_id="phase-12-tutorial-release",
        environment="production",
        results=(failed,),
    )

    incident = create_incident(
        release_id="phase-12-tutorial-release",
        environment="production",
        alerts=alerts,
        deployment_report=deployment_report(),
    )

    assert incident is not None
    assert (
        incident.status
        is IncidentStatus.INVESTIGATING
    )
    assert incident.human_escalation_required


def test_incident_correlates_to_current_release() -> None:
    failed = evaluate(
        definition(target=99.0),
        samples(
            "request_success",
            (1.0, 0.0, 0.0, 0.0),
        ),
    )
    alerts = create_alerts(
        release_id="phase-12-tutorial-release",
        environment="production",
        results=(failed,),
    )

    incident = create_incident(
        release_id="phase-12-tutorial-release",
        environment="production",
        alerts=alerts,
        deployment_report=deployment_report(),
    )

    assert incident is not None
    assert (
        incident.deployment_correlation
        == "correlated_to_current_release"
    )


def test_availability_runbook_is_selected() -> None:
    failed = evaluate(
        definition(target=99.0),
        samples(
            "request_success",
            (1.0, 0.0, 0.0, 0.0),
        ),
    )
    alerts = create_alerts(
        release_id="phase-12-tutorial-release",
        environment="production",
        results=(failed,),
    )
    incident = create_incident(
        release_id="phase-12-tutorial-release",
        environment="production",
        alerts=alerts,
        deployment_report=deployment_report(),
    )

    assert incident is not None

    runbook = select_runbook(
        incident=incident,
        alerts=alerts,
        runbooks=policy()["runbooks"],
    )

    assert (
        runbook.runbook_path
        == "runbooks/availability-degradation.md"
    )
    assert not runbook.automatic_execution_allowed


def test_release_correlation_can_recommend_rollback() -> None:
    failed = evaluate(
        definition(target=99.0),
        samples(
            "request_success",
            (1.0, 0.0, 0.0, 0.0),
        ),
    )
    alerts = create_alerts(
        release_id="phase-12-tutorial-release",
        environment="production",
        results=(failed,),
    )
    incident = create_incident(
        release_id="phase-12-tutorial-release",
        environment="production",
        alerts=alerts,
        deployment_report=deployment_report(),
    )

    assert incident is not None

    recommendation = recommend_mitigation(
        incident=incident,
        alerts=alerts,
    )

    assert recommendation.rollback_recommended
    assert recommendation.human_approval_required


def test_recovery_requires_all_slos_to_pass() -> None:
    failed = evaluate(
        definition(target=99.0),
        samples(
            "request_success",
            (1.0, 0.0, 0.0, 0.0),
        ),
    )
    alerts = create_alerts(
        release_id="phase-12-tutorial-release",
        environment="production",
        results=(failed,),
    )
    incident = create_incident(
        release_id="phase-12-tutorial-release",
        environment="production",
        alerts=alerts,
        deployment_report=deployment_report(),
    )

    assert incident is not None

    recovery = verify_recovery(
        incident=incident,
        results=(failed,),
    )

    assert not recovery.recovered
    assert recovery.status is IncidentStatus.ESCALATED


def test_recovery_passes_when_all_slos_pass() -> None:
    passed = evaluate(
        definition(target=75.0),
        samples(
            "request_success",
            (1.0, 1.0, 1.0, 1.0),
        ),
    )
    alerts = create_alerts(
        release_id="phase-12-tutorial-release",
        environment="production",
        results=(
            evaluate(
                definition(target=99.0),
                samples(
                    "request_success",
                    (1.0, 0.0, 0.0, 0.0),
                ),
            ),
        ),
    )
    incident = create_incident(
        release_id="phase-12-tutorial-release",
        environment="production",
        alerts=alerts,
        deployment_report=deployment_report(),
    )

    assert incident is not None

    recovery = verify_recovery(
        incident=incident,
        results=(passed,),
    )

    assert recovery.recovered
    assert recovery.status is IncidentStatus.RECOVERED
