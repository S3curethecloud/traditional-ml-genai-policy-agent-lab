"""Deployment manifest and environment loading."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from incident_agent.deployment.contracts import (
    DeploymentEnvironment,
    DeploymentManifest,
    EnvironmentConfiguration,
)


IMAGE_DIGEST_PATTERN = re.compile(
    r"^sha256:[0-9a-f]{64}$"
)


def load_deployment_manifest(
    path: Path,
) -> DeploymentManifest:
    """Load and validate an immutable deployment manifest."""

    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    digest = payload.get("image_digest", "")

    if not IMAGE_DIGEST_PATTERN.fullmatch(digest):
        raise ValueError(
            "Deployment image must use an immutable "
            "sha256 digest"
        )

    required = (
        "manifest_version",
        "release_id",
        "application_name",
        "image_repository",
        "source_revision",
        "model_version",
        "prompt_version",
        "policy_version",
        "runtime_version",
        "orchestrator_version",
        "evaluation_version",
        "supply_chain_policy_version",
        "required_handoff_path",
        "rollback_plan_path",
        "health_endpoint",
        "readiness_endpoint",
    )

    for field_name in required:
        value = payload.get(field_name)

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Missing deployment manifest field: "
                f"{field_name}"
            )

    return DeploymentManifest(
        manifest_version=payload["manifest_version"],
        release_id=payload["release_id"],
        application_name=payload["application_name"],
        image_repository=payload["image_repository"],
        image_digest=digest,
        source_revision=payload["source_revision"],
        model_version=payload["model_version"],
        prompt_version=payload["prompt_version"],
        policy_version=payload["policy_version"],
        runtime_version=payload["runtime_version"],
        orchestrator_version=(
            payload["orchestrator_version"]
        ),
        evaluation_version=(
            payload["evaluation_version"]
        ),
        supply_chain_policy_version=(
            payload["supply_chain_policy_version"]
        ),
        required_handoff_path=(
            payload["required_handoff_path"]
        ),
        rollback_plan_path=(
            payload["rollback_plan_path"]
        ),
        health_endpoint=payload["health_endpoint"],
        readiness_endpoint=payload["readiness_endpoint"],
    )


def load_environment_configuration(
    path: Path,
) -> EnvironmentConfiguration:
    """Load a deployment environment overlay."""

    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    environment = DeploymentEnvironment(
        payload["environment"]
    )

    positive_fields = (
        "replica_count",
        "maximum_concurrent_workflows",
        "request_timeout_seconds",
        "provider_timeout_seconds",
        "health_failure_threshold",
    )

    for field_name in positive_fields:
        value = payload.get(field_name)

        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or value <= 0
        ):
            raise ValueError(
                f"{field_name} must be positive"
            )

    if (
        payload["provider_timeout_seconds"]
        >= payload["request_timeout_seconds"]
    ):
        raise ValueError(
            "Provider timeout must be lower than "
            "request timeout"
        )

    if payload.get("production_side_effects_allowed"):
        raise ValueError(
            "Tutorial environments cannot allow "
            "production side effects"
        )

    return EnvironmentConfiguration(
        environment=environment,
        replica_count=int(payload["replica_count"]),
        maximum_concurrent_workflows=int(
            payload["maximum_concurrent_workflows"]
        ),
        request_timeout_seconds=float(
            payload["request_timeout_seconds"]
        ),
        provider_timeout_seconds=float(
            payload["provider_timeout_seconds"]
        ),
        health_failure_threshold=int(
            payload["health_failure_threshold"]
        ),
        require_human_approval=bool(
            payload["require_human_approval"]
        ),
        allow_deployment_simulation=bool(
            payload["allow_deployment_simulation"]
        ),
        production_side_effects_allowed=bool(
            payload["production_side_effects_allowed"]
        ),
    )


def configuration_sha256(
    configuration: EnvironmentConfiguration,
) -> str:
    """Return a deterministic overlay digest."""

    canonical = json.dumps(
        configuration.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()
