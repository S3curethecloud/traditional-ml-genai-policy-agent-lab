"""Desired-versus-observed runtime drift detection."""

from __future__ import annotations

from incident_agent.deployment.contracts import (
    DeploymentManifest,
    DriftReport,
    DriftStatus,
    EnvironmentConfiguration,
    RuntimeState,
)
from incident_agent.deployment.loading import (
    configuration_sha256,
)


def detect_runtime_drift(
    manifest: DeploymentManifest,
    configuration: EnvironmentConfiguration,
    runtime_state: RuntimeState,
) -> DriftReport:
    """Compare desired deployment state with observed state."""

    differences: list[str] = []

    expected = {
        "release_id": manifest.release_id,
        "image_digest": manifest.image_digest,
        "source_revision": manifest.source_revision,
        "replica_count": configuration.replica_count,
        "configuration_sha256":
            configuration_sha256(configuration),
        "environment": configuration.environment,
    }

    observed = {
        "release_id": runtime_state.release_id,
        "image_digest": runtime_state.image_digest,
        "source_revision": runtime_state.source_revision,
        "replica_count": runtime_state.replica_count,
        "configuration_sha256":
            runtime_state.configuration_sha256,
        "environment": runtime_state.environment,
    }

    for field_name, expected_value in expected.items():
        if observed[field_name] != expected_value:
            differences.append(
                f"{field_name}: expected="
                f"{expected_value!s}, observed="
                f"{observed[field_name]!s}"
            )

    return DriftReport(
        status=(
            DriftStatus.IN_SYNC
            if not differences
            else DriftStatus.DRIFTED
        ),
        differences=tuple(differences),
    )
