"""Release artifact checksum generation and verification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from incident_agent.supply_chain.contracts import (
    ArtifactChecksum,
    ChecksumManifest,
)


MANIFEST_VERSION = "checksum-manifest-v1"


def file_sha256(
    path: Path,
) -> str:
    """Return the SHA-256 digest of a file."""

    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(65536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def build_checksum_manifest(
    root: Path,
    artifact_paths: tuple[Path, ...],
) -> ChecksumManifest:
    """Create a deterministic artifact checksum manifest."""

    artifacts: list[ArtifactChecksum] = []

    for path in sorted(
        artifact_paths,
        key=lambda item: item.as_posix(),
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

        relative = path.relative_to(root).as_posix()

        artifacts.append(
            ArtifactChecksum(
                path=relative,
                sha256=file_sha256(path),
                size_bytes=path.stat().st_size,
            )
        )

    canonical_artifacts = [
        {
            "path": item.path,
            "sha256": item.sha256,
            "size_bytes": item.size_bytes,
        }
        for item in artifacts
    ]

    aggregate = hashlib.sha256(
        json.dumps(
            canonical_artifacts,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    return ChecksumManifest(
        manifest_version=MANIFEST_VERSION,
        artifacts=tuple(artifacts),
        aggregate_sha256=aggregate,
    )


def verify_checksum_manifest(
    root: Path,
    manifest: ChecksumManifest,
) -> bool:
    """Verify every artifact in a checksum manifest."""

    for artifact in manifest.artifacts:
        path = root / artifact.path

        if not path.is_file():
            return False

        if path.stat().st_size != artifact.size_bytes:
            return False

        if file_sha256(path) != artifact.sha256:
            return False

    rebuilt = build_checksum_manifest(
        root=root,
        artifact_paths=tuple(
            root / artifact.path
            for artifact in manifest.artifacts
        ),
    )

    return (
        rebuilt.aggregate_sha256
        == manifest.aggregate_sha256
    )
