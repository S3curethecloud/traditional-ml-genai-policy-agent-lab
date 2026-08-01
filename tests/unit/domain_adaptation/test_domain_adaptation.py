"""Tests for Phase 17 reusable domain adaptation packs."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from incident_agent.domain_adaptation.comparison import (
    compare_domain_packs,
    determine_adaptation_decision,
)
from incident_agent.domain_adaptation.contracts import (
    AdaptationDecision,
    PackValidationStatus,
)
from incident_agent.domain_adaptation.loading import (
    load_adaptation_policy,
    load_domain_pack,
)
from incident_agent.domain_adaptation.validation import (
    validate_domain_pack,
)


POLICY_PATH = Path(
    "config/domain-adaptation/"
    "domain-adaptation-policy.json"
)
IDENTITY_PATH = Path(
    "domains/identity-operations/domain-pack.json"
)
PAYMENTS_PATH = Path(
    "domains/payments-operations/domain-pack.json"
)


def policy():
    return load_adaptation_policy(POLICY_PATH)


def identity():
    return load_domain_pack(IDENTITY_PATH)


def payments():
    return load_domain_pack(PAYMENTS_PATH)


def test_adaptation_policy_loads() -> None:
    loaded = policy()

    assert (
        loaded["policy_version"]
        == "domain-adaptation-policy-v1"
    )


def test_automatic_adaptation_actions_are_disabled() -> None:
    loaded = policy()

    assert not loaded[
        "automatic_pack_activation_allowed"
    ]
    assert not loaded[
        "automatic_policy_mutation_allowed"
    ]
    assert not loaded[
        "automatic_tool_registration_allowed"
    ]
    assert not loaded["production_changes_allowed"]


def test_identity_pack_digest_is_reproducible() -> None:
    assert identity().digest == identity().digest


def test_payments_pack_digest_is_reproducible() -> None:
    assert payments().digest == payments().digest


def test_pack_ids_are_distinct() -> None:
    assert identity().pack_id != payments().pack_id


def test_identity_pack_is_valid() -> None:
    result = validate_domain_pack(
        identity(),
        policy(),
    )

    assert result.status is PackValidationStatus.VALID
    assert all(
        finding.passed
        for finding in result.findings
    )


def test_payments_pack_is_valid() -> None:
    result = validate_domain_pack(
        payments(),
        policy(),
    )

    assert result.status is PackValidationStatus.VALID


def test_unknown_capability_invalidates_pack() -> None:
    modified = replace(
        payments(),
        supported_capabilities=(
            *payments().supported_capabilities,
            "execute_unrestricted_production_action",
        ),
    )

    result = validate_domain_pack(
        modified,
        policy(),
    )

    assert result.status is PackValidationStatus.INVALID


def test_policy_expansion_invalidates_pack() -> None:
    modified = replace(
        payments(),
        may_expand_platform_policy=True,
    )

    result = validate_domain_pack(
        modified,
        policy(),
    )

    assert result.status is PackValidationStatus.INVALID


def test_cross_tenant_access_must_be_denied() -> None:
    modified = replace(
        payments(),
        deny_cross_tenant_access=False,
    )

    result = validate_domain_pack(
        modified,
        policy(),
    )

    assert result.status is PackValidationStatus.INVALID


def test_mutating_tool_requires_approval() -> None:
    tools = list(payments().tools)
    tools[-1] = replace(
        tools[-1],
        required_approval=False,
    )

    modified = replace(
        payments(),
        tools=tuple(tools),
    )

    result = validate_domain_pack(
        modified,
        policy(),
    )

    assert result.status is PackValidationStatus.INVALID


def test_domain_pack_cannot_execute_tools() -> None:
    modified = replace(
        payments(),
        domain_pack_can_execute_tools=True,
    )

    result = validate_domain_pack(
        modified,
        policy(),
    )

    assert result.status is PackValidationStatus.INVALID


def test_domain_pack_cannot_modify_policy() -> None:
    modified = replace(
        payments(),
        domain_pack_can_modify_platform_policy=True,
    )

    result = validate_domain_pack(
        modified,
        policy(),
    )

    assert result.status is PackValidationStatus.INVALID


def test_domain_pack_cannot_approve_exceptions() -> None:
    modified = replace(
        payments(),
        domain_pack_can_approve_exceptions=True,
    )

    result = validate_domain_pack(
        modified,
        policy(),
    )

    assert result.status is PackValidationStatus.INVALID


def test_domain_pack_cannot_activate_itself() -> None:
    modified = replace(
        payments(),
        domain_pack_can_activate_itself=True,
    )

    result = validate_domain_pack(
        modified,
        policy(),
    )

    assert result.status is PackValidationStatus.INVALID


def test_domain_taxonomies_are_isolated() -> None:
    comparison = compare_domain_packs(
        identity(),
        payments(),
    )

    assert comparison.isolated_taxonomies


def test_domain_evidence_sources_are_isolated() -> None:
    comparison = compare_domain_packs(
        identity(),
        payments(),
    )

    assert comparison.isolated_evidence_sources


def test_candidate_has_no_additional_capabilities() -> None:
    comparison = compare_domain_packs(
        identity(),
        payments(),
    )

    assert not comparison.candidate_only_capabilities


def test_valid_adaptation_is_ready_for_integration() -> None:
    loaded_policy = policy()
    reference = identity()
    candidate = payments()

    results = (
        validate_domain_pack(
            reference,
            loaded_policy,
        ),
        validate_domain_pack(
            candidate,
            loaded_policy,
        ),
    )

    comparison = compare_domain_packs(
        reference,
        candidate,
    )

    decision, reasons = determine_adaptation_decision(
        results,
        comparison,
    )

    assert (
        decision
        is AdaptationDecision.READY_FOR_INTEGRATION
    )
    assert not reasons


def test_invalid_candidate_blocks_adaptation() -> None:
    loaded_policy = policy()
    reference = identity()
    candidate = replace(
        payments(),
        may_expand_platform_policy=True,
    )

    results = (
        validate_domain_pack(
            reference,
            loaded_policy,
        ),
        validate_domain_pack(
            candidate,
            loaded_policy,
        ),
    )

    comparison = compare_domain_packs(
        reference,
        candidate,
    )

    decision, reasons = determine_adaptation_decision(
        results,
        comparison,
    )

    assert decision is AdaptationDecision.BLOCKED
    assert reasons
