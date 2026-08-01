"""Resilience-policy loading and validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def load_resilience_policy(
    path: Path,
) -> dict[str, Any]:
    """Load and validate resilience policy."""

    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    if (
        not isinstance(payload.get("policy_version"), str)
        or not payload["policy_version"].strip()
    ):
        raise ValueError(
            "Resilience policy version is required"
        )

    if payload.get("automatic_failover_allowed"):
        raise ValueError(
            "Automatic failover must remain disabled"
        )

    if payload.get(
        "automatic_disaster_declaration_allowed"
    ):
        raise ValueError(
            "Automatic disaster declaration must remain disabled"
        )

    for field_name in (
        "maximum_rpo_seconds",
        "maximum_rto_seconds",
        "minimum_healthy_regions",
        "required_backup_copies",
    ):
        value = payload.get(field_name)

        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value <= 0
        ):
            raise ValueError(
                f"{field_name} must be a positive integer"
            )

    scenarios = payload.get("chaos_scenarios")

    if (
        not isinstance(scenarios, list)
        or not scenarios
    ):
        raise ValueError(
            "At least one chaos scenario is required"
        )

    if len(scenarios) != len(set(scenarios)):
        raise ValueError(
            "Chaos scenario identifiers must be unique"
        )

    return payload


def policy_sha256(
    policy: dict[str, Any],
) -> str:
    """Return deterministic resilience-policy digest."""

    canonical = json.dumps(
        policy,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()
