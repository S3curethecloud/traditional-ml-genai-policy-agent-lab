#!/usr/bin/env python3
"""Evaluate the sealed Phase 3B ambiguity challenge set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from incident_agent.evaluation.ambiguity import (
    build_ambiguity_report,
    evaluate_ambiguity_pack,
    load_ambiguity_pack,
    sha256_file,
    write_ambiguity_report,
)
from incident_agent.ml.inference import IncidentClassifier


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the locked ML model and deterministic "
            "classifier against the sealed ambiguity pack."
        )
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(
            "data/ambiguity/phase-3b-cases.yaml"
        ),
    )
    parser.add_argument(
        "--model-directory",
        type=Path,
        default=Path(
            "models/incident-classifier"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "reports/ambiguity/"
            "phase-3b-report.json"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    model_path = (
        args.model_directory / "model.joblib"
    )
    metadata_path = (
        args.model_directory / "metadata.json"
    )

    model_hash_before = sha256_file(model_path)
    metadata_hash_before = sha256_file(
        metadata_path
    )

    cases = load_ambiguity_pack(args.cases)
    classifier = IncidentClassifier.load(
        args.model_directory
    )

    results = evaluate_ambiguity_pack(
        cases=cases,
        classifier=classifier,
    )

    report = build_ambiguity_report(
        cases_path=args.cases,
        model_path=model_path,
        metadata_path=metadata_path,
        results=results,
    )

    write_ambiguity_report(
        args.output,
        report,
    )

    model_hash_after = sha256_file(model_path)
    metadata_hash_after = sha256_file(
        metadata_path
    )

    if model_hash_before != model_hash_after:
        raise RuntimeError(
            "Locked model changed during evaluation"
        )

    if metadata_hash_before != metadata_hash_after:
        raise RuntimeError(
            "Locked model metadata changed during evaluation"
        )

    summary = report["summary"]

    print(
        f"PASS: evaluated {summary['case_count']} "
        "sealed ambiguity cases"
    )
    print(
        "PASS: training_performed=false"
    )
    print(
        "PASS: model_selection_performed=false"
    )
    print(
        "PASS: threshold_tuning_performed=false"
    )
    print(
        "PASS: locked model and metadata were unchanged"
    )

    print(
        "\nSummary:"
    )
    print(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
    )

    print("\nCase results:")

    for result in results:
        agreement = (
            "AGREE"
            if result.classifiers_agree
            else "DISAGREE"
        )

        print(
            f"  {result.case_id}: {agreement}; "
            f"rules={result.deterministic_category}; "
            f"ml={result.ml_category}; "
            f"ml_confidence={result.ml_confidence:.4f}; "
            f"margin={result.ml_probability_margin:.4f}; "
            f"review={result.requires_genai_review}"
        )

    print(
        "\nPASS: classifier outputs remain "
        "diagnostic evidence only"
    )


if __name__ == "__main__":
    main()
