"""Evaluate operational readiness and production handoff."""

from __future__ import annotations

from incident_agent.operational_readiness.contracts import (
    AccessControl,
    HandoffCheck,
    OwnershipAssignment,
    ReadinessDecision,
    ReadinessMetrics,
    Runbook,
    SupportTier,
)


def _percentage(
    numerator: int,
    denominator: int,
) -> float:
    if denominator <= 0:
        raise ValueError(
            "Coverage denominator must be greater than zero"
        )

    return round(
        numerator / denominator * 100.0,
        4,
    )


def calculate_readiness_metrics(
    policy: dict,
    assignments: tuple[OwnershipAssignment, ...],
    runbooks: tuple[Runbook, ...],
    checks: tuple[HandoffCheck, ...],
) -> ReadinessMetrics:
    required_checks = tuple(
        check
        for check in checks
        if check.required
    )
    passed_checks = tuple(
        check
        for check in required_checks
        if check.passed
    )

    required_capabilities = set(
        policy["required_operational_capabilities"]
    )
    covered_capabilities = {
        item.capability
        for item in assignments
    }

    required_runbooks = set(
        policy["required_runbooks"]
    )
    covered_runbooks = {
        item.runbook_id
        for item in runbooks
    }

    required_evidence = set(
        policy["required_evidence_artifacts"]
    )
    covered_evidence = {
        check.evidence_id
        for check in checks
        if check.passed
    }

    return ReadinessMetrics(
        total_required_checks=len(required_checks),
        passed_required_checks=len(passed_checks),
        check_pass_rate_percentage=_percentage(
            len(passed_checks),
            len(required_checks),
        ),
        required_owner_count=len(required_capabilities),
        covered_owner_count=len(
            required_capabilities & covered_capabilities
        ),
        owner_coverage_percentage=_percentage(
            len(required_capabilities & covered_capabilities),
            len(required_capabilities),
        ),
        required_runbook_count=len(required_runbooks),
        covered_runbook_count=len(
            required_runbooks & covered_runbooks
        ),
        runbook_coverage_percentage=_percentage(
            len(required_runbooks & covered_runbooks),
            len(required_runbooks),
        ),
        required_evidence_count=len(required_evidence),
        covered_evidence_count=len(
            required_evidence & covered_evidence
        ),
        evidence_coverage_percentage=_percentage(
            len(required_evidence & covered_evidence),
            len(required_evidence),
        ),
    )


def determine_readiness_decision(
    policy: dict,
    metrics: ReadinessMetrics,
    support_tiers: tuple[SupportTier, ...],
    access_controls: tuple[AccessControl, ...],
    ownership_flags: dict[str, bool],
    access_flags: dict[str, bool],
) -> tuple[ReadinessDecision, tuple[str, ...]]:
    reasons: list[str] = []

    threshold_pairs = (
        (
            metrics.check_pass_rate_percentage,
            policy[
                "minimum_check_pass_rate_percentage"
            ],
            "Required handoff checks are incomplete.",
        ),
        (
            metrics.owner_coverage_percentage,
            policy[
                "minimum_owner_coverage_percentage"
            ],
            "Operational ownership coverage is incomplete.",
        ),
        (
            metrics.runbook_coverage_percentage,
            policy[
                "minimum_runbook_coverage_percentage"
            ],
            "Runbook coverage is incomplete.",
        ),
        (
            metrics.evidence_coverage_percentage,
            policy[
                "minimum_evidence_coverage_percentage"
            ],
            "Evidence coverage is incomplete.",
        ),
    )

    for actual, minimum, reason in threshold_pairs:
        if actual < minimum:
            reasons.append(reason)

    required_tiers = set(
        policy["required_support_tiers"]
    )
    actual_tiers = {
        item.tier
        for item in support_tiers
    }

    if not required_tiers <= actual_tiers:
        reasons.append(
            "Required support tiers are incomplete."
        )

    if any(
        tier.may_execute_production_tools
        for tier in support_tiers
    ):
        reasons.append(
            "Support model grants production tool authority."
        )

    required_controls = set(
        policy["required_access_controls"]
    )
    implemented_controls = {
        item.control_id
        for item in access_controls
        if item.implemented
    }

    if not required_controls <= implemented_controls:
        reasons.append(
            "Required access controls are incomplete."
        )

    if ownership_flags["automatic_owner_assignment"]:
        reasons.append(
            "Automatic owner assignment was enabled."
        )

    if ownership_flags["real_people_assigned"]:
        reasons.append(
            "The readiness harness assigned real people."
        )

    if ownership_flags[
        "production_authority_transferred"
    ]:
        reasons.append(
            "Production authority was transferred."
        )

    if any(access_flags.values()):
        reasons.append(
            "The readiness harness changed access state."
        )

    decision = (
        ReadinessDecision
        .READY_FOR_CONTROLLED_RELEASE_CLOSURE
        if not reasons
        else ReadinessDecision.BLOCKED
    )

    return decision, tuple(reasons)
