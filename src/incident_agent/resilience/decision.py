"""Governed resilience and failover decisions."""

from __future__ import annotations

from incident_agent.resilience.contracts import (
    FailoverAuthorization,
    FailureAssessment,
    FailureType,
    ResilienceAction,
    ResilienceDecision,
)


def decide_resilience_action(
    assessment: FailureAssessment,
    authorization: FailoverAuthorization | None = None,
) -> ResilienceAction:
    """Return a resilience action without executing infrastructure."""

    if assessment.failure_type is FailureType.PROVIDER_TIMEOUT:
        return ResilienceAction(
            decision=ResilienceDecision.CONTINUE_DEGRADED,
            action_name="abstain_or_use_approved_fallback",
            human_authorization_required=False,
            automatic_execution_allowed=False,
            explanation=(
                "The platform may return a controlled degraded "
                "response but may not broaden model or tool access."
            ),
        )

    if (
        assessment.failure_type
        is FailureType.REGIONAL_FAILURE
    ):
        if authorization is None or not authorization.approved:
            return ResilienceAction(
                decision=(
                    ResilienceDecision.REQUIRE_FAILOVER_APPROVAL
                ),
                action_name="request_regional_failover",
                human_authorization_required=True,
                automatic_execution_allowed=False,
                explanation=(
                    "Regional failover requires explicit human "
                    "authorization."
                ),
            )

        return ResilienceAction(
            decision=ResilienceDecision.FAILOVER_ALLOWED,
            action_name="simulate_regional_failover",
            human_authorization_required=True,
            automatic_execution_allowed=False,
            explanation=(
                "Authorization permits only simulated failover "
                "in this tutorial."
            ),
        )

    if (
        assessment.failure_type
        is FailureType.CHECKPOINT_CORRUPTION
    ):
        return ResilienceAction(
            decision=ResilienceDecision.RESTORE_REQUIRED,
            action_name="restore_verified_checkpoint",
            human_authorization_required=True,
            automatic_execution_allowed=False,
            explanation=(
                "Recovery must use verified backup evidence."
            ),
        )

    return ResilienceAction(
        decision=ResilienceDecision.STOP_SAFELY,
        action_name="stop_or_reject_new_work",
        human_authorization_required=False,
        automatic_execution_allowed=False,
        explanation=(
            "The platform must fail closed and preserve its "
            "authority boundary."
        ),
    )
