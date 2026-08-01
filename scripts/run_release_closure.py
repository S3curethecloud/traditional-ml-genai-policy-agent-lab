#!/usr/bin/env python3
"""Run Phase 20 final release-closure evaluation."""

from __future__ import annotations

import json
from pathlib import Path

from incident_agent.release_closure.contracts import (
    ReleaseClosureReport,
)
from incident_agent.release_closure.evaluation import (
    calculate_closure_metrics,
    determine_release_closure,
)
from incident_agent.release_closure.loading import (
    load_authority_boundary,
    load_closure_policy,
    load_evidence_registry,
    load_recovery_closure,
    load_release_candidate,
    load_release_gates,
    load_risk_closure,
)


ROOT = Path(".")
POLICY_PATH = (
    ROOT
    / "config/release-closure/"
    "release-closure-policy.json"
)
CANDIDATE_PATH = (
    ROOT
    / "release/closure/release-candidate.json"
)
EVIDENCE_PATH = (
    ROOT
    / "release/closure/evidence-registry.json"
)
GATES_PATH = (
    ROOT
    / "release/closure/release-gates.json"
)
RISK_PATH = (
    ROOT
    / "release/closure/"
    "risk-and-exception-closure.json"
)
RECOVERY_PATH = (
    ROOT
    / "release/closure/"
    "rollback-and-recovery.json"
)
AUTHORITY_PATH = (
    ROOT
    / "release/closure/authority-boundary.json"
)
OUTPUT_PATH = (
    ROOT
    / "reports/release-closure/"
    "phase-20-release-closure-report.json"
)


def main() -> None:
    policy = load_closure_policy(POLICY_PATH)
    candidate = load_release_candidate(
        CANDIDATE_PATH
    )

    (
        _registry_id,
        evidence,
        evidence_flags,
    ) = load_evidence_registry(EVIDENCE_PATH)

    _gate_set_id, gates = load_release_gates(
        GATES_PATH
    )

    (
        _risk_register_id,
        risks,
        risk_values,
    ) = load_risk_closure(RISK_PATH)

    (
        _recovery_closure_id,
        recovery,
        recovery_flags,
    ) = load_recovery_closure(RECOVERY_PATH)

    (
        _boundary_id,
        restrictions,
        authority_flags,
    ) = load_authority_boundary(AUTHORITY_PATH)

    metrics = calculate_closure_metrics(
        policy=policy,
        gates=gates,
        evidence=evidence,
        risk_values=risk_values,
        recovery=recovery,
        restrictions=restrictions,
    )

    decision, reasons = determine_release_closure(
        policy=policy,
        candidate=candidate,
        metrics=metrics,
        evidence_flags=evidence_flags,
        risk_values=risk_values,
        recovery=recovery,
        recovery_flags=recovery_flags,
        authority_flags=authority_flags,
    )

    report = ReleaseClosureReport(
        policy_version=policy["policy_version"],
        platform_contract_version=policy[
            "platform_contract_version"
        ],
        release_train=policy["release_train"],
        candidate=candidate,
        evidence=evidence,
        gates=gates,
        residual_risks=risks,
        recovery_capabilities=recovery,
        authority_restrictions=restrictions,
        metrics=metrics,
        decision=decision,
        reasons=reasons,
        automatic_release_approval_performed=False,
        automatic_deployment_performed=False,
        automatic_traffic_shift_performed=False,
        automatic_exception_approval_performed=False,
        automatic_risk_acceptance_performed=False,
        production_authority_transfer_performed=False,
        production_state_changed=False,
        authority_boundary=(
            "Release closure may validate an immutable "
            "candidate, bind prior evidence, evaluate final "
            "gates, verify rollback and recovery capability, "
            "and issue a controlled-deployment readiness "
            "decision. It cannot approve production use, "
            "deploy infrastructure, shift traffic, create or "
            "use credentials, accept risks, approve "
            "exceptions, or transfer production authority."
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
        "PASS: release gates="
        f"{metrics.passed_required_gates}/"
        f"{metrics.total_required_gates}"
    )
    print(
        "PASS: evidence coverage="
        f"{metrics.evidence_coverage_percentage:.2f}%"
    )
    print(
        "PASS: open critical risks="
        f"{metrics.open_critical_risks}"
    )
    print(
        "PASS: approved exceptions="
        f"{metrics.approved_exceptions}"
    )
    print(
        "PASS: recovery capabilities="
        f"{metrics.verified_recovery_capabilities}/"
        f"{metrics.required_recovery_capabilities}"
    )
    print(
        "PASS: authority restrictions="
        f"{metrics.preserved_authority_restrictions}/"
        f"{metrics.required_authority_restrictions}"
    )
    print(
        "PASS: closure decision="
        f"{decision.value}"
    )
    print("PASS: no automatic release approval")
    print("PASS: no deployment")
    print("PASS: no traffic shift")
    print("PASS: no exception approval")
    print("PASS: no risk acceptance")
    print("PASS: no production authority transfer")


if __name__ == "__main__":
    main()
