"""Transparent deterministic incident classification baseline."""

from __future__ import annotations

from incident_agent.baseline.contracts import (
    BaselineDecision,
    IncidentCategory,
    IncidentFeatures,
    IncidentSeverity,
    RuleMatch,
)

CLASSIFIER_VERSION = "deterministic-baseline-v1"


def classify_incident(features: IncidentFeatures) -> BaselineDecision:
    """Classify an incident using explicit and inspectable rules."""

    rule_results = (
        _deployment_regression_rule(features),
        _authentication_failure_rule(features),
        _infrastructure_saturation_rule(features),
        _network_degradation_rule(features),
        _dependency_failure_rule(features),
    )

    matched = tuple(result for result in rule_results if result.matched)

    category = _select_category(matched)
    severity = _calculate_severity(features)
    confidence = _calculate_confidence(category, matched)

    return BaselineDecision(
        category=category,
        severity=severity,
        confidence=confidence,
        matched_rules=matched,
        classifier_version=CLASSIFIER_VERSION,
    )


def _deployment_regression_rule(features: IncidentFeatures) -> RuleMatch:
    recent_deployment = (
        features.deployment_age_minutes is not None
        and features.deployment_age_minutes <= 30
    )
    elevated_failures = (
        features.login_failure_rate >= 0.10
        or features.http_5xx_rate >= 0.08
    )

    matched = recent_deployment and elevated_failures

    return RuleMatch(
        rule_id="deployment-regression-001",
        matched=matched,
        reason=(
            "A deployment occurred within 30 minutes and failure rates are elevated."
            if matched
            else "No recent deployment and elevated failure-rate combination was found."
        ),
    )


def _authentication_failure_rule(features: IncidentFeatures) -> RuleMatch:
    matched = (
        features.login_failure_rate >= 0.10
        and features.token_validation_error_rate >= 0.05
    )

    return RuleMatch(
        rule_id="authentication-failure-001",
        matched=matched,
        reason=(
            "Login failures and token-validation errors exceed thresholds."
            if matched
            else "Authentication-specific thresholds were not both exceeded."
        ),
    )


def _infrastructure_saturation_rule(features: IncidentFeatures) -> RuleMatch:
    matched = (
        features.cpu_utilization_percent >= 90.0
        or features.memory_utilization_percent >= 90.0
    )

    return RuleMatch(
        rule_id="infrastructure-saturation-001",
        matched=matched,
        reason=(
            "CPU or memory utilization exceeds 90 percent."
            if matched
            else "Infrastructure utilization remains below saturation thresholds."
        ),
    )


def _network_degradation_rule(features: IncidentFeatures) -> RuleMatch:
    matched = features.network_packet_loss_percent >= 3.0

    return RuleMatch(
        rule_id="network-degradation-001",
        matched=matched,
        reason=(
            "Packet loss exceeds the 3 percent degradation threshold."
            if matched
            else "Packet loss remains below the degradation threshold."
        ),
    )


def _dependency_failure_rule(features: IncidentFeatures) -> RuleMatch:
    matched = features.dependency_error_rate >= 0.08

    return RuleMatch(
        rule_id="dependency-failure-001",
        matched=matched,
        reason=(
            "Dependency error rate exceeds the configured threshold."
            if matched
            else "Dependency errors remain below the configured threshold."
        ),
    )


def _select_category(
    matched_rules: tuple[RuleMatch, ...],
) -> IncidentCategory:
    priority = (
        ("deployment-regression-001", IncidentCategory.DEPLOYMENT_REGRESSION),
        ("authentication-failure-001", IncidentCategory.AUTHENTICATION_FAILURE),
        (
            "infrastructure-saturation-001",
            IncidentCategory.INFRASTRUCTURE_SATURATION,
        ),
        ("network-degradation-001", IncidentCategory.NETWORK_DEGRADATION),
        ("dependency-failure-001", IncidentCategory.DEPENDENCY_FAILURE),
    )

    matched_rule_ids = {rule.rule_id for rule in matched_rules}

    for rule_id, category in priority:
        if rule_id in matched_rule_ids:
            return category

    return IncidentCategory.UNKNOWN


def _calculate_severity(features: IncidentFeatures) -> IncidentSeverity:
    if (
        features.affected_user_count >= 10_000
        or features.regions_affected >= 3
        or features.http_5xx_rate >= 0.50
    ):
        return IncidentSeverity.SEV_1

    if (
        features.affected_user_count >= 1_000
        or features.regions_affected >= 2
        or features.http_5xx_rate >= 0.20
    ):
        return IncidentSeverity.SEV_2

    if (
        features.affected_user_count >= 100
        or features.login_failure_rate >= 0.10
        or features.latency_p95_ms >= 2_000
    ):
        return IncidentSeverity.SEV_3

    return IncidentSeverity.SEV_4


def _calculate_confidence(
    category: IncidentCategory,
    matched_rules: tuple[RuleMatch, ...],
) -> float:
    if category is IncidentCategory.UNKNOWN:
        return 0.0

    if len(matched_rules) >= 3:
        return 0.95

    if len(matched_rules) == 2:
        return 0.85

    return 0.70
