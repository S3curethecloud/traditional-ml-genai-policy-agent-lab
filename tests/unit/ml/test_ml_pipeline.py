"""Tests for Phase 3 traditional ML behavior."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from incident_agent.baseline.contracts import (
    IncidentFeatures,
)
from incident_agent.data.contracts import (
    DATASET_COLUMNS,
    FEATURE_COLUMNS,
)
from incident_agent.ml.data_loader import (
    DatasetSchemaError,
    assert_no_label_leakage,
    load_dataset_matrix,
)
from incident_agent.ml.inference import (
    IncidentClassifier,
    ModelArtifactError,
)
from incident_agent.ml.training import (
    compare_deterministic_baseline,
    evaluate_selected_model,
    explain_model,
    persist_model_artifacts,
    train_and_select_model,
)


DATA_DIRECTORY = Path("data/generated")


def load_splits():
    return (
        load_dataset_matrix(
            DATA_DIRECTORY / "train.csv"
        ),
        load_dataset_matrix(
            DATA_DIRECTORY / "validation.csv"
        ),
        load_dataset_matrix(
            DATA_DIRECTORY / "test.csv"
        ),
    )


def test_loader_uses_only_canonical_features() -> None:
    train = load_dataset_matrix(
        DATA_DIRECTORY / "train.csv"
    )

    assert train.feature_names == tuple(
        FEATURE_COLUMNS
    )
    assert train.features.shape == (
        420,
        len(FEATURE_COLUMNS),
    )
    assert "incident_id" not in train.feature_names
    assert "category" not in train.feature_names
    assert "severity" not in train.feature_names


def test_missing_deployment_age_becomes_nan() -> None:
    train = load_dataset_matrix(
        DATA_DIRECTORY / "train.csv"
    )

    deployment_index = train.feature_names.index(
        "deployment_age_minutes"
    )

    assert np.isnan(
        train.features[:, deployment_index]
    ).any()


def test_label_leakage_is_rejected() -> None:
    with pytest.raises(
        DatasetSchemaError,
        match="leakage",
    ):
        assert_no_label_leakage(
            (
                *FEATURE_COLUMNS,
                "category",
            )
        )


def test_schema_drift_is_rejected(
    tmp_path: Path,
) -> None:
    source = DATA_DIRECTORY / "train.csv"
    target = tmp_path / "drifted.csv"

    with source.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as source_handle:
        reader = csv.DictReader(source_handle)
        rows = list(reader)

    drifted_columns = [
        column
        for column in DATASET_COLUMNS
        if column != "memory_utilization_percent"
    ]

    with target.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as target_handle:
        writer = csv.DictWriter(
            target_handle,
            fieldnames=drifted_columns,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(
        DatasetSchemaError,
        match="schema mismatch",
    ):
        load_dataset_matrix(target)


def test_training_is_reproducible() -> None:
    train, validation, _ = load_splits()

    first_name, first_model, first_results = (
        train_and_select_model(
            train,
            validation,
            random_seed=42,
        )
    )

    second_name, second_model, second_results = (
        train_and_select_model(
            train,
            validation,
            random_seed=42,
        )
    )

    assert first_name == second_name

    assert np.array_equal(
        first_model.predict(validation.features),
        second_model.predict(validation.features),
    )

    assert first_results == second_results


def test_validation_selects_a_supported_model() -> None:
    train, validation, _ = load_splits()

    selected_name, _, evaluations = (
        train_and_select_model(
            train,
            validation,
            random_seed=42,
        )
    )

    assert selected_name in {
        "logistic_regression",
        "random_forest",
    }

    assert {
        evaluation.model_name
        for evaluation in evaluations
    } == {
        "logistic_regression",
        "random_forest",
    }


def test_selected_model_produces_required_metrics() -> None:
    train, validation, test = load_splits()

    _, model, _ = train_and_select_model(
        train,
        validation,
        random_seed=42,
    )

    metrics = evaluate_selected_model(
        model,
        test,
    )

    assert 0.0 <= metrics.accuracy <= 1.0
    assert 0.0 <= metrics.precision_macro <= 1.0
    assert 0.0 <= metrics.recall_macro <= 1.0
    assert 0.0 <= metrics.f1_macro <= 1.0
    assert metrics.log_loss >= 0.0

    assert (
        0.0
        <= metrics.expected_calibration_error
        <= 1.0
    )

    assert len(metrics.confusion_matrix) == 6
    assert all(
        len(row) == 6
        for row in metrics.confusion_matrix
    )


def test_model_explanation_is_available() -> None:
    train, validation, _ = load_splits()

    selected_name, model, _ = (
        train_and_select_model(
            train,
            validation,
            random_seed=42,
        )
    )

    explanation = explain_model(
        model_name=selected_name,
        model=model,
        canonical_feature_names=
            train.feature_names,
    )

    assert explanation["method"] in {
        "multiclass_logistic_coefficients",
        "random_forest_feature_importance",
    }


def test_deterministic_baseline_comparison_runs() -> None:
    _, _, test = load_splits()

    metrics = compare_deterministic_baseline(
        test
    )

    assert 0.0 <= metrics.accuracy <= 1.0
    assert 0.0 <= metrics.f1_macro <= 1.0
    assert len(metrics.confusion_matrix) == 6


def test_persisted_model_supports_typed_inference(
    tmp_path: Path,
) -> None:
    train, validation, test = load_splits()

    (
        selected_name,
        model,
        evaluations,
    ) = train_and_select_model(
        train,
        validation,
        random_seed=42,
    )

    test_metrics = evaluate_selected_model(
        model,
        test,
    )

    deterministic_metrics = (
        compare_deterministic_baseline(test)
    )

    explanation = explain_model(
        model_name=selected_name,
        model=model,
        canonical_feature_names=
            train.feature_names,
    )

    persist_model_artifacts(
        output_directory=tmp_path,
        selected_model_name=selected_name,
        model=model,
        validation_evaluations=evaluations,
        test_metrics=test_metrics,
        deterministic_baseline_metrics=
            deterministic_metrics,
        feature_names=train.feature_names,
        explanation=explanation,
        train=train,
        validation=validation,
        test=test,
    )

    classifier = IncidentClassifier.load(
        tmp_path
    )

    prediction = classifier.predict(
        IncidentFeatures(
            login_failure_rate=0.24,
            token_validation_error_rate=0.15,
            http_5xx_rate=0.08,
            latency_p95_ms=1_400.0,
            cpu_utilization_percent=55.0,
            memory_utilization_percent=62.0,
            dependency_error_rate=0.02,
            network_packet_loss_percent=0.4,
            deployment_age_minutes=None,
            affected_user_count=750,
            regions_affected=1,
        )
    )

    assert prediction.predicted_category
    assert 0.0 <= prediction.confidence <= 1.0
    assert len(
        prediction.class_probabilities
    ) == 6

    assert abs(
        sum(
            prediction.class_probabilities.values()
        )
        - 1.0
    ) < 1e-6

    assert (
        prediction.model_version
        == "incident-classifier-v1"
    )

    assert (
        prediction.feature_schema_version
        == "incident-features-v1"
    )


def test_metadata_records_authority_boundary(
    tmp_path: Path,
) -> None:
    train, validation, test = load_splits()

    (
        selected_name,
        model,
        evaluations,
    ) = train_and_select_model(
        train,
        validation,
        random_seed=42,
    )

    metrics = evaluate_selected_model(
        model,
        test,
    )

    persist_model_artifacts(
        output_directory=tmp_path,
        selected_model_name=selected_name,
        model=model,
        validation_evaluations=evaluations,
        test_metrics=metrics,
        deterministic_baseline_metrics=
            compare_deterministic_baseline(test),
        feature_names=train.feature_names,
        explanation=explain_model(
            selected_name,
            model,
            train.feature_names,
        ),
        train=train,
        validation=validation,
        test=test,
    )

    metadata = json.loads(
        (
            tmp_path / "metadata.json"
        ).read_text(encoding="utf-8")
    )

    assert metadata["excluded_columns"] == [
        "incident_id",
        "category",
        "severity",
    ]

    assert (
        "evidence only"
        in metadata["authority_boundary"]
    )


def test_inference_rejects_schema_mismatch(
    tmp_path: Path,
) -> None:
    train, validation, test = load_splits()

    selected_name, model, evaluations = (
        train_and_select_model(
            train,
            validation,
            random_seed=42,
        )
    )

    persist_model_artifacts(
        output_directory=tmp_path,
        selected_model_name=selected_name,
        model=model,
        validation_evaluations=evaluations,
        test_metrics=evaluate_selected_model(
            model,
            test,
        ),
        deterministic_baseline_metrics=
            compare_deterministic_baseline(test),
        feature_names=train.feature_names,
        explanation=explain_model(
            selected_name,
            model,
            train.feature_names,
        ),
        train=train,
        validation=validation,
        test=test,
    )

    metadata_path = tmp_path / "metadata.json"

    metadata = json.loads(
        metadata_path.read_text(
            encoding="utf-8"
        )
    )

    metadata["feature_columns"] = [
        *metadata["feature_columns"],
        "unexpected_feature",
    ]

    metadata_path.write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    with pytest.raises(
        ModelArtifactError,
        match="feature schema",
    ):
        IncidentClassifier.load(tmp_path)
