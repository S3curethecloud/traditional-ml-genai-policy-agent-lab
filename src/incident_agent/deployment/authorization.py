"""Deployment preflight and authorization controls."""

from __future__ import annotations

import json
from pathlib import Path

from incident_agent.deployment.contracts import (
    DeploymentApproval,
    DeploymentAuthorization,
    DeploymentDecision,
    DeploymentEnvironment,
    DeploymentIdentity,
    DeploymentManifest,
    EnvironmentConfiguration,
    PreflightCheck,
)


DEPLOYMENT_ROLE = "deployment_operator"
PRODUCTION_APPROVER_ROLE = "production_approver"


def authorize_deployment(
    root: Path,
    identity: DeploymentIdentity,
    manifest: DeploymentManifest,
    configuration: EnvironmentConfiguration,
    approval: DeploymentApproval | None,
) -> DeploymentAuthorization:
    """Evaluate deployment identity and release evidence."""

    handoff_path = (
        root / manifest.required_handoff_path
    )
    rollback_path = (
        root / manifest.rollback_plan_path
    )

    handoff_exists = handoff_path.is_file()

    handoff: dict = {}

    if handoff_exists:
        handoff = json.loads(
            handoff_path.read_text(encoding="utf-8")
        )

    target = configuration.environment.value

    checks = [
        PreflightCheck(
            check_name="deployment_role",
            passed=DEPLOYMENT_ROLE in identity.roles,
            explanation=(
                "Identity must hold deployment_operator."
            ),
        ),
        PreflightCheck(
            check_name="environment_scope",
            passed=target in identity.allowed_environments,
            explanation=(
                "Identity must be scoped to the target "
                "environment."
            ),
        ),
        PreflightCheck(
            check_name="deployment_simulation_enabled",
            passed=(
                configuration.allow_deployment_simulation
            ),
            explanation=(
                "Environment must permit deployment "
                "simulation."
            ),
        ),
        PreflightCheck(
            check_name="production_side_effects_disabled",
            passed=(
                not configuration
                .production_side_effects_allowed
            ),
            explanation=(
                "Tutorial deployment must not allow "
                "production side effects."
            ),
        ),
        PreflightCheck(
            check_name="deployment_handoff_exists",
            passed=handoff_exists,
            explanation=(
                "Phase 11 deployment handoff must exist."
            ),
        ),
        PreflightCheck(
            check_name="deployment_handoff_ready",
            passed=(
                handoff.get("decision")
                == "READY_FOR_DEPLOYMENT_HANDOFF"
            ),
            explanation=(
                "Supply-chain handoff must be ready."
            ),
        ),
        PreflightCheck(
            check_name="handoff_not_already_deployed",
            passed=(
                handoff.get("deployment_performed")
                is False
            ),
            explanation=(
                "Supply-chain handoff must not claim "
                "deployment already occurred."
            ),
        ),
        PreflightCheck(
            check_name="rollback_plan_exists",
            passed=(
                rollback_path.is_file()
                and rollback_path.stat().st_size > 0
            ),
            explanation=(
                "Rollback evidence must exist."
            ),
        ),
        PreflightCheck(
            check_name="source_revision_binding",
            passed=(
                handoff.get("source_revision")
                == manifest.source_revision
            ),
            explanation=(
                "Manifest revision must match the "
                "supply-chain handoff."
            ),
        ),
    ]

    if (
        configuration.environment
        is DeploymentEnvironment.PRODUCTION
    ):
        approval_valid = (
            approval is not None
            and approval.approved
            and approval.release_id
            == manifest.release_id
            and approval.environment
            is DeploymentEnvironment.PRODUCTION
            and PRODUCTION_APPROVER_ROLE
            in identity.roles
            and approval.evidence_sha256
            == handoff.get("evidence_sha256")
        )

        checks.append(
            PreflightCheck(
                check_name="production_approval",
                passed=approval_valid,
                explanation=(
                    "Production requires an explicit "
                    "evidence-bound approval."
                ),
            )
        )

    failed = tuple(
        check.check_name
        for check in checks
        if not check.passed
    )

    if not failed:
        decision = DeploymentDecision.ALLOW
        reasons = (
            "All deployment preflight checks passed.",
        )
    elif (
        configuration.environment
        is DeploymentEnvironment.PRODUCTION
        and failed == ("production_approval",)
    ):
        decision = DeploymentDecision.REQUIRE_APPROVAL
        reasons = (
            "Production deployment requires approval.",
        )
    else:
        decision = DeploymentDecision.DENY
        reasons = tuple(
            f"Failed deployment check: {name}"
            for name in failed
        )

    return DeploymentAuthorization(
        decision=decision,
        checks=tuple(checks),
        reasons=reasons,
    )
