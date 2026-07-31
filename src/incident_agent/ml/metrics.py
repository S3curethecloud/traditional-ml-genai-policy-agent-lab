"""Classification and probability-calibration metrics."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
)

from incident_agent.ml.contracts import ClassificationMetrics


def evaluate_classifier(
    labels: np.ndarray,
    predictions: np.ndarray,
    probabilities: np.ndarray,
    class_names: np.ndarray,
) -> ClassificationMetrics:
    """Calculate required classification and calibration metrics."""

    matrix = confusion_matrix(
        labels,
        predictions,
        labels=class_names,
    )

    return ClassificationMetrics(
        accuracy=float(
            accuracy_score(labels, predictions)
        ),
        precision_macro=float(
            precision_score(
                labels,
                predictions,
                average="macro",
                zero_division=0,
            )
        ),
        recall_macro=float(
            recall_score(
                labels,
                predictions,
                average="macro",
                zero_division=0,
            )
        ),
        f1_macro=float(
            f1_score(
                labels,
                predictions,
                average="macro",
                zero_division=0,
            )
        ),
        log_loss=float(
            log_loss(
                labels,
                probabilities,
                labels=class_names,
            )
        ),
        expected_calibration_error=float(
            expected_calibration_error(
                labels=labels,
                predictions=predictions,
                probabilities=probabilities,
            )
        ),
        confusion_matrix=tuple(
            tuple(int(value) for value in row)
            for row in matrix
        ),
    )


def expected_calibration_error(
    labels: np.ndarray,
    predictions: np.ndarray,
    probabilities: np.ndarray,
    number_of_bins: int = 10,
) -> float:
    """Calculate confidence-based multiclass calibration error."""

    if number_of_bins < 2:
        raise ValueError("number_of_bins must be at least 2")

    confidences = probabilities.max(axis=1)
    correctness = (predictions == labels).astype(float)

    bin_edges = np.linspace(
        0.0,
        1.0,
        number_of_bins + 1,
    )

    calibration_error = 0.0
    observation_count = len(labels)

    for bin_index in range(number_of_bins):
        lower = bin_edges[bin_index]
        upper = bin_edges[bin_index + 1]

        if bin_index == 0:
            in_bin = (
                (confidences >= lower)
                & (confidences <= upper)
            )
        else:
            in_bin = (
                (confidences > lower)
                & (confidences <= upper)
            )

        bin_count = int(in_bin.sum())

        if bin_count == 0:
            continue

        average_confidence = float(
            confidences[in_bin].mean()
        )
        average_accuracy = float(
            correctness[in_bin].mean()
        )

        calibration_error += (
            bin_count
            / observation_count
            * abs(average_accuracy - average_confidence)
        )

    return calibration_error
