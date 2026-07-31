"""Strict CSV loading for ML training and evaluation."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from incident_agent.data.contracts import (
    DATASET_COLUMNS,
    FEATURE_COLUMNS,
)
from incident_agent.ml.contracts import DatasetMatrix


LABEL_COLUMN = "category"

NON_FEATURE_COLUMNS = frozenset(
    {
        "incident_id",
        "category",
        "severity",
    }
)

FEATURE_SCHEMA_VERSION = "incident-features-v1"


class DatasetSchemaError(ValueError):
    """Raised when a dataset does not match the expected schema."""


def load_dataset_matrix(path: Path) -> DatasetMatrix:
    """Load a generated CSV using an explicit feature allowlist."""

    if not path.exists():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)

        observed_columns = tuple(reader.fieldnames or ())
        expected_columns = tuple(DATASET_COLUMNS)

        if observed_columns != expected_columns:
            raise DatasetSchemaError(
                "Dataset schema mismatch. "
                f"expected={expected_columns}, "
                f"observed={observed_columns}"
            )

        feature_rows: list[list[float]] = []
        labels: list[str] = []
        incident_ids: list[str] = []

        for row_number, row in enumerate(reader, start=2):
            incident_id = row["incident_id"].strip()
            label = row[LABEL_COLUMN].strip()

            if not incident_id:
                raise DatasetSchemaError(
                    f"row {row_number} has an empty incident_id"
                )

            if not label:
                raise DatasetSchemaError(
                    f"row {row_number} has an empty category"
                )

            feature_values = [
                _parse_feature_value(
                    value=row[feature_name],
                    feature_name=feature_name,
                    row_number=row_number,
                )
                for feature_name in FEATURE_COLUMNS
            ]

            feature_rows.append(feature_values)
            labels.append(label)
            incident_ids.append(incident_id)

    if not feature_rows:
        raise DatasetSchemaError("Dataset contains no records")

    return DatasetMatrix(
        features=np.asarray(feature_rows, dtype=float),
        labels=np.asarray(labels, dtype=str),
        incident_ids=tuple(incident_ids),
        feature_names=tuple(FEATURE_COLUMNS),
    )


def assert_no_label_leakage(
    feature_names: tuple[str, ...],
) -> None:
    """Reject identifiers or target columns from the feature matrix."""

    leaked = sorted(
        set(feature_names) & NON_FEATURE_COLUMNS
    )

    if leaked:
        raise DatasetSchemaError(
            f"Label or identifier leakage detected: {leaked}"
        )

    if tuple(feature_names) != tuple(FEATURE_COLUMNS):
        raise DatasetSchemaError(
            "Feature allowlist does not match the canonical schema"
        )


def _parse_feature_value(
    value: str,
    feature_name: str,
    row_number: int,
) -> float:
    stripped = value.strip()

    if (
        feature_name == "deployment_age_minutes"
        and stripped == ""
    ):
        return float("nan")

    if stripped == "":
        raise DatasetSchemaError(
            f"row {row_number} has an unexpected missing value "
            f"for {feature_name}"
        )

    try:
        return float(stripped)
    except ValueError as exc:
        raise DatasetSchemaError(
            f"row {row_number} contains non-numeric value "
            f"for {feature_name}: {stripped!r}"
        ) from exc
