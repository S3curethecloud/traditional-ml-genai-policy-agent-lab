"""Deterministic stratified dataset splitting."""

from __future__ import annotations

import random
from collections import defaultdict

from incident_agent.baseline.contracts import IncidentCategory
from incident_agent.data.contracts import (
    SplitConfiguration,
    SyntheticIncident,
)


def stratified_split(
    incidents: list[SyntheticIncident],
    configuration: SplitConfiguration | None = None,
) -> dict[str, list[SyntheticIncident]]:
    """Split incidents while preserving every category in every split."""

    config = configuration or SplitConfiguration()
    config.validate()

    if not incidents:
        raise ValueError("incidents must not be empty")

    grouped: dict[IncidentCategory, list[SyntheticIncident]] = defaultdict(
        list
    )

    for incident in incidents:
        grouped[incident.category].append(incident)

    expected_categories = set(IncidentCategory)
    observed_categories = set(grouped)

    if observed_categories != expected_categories:
        missing = sorted(
            category.value
            for category in expected_categories - observed_categories
        )
        raise ValueError(
            f"dataset must contain every incident category; missing={missing}"
        )

    rng = random.Random(config.random_seed)

    splits: dict[str, list[SyntheticIncident]] = {
        "train": [],
        "validation": [],
        "test": [],
    }

    for category in IncidentCategory:
        category_records = list(grouped[category])
        rng.shuffle(category_records)

        count = len(category_records)

        train_count = int(count * config.train_fraction)
        validation_count = int(count * config.validation_fraction)
        test_count = count - train_count - validation_count

        if min(train_count, validation_count, test_count) < 1:
            raise ValueError(
                f"category {category.value} does not have enough records "
                "for all three splits"
            )

        train_end = train_count
        validation_end = train_count + validation_count

        splits["train"].extend(category_records[:train_end])
        splits["validation"].extend(
            category_records[train_end:validation_end]
        )
        splits["test"].extend(category_records[validation_end:])

    for split_records in splits.values():
        rng.shuffle(split_records)

    return splits
