"""Deterministic software bill of materials generation."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import uuid

from incident_agent.supply_chain.contracts import (
    DependencyComponent,
    SoftwareBillOfMaterials,
)


SBOM_NAMESPACE = uuid.UUID(
    "45935125-9054-4dc1-a9ad-7e29f9db61fc"
)


def build_python_sbom(
    distributions: tuple[
        importlib.metadata.Distribution,
        ...,
    ] | None = None,
) -> SoftwareBillOfMaterials:
    """Build a deterministic Python dependency SBOM."""

    installed = (
        tuple(importlib.metadata.distributions())
        if distributions is None
        else distributions
    )

    components: list[DependencyComponent] = []

    for distribution in installed:
        name = (
            distribution.metadata.get("Name")
            or "unknown"
        )
        version = distribution.version or "unknown"

        normalized_name = name.lower().replace(
            "_",
            "-",
        )

        components.append(
            DependencyComponent(
                name=name,
                version=version,
                component_type="library",
                package_url=(
                    f"pkg:pypi/{normalized_name}"
                    f"@{version}"
                ),
            )
        )

    components.sort(
        key=lambda item: (
            item.name.lower(),
            item.version,
        )
    )

    serial_payload = "|".join(
        f"{item.name}=={item.version}"
        for item in components
    )

    serial = uuid.uuid5(
        SBOM_NAMESPACE,
        serial_payload,
    )

    return SoftwareBillOfMaterials(
        bom_format="CycloneDX",
        spec_version="1.5",
        serial_number=f"urn:uuid:{serial}",
        version=1,
        components=tuple(components),
    )


def sbom_sha256(
    sbom: SoftwareBillOfMaterials,
) -> str:
    """Return the deterministic SBOM digest."""

    canonical = json.dumps(
        sbom.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()
