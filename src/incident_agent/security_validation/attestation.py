"""Compliance coverage and security-attestation logic."""

from __future__ import annotations

from pathlib import Path

from incident_agent.security_validation.contracts import (
    AttestationStatus,
    ComplianceControl,
    ControlCoverageResult,
    ResidualRisk,
    RiskSeverity,
    SecurityAttestation,
)
from incident_agent.security_validation.loading import (
    canonical_sha256,
)


def evaluate_control_coverage(
    root: Path,
    controls: tuple[ComplianceControl, ...],
) -> ControlCoverageResult:
    if not controls:
        raise ValueError(
            "At least one compliance control is required"
        )

    covered = 0

    for control in controls:
        if (
            control.framework_mappings
            and control.evidence_references
            and all(
                (root / reference).exists()
                for reference in control.evidence_references
            )
        ):
            covered += 1

    percentage = round(
        (covered / len(controls)) * 100.0,
        4,
    )

    return ControlCoverageResult(
        total_controls=len(controls),
        covered_controls=covered,
        coverage_percentage=percentage,
        passed=covered == len(controls),
    )


def count_open_critical_risks(
    risks: tuple[ResidualRisk, ...],
) -> int:
    return sum(
        risk.severity is RiskSeverity.CRITICAL
        and risk.status == "OPEN"
        for risk in risks
    )


def build_security_attestation(
    policy_version: str,
    attack_block_rate_percentage: float,
    control_coverage_percentage: float,
    open_critical_risks: int,
    minimum_attack_block_rate_percentage: float,
    minimum_control_coverage_percentage: float,
    maximum_open_critical_risks: int,
) -> SecurityAttestation:
    reasons: list[str] = []

    if (
        attack_block_rate_percentage
        < minimum_attack_block_rate_percentage
    ):
        reasons.append(
            "Adversarial block rate is below policy minimum."
        )

    if (
        control_coverage_percentage
        < minimum_control_coverage_percentage
    ):
        reasons.append(
            "Control coverage is below policy minimum."
        )

    if open_critical_risks > maximum_open_critical_risks:
        reasons.append(
            "Open critical risks exceed policy maximum."
        )

    status = (
        AttestationStatus.APPROVED
        if not reasons
        else AttestationStatus.BLOCKED
    )

    attestation_material = {
        "policy_version": policy_version,
        "attack_block_rate_percentage":
            attack_block_rate_percentage,
        "control_coverage_percentage":
            control_coverage_percentage,
        "open_critical_risks": open_critical_risks,
        "status": status.value,
    }

    return SecurityAttestation(
        attestation_id=(
            "security-attestation-"
            + canonical_sha256(
                attestation_material
            )[:12]
        ),
        policy_version=policy_version,
        attack_block_rate_percentage=(
            attack_block_rate_percentage
        ),
        control_coverage_percentage=(
            control_coverage_percentage
        ),
        open_critical_risks=open_critical_risks,
        status=status,
        reasons=tuple(reasons),
        automatic_exception_approval_performed=False,
        automatic_remediation_performed=False,
    )
