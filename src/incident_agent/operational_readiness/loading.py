"""Load and validate Phase 19 operational-readiness inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from incident_agent.operational_readiness.contracts import (
    AccessControl,
    HandoffCheck,
    OwnershipAssignment,
    Runbook,
    SupportTier,
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_readiness_policy(path: Path) -> dict[str, Any]:
    payload = _load_json(path)

    if not payload.get("policy_version"):
        raise ValueError("Policy version is required")

    if not payload.get("platform_contract_version"):
        raise ValueError(
            "Platform contract version is required"
        )

    prohibited_flags = (
        "automatic_handoff_allowed",
        "automatic_access_provisioning_allowed",
        "automatic_owner_assignment_allowed",
        "automatic_production_activation_allowed",
    )

    for flag in prohibited_flags:
        if payload.get(flag) is not False:
            raise ValueError(f"{flag} must remain false")

    percentage_fields = (
        "minimum_check_pass_rate_percentage",
        "minimum_runbook_coverage_percentage",
        "minimum_owner_coverage_percentage",
        "minimum_evidence_coverage_percentage",
    )

    for field_name in percentage_fields:
        value = payload.get(field_name)

        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not 0.0 <= float(value) <= 100.0
        ):
            raise ValueError(
                f"{field_name} must be between 0 and 100"
            )

    return payload


def load_ownership_model(
    path: Path,
) -> tuple[
    str,
    tuple[OwnershipAssignment, ...],
    tuple[SupportTier, ...],
    dict[str, bool],
]:
    payload = _load_json(path)

    assignments = tuple(
        OwnershipAssignment(
            capability=item["capability"],
            accountable_role=item["accountable_role"],
            responsible_role=item["responsible_role"],
            consulted_roles=tuple(
                item["consulted_roles"]
            ),
            informed_roles=tuple(
                item["informed_roles"]
            ),
        )
        for item in payload["capabilities"]
    )

    tiers = tuple(
        SupportTier(
            tier=item["tier"],
            role=item["role"],
            responsibility=item["responsibility"],
            may_execute_production_tools=bool(
                item["may_execute_production_tools"]
            ),
        )
        for item in payload["support_tiers"]
    )

    flags = {
        "automatic_owner_assignment": bool(
            payload["automatic_owner_assignment"]
        ),
        "real_people_assigned": bool(
            payload["real_people_assigned"]
        ),
        "production_authority_transferred": bool(
            payload["production_authority_transferred"]
        ),
    }

    return payload["model_id"], assignments, tiers, flags


def load_runbook_catalog(
    path: Path,
) -> tuple[str, tuple[Runbook, ...]]:
    payload = _load_json(path)

    runbooks = tuple(
        Runbook(
            runbook_id=item["runbook_id"],
            owner_role=item["owner_role"],
            trigger=item["trigger"],
            first_action=item["first_action"],
            escalation_role=item["escalation_role"],
            production_mutation_allowed=bool(
                item["production_mutation_allowed"]
            ),
        )
        for item in payload["runbooks"]
    )

    return payload["catalog_id"], runbooks


def load_access_profile(
    path: Path,
) -> tuple[
    str,
    tuple[AccessControl, ...],
    dict[str, bool],
]:
    payload = _load_json(path)

    controls = tuple(
        AccessControl(
            control_id=item["control_id"],
            implemented=bool(item["implemented"]),
            detail=item["detail"],
        )
        for item in payload["controls"]
    )

    flags = {
        "credentials_created": bool(
            payload["credentials_created"]
        ),
        "access_granted": bool(
            payload["access_granted"]
        ),
        "production_roles_assigned": bool(
            payload["production_roles_assigned"]
        ),
        "break_glass_access_activated": bool(
            payload["break_glass_access_activated"]
        ),
    }

    return payload["profile_id"], controls, flags


def load_handoff_checklist(
    path: Path,
) -> tuple[str, tuple[HandoffCheck, ...]]:
    payload = _load_json(path)

    checks = tuple(
        HandoffCheck(
            check_id=item["check_id"],
            category=item["category"],
            required=bool(item["required"]),
            passed=bool(item["passed"]),
            evidence_id=item["evidence_id"],
        )
        for item in payload["checks"]
    )

    return payload["checklist_id"], checks
