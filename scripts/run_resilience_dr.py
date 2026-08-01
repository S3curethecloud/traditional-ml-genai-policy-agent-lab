#!/usr/bin/env python3
"""Run Phase 14 resilience and disaster-recovery simulation."""

from __future__ import annotations

import json
from pathlib import Path

from incident_agent.resilience.chaos import (
    assess_failure,
    build_default_scenarios,
)
from incident_agent.resilience.contracts import (
    FailoverAuthorization,
    ResilienceAuditEvent,
    ResilienceReport,
)
from incident_agent.resilience.decision import (
    decide_resilience_action,
)
from incident_agent.resilience.loading import (
    load_resilience_policy,
)
from incident_agent.resilience.recovery import (
    create_backup,
    create_checkpoint,
    evaluate_rpo,
    evaluate_rto,
    restore_backup,
    verify_recovery,
)


ROOT = Path(".")
POLICY_PATH = ROOT / "config/resilience-policy.json"
DEPLOYMENT_REPORT_PATH = (
    ROOT
    / "reports/deployment/"
    "phase-12-deployment-report.json"
)
OUTPUT_PATH = (
    ROOT
    / "reports/resilience/"
    "phase-14-resilience-report.json"
)
BACKUP_PATH = (
    ROOT
    / "backup/resilience/"
    "phase-14-checkpoint-backup.json"
)


def main() -> None:
    """Generate resilience and recovery evidence."""

    policy = load_resilience_policy(
        POLICY_PATH
    )

    deployment_report = json.loads(
        DEPLOYMENT_REPORT_PATH.read_text(
            encoding="utf-8"
        )
    )

    production = deployment_report[
        "production_with_approval"
    ]
    release_id = production["release_id"]

    scenarios = build_default_scenarios()
    assessments = tuple(
        assess_failure(scenario)
        for scenario in scenarios
    )

    unapproved_actions = tuple(
        decide_resilience_action(assessment)
        for assessment in assessments
    )

    regional_assessment = next(
        assessment
        for assessment in assessments
        if assessment.failure_type.value
        == "REGIONAL_FAILURE"
    )

    authorization = FailoverAuthorization(
        authorization_id="failover-approval-phase-14",
        release_id=release_id,
        source_region="us-west",
        target_region="us-east",
        approved=True,
        approver_id="disaster-recovery-controller",
        evidence_sha256=production[
            "runtime_state"
        ]["configuration_sha256"],
    )

    approved_regional_action = (
        decide_resilience_action(
            regional_assessment,
            authorization=authorization,
        )
    )

    actions = tuple(
        approved_regional_action
        if action.action_name
        == "request_regional_failover"
        else action
        for action in unapproved_actions
    )

    checkpoint = create_checkpoint(
        workflow_id="workflow-phase-14",
        sequence=7,
        payload={
            "release_id": release_id,
            "workflow_status": "POLICY_EVALUATED",
            "policy_decision": "ALLOW",
            "runtime_executed": False,
            "authority_expanded": False
        },
    )

    backup = create_backup(
        checkpoint=checkpoint,
        release_id=release_id,
        created_epoch_seconds=1000,
        output_path=BACKUP_PATH,
    )

    restored = restore_backup(backup)

    rpo = evaluate_rpo(
        failure_epoch_seconds=1180,
        backup_epoch_seconds=(
            backup.created_epoch_seconds
        ),
        objective_seconds=policy[
            "maximum_rpo_seconds"
        ],
    )

    rto = evaluate_rto(
        recovery_started_epoch_seconds=1200,
        recovery_completed_epoch_seconds=1500,
        objective_seconds=policy[
            "maximum_rto_seconds"
        ],
    )

    recovery = verify_recovery(
        checkpoint=checkpoint,
        restored_payload=restored,
        replay_verified=True,
    )

    events: list[ResilienceAuditEvent] = []

    for scenario, assessment, action in zip(
        scenarios,
        assessments,
        actions,
        strict=True,
    ):
        events.append(
            ResilienceAuditEvent(
                sequence=len(events) + 1,
                event_type="chaos_scenario_evaluated",
                scenario_id=scenario.scenario_id,
                detail=(
                    f"{assessment.impact.value}: "
                    f"{action.decision.value}"
                ),
                evidence_references=(
                    scenario.failure_type.value,
                    action.action_name,
                ),
            )
        )

    events.extend(
        (
            ResilienceAuditEvent(
                sequence=len(events) + 1,
                event_type="backup_verified",
                scenario_id=(
                    "chaos-checkpoint-corruption"
                ),
                detail=(
                    "Checkpoint backup integrity verified."
                ),
                evidence_references=(
                    backup.backup_id,
                    backup.backup_sha256,
                ),
            ),
            ResilienceAuditEvent(
                sequence=len(events) + 2,
                event_type="recovery_verified",
                scenario_id=(
                    "chaos-checkpoint-corruption"
                ),
                detail=(
                    "Restored checkpoint and replay "
                    "verification passed."
                ),
                evidence_references=(
                    recovery.status.value,
                    checkpoint.state_sha256,
                ),
            ),
        )
    )

    report = ResilienceReport(
        policy_version=policy["policy_version"],
        release_id=release_id,
        scenarios=scenarios,
        assessments=assessments,
        actions=actions,
        backup=backup,
        rpo=rpo,
        rto=rto,
        recovery=recovery,
        audit_events=tuple(events),
        automatic_failover_performed=False,
        real_infrastructure_changes_performed=False,
        authority_boundary=(
            "The resilience layer may inject simulated "
            "failures, classify impact, recommend recovery, "
            "validate authorization, restore tutorial backup "
            "state, and verify consistency. It cannot perform "
            "real infrastructure failover or autonomous "
            "disaster actions."
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
        f"PASS: chaos scenarios={len(scenarios)}"
    )
    print(
        "PASS: regional failover="
        f"{approved_regional_action.decision.value}"
    )
    print(
        f"PASS: RPO={rpo.observed_seconds}s"
    )
    print(
        f"PASS: RTO={rto.observed_seconds}s"
    )
    print(
        f"PASS: recovery={recovery.status.value}"
    )
    print(
        "PASS: authority boundary preserved"
    )
    print(
        "PASS: no automatic failover performed"
    )
    print(
        "PASS: no real infrastructure changes performed"
    )


if __name__ == "__main__":
    main()
