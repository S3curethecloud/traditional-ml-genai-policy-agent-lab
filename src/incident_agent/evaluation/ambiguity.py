"""Sealed ambiguity evaluation for deterministic and ML classifiers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from incident_agent.baseline.classifier import classify_incident
from incident_agent.baseline.contracts import IncidentFeatures
from incident_agent.data.contracts import FEATURE_COLUMNS
from incident_agent.ml.inference import IncidentClassifier


AMBIGUITY_PACK_VERSION = "phase-3b-ambiguity-v1"

PROHIBITED_USES = frozenset(
    {
        "model_training",
        "hyperparameter_tuning",
        "model_selection",
        "threshold_optimization",
        "synthetic_dataset_generation",
    }
)


class AmbiguityPackError(ValueError):
    """Raised when the sealed ambiguity pack is invalid."""


@dataclass(frozen=True)
class AmbiguityCase:
    """One sealed classifier challenge case."""

    case_id: str
    title: str
    features: IncidentFeatures
    competing_signals: tuple[str, ...]
    contradictions: tuple[str, ...]
    expected_review_reason: str


@dataclass(frozen=True)
class AmbiguityResult:
    """Comparison result for one ambiguity case."""

    case_id: str
    title: str
    deterministic_category: str
    deterministic_confidence: float
    deterministic_matched_rules: tuple[str, ...]
    ml_category: str
    ml_confidence: float
    ml_second_category: str
    ml_second_probability: float
    ml_probability_margin: float
    class_probabilities: dict[str, float]
    classifiers_agree: bool
    competing_signals: tuple[str, ...]
    contradictions: tuple[str, ...]
    review_triggers: tuple[str, ...]
    requires_genai_review: bool
    authority_boundary: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)


def load_ambiguity_pack(path: Path) -> list[AmbiguityCase]:
    """Load and strictly validate the sealed challenge set."""

    with path.open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle)

    if not isinstance(document, dict):
        raise AmbiguityPackError("Pack root must be a mapping")

    pack = document.get("pack")

    if not isinstance(pack, dict):
        raise AmbiguityPackError("pack must be a mapping")

    if pack.get("id") != AMBIGUITY_PACK_VERSION:
        raise AmbiguityPackError(
            "Unexpected ambiguity pack version"
        )

    prohibited_uses = set(pack.get("prohibited_uses", []))

    if prohibited_uses != PROHIBITED_USES:
        raise AmbiguityPackError(
            "The prohibited-use declaration is incomplete"
        )

    raw_cases = pack.get("cases")

    if not isinstance(raw_cases, list) or not raw_cases:
        raise AmbiguityPackError(
            "Pack must contain at least one case"
        )

    cases: list[AmbiguityCase] = []
    seen_ids: set[str] = set()

    for raw_case in raw_cases:
        case = _parse_case(raw_case)

        if case.case_id in seen_ids:
            raise AmbiguityPackError(
                f"Duplicate ambiguity case ID: {case.case_id}"
            )

        seen_ids.add(case.case_id)
        cases.append(case)

    return cases


def evaluate_ambiguity_pack(
    cases: list[AmbiguityCase],
    classifier: IncidentClassifier,
) -> list[AmbiguityResult]:
    """Evaluate cases without fitting or mutating the model."""

    results: list[AmbiguityResult] = []

    for case in cases:
        deterministic = classify_incident(case.features)
        ml_prediction = classifier.predict(case.features)

        ranked_probabilities = sorted(
            ml_prediction.class_probabilities.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        top_category, top_probability = ranked_probabilities[0]
        second_category, second_probability = ranked_probabilities[1]
        probability_margin = top_probability - second_probability

        matched_rule_ids = tuple(
            rule.rule_id
            for rule in deterministic.matched_rules
        )

        review_triggers = _derive_review_triggers(
            deterministic_category=deterministic.category.value,
            ml_category=ml_prediction.predicted_category,
            ml_confidence=ml_prediction.confidence,
            probability_margin=probability_margin,
            matched_rule_count=len(matched_rule_ids),
            contradictions=case.contradictions,
        )

        results.append(
            AmbiguityResult(
                case_id=case.case_id,
                title=case.title,
                deterministic_category=
                    deterministic.category.value,
                deterministic_confidence=
                    deterministic.confidence,
                deterministic_matched_rules=
                    matched_rule_ids,
                ml_category=top_category,
                ml_confidence=top_probability,
                ml_second_category=second_category,
                ml_second_probability=second_probability,
                ml_probability_margin=probability_margin,
                class_probabilities=
                    ml_prediction.class_probabilities,
                classifiers_agree=(
                    deterministic.category.value
                    == ml_prediction.predicted_category
                ),
                competing_signals=
                    case.competing_signals,
                contradictions=case.contradictions,
                review_triggers=review_triggers,
                requires_genai_review=bool(
                    review_triggers
                ),
                authority_boundary=(
                    "Classifier outputs are diagnostic evidence only. "
                    "They cannot authorize or execute an action."
                ),
            )
        )

    return results


def build_ambiguity_report(
    cases_path: Path,
    model_path: Path,
    metadata_path: Path,
    results: list[AmbiguityResult],
) -> dict[str, Any]:
    """Build immutable evidence describing the challenge run."""

    disagreements = [
        result
        for result in results
        if not result.classifiers_agree
    ]

    low_margin_results = [
        result
        for result in results
        if result.ml_probability_margin < 0.20
    ]

    multiple_rule_results = [
        result
        for result in results
        if len(result.deterministic_matched_rules) > 1
    ]

    return {
        "evaluation_pack_version":
            AMBIGUITY_PACK_VERSION,
        "evaluation_type":
            "sealed_post_selection_challenge",
        "training_performed": False,
        "model_selection_performed": False,
        "threshold_tuning_performed": False,
        "input_artifacts": {
            "ambiguity_pack": {
                "path": str(cases_path),
                "sha256": sha256_file(cases_path),
            },
            "locked_model": {
                "path": str(model_path),
                "sha256": sha256_file(model_path),
            },
            "locked_metadata": {
                "path": str(metadata_path),
                "sha256": sha256_file(metadata_path),
            },
        },
        "summary": {
            "case_count": len(results),
            "classifier_agreement_count":
                len(results) - len(disagreements),
            "classifier_disagreement_count":
                len(disagreements),
            "low_ml_margin_count":
                len(low_margin_results),
            "multiple_rule_match_count":
                len(multiple_rule_results),
            "genai_review_required_count": sum(
                result.requires_genai_review
                for result in results
            ),
        },
        "results": [
            result.to_dict()
            for result in results
        ],
        "downstream_instruction": (
            "Use disagreement, competing signals, contradictions, "
            "confidence, and probability margin as evidence for "
            "GenAI hypothesis generation. Do not treat either "
            "classifier as authorization."
        ),
    }


def write_ambiguity_report(
    path: Path,
    report: dict[str, Any],
) -> None:
    """Persist the evaluation report deterministically."""

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        json.dump(
            report,
            handle,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")


def sha256_file(path: Path) -> str:
    """Calculate a SHA-256 artifact digest."""

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(65_536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _parse_case(raw_case: Any) -> AmbiguityCase:
    if not isinstance(raw_case, dict):
        raise AmbiguityPackError(
            "Each ambiguity case must be a mapping"
        )

    raw_features = raw_case.get("features")

    if not isinstance(raw_features, dict):
        raise AmbiguityPackError(
            "Case features must be a mapping"
        )

    observed_feature_names = tuple(
        raw_features.keys()
    )

    if observed_feature_names != tuple(FEATURE_COLUMNS):
        raise AmbiguityPackError(
            "Ambiguity case feature schema mismatch. "
            f"expected={tuple(FEATURE_COLUMNS)}, "
            f"observed={observed_feature_names}"
        )

    case_id = str(raw_case.get("id", "")).strip()
    title = str(raw_case.get("title", "")).strip()
    review_reason = str(
        raw_case.get(
            "expected_review_reason",
            "",
        )
    ).strip()

    if not case_id or not title or not review_reason:
        raise AmbiguityPackError(
            "Case ID, title, and review reason are required"
        )

    features = IncidentFeatures(
        login_failure_rate=float(
            raw_features["login_failure_rate"]
        ),
        token_validation_error_rate=float(
            raw_features[
                "token_validation_error_rate"
            ]
        ),
        http_5xx_rate=float(
            raw_features["http_5xx_rate"]
        ),
        latency_p95_ms=float(
            raw_features["latency_p95_ms"]
        ),
        cpu_utilization_percent=float(
            raw_features[
                "cpu_utilization_percent"
            ]
        ),
        memory_utilization_percent=float(
            raw_features[
                "memory_utilization_percent"
            ]
        ),
        dependency_error_rate=float(
            raw_features["dependency_error_rate"]
        ),
        network_packet_loss_percent=float(
            raw_features[
                "network_packet_loss_percent"
            ]
        ),
        deployment_age_minutes=(
            None
            if raw_features[
                "deployment_age_minutes"
            ] is None
            else int(
                raw_features[
                    "deployment_age_minutes"
                ]
            )
        ),
        affected_user_count=int(
            raw_features["affected_user_count"]
        ),
        regions_affected=int(
            raw_features["regions_affected"]
        ),
    )

    return AmbiguityCase(
        case_id=case_id,
        title=title,
        features=features,
        competing_signals=tuple(
            str(value)
            for value in raw_case.get(
                "competing_signals",
                [],
            )
        ),
        contradictions=tuple(
            str(value)
            for value in raw_case.get(
                "contradictions",
                [],
            )
        ),
        expected_review_reason=review_reason,
    )


def _derive_review_triggers(
    deterministic_category: str,
    ml_category: str,
    ml_confidence: float,
    probability_margin: float,
    matched_rule_count: int,
    contradictions: tuple[str, ...],
) -> tuple[str, ...]:
    triggers: list[str] = []

    if deterministic_category != ml_category:
        triggers.append("classifier_disagreement")

    if ml_confidence < 0.70:
        triggers.append("low_ml_confidence")

    if probability_margin < 0.20:
        triggers.append("low_ml_probability_margin")

    if matched_rule_count > 1:
        triggers.append("multiple_deterministic_rules_matched")

    if contradictions:
        triggers.append("contradictory_evidence_present")

    return tuple(triggers)
