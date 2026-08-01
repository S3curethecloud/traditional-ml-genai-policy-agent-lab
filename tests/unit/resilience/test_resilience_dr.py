"""Tests for Phase 14 resilience and disaster recovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from incident_agent.resilience.chaos import (
    assess_failure,
    build_default_scenarios,
)
from incident_agent.resilience.contracts import (
    FailoverAuthorization,
    FailureImpact,
    FailureType,
    RecoveryStatus,
    ResilienceDecision,
)
from incident_agent.resilience.decision import (
    decide_resilience_action,
)
from incident_agent.resilience.loading import (
    load_resilience_policy,
    policy_sha256,
)
from incident_agent.resilience.recovery import (
    canonical_sha256,
    create_backup,
    create_checkpoint,
    evaluate_rpo,
    evaluate_rto,
    restore_backup,
    verify_recovery,
)


POLICY_PATH = Path(
    "config/resilience-policy.json"
)


def policy():
    return load_resilience_policy(
        POLICY_PATH
    )


def scenario(
    failure_type: FailureType,
):
    return next(
        item
        for item in build_default_scenarios()
        if item.failure_type is failure_type
    )


def test_resilience_policy_loads() -> None:
    assert (
        policy()["policy_version"]
        == "resilience-policy-v1"
    )


def test_automatic_failover_is_disabled() -> None:
    loaded = policy()

    assert not loaded[
        "automatic_failover_allowed"
    ]
    assert not loaded[
        "automatic_disaster_declaration_allowed"
    ]


def test_policy_digest_is_reproducible() -> None:
    loaded = policy()

    assert policy_sha256(loaded) == policy_sha256(
        loaded
    )


def test_six_unique_scenarios_exist() -> None:
    scenarios = build_default_scenarios()

    assert len(scenarios) == 6
    assert len(
        {item.scenario_id for item in scenarios}
    ) == 6


def test_provider_timeout_is_degraded() -> None:
    result = assess_failure(
        scenario(FailureType.PROVIDER_TIMEOUT)
    )

    assert result.impact is FailureImpact.DEGRADED
    assert result.safe_to_continue


def test_retrieval_outage_stops_safely() -> None:
    result = decide_resilience_action(
        assess_failure(
            scenario(
                FailureType.RETRIEVAL_UNAVAILABLE
            )
        )
    )

    assert (
        result.decision
        is ResilienceDecision.STOP_SAFELY
    )


def test_policy_outage_stops_safely() -> None:
    result = decide_resilience_action(
        assess_failure(
            scenario(
                FailureType.POLICY_ENGINE_UNAVAILABLE
            )
        )
    )

    assert (
        result.decision
        is ResilienceDecision.STOP_SAFELY
    )


def test_runtime_saturation_stops_new_work() -> None:
    result = decide_resilience_action(
        assess_failure(
            scenario(
                FailureType.RUNTIME_SATURATION
            )
        )
    )

    assert (
        result.action_name
        == "stop_or_reject_new_work"
    )


def test_regional_failure_requires_approval() -> None:
    result = decide_resilience_action(
        assess_failure(
            scenario(FailureType.REGIONAL_FAILURE)
        )
    )

    assert (
        result.decision
        is ResilienceDecision.REQUIRE_FAILOVER_APPROVAL
    )


def test_approved_regional_failover_is_allowed() -> None:
    authorization = FailoverAuthorization(
        authorization_id="auth-test",
        release_id="release-test",
        source_region="us-west",
        target_region="us-east",
        approved=True,
        approver_id="dr-controller",
        evidence_sha256="a" * 64,
    )

    result = decide_resilience_action(
        assess_failure(
            scenario(FailureType.REGIONAL_FAILURE)
        ),
        authorization=authorization,
    )

    assert (
        result.decision
        is ResilienceDecision.FAILOVER_ALLOWED
    )
    assert not result.automatic_execution_allowed


def test_checkpoint_corruption_requires_restore() -> None:
    result = decide_resilience_action(
        assess_failure(
            scenario(
                FailureType.CHECKPOINT_CORRUPTION
            )
        )
    )

    assert (
        result.decision
        is ResilienceDecision.RESTORE_REQUIRED
    )


def test_checkpoint_digest_is_reproducible() -> None:
    payload = {
        "policy_decision": "ALLOW",
        "authority_expanded": False,
    }

    assert canonical_sha256(
        payload
    ) == canonical_sha256(payload)


def test_backup_restores_verified_state(
    tmp_path,
) -> None:
    checkpoint = create_checkpoint(
        workflow_id="workflow-test",
        sequence=3,
        payload={
            "policy_decision": "ALLOW",
            "authority_expanded": False,
        },
    )

    backup = create_backup(
        checkpoint=checkpoint,
        release_id="release-test",
        created_epoch_seconds=100,
        output_path=tmp_path / "backup.json",
    )

    restored = restore_backup(backup)

    assert (
        restored["state_sha256"]
        == checkpoint.state_sha256
    )


def test_tampered_backup_is_rejected(
    tmp_path,
) -> None:
    checkpoint = create_checkpoint(
        workflow_id="workflow-test",
        sequence=3,
        payload={
            "policy_decision": "ALLOW",
            "authority_expanded": False,
        },
    )

    path = tmp_path / "backup.json"

    backup = create_backup(
        checkpoint=checkpoint,
        release_id="release-test",
        created_epoch_seconds=100,
        output_path=path,
    )

    path.write_text(
        '{"tampered": true}\n',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="integrity",
    ):
        restore_backup(backup)


def test_rpo_passes_within_objective() -> None:
    result = evaluate_rpo(
        failure_epoch_seconds=300,
        backup_epoch_seconds=100,
        objective_seconds=300,
    )

    assert result.passed
    assert result.observed_seconds == 200


def test_rpo_fails_outside_objective() -> None:
    result = evaluate_rpo(
        failure_epoch_seconds=500,
        backup_epoch_seconds=100,
        objective_seconds=300,
    )

    assert not result.passed


def test_rto_passes_within_objective() -> None:
    result = evaluate_rto(
        recovery_started_epoch_seconds=100,
        recovery_completed_epoch_seconds=500,
        objective_seconds=600,
    )

    assert result.passed


def test_recovery_verifies_consistency() -> None:
    checkpoint = create_checkpoint(
        workflow_id="workflow-test",
        sequence=3,
        payload={
            "policy_decision": "ALLOW",
            "authority_expanded": False,
        },
    )

    restored = {
        "state_sha256": checkpoint.state_sha256,
        "payload": checkpoint.payload,
    }

    result = verify_recovery(
        checkpoint=checkpoint,
        restored_payload=restored,
        replay_verified=True,
    )

    assert result.status is RecoveryStatus.RECOVERED
    assert result.state_consistent
    assert result.replay_verified
    assert result.authority_boundary_preserved


def test_recovery_fails_when_replay_fails() -> None:
    checkpoint = create_checkpoint(
        workflow_id="workflow-test",
        sequence=3,
        payload={
            "policy_decision": "ALLOW",
            "authority_expanded": False,
        },
    )

    restored = {
        "state_sha256": checkpoint.state_sha256,
        "payload": checkpoint.payload,
    }

    result = verify_recovery(
        checkpoint=checkpoint,
        restored_payload=restored,
        replay_verified=False,
    )

    assert result.status is RecoveryStatus.FAILED


def test_failures_never_expand_authority() -> None:
    assessments = tuple(
        assess_failure(item)
        for item in build_default_scenarios()
    )

    assert all(
        not item.authority_expansion_detected
        for item in assessments
    )
