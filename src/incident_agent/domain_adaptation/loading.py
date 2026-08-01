"""Load and normalize reusable domain adaptation packs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from incident_agent.domain_adaptation.contracts import (
    DomainPack,
    DomainTool,
    EvidenceSource,
    IncidentCategory,
)


def canonical_sha256(payload: Any) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()


def load_adaptation_policy(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not payload.get("policy_version"):
        raise ValueError("Policy version is required")

    if not payload.get("platform_contract_version"):
        raise ValueError(
            "Platform contract version is required"
        )

    prohibited_flags = (
        "automatic_pack_activation_allowed",
        "automatic_policy_mutation_allowed",
        "automatic_tool_registration_allowed",
        "production_changes_allowed",
    )

    for flag in prohibited_flags:
        if payload.get(flag) is not False:
            raise ValueError(
                f"{flag} must remain false"
            )

    return payload


def load_domain_pack(path: Path) -> DomainPack:
    payload = json.loads(path.read_text(encoding="utf-8"))

    metadata = payload["metadata"]
    domain = payload["domain"]
    taxonomy = payload["incident_taxonomy"]
    overlay = payload["policy_overlay"]
    evaluation = payload["evaluation_profile"]
    deployment = payload["deployment_profile"]
    boundary = payload["authority_boundary"]

    categories = tuple(
        IncidentCategory(
            category_id=item["category_id"],
            display_name=item["display_name"],
            default_severity=item["default_severity"],
        )
        for item in taxonomy["categories"]
    )

    sources = tuple(
        EvidenceSource(
            source_id=item["source_id"],
            source_type=item["source_type"],
            tenant_scoped=bool(item["tenant_scoped"]),
            required_roles=tuple(item["required_roles"]),
        )
        for item in payload["evidence_sources"]
    )

    tools = tuple(
        DomainTool(
            tool_name=item["tool_name"],
            risk=item["risk"],
            mutating=bool(item["mutating"]),
            allowed_environments=tuple(
                item["allowed_environments"]
            ),
            required_approval=bool(
                item["required_approval"]
            ),
        )
        for item in payload["tool_catalog"]
    )

    return DomainPack(
        pack_id=metadata["pack_id"],
        pack_version=metadata["pack_version"],
        platform_contract_version=metadata[
            "platform_contract_version"
        ],
        status=metadata["status"],
        owner=metadata["owner"],
        domain_name=domain["name"],
        description=domain["description"],
        tenant_isolation_required=bool(
            domain["tenant_isolation_required"]
        ),
        regulated_data=bool(domain["regulated_data"]),
        supported_capabilities=tuple(
            domain["supported_capabilities"]
        ),
        incident_categories=categories,
        evidence_sources=sources,
        tools=tools,
        may_narrow_platform_policy=bool(
            overlay["may_narrow_platform_policy"]
        ),
        may_expand_platform_policy=bool(
            overlay["may_expand_platform_policy"]
        ),
        deny_cross_tenant_access=bool(
            overlay["deny_cross_tenant_access"]
        ),
        deny_unapproved_production_mutation=bool(
            overlay[
                "deny_unapproved_production_mutation"
            ]
        ),
        deny_direct_genai_tool_execution=bool(
            overlay["deny_direct_genai_tool_execution"]
        ),
        required_evaluation_cases=tuple(
            evaluation["required_cases"]
        ),
        minimum_pass_rate_percentage=float(
            evaluation["minimum_pass_rate_percentage"]
        ),
        allowed_deployment_environments=tuple(
            deployment["allowed_environments"]
        ),
        production_activation_requires_human_approval=bool(
            deployment[
                "production_activation_requires_human_approval"
            ]
        ),
        automatic_activation=bool(
            deployment["automatic_activation"]
        ),
        domain_pack_can_execute_tools=bool(
            boundary["domain_pack_can_execute_tools"]
        ),
        domain_pack_can_modify_platform_policy=bool(
            boundary[
                "domain_pack_can_modify_platform_policy"
            ]
        ),
        domain_pack_can_approve_exceptions=bool(
            boundary[
                "domain_pack_can_approve_exceptions"
            ]
        ),
        domain_pack_can_activate_itself=bool(
            boundary["domain_pack_can_activate_itself"]
        ),
        digest=canonical_sha256(payload),
    )
