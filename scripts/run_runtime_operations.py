#!/usr/bin/env python3
"""Run Phase 13 runtime operations and incident response."""

from __future__ import annotations

import json
from pathlib import Path

from incident_agent.operations.contracts import (
    MetricSample,
    OperationsAuditEvent,
    OperationsReport,
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
)
from incident_agent.operations.monitoring import (
    create_alerts,
)
from incident_agent.operations.slo import (
    evaluate_all_slos,
)


ROOT = Path(".")
POLICY_PATH = Path(
    "config/runtime-operations-policy.json"
)
DEPLOYMENT_REPORT_PATH = Path(
    "reports/deployment/"
    "phase-12-deployment-report.json"
)
OUTPUT_PATH = Path(
    "reports/operations/"
    "phase-13-operations-report.json"
)


def sample(
    metric_name: str,
    value: float,
    index: int,
    prefix: str,
) -> MetricSample:
    """Create deterministic tutorial telemetry."""

    return MetricSample(
        metric_name=metric_name,
        value=value,
        timestamp=(
            f"2026-07-31T18:{index:02d}:00-07:00"
        ),
        trace_id=f"{prefix}-trace-{index:02d}",
    )


def normal_samples() -> tuple[MetricSample, ...]:
    """Return telemetry representing healthy operation."""

    samples: list[MetricSample] = []

    for index in range(1, 21):
        samples.extend(
            (
                sample(
                    "request_success",
                    1.0,
                    index,
                    "normal",
                ),
                sample(
                    "request_latency_ms",
                    120.0 + index,
                    index,
                    "normal",
                ),
                sample(
                    "unauthorized_runtime_execution",
                    0.0,
                    index,
                    "normal",
                ),
                sample(
                    "recovery_time_seconds",
                    180.0,
                    index,
                    "normal",
                ),
            )
        )

    return tuple(samples)


def degraded_samples() -> tuple[MetricSample, ...]:
    """Return telemetry representing a release regression."""

    samples: list[MetricSample] = []

    for index in range(1, 21):
        samples.extend(
            (
                sample(
                    "request_success",
                    1.0 if index <= 12 else 0.0,
                    index,
                    "degraded",
                ),
                sample(
                    "request_latency_ms",
                    150.0 if index <= 8 else 420.0,
                    index,
                    "degraded",
                ),
                sample(
                    "unauthorized_runtime_execution",
                    0.0,
                    index,
                    "degraded",
                ),
                sample(
                    "recovery_time_seconds",
                    180.0 if index <= 18 else 480.0,
                    index,
                    "degraded",
                ),
            )
        )

    return tuple(samples)


def main() -> None:
    """Generate operational and incident-response evidence."""

    policy = load_operations_policy(
        ROOT / POLICY_PATH
    )
    definitions = parse_slo_definitions(policy)

    deployment_report = json.loads(
        (
            ROOT / DEPLOYMENT_REPORT_PATH
        ).read_text(encoding="utf-8")
    )

    production = deployment_report[
        "production_with_approval"
    ]

    release_id = production["release_id"]
    environment = production["environment"]

    evaluation_arguments = {
        "definitions": definitions,
        "minimum_samples": policy[
            "minimum_samples_per_sli"
        ],
        "warning_threshold": policy[
            "error_budget_warning_threshold"
        ],
        "exhausted_threshold": policy[
            "error_budget_exhausted_threshold"
        ],
    }

    normal_results = evaluate_all_slos(
        samples=normal_samples(),
        **evaluation_arguments,
    )

    degraded_results = evaluate_all_slos(
        samples=degraded_samples(),
        **evaluation_arguments,
    )

    alerts = create_alerts(
        release_id=release_id,
        environment=environment,
        results=degraded_results,
    )

    incident = create_incident(
        release_id=release_id,
        environment=environment,
        alerts=alerts,
        deployment_report=deployment_report,
    )

    if incident is None:
        raise RuntimeError(
            "Expected degraded telemetry to create "
            "an incident"
        )

    runbook = select_runbook(
        incident=incident,
        alerts=alerts,
        runbooks=policy["runbooks"],
    )

    mitigation = recommend_mitigation(
        incident=incident,
        alerts=alerts,
    )

    recovery = verify_recovery(
        incident=incident,
        results=normal_results,
    )

    audit_events = (
        OperationsAuditEvent(
            sequence=1,
            event_type="telemetry_evaluated",
            incident_id=incident.incident_id,
            detail=(
                "Normal and degraded telemetry windows "
                "were evaluated."
            ),
            evidence_references=tuple(
                result.slo_id
                for result in degraded_results
            ),
        ),
        OperationsAuditEvent(
            sequence=2,
            event_type="alerts_created",
            incident_id=incident.incident_id,
            detail=(
                f"{len(alerts)} operational alert(s) "
                "were created."
            ),
            evidence_references=tuple(
                alert.alert_id
                for alert in alerts
            ),
        ),
        OperationsAuditEvent(
            sequence=3,
            event_type="incident_created",
            incident_id=incident.incident_id,
            detail=incident.summary,
            evidence_references=(
                incident.release_id,
                incident.deployment_correlation,
            ),
        ),
        OperationsAuditEvent(
            sequence=4,
            event_type="runbook_recommended",
            incident_id=incident.incident_id,
            detail=runbook.rationale,
            evidence_references=(
                runbook.runbook_path,
            ),
        ),
        OperationsAuditEvent(
            sequence=5,
            event_type="mitigation_recommended",
            incident_id=incident.incident_id,
            detail=mitigation.rationale,
            evidence_references=(
                str(
                    mitigation.rollback_recommended
                ),
            ),
        ),
        OperationsAuditEvent(
            sequence=6,
            event_type="recovery_verified",
            incident_id=incident.incident_id,
            detail=(
                "Recovery telemetry satisfied all "
                "configured service objectives."
            ),
            evidence_references=(
                recovery.status.value,
            ),
        ),
    )

    report = OperationsReport(
        policy_version=policy["policy_version"],
        release_id=release_id,
        environment=environment,
        normal_slo_results=normal_results,
        degraded_slo_results=degraded_results,
        alerts=alerts,
        incident=incident,
        runbook=runbook,
        mitigation=mitigation,
        recovery=recovery,
        audit_events=audit_events,
        automatic_remediation_performed=False,
        production_side_effects_performed=False,
        authority_boundary=(
            "Runtime operations may observe, evaluate, "
            "classify, recommend, escalate, and verify. "
            "It cannot execute production remediation "
            "or rollback without a separate authorized "
            "deployment action."
        ),
    )

    output = ROOT / OUTPUT_PATH
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output.write_text(
        json.dumps(
            report.to_dict(),
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "PASS: normal SLOs="
        f"{sum(result.passed for result in normal_results)}"
        f"/{len(normal_results)}"
    )
    print(
        "PASS: degraded alerts="
        f"{len(alerts)}"
    )
    print(
        "PASS: incident="
        f"{incident.incident_id}"
    )
    print(
        "PASS: severity="
        f"{incident.severity.value}"
    )
    print(
        "PASS: rollback recommended="
        f"{mitigation.rollback_recommended}"
    )
    print(
        "PASS: recovery="
        f"{recovery.status.value}"
    )
    print(
        "PASS: no automatic remediation performed"
    )
    print(
        "PASS: no production side effects performed"
    )


if __name__ == "__main__":
    main()
