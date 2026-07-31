"""Persistence helpers for generated incident datasets."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from incident_agent.data.contracts import (
    DATASET_COLUMNS,
    SyntheticIncident,
)


def write_dataset_csv(
    path: Path,
    incidents: list[SyntheticIncident],
) -> None:
    """Write synthetic incidents using a stable column order."""

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(DATASET_COLUMNS),
        )
        writer.writeheader()

        for incident in incidents:
            writer.writerow(incident.to_flat_dict())


def sha256_file(path: Path) -> str:
    """Calculate a SHA-256 digest for one file."""

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def build_manifest(
    output_directory: Path,
    splits: dict[str, list[SyntheticIncident]],
    random_seed: int,
    records_per_category: int,
) -> dict[str, Any]:
    """Build reproducibility and distribution metadata."""

    files = {
        split_name: {
            "path": f"{split_name}.csv",
            "sha256": sha256_file(
                output_directory / f"{split_name}.csv"
            ),
            "record_count": len(records),
            "class_distribution": dict(
                sorted(
                    Counter(
                        incident.category.value
                        for incident in records
                    ).items()
                )
            ),
        }
        for split_name, records in splits.items()
    }

    return {
        "dataset_version": "synthetic-incidents-v1",
        "random_seed": random_seed,
        "records_per_category": records_per_category,
        "total_record_count": sum(
            len(records)
            for records in splits.values()
        ),
        "files": files,
    }


def write_manifest(
    path: Path,
    manifest: dict[str, Any],
) -> None:
    """Write a deterministic JSON manifest."""

    with path.open("w", encoding="utf-8") as handle:
        json.dump(
            manifest,
            handle,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")
