"""Progressive-delivery policy and release loading."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from incident_agent.progressive_delivery.contracts import (
    ReleaseCandidate,
)


IMAGE_DIGEST_PATTERN = re.compile(
    r"^sha256:[0-9a-f]{64}$"
)


def load_progressive_delivery_policy(
    path: Path,
) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    if (
        not isinstance(payload.get("policy_version"), str)
        or not payload["policy_version"].strip()
    ):
        raise ValueError("Policy version is required")

    if payload.get(
        "automatic_production_progression_allowed"
    ):
        raise ValueError(
            "Automatic production progression must remain disabled"
        )

    if payload.get("automatic_rollback_allowed"):
        raise ValueError(
            "Automatic rollback must remain disabled"
        )

    stages = payload.get("traffic_stages")

    if stages != [0, 5, 25, 50, 100]:
        raise ValueError(
            "Traffic stages must be [0, 5, 25, 50, 100]"
        )

    maximum_budget = payload.get(
        "maximum_error_budget_consumed"
    )

    if (
        not isinstance(maximum_budget, (int, float))
        or isinstance(maximum_budget, bool)
        or not 0.0 <= float(maximum_budget) <= 1.0
    ):
        raise ValueError(
            "maximum_error_budget_consumed must be between zero and one"
        )

    return payload


def load_release_candidate(
    path: Path,
) -> ReleaseCandidate:
    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not IMAGE_DIGEST_PATTERN.fullmatch(
        payload.get("image_digest", "")
    ):
        raise ValueError(
            "Release candidate requires immutable image digest"
        )

    required = (
        "release_id",
        "application_name",
        "candidate_version",
        "previous_version",
        "source_revision",
        "target_environment",
        "deployment_report_path",
        "operations_report_path",
        "resilience_report_path",
    )

    for field_name in required:
        value = payload.get(field_name)

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Missing release candidate field: {field_name}"
            )

    if (
        payload["candidate_version"]
        == payload["previous_version"]
    ):
        raise ValueError(
            "Candidate and previous versions must differ"
        )

    return ReleaseCandidate(
        release_id=payload["release_id"],
        application_name=payload["application_name"],
        candidate_version=payload["candidate_version"],
        previous_version=payload["previous_version"],
        source_revision=payload["source_revision"],
        image_digest=payload["image_digest"],
        target_environment=payload["target_environment"],
        deployment_report_path=(
            payload["deployment_report_path"]
        ),
        operations_report_path=(
            payload["operations_report_path"]
        ),
        resilience_report_path=(
            payload["resilience_report_path"]
        ),
    )


def canonical_sha256(payload: Any) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()
