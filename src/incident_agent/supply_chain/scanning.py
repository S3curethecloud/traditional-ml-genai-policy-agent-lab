"""Repository source and secret scanning."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path

from incident_agent.supply_chain.contracts import (
    GateResult,
    GateStatus,
    SupplyChainPolicy,
)


TEXT_SUFFIXES = {
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class ScanFinding:
    """One source-scan finding."""

    path: str
    finding_type: str
    detail: str


def scan_repository(
    root: Path,
    policy: SupplyChainPolicy,
) -> tuple[GateResult, tuple[ScanFinding, ...]]:
    """Scan source files for prohibited names and markers."""

    findings: list[ScanFinding] = []

    ignored_parts = {
        ".git",
        ".pytest_cache",
        ".venv",
        "__pycache__",
        "build",
    }

    marker_scan_exclusions = {
        "config/supply-chain-policy.json",
        "tests/unit/supply_chain/"
        "test_supply_chain.py",
    }

    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)

        if any(
            part in ignored_parts
            for part in relative.parts
        ):
            continue

        if not path.is_file():
            continue

        relative_text = relative.as_posix()

        for pattern in policy.prohibited_file_patterns:
            if fnmatch.fnmatch(
                path.name,
                pattern,
            ) or fnmatch.fnmatch(
                relative_text,
                pattern,
            ):
                findings.append(
                    ScanFinding(
                        path=relative_text,
                        finding_type=(
                            "prohibited_file_pattern"
                        ),
                        detail=pattern,
                    )
                )

        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue

        if relative_text in marker_scan_exclusions:
            continue

        try:
            content = path.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError:
            continue

        lowered = content.lower()

        for marker in policy.prohibited_secret_markers:
            if marker.lower() in lowered:
                findings.append(
                    ScanFinding(
                        path=relative_text,
                        finding_type=(
                            "prohibited_secret_marker"
                        ),
                        detail=marker,
                    )
                )

    status = (
        GateStatus.PASS
        if not findings
        else GateStatus.FAIL
    )

    return (
        GateResult(
            gate_name="repository_secret_scan",
            status=status,
            explanation=(
                "No prohibited secret markers or file "
                "patterns were detected."
                if not findings
                else (
                    f"Detected {len(findings)} prohibited "
                    "repository finding(s)."
                )
            ),
            evidence_references=tuple(
                finding.path
                for finding in findings
            ),
        ),
        tuple(findings),
    )
