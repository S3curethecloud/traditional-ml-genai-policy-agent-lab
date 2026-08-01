"""Evaluate final controlled-deployment readiness."""

from __future__ import annotations

from incident_agent.release_closure.contracts import (
    AuthorityRestriction,
    ClosureMetrics,
    EvidenceRecord,
    RecoveryCapability,
    ReleaseCandidate,
    ReleaseClosureDecision,
    ReleaseGate,
)


def _percentage(
    numerator: int,
    denominator: int,
) -> float:
    if denominator <= 0:
        raise ValueError(
            "Percentage denominator must be greater than zero"
        )

    return round(
        numerator / denominator * 100.0,
        4,
    )


def calculate_closure_metrics(
    policy: dict,
    gates: tuple[ReleaseGate, ...],
    evidence: tuple[EvidenceRecord, ...],
    risk_values: dict[str, int | bool],
    recovery: tuple[RecoveryCapability, ...],
    restrictions: tuple[AuthorityRestriction, ...],
) -> ClosureMetrics:
    required_gates = set(
        policy["required_release_gates"]
    )
    passed_gates = {
        gate.gate_id
        for gate in gates
        if gate.passed
    }

    required_evidence = set(
        policy["required_phase_evidence"]
    )
    covered_evidence = {
        item.evidence_id
        for item in evidence
        if item.required and item.validated
    }

    required_recovery = set(
        policy["required_recovery_capabilities"]
    )
    verified_recovery = {
        item.capability
        for item in recovery
        if item.verified
    }

    required_restrictions = set(
        policy["required_authority_restrictions"]
    )
    preserved_restrictions = {
        item.restriction
        for item in restrictions
        if item.preserved
    }

    return ClosureMetrics(
        total_required_gates=len(required_gates),
        passed_required_gates=len(
            required_gates & passed_gates
        ),
        gate_pass_rate_percentage=_percentage(
            len(required_gates & passed_gates),
            len(required_gates),
        ),
        total_required_evidence=len(required_evidence),
        covered_required_evidence=len(
            required_evidence & covered_evidence
        ),
        evidence_coverage_percentage=_percentage(
            len(required_evidence & covered_evidence),
            len(required_evidence),
        ),
        open_critical_risks=int(
            risk_values["open_critical_risks"]
        ),
        approved_exceptions=int(
            risk_values["approved_exceptions"]
        ),
        verified_recovery_capabilities=len(
            required_recovery & verified_recovery
        ),
        required_recovery_capabilities=len(
            required_recovery
        ),
        preserved_authority_restrictions=len(
            required_restrictions
            & preserved_restrictions
        ),
        required_authority_restrictions=len(
            required_restrictions
        ),
    )


def determine_release_closure(
    policy: dict,
    candidate: ReleaseCandidate,
    metrics: ClosureMetrics,
    evidence_flags: dict[str, bool],
    risk_values: dict[str, int | bool],
    recovery: tuple[RecoveryCapability, ...],
    recovery_flags: dict[str, bool],
    authority_flags: dict[str, bool],
) -> tuple[
    ReleaseClosureDecision,
    tuple[str, ...],
]:
    reasons: list[str] = []

    if (
        candidate.platform_contract_version
        != policy["platform_contract_version"]
    ):
        reasons.append(
            "Release candidate targets the wrong platform contract."
        )

    if not candidate.immutable:
        reasons.append(
            "Release candidate is not immutable."
        )

    if (
        metrics.gate_pass_rate_percentage
        < policy["minimum_gate_pass_rate_percentage"]
    ):
        reasons.append(
            "Required release gates are incomplete."
        )

    if (
        metrics.evidence_coverage_percentage
        < policy[
            "minimum_evidence_coverage_percentage"
        ]
    ):
        reasons.append(
            "Required phase evidence is incomplete."
        )

    if (
        metrics.open_critical_risks
        > policy["maximum_open_critical_risks"]
    ):
        reasons.append(
            "Open critical risks exceed policy."
        )

    if (
        metrics.approved_exceptions
        > policy["maximum_approved_exceptions"]
    ):
        reasons.append(
            "Approved exceptions exceed policy."
        )

    if (
        metrics.verified_recovery_capabilities
        != metrics.required_recovery_capabilities
    ):
        reasons.append(
            "Recovery capability verification is incomplete."
        )

    if (
        metrics.preserved_authority_restrictions
        != metrics.required_authority_restrictions
    ):
        reasons.append(
            "Authority restrictions are incomplete."
        )

    if any(evidence_flags.values()):
        reasons.append(
            "Prior-phase evidence was changed or substituted."
        )

    if any(
        item.automatic_execution
        for item in recovery
    ):
        reasons.append(
            "Recovery capability enables automatic execution."
        )

    if any(recovery_flags.values()):
        reasons.append(
            "Closure evaluation changed production state."
        )

    if bool(risk_values["risk_acceptance_performed"]):
        reasons.append(
            "Risk acceptance was performed automatically."
        )

    if bool(
        risk_values["exception_approval_performed"]
    ):
        reasons.append(
            "Exception approval was performed automatically."
        )

    if int(
        risk_values["automatically_accepted_risks"]
    ) > 0:
        reasons.append(
            "Risks were automatically accepted."
        )

    if int(
        risk_values[
            "automatically_approved_exceptions"
        ]
    ) > 0:
        reasons.append(
            "Exceptions were automatically approved."
        )

    if not authority_flags[
        "production_approval_required"
    ]:
        reasons.append(
            "Human production approval is not required."
        )

    prohibited_authority_flags = (
        "production_approver_assigned",
        "deployment_credentials_created",
        "deployment_credentials_used",
        "production_access_granted",
        "production_authority_transferred",
    )

    if any(
        authority_flags[flag]
        for flag in prohibited_authority_flags
    ):
        reasons.append(
            "Release closure changed production authority."
        )

    candidate_side_effects = (
        candidate.deployment_performed,
        candidate.traffic_shift_performed,
        candidate.production_activation_performed,
    )

    if any(candidate_side_effects):
        reasons.append(
            "Release candidate records a production side effect."
        )

    if not candidate.human_production_approval_required:
        reasons.append(
            "Release candidate bypasses human approval."
        )

    decision = (
        ReleaseClosureDecision
        .READY_FOR_CONTROLLED_DEPLOYMENT
        if not reasons
        else ReleaseClosureDecision.BLOCKED
    )

    return decision, tuple(reasons)
