"""Load and normalize final release-closure artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from incident_agent.release_closure.contracts import (
    AuthorityRestriction,
    EvidenceRecord,
    RecoveryCapability,
    ReleaseCandidate,
    ReleaseGate,
    ResidualRisk,
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_sha256(payload: Any) -> str:
    material = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(material).hexdigest()


def load_closure_policy(path: Path) -> dict[str, Any]:
    payload = _load_json(path)

    if not payload.get("policy_version"):
        raise ValueError("Policy version is required")

    if not payload.get("platform_contract_version"):
        raise ValueError(
            "Platform contract version is required"
        )

    prohibited_flags = (
        "automatic_release_approval_allowed",
        "automatic_deployment_allowed",
        "automatic_traffic_shift_allowed",
        "automatic_exception_approval_allowed",
        "automatic_risk_acceptance_allowed",
        "production_authority_transfer_allowed",
    )

    for flag in prohibited_flags:
        if payload.get(flag) is not False:
            raise ValueError(f"{flag} must remain false")

    return payload


def load_release_candidate(path: Path) -> ReleaseCandidate:
    payload = _load_json(path)

    domain_digests = tuple(
        sorted(
            payload["domain_pack_digests"].items()
        )
    )

    return ReleaseCandidate(
        release_id=payload["release_id"],
        release_version=payload["release_version"],
        platform_contract_version=payload[
            "platform_contract_version"
        ],
        source_branch=payload["source_branch"],
        candidate_status=payload["candidate_status"],
        artifact_digest=payload["artifact_digest"],
        configuration_digest=payload[
            "configuration_digest"
        ],
        policy_digest=payload["policy_digest"],
        domain_pack_digests=domain_digests,
        target_environment=payload["target_environment"],
        deployment_performed=bool(
            payload["deployment_performed"]
        ),
        traffic_shift_performed=bool(
            payload["traffic_shift_performed"]
        ),
        production_activation_performed=bool(
            payload["production_activation_performed"]
        ),
        human_production_approval_required=bool(
            payload[
                "human_production_approval_required"
            ]
        ),
        immutable=bool(payload["immutable"]),
        manifest_digest=canonical_sha256(payload),
    )


def load_evidence_registry(
    path: Path,
) -> tuple[
    str,
    tuple[EvidenceRecord, ...],
    dict[str, bool],
]:
    payload = _load_json(path)

    evidence = tuple(
        EvidenceRecord(
            evidence_id=item["evidence_id"],
            phase=int(item["phase"]),
            path=item["path"],
            required=bool(item["required"]),
            validated=bool(item["validated"]),
            decision=item["decision"],
        )
        for item in payload["evidence"]
    )

    flags = {
        "evidence_mutated": bool(
            payload["evidence_mutated"]
        ),
        "evidence_deleted": bool(
            payload["evidence_deleted"]
        ),
        "evidence_substituted": bool(
            payload["evidence_substituted"]
        ),
    }

    return payload["registry_id"], evidence, flags


def load_release_gates(
    path: Path,
) -> tuple[str, tuple[ReleaseGate, ...]]:
    payload = _load_json(path)

    gates = tuple(
        ReleaseGate(
            gate_id=item["gate_id"],
            passed=bool(item["passed"]),
            evidence_id=item["evidence_id"],
        )
        for item in payload["gates"]
    )

    return payload["gate_set_id"], gates


def load_risk_closure(
    path: Path,
) -> tuple[
    str,
    tuple[ResidualRisk, ...],
    dict[str, int | bool],
]:
    payload = _load_json(path)

    risks = tuple(
        ResidualRisk(
            risk_id=item["risk_id"],
            severity=item["severity"],
            status=item["status"],
            mitigation=item["mitigation"],
        )
        for item in payload["residual_risks"]
    )

    values: dict[str, int | bool] = {
        "open_critical_risks": int(
            payload["open_critical_risks"]
        ),
        "open_high_risks": int(
            payload["open_high_risks"]
        ),
        "approved_exceptions": int(
            payload["approved_exceptions"]
        ),
        "automatically_accepted_risks": int(
            payload["automatically_accepted_risks"]
        ),
        "automatically_approved_exceptions": int(
            payload[
                "automatically_approved_exceptions"
            ]
        ),
        "risk_acceptance_performed": bool(
            payload["risk_acceptance_performed"]
        ),
        "exception_approval_performed": bool(
            payload["exception_approval_performed"]
        ),
    }

    return payload["register_id"], risks, values


def load_recovery_closure(
    path: Path,
) -> tuple[
    str,
    tuple[RecoveryCapability, ...],
    dict[str, bool],
]:
    payload = _load_json(path)

    capabilities = tuple(
        RecoveryCapability(
            capability=item["capability"],
            verified=bool(item["verified"]),
            evidence=item["evidence"],
            automatic_execution=bool(
                item["automatic_execution"]
            ),
        )
        for item in payload["capabilities"]
    )

    flags = {
        "real_rollback_performed": bool(
            payload["real_rollback_performed"]
        ),
        "real_restore_performed": bool(
            payload["real_restore_performed"]
        ),
        "real_failover_performed": bool(
            payload["real_failover_performed"]
        ),
        "production_state_changed": bool(
            payload["production_state_changed"]
        ),
    }

    return payload["closure_id"], capabilities, flags


def load_authority_boundary(
    path: Path,
) -> tuple[
    str,
    tuple[AuthorityRestriction, ...],
    dict[str, bool],
]:
    payload = _load_json(path)

    restrictions = tuple(
        AuthorityRestriction(
            restriction=item["restriction"],
            preserved=bool(item["preserved"]),
        )
        for item in payload["restrictions"]
    )

    flags = {
        "production_approval_required": bool(
            payload["production_approval_required"]
        ),
        "production_approver_assigned": bool(
            payload["production_approver_assigned"]
        ),
        "deployment_credentials_created": bool(
            payload["deployment_credentials_created"]
        ),
        "deployment_credentials_used": bool(
            payload["deployment_credentials_used"]
        ),
        "production_access_granted": bool(
            payload["production_access_granted"]
        ),
        "production_authority_transferred": bool(
            payload[
                "production_authority_transferred"
            ]
        ),
    }

    return payload["boundary_id"], restrictions, flags
