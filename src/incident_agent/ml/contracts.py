"""Typed contracts for traditional ML training and inference."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DatasetMatrix:
    """A feature matrix and its traceability metadata."""

    features: Any
    labels: Any
    incident_ids: tuple[str, ...]
    feature_names: tuple[str, ...]


@dataclass(frozen=True)
class ClassificationMetrics:
    """Evaluation metrics for one classifier."""

    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    log_loss: float
    expected_calibration_error: float
    confusion_matrix: tuple[tuple[int, ...], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "accuracy": self.accuracy,
            "precision_macro": self.precision_macro,
            "recall_macro": self.recall_macro,
            "f1_macro": self.f1_macro,
            "log_loss": self.log_loss,
            "expected_calibration_error":
                self.expected_calibration_error,
            "confusion_matrix": [
                list(row)
                for row in self.confusion_matrix
            ],
        }


@dataclass(frozen=True)
class CandidateEvaluation:
    """Validation result for one candidate model."""

    model_name: str
    metrics: ClassificationMetrics


@dataclass(frozen=True)
class IncidentPrediction:
    """Typed inference result from the selected classifier."""

    predicted_category: str
    confidence: float
    class_probabilities: dict[str, float]
    model_version: str
    feature_schema_version: str

    def to_dict(self) -> dict[str, object]:
        return {
            "predicted_category": self.predicted_category,
            "confidence": self.confidence,
            "class_probabilities": self.class_probabilities,
            "model_version": self.model_version,
            "feature_schema_version": self.feature_schema_version,
        }
