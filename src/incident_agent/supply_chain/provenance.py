"""Build provenance and deployment handoff generation."""

from __future__ import annotations

import hashlib
import json

from incident_agent.supply_chain.contracts import (
    BuildProvenance,
    ChecksumManifest,
    DeploymentHandoff,
    DeploymentHandoffDecision,
    GateResult,
    GateStatus,
    SupplyChainPolicy,
)


PROVENANCE_VERSION = "build-provenance-v1"
HANDOFF_VERSION = "deployment-handoff-v1"


def build_provenance(
    release_id: str,
    source_repository: str,
    source_revision: str,
    source_branch: str,
    builder_identity: str,
    build_command: str,
    test_command: str,
    policy_sha256: str,
    checksum_manifest: ChecksumManifest,
    sbom_sha256: str,
) -> BuildProvenance:
    """Create deterministic build provenance."""

    return BuildProvenance(
        provenance_version=PROVENANCE_VERSION,
        release_id=release_id,
        source_repository=source_repository,
        source_revision=source_revision,
        source_branch=source_branch,
        builder_identity=builder_identity,
        build_command=build_command,
        test_command=test_command,
        policy_sha256=policy_sha256,
        checksum_manifest_sha256=(
            checksum_manifest.aggregate_sha256
        ),
        sbom_sha256=sbom_sha256,
        production_deployment_performed=False,
    )


def provenance_sha256(
    provenance: BuildProvenance,
) -> str:
    """Return deterministic provenance digest."""

    canonical = json.dumps(
        provenance.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()


def create_deployment_handoff(
    policy: SupplyChainPolicy,
    release_id: str,
    source_revision: str,
    evidence_sha256: str,
    checksum_manifest_sha256: str,
    sbom_sha256_value: str,
    provenance_sha256_value: str,
    rollback_plan_path: str,
    gates: tuple[GateResult, ...],
) -> DeploymentHandoff:
    """Create a non-deploying deployment handoff."""

    failed = tuple(
        gate.gate_name
        for gate in gates
        if gate.status is GateStatus.FAIL
    )

    rollback_present = bool(
        rollback_plan_path.strip()
    )

    if (
        policy.require_rollback_artifact
        and not rollback_present
    ):
        failed = (
            *failed,
            "rollback_artifact",
        )

    decision = (
        DeploymentHandoffDecision
        .READY_FOR_DEPLOYMENT_HANDOFF
        if not failed
        else DeploymentHandoffDecision.BLOCKED
    )

    reasons = (
        (
            "All supply-chain and evidence gates passed.",
        )
        if not failed
        else tuple(
            f"Failed gate: {gate_name}"
            for gate_name in failed
        )
    )

    return DeploymentHandoff(
        handoff_version=HANDOFF_VERSION,
        release_id=release_id,
        decision=decision,
        source_environment=(
            policy.allowed_promotion_source
        ),
        target_environment=(
            policy.allowed_promotion_target
        ),
        source_revision=source_revision,
        evidence_sha256=evidence_sha256,
        checksum_manifest_sha256=(
            checksum_manifest_sha256
        ),
        sbom_sha256=sbom_sha256_value,
        provenance_sha256=(
            provenance_sha256_value
        ),
        rollback_plan_path=rollback_plan_path,
        deployment_performed=False,
        reasons=reasons,
    )
