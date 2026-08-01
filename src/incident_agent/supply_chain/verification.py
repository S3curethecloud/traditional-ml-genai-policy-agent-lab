"""Verification of prior release and hardening evidence."""

from __future__ import annotations

import json
from pathlib import Path

from incident_agent.supply_chain.contracts import (
    GateResult,
    GateStatus,
    SupplyChainPolicy,
)


def verify_prior_phase_evidence(
    root: Path,
    policy: SupplyChainPolicy,
) -> tuple[GateResult, ...]:
    """Verify Phase 9 and Phase 10 release evidence."""

    gates: list[GateResult] = []

    missing = tuple(
        path
        for path in policy.required_evidence_files
        if not (root / path).is_file()
    )

    gates.append(
        GateResult(
            gate_name="required_evidence_files",
            status=(
                GateStatus.PASS
                if not missing
                else GateStatus.FAIL
            ),
            explanation=(
                "All required release evidence files exist."
                if not missing
                else "Required release evidence is missing."
            ),
            evidence_references=missing,
        )
    )

    if missing:
        return tuple(gates)

    phase_9 = json.loads(
        (
            root
            / "reports/observability/"
            "phase-09-release-evidence.json"
        ).read_text(encoding="utf-8")
    )

    phase_10 = json.loads(
        (
            root
            / "reports/hardening/"
            "phase-10-production-readiness.json"
        ).read_text(encoding="utf-8")
    )

    gates.append(
        GateResult(
            gate_name="phase_09_release_gate",
            status=(
                GateStatus.PASS
                if (
                    phase_9["release_gate_passed"]
                    is policy.required_release_gate_status
                )
                else GateStatus.FAIL
            ),
            explanation=(
                "Phase 9 release gate matches policy."
            ),
            evidence_references=(
                phase_9["aggregate_sha256"],
            ),
        )
    )

    readiness = phase_10[
        "deployment_readiness"
    ]["status"]

    gates.append(
        GateResult(
            gate_name="phase_10_readiness",
            status=(
                GateStatus.PASS
                if readiness
                == policy.required_readiness_status
                else GateStatus.FAIL
            ),
            explanation=(
                "Phase 10 readiness status matches policy."
            ),
            evidence_references=(readiness,),
        )
    )

    promotion = phase_10[
        "promotion_evaluation"
    ]

    promotion_valid = (
        promotion["decision"]
        == policy.required_promotion_decision
        and promotion["source_environment"]
        == policy.allowed_promotion_source
        and promotion["target_environment"]
        == policy.allowed_promotion_target
    )

    gates.append(
        GateResult(
            gate_name="phase_10_promotion",
            status=(
                GateStatus.PASS
                if promotion_valid
                else GateStatus.FAIL
            ),
            explanation=(
                "Phase 10 promotion decision and path "
                "match supply-chain policy."
            ),
            evidence_references=(
                promotion["decision"],
                promotion["source_environment"],
                promotion["target_environment"],
            ),
        )
    )

    return tuple(gates)
