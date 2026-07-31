"""Contracts for synthetic incident dataset generation and validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from incident_agent.baseline.contracts import (
    IncidentCategory,
    IncidentFeatures,
    IncidentSeverity,
)


FEATURE_COLUMNS = (
    "login_failure_rate",
    "token_validation_error_rate",
    "http_5xx_rate",
    "latency_p95_ms",
    "cpu_utilization_percent",
    "memory_utilization_percent",
    "dependency_error_rate",
    "network_packet_loss_percent",
    "deployment_age_minutes",
    "affected_user_count",
    "regions_affected",
)

TARGET_COLUMNS = (
    "category",
    "severity",
)

IDENTIFIER_COLUMNS = ("incident_id",)

DATASET_COLUMNS = (
    *IDENTIFIER_COLUMNS,
    *FEATURE_COLUMNS,
    *TARGET_COLUMNS,
)


@dataclass(frozen=True)
class SyntheticIncident:
    """One labeled synthetic incident record."""

    incident_id: str
    features: IncidentFeatures
    category: IncidentCategory
    severity: IncidentSeverity

    def to_flat_dict(self) -> dict[str, Any]:
        """Return the record in CSV-compatible flat form."""

        record: dict[str, Any] = {
            "incident_id": self.incident_id,
            **asdict(self.features),
            "category": self.category.value,
            "severity": self.severity.value,
        }

        return record


@dataclass(frozen=True)
class SplitConfiguration:
    """Configuration for deterministic train, validation, and test splits."""

    train_fraction: float = 0.70
    validation_fraction: float = 0.15
    test_fraction: float = 0.15
    random_seed: int = 42

    def validate(self) -> None:
        total = (
            self.train_fraction
            + self.validation_fraction
            + self.test_fraction
        )

        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                "train, validation, and test fractions must sum to 1.0"
            )

        for name, value in (
            ("train_fraction", self.train_fraction),
            ("validation_fraction", self.validation_fraction),
            ("test_fraction", self.test_fraction),
        ):
            if not 0.0 < value < 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
