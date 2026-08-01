"""Tests for Phase 16 security validation."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from incident_agent.security_validation.adversarial import (
    attack_block_rate,
    evaluate_adversarial_case,
    evaluate_adversarial_suite,
)
from incident_agent.security_validation.attestation import (
    build_security_attestation,
    count_open_critical_risks,
    evaluate_control_coverage,
)
from incident_agent.security_validation.contracts import (
    AttestationStatus,
    AttackOutcome,
    RiskSeverity,
    ValidationStatus,
)
from incident_agent.security_validation.loading import (
    canonical_sha256,
    load_adversarial_cases,
    load_compliance_controls,
    load_residual_risks,
    load_security_policy,
)


ROOT = Path(".")
POLICY_PATH = Path(
    "config/security-validation-policy.json"
)
CASES_PATH = Path(
    "security/phase-16-adversarial-cases.json"
)
MAPPING_PATH = Path(
    "security/phase-16-compliance-mapping.json"
)
RISKS_PATH = Path(
    "security/phase-16-residual-risks.json"
)


def policy():
    return load_security_policy(POLICY_PATH)


def cases():
    return load_adversarial_cases(CASES_PATH)[1]


def controls():
    return load_compliance_controls(MAPPING_PATH)


def risks():
    return load_residual_risks(RISKS_PATH)


def test_security_policy_loads() -> None:
    assert (
        policy()["policy_version"]
        == "security-validation-policy-v1"
    )


def test_automatic_security_actions_are_disabled() -> None:
    loaded = policy()

    assert not loaded[
        "automatic_remediation_allowed"
    ]
    assert not loaded[
        "automatic_exception_approval_allowed"
    ]


def test_ten_required_attack_categories_exist() -> None:
    required = set(
        policy()["required_attack_categories"]
    )
    actual = {
        case.category
        for case in cases()
    }

    assert len(required) == 10
    assert actual == required


def test_adversarial_case_ids_are_unique() -> None:
    loaded = cases()

    assert len(loaded) == len(
        {case.case_id for case in loaded}
    )


def test_prompt_injection_is_blocked() -> None:
    case = next(
        item
        for item in cases()
        if item.category == "prompt_injection"
    )

    result = evaluate_adversarial_case(case)

    assert result.observed_outcome is AttackOutcome.BLOCKED
    assert result.status is ValidationStatus.PASS


def test_cross_tenant_access_is_denied() -> None:
    case = next(
        item
        for item in cases()
        if item.category == "cross_tenant_access"
    )

    result = evaluate_adversarial_case(case)

    assert result.observed_outcome is AttackOutcome.DENIED


def test_policy_forgery_is_rejected() -> None:
    case = next(
        item
        for item in cases()
        if item.category == "policy_forgery"
    )

    result = evaluate_adversarial_case(case)

    assert result.observed_outcome is AttackOutcome.REJECTED


def test_promotion_abuse_requires_approval() -> None:
    case = next(
        item
        for item in cases()
        if item.category
        == "promotion_approval_abuse"
    )

    result = evaluate_adversarial_case(case)

    assert (
        result.observed_outcome
        is AttackOutcome.REQUIRE_APPROVAL
    )


def test_all_adversarial_cases_pass() -> None:
    results = evaluate_adversarial_suite(
        cases()
    )

    assert len(results) == 10
    assert all(
        item.status is ValidationStatus.PASS
        for item in results
    )


def test_attack_block_rate_is_one_hundred() -> None:
    results = evaluate_adversarial_suite(
        cases()
    )

    assert attack_block_rate(results) == 100.0


def test_empty_attack_results_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="At least one",
    ):
        attack_block_rate(())


def test_compliance_controls_are_unique() -> None:
    loaded = controls()

    assert len(loaded) == len(
        {item.control_id for item in loaded}
    )


def test_control_evidence_exists() -> None:
    result = evaluate_control_coverage(
        root=ROOT,
        controls=controls(),
    )

    assert result.covered_controls == result.total_controls
    assert result.coverage_percentage == 100.0
    assert result.passed


def test_missing_control_evidence_reduces_coverage() -> None:
    loaded = controls()
    modified = (
        replace(
            loaded[0],
            evidence_references=(
                "missing/evidence.json",
            ),
        ),
        *loaded[1:],
    )

    result = evaluate_control_coverage(
        root=ROOT,
        controls=modified,
    )

    assert not result.passed
    assert (
        result.covered_controls
        == result.total_controls - 1
    )


def test_no_open_critical_risks_exist() -> None:
    assert count_open_critical_risks(
        risks()
    ) == 0


def test_open_critical_risk_is_counted() -> None:
    modified = (
        replace(
            risks()[0],
            severity=RiskSeverity.CRITICAL,
            status="OPEN",
        ),
        *risks()[1:],
    )

    assert count_open_critical_risks(
        modified
    ) == 1


def test_residual_risks_have_no_approved_exceptions() -> None:
    assert all(
        not risk.exception_approved
        for risk in risks()
    )


def test_passing_attestation_is_approved() -> None:
    attestation = build_security_attestation(
        policy_version="test-policy",
        attack_block_rate_percentage=100.0,
        control_coverage_percentage=100.0,
        open_critical_risks=0,
        minimum_attack_block_rate_percentage=100.0,
        minimum_control_coverage_percentage=100.0,
        maximum_open_critical_risks=0,
    )

    assert (
        attestation.status
        is AttestationStatus.APPROVED
    )
    assert not attestation.reasons


def test_failed_attack_rate_blocks_attestation() -> None:
    attestation = build_security_attestation(
        policy_version="test-policy",
        attack_block_rate_percentage=90.0,
        control_coverage_percentage=100.0,
        open_critical_risks=0,
        minimum_attack_block_rate_percentage=100.0,
        minimum_control_coverage_percentage=100.0,
        maximum_open_critical_risks=0,
    )

    assert (
        attestation.status
        is AttestationStatus.BLOCKED
    )


def test_attestation_digest_is_reproducible() -> None:
    payload = {
        "attack_block_rate": 100.0,
        "coverage": 100.0,
        "critical_risks": 0,
    }

    assert canonical_sha256(
        payload
    ) == canonical_sha256(payload)
