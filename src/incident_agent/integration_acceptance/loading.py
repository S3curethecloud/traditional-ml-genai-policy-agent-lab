"""Loading and validation for Phase 18 acceptance inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from incident_agent.integration_acceptance.contracts import (
    AcceptanceOutcome,
    AcceptanceScenario,
)


def load_acceptance_policy(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not payload.get("policy_version"):
        raise ValueError("Policy version is required")

    if not payload.get("platform_contract_version"):
        raise ValueError(
            "Platform contract version is required"
        )

    prohibited_flags = (
        "automatic_acceptance_approval_allowed",
        "automatic_exception_approval_allowed",
        "automatic_remediation_allowed",
        "production_execution_allowed",
    )

    for flag in prohibited_flags:
        if payload.get(flag) is not False:
            raise ValueError(f"{flag} must remain false")

    for field_name in (
        "minimum_scenario_pass_rate_percentage",
        "minimum_stage_coverage_percentage",
        "minimum_evidence_continuity_percentage",
    ):
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


def load_acceptance_scenarios(
    path: Path,
) -> tuple[str, tuple[AcceptanceScenario, ...]]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    scenarios = tuple(
        AcceptanceScenario(
            scenario_id=item["scenario_id"],
            domain=item["domain"],
            scenario_type=item["scenario_type"],
            tenant_id=item["tenant_id"],
            actor_role=item["actor_role"],
            incident_category=item["incident_category"],
            authorized_evidence_available=bool(
                item["authorized_evidence_available"]
            ),
            prompt_injection_detected=bool(
                item["prompt_injection_detected"]
            ),
            cross_tenant_attempt=bool(
                item["cross_tenant_attempt"]
            ),
            policy_fingerprint_valid=bool(
                item["policy_fingerprint_valid"]
            ),
            tool_name=item["tool_name"],
            tool_mutating=bool(item["tool_mutating"]),
            human_approval_present=bool(
                item["human_approval_present"]
            ),
            expected_outcome=AcceptanceOutcome(
                item["expected_outcome"]
            ),
        )
        for item in payload["scenarios"]
    )

    ids = tuple(item.scenario_id for item in scenarios)

    if len(ids) != len(set(ids)):
        raise ValueError("Scenario IDs must be unique")

    return payload["suite_id"], scenarios
