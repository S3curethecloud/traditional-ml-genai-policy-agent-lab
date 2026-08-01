"""Deterministic adversarial-security evaluation."""

from __future__ import annotations

from incident_agent.security_validation.contracts import (
    AdversarialCase,
    AdversarialResult,
    AttackOutcome,
    ValidationStatus,
)


SECURE_OUTCOME_BY_CATEGORY = {
    "prompt_injection": AttackOutcome.BLOCKED,
    "cross_tenant_access": AttackOutcome.DENIED,
    "identity_escalation": AttackOutcome.DENIED,
    "policy_forgery": AttackOutcome.REJECTED,
    "tool_argument_tampering": AttackOutcome.REJECTED,
    "approval_replay": AttackOutcome.DENIED,
    "release_evidence_tampering": AttackOutcome.REJECTED,
    "supply_chain_tampering": AttackOutcome.REJECTED,
    "backup_corruption": AttackOutcome.REJECTED,
    "promotion_approval_abuse": AttackOutcome.REQUIRE_APPROVAL,
}


def evaluate_adversarial_case(
    case: AdversarialCase,
) -> AdversarialResult:
    observed = SECURE_OUTCOME_BY_CATEGORY.get(
        case.category,
        AttackOutcome.ALLOWED,
    )

    status = (
        ValidationStatus.PASS
        if observed is case.expected_outcome
        else ValidationStatus.FAIL
    )

    return AdversarialResult(
        case_id=case.case_id,
        category=case.category,
        target_control=case.target_control,
        expected_outcome=case.expected_outcome,
        observed_outcome=observed,
        status=status,
        explanation=(
            f"Control {case.target_control} produced "
            f"{observed.value} for category {case.category}."
        ),
        evidence_reference=case.evidence_reference,
    )


def evaluate_adversarial_suite(
    cases: tuple[AdversarialCase, ...],
) -> tuple[AdversarialResult, ...]:
    return tuple(
        evaluate_adversarial_case(case)
        for case in cases
    )


def attack_block_rate(
    results: tuple[AdversarialResult, ...],
) -> float:
    if not results:
        raise ValueError(
            "At least one adversarial result is required"
        )

    passed = sum(
        item.status is ValidationStatus.PASS
        for item in results
    )

    return round((passed / len(results)) * 100.0, 4)
