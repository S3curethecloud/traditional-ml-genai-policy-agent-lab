"""Operational alert classification."""

from __future__ import annotations

import hashlib

from incident_agent.operations.contracts import (
    AlertType,
    IncidentSeverity,
    OperationalAlert,
    SLOResult,
)


ALERT_TYPE_BY_SLO = {
    "availability-slo":
        AlertType.AVAILABILITY_DEGRADATION,
    "latency-slo":
        AlertType.LATENCY_DEGRADATION,
    "authorization-slo":
        AlertType.AUTHORIZATION_VIOLATION,
    "recovery-slo":
        AlertType.RECOVERY_OBJECTIVE_BREACH,
}


def _alert_id(
    release_id: str,
    environment: str,
    result: SLOResult,
) -> str:
    material = (
        f"{release_id}|{environment}|"
        f"{result.slo_id}|"
        f"{result.compliance_percentage}"
    ).encode("utf-8")

    return (
        "alert-"
        + hashlib.sha256(material).hexdigest()[:12]
    )


def classify_severity(
    result: SLOResult,
) -> IncidentSeverity:
    """Map failed SLO evidence to incident severity."""

    if result.slo_id == "authorization-slo":
        return IncidentSeverity.SEV_1

    if result.slo_id == "availability-slo":
        if result.compliance_percentage < 50.0:
            return IncidentSeverity.SEV_1
        return IncidentSeverity.SEV_2

    if result.slo_id == "latency-slo":
        return IncidentSeverity.SEV_2

    return IncidentSeverity.SEV_3


def create_alerts(
    release_id: str,
    environment: str,
    results: tuple[SLOResult, ...],
) -> tuple[OperationalAlert, ...]:
    """Create alerts only for failed SLO evaluations."""

    alerts: list[OperationalAlert] = []

    for result in results:
        if result.passed:
            continue

        alert_type = ALERT_TYPE_BY_SLO.get(
            result.slo_id,
            AlertType.UNKNOWN,
        )

        alerts.append(
            OperationalAlert(
                alert_id=_alert_id(
                    release_id,
                    environment,
                    result,
                ),
                alert_type=alert_type,
                severity=classify_severity(result),
                slo_id=result.slo_id,
                metric_name=result.metric_name,
                summary=(
                    f"{result.slo_id} achieved "
                    f"{result.compliance_percentage:.2f}% "
                    f"against target "
                    f"{result.target_percentage:.2f}%."
                ),
                evidence_references=(
                    result.slo_id,
                    result.metric_name,
                    result.error_budget_status.value,
                ),
            )
        )

    return tuple(alerts)
