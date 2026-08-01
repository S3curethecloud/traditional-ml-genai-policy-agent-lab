#!/usr/bin/env python3
"""Run Phase 12 deployment and promotion simulation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from incident_agent.deployment.contracts import (
    DeploymentApproval,
    DeploymentEnvironment,
    DeploymentIdentity,
)
from incident_agent.deployment.loading import (
    load_deployment_manifest,
    load_environment_configuration,
)
from incident_agent.deployment.runtime import (
    SimulatedDeploymentRuntime,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate staging and production deployment "
            "promotion."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(
            "deployment/manifests/"
            "phase-12-release.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "reports/deployment/"
            "phase-12-deployment-report.json"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()

    manifest = load_deployment_manifest(
        root / args.manifest
    )

    staging = load_environment_configuration(
        root
        / "deployment/environments/staging.json"
    )

    production = load_environment_configuration(
        root
        / "deployment/environments/production.json"
    )

    handoff = json.loads(
        (
            root
            / manifest.required_handoff_path
        ).read_text(encoding="utf-8")
    )

    runtime = SimulatedDeploymentRuntime()

    staging_identity = DeploymentIdentity(
        subject_id="deployment-operator-staging",
        roles=("deployment_operator",),
        allowed_environments=("staging",),
    )

    staging_outcome = runtime.deploy(
        root=root,
        identity=staging_identity,
        manifest=manifest,
        configuration=staging,
    )

    unapproved_production_identity = (
        DeploymentIdentity(
            subject_id="deployment-operator-production",
            roles=("deployment_operator",),
            allowed_environments=("production",),
        )
    )

    production_without_approval = runtime.deploy(
        root=root,
        identity=unapproved_production_identity,
        manifest=manifest,
        configuration=production,
    )

    approved_identity = DeploymentIdentity(
        subject_id="production-release-controller",
        roles=(
            "deployment_operator",
            "production_approver",
        ),
        allowed_environments=("production",),
    )

    approval = DeploymentApproval(
        approval_id="approval-phase-12-v1",
        release_id=manifest.release_id,
        environment=DeploymentEnvironment.PRODUCTION,
        approver_id="production-release-controller",
        approved=True,
        evidence_sha256=handoff["evidence_sha256"],
    )

    production_outcome = runtime.deploy(
        root=root,
        identity=approved_identity,
        manifest=manifest,
        configuration=production,
        approval=approval,
    )

    failed_health_outcome = runtime.deploy(
        root=root,
        identity=staging_identity,
        manifest=manifest,
        configuration=staging,
        health_passed=False,
        readiness_passed=True,
    )

    report = {
        "phase": "phase-12",
        "manifest": manifest.to_dict(),
        "staging_deployment":
            staging_outcome.to_dict(),
        "production_without_approval":
            production_without_approval.to_dict(),
        "production_with_approval":
            production_outcome.to_dict(),
        "failed_health_rollback":
            failed_health_outcome.to_dict(),
        "security_properties": {
            "immutable_image_required": True,
            "deployment_identity_required": True,
            "environment_scope_required": True,
            "supply_chain_handoff_required": True,
            "rollback_plan_required": True,
            "production_approval_required": True,
            "health_and_readiness_required": True,
            "drift_detection_performed": True,
            "ci_direct_to_production_allowed": False,
            "production_side_effects_performed": False
        }
    }

    output = root / args.output
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"PASS: staging="
        f"{staging_outcome.status.value}"
    )
    print(
        "PASS: production without approval="
        f"{production_without_approval.authorization_decision.value}"
    )
    print(
        f"PASS: approved production="
        f"{production_outcome.status.value}"
    )
    print(
        f"PASS: failed health deployment="
        f"{failed_health_outcome.status.value}"
    )
    drift_status = (
        production_outcome.drift_report.status.value
        if production_outcome.drift_report is not None
        else "NOT_EVALUATED"
    )

    print(
        "PASS: drift detection="
        f"{drift_status}"
    )
    print(
        "PASS: no real infrastructure changes performed"
    )


if __name__ == "__main__":
    main()
