#!/usr/bin/env python3
"""Run Phase 15 progressive-delivery simulation."""

from __future__ import annotations

import json
from pathlib import Path

from incident_agent.progressive_delivery.contracts import (
    GateStatus,
    PromotionApproval,
    ReleaseAuditEvent,
    ReleaseStatus,
    ProgressiveDeliveryReport,
)
from incident_agent.progressive_delivery.controller import (
    apply_simulated_traffic_state,
    authorize_rollback,
    evaluate_promotion,
    promotion_evidence_sha256,
)
from incident_agent.progressive_delivery.gates import (
    evaluate_release_gates,
)
from incident_agent.progressive_delivery.loading import (
    load_progressive_delivery_policy,
    load_release_candidate,
)


ROOT = Path(".")
POLICY_PATH = ROOT / (
    "config/progressive-delivery-policy.json"
)
CANDIDATE_PATH = ROOT / (
    "release/phase-15-release-candidate.json"
)
OUTPUT_PATH = ROOT / (
    "reports/progressive-delivery/"
    "phase-15-progressive-delivery-report.json"
)


def approved_promotion(
    candidate,
    gates,
    from_percentage: int,
    to_percentage: int,
) -> PromotionApproval:
    return PromotionApproval(
        approval_id=(
            f"promotion-{from_percentage}-"
            f"{to_percentage}"
        ),
        release_id=candidate.release_id,
        from_percentage=from_percentage,
        to_percentage=to_percentage,
        approver_id="production-release-controller",
        approved=True,
        evidence_sha256=promotion_evidence_sha256(
            candidate=candidate,
            gates=gates,
            from_percentage=from_percentage,
            to_percentage=to_percentage,
        ),
    )


def main() -> None:
    policy = load_progressive_delivery_policy(
        POLICY_PATH
    )
    candidate = load_release_candidate(
        CANDIDATE_PATH
    )

    gates = evaluate_release_gates(
        root=ROOT,
        candidate=candidate,
        maximum_error_budget_consumed=policy[
            "maximum_error_budget_consumed"
        ],
    )

    stages = tuple(policy["traffic_stages"])
    evaluations = []
    traffic_states = [
        apply_simulated_traffic_state(
            candidate,
            0,
        )
    ]
    events = [
        ReleaseAuditEvent(
            sequence=1,
            event_type="release_candidate_registered",
            release_id=candidate.release_id,
            detail=(
                f"Candidate "
                f"{candidate.candidate_version} registered."
            ),
            evidence_references=(
                candidate.image_digest,
                candidate.source_revision,
            ),
        )
    ]

    for from_percentage, to_percentage in zip(
        stages,
        stages[1:],
    ):
        unapproved = evaluate_promotion(
            candidate=candidate,
            gates=gates,
            from_percentage=from_percentage,
            to_percentage=to_percentage,
            valid_stages=stages,
            approval=None,
        )

        if (
            unapproved.decision.value
            != "REQUIRE_APPROVAL"
        ):
            raise RuntimeError(
                "Expected promotion approval requirement"
            )

        approval = approved_promotion(
            candidate=candidate,
            gates=gates,
            from_percentage=from_percentage,
            to_percentage=to_percentage,
        )

        evaluation = evaluate_promotion(
            candidate=candidate,
            gates=gates,
            from_percentage=from_percentage,
            to_percentage=to_percentage,
            valid_stages=stages,
            approval=approval,
        )
        evaluations.append(evaluation)

        if evaluation.decision.value != "ALLOW":
            raise RuntimeError(
                "Expected approved promotion to pass"
            )

        traffic_states.append(
            apply_simulated_traffic_state(
                candidate,
                to_percentage,
            )
        )

        events.append(
            ReleaseAuditEvent(
                sequence=len(events) + 1,
                event_type="traffic_stage_approved",
                release_id=candidate.release_id,
                detail=(
                    f"Simulated candidate traffic advanced "
                    f"from {from_percentage}% "
                    f"to {to_percentage}%."
                ),
                evidence_references=(
                    approval.approval_id,
                    approval.evidence_sha256,
                ),
            )
        )

    failed_gates = tuple(
        gate
        if gate.gate_name != "slo_health"
        else type(gate)(
            gate_name=gate.gate_name,
            status=GateStatus.FAIL,
            explanation=(
                "Injected SLO failure for rollback test."
            ),
            evidence_reference=(
                gate.evidence_reference
            ),
        )
        for gate in gates
    )

    rollback_evaluation = evaluate_promotion(
        candidate=candidate,
        gates=failed_gates,
        from_percentage=50,
        to_percentage=100,
        valid_stages=stages,
        approval=None,
    )

    rollback = authorize_rollback(
        candidate=candidate,
        reason=rollback_evaluation.reasons[0],
        authorized=True,
    )

    events.append(
        ReleaseAuditEvent(
            sequence=len(events) + 1,
            event_type="rollback_authorized",
            release_id=candidate.release_id,
            detail=(
                f"Previous version "
                f"{candidate.previous_version} restored "
                "in simulation."
            ),
            evidence_references=(
                rollback.reason,
            ),
        )
    )

    report = ProgressiveDeliveryReport(
        policy_version=policy["policy_version"],
        release_candidate=candidate,
        evaluations=tuple(evaluations),
        traffic_states=tuple(traffic_states),
        rollback=rollback,
        audit_events=tuple(events),
        final_status=ReleaseStatus.ROLLED_BACK,
        automatic_progression_performed=False,
        automatic_rollback_performed=False,
        real_traffic_shift_performed=False,
        authority_boundary=(
            "The progressive-delivery controller may "
            "evaluate release evidence, require approval, "
            "simulate traffic states, pause progression, "
            "recommend rollback, and record evidence. "
            "It cannot shift real traffic or authorize "
            "its own production expansion."
        ),
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    OUTPUT_PATH.write_text(
        json.dumps(
            report.to_dict(),
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"PASS: release candidate="
        f"{candidate.candidate_version}"
    )
    print(
        f"PASS: release gates="
        f"{sum(g.status is GateStatus.PASS for g in gates)}"
        f"/{len(gates)}"
    )
    print(
        f"PASS: approved stages="
        f"{len(evaluations)}"
    )
    print(
        "PASS: final simulated candidate traffic=100%"
    )
    print(
        "PASS: failed gate triggered rollback decision"
    )
    print(
        f"PASS: restored version="
        f"{rollback.restored_version}"
    )
    print(
        "PASS: no automatic progression performed"
    )
    print(
        "PASS: no real traffic shift performed"
    )


if __name__ == "__main__":
    main()
