#!/usr/bin/env python3
"""Run Phase 19 operational-readiness evaluation."""

from __future__ import annotations

import json
from pathlib import Path

from incident_agent.operational_readiness.contracts import (
    OperationalReadinessReport,
)
from incident_agent.operational_readiness.evaluation import (
    calculate_readiness_metrics,
    determine_readiness_decision,
)
from incident_agent.operational_readiness.loading import (
    load_access_profile,
    load_handoff_checklist,
    load_ownership_model,
    load_readiness_policy,
    load_runbook_catalog,
)


ROOT = Path(".")
POLICY_PATH = (
    ROOT
    / "config/operational-readiness/"
    "operational-readiness-policy.json"
)
OWNERSHIP_PATH = (
    ROOT
    / "operations/handoff/ownership-model.json"
)
RUNBOOK_PATH = (
    ROOT
    / "operations/runbooks/runbook-catalog.json"
)
ACCESS_PATH = (
    ROOT
    / "operations/handoff/access-readiness.json"
)
CHECKLIST_PATH = (
    ROOT
    / "operations/handoff/"
    "production-handoff-checklist.json"
)
OUTPUT_PATH = (
    ROOT
    / "reports/operational-readiness/"
    "phase-19-operational-readiness-report.json"
)


def main() -> None:
    policy = load_readiness_policy(POLICY_PATH)

    (
        ownership_model_id,
        assignments,
        support_tiers,
        ownership_flags,
    ) = load_ownership_model(OWNERSHIP_PATH)

    runbook_catalog_id, runbooks = (
        load_runbook_catalog(RUNBOOK_PATH)
    )

    (
        _access_profile_id,
        access_controls,
        access_flags,
    ) = load_access_profile(ACCESS_PATH)

    checklist_id, checks = load_handoff_checklist(
        CHECKLIST_PATH
    )

    metrics = calculate_readiness_metrics(
        policy=policy,
        assignments=assignments,
        runbooks=runbooks,
        checks=checks,
    )

    decision, reasons = determine_readiness_decision(
        policy=policy,
        metrics=metrics,
        support_tiers=support_tiers,
        access_controls=access_controls,
        ownership_flags=ownership_flags,
        access_flags=access_flags,
    )

    report = OperationalReadinessReport(
        policy_version=policy["policy_version"],
        platform_contract_version=policy[
            "platform_contract_version"
        ],
        ownership_model_id=ownership_model_id,
        runbook_catalog_id=runbook_catalog_id,
        checklist_id=checklist_id,
        ownership_assignments=assignments,
        support_tiers=support_tiers,
        runbooks=runbooks,
        access_controls=access_controls,
        handoff_checks=checks,
        metrics=metrics,
        decision=decision,
        reasons=reasons,
        automatic_handoff_performed=False,
        automatic_access_provisioning_performed=False,
        automatic_owner_assignment_performed=False,
        automatic_production_activation_performed=False,
        credentials_created=False,
        access_granted=False,
        production_authority_transferred=False,
        authority_boundary=(
            "Operational readiness may define roles, "
            "support tiers, runbooks, access prerequisites, "
            "evidence requirements, and handoff gates. It "
            "cannot provision access, assign real people, "
            "activate break-glass access, transfer production "
            "authority, deploy infrastructure, or approve a "
            "production release."
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
        "PASS: required checks="
        f"{metrics.passed_required_checks}/"
        f"{metrics.total_required_checks}"
    )
    print(
        "PASS: owner coverage="
        f"{metrics.owner_coverage_percentage:.2f}%"
    )
    print(
        "PASS: runbook coverage="
        f"{metrics.runbook_coverage_percentage:.2f}%"
    )
    print(
        "PASS: evidence coverage="
        f"{metrics.evidence_coverage_percentage:.2f}%"
    )
    print(
        "PASS: readiness decision="
        f"{decision.value}"
    )
    print("PASS: no automatic handoff")
    print("PASS: no access provisioning")
    print("PASS: no owner assignment")
    print("PASS: no production activation")
    print("PASS: no production authority transfer")


if __name__ == "__main__":
    main()
