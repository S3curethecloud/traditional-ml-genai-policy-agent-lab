"""Signed release attestations for promotion evidence."""

from __future__ import annotations

import hashlib
import hmac
import json

from incident_agent.hardening.contracts import (
    ReleaseAttestation,
)


SIGNATURE_ALGORITHM = "HMAC-SHA256"


def create_release_attestation(
    release_id: str,
    source_environment: str,
    target_environment: str,
    evidence_sha256: str,
    configuration_sha256: str,
    rollback_plan_id: str,
    signer_id: str,
    signing_key: str,
) -> ReleaseAttestation:
    """Create a signed release attestation."""

    unsigned = {
        "release_id": release_id,
        "source_environment": source_environment,
        "target_environment": target_environment,
        "evidence_sha256": evidence_sha256,
        "configuration_sha256":
            configuration_sha256,
        "rollback_plan_id": rollback_plan_id,
        "signer_id": signer_id,
        "signature_algorithm":
            SIGNATURE_ALGORITHM,
    }

    signature = _signature(
        payload=unsigned,
        signing_key=signing_key,
    )

    return ReleaseAttestation(
        release_id=release_id,
        source_environment=source_environment,
        target_environment=target_environment,
        evidence_sha256=evidence_sha256,
        configuration_sha256=(
            configuration_sha256
        ),
        rollback_plan_id=rollback_plan_id,
        signer_id=signer_id,
        signature_algorithm=SIGNATURE_ALGORITHM,
        signature=signature,
    )


def verify_release_attestation(
    attestation: ReleaseAttestation,
    signing_key: str,
) -> bool:
    """Verify an HMAC release attestation."""

    if (
        attestation.signature_algorithm
        != SIGNATURE_ALGORITHM
    ):
        return False

    unsigned = {
        "release_id": attestation.release_id,
        "source_environment":
            attestation.source_environment,
        "target_environment":
            attestation.target_environment,
        "evidence_sha256":
            attestation.evidence_sha256,
        "configuration_sha256":
            attestation.configuration_sha256,
        "rollback_plan_id":
            attestation.rollback_plan_id,
        "signer_id": attestation.signer_id,
        "signature_algorithm":
            attestation.signature_algorithm,
    }

    expected = _signature(
        payload=unsigned,
        signing_key=signing_key,
    )

    return hmac.compare_digest(
        expected,
        attestation.signature,
    )


def _signature(
    payload: dict[str, str],
    signing_key: str,
) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hmac.new(
        signing_key.encode("utf-8"),
        canonical,
        hashlib.sha256,
    ).hexdigest()
