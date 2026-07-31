#!/usr/bin/env python3
"""Train, select, evaluate, explain, and persist Phase 3 models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from incident_agent.ml.data_loader import (
    load_dataset_matrix,
)
from incident_agent.ml.training import (
    TRAINING_RANDOM_SEED,
    compare_deterministic_baseline,
    evaluate_selected_model,
    explain_model,
    persist_model_artifacts,
    train_and_select_model,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Train and evaluate the traditional "
            "incident classifier."
        )
    )
    parser.add_argument(
        "--data-directory",
        type=Path,
        default=Path("data/generated"),
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path(
            "models/incident-classifier"
        ),
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=TRAINING_RANDOM_SEED,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    train = load_dataset_matrix(
        args.data_directory / "train.csv"
    )
    validation = load_dataset_matrix(
        args.data_directory / "validation.csv"
    )
    test = load_dataset_matrix(
        args.data_directory / "test.csv"
    )

    (
        selected_model_name,
        selected_model,
        validation_evaluations,
    ) = train_and_select_model(
        train=train,
        validation=validation,
        random_seed=args.random_seed,
    )

    test_metrics = evaluate_selected_model(
        model=selected_model,
        test=test,
    )

    deterministic_metrics = (
        compare_deterministic_baseline(test)
    )

    explanation = explain_model(
        model_name=selected_model_name,
        model=selected_model,
        canonical_feature_names=train.feature_names,
    )

    metadata = persist_model_artifacts(
        output_directory=args.output_directory,
        selected_model_name=selected_model_name,
        model=selected_model,
        validation_evaluations=validation_evaluations,
        test_metrics=test_metrics,
        deterministic_baseline_metrics=
            deterministic_metrics,
        feature_names=train.feature_names,
        explanation=explanation,
        train=train,
        validation=validation,
        test=test,
        random_seed=args.random_seed,
    )

    print(
        f"PASS: selected model: {selected_model_name}"
    )

    print("\nValidation candidate metrics:")

    for evaluation in validation_evaluations:
        print(
            f"  {evaluation.model_name}: "
            f"accuracy="
            f"{evaluation.metrics.accuracy:.4f}, "
            f"macro_f1="
            f"{evaluation.metrics.f1_macro:.4f}, "
            f"ece="
            f"{evaluation.metrics.expected_calibration_error:.4f}"
        )

    print("\nSelected model test metrics:")
    print(
        json.dumps(
            metadata["test_metrics"],
            indent=2,
            sort_keys=True,
        )
    )

    print("\nDeterministic baseline test metrics:")
    print(
        json.dumps(
            metadata[
                "deterministic_baseline_test_metrics"
            ],
            indent=2,
            sort_keys=True,
        )
    )

    print(
        "\nPASS: prediction remains evidence only; "
        "no authorization or execution authority granted"
    )


if __name__ == "__main__":
    main()
