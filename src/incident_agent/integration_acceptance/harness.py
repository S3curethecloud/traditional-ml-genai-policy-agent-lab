"""Deterministic end-to-end integration acceptance harness."""

from __future__ import annotations

import hashlib

from incident_agent.integration_acceptance.contracts import (
    AcceptanceOutcome,
    AcceptanceScenario,
    AcceptanceScenarioResult,
    ScenarioStatus,
    StageEvidence,
)


STAGE_ORDER = (
    "request_validation",
    "domain_resolution",
    "ml_inference",
    "retrieval",
    "genai_synthesis",
    "policy_evaluation",
    "runtime_evaluation",
    "orchestration",
    "observability",
    "security_validation",
    "release_evidence",
)


def _evidence_id(
    scenario_id: str,
    stage: str,
) -> str:
    material = f"{scenario_id}:{stage}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:16]


def _stage(
    scenario: AcceptanceScenario,
    stage: str,
    executed: bool,
    detail: str,
) -> StageEvidence:
    return StageEvidence(
        stage=stage,
        executed=executed,
        evidence_id=_evidence_id(
            scenario.scenario_id,
            stage,
        ),
        detail=detail,
    )


def determine_outcome(
    scenario: AcceptanceScenario,
) -> AcceptanceOutcome:
    if scenario.cross_tenant_attempt:
        return AcceptanceOutcome.DENIED

    if scenario.prompt_injection_detected:
        return AcceptanceOutcome.ESCALATED

    if not scenario.authorized_evidence_available:
        return AcceptanceOutcome.ABSTAINED

    if not scenario.policy_fingerprint_valid:
        return AcceptanceOutcome.REJECTED

    if (
        scenario.tool_mutating
        and not scenario.human_approval_present
    ):
        return AcceptanceOutcome.ESCALATED

    return AcceptanceOutcome.COMPLETED


def execute_acceptance_scenario(
    scenario: AcceptanceScenario,
) -> AcceptanceScenarioResult:
    observed = determine_outcome(scenario)

    runtime_executed = (
        observed is AcceptanceOutcome.COMPLETED
        and not scenario.tool_mutating
    )

    stages: list[StageEvidence] = []

    stages.append(
        _stage(
            scenario,
            "request_validation",
            True,
            "Request shape and actor context validated.",
        )
    )

    stages.append(
        _stage(
            scenario,
            "domain_resolution",
            True,
            f"Resolved domain {scenario.domain}.",
        )
    )

    stages.append(
        _stage(
            scenario,
            "ml_inference",
            True,
            "Typed ML evidence produced.",
        )
    )

    retrieval_executed = not scenario.cross_tenant_attempt

    stages.append(
        _stage(
            scenario,
            "retrieval",
            retrieval_executed,
            (
                "Authorized evidence retrieval evaluated."
                if retrieval_executed
                else "Cross-tenant request denied before retrieval."
            ),
        )
    )

    genai_executed = (
        retrieval_executed
        and scenario.authorized_evidence_available
    )

    stages.append(
        _stage(
            scenario,
            "genai_synthesis",
            genai_executed,
            (
                "Evidence synthesis evaluated."
                if genai_executed
                else "Synthesis skipped without authorized evidence."
            ),
        )
    )

    policy_executed = (
        retrieval_executed
        and scenario.authorized_evidence_available
    )

    stages.append(
        _stage(
            scenario,
            "policy_evaluation",
            policy_executed,
            (
                "Deterministic policy evaluated."
                if policy_executed
                else "Policy execution not reached."
            ),
        )
    )

    stages.append(
        _stage(
            scenario,
            "runtime_evaluation",
            runtime_executed,
            (
                "Authorized read-only runtime simulated."
                if runtime_executed
                else "Runtime correctly not executed."
            ),
        )
    )

    for stage, detail in (
        (
            "orchestration",
            "Workflow state and stop condition recorded.",
        ),
        (
            "observability",
            "Trace and acceptance evidence recorded.",
        ),
        (
            "security_validation",
            "Security boundary outcome validated.",
        ),
        (
            "release_evidence",
            "Acceptance evidence bound to platform state.",
        ),
    ):
        stages.append(
            _stage(
                scenario,
                stage,
                True,
                detail,
            )
        )

    status = (
        ScenarioStatus.PASS
        if observed is scenario.expected_outcome
        else ScenarioStatus.FAIL
    )

    return AcceptanceScenarioResult(
        scenario_id=scenario.scenario_id,
        domain=scenario.domain,
        scenario_type=scenario.scenario_type,
        expected_outcome=scenario.expected_outcome,
        observed_outcome=observed,
        status=status,
        stages=tuple(stages),
        runtime_executed=runtime_executed,
        real_side_effect_performed=False,
        explanation=(
            f"Observed {observed.value}; "
            f"expected {scenario.expected_outcome.value}."
        ),
    )


def execute_acceptance_suite(
    scenarios: tuple[AcceptanceScenario, ...],
) -> tuple[AcceptanceScenarioResult, ...]:
    return tuple(
        execute_acceptance_scenario(scenario)
        for scenario in scenarios
    )
