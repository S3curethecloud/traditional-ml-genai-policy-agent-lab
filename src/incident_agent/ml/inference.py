"""Typed inference for the selected incident classifier."""

from __future__ import annotations

import json
from dataclasses import astuple
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from incident_agent.baseline.contracts import IncidentFeatures
from incident_agent.data.contracts import FEATURE_COLUMNS
from incident_agent.ml.contracts import IncidentPrediction
from incident_agent.ml.data_loader import FEATURE_SCHEMA_VERSION
from incident_agent.ml.training import (
    MODEL_ARTIFACT_NAME,
    MODEL_METADATA_NAME,
)


class ModelArtifactError(ValueError):
    """Raised when model artifacts are missing or incompatible."""


class IncidentClassifier:
    """Load and execute a versioned incident classifier."""

    def __init__(
        self,
        model: Any,
        metadata: dict[str, Any],
    ) -> None:
        self._model = model
        self._metadata = metadata
        self._validate_metadata()

    @classmethod
    def load(
        cls,
        artifact_directory: Path,
    ) -> IncidentClassifier:
        model_path = (
            artifact_directory / MODEL_ARTIFACT_NAME
        )
        metadata_path = (
            artifact_directory / MODEL_METADATA_NAME
        )

        if not model_path.exists():
            raise ModelArtifactError(
                f"Model artifact not found: {model_path}"
            )

        if not metadata_path.exists():
            raise ModelArtifactError(
                f"Metadata not found: {metadata_path}"
            )

        model = joblib.load(model_path)

        with metadata_path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            metadata = json.load(handle)

        return cls(
            model=model,
            metadata=metadata,
        )

    def predict(
        self,
        features: IncidentFeatures,
    ) -> IncidentPrediction:
        """Return a typed probabilistic prediction."""

        feature_values = list(astuple(features))

        if len(feature_values) != len(FEATURE_COLUMNS):
            raise ModelArtifactError(
                "Inference feature count does not match schema"
            )

        matrix = np.asarray(
            [
                [
                    float("nan")
                    if value is None
                    else float(value)
                    for value in feature_values
                ]
            ],
            dtype=float,
        )

        predicted_category = str(
            self._model.predict(matrix)[0]
        )
        probabilities = self._model.predict_proba(
            matrix
        )[0]

        class_probabilities = {
            str(class_name): round(
                float(probability),
                8,
            )
            for class_name, probability in zip(
                self._model.classes_,
                probabilities,
                strict=True,
            )
        }

        return IncidentPrediction(
            predicted_category=predicted_category,
            confidence=max(class_probabilities.values()),
            class_probabilities=class_probabilities,
            model_version=str(
                self._metadata["model_version"]
            ),
            feature_schema_version=str(
                self._metadata[
                    "feature_schema_version"
                ]
            ),
        )

    def _validate_metadata(self) -> None:
        observed_features = tuple(
            self._metadata.get(
                "feature_columns",
                (),
            )
        )

        if observed_features != tuple(FEATURE_COLUMNS):
            raise ModelArtifactError(
                "Model feature schema does not match "
                "the runtime feature schema"
            )

        if (
            self._metadata.get(
                "feature_schema_version"
            )
            != FEATURE_SCHEMA_VERSION
        ):
            raise ModelArtifactError(
                "Feature schema version mismatch"
            )

        authority_boundary = self._metadata.get(
            "authority_boundary"
        )

        if not authority_boundary:
            raise ModelArtifactError(
                "Model metadata is missing "
                "the authority boundary"
            )
