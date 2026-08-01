"""Tests for Phase 15 progressive delivery."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from incident_agent.progressive_delivery.contracts import (
    GateStatus,
    PromotionApproval,
    PromotionDecision,
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
    canonical_sha256,
    load_progressive_delivery_policy,
    load_release_candidate,
)


ROOT = Path(".")
POLICY_PATH = Path(
    "config/progressive-delivery-policy.json"
)
CANDIDATE_PATH = Path(
    "release/phase-15-release-candidate.json"
)


def policy():
    return load_progressive_delivery_policy(
        POLICY_PATH
    )


def candidate():
    return load_release_candidate(
        CANDIDATE_PATH
    )


def gates():
    return evaluate_release_gates(
        root=ROOT,
        candidate=candidate(),
        maximum_error_budget_consumed=policy()[
            "maximum_error_budget_consumed"
        ],
    )


def approval(
    from_percentage: int,
    to_percentage: int,
):
    release = candidate()
    release_gates = gates()

    return PromotionApproval(
        approval_id="approval-test",
        release_id=release.release_id,
        from_percentage=from_percentage,
        to_percentage=to_percentage,
        approver_id="release-controller",
        approved=True,
        evidence_sha256=promotion_evidence_sha256(
            candidate=release,
            gates=release_gates,
            from_percentage=from_percentage,
            to_percentage=to_percentage,
        ),
    )


def test_policy_loads() -> None:
    assert (
        policy()["policy_version"]
        == "progressive-delivery-policy-v1"
    )


def test_automatic_progression_is_disabled() -> None:
    loaded = policy()

    assert not loaded[
        "automatic_production_progression_allowed"
    ]
    assert not loaded[
        "automatic_rollback_allowed"
    ]


def test_traffic_stages_are_fixed() -> None:
    assert policy()["traffic_stages"] == [
        0,
        5,
        25,
        50,
        100,
    ]


def test_candidate_requires_immutable_digest(
    tmp_path,
) -> None:
    import json

    payload = json.loads(
        CANDIDATE_PATH.read_text(
            encoding="utf-8"
        )
    )
    payload["image_digest"] = "latest"

    path = tmp_path / "candidate.json"
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="immutable",
    ):
        load_release_candidate(path)


def test_candidate_loads() -> None:
    release = candidate()

    assert release.candidate_version == "v15.0.0"
    assert release.previous_version == "v14.0.0"


def test_candidate_and_previous_versions_differ() -> None:
    release = candidate()

    assert (
        release.candidate_version
        != release.previous_version
    )


def test_release_evidence_digest_is_reproducible() -> None:
    payload = {"release": "test", "stage": 5}

    assert canonical_sha256(
        payload
    ) == canonical_sha256(payload)


def test_all_release_gates_pass() -> None:
    release_gates = gates()

    assert len(release_gates) == 5
    assert all(
        gate.status is GateStatus.PASS
        for gate in release_gates
    )


def test_promotion_without_approval_requires_approval() -> None:
    result = evaluate_promotion(
        candidate=candidate(),
        gates=gates(),
        from_percentage=0,
        to_percentage=5,
        valid_stages=tuple(
            policy()["traffic_stages"]
        ),
        approval=None,
    )

    assert (
        result.decision
        is PromotionDecision.REQUIRE_APPROVAL
    )


def test_approved_canary_is_allowed() -> None:
    result = evaluate_promotion(
        candidate=candidate(),
        gates=gates(),
        from_percentage=0,
        to_percentage=5,
        valid_stages=tuple(
            policy()["traffic_stages"]
        ),
        approval=approval(0, 5),
    )

    assert result.decision is PromotionDecision.ALLOW


def test_wrong_release_approval_is_rejected() -> None:
    invalid = replace(
        approval(0, 5),
        release_id="wrong-release",
    )

    result = evaluate_promotion(
        candidate=candidate(),
        gates=gates(),
        from_percentage=0,
        to_percentage=5,
        valid_stages=tuple(
            policy()["traffic_stages"]
        ),
        approval=invalid,
    )

    assert (
        result.decision
        is PromotionDecision.REQUIRE_APPROVAL
    )


def test_wrong_evidence_approval_is_rejected() -> None:
    invalid = replace(
        approval(0, 5),
        evidence_sha256="c" * 64,
    )

    result = evaluate_promotion(
        candidate=candidate(),
        gates=gates(),
        from_percentage=0,
        to_percentage=5,
        valid_stages=tuple(
            policy()["traffic_stages"]
        ),
        approval=invalid,
    )

    assert (
        result.decision
        is PromotionDecision.REQUIRE_APPROVAL
    )


def test_invalid_stage_is_paused() -> None:
    result = evaluate_promotion(
        candidate=candidate(),
        gates=gates(),
        from_percentage=5,
        to_percentage=33,
        valid_stages=tuple(
            policy()["traffic_stages"]
        ),
        approval=None,
    )

    assert result.decision is PromotionDecision.PAUSE


def test_reverse_progression_is_paused() -> None:
    result = evaluate_promotion(
        candidate=candidate(),
        gates=gates(),
        from_percentage=25,
        to_percentage=5,
        valid_stages=tuple(
            policy()["traffic_stages"]
        ),
        approval=None,
    )

    assert result.decision is PromotionDecision.PAUSE


def test_failed_gate_requires_rollback() -> None:
    failed = tuple(
        replace(
            gate,
            status=GateStatus.FAIL,
        )
        if gate.gate_name == "slo_health"
        else gate
        for gate in gates()
    )

    result = evaluate_promotion(
        candidate=candidate(),
        gates=failed,
        from_percentage=25,
        to_percentage=50,
        valid_stages=tuple(
            policy()["traffic_stages"]
        ),
        approval=None,
    )

    assert (
        result.decision
        is PromotionDecision.ROLLBACK
    )


def test_traffic_state_totals_one_hundred() -> None:
    state = apply_simulated_traffic_state(
        candidate(),
        25,
    )

    assert (
        state.candidate_percentage
        + state.previous_percentage
        == 100
    )


def test_simulated_state_shifts_no_real_traffic() -> None:
    state = apply_simulated_traffic_state(
        candidate(),
        50,
    )

    assert not state.real_traffic_shift_performed


def test_invalid_traffic_percentage_is_rejected() -> None:
    with pytest.raises(ValueError):
        apply_simulated_traffic_state(
            candidate(),
            101,
        )


def test_authorized_rollback_restores_previous() -> None:
    release = candidate()

    rollback = authorize_rollback(
        candidate=release,
        reason="SLO gate failed",
        authorized=True,
    )

    assert rollback.completed
    assert (
        rollback.restored_version
        == release.previous_version
    )


def test_rollback_performs_no_real_traffic_shift() -> None:
    rollback = authorize_rollback(
        candidate=candidate(),
        reason="Security gate failed",
        authorized=True,
    )

    assert not rollback.real_traffic_shift_performed
