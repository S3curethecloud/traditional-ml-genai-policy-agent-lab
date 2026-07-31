"""Tests for synthetic incident dataset generation."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace

import pytest

from incident_agent.baseline.contracts import (
    IncidentCategory,
    IncidentFeatures,
)
from incident_agent.data.contracts import SplitConfiguration
from incident_agent.data.generator import generate_balanced_dataset
from incident_agent.data.splitting import stratified_split
from incident_agent.data.validation import (
    DatasetValidationError,
    validate_dataset,
    validate_split_isolation,
)


def test_generation_is_reproducible() -> None:
    first = generate_balanced_dataset(
        records_per_category=20,
        random_seed=42,
    )
    second = generate_balanced_dataset(
        records_per_category=20,
        random_seed=42,
    )

    assert first == second


def test_different_seed_changes_generated_features() -> None:
    first = generate_balanced_dataset(
        records_per_category=20,
        random_seed=42,
    )
    second = generate_balanced_dataset(
        records_per_category=20,
        random_seed=43,
    )

    assert first != second


def test_generated_dataset_is_exactly_balanced() -> None:
    incidents = generate_balanced_dataset(
        records_per_category=25,
        random_seed=42,
    )

    counts = Counter(
        incident.category
        for incident in incidents
    )

    assert set(counts) == set(IncidentCategory)
    assert set(counts.values()) == {25}


def test_generated_incident_ids_are_unique() -> None:
    incidents = generate_balanced_dataset(
        records_per_category=20,
        random_seed=42,
    )

    identifiers = [
        incident.incident_id
        for incident in incidents
    ]

    assert len(identifiers) == len(set(identifiers))


def test_dataset_quality_validation_passes() -> None:
    incidents = generate_balanced_dataset(
        records_per_category=20,
        random_seed=42,
    )

    findings = validate_dataset(incidents)

    assert all(finding.passed for finding in findings)


def test_invalid_rate_is_rejected() -> None:
    incidents = generate_balanced_dataset(
        records_per_category=20,
        random_seed=42,
    )

    first = incidents[0]
    invalid_features = replace(
        first.features,
        login_failure_rate=1.50,
    )
    incidents[0] = replace(
        first,
        features=invalid_features,
    )

    with pytest.raises(
        DatasetValidationError,
        match="feature-ranges",
    ):
        validate_dataset(incidents)


def test_duplicate_incident_id_is_rejected() -> None:
    incidents = generate_balanced_dataset(
        records_per_category=20,
        random_seed=42,
    )

    incidents[1] = replace(
        incidents[1],
        incident_id=incidents[0].incident_id,
    )

    with pytest.raises(
        DatasetValidationError,
        match="unique-incident-ids",
    ):
        validate_dataset(incidents)


def test_significant_class_imbalance_is_rejected() -> None:
    incidents = generate_balanced_dataset(
        records_per_category=20,
        random_seed=42,
    )

    imbalanced = [
        incident
        for incident in incidents
        if (
            incident.category
            is not IncidentCategory.UNKNOWN
            or incident.incident_id.endswith("00001")
        )
    ]

    with pytest.raises(
        DatasetValidationError,
        match="class-balance",
    ):
        validate_dataset(imbalanced)


def test_stratified_split_preserves_every_category() -> None:
    incidents = generate_balanced_dataset(
        records_per_category=20,
        random_seed=42,
    )

    splits = stratified_split(
        incidents,
        SplitConfiguration(random_seed=42),
    )

    for records in splits.values():
        assert {
            incident.category
            for incident in records
        } == set(IncidentCategory)


def test_split_sizes_are_deterministic() -> None:
    incidents = generate_balanced_dataset(
        records_per_category=20,
        random_seed=42,
    )

    splits = stratified_split(
        incidents,
        SplitConfiguration(random_seed=42),
    )

    assert len(splits["train"]) == 84
    assert len(splits["validation"]) == 18
    assert len(splits["test"]) == 18


def test_split_isolation_prevents_leakage() -> None:
    incidents = generate_balanced_dataset(
        records_per_category=20,
        random_seed=42,
    )

    splits = stratified_split(
        incidents,
        SplitConfiguration(random_seed=42),
    )

    findings = validate_split_isolation(splits)

    assert findings[0].passed


def test_leaked_incident_id_is_rejected() -> None:
    incidents = generate_balanced_dataset(
        records_per_category=20,
        random_seed=42,
    )

    splits = stratified_split(
        incidents,
        SplitConfiguration(random_seed=42),
    )

    splits["test"].append(splits["train"][0])

    with pytest.raises(
        DatasetValidationError,
        match="Leaked incident IDs",
    ):
        validate_split_isolation(splits)


def test_minimum_records_per_category_is_enforced() -> None:
    with pytest.raises(
        ValueError,
        match="at least 10",
    ):
        generate_balanced_dataset(
            records_per_category=5,
            random_seed=42,
        )


def test_feature_contract_remains_numeric() -> None:
    incidents = generate_balanced_dataset(
        records_per_category=10,
        random_seed=42,
    )

    features: IncidentFeatures = incidents[0].features

    assert isinstance(features.login_failure_rate, float)
    assert isinstance(features.affected_user_count, int)
