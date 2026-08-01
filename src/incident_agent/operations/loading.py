"""Runtime-operations policy loading and validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from incident_agent.operations.contracts import (
    ComparisonOperator,
    SLODefinition,
)


def load_operations_policy(path: Path) -> dict[str, Any]:
    """Load and validate the runtime-operations policy."""

    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    if (
        not isinstance(payload.get("policy_version"), str)
        or not payload["policy_version"].strip()
    ):
        raise ValueError(
            "Operations policy version is required"
        )

    minimum_samples = payload.get(
        "minimum_samples_per_sli"
    )

    if (
        not isinstance(minimum_samples, int)
        or isinstance(minimum_samples, bool)
        or minimum_samples <= 0
    ):
        raise ValueError(
            "minimum_samples_per_sli must be positive"
        )

    warning = payload.get(
        "error_budget_warning_threshold"
    )
    exhausted = payload.get(
        "error_budget_exhausted_threshold"
    )

    if not isinstance(warning, (int, float)):
        raise ValueError(
            "Error-budget warning threshold is required"
        )

    if not isinstance(exhausted, (int, float)):
        raise ValueError(
            "Error-budget exhausted threshold is required"
        )

    if not 0.0 <= float(warning) <= float(exhausted):
        raise ValueError(
            "Error-budget thresholds are invalid"
        )

    if payload.get("automatic_remediation_allowed"):
        raise ValueError(
            "Automatic remediation must remain disabled"
        )

    if payload.get("automatic_rollback_allowed"):
        raise ValueError(
            "Automatic rollback must remain disabled"
        )

    definitions = parse_slo_definitions(payload)

    if len(definitions) != len(
        {definition.slo_id for definition in definitions}
    ):
        raise ValueError("SLO identifiers must be unique")

    return payload


def parse_slo_definitions(
    policy: dict[str, Any],
) -> tuple[SLODefinition, ...]:
    """Parse typed SLO definitions from a policy."""

    definitions: list[SLODefinition] = []

    for raw in policy.get("slo_definitions", []):
        target = float(raw["target_percentage"])

        if not 0.0 < target <= 100.0:
            raise ValueError(
                "SLO target_percentage must be "
                "between zero and one hundred"
            )

        definitions.append(
            SLODefinition(
                slo_id=str(raw["slo_id"]),
                metric_name=str(raw["metric_name"]),
                description=str(raw["description"]),
                comparison=ComparisonOperator(
                    raw["comparison"]
                ),
                threshold=float(raw["threshold"]),
                target_percentage=target,
            )
        )

    if not definitions:
        raise ValueError(
            "At least one SLO definition is required"
        )

    return tuple(definitions)


def policy_sha256(policy: dict[str, Any]) -> str:
    """Return a deterministic operations-policy digest."""

    canonical = json.dumps(
        policy,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()
