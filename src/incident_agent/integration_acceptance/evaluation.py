"""Evaluate Phase 18 acceptance metrics and decision."""

from __future__ import annotations

from incident_agent.integration_acceptance.contracts import (
    AcceptanceMetrics,
    AcceptanceScenarioResult,
    PlatformAcceptanceDecision,
    ScenarioStatus,
)


def calculate_acceptance_metrics(
    results: tuple[AcceptanceScenarioResult, ...],
    required_stages: tuple[str, ...],
) -> AcceptanceMetrics:
    if not results:
        raise ValueError(
            "At least one acceptance result is required"
        )

    passed = sum(
        result.status is ScenarioStatus.PASS
        for result in results
    )

    covered_stages = {
        stage.stage
        for result in results
        for stage in result.stages
    }

    expected_evidence_count = sum(
        len(result.stages)
        for result in results
    )
    actual_evidence_count = sum(
        bool(stage.evidence_id)
        for result in results
        for stage in result.stages
    )

    return AcceptanceMetrics(
        total_scenarios=len(results),
        passed_scenarios=passed,
        scenario_pass_rate_percentage=round(
            passed / len(results) * 100.0,
            4,
        ),
        required_stage_count=len(required_stages),
        covered_stage_count=len(
            set(required_stages) & covered_stages
        ),
        stage_coverage_percentage=round(
            len(set(required_stages) & covered_stages)
            / len(required_stages)
            * 100.0,
            4,
        ),
        evidence_continuity_percentage=round(
            actual_evidence_count
            / expected_evidence_count
            * 100.0,
            4,
        ),
    )


def determine_platform_acceptance(
    metrics: AcceptanceMetrics,
    policy: dict,
    required_domains_present: bool,
    required_scenario_types_present: bool,
    real_side_effects_performed: bool,
) -> tuple[
    PlatformAcceptanceDecision,
    tuple[str, ...],
]:
    reasons: list[str] = []

    if (
        metrics.scenario_pass_rate_percentage
        < policy[
            "minimum_scenario_pass_rate_percentage"
        ]
    ):
        reasons.append(
            "Scenario pass rate is below policy minimum."
        )

    if (
        metrics.stage_coverage_percentage
        < policy["minimum_stage_coverage_percentage"]
    ):
        reasons.append(
            "Stage coverage is below policy minimum."
        )

    if (
        metrics.evidence_continuity_percentage
        < policy[
            "minimum_evidence_continuity_percentage"
        ]
    ):
        reasons.append(
            "Evidence continuity is below policy minimum."
        )

    if not required_domains_present:
        reasons.append(
            "Required domains are not fully represented."
        )

    if not required_scenario_types_present:
        reasons.append(
            "Required scenario types are not fully represented."
        )

    if real_side_effects_performed:
        reasons.append(
            "Acceptance harness performed a real side effect."
        )

    decision = (
        PlatformAcceptanceDecision
        .ACCEPTED_FOR_OPERATIONAL_READINESS
        if not reasons
        else PlatformAcceptanceDecision.BLOCKED
    )

    return decision, tuple(reasons)
