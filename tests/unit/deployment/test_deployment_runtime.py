"""Tests for Phase 12 deployment runtime."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from incident_agent.deployment.authorization import (
    authorize_deployment,
)
from incident_agent.deployment.contracts import (
    DeploymentApproval,
    DeploymentDecision,
    DeploymentEnvironment,
    DeploymentIdentity,
    DeploymentStatus,
    DriftStatus,
)
from incident_agent.deployment.drift import (
    detect_runtime_drift,
)
from incident_agent.deployment.loading import (
    configuration_sha256,
    load_deployment_manifest,
    load_environment_configuration,
)
from incident_agent.deployment.runtime import (
    DEPLOYMENT_RUNTIME_VERSION,
    SimulatedDeploymentRuntime,
)


ROOT = Path(".")
MANIFEST_PATH = Path(
    "deployment/manifests/phase-12-release.json"
)
STAGING_PATH = Path(
    "deployment/environments/staging.json"
)
PRODUCTION_PATH = Path(
    "deployment/environments/production.json"
)


def manifest():
    return load_deployment_manifest(MANIFEST_PATH)


def staging():
    return load_environment_configuration(
        STAGING_PATH
    )


def production():
    return load_environment_configuration(
        PRODUCTION_PATH
    )


def staging_identity():
    return DeploymentIdentity(
        subject_id="staging-operator",
        roles=("deployment_operator",),
        allowed_environments=("staging",),
    )


def production_identity():
    return DeploymentIdentity(
        subject_id="production-controller",
        roles=(
            "deployment_operator",
            "production_approver",
        ),
        allowed_environments=("production",),
    )


def approval():
    handoff = json.loads(
        Path(
            "reports/supply-chain/"
            "deployment-handoff.json"
        ).read_text(encoding="utf-8")
    )

    return DeploymentApproval(
        approval_id="approval-test",
        release_id=manifest().release_id,
        environment=DeploymentEnvironment.PRODUCTION,
        approver_id="production-controller",
        approved=True,
        evidence_sha256=handoff["evidence_sha256"],
    )


def test_manifest_requires_immutable_digest(
    tmp_path,
) -> None:
    payload = json.loads(
        MANIFEST_PATH.read_text(
            encoding="utf-8"
        )
    )
    payload["image_digest"] = "latest"

    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="immutable",
    ):
        load_deployment_manifest(path)


def test_manifest_loads() -> None:
    loaded = manifest()

    assert loaded.release_id
    assert loaded.image_digest.startswith(
        "sha256:"
    )


def test_staging_overlay_loads() -> None:
    loaded = staging()

    assert (
        loaded.environment
        is DeploymentEnvironment.STAGING
    )
    assert not loaded.require_human_approval


def test_production_requires_approval() -> None:
    loaded = production()

    assert (
        loaded.environment
        is DeploymentEnvironment.PRODUCTION
    )
    assert loaded.require_human_approval


def test_environment_digest_is_reproducible() -> None:
    loaded = staging()

    assert (
        configuration_sha256(loaded)
        == configuration_sha256(loaded)
    )


def test_unauthorized_role_is_denied() -> None:
    identity = DeploymentIdentity(
        subject_id="viewer",
        roles=("viewer",),
        allowed_environments=("staging",),
    )

    result = authorize_deployment(
        root=ROOT,
        identity=identity,
        manifest=manifest(),
        configuration=staging(),
        approval=None,
    )

    assert (
        result.decision
        is DeploymentDecision.DENY
    )


def test_environment_scope_is_enforced() -> None:
    identity = DeploymentIdentity(
        subject_id="staging-operator",
        roles=("deployment_operator",),
        allowed_environments=("staging",),
    )

    result = authorize_deployment(
        root=ROOT,
        identity=identity,
        manifest=manifest(),
        configuration=production(),
        approval=None,
    )

    assert (
        result.decision
        is DeploymentDecision.DENY
    )


def test_staging_deployment_is_allowed() -> None:
    result = authorize_deployment(
        root=ROOT,
        identity=staging_identity(),
        manifest=manifest(),
        configuration=staging(),
        approval=None,
    )

    assert (
        result.decision
        is DeploymentDecision.ALLOW
    )


def test_production_without_approval_requires_approval() -> None:
    identity = DeploymentIdentity(
        subject_id="production-operator",
        roles=("deployment_operator",),
        allowed_environments=("production",),
    )

    result = authorize_deployment(
        root=ROOT,
        identity=identity,
        manifest=manifest(),
        configuration=production(),
        approval=None,
    )

    assert (
        result.decision
        is DeploymentDecision.REQUIRE_APPROVAL
    )


def test_production_with_approval_is_allowed() -> None:
    result = authorize_deployment(
        root=ROOT,
        identity=production_identity(),
        manifest=manifest(),
        configuration=production(),
        approval=approval(),
    )

    assert (
        result.decision
        is DeploymentDecision.ALLOW
    )


def test_wrong_evidence_approval_is_denied() -> None:
    invalid = replace(
        approval(),
        evidence_sha256="b" * 64,
    )

    result = authorize_deployment(
        root=ROOT,
        identity=production_identity(),
        manifest=manifest(),
        configuration=production(),
        approval=invalid,
    )

    assert (
        result.decision
        is DeploymentDecision.REQUIRE_APPROVAL
    )


def test_staging_runtime_becomes_healthy() -> None:
    runtime = SimulatedDeploymentRuntime()

    result = runtime.deploy(
        root=ROOT,
        identity=staging_identity(),
        manifest=manifest(),
        configuration=staging(),
    )

    assert (
        result.status
        is DeploymentStatus.HEALTHY
    )
    assert result.runtime_state is not None
    assert result.runtime_state.healthy
    assert result.runtime_state.ready


def test_production_runtime_requires_approval() -> None:
    runtime = SimulatedDeploymentRuntime()

    identity = DeploymentIdentity(
        subject_id="production-operator",
        roles=("deployment_operator",),
        allowed_environments=("production",),
    )

    result = runtime.deploy(
        root=ROOT,
        identity=identity,
        manifest=manifest(),
        configuration=production(),
    )

    assert (
        result.status
        is DeploymentStatus.BLOCKED
    )
    assert result.runtime_state is None


def test_approved_production_runtime_becomes_healthy() -> None:
    runtime = SimulatedDeploymentRuntime()

    result = runtime.deploy(
        root=ROOT,
        identity=production_identity(),
        manifest=manifest(),
        configuration=production(),
        approval=approval(),
    )

    assert (
        result.status
        is DeploymentStatus.HEALTHY
    )
    assert result.runtime_state is not None


def test_health_failure_rolls_back() -> None:
    runtime = SimulatedDeploymentRuntime()

    result = runtime.deploy(
        root=ROOT,
        identity=staging_identity(),
        manifest=manifest(),
        configuration=staging(),
        health_passed=False,
    )

    assert (
        result.status
        is DeploymentStatus.ROLLED_BACK
    )
    assert result.rollback_performed
    assert runtime.current_state(
        DeploymentEnvironment.STAGING
    ) is None


def test_readiness_failure_rolls_back() -> None:
    runtime = SimulatedDeploymentRuntime()

    result = runtime.deploy(
        root=ROOT,
        identity=staging_identity(),
        manifest=manifest(),
        configuration=staging(),
        readiness_passed=False,
    )

    assert (
        result.status
        is DeploymentStatus.ROLLED_BACK
    )


def test_runtime_state_has_no_drift() -> None:
    runtime = SimulatedDeploymentRuntime()

    result = runtime.deploy(
        root=ROOT,
        identity=staging_identity(),
        manifest=manifest(),
        configuration=staging(),
    )

    assert result.drift_report is not None
    assert (
        result.drift_report.status
        is DriftStatus.IN_SYNC
    )


def test_modified_runtime_state_detects_drift() -> None:
    runtime = SimulatedDeploymentRuntime()

    result = runtime.deploy(
        root=ROOT,
        identity=staging_identity(),
        manifest=manifest(),
        configuration=staging(),
    )

    assert result.runtime_state is not None

    modified = replace(
        result.runtime_state,
        replica_count=99,
    )

    drift = detect_runtime_drift(
        manifest=manifest(),
        configuration=staging(),
        runtime_state=modified,
    )

    assert drift.status is DriftStatus.DRIFTED
    assert drift.differences


def test_manual_rollback_removes_state() -> None:
    runtime = SimulatedDeploymentRuntime()

    runtime.deploy(
        root=ROOT,
        identity=staging_identity(),
        manifest=manifest(),
        configuration=staging(),
    )

    assert runtime.rollback(
        DeploymentEnvironment.STAGING
    )

    assert runtime.current_state(
        DeploymentEnvironment.STAGING
    ) is None


def test_audit_events_are_ordered() -> None:
    runtime = SimulatedDeploymentRuntime()

    result = runtime.deploy(
        root=ROOT,
        identity=staging_identity(),
        manifest=manifest(),
        configuration=staging(),
    )

    sequences = [
        event.sequence
        for event in result.audit_events
    ]

    assert sequences == list(
        range(1, len(sequences) + 1)
    )


def test_audit_events_bind_release_and_environment() -> None:
    runtime = SimulatedDeploymentRuntime()

    result = runtime.deploy(
        root=ROOT,
        identity=staging_identity(),
        manifest=manifest(),
        configuration=staging(),
    )

    assert all(
        event.release_id == manifest().release_id
        and event.environment == "staging"
        for event in result.audit_events
    )


def test_runtime_performs_no_real_side_effects() -> None:
    runtime = SimulatedDeploymentRuntime()

    result = runtime.deploy(
        root=ROOT,
        identity=staging_identity(),
        manifest=manifest(),
        configuration=staging(),
    )

    assert not (
        result.production_side_effects_performed
    )
    assert "cannot perform real" in (
        result.authority_boundary
    )


def test_deployment_runtime_version_is_recorded() -> None:
    assert (
        DEPLOYMENT_RUNTIME_VERSION
        == "deployment-runtime-v1"
    )
