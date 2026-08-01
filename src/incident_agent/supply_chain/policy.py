"""Supply-chain policy loading and validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from incident_agent.supply_chain.contracts import (
    SupplyChainPolicy,
)


def load_supply_chain_policy(
    path: Path,
) -> SupplyChainPolicy:
    """Load and validate the supply-chain policy."""

    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    required_string_fields = (
        "policy_version",
        "required_test_command",
        "required_python_version",
        "required_readiness_status",
        "required_promotion_decision",
        "required_container_user",
        "allowed_promotion_source",
        "allowed_promotion_target",
    )

    for field_name in required_string_fields:
        value = payload.get(field_name)

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Missing required policy field: "
                f"{field_name}"
            )

    if (
        not isinstance(
            payload.get("maximum_container_size_mb"),
            int,
        )
        or payload["maximum_container_size_mb"] <= 0
    ):
        raise ValueError(
            "maximum_container_size_mb must be positive"
        )

    required_lists = (
        "required_evidence_files",
        "prohibited_file_patterns",
        "prohibited_secret_markers",
    )

    for field_name in required_lists:
        value = payload.get(field_name)

        if not isinstance(value, list):
            raise ValueError(
                f"{field_name} must be a list"
            )

    return SupplyChainPolicy(
        policy_version=payload["policy_version"],
        required_test_command=(
            payload["required_test_command"]
        ),
        required_python_version=(
            payload["required_python_version"]
        ),
        required_evidence_files=tuple(
            payload["required_evidence_files"]
        ),
        required_release_gate_status=bool(
            payload["required_release_gate_status"]
        ),
        required_readiness_status=(
            payload["required_readiness_status"]
        ),
        required_promotion_decision=(
            payload["required_promotion_decision"]
        ),
        required_container_user=(
            payload["required_container_user"]
        ),
        maximum_container_size_mb=int(
            payload["maximum_container_size_mb"]
        ),
        require_non_root_container=bool(
            payload["require_non_root_container"]
        ),
        require_sbom=bool(payload["require_sbom"]),
        require_checksum_manifest=bool(
            payload["require_checksum_manifest"]
        ),
        require_build_provenance=bool(
            payload["require_build_provenance"]
        ),
        require_rollback_artifact=bool(
            payload["require_rollback_artifact"]
        ),
        require_deployment_handoff=bool(
            payload["require_deployment_handoff"]
        ),
        prohibited_file_patterns=tuple(
            payload["prohibited_file_patterns"]
        ),
        prohibited_secret_markers=tuple(
            payload["prohibited_secret_markers"]
        ),
        allowed_promotion_source=(
            payload["allowed_promotion_source"]
        ),
        allowed_promotion_target=(
            payload["allowed_promotion_target"]
        ),
    )


def policy_sha256(
    path: Path,
) -> str:
    """Return a digest of the canonical policy payload."""

    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()
