"""Evidence-bound incident-response decisions."""

from __future__ import annotations

import hashlib
from typing import Any

from incident_agent.operations.contracts import (
    AlertType,
    IncidentRecord,
    IncidentSeverity,
    IncidentStatus,
    MitigationRecommendation,
    OperationalAlert,
    RecoveryVerification,
    RunbookRecommendation,
    SLOResult,
)


SEVERITY_ORDER = {
    IncidentSeverity.SEV_1: 1,
    IncidentSeverity.SEV_2: 2,
    IncidentSeverity.SEV_3: 3,
}


def create_incident(
    release_id: str,
    environment: str,
    alerts: tuple[OperationalAlert, ...],
    deployment_report: dict[str, Any],
) -> IncidentRecord | None:
    """Create an incident when alerts are present."""

    if not alerts:
        return None

    severity = min(
        (alert.severity for alert in alerts),
        key=lambda value: SEVERITY_ORDER[value],
    )

    alert_ids = tuple(
        alert.alert_id
        for alert in alerts
    )

    material = (
        f"{release_id}|{environment}|"
        + "|".join(sorted(alert_ids))
    ).encode("utf-8")

    incident_id = (
        "incident-"
        + hashlib.sha256(material).hexdigest()[:12]
    )

    production = deployment_report.get(
        "production_with_approval",
        {}
    )

    deployment_correlation = (
        "correlated_to_current_release"
        if (
            production.get("release_id") == release_id
            and production.get("status") == "HEALTHY"
        )
        else "deployment_state_unconfirmed"
    )

    return IncidentRecord(
        incident_id=incident_id,
        release_id=release_id,
        environment=environment,
        severity=severity,
        status=IncidentStatus.INVESTIGATING,
        alert_ids=alert_ids,
        summary=(
            f"{len(alerts)} operational alert(s) "
            f"detected for {environment}."
        ),
        deployment_correlation=deployment_correlation,
        human_escalation_required=(
            environment == "production"
            or severity is IncidentSeverity.SEV_1
        ),
    )


def select_runbook(
    incident: IncidentRecord,
    alerts: tuple[OperationalAlert, ...],
    runbooks: dict[str, str],
) -> RunbookRecommendation:
    """Select a runbook without executing it."""

    alert_types = {
        alert.alert_type
        for alert in alerts
    }

    if AlertType.AUTHORIZATION_VIOLATION in alert_types:
        key = "authorization_violation"
        rationale = (
            "Authorization violations take precedence "
            "because they indicate an authority-boundary "
            "failure."
        )
    elif (
        AlertType.AVAILABILITY_DEGRADATION
        in alert_types
    ):
        key = "availability_degradation"
        rationale = (
            "Availability evidence indicates service "
            "degradation."
        )
    elif AlertType.LATENCY_DEGRADATION in alert_types:
        key = "latency_degradation"
        rationale = (
            "Latency evidence exceeds the configured "
            "objective."
        )
    elif (
        AlertType.RECOVERY_OBJECTIVE_BREACH
        in alert_types
    ):
        key = "deployment_regression"
        rationale = (
            "Recovery evidence supports reviewing the "
            "deployment rollback plan."
        )
    else:
        key = "unknown"
        rationale = (
            "No specialized runbook matched the evidence."
        )

    return RunbookRecommendation(
        incident_id=incident.incident_id,
        runbook_path=runbooks[key],
        rationale=rationale,
        automatic_execution_allowed=False,
    )


def recommend_mitigation(
    incident: IncidentRecord,
    alerts: tuple[OperationalAlert, ...],
) -> MitigationRecommendation:
    """Recommend rollback or escalation without execution."""

    types = {
        alert.alert_type
        for alert in alerts
    }

    rollback_recommended = (
        incident.deployment_correlation
        == "correlated_to_current_release"
        and (
            AlertType.AVAILABILITY_DEGRADATION in types
            or AlertType.LATENCY_DEGRADATION in types
            or AlertType.RECOVERY_OBJECTIVE_BREACH in types
        )
    )

    if AlertType.AUTHORIZATION_VIOLATION in types:
        rationale = (
            "Escalate immediately and isolate runtime "
            "access. Rollback alone may not correct an "
            "authorization-boundary violation."
        )
    elif rollback_recommended:
        rationale = (
            "Current-release correlation and failed "
            "service objectives support a rollback "
            "recommendation."
        )
    else:
        rationale = (
            "Continue human-led investigation before "
            "changing runtime state."
        )

    return MitigationRecommendation(
        incident_id=incident.incident_id,
        rollback_recommended=rollback_recommended,
        human_approval_required=True,
        rationale=rationale,
    )


def verify_recovery(
    incident: IncidentRecord,
    results: tuple[SLOResult, ...],
) -> RecoveryVerification:
    """Verify whether every evaluated SLO recovered."""

    recovered = tuple(
        result.slo_id
        for result in results
        if result.passed
    )

    failed = tuple(
        result.slo_id
        for result in results
        if not result.passed
    )

    all_recovered = not failed

    return RecoveryVerification(
        incident_id=incident.incident_id,
        recovered=all_recovered,
        recovered_slo_ids=recovered,
        failed_slo_ids=failed,
        status=(
            IncidentStatus.RECOVERED
            if all_recovered
            else IncidentStatus.ESCALATED
        ),
    )
