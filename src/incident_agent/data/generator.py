"""Reproducible synthetic incident dataset generation."""

from __future__ import annotations

import random
from collections.abc import Callable

from incident_agent.baseline.contracts import (
    IncidentCategory,
    IncidentFeatures,
    IncidentSeverity,
)
from incident_agent.data.contracts import SyntheticIncident


DEFAULT_RANDOM_SEED = 42
DEFAULT_RECORDS_PER_CATEGORY = 100


def generate_balanced_dataset(
    records_per_category: int = DEFAULT_RECORDS_PER_CATEGORY,
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> list[SyntheticIncident]:
    """Generate an exactly balanced synthetic incident dataset."""

    if records_per_category < 10:
        raise ValueError("records_per_category must be at least 10")

    rng = random.Random(random_seed)
    incidents: list[SyntheticIncident] = []

    generators: dict[
        IncidentCategory,
        Callable[[random.Random], IncidentFeatures],
    ] = {
        IncidentCategory.AUTHENTICATION_FAILURE:
            _authentication_failure_features,
        IncidentCategory.DEPLOYMENT_REGRESSION:
            _deployment_regression_features,
        IncidentCategory.INFRASTRUCTURE_SATURATION:
            _infrastructure_saturation_features,
        IncidentCategory.NETWORK_DEGRADATION:
            _network_degradation_features,
        IncidentCategory.DEPENDENCY_FAILURE:
            _dependency_failure_features,
        IncidentCategory.UNKNOWN:
            _unknown_features,
    }

    for category, feature_generator in generators.items():
        for category_index in range(records_per_category):
            features = feature_generator(rng)
            severity = _derive_severity(features)

            incidents.append(
                SyntheticIncident(
                    incident_id=(
                        f"{category.value}-{category_index + 1:05d}"
                    ),
                    features=features,
                    category=category,
                    severity=severity,
                )
            )

    rng.shuffle(incidents)
    return incidents


def _authentication_failure_features(
    rng: random.Random,
) -> IncidentFeatures:
    return IncidentFeatures(
        login_failure_rate=_rate(rng, 0.12, 0.55),
        token_validation_error_rate=_rate(rng, 0.06, 0.40),
        http_5xx_rate=_rate(rng, 0.01, 0.15),
        latency_p95_ms=_float(rng, 500.0, 2_500.0),
        cpu_utilization_percent=_float(rng, 25.0, 80.0),
        memory_utilization_percent=_float(rng, 30.0, 82.0),
        dependency_error_rate=_rate(rng, 0.00, 0.06),
        network_packet_loss_percent=_float(rng, 0.0, 1.5),
        deployment_age_minutes=_optional_deployment_age(
            rng,
            present_probability=0.15,
            minimum=45,
            maximum=1_440,
        ),
        affected_user_count=rng.randint(100, 8_000),
        regions_affected=rng.randint(1, 3),
    )


def _deployment_regression_features(
    rng: random.Random,
) -> IncidentFeatures:
    return IncidentFeatures(
        login_failure_rate=_rate(rng, 0.10, 0.45),
        token_validation_error_rate=_rate(rng, 0.01, 0.20),
        http_5xx_rate=_rate(rng, 0.08, 0.45),
        latency_p95_ms=_float(rng, 800.0, 4_000.0),
        cpu_utilization_percent=_float(rng, 30.0, 88.0),
        memory_utilization_percent=_float(rng, 35.0, 88.0),
        dependency_error_rate=_rate(rng, 0.00, 0.08),
        network_packet_loss_percent=_float(rng, 0.0, 1.5),
        deployment_age_minutes=rng.randint(1, 30),
        affected_user_count=rng.randint(250, 12_000),
        regions_affected=rng.randint(1, 4),
    )


def _infrastructure_saturation_features(
    rng: random.Random,
) -> IncidentFeatures:
    return IncidentFeatures(
        login_failure_rate=_rate(rng, 0.01, 0.14),
        token_validation_error_rate=_rate(rng, 0.00, 0.04),
        http_5xx_rate=_rate(rng, 0.05, 0.35),
        latency_p95_ms=_float(rng, 1_500.0, 8_000.0),
        cpu_utilization_percent=_float(rng, 90.0, 100.0),
        memory_utilization_percent=_float(rng, 82.0, 100.0),
        dependency_error_rate=_rate(rng, 0.00, 0.06),
        network_packet_loss_percent=_float(rng, 0.0, 1.5),
        deployment_age_minutes=_optional_deployment_age(
            rng,
            present_probability=0.10,
            minimum=60,
            maximum=1_440,
        ),
        affected_user_count=rng.randint(100, 15_000),
        regions_affected=rng.randint(1, 4),
    )


def _network_degradation_features(
    rng: random.Random,
) -> IncidentFeatures:
    return IncidentFeatures(
        login_failure_rate=_rate(rng, 0.01, 0.18),
        token_validation_error_rate=_rate(rng, 0.00, 0.04),
        http_5xx_rate=_rate(rng, 0.02, 0.25),
        latency_p95_ms=_float(rng, 1_000.0, 7_000.0),
        cpu_utilization_percent=_float(rng, 20.0, 75.0),
        memory_utilization_percent=_float(rng, 25.0, 78.0),
        dependency_error_rate=_rate(rng, 0.00, 0.06),
        network_packet_loss_percent=_float(rng, 3.0, 15.0),
        deployment_age_minutes=_optional_deployment_age(
            rng,
            present_probability=0.10,
            minimum=60,
            maximum=1_440,
        ),
        affected_user_count=rng.randint(100, 10_000),
        regions_affected=rng.randint(1, 5),
    )


def _dependency_failure_features(
    rng: random.Random,
) -> IncidentFeatures:
    return IncidentFeatures(
        login_failure_rate=_rate(rng, 0.01, 0.20),
        token_validation_error_rate=_rate(rng, 0.00, 0.04),
        http_5xx_rate=_rate(rng, 0.06, 0.40),
        latency_p95_ms=_float(rng, 900.0, 6_000.0),
        cpu_utilization_percent=_float(rng, 20.0, 80.0),
        memory_utilization_percent=_float(rng, 25.0, 82.0),
        dependency_error_rate=_rate(rng, 0.08, 0.60),
        network_packet_loss_percent=_float(rng, 0.0, 1.5),
        deployment_age_minutes=_optional_deployment_age(
            rng,
            present_probability=0.10,
            minimum=60,
            maximum=1_440,
        ),
        affected_user_count=rng.randint(100, 12_000),
        regions_affected=rng.randint(1, 4),
    )


def _unknown_features(rng: random.Random) -> IncidentFeatures:
    return IncidentFeatures(
        login_failure_rate=_rate(rng, 0.00, 0.08),
        token_validation_error_rate=_rate(rng, 0.00, 0.03),
        http_5xx_rate=_rate(rng, 0.00, 0.06),
        latency_p95_ms=_float(rng, 100.0, 1_800.0),
        cpu_utilization_percent=_float(rng, 15.0, 85.0),
        memory_utilization_percent=_float(rng, 20.0, 85.0),
        dependency_error_rate=_rate(rng, 0.00, 0.05),
        network_packet_loss_percent=_float(rng, 0.0, 2.5),
        deployment_age_minutes=_optional_deployment_age(
            rng,
            present_probability=0.15,
            minimum=60,
            maximum=1_440,
        ),
        affected_user_count=rng.randint(1, 250),
        regions_affected=1,
    )


def _derive_severity(features: IncidentFeatures) -> IncidentSeverity:
    if (
        features.affected_user_count >= 10_000
        or features.regions_affected >= 4
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


def _rate(
    rng: random.Random,
    minimum: float,
    maximum: float,
) -> float:
    return round(rng.uniform(minimum, maximum), 6)


def _float(
    rng: random.Random,
    minimum: float,
    maximum: float,
) -> float:
    return round(rng.uniform(minimum, maximum), 3)


def _optional_deployment_age(
    rng: random.Random,
    present_probability: float,
    minimum: int,
    maximum: int,
) -> int | None:
    if rng.random() <= present_probability:
        return rng.randint(minimum, maximum)

    return None
