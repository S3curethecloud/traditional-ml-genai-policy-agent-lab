"""Tests for Phase 18 platform integration acceptance."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from incident_agent.integration_acceptance.contracts import (
    AcceptanceOutcome,
    PlatformAcceptanceDecision,
    ScenarioStatus,
)
from incident_agent.integration_acceptance.evaluation import (
    calculate_acceptance_metrics,
    determine_platform_acceptance,
)
from incident_agent.integration_acceptance.harness import (
    STAGE_ORDER,
    determine_outcome,
    execute_acceptance_scenario,
    execute_acceptance_suite,
)
from incident_agent.integration_acceptance.loading import (
    load_acceptance_policy,
    load_acceptance_scenarios,
)


POLICY_PATH = Path(
    "config/integration-acceptance/"
    "integration-acceptance-policy.json"
)
SCENARIOS_PATH = Path(
    "acceptance/scenarios/"
    "phase-18-acceptance-scenarios.json"
)


def policy():
    return load_acceptance_policy(POLICY_PATH)


def scenarios():
    return load_acceptance_scenarios(
        SCENARIOS_PATH
    )[1]


def test_acceptance_policy_loads() -> None:
    assert (
        policy()["policy_version"]
        == "integration-acceptance-policy-v1"
    )


def test_automatic_acceptance_actions_are_disabled() -> None:
    loaded = policy()

    assert not loaded[
        "automatic_acceptance_approval_allowed"
    ]
    assert not loaded[
        "automatic_exception_approval_allowed"
    ]
    assert not loaded[
        "automatic_remediation_allowed"
    ]
    assert not loaded["production_execution_allowed"]


def test_scenario_ids_are_unique() -> None:
    loaded = scenarios()

    assert len(loaded) == len(
        {item.scenario_id for item in loaded}
    )


def test_required_domains_are_present() -> None:
    actual = {
        item.domain
        for item in scenarios()
    }

    assert set(policy()["required_domains"]) <= actual


def test_required_scenario_types_are_present() -> None:
    actual = {
        item.scenario_type
        for item in scenarios()
    }

    assert (
        set(policy()["required_scenario_types"])
        <= actual
    )


def test_authorized_identity_scenario_completes() -> None:
    scenario = next(
        item
        for item in scenarios()
        if item.scenario_id
        == "identity-authorized-success"
    )

    assert (
        determine_outcome(scenario)
        is AcceptanceOutcome.COMPLETED
    )


def test_cross_tenant_scenario_is_denied() -> None:
    scenario = next(
        item
        for item in scenarios()
        if item.scenario_type
        == "cross_tenant_denial"
    )

    assert (
        determine_outcome(scenario)
        is AcceptanceOutcome.DENIED
    )


def test_prompt_injection_is_escalated() -> None:
    scenario = next(
        item
        for item in scenarios()
        if item.scenario_type
        == "prompt_injection_block"
    )

    assert (
        determine_outcome(scenario)
        is AcceptanceOutcome.ESCALATED
    )


def test_insufficient_evidence_abstains() -> None:
    scenario = next(
        item
        for item in scenarios()
        if item.scenario_type
        == "insufficient_evidence_abstention"
    )

    assert (
        determine_outcome(scenario)
        is AcceptanceOutcome.ABSTAINED
    )


def test_policy_forgery_is_rejected() -> None:
    scenario = next(
        item
        for item in scenarios()
        if item.scenario_type
        == "policy_forgery_rejection"
    )

    assert (
        determine_outcome(scenario)
        is AcceptanceOutcome.REJECTED
    )


def test_mutating_action_without_approval_escalates() -> None:
    scenario = next(
        item
        for item in scenarios()
        if item.scenario_type
        == "mutating_action_escalation"
    )

    assert (
        determine_outcome(scenario)
        is AcceptanceOutcome.ESCALATED
    )


def test_read_only_success_executes_runtime() -> None:
    scenario = next(
        item
        for item in scenarios()
        if item.scenario_id
        == "payments-authorized-success"
    )

    result = execute_acceptance_scenario(scenario)

    assert result.runtime_executed
    assert result.status is ScenarioStatus.PASS


def test_denied_scenario_does_not_execute_runtime() -> None:
    scenario = next(
        item
        for item in scenarios()
        if item.scenario_type
        == "cross_tenant_denial"
    )

    result = execute_acceptance_scenario(scenario)

    assert not result.runtime_executed


def test_stage_order_is_stable() -> None:
    result = execute_acceptance_scenario(
        scenarios()[0]
    )

    assert tuple(
        item.stage
        for item in result.stages
    ) == STAGE_ORDER


def test_all_stage_evidence_ids_are_present() -> None:
    results = execute_acceptance_suite(
        scenarios()
    )

    assert all(
        stage.evidence_id
        for result in results
        for stage in result.stages
    )


def test_acceptance_suite_passes() -> None:
    results = execute_acceptance_suite(
        scenarios()
    )

    assert len(results) == 12
    assert all(
        result.status is ScenarioStatus.PASS
        for result in results
    )


def test_no_scenario_performs_real_side_effect() -> None:
    results = execute_acceptance_suite(
        scenarios()
    )

    assert all(
        not result.real_side_effect_performed
        for result in results
    )


def test_metrics_are_one_hundred_percent() -> None:
    results = execute_acceptance_suite(
        scenarios()
    )

    metrics = calculate_acceptance_metrics(
        results,
        tuple(policy()["required_stages"]),
    )

    assert metrics.scenario_pass_rate_percentage == 100.0
    assert metrics.stage_coverage_percentage == 100.0
    assert (
        metrics.evidence_continuity_percentage
        == 100.0
    )


def test_empty_results_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="At least one",
    ):
        calculate_acceptance_metrics(
            (),
            tuple(policy()["required_stages"]),
        )


def test_valid_platform_is_accepted() -> None:
    results = execute_acceptance_suite(
        scenarios()
    )

    metrics = calculate_acceptance_metrics(
        results,
        tuple(policy()["required_stages"]),
    )

    decision, reasons = determine_platform_acceptance(
        metrics=metrics,
        policy=policy(),
        required_domains_present=True,
        required_scenario_types_present=True,
        real_side_effects_performed=False,
    )

    assert (
        decision
        is PlatformAcceptanceDecision
        .ACCEPTED_FOR_OPERATIONAL_READINESS
    )
    assert not reasons


def test_real_side_effect_blocks_acceptance() -> None:
    results = execute_acceptance_suite(
        scenarios()
    )

    metrics = calculate_acceptance_metrics(
        results,
        tuple(policy()["required_stages"]),
    )

    decision, reasons = determine_platform_acceptance(
        metrics=metrics,
        policy=policy(),
        required_domains_present=True,
        required_scenario_types_present=True,
        real_side_effects_performed=True,
    )

    assert (
        decision
        is PlatformAcceptanceDecision.BLOCKED
    )
    assert reasons
