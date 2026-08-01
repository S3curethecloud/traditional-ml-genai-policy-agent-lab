"""Tests for Phase 19 operational readiness."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from incident_agent.operational_readiness.contracts import (
    ReadinessDecision,
)
from incident_agent.operational_readiness.evaluation import (
    calculate_readiness_metrics,
    determine_readiness_decision,
)
from incident_agent.operational_readiness.loading import (
    load_access_profile,
    load_handoff_checklist,
    load_ownership_model,
    load_readiness_policy,
    load_runbook_catalog,
)


POLICY_PATH = Path(
    "config/operational-readiness/"
    "operational-readiness-policy.json"
)
OWNERSHIP_PATH = Path(
    "operations/handoff/ownership-model.json"
)
RUNBOOK_PATH = Path(
    "operations/runbooks/runbook-catalog.json"
)
ACCESS_PATH = Path(
    "operations/handoff/access-readiness.json"
)
CHECKLIST_PATH = Path(
    "operations/handoff/"
    "production-handoff-checklist.json"
)


def policy():
    return load_readiness_policy(POLICY_PATH)


def ownership():
    return load_ownership_model(OWNERSHIP_PATH)


def runbooks():
    return load_runbook_catalog(RUNBOOK_PATH)


def access():
    return load_access_profile(ACCESS_PATH)


def checklist():
    return load_handoff_checklist(CHECKLIST_PATH)


def test_readiness_policy_loads() -> None:
    assert (
        policy()["policy_version"]
        == "operational-readiness-policy-v1"
    )


def test_automatic_handoff_actions_are_disabled() -> None:
    loaded = policy()

    assert not loaded["automatic_handoff_allowed"]
    assert not loaded[
        "automatic_access_provisioning_allowed"
    ]
    assert not loaded[
        "automatic_owner_assignment_allowed"
    ]
    assert not loaded[
        "automatic_production_activation_allowed"
    ]


def test_required_capabilities_have_owners() -> None:
    assignments = ownership()[1]

    assert set(
        policy()["required_operational_capabilities"]
    ) <= {
        item.capability
        for item in assignments
    }


def test_each_capability_has_accountable_role() -> None:
    assignments = ownership()[1]

    assert all(
        item.accountable_role
        for item in assignments
    )


def test_each_capability_has_responsible_role() -> None:
    assignments = ownership()[1]

    assert all(
        item.responsible_role
        for item in assignments
    )


def test_required_support_tiers_are_present() -> None:
    tiers = ownership()[2]

    assert set(
        policy()["required_support_tiers"]
    ) <= {
        item.tier
        for item in tiers
    }


def test_support_tiers_have_no_production_authority() -> None:
    tiers = ownership()[2]

    assert all(
        not item.may_execute_production_tools
        for item in tiers
    )


def test_ownership_model_assigns_no_real_people() -> None:
    flags = ownership()[3]

    assert not flags["automatic_owner_assignment"]
    assert not flags["real_people_assigned"]
    assert not flags[
        "production_authority_transferred"
    ]


def test_required_runbooks_are_present() -> None:
    loaded = runbooks()[1]

    assert set(
        policy()["required_runbooks"]
    ) <= {
        item.runbook_id
        for item in loaded
    }


def test_runbook_ids_are_unique() -> None:
    loaded = runbooks()[1]
    ids = tuple(
        item.runbook_id
        for item in loaded
    )

    assert len(ids) == len(set(ids))


def test_runbooks_do_not_mutate_production() -> None:
    loaded = runbooks()[1]

    assert all(
        not item.production_mutation_allowed
        for item in loaded
    )


def test_required_access_controls_are_implemented() -> None:
    controls = access()[1]

    assert set(
        policy()["required_access_controls"]
    ) <= {
        item.control_id
        for item in controls
        if item.implemented
    }


def test_access_profile_changes_no_access_state() -> None:
    flags = access()[2]

    assert not any(flags.values())


def test_required_handoff_checks_pass() -> None:
    checks = checklist()[1]

    assert all(
        check.passed
        for check in checks
        if check.required
    )


def test_handoff_check_ids_are_unique() -> None:
    checks = checklist()[1]
    ids = tuple(
        item.check_id
        for item in checks
    )

    assert len(ids) == len(set(ids))


def test_required_evidence_is_covered() -> None:
    checks = checklist()[1]

    assert set(
        policy()["required_evidence_artifacts"]
    ) <= {
        check.evidence_id
        for check in checks
        if check.passed
    }


def test_readiness_metrics_are_one_hundred_percent() -> None:
    metrics = calculate_readiness_metrics(
        policy=policy(),
        assignments=ownership()[1],
        runbooks=runbooks()[1],
        checks=checklist()[1],
    )

    assert metrics.check_pass_rate_percentage == 100.0
    assert metrics.owner_coverage_percentage == 100.0
    assert metrics.runbook_coverage_percentage == 100.0
    assert metrics.evidence_coverage_percentage == 100.0


def test_valid_handoff_is_ready_for_release_closure() -> None:
    metrics = calculate_readiness_metrics(
        policy=policy(),
        assignments=ownership()[1],
        runbooks=runbooks()[1],
        checks=checklist()[1],
    )

    decision, reasons = determine_readiness_decision(
        policy=policy(),
        metrics=metrics,
        support_tiers=ownership()[2],
        access_controls=access()[1],
        ownership_flags=ownership()[3],
        access_flags=access()[2],
    )

    assert (
        decision
        is ReadinessDecision
        .READY_FOR_CONTROLLED_RELEASE_CLOSURE
    )
    assert not reasons


def test_failed_required_check_blocks_handoff() -> None:
    checks = list(checklist()[1])
    checks[0] = replace(
        checks[0],
        passed=False,
    )

    metrics = calculate_readiness_metrics(
        policy=policy(),
        assignments=ownership()[1],
        runbooks=runbooks()[1],
        checks=tuple(checks),
    )

    decision, reasons = determine_readiness_decision(
        policy=policy(),
        metrics=metrics,
        support_tiers=ownership()[2],
        access_controls=access()[1],
        ownership_flags=ownership()[3],
        access_flags=access()[2],
    )

    assert decision is ReadinessDecision.BLOCKED
    assert reasons


def test_access_change_blocks_handoff() -> None:
    metrics = calculate_readiness_metrics(
        policy=policy(),
        assignments=ownership()[1],
        runbooks=runbooks()[1],
        checks=checklist()[1],
    )

    changed_flags = dict(access()[2])
    changed_flags["access_granted"] = True

    decision, reasons = determine_readiness_decision(
        policy=policy(),
        metrics=metrics,
        support_tiers=ownership()[2],
        access_controls=access()[1],
        ownership_flags=ownership()[3],
        access_flags=changed_flags,
    )

    assert decision is ReadinessDecision.BLOCKED
    assert reasons
