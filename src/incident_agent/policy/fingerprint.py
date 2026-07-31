"""Canonical policy-request fingerprinting."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from incident_agent.genai.contracts import SynthesisResponse
from incident_agent.policy.contracts import PolicyContext


def build_request_fingerprint(
    synthesis: SynthesisResponse,
    context: PolicyContext,
) -> str:
    """Create a stable SHA-256 policy-input fingerprint."""

    payload = {
        "synthesis": asdict(synthesis),
        "context": asdict(context),
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()
