"""Deterministic chaos injection and failure assessment."""

from __future__ import annotations

from incident_agent.resilience.contracts import (
    ChaosScenario,
    FailureAssessment,
    FailureImpact,
    FailureType,
)


def build_default_scenarios() -> tuple[ChaosScenario, ...]:
    """Return deterministic Phase 14 chaos scenarios."""

    return (
        ChaosScenario(
            scenario_id="chaos-provider-timeout",
            failure_type=FailureType.PROVIDER_TIMEOUT,
            target_component="genai-provider",
            affected_region=None,
            injected=True,
        ),
        ChaosScenario(
            scenario_id="chaos-retrieval-outage",
            failure_type=FailureType.RETRIEVAL_UNAVAILABLE,
            target_component="permission-aware-retrieval",
            affected_region=None,
            injected=True,
        ),
        ChaosScenario(
            scenario_id="chaos-policy-outage",
            failure_type=FailureType.POLICY_ENGINE_UNAVAILABLE,
            target_component="deterministic-policy-engine",
            affected_region=None,
            injected=True,
        ),
        ChaosScenario(
            scenario_id="chaos-runtime-saturation",
            failure_type=FailureType.RUNTIME_SATURATION,
            target_component="isolated-tool-runtime",
            affected_region=None,
            injected=True,
        ),
        ChaosScenario(
            scenario_id="chaos-region-west",
            failure_type=FailureType.REGIONAL_FAILURE,
            target_component="deployment-runtime",
            affected_region="us-west",
            injected=True,
        ),
        ChaosScenario(
            scenario_id="chaos-checkpoint-corruption",
            failure_type=FailureType.CHECKPOINT_CORRUPTION,
            target_component="workflow-checkpoint-store",
            affected_region=None,
            injected=True,
        ),
    )


def assess_failure(
    scenario: ChaosScenario,
) -> FailureAssessment:
    """Classify impact without expanding authority."""

    if scenario.failure_type is FailureType.PROVIDER_TIMEOUT:
        return FailureAssessment(
            failure_type=scenario.failure_type,
            impact=FailureImpact.DEGRADED,
            safe_to_continue=True,
            authority_expansion_detected=False,
            explanation=(
                "The workflow may abstain or use an approved "
                "fallback without expanding execution authority."
            ),
        )

    if (
        scenario.failure_type
        is FailureType.RETRIEVAL_UNAVAILABLE
    ):
        return FailureAssessment(
            failure_type=scenario.failure_type,
            impact=FailureImpact.CRITICAL,
            safe_to_continue=False,
            authority_expansion_detected=False,
            explanation=(
                "Evidence-grounded reasoning cannot continue "
                "without authorized retrieval."
            ),
        )

    if (
        scenario.failure_type
        is FailureType.POLICY_ENGINE_UNAVAILABLE
    ):
        return FailureAssessment(
            failure_type=scenario.failure_type,
            impact=FailureImpact.CRITICAL,
            safe_to_continue=False,
            authority_expansion_detected=False,
            explanation=(
                "Tool execution must stop when deterministic "
                "policy is unavailable."
            ),
        )

    if (
        scenario.failure_type
        is FailureType.RUNTIME_SATURATION
    ):
        return FailureAssessment(
            failure_type=scenario.failure_type,
            impact=FailureImpact.DEGRADED,
            safe_to_continue=False,
            authority_expansion_detected=False,
            explanation=(
                "New work must be rejected while existing "
                "authorized work drains safely."
            ),
        )

    if scenario.failure_type is FailureType.REGIONAL_FAILURE:
        return FailureAssessment(
            failure_type=scenario.failure_type,
            impact=FailureImpact.DISASTER,
            safe_to_continue=False,
            authority_expansion_detected=False,
            explanation=(
                "Regional service loss requires human-authorized "
                "failover."
            ),
        )

    return FailureAssessment(
        failure_type=scenario.failure_type,
        impact=FailureImpact.CRITICAL,
        safe_to_continue=False,
        authority_expansion_detected=False,
        explanation=(
            "Corrupted checkpoint evidence requires restore "
            "from a verified backup."
        ),
    )
