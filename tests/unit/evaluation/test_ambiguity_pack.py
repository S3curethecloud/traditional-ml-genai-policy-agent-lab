"""Tests for the sealed Phase 3B ambiguity evaluation pack."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from incident_agent.data.contracts import (
    FEATURE_COLUMNS,
)
from incident_agent.evaluation.ambiguity import (
    AMBIGUITY_PACK_VERSION,
    AmbiguityPackError,
    build_ambiguity_report,
    evaluate_ambiguity_pack,
    load_ambiguity_pack,
    sha256_file,
    write_ambiguity_report,
)
from incident_agent.ml.inference import (
    IncidentClassifier,
)


PACK_PATH = Path(
    "data/ambiguity/phase-3b-cases.yaml"
)

MODEL_DIRECTORY = Path(
    "models/incident-classifier"
)


def test_pack_contains_eight_unique_cases() -> None:
    cases = load_ambiguity_pack(PACK_PATH)

    identifiers = [
        case.case_id
        for case in cases
    ]

    assert len(cases) == 8
    assert len(identifiers) == len(
        set(identifiers)
    )


def test_pack_declares_prohibited_uses() -> None:
    document = yaml.safe_load(
        PACK_PATH.read_text(encoding="utf-8")
    )

    assert (
        document["pack"]["id"]
        == AMBIGUITY_PACK_VERSION
    )

    assert set(
        document["pack"]["prohibited_uses"]
    ) == {
        "model_training",
        "hyperparameter_tuning",
        "model_selection",
        "threshold_optimization",
        "synthetic_dataset_generation",
    }


def test_case_feature_schema_is_exact() -> None:
    document = yaml.safe_load(
        PACK_PATH.read_text(encoding="utf-8")
    )

    for case in document["pack"]["cases"]:
        assert tuple(
            case["features"].keys()
        ) == tuple(FEATURE_COLUMNS)


def test_pack_contains_no_training_labels() -> None:
    document = yaml.safe_load(
        PACK_PATH.read_text(encoding="utf-8")
    )

    prohibited_fields = {
        "category",
        "severity",
        "expected_category",
        "training_label",
        "split",
    }

    for case in document["pack"]["cases"]:
        assert not (
            set(case) & prohibited_fields
        )

        assert not (
            set(case["features"])
            & prohibited_fields
        )


def test_evaluation_does_not_modify_locked_artifacts() -> None:
    model_path = (
        MODEL_DIRECTORY / "model.joblib"
    )
    metadata_path = (
        MODEL_DIRECTORY / "metadata.json"
    )

    before_model = sha256_file(model_path)
    before_metadata = sha256_file(
        metadata_path
    )

    classifier = IncidentClassifier.load(
        MODEL_DIRECTORY
    )
    cases = load_ambiguity_pack(PACK_PATH)

    evaluate_ambiguity_pack(
        cases,
        classifier,
    )

    assert sha256_file(model_path) == before_model
    assert (
        sha256_file(metadata_path)
        == before_metadata
    )


def test_each_case_produces_comparison_evidence() -> None:
    classifier = IncidentClassifier.load(
        MODEL_DIRECTORY
    )
    cases = load_ambiguity_pack(PACK_PATH)

    results = evaluate_ambiguity_pack(
        cases,
        classifier,
    )

    assert len(results) == len(cases)

    for result in results:
        assert result.deterministic_category
        assert result.ml_category
        assert 0.0 <= result.ml_confidence <= 1.0
        assert (
            0.0
            <= result.ml_probability_margin
            <= 1.0
        )
        assert len(
            result.class_probabilities
        ) == 6
        assert (
            "evidence only"
            in result.authority_boundary
        )


def test_pack_exposes_competing_classifier_evidence() -> None:
    classifier = IncidentClassifier.load(
        MODEL_DIRECTORY
    )
    cases = load_ambiguity_pack(PACK_PATH)

    results = evaluate_ambiguity_pack(
        cases,
        classifier,
    )

    assert any(
        not result.classifiers_agree
        or len(
            result.deterministic_matched_rules
        ) > 1
        or result.ml_probability_margin < 0.20
        for result in results
    )


def test_every_case_requires_genai_review() -> None:
    classifier = IncidentClassifier.load(
        MODEL_DIRECTORY
    )
    cases = load_ambiguity_pack(PACK_PATH)

    results = evaluate_ambiguity_pack(
        cases,
        classifier,
    )

    assert all(
        result.requires_genai_review
        for result in results
    )


def test_report_records_no_training_or_selection(
    tmp_path: Path,
) -> None:
    classifier = IncidentClassifier.load(
        MODEL_DIRECTORY
    )
    cases = load_ambiguity_pack(PACK_PATH)
    results = evaluate_ambiguity_pack(
        cases,
        classifier,
    )

    report = build_ambiguity_report(
        cases_path=PACK_PATH,
        model_path=(
            MODEL_DIRECTORY / "model.joblib"
        ),
        metadata_path=(
            MODEL_DIRECTORY / "metadata.json"
        ),
        results=results,
    )

    output = tmp_path / "report.json"
    write_ambiguity_report(
        output,
        report,
    )

    persisted = json.loads(
        output.read_text(encoding="utf-8")
    )

    assert persisted["training_performed"] is False
    assert (
        persisted["model_selection_performed"]
        is False
    )
    assert (
        persisted["threshold_tuning_performed"]
        is False
    )


def test_duplicate_case_id_is_rejected(
    tmp_path: Path,
) -> None:
    document = yaml.safe_load(
        PACK_PATH.read_text(encoding="utf-8")
    )

    document["pack"]["cases"][1]["id"] = (
        document["pack"]["cases"][0]["id"]
    )

    duplicate_pack = tmp_path / "duplicate.yaml"
    duplicate_pack.write_text(
        yaml.safe_dump(
            document,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        AmbiguityPackError,
        match="Duplicate",
    ):
        load_ambiguity_pack(duplicate_pack)


def test_feature_schema_drift_is_rejected(
    tmp_path: Path,
) -> None:
    document = yaml.safe_load(
        PACK_PATH.read_text(encoding="utf-8")
    )

    del document["pack"]["cases"][0][
        "features"
    ]["memory_utilization_percent"]

    drifted_pack = tmp_path / "drifted.yaml"
    drifted_pack.write_text(
        yaml.safe_dump(
            document,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        AmbiguityPackError,
        match="schema mismatch",
    ):
        load_ambiguity_pack(drifted_pack)
