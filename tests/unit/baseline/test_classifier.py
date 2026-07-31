"""Tests for the deterministic incident-classification baseline."""

from incident_agent.baseline.classifier import (
    CLASSIFIER_VERSION,
    classify_incident,
)
from incident_agent.baseline.contracts import (
    IncidentCategory,
    IncidentFeatures,
    IncidentSeverity,
)


def make_features(**overrides: object) -> IncidentFeatures:
    values: dict[str, object] = {
        "login_failure_rate": 0.01,
        "token_validation_error_rate": 0.01,
        "http_5xx_rate": 0.01,
        "latency_p95_ms": 250.0,
        "cpu_utilization_percent": 40.0,
        "memory_utilization_percent": 45.0,
        "dependency_error_rate": 0.01,
        "network_packet_loss_percent": 0.1,
        "deployment_age_minutes": None,
        "affected_user_count": 10,
        "regions_affected": 1,
    }
    values.update(overrides)
    return IncidentFeatures(**values)


def test_recent_deployment_with_failures_is_deployment_regression() -> None:
    result = classify_incident(
        make_features(
            login_failure_rate=0.20,
            http_5xx_rate=0.12,
            deployment_age_minutes=15,
            affected_user_count=1_500,
        )
    )

    assert result.category is IncidentCategory.DEPLOYMENT_REGRESSION
    assert result.severity is IncidentSeverity.SEV_2
    assert result.confidence >= 0.70
    assert result.classifier_version == CLASSIFIER_VERSION


def test_token_errors_and_login_failures_are_authentication_failure() -> None:
    result = classify_incident(
        make_features(
            login_failure_rate=0.18,
            token_validation_error_rate=0.11,
            affected_user_count=300,
        )
    )

    assert result.category is IncidentCategory.AUTHENTICATION_FAILURE
    assert result.severity is IncidentSeverity.SEV_3


def test_cpu_saturation_is_infrastructure_saturation() -> None:
    result = classify_incident(
        make_features(
            cpu_utilization_percent=96.0,
            affected_user_count=250,
        )
    )

    assert result.category is IncidentCategory.INFRASTRUCTURE_SATURATION


def test_packet_loss_is_network_degradation() -> None:
    result = classify_incident(
        make_features(
            network_packet_loss_percent=5.5,
            affected_user_count=150,
        )
    )

    assert result.category is IncidentCategory.NETWORK_DEGRADATION


def test_dependency_errors_are_dependency_failure() -> None:
    result = classify_incident(
        make_features(
            dependency_error_rate=0.15,
            affected_user_count=200,
        )
    )

    assert result.category is IncidentCategory.DEPENDENCY_FAILURE


def test_no_matching_rule_returns_unknown() -> None:
    result = classify_incident(make_features())

    assert result.category is IncidentCategory.UNKNOWN
    assert result.severity is IncidentSeverity.SEV_4
    assert result.confidence == 0.0
    assert result.matched_rules == ()


def test_priority_is_deterministic_when_multiple_rules_match() -> None:
    result = classify_incident(
        make_features(
            login_failure_rate=0.25,
            token_validation_error_rate=0.12,
            http_5xx_rate=0.15,
            deployment_age_minutes=10,
            dependency_error_rate=0.20,
        )
    )

    assert result.category is IncidentCategory.DEPLOYMENT_REGRESSION
    assert len(result.matched_rules) == 3
    assert result.confidence == 0.95


def test_large_multi_region_incident_is_sev_1() -> None:
    result = classify_incident(
        make_features(
            dependency_error_rate=0.20,
            affected_user_count=15_000,
            regions_affected=4,
        )
    )

    assert result.severity is IncidentSeverity.SEV_1
