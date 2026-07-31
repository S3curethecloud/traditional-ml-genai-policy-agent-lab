#!/usr/bin/env python3
"""Generate, validate, split, and persist the synthetic incident dataset."""

from __future__ import annotations

import argparse
from pathlib import Path

from incident_agent.data.contracts import SplitConfiguration
from incident_agent.data.generator import generate_balanced_dataset
from incident_agent.data.io import (
    build_manifest,
    write_dataset_csv,
    write_manifest,
)
from incident_agent.data.splitting import stratified_split
from incident_agent.data.validation import (
    validate_dataset,
    validate_split_isolation,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the synthetic incident dataset."
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/generated"),
    )
    parser.add_argument(
        "--records-per-category",
        type=int,
        default=100,
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    incidents = generate_balanced_dataset(
        records_per_category=args.records_per_category,
        random_seed=args.random_seed,
    )

    dataset_findings = validate_dataset(incidents)

    splits = stratified_split(
        incidents,
        SplitConfiguration(random_seed=args.random_seed),
    )

    split_findings = validate_split_isolation(splits)

    args.output_directory.mkdir(parents=True, exist_ok=True)

    for split_name, records in splits.items():
        write_dataset_csv(
            args.output_directory / f"{split_name}.csv",
            records,
        )

    manifest = build_manifest(
        output_directory=args.output_directory,
        splits=splits,
        random_seed=args.random_seed,
        records_per_category=args.records_per_category,
    )

    write_manifest(
        args.output_directory / "manifest.json",
        manifest,
    )

    print(
        f"PASS: generated {len(incidents)} synthetic incidents"
    )

    for finding in (*dataset_findings, *split_findings):
        print(
            f"PASS: {finding.check_id}: {finding.message}"
        )

    for split_name, records in splits.items():
        print(f"{split_name}: {len(records)} records")


if __name__ == "__main__":
    main()
