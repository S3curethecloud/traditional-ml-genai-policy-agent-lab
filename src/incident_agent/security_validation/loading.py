"""Loading and validation for Phase 16 security evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from incident_agent.security_validation.contracts import (
    AdversarialCase,
    AttackOutcome,
    ComplianceControl,
    ResidualRisk,
    RiskSeverity,
)


def load_security_policy(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if (
        not isinstance(payload.get("policy_version"), str)
        or not payload["policy_version"].strip()
    ):
        raise ValueError("Security policy version is required")

    if payload.get("automatic_remediation_allowed"):
        raise ValueError(
            "Automatic remediation must remain disabled"
        )

    if payload.get("automatic_exception_approval_allowed"):
        raise ValueError(
            "Automatic exception approval must remain disabled"
        )

    for field_name in (
        "minimum_control_coverage_percentage",
        "minimum_attack_block_rate_percentage",
    ):
        value = payload.get(field_name)

        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not 0.0 <= float(value) <= 100.0
        ):
            raise ValueError(
                f"{field_name} must be between zero and one hundred"
            )

    maximum_critical = payload.get("maximum_open_critical_risks")

    if (
        not isinstance(maximum_critical, int)
        or isinstance(maximum_critical, bool)
        or maximum_critical < 0
    ):
        raise ValueError(
            "maximum_open_critical_risks must be non-negative"
        )

    categories = payload.get("required_attack_categories", [])

    if len(categories) != len(set(categories)):
        raise ValueError(
            "Required attack categories must be unique"
        )

    return payload


def load_adversarial_cases(
    path: Path,
) -> tuple[str, tuple[AdversarialCase, ...]]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    cases = tuple(
        AdversarialCase(
            case_id=item["case_id"],
            category=item["category"],
            target_control=item["target_control"],
            attack_payload=item["attack_payload"],
            expected_outcome=AttackOutcome(
                item["expected_outcome"]
            ),
            evidence_reference=item["evidence_reference"],
        )
        for item in payload["cases"]
    )

    if len(cases) != len({item.case_id for item in cases}):
        raise ValueError("Adversarial case IDs must be unique")

    return payload["suite_id"], cases


def load_compliance_controls(
    path: Path,
) -> tuple[ComplianceControl, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    controls = tuple(
        ComplianceControl(
            control_id=item["control_id"],
            control_name=item["control_name"],
            framework_mappings=tuple(
                item["framework_mappings"]
            ),
            evidence_references=tuple(
                item["evidence_references"]
            ),
        )
        for item in payload["controls"]
    )

    if len(controls) != len(
        {item.control_id for item in controls}
    ):
        raise ValueError("Compliance control IDs must be unique")

    return controls


def load_residual_risks(
    path: Path,
) -> tuple[ResidualRisk, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    return tuple(
        ResidualRisk(
            risk_id=item["risk_id"],
            title=item["title"],
            severity=RiskSeverity(item["severity"]),
            status=item["status"],
            description=item["description"],
            treatment=item["treatment"],
            exception_approved=bool(
                item["exception_approved"]
            ),
        )
        for item in payload["risks"]
    )


def canonical_sha256(payload: Any) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()
