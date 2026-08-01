"""Governed progressive-delivery controller."""

from __future__ import annotations

from incident_agent.progressive_delivery.contracts import (
    GateStatus,
    PromotionApproval,
    PromotionDecision,
    PromotionEvaluation,
    ReleaseCandidate,
    ReleaseGate,
    RollbackRecord,
    TrafficState,
)
from incident_agent.progressive_delivery.loading import (
    canonical_sha256,
)


def promotion_evidence_sha256(
    candidate: ReleaseCandidate,
    gates: tuple[ReleaseGate, ...],
    from_percentage: int,
    to_percentage: int,
) -> str:
    return canonical_sha256(
        {
            "release_id": candidate.release_id,
            "candidate_version":
                candidate.candidate_version,
            "from_percentage": from_percentage,
            "to_percentage": to_percentage,
            "gates": [
                {
                    "gate_name": gate.gate_name,
                    "status": gate.status.value,
                    "evidence_reference":
                        gate.evidence_reference,
                }
                for gate in gates
            ],
        }
    )


def evaluate_promotion(
    candidate: ReleaseCandidate,
    gates: tuple[ReleaseGate, ...],
    from_percentage: int,
    to_percentage: int,
    valid_stages: tuple[int, ...],
    approval: PromotionApproval | None,
) -> PromotionEvaluation:
    if (
        from_percentage not in valid_stages
        or to_percentage not in valid_stages
        or to_percentage <= from_percentage
    ):
        return PromotionEvaluation(
            from_percentage=from_percentage,
            to_percentage=to_percentage,
            decision=PromotionDecision.PAUSE,
            gates=gates,
            reasons=("Invalid traffic progression.",),
            human_approval_required=True,
        )

    failed = tuple(
        gate.gate_name
        for gate in gates
        if gate.status is GateStatus.FAIL
    )

    if failed:
        return PromotionEvaluation(
            from_percentage=from_percentage,
            to_percentage=to_percentage,
            decision=PromotionDecision.ROLLBACK,
            gates=gates,
            reasons=tuple(
                f"Failed release gate: {name}"
                for name in failed
            ),
            human_approval_required=True,
        )

    expected_digest = promotion_evidence_sha256(
        candidate=candidate,
        gates=gates,
        from_percentage=from_percentage,
        to_percentage=to_percentage,
    )

    approval_valid = (
        approval is not None
        and approval.approved
        and approval.release_id
        == candidate.release_id
        and approval.from_percentage
        == from_percentage
        and approval.to_percentage
        == to_percentage
        and approval.evidence_sha256
        == expected_digest
    )

    if not approval_valid:
        return PromotionEvaluation(
            from_percentage=from_percentage,
            to_percentage=to_percentage,
            decision=PromotionDecision.REQUIRE_APPROVAL,
            gates=gates,
            reasons=(
                "Production traffic expansion requires an "
                "evidence-bound human approval.",
            ),
            human_approval_required=True,
        )

    return PromotionEvaluation(
        from_percentage=from_percentage,
        to_percentage=to_percentage,
        decision=PromotionDecision.ALLOW,
        gates=gates,
        reasons=("All gates and approval checks passed.",),
        human_approval_required=True,
    )


def apply_simulated_traffic_state(
    candidate: ReleaseCandidate,
    percentage: int,
) -> TrafficState:
    if not 0 <= percentage <= 100:
        raise ValueError(
            "Traffic percentage must be between zero and one hundred"
        )

    return TrafficState(
        release_id=candidate.release_id,
        candidate_version=candidate.candidate_version,
        previous_version=candidate.previous_version,
        candidate_percentage=percentage,
        previous_percentage=100 - percentage,
        real_traffic_shift_performed=False,
    )


def authorize_rollback(
    candidate: ReleaseCandidate,
    reason: str,
    authorized: bool,
) -> RollbackRecord:
    return RollbackRecord(
        release_id=candidate.release_id,
        from_version=candidate.candidate_version,
        restored_version=candidate.previous_version,
        reason=reason,
        authorized=authorized,
        completed=authorized,
        real_traffic_shift_performed=False,
    )
