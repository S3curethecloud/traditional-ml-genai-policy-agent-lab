"""Tests for Phase 11 CI/CD and supply-chain controls."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from incident_agent.supply_chain.checksums import (
    build_checksum_manifest,
    verify_checksum_manifest,
)
from incident_agent.supply_chain.contracts import (
    GateResult,
    GateStatus,
    SupplyChainPolicy,
)
from incident_agent.supply_chain.policy import (
    load_supply_chain_policy,
    policy_sha256,
)
from incident_agent.supply_chain.provenance import (
    build_provenance,
    create_deployment_handoff,
    provenance_sha256,
)
from incident_agent.supply_chain.sbom import (
    build_python_sbom,
    sbom_sha256,
)
from incident_agent.supply_chain.scanning import (
    scan_repository,
)
from incident_agent.supply_chain.verification import (
    verify_prior_phase_evidence,
)


ROOT = Path(".")
POLICY_PATH = Path(
    "config/supply-chain-policy.json"
)


def policy() -> SupplyChainPolicy:
    return load_supply_chain_policy(
        POLICY_PATH
    )


def passing_gate(
    name: str = "test-gate",
) -> GateResult:
    return GateResult(
        gate_name=name,
        status=GateStatus.PASS,
        explanation="Gate passed.",
    )


def test_supply_chain_policy_loads() -> None:
    loaded = policy()

    assert (
        loaded.policy_version
        == "supply-chain-policy-v1"
    )
    assert loaded.require_sbom
    assert loaded.require_build_provenance
    assert loaded.require_deployment_handoff


def test_policy_digest_is_reproducible() -> None:
    first = policy_sha256(POLICY_PATH)
    second = policy_sha256(POLICY_PATH)

    assert first == second
    assert len(first) == 64


def test_invalid_container_size_is_rejected(
    tmp_path,
) -> None:
    payload = json.loads(
        POLICY_PATH.read_text(
            encoding="utf-8"
        )
    )
    payload["maximum_container_size_mb"] = 0

    path = tmp_path / "policy.json"
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="maximum_container_size_mb",
    ):
        load_supply_chain_policy(path)


def test_repository_scan_passes() -> None:
    gate, findings = scan_repository(
        root=ROOT,
        policy=policy(),
    )

    assert gate.status is GateStatus.PASS
    assert not findings


def test_repository_scan_detects_secret_marker(
    tmp_path,
) -> None:
    (tmp_path / "unsafe.txt").write_text(
        "BEGIN PRIVATE KEY",
        encoding="utf-8",
    )

    gate, findings = scan_repository(
        root=tmp_path,
        policy=policy(),
    )

    assert gate.status is GateStatus.FAIL
    assert findings


def test_repository_scan_detects_prohibited_file(
    tmp_path,
) -> None:
    (tmp_path / ".env").write_text(
        "DEMO_SETTING=true",
        encoding="utf-8",
    )

    gate, findings = scan_repository(
        root=tmp_path,
        policy=policy(),
    )

    assert gate.status is GateStatus.FAIL
    assert any(
        finding.finding_type
        == "prohibited_file_pattern"
        for finding in findings
    )


def test_sbom_has_cyclonedx_shape() -> None:
    sbom = build_python_sbom()
    payload = sbom.to_dict()

    assert payload["bomFormat"] == "CycloneDX"
    assert payload["specVersion"] == "1.5"
    assert payload["serialNumber"].startswith(
        "urn:uuid:"
    )
    assert payload["components"]


def test_sbom_is_reproducible() -> None:
    first = build_python_sbom()
    second = build_python_sbom()

    assert first.to_dict() == second.to_dict()
    assert sbom_sha256(first) == sbom_sha256(
        second
    )


def test_sbom_digest_has_sha256_length() -> None:
    digest = sbom_sha256(
        build_python_sbom()
    )

    assert len(digest) == 64


def test_checksum_manifest_verifies(
    tmp_path,
) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"

    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")

    manifest = build_checksum_manifest(
        root=tmp_path,
        artifact_paths=(first, second),
    )

    assert verify_checksum_manifest(
        root=tmp_path,
        manifest=manifest,
    )


def test_checksum_manifest_detects_tampering(
    tmp_path,
) -> None:
    artifact = tmp_path / "artifact.txt"
    artifact.write_text(
        "original",
        encoding="utf-8",
    )

    manifest = build_checksum_manifest(
        root=tmp_path,
        artifact_paths=(artifact,),
    )

    artifact.write_text(
        "tampered",
        encoding="utf-8",
    )

    assert not verify_checksum_manifest(
        root=tmp_path,
        manifest=manifest,
    )


def test_checksum_manifest_is_reproducible(
    tmp_path,
) -> None:
    artifact = tmp_path / "artifact.txt"
    artifact.write_text(
        "stable",
        encoding="utf-8",
    )

    first = build_checksum_manifest(
        root=tmp_path,
        artifact_paths=(artifact,),
    )
    second = build_checksum_manifest(
        root=tmp_path,
        artifact_paths=(artifact,),
    )

    assert (
        first.aggregate_sha256
        == second.aggregate_sha256
    )


def test_prior_phase_evidence_passes() -> None:
    gates = verify_prior_phase_evidence(
        root=ROOT,
        policy=policy(),
    )

    assert gates
    assert all(
        gate.status is GateStatus.PASS
        for gate in gates
    )


def test_missing_prior_evidence_fails(
    tmp_path,
) -> None:
    gates = verify_prior_phase_evidence(
        root=tmp_path,
        policy=policy(),
    )

    assert gates[0].status is GateStatus.FAIL


def test_provenance_records_no_deployment(
    tmp_path,
) -> None:
    artifact = tmp_path / "artifact.txt"
    artifact.write_text(
        "artifact",
        encoding="utf-8",
    )

    manifest = build_checksum_manifest(
        root=tmp_path,
        artifact_paths=(artifact,),
    )

    provenance = build_provenance(
        release_id="release-test",
        source_repository="owner/repository",
        source_revision="abc123",
        source_branch="main",
        builder_identity="ci",
        build_command="docker build .",
        test_command="pytest",
        policy_sha256="a" * 64,
        checksum_manifest=manifest,
        sbom_sha256="b" * 64,
    )

    assert not (
        provenance.production_deployment_performed
    )
    assert len(provenance_sha256(provenance)) == 64


def test_provenance_digest_is_reproducible(
    tmp_path,
) -> None:
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("x", encoding="utf-8")

    manifest = build_checksum_manifest(
        root=tmp_path,
        artifact_paths=(artifact,),
    )

    first = build_provenance(
        "release",
        "owner/repo",
        "revision",
        "main",
        "builder",
        "build",
        "test",
        "a" * 64,
        manifest,
        "b" * 64,
    )
    second = build_provenance(
        "release",
        "owner/repo",
        "revision",
        "main",
        "builder",
        "build",
        "test",
        "a" * 64,
        manifest,
        "b" * 64,
    )

    assert provenance_sha256(
        first
    ) == provenance_sha256(second)


def test_passing_gates_create_ready_handoff() -> None:
    handoff = create_deployment_handoff(
        policy=policy(),
        release_id="release-test",
        source_revision="abc123",
        evidence_sha256="a" * 64,
        checksum_manifest_sha256="b" * 64,
        sbom_sha256_value="c" * 64,
        provenance_sha256_value="d" * 64,
        rollback_plan_path=(
            "deployment/ROLLBACK_PLAN.md"
        ),
        gates=(
            passing_gate("evidence"),
            passing_gate("scan"),
        ),
    )

    assert (
        handoff.decision.value
        == "READY_FOR_DEPLOYMENT_HANDOFF"
    )
    assert not handoff.deployment_performed


def test_failed_gate_blocks_handoff() -> None:
    failed = replace(
        passing_gate("secret-scan"),
        status=GateStatus.FAIL,
    )

    handoff = create_deployment_handoff(
        policy=policy(),
        release_id="release-test",
        source_revision="abc123",
        evidence_sha256="a" * 64,
        checksum_manifest_sha256="b" * 64,
        sbom_sha256_value="c" * 64,
        provenance_sha256_value="d" * 64,
        rollback_plan_path=(
            "deployment/ROLLBACK_PLAN.md"
        ),
        gates=(failed,),
    )

    assert handoff.decision.value == "BLOCKED"
    assert any(
        "secret-scan" in reason
        for reason in handoff.reasons
    )


def test_missing_rollback_path_blocks_handoff() -> None:
    handoff = create_deployment_handoff(
        policy=policy(),
        release_id="release-test",
        source_revision="abc123",
        evidence_sha256="a" * 64,
        checksum_manifest_sha256="b" * 64,
        sbom_sha256_value="c" * 64,
        provenance_sha256_value="d" * 64,
        rollback_plan_path="",
        gates=(passing_gate(),),
    )

    assert handoff.decision.value == "BLOCKED"


def test_handoff_preserves_promotion_path() -> None:
    loaded = policy()

    handoff = create_deployment_handoff(
        policy=loaded,
        release_id="release-test",
        source_revision="abc123",
        evidence_sha256="a" * 64,
        checksum_manifest_sha256="b" * 64,
        sbom_sha256_value="c" * 64,
        provenance_sha256_value="d" * 64,
        rollback_plan_path=(
            "deployment/ROLLBACK_PLAN.md"
        ),
        gates=(passing_gate(),),
    )

    assert (
        handoff.source_environment
        == loaded.allowed_promotion_source
    )
    assert (
        handoff.target_environment
        == loaded.allowed_promotion_target
    )


def test_dockerfile_uses_non_root_user() -> None:
    content = Path("Dockerfile").read_text(
        encoding="utf-8"
    )

    assert "USER 10001:10001" in content


def test_rollback_plan_exists() -> None:
    path = Path(
        "deployment/ROLLBACK_PLAN.md"
    )

    assert path.is_file()
    assert path.stat().st_size > 0
    assert "does not execute a rollback" in (
        path.read_text(encoding="utf-8")
    )


def test_scanner_exclusions_do_not_hide_other_files(
    tmp_path,
) -> None:
    config_directory = tmp_path / "config"
    test_directory = (
        tmp_path
        / "tests"
        / "unit"
        / "supply_chain"
    )

    config_directory.mkdir(parents=True)
    test_directory.mkdir(parents=True)

    (
        config_directory
        / "supply-chain-policy.json"
    ).write_text(
        json.dumps(
            {
                "prohibited_secret_markers": [
                    "BEGIN PRIVATE KEY"
                ]
            }
        ),
        encoding="utf-8",
    )

    (
        test_directory
        / "test_supply_chain.py"
    ).write_text(
        '"BEGIN PRIVATE KEY"',
        encoding="utf-8",
    )

    (
        tmp_path
        / "application.py"
    ).write_text(
        '"BEGIN PRIVATE KEY"',
        encoding="utf-8",
    )

    gate, findings = scan_repository(
        root=tmp_path,
        policy=policy(),
    )

    assert gate.status is GateStatus.FAIL
    assert len(findings) == 1
    assert findings[0].path == "application.py"
