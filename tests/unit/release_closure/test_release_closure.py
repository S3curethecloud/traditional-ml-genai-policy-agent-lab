"""Tests for Phase 20 controlled release closure."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from incident_agent.release_closure.contracts import (
    ReleaseClosureDecision,
)
from incident_agent.release_closure.evaluation import (
    calculate_closure_metrics,
    determine_release_closure,
)
from incident_agent.release_closure.loading import (
    load_authority_boundary,
    load_closure_policy,
    load_evidence_registry,
    load_recovery_closure,
    load_release_candidate,
    load_release_gates,
    load_risk_closure,
)


POLICY_PATH = Path(
    "config/release-closure/"
    "release-closure-policy.json"
)
CANDIDATE_PATH = Path(
    "release/closure/release-candidate.json"
)
EVIDENCE_PATH = Path(
    "release/closure/evidence-registry.json"
)
GATES_PATH = Path(
    "release/closure/release-gates.json"
)
RISK_PATH = Path(
    "release/closure/"
    "risk-and-exception-closure.json"
)
RECOVERY_PATH = Path(
    "release/closure/rollback-and-recovery.json"
)
AUTHORITY_PATH = Path(
    "release/closure/authority-boundary.json"
)


def policy():
    return load_closure_policy(POLICY_PATH)


def candidate():
    return load_release_candidate(CANDIDATE_PATH)


def evidence():
    return load_evidence_registry(EVIDENCE_PATH)


def gates():
    return load_release_gates(GATES_PATH)


def risks():
    return load_risk_closure(RISK_PATH)


def recovery():
    return load_recovery_closure(RECOVERY_PATH)


def authority():
    return load_authority_boundary(AUTHORITY_PATH)


def metrics():
    return calculate_closure_metrics(
        policy=policy(),
        gates=gates()[1],
        evidence=evidence()[1],
        risk_values=risks()[2],
        recovery=recovery()[1],
        restrictions=authority()[1],
    )


def decision(
    release_candidate=None,
    closure_metrics=None,
    evidence_flags=None,
    risk_values=None,
    recovery_capabilities=None,
    recovery_flags=None,
    authority_flags=None,
):
    return determine_release_closure(
        policy=policy(),
        candidate=(
            release_candidate
            if release_candidate is not None
            else candidate()
        ),
        metrics=(
            closure_metrics
            if closure_metrics is not None
            else metrics()
        ),
        evidence_flags=(
            evidence_flags
            if evidence_flags is not None
            else evidence()[2]
        ),
        risk_values=(
            risk_values
            if risk_values is not None
            else risks()[2]
        ),
        recovery=(
            recovery_capabilities
            if recovery_capabilities is not None
            else recovery()[1]
        ),
        recovery_flags=(
            recovery_flags
            if recovery_flags is not None
            else recovery()[2]
        ),
        authority_flags=(
            authority_flags
            if authority_flags is not None
            else authority()[2]
        ),
    )


def test_release_closure_policy_loads() -> None:
    assert (
        policy()["policy_version"]
        == "release-closure-policy-v1"
    )


def test_automatic_release_actions_are_disabled() -> None:
    loaded = policy()

    assert not loaded[
        "automatic_release_approval_allowed"
    ]
    assert not loaded["automatic_deployment_allowed"]
    assert not loaded[
        "automatic_traffic_shift_allowed"
    ]
    assert not loaded[
        "automatic_exception_approval_allowed"
    ]
    assert not loaded[
        "automatic_risk_acceptance_allowed"
    ]
    assert not loaded[
        "production_authority_transfer_allowed"
    ]


def test_release_candidate_is_immutable() -> None:
    assert candidate().immutable


def test_release_manifest_digest_is_reproducible() -> None:
    assert (
        candidate().manifest_digest
        == candidate().manifest_digest
    )


def test_release_candidate_records_no_side_effects() -> None:
    loaded = candidate()

    assert not loaded.deployment_performed
    assert not loaded.traffic_shift_performed
    assert not loaded.production_activation_performed


def test_required_phase_evidence_is_covered() -> None:
    required = set(
        policy()["required_phase_evidence"]
    )
    covered = {
        item.evidence_id
        for item in evidence()[1]
        if item.required and item.validated
    }

    assert required <= covered


def test_prior_evidence_is_not_mutated() -> None:
    assert not any(evidence()[2].values())


def test_required_release_gates_pass() -> None:
    required = set(
        policy()["required_release_gates"]
    )
    passed = {
        item.gate_id
        for item in gates()[1]
        if item.passed
    }

    assert required <= passed


def test_open_critical_risks_are_zero() -> None:
    assert risks()[2]["open_critical_risks"] == 0


def test_approved_exceptions_are_zero() -> None:
    assert risks()[2]["approved_exceptions"] == 0


def test_no_automatic_risk_or_exception_action() -> None:
    values = risks()[2]

    assert values["automatically_accepted_risks"] == 0
    assert (
        values[
            "automatically_approved_exceptions"
        ]
        == 0
    )
    assert not values["risk_acceptance_performed"]
    assert not values["exception_approval_performed"]


def test_required_recovery_capabilities_are_verified() -> None:
    required = set(
        policy()["required_recovery_capabilities"]
    )
    verified = {
        item.capability
        for item in recovery()[1]
        if item.verified
    }

    assert required <= verified


def test_recovery_is_never_automatic() -> None:
    assert all(
        not item.automatic_execution
        for item in recovery()[1]
    )


def test_recovery_closure_changes_no_state() -> None:
    assert not any(recovery()[2].values())


def test_required_authority_restrictions_are_preserved() -> None:
    required = set(
        policy()["required_authority_restrictions"]
    )
    preserved = {
        item.restriction
        for item in authority()[1]
        if item.preserved
    }

    assert required <= preserved


def test_authority_boundary_changes_no_production_access() -> None:
    flags = authority()[2]

    assert flags["production_approval_required"]
    assert not flags["production_approver_assigned"]
    assert not flags["deployment_credentials_created"]
    assert not flags["deployment_credentials_used"]
    assert not flags["production_access_granted"]
    assert not flags[
        "production_authority_transferred"
    ]


def test_closure_metrics_are_complete() -> None:
    loaded = metrics()

    assert loaded.gate_pass_rate_percentage == 100.0
    assert (
        loaded.evidence_coverage_percentage
        == 100.0
    )
    assert loaded.open_critical_risks == 0
    assert loaded.approved_exceptions == 0
    assert (
        loaded.verified_recovery_capabilities
        == loaded.required_recovery_capabilities
    )
    assert (
        loaded.preserved_authority_restrictions
        == loaded.required_authority_restrictions
    )


def test_valid_release_is_ready_for_controlled_deployment() -> None:
    result, reasons = decision()

    assert (
        result
        is ReleaseClosureDecision
        .READY_FOR_CONTROLLED_DEPLOYMENT
    )
    assert not reasons


def test_open_critical_risk_blocks_closure() -> None:
    changed = dict(risks()[2])
    changed["open_critical_risks"] = 1

    changed_metrics = calculate_closure_metrics(
        policy=policy(),
        gates=gates()[1],
        evidence=evidence()[1],
        risk_values=changed,
        recovery=recovery()[1],
        restrictions=authority()[1],
    )

    result, reasons = decision(
        closure_metrics=changed_metrics,
        risk_values=changed,
    )

    assert result is ReleaseClosureDecision.BLOCKED
    assert reasons


def test_production_access_change_blocks_closure() -> None:
    changed = dict(authority()[2])
    changed["production_access_granted"] = True

    result, reasons = decision(
        authority_flags=changed,
    )

    assert result is ReleaseClosureDecision.BLOCKED
    assert reasons
