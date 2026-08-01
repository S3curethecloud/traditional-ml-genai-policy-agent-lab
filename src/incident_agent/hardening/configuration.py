"""Production configuration loading and validation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from incident_agent.hardening.contracts import (
    HardeningError,
    HardeningErrorCode,
    ProductionConfiguration,
)


REQUIRED_VERSION_FIELDS = (
    "configuration_version",
    "model_provider",
    "model_name",
    "model_version",
    "prompt_version",
    "policy_version",
    "runtime_version",
    "orchestrator_version",
    "evaluation_version",
)


def load_production_configuration(
    path: Path,
    environment: dict[str, str] | None = None,
) -> ProductionConfiguration:
    """Load and validate production hardening configuration."""

    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    errors = validate_configuration_payload(
        payload=payload,
        environment=(
            dict(os.environ)
            if environment is None
            else environment
        ),
    )

    if errors:
        messages = "; ".join(
            f"{error.code.value}: {error.message}"
            for error in errors
        )

        raise ValueError(messages)

    return ProductionConfiguration(
        configuration_version=(
            payload["configuration_version"]
        ),
        environment=payload["environment"],
        model_provider=payload["model_provider"],
        model_name=payload["model_name"],
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
        request_timeout_seconds=float(
            payload["request_timeout_seconds"]
        ),
        provider_timeout_seconds=float(
            payload["provider_timeout_seconds"]
        ),
        maximum_requests_per_window=int(
            payload["maximum_requests_per_window"]
        ),
        rate_limit_window_seconds=float(
            payload["rate_limit_window_seconds"]
        ),
        maximum_concurrent_workflows=int(
            payload["maximum_concurrent_workflows"]
        ),
        circuit_breaker_failure_threshold=int(
            payload[
                "circuit_breaker_failure_threshold"
            ]
        ),
        circuit_breaker_recovery_seconds=float(
            payload[
                "circuit_breaker_recovery_seconds"
            ]
        ),
        minimum_release_evidence_artifacts=int(
            payload[
                "minimum_release_evidence_artifacts"
            ]
        ),
        require_release_gate_pass=bool(
            payload["require_release_gate_pass"]
        ),
        require_signed_attestation=bool(
            payload["require_signed_attestation"]
        ),
        require_rollback_plan=bool(
            payload["require_rollback_plan"]
        ),
        allowed_promotion_sources=tuple(
            payload["allowed_promotion_sources"]
        ),
        allowed_promotion_targets=tuple(
            payload["allowed_promotion_targets"]
        ),
        secret_references=tuple(
            payload["secret_references"]
        ),
        prohibited_inline_secret_fields=tuple(
            payload["prohibited_inline_secret_fields"]
        ),
    )


def validate_configuration_payload(
    payload: dict[str, Any],
    environment: dict[str, str],
) -> tuple[HardeningError, ...]:
    """Validate configuration and external secret references."""

    errors: list[HardeningError] = []

    for field_name in REQUIRED_VERSION_FIELDS:
        value = payload.get(field_name)

        if not isinstance(value, str) or not value.strip():
            errors.append(
                HardeningError(
                    code=(
                        HardeningErrorCode
                        .INVALID_CONFIGURATION
                    ),
                    message=(
                        f"Required version field "
                        f"{field_name!r} is missing."
                    ),
                )
            )

    if payload.get("environment") != "production":
        errors.append(
            HardeningError(
                code=(
                    HardeningErrorCode
                    .INVALID_CONFIGURATION
                ),
                message=(
                    "Production configuration must declare "
                    "environment='production'."
                ),
            )
        )

    positive_numeric_fields = (
        "request_timeout_seconds",
        "provider_timeout_seconds",
        "maximum_requests_per_window",
        "rate_limit_window_seconds",
        "maximum_concurrent_workflows",
        "circuit_breaker_failure_threshold",
        "circuit_breaker_recovery_seconds",
        "minimum_release_evidence_artifacts",
    )

    for field_name in positive_numeric_fields:
        value = payload.get(field_name)

        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or value <= 0
        ):
            errors.append(
                HardeningError(
                    code=(
                        HardeningErrorCode
                        .INVALID_CONFIGURATION
                    ),
                    message=(
                        f"{field_name!r} must be positive."
                    ),
                )
            )

    prohibited_fields = {
        str(field).lower()
        for field in payload.get(
            "prohibited_inline_secret_fields",
            (),
        )
    }

    _find_inline_secrets(
        value=payload,
        prohibited_fields=prohibited_fields,
        path=(),
        errors=errors,
    )

    for reference in payload.get(
        "secret_references",
        (),
    ):
        if not isinstance(reference, str):
            errors.append(
                HardeningError(
                    code=(
                        HardeningErrorCode
                        .INVALID_CONFIGURATION
                    ),
                    message=(
                        "Secret references must be strings."
                    ),
                )
            )
            continue

        if not reference.startswith("env://"):
            errors.append(
                HardeningError(
                    code=(
                        HardeningErrorCode
                        .INVALID_CONFIGURATION
                    ),
                    message=(
                        "Only env:// secret references are "
                        "supported by this tutorial."
                    ),
                )
            )
            continue

        environment_name = reference.removeprefix(
            "env://"
        )

        if not environment.get(environment_name):
            errors.append(
                HardeningError(
                    code=(
                        HardeningErrorCode
                        .SECRET_REFERENCE_MISSING
                    ),
                    message=(
                        f"Required secret reference "
                        f"{environment_name!r} is unresolved."
                    ),
                )
            )

    if (
        float(payload.get(
            "provider_timeout_seconds",
            0,
        ))
        >= float(payload.get(
            "request_timeout_seconds",
            0,
        ))
    ):
        errors.append(
            HardeningError(
                code=(
                    HardeningErrorCode
                    .INVALID_CONFIGURATION
                ),
                message=(
                    "Provider timeout must be lower than "
                    "the overall request timeout."
                ),
            )
        )

    return tuple(errors)


def configuration_sha256(
    configuration: ProductionConfiguration,
) -> str:
    """Create a deterministic configuration digest."""

    import hashlib

    canonical = json.dumps(
        configuration.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()


def _find_inline_secrets(
    value: Any,
    prohibited_fields: set[str],
    path: tuple[str, ...],
    errors: list[HardeningError],
) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized_key = str(key).lower()

            if (
                normalized_key in prohibited_fields
                and nested not in {None, "", "***"}
            ):
                errors.append(
                    HardeningError(
                        code=(
                            HardeningErrorCode
                            .INLINE_SECRET_DETECTED
                        ),
                        message=(
                            "Inline secret detected at "
                            + ".".join((*path, str(key)))
                        ),
                    )
                )

            _find_inline_secrets(
                value=nested,
                prohibited_fields=prohibited_fields,
                path=(*path, str(key)),
                errors=errors,
            )

    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _find_inline_secrets(
                value=nested,
                prohibited_fields=prohibited_fields,
                path=(*path, str(index)),
                errors=errors,
            )
