"""Tamper-evident release evidence bundle generation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from incident_agent.observability.contracts import (
    EvaluationSummary,
    EvidenceArtifact,
    ReleaseEvidenceBundle,
)
from incident_agent.observability.evaluator import (
    failed_metric_names,
    release_gate_passed,
)


BUNDLE_VERSION = "release-evidence-bundle-v1"


def sha256_bytes(data: bytes) -> str:
    """Return a SHA-256 digest."""

    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(
    payload: Any,
) -> bytes:
    """Serialize JSON deterministically."""

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def build_release_evidence_bundle(
    release_id: str,
    summary: EvaluationSummary,
    artifact_payloads: dict[str, Any],
) -> ReleaseEvidenceBundle:
    """Build a tamper-evident evidence manifest."""

    artifacts: list[EvidenceArtifact] = []

    evaluation_payload = summary.to_dict()

    combined_payloads = {
        "evaluation-summary.json":
            evaluation_payload,
        **artifact_payloads,
    }

    for artifact_name, payload in sorted(
        combined_payloads.items()
    ):
        digest = sha256_bytes(
            canonical_json_bytes(payload)
        )

        artifacts.append(
            EvidenceArtifact(
                artifact_name=artifact_name,
                artifact_type="application/json",
                sha256=digest,
                description=(
                    "Governed Phase 9 evaluation evidence."
                ),
            )
        )

    aggregate_payload = [
        asdict(artifact)
        for artifact in artifacts
    ]

    return ReleaseEvidenceBundle(
        bundle_version=BUNDLE_VERSION,
        release_id=release_id,
        evaluation_version=(
            summary.evaluation_version
        ),
        artifact_count=len(artifacts),
        artifacts=tuple(artifacts),
        aggregate_sha256=sha256_bytes(
            canonical_json_bytes(
                aggregate_payload
            )
        ),
        release_gate_passed=release_gate_passed(
            summary
        ),
        failed_metric_names=failed_metric_names(
            summary
        ),
        authority_boundary=(
            "The evidence bundle records release evidence. "
            "It cannot waive a failed metric, authorize a "
            "deployment, or modify source outcomes."
        ),
    )


def write_evidence_bundle(
    path: Path,
    bundle: ReleaseEvidenceBundle,
) -> None:
    """Write a release evidence bundle as JSON."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            bundle.to_dict(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
