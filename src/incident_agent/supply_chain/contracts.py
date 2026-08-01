"""Typed contracts for CI/CD and supply-chain evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class GateStatus(StrEnum):
    """Status of a CI or release gate."""

    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DeploymentHandoffDecision(StrEnum):
    """Decision produced for a deployment system."""

    READY_FOR_DEPLOYMENT_HANDOFF = (
        "READY_FOR_DEPLOYMENT_HANDOFF"
    )
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class SupplyChainPolicy:
    """Validated supply-chain policy."""

    policy_version: str
    required_test_command: str
    required_python_version: str
    required_evidence_files: tuple[str, ...]
    required_release_gate_status: bool
    required_readiness_status: str
    required_promotion_decision: str
    required_container_user: str
    maximum_container_size_mb: int
    require_non_root_container: bool
    require_sbom: bool
    require_checksum_manifest: bool
    require_build_provenance: bool
    require_rollback_artifact: bool
    require_deployment_handoff: bool
    prohibited_file_patterns: tuple[str, ...]
    prohibited_secret_markers: tuple[str, ...]
    allowed_promotion_source: str
    allowed_promotion_target: str


@dataclass(frozen=True)
class GateResult:
    """One pipeline gate result."""

    gate_name: str
    status: GateStatus
    explanation: str
    evidence_references: tuple[str, ...] = ()


@dataclass(frozen=True)
class DependencyComponent:
    """One dependency recorded in the SBOM."""

    name: str
    version: str
    component_type: str
    package_url: str


@dataclass(frozen=True)
class SoftwareBillOfMaterials:
    """Minimal deterministic CycloneDX-compatible SBOM."""

    bom_format: str
    spec_version: str
    serial_number: str
    version: int
    components: tuple[DependencyComponent, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return {
            "bomFormat": self.bom_format,
            "specVersion": self.spec_version,
            "serialNumber": self.serial_number,
            "version": self.version,
            "components": [
                {
                    "type": component.component_type,
                    "name": component.name,
                    "version": component.version,
                    "purl": component.package_url,
                }
                for component in self.components
            ],
        }


@dataclass(frozen=True)
class ArtifactChecksum:
    """Checksum for one release artifact."""

    path: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class ChecksumManifest:
    """Deterministic artifact checksum manifest."""

    manifest_version: str
    artifacts: tuple[ArtifactChecksum, ...]
    aggregate_sha256: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)


@dataclass(frozen=True)
class BuildProvenance:
    """Build provenance for a release candidate."""

    provenance_version: str
    release_id: str
    source_repository: str
    source_revision: str
    source_branch: str
    builder_identity: str
    build_command: str
    test_command: str
    policy_sha256: str
    checksum_manifest_sha256: str
    sbom_sha256: str
    production_deployment_performed: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)


@dataclass(frozen=True)
class DeploymentHandoff:
    """Contract passed to a separate deployment system."""

    handoff_version: str
    release_id: str
    decision: DeploymentHandoffDecision
    source_environment: str
    target_environment: str
    source_revision: str
    evidence_sha256: str
    checksum_manifest_sha256: str
    sbom_sha256: str
    provenance_sha256: str
    rollback_plan_path: str
    deployment_performed: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)


@dataclass(frozen=True)
class SupplyChainReport:
    """Aggregate CI/CD and supply-chain report."""

    report_version: str
    release_id: str
    status: GateStatus
    gates: tuple[GateResult, ...]
    passed_count: int
    failed_count: int
    deployment_handoff: DeploymentHandoff
    authority_boundary: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)
