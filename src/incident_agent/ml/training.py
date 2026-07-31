"""Traditional ML training, model selection, and comparison."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from incident_agent.baseline.classifier import classify_incident
from incident_agent.baseline.contracts import IncidentFeatures
from incident_agent.ml.contracts import (
    CandidateEvaluation,
    ClassificationMetrics,
    DatasetMatrix,
)
from incident_agent.ml.data_loader import (
    FEATURE_SCHEMA_VERSION,
    assert_no_label_leakage,
)
from incident_agent.ml.metrics import evaluate_classifier


MODEL_VERSION = "incident-classifier-v1"
TRAINING_RANDOM_SEED = 42

MODEL_ARTIFACT_NAME = "model.joblib"
MODEL_METADATA_NAME = "metadata.json"


def build_candidate_models(
    feature_count: int,
    random_seed: int = TRAINING_RANDOM_SEED,
) -> dict[str, Pipeline]:
    """Build the interpretable and tree-based candidates."""

    feature_indexes = list(range(feature_count))

    logistic_preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    steps=[
                        (
                            "imputer",
                            SimpleImputer(
                                strategy="median",
                                add_indicator=True,
                            ),
                        ),
                        ("scaler", StandardScaler()),
                    ]
                ),
                feature_indexes,
            )
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    tree_preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    steps=[
                        (
                            "imputer",
                            SimpleImputer(
                                strategy="median",
                                add_indicator=True,
                            ),
                        ),
                    ]
                ),
                feature_indexes,
            )
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    logistic_model = Pipeline(
        steps=[
            ("preprocessor", logistic_preprocessor),
            (
                "classifier",
                LogisticRegression(
                    max_iter=3_000,
                    solver="lbfgs",
                    random_state=random_seed,
                ),
            ),
        ]
    )

    random_forest_model = Pipeline(
        steps=[
            ("preprocessor", tree_preprocessor),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=300,
                    max_depth=10,
                    min_samples_leaf=2,
                    random_state=random_seed,
                    n_jobs=1,
                ),
            ),
        ]
    )

    return {
        "logistic_regression": logistic_model,
        "random_forest": random_forest_model,
    }


def train_and_select_model(
    train: DatasetMatrix,
    validation: DatasetMatrix,
    random_seed: int = TRAINING_RANDOM_SEED,
) -> tuple[
    str,
    Pipeline,
    tuple[CandidateEvaluation, ...],
]:
    """Fit candidates and select using validation macro F1."""

    _validate_matrix_compatibility(train, validation)

    candidates = build_candidate_models(
        feature_count=len(train.feature_names),
        random_seed=random_seed,
    )

    evaluations: list[CandidateEvaluation] = []
    fitted_models: dict[str, Pipeline] = {}

    for model_name, model in candidates.items():
        model.fit(train.features, train.labels)

        predictions = model.predict(validation.features)
        probabilities = model.predict_proba(
            validation.features
        )

        metrics = evaluate_classifier(
            labels=validation.labels,
            predictions=predictions,
            probabilities=probabilities,
            class_names=model.classes_,
        )

        fitted_models[model_name] = model
        evaluations.append(
            CandidateEvaluation(
                model_name=model_name,
                metrics=metrics,
            )
        )

    selected_evaluation = max(
        evaluations,
        key=lambda evaluation: (
            evaluation.metrics.f1_macro,
            -evaluation.metrics.log_loss,
            evaluation.model_name == "logistic_regression",
        ),
    )

    return (
        selected_evaluation.model_name,
        fitted_models[selected_evaluation.model_name],
        tuple(evaluations),
    )


def evaluate_selected_model(
    model: Pipeline,
    test: DatasetMatrix,
) -> ClassificationMetrics:
    """Evaluate the locked selected model on the test split."""

    assert_no_label_leakage(test.feature_names)

    predictions = model.predict(test.features)
    probabilities = model.predict_proba(test.features)

    return evaluate_classifier(
        labels=test.labels,
        predictions=predictions,
        probabilities=probabilities,
        class_names=model.classes_,
    )


def compare_deterministic_baseline(
    test: DatasetMatrix,
) -> ClassificationMetrics:
    """Evaluate Phase 1 rules against the same Phase 3 test labels."""

    feature_positions = {
        feature_name: index
        for index, feature_name in enumerate(test.feature_names)
    }

    predictions: list[str] = []

    for row in test.features:
        deployment_age = row[
            feature_positions["deployment_age_minutes"]
        ]

        features = IncidentFeatures(
            login_failure_rate=float(
                row[
                    feature_positions[
                        "login_failure_rate"
                    ]
                ]
            ),
            token_validation_error_rate=float(
                row[
                    feature_positions[
                        "token_validation_error_rate"
                    ]
                ]
            ),
            http_5xx_rate=float(
                row[feature_positions["http_5xx_rate"]]
            ),
            latency_p95_ms=float(
                row[feature_positions["latency_p95_ms"]]
            ),
            cpu_utilization_percent=float(
                row[
                    feature_positions[
                        "cpu_utilization_percent"
                    ]
                ]
            ),
            memory_utilization_percent=float(
                row[
                    feature_positions[
                        "memory_utilization_percent"
                    ]
                ]
            ),
            dependency_error_rate=float(
                row[
                    feature_positions[
                        "dependency_error_rate"
                    ]
                ]
            ),
            network_packet_loss_percent=float(
                row[
                    feature_positions[
                        "network_packet_loss_percent"
                    ]
                ]
            ),
            deployment_age_minutes=(
                None
                if np.isnan(deployment_age)
                else int(deployment_age)
            ),
            affected_user_count=int(
                row[
                    feature_positions[
                        "affected_user_count"
                    ]
                ]
            ),
            regions_affected=int(
                row[
                    feature_positions[
                        "regions_affected"
                    ]
                ]
            ),
        )

        predictions.append(
            classify_incident(features).category.value
        )

    prediction_array = np.asarray(predictions, dtype=str)
    class_names = np.asarray(
        sorted(set(test.labels) | set(prediction_array)),
        dtype=str,
    )

    probability_matrix = np.zeros(
        (len(prediction_array), len(class_names)),
        dtype=float,
    )

    class_positions = {
        class_name: index
        for index, class_name in enumerate(class_names)
    }

    for row_index, prediction in enumerate(
        prediction_array
    ):
        probability_matrix[
            row_index,
            class_positions[prediction],
        ] = 1.0

    return evaluate_classifier(
        labels=test.labels,
        predictions=prediction_array,
        probabilities=probability_matrix,
        class_names=class_names,
    )


def explain_model(
    model_name: str,
    model: Pipeline,
    canonical_feature_names: tuple[str, ...],
    number_of_features: int = 5,
) -> dict[str, Any]:
    """Return coefficients or feature importances."""

    preprocessor = model.named_steps["preprocessor"]
    transformed_names = tuple(
        str(name)
        for name in preprocessor.get_feature_names_out(
            canonical_feature_names
        )
    )

    classifier = model.named_steps["classifier"]

    if model_name == "logistic_regression":
        explanations: dict[str, list[dict[str, object]]] = {}

        for class_name, coefficients in zip(
            classifier.classes_,
            classifier.coef_,
            strict=True,
        ):
            ranked_indexes = np.argsort(
                np.abs(coefficients)
            )[::-1][:number_of_features]

            explanations[str(class_name)] = [
                {
                    "feature": transformed_names[index],
                    "coefficient": round(
                        float(coefficients[index]),
                        8,
                    ),
                    "absolute_coefficient": round(
                        float(abs(coefficients[index])),
                        8,
                    ),
                }
                for index in ranked_indexes
            ]

        return {
            "method": "multiclass_logistic_coefficients",
            "classes": explanations,
        }

    ranked_indexes = np.argsort(
        classifier.feature_importances_
    )[::-1][:number_of_features]

    return {
        "method": "random_forest_feature_importance",
        "features": [
            {
                "feature": transformed_names[index],
                "importance": round(
                    float(
                        classifier.feature_importances_[
                            index
                        ]
                    ),
                    8,
                ),
            }
            for index in ranked_indexes
        ],
    }


def persist_model_artifacts(
    output_directory: Path,
    selected_model_name: str,
    model: Pipeline,
    validation_evaluations: tuple[
        CandidateEvaluation,
        ...
    ],
    test_metrics: ClassificationMetrics,
    deterministic_baseline_metrics:
        ClassificationMetrics,
    feature_names: tuple[str, ...],
    explanation: dict[str, Any],
    train: DatasetMatrix,
    validation: DatasetMatrix,
    test: DatasetMatrix,
    random_seed: int = TRAINING_RANDOM_SEED,
) -> dict[str, Any]:
    """Persist the selected model and evidence metadata."""

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    model_path = output_directory / MODEL_ARTIFACT_NAME
    metadata_path = (
        output_directory / MODEL_METADATA_NAME
    )

    joblib.dump(model, model_path)

    model_digest = _sha256_file(model_path)

    metadata: dict[str, Any] = {
        "model_version": MODEL_VERSION,
        "feature_schema_version":
            FEATURE_SCHEMA_VERSION,
        "selected_model": selected_model_name,
        "selection_metric": "validation_macro_f1",
        "selection_rule": (
            "highest validation macro F1; "
            "lower validation log loss breaks ties"
        ),
        "random_seed": random_seed,
        "feature_columns": list(feature_names),
        "excluded_columns": [
            "incident_id",
            "category",
            "severity",
        ],
        "class_names": [
            str(class_name)
            for class_name in model.classes_
        ],
        "split_record_counts": {
            "train": len(train.labels),
            "validation": len(validation.labels),
            "test": len(test.labels),
        },
        "split_label_distributions": {
            "train": dict(
                sorted(Counter(train.labels).items())
            ),
            "validation": dict(
                sorted(
                    Counter(validation.labels).items()
                )
            ),
            "test": dict(
                sorted(Counter(test.labels).items())
            ),
        },
        "validation_candidates": {
            evaluation.model_name:
                evaluation.metrics.to_dict()
            for evaluation in validation_evaluations
        },
        "test_metrics": test_metrics.to_dict(),
        "deterministic_baseline_test_metrics":
            deterministic_baseline_metrics.to_dict(),
        "model_explanation": explanation,
        "model_artifact": {
            "path": MODEL_ARTIFACT_NAME,
            "sha256": model_digest,
        },
        "authority_boundary": (
            "The prediction is evidence only. "
            "It cannot authorize or execute an action."
        ),
    }

    with metadata_path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            metadata,
            handle,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")

    return metadata


def _validate_matrix_compatibility(
    train: DatasetMatrix,
    validation: DatasetMatrix,
) -> None:
    assert_no_label_leakage(train.feature_names)
    assert_no_label_leakage(
        validation.feature_names
    )

    if train.feature_names != validation.feature_names:
        raise ValueError(
            "Train and validation feature schemas differ"
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(65_536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()
