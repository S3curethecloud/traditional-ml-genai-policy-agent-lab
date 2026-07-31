"""Data-quality checks for synthetic incident datasets."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from incident_agent.baseline.contracts import IncidentCategory
from incident_agent.data.contracts import SyntheticIncident


@dataclass(frozen=True)
class ValidationFinding:
    """One data-quality finding."""

    check_id: str
    passed: bool
    message: str


class DatasetValidationError(ValueError):
    """Raised when one or more data-quality checks fail."""


def validate_dataset(
    incidents: list[SyntheticIncident],
    maximum_class_ratio: float = 1.10,
) -> tuple[ValidationFinding, ...]:
    """Run required dataset-level quality checks."""

    findings = (
        _validate_non_empty(incidents),
        _validate_unique_incident_ids(incidents),
        _validate_feature_ranges(incidents),
        _validate_all_categories_present(incidents),
        _validate_class_balance(incidents, maximum_class_ratio),
    )

    failures = [finding for finding in findings if not finding.passed]

    if failures:
        details = "; ".join(
            f"{finding.check_id}: {finding.message}"
            for finding in failures
        )
        raise DatasetValidationError(details)

    return findings


def validate_split_isolation(
    splits: dict[str, list[SyntheticIncident]],
) -> tuple[ValidationFinding, ...]:
    """Ensure train, validation, and test splits do not overlap."""

    required_names = {"train", "validation", "test"}
    observed_names = set(splits)

    if observed_names != required_names:
        raise DatasetValidationError(
            "splits must contain exactly train, validation, and test"
        )

    id_sets = {
        split_name: {
            incident.incident_id
            for incident in split_records
        }
        for split_name, split_records in splits.items()
    }

    overlaps = {
        "train_validation": id_sets["train"] & id_sets["validation"],
        "train_test": id_sets["train"] & id_sets["test"],
        "validation_test": id_sets["validation"] & id_sets["test"],
    }

    leaked_ids = sorted(
        incident_id
        for overlap in overlaps.values()
        for incident_id in overlap
    )

    finding = ValidationFinding(
        check_id="split-isolation",
        passed=not leaked_ids,
        message=(
            "No incident IDs overlap across dataset splits."
            if not leaked_ids
            else f"Leaked incident IDs detected: {leaked_ids}"
        ),
    )

    if not finding.passed:
        raise DatasetValidationError(finding.message)

    return (finding,)


def _validate_non_empty(
    incidents: list[SyntheticIncident],
) -> ValidationFinding:
    return ValidationFinding(
        check_id="non-empty",
        passed=bool(incidents),
        message=(
            f"Dataset contains {len(incidents)} records."
            if incidents
            else "Dataset is empty."
        ),
    )


def _validate_unique_incident_ids(
    incidents: list[SyntheticIncident],
) -> ValidationFinding:
    identifiers = [incident.incident_id for incident in incidents]
    duplicate_ids = sorted(
        identifier
        for identifier, count in Counter(identifiers).items()
        if count > 1
    )

    return ValidationFinding(
        check_id="unique-incident-ids",
        passed=not duplicate_ids,
        message=(
            "All incident IDs are unique."
            if not duplicate_ids
            else f"Duplicate incident IDs detected: {duplicate_ids}"
        ),
    )


def _validate_feature_ranges(
    incidents: list[SyntheticIncident],
) -> ValidationFinding:
    errors: list[str] = []

    for incident in incidents:
        features = incident.features
        incident_id = incident.incident_id

        rate_fields = {
            "login_failure_rate": features.login_failure_rate,
            "token_validation_error_rate":
                features.token_validation_error_rate,
            "http_5xx_rate": features.http_5xx_rate,
            "dependency_error_rate": features.dependency_error_rate,
        }

        for field_name, value in rate_fields.items():
            if not 0.0 <= value <= 1.0:
                errors.append(
                    f"{incident_id}.{field_name}={value}"
                )

        percentage_fields = {
            "cpu_utilization_percent":
                features.cpu_utilization_percent,
            "memory_utilization_percent":
                features.memory_utilization_percent,
            "network_packet_loss_percent":
                features.network_packet_loss_percent,
        }

        for field_name, value in percentage_fields.items():
            if not 0.0 <= value <= 100.0:
                errors.append(
                    f"{incident_id}.{field_name}={value}"
                )

        if features.latency_p95_ms < 0.0:
            errors.append(
                f"{incident_id}.latency_p95_ms="
                f"{features.latency_p95_ms}"
            )

        if (
            features.deployment_age_minutes is not None
            and features.deployment_age_minutes < 0
        ):
            errors.append(
                f"{incident_id}.deployment_age_minutes="
                f"{features.deployment_age_minutes}"
            )

        if features.affected_user_count < 0:
            errors.append(
                f"{incident_id}.affected_user_count="
                f"{features.affected_user_count}"
            )

        if features.regions_affected < 1:
            errors.append(
                f"{incident_id}.regions_affected="
                f"{features.regions_affected}"
            )

    return ValidationFinding(
        check_id="feature-ranges",
        passed=not errors,
        message=(
            "All feature values are within allowed ranges."
            if not errors
            else f"Invalid feature values: {errors[:10]}"
        ),
    )


def _validate_all_categories_present(
    incidents: list[SyntheticIncident],
) -> ValidationFinding:
    observed = {incident.category for incident in incidents}
    expected = set(IncidentCategory)
    missing = sorted(
        category.value
        for category in expected - observed
    )

    return ValidationFinding(
        check_id="all-categories-present",
        passed=not missing,
        message=(
            "Every incident category is represented."
            if not missing
            else f"Missing categories: {missing}"
        ),
    )


def _validate_class_balance(
    incidents: Iterable[SyntheticIncident],
    maximum_class_ratio: float,
) -> ValidationFinding:
    counts = Counter(
        incident.category.value
        for incident in incidents
    )

    if not counts:
        return ValidationFinding(
            check_id="class-balance",
            passed=False,
            message="Class balance cannot be evaluated on an empty dataset.",
        )

    smallest = min(counts.values())
    largest = max(counts.values())
    ratio = largest / smallest if smallest else float("inf")

    return ValidationFinding(
        check_id="class-balance",
        passed=ratio <= maximum_class_ratio,
        message=(
            f"Class ratio is {ratio:.3f}; counts={dict(sorted(counts.items()))}"
        ),
    )
