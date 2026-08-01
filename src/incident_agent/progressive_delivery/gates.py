"""Release security, reliability, and resilience gates."""

from __future__ import annotations

import json
from pathlib import Path

from incident_agent.progressive_delivery.contracts import (
    GateStatus,
    ReleaseCandidate,
    ReleaseGate,
)


def evaluate_release_gates(
    root: Path,
    candidate: ReleaseCandidate,
    maximum_error_budget_consumed: float,
) -> tuple[ReleaseGate, ...]:
    deployment = json.loads(
        (
            root / candidate.deployment_report_path
        ).read_text(encoding="utf-8")
    )
    operations = json.loads(
        (
            root / candidate.operations_report_path
        ).read_text(encoding="utf-8")
    )
    resilience = json.loads(
        (
            root / candidate.resilience_report_path
        ).read_text(encoding="utf-8")
    )

    production = deployment[
        "production_with_approval"
    ]

    deployment_passed = (
        production["status"] == "HEALTHY"
        and production["authorization_decision"] == "ALLOW"
        and production[
            "production_side_effects_performed"
        ]
        is False
    )

    normal_results = operations[
        "normal_slo_results"
    ]

    slo_passed = (
        len(normal_results) > 0
        and all(
            result["passed"]
            for result in normal_results
        )
    )

    maximum_observed_budget = max(
        result["error_budget_consumed"]
        for result in normal_results
    )

    error_budget_passed = (
        maximum_observed_budget
        <= maximum_error_budget_consumed
    )

    security_passed = (
        deployment[
            "security_properties"
        ]["production_side_effects_performed"]
        is False
        and operations[
            "automatic_remediation_performed"
        ]
        is False
        and operations[
            "production_side_effects_performed"
        ]
        is False
    )

    recovery = resilience["recovery"]

    resilience_passed = (
        resilience["rpo"]["passed"] is True
        and resilience["rto"]["passed"] is True
        and recovery["status"] == "RECOVERED"
        and recovery["replay_verified"] is True
        and recovery[
            "authority_boundary_preserved"
        ]
        is True
    )

    return (
        ReleaseGate(
            gate_name="deployment_health",
            status=(
                GateStatus.PASS
                if deployment_passed
                else GateStatus.FAIL
            ),
            explanation=(
                "Approved production deployment must be healthy."
            ),
            evidence_reference=(
                candidate.deployment_report_path
            ),
        ),
        ReleaseGate(
            gate_name="slo_health",
            status=(
                GateStatus.PASS
                if slo_passed
                else GateStatus.FAIL
            ),
            explanation=(
                "Normal operational SLOs must pass."
            ),
            evidence_reference=(
                candidate.operations_report_path
            ),
        ),
        ReleaseGate(
            gate_name="error_budget",
            status=(
                GateStatus.PASS
                if error_budget_passed
                else GateStatus.FAIL
            ),
            explanation=(
                "Observed error-budget consumption must remain "
                "within the configured limit."
            ),
            evidence_reference=(
                candidate.operations_report_path
            ),
        ),
        ReleaseGate(
            gate_name="security_boundary",
            status=(
                GateStatus.PASS
                if security_passed
                else GateStatus.FAIL
            ),
            explanation=(
                "No autonomous production action may be present."
            ),
            evidence_reference=(
                candidate.operations_report_path
            ),
        ),
        ReleaseGate(
            gate_name="resilience_readiness",
            status=(
                GateStatus.PASS
                if resilience_passed
                else GateStatus.FAIL
            ),
            explanation=(
                "RPO, RTO, replay, and recovery checks must pass."
            ),
            evidence_reference=(
                candidate.resilience_report_path
            ),
        ),
    )
