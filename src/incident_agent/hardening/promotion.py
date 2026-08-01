"""Environment promotion and deployment-readiness controls."""

from __future__ import annotations

from incident_agent.hardening.attestation import (
    verify_release_attestation,
)
from incident_agent.hardening.contracts import (
    DeploymentReadinessReport,
    ProductionConfiguration,
    PromotionDecision,
    PromotionEvaluation,
    ReadinessCheck,
    ReadinessStatus,
    ReleaseAttestation,
)


HARDENING_VERSION = "production-hardening-v1"


def evaluate_deployment_readiness(
    configuration: ProductionConfiguration,
    release_id: str,
    release_gate_passed: bool,
    evidence_artifact_count: int,
    evidence_sha256: str,
    attestation: ReleaseAttestation,
    signing_key: str,
    rollback_plan_exists: bool,
) -> DeploymentReadinessReport:
    """Evaluate production deployment readiness."""

    checks = (
        ReadinessCheck(
            check_name="production_configuration",
            passed=(
                configuration.environment
                == "production"
            ),
            explanation=(
                "Configuration targets production."
            ),
        ),
        ReadinessCheck(
            check_name="release_gate",
            passed=(
                release_gate_passed
                or not configuration
                .require_release_gate_pass
            ),
            explanation=(
                "Phase 9 release gate must pass."
            ),
        ),
        ReadinessCheck(
            check_name="minimum_evidence_artifacts",
            passed=(
                evidence_artifact_count
                >= configuration
                .minimum_release_evidence_artifacts
            ),
            explanation=(
                "Evidence bundle contains the minimum "
                "required artifacts."
            ),
        ),
        ReadinessCheck(
            check_name="evidence_digest_binding",
            passed=(
                attestation.evidence_sha256
                == evidence_sha256
            ),
            explanation=(
                "Attestation is bound to the evaluated "
                "release evidence."
            ),
        ),
        ReadinessCheck(
            check_name="signed_attestation",
            passed=(
                verify_release_attestation(
                    attestation=attestation,
                    signing_key=signing_key,
                )
                if configuration
                .require_signed_attestation
                else True
            ),
            explanation=(
                "Release attestation signature is valid."
            ),
        ),
        ReadinessCheck(
            check_name="release_identifier_binding",
            passed=(
                attestation.release_id == release_id
            ),
            explanation=(
                "Attestation release ID matches the "
                "promotion request."
            ),
        ),
        ReadinessCheck(
            check_name="promotion_source",
            passed=(
                attestation.source_environment
                in configuration
                .allowed_promotion_sources
            ),
            explanation=(
                "Promotion source is explicitly allowed."
            ),
        ),
        ReadinessCheck(
            check_name="promotion_target",
            passed=(
                attestation.target_environment
                in configuration
                .allowed_promotion_targets
            ),
            explanation=(
                "Promotion target is explicitly allowed."
            ),
        ),
        ReadinessCheck(
            check_name="rollback_plan",
            passed=(
                (
                    rollback_plan_exists
                    and bool(
                        attestation.rollback_plan_id
                    )
                )
                if configuration.require_rollback_plan
                else True
            ),
            explanation=(
                "A rollback plan is recorded."
            ),
        ),
        ReadinessCheck(
            check_name="version_pinning",
            passed=all(
                (
                    configuration.model_version,
                    configuration.prompt_version,
                    configuration.policy_version,
                    configuration.runtime_version,
                    configuration.orchestrator_version,
                    configuration.evaluation_version,
                )
            ),
            explanation=(
                "Model, prompt, policy, runtime, "
                "orchestrator, and evaluation versions "
                "are pinned."
            ),
        ),
    )

    failed_count = sum(
        not check.passed
        for check in checks
    )

    status = (
        ReadinessStatus.READY
        if failed_count == 0
        else ReadinessStatus.BLOCKED
    )

    return DeploymentReadinessReport(
        release_id=release_id,
        status=status,
        checks=checks,
        passed_count=len(checks) - failed_count,
        failed_count=failed_count,
        hardening_version=HARDENING_VERSION,
        authority_boundary=(
            "Readiness evaluation may block promotion. "
            "It cannot deploy, change policy decisions, "
            "or waive failed release controls."
        ),
    )


def evaluate_promotion(
    report: DeploymentReadinessReport,
    attestation: ReleaseAttestation,
) -> PromotionEvaluation:
    """Convert readiness evidence into a promotion decision."""

    failed_checks = tuple(
        check.check_name
        for check in report.checks
        if not check.passed
    )

    decision = (
        PromotionDecision.APPROVE
        if report.status is ReadinessStatus.READY
        else PromotionDecision.REJECT
    )

    reasons = (
        (
            "All production-readiness checks passed.",
        )
        if decision is PromotionDecision.APPROVE
        else tuple(
            f"Failed readiness check: {name}"
            for name in failed_checks
        )
    )

    return PromotionEvaluation(
        decision=decision,
        reasons=reasons,
        release_id=attestation.release_id,
        source_environment=(
            attestation.source_environment
        ),
        target_environment=(
            attestation.target_environment
        ),
        evidence_sha256=attestation.evidence_sha256,
        readiness_status=report.status,
    )
