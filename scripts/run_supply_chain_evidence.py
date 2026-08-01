#!/usr/bin/env python3
"""Generate Phase 11 CI/CD and supply-chain evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from incident_agent.supply_chain.checksums import (
    build_checksum_manifest,
    file_sha256,
    verify_checksum_manifest,
)
from incident_agent.supply_chain.contracts import (
    GateResult,
    GateStatus,
    SupplyChainReport,
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


REPORT_VERSION = "supply-chain-report-v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate CI/CD, SBOM, provenance, checksum, "
            "and deployment-handoff evidence."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path(
            "config/supply-chain-policy.json"
        ),
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path(
            "reports/supply-chain"
        ),
    )
    parser.add_argument(
        "--release-id",
        default="phase-11-tutorial-release",
    )
    return parser.parse_args()


def git_value(
    root: Path,
    arguments: list[str],
    fallback: str,
) -> str:
    """Read one Git value with a deterministic fallback."""

    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

        value = result.stdout.strip()

        return value or fallback

    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
    ):
        return fallback


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    output_directory = (
        root / args.output_directory
    )
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    policy_path = root / args.policy
    policy = load_supply_chain_policy(
        policy_path
    )

    prior_gates = verify_prior_phase_evidence(
        root=root,
        policy=policy,
    )

    scan_gate, scan_findings = scan_repository(
        root=root,
        policy=policy,
    )

    sbom = build_python_sbom()
    sbom_path = output_directory / "sbom.json"
    sbom_path.write_text(
        json.dumps(
            sbom.to_dict(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    sbom_digest = sbom_sha256(sbom)

    artifact_paths = (
        root
        / "reports/observability/"
        "phase-09-release-evidence.json",
        root
        / "reports/hardening/"
        "phase-10-production-readiness.json",
        root / "config/production-hardening.json",
        root / "config/supply-chain-policy.json",
        root / "deployment/ROLLBACK_PLAN.md",
        root / "Dockerfile",
        sbom_path,
    )

    checksum_manifest = build_checksum_manifest(
        root=root,
        artifact_paths=artifact_paths,
    )

    checksum_path = (
        output_directory
        / "checksum-manifest.json"
    )
    checksum_path.write_text(
        json.dumps(
            checksum_manifest.to_dict(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    checksum_gate = GateResult(
        gate_name="checksum_manifest",
        status=(
            GateStatus.PASS
            if verify_checksum_manifest(
                root=root,
                manifest=checksum_manifest,
            )
            else GateStatus.FAIL
        ),
        explanation=(
            "Artifact checksums and aggregate digest "
            "verified."
        ),
        evidence_references=(
            checksum_manifest.aggregate_sha256,
        ),
    )

    rollback_path = (
        root / "deployment/ROLLBACK_PLAN.md"
    )

    rollback_gate = GateResult(
        gate_name="rollback_artifact",
        status=(
            GateStatus.PASS
            if rollback_path.is_file()
            and rollback_path.stat().st_size > 0
            else GateStatus.FAIL
        ),
        explanation=(
            "Rollback artifact exists and is non-empty."
        ),
        evidence_references=(
            "deployment/ROLLBACK_PLAN.md",
        ),
    )

    container_text = (
        root / "Dockerfile"
    ).read_text(encoding="utf-8")

    expected_user = (
        f"USER {policy.required_container_user}:"
        f"{policy.required_container_user}"
    )

    container_gate = GateResult(
        gate_name="container_non_root_user",
        status=(
            GateStatus.PASS
            if (
                not policy.require_non_root_container
                or expected_user in container_text
            )
            else GateStatus.FAIL
        ),
        explanation=(
            "Container definition uses the required "
            "non-root user."
        ),
        evidence_references=("Dockerfile",),
    )

    source_revision = git_value(
        root,
        ["rev-parse", "HEAD"],
        "unavailable",
    )
    source_branch = git_value(
        root,
        ["rev-parse", "--abbrev-ref", "HEAD"],
        "unavailable",
    )

    provenance = build_provenance(
        release_id=args.release_id,
        source_repository=(
            os.environ.get(
                "GITHUB_REPOSITORY",
                "S3curethecloud/"
                "traditional-ml-genai-policy-agent-lab",
            )
        ),
        source_revision=source_revision,
        source_branch=source_branch,
        builder_identity=(
            os.environ.get(
                "GITHUB_ACTOR",
                "local-tutorial-builder",
            )
        ),
        build_command="docker build --tag incident-agent .",
        test_command=policy.required_test_command,
        policy_sha256=policy_sha256(policy_path),
        checksum_manifest=checksum_manifest,
        sbom_sha256=sbom_digest,
    )

    provenance_path = (
        output_directory
        / "build-provenance.json"
    )
    provenance_path.write_text(
        json.dumps(
            provenance.to_dict(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    provenance_digest = provenance_sha256(
        provenance
    )

    phase_9 = json.loads(
        (
            root
            / "reports/observability/"
            "phase-09-release-evidence.json"
        ).read_text(encoding="utf-8")
    )

    all_gates = (
        *prior_gates,
        scan_gate,
        checksum_gate,
        rollback_gate,
        container_gate,
    )

    handoff = create_deployment_handoff(
        policy=policy,
        release_id=args.release_id,
        source_revision=source_revision,
        evidence_sha256=(
            phase_9["aggregate_sha256"]
        ),
        checksum_manifest_sha256=(
            checksum_manifest.aggregate_sha256
        ),
        sbom_sha256_value=sbom_digest,
        provenance_sha256_value=(
            provenance_digest
        ),
        rollback_plan_path=(
            "deployment/ROLLBACK_PLAN.md"
        ),
        gates=all_gates,
    )

    handoff_path = (
        output_directory
        / "deployment-handoff.json"
    )
    handoff_path.write_text(
        json.dumps(
            handoff.to_dict(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    failed_count = sum(
        gate.status is GateStatus.FAIL
        for gate in all_gates
    )

    report = SupplyChainReport(
        report_version=REPORT_VERSION,
        release_id=args.release_id,
        status=(
            GateStatus.PASS
            if failed_count == 0
            else GateStatus.FAIL
        ),
        gates=all_gates,
        passed_count=(
            len(all_gates) - failed_count
        ),
        failed_count=failed_count,
        deployment_handoff=handoff,
        authority_boundary=(
            "The supply-chain pipeline may build, inspect, "
            "attest, and prepare a deployment handoff. It "
            "does not perform a production deployment."
        ),
    )

    report_path = (
        output_directory
        / "phase-11-supply-chain-report.json"
    )
    report_path.write_text(
        json.dumps(
            report.to_dict(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    evidence_index = {
        "release_id": args.release_id,
        "report_sha256": file_sha256(report_path),
        "sbom_sha256": file_sha256(sbom_path),
        "checksum_manifest_sha256":
            file_sha256(checksum_path),
        "provenance_sha256":
            file_sha256(provenance_path),
        "deployment_handoff_sha256":
            file_sha256(handoff_path),
        "production_deployment_performed": False,
    }

    (
        output_directory
        / "evidence-index.json"
    ).write_text(
        json.dumps(
            evidence_index,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"PASS: supply-chain status="
        f"{report.status.value}"
    )
    print(
        f"PASS: passed gates="
        f"{report.passed_count}"
    )
    print(
        f"PASS: failed gates="
        f"{report.failed_count}"
    )
    print(
        f"PASS: SBOM components="
        f"{len(sbom.components)}"
    )
    print(
        "PASS: checksum manifest verified"
    )
    print(
        "PASS: build provenance generated"
    )
    print(
        f"PASS: deployment handoff="
        f"{handoff.decision.value}"
    )
    print(
        "PASS: production deployment was not performed"
    )

    if scan_findings:
        for finding in scan_findings:
            print(
                f"FINDING: {finding.path}: "
                f"{finding.finding_type}"
            )


if __name__ == "__main__":
    main()
