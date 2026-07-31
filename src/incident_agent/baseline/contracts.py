"""Typed contracts for the deterministic incident baseline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class IncidentCategory(StrEnum):
    """Supported incident classifications."""

    AUTHENTICATION_FAILURE = "authentication_failure"
    DEPLOYMENT_REGRESSION = "deployment_regression"
    INFRASTRUCTURE_SATURATION = "infrastructure_saturation"
    NETWORK_DEGRADATION = "network_degradation"
    DEPENDENCY_FAILURE = "dependency_failure"
    UNKNOWN = "unknown"


class IncidentSeverity(StrEnum):
    """Supported incident severity levels."""

    SEV_1 = "SEV-1"
    SEV_2 = "SEV-2"
    SEV_3 = "SEV-3"
    SEV_4 = "SEV-4"


@dataclass(frozen=True)
class IncidentFeatures:
    """Normalized incident features used by the baseline classifier."""

    login_failure_rate: float
    token_validation_error_rate: float
    http_5xx_rate: float
    latency_p95_ms: float
    cpu_utilization_percent: float
    memory_utilization_percent: float
    dependency_error_rate: float
    network_packet_loss_percent: float
    deployment_age_minutes: int | None
    affected_user_count: int
    regions_affected: int


@dataclass(frozen=True)
class RuleMatch:
    """A single deterministic rule evaluation result."""

    rule_id: str
    matched: bool
    reason: str


@dataclass(frozen=True)
class BaselineDecision:
    """Final deterministic baseline classification."""

    category: IncidentCategory
    severity: IncidentSeverity
    confidence: float
    matched_rules: tuple[RuleMatch, ...]
    classifier_version: str
