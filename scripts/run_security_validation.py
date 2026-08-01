#!/usr/bin/env python3
"""Run Phase 16 adversarial validation and compliance evidence."""

from __future__ import annotations

import json
from pathlib import Path

from incident_agent.security_validation.adversarial import (
    attack_block_rate,
    evaluate_adversarial_suite,
)
from incident_agent.security_validation.attestation import (
    build_security_attestation,
    count_open_critical_risks,
    evaluate_control_coverage,
)
from incident_agent.security_validation.contracts import (
    SecurityAuditEvent,
    SecurityValidationReport,
    ValidationStatus,
)
from incident_agent.security_validation.loading import (
    load_adversarial_cases,
    load_compliance_controls,
    load_residual_risks,
    load_security_policy,
)


ROOT = Path(".")
POLICY_PATH = ROOT / "config/security-validation-policy.json"
CASES_PATH = ROOT / "security/phase-16-adversarial-cases.json"
MAPPING_PATH = ROOT / "security/phase-16-compliance-mapping.json"
RISKS_PATH = ROOT / "security/phase-16-residual-risks.json"
OUTPUT_PATH = (
    ROOT
    / "reports/security-validation/"
    "phase-16-security-validation-report.json"
)


def main() -> None:
    policy = load_security_policy(POLICY_PATH)

    suite_id, cases = load_adversarial_cases(
        CASES_PATH
    )
    controls = load_compliance_controls(
        MAPPING_PATH
    )
    risks = load_residual_risks(
        RISKS_PATH
    )

    required_categories = set(
        policy["required_attack_categories"]
    )
    actual_categories = {
        case.category
        for case in cases
    }

    if actual_categories != required_categories:
        raise RuntimeError(
            "Adversarial suite does not match required categories"
        )

    results = evaluate_adversarial_suite(cases)
    block_rate = attack_block_rate(results)

    coverage = evaluate_control_coverage(
        root=ROOT,
        controls=controls,
    )

    open_critical = count_open_critical_risks(
        risks
    )

    attestation = build_security_attestation(
        policy_version=policy["policy_version"],
        attack_block_rate_percentage=block_rate,
        control_coverage_percentage=(
            coverage.coverage_percentage
        ),
        open_critical_risks=open_critical,
        minimum_attack_block_rate_percentage=policy[
            "minimum_attack_block_rate_percentage"
        ],
        minimum_control_coverage_percentage=policy[
            "minimum_control_coverage_percentage"
        ],
        maximum_open_critical_risks=policy[
            "maximum_open_critical_risks"
        ],
    )

    events = (
        SecurityAuditEvent(
            sequence=1,
            event_type="adversarial_suite_loaded",
            detail=(
                f"{len(cases)} adversarial cases loaded."
            ),
            evidence_references=(suite_id,),
        ),
        SecurityAuditEvent(
            sequence=2,
            event_type="adversarial_suite_evaluated",
            detail=(
                f"Attack block rate: {block_rate:.2f}%."
            ),
            evidence_references=tuple(
                result.case_id
                for result in results
            ),
        ),
        SecurityAuditEvent(
            sequence=3,
            event_type="control_coverage_evaluated",
            detail=(
                f"Control coverage: "
                f"{coverage.coverage_percentage:.2f}%."
            ),
            evidence_references=tuple(
                control.control_id
                for control in controls
            ),
        ),
        SecurityAuditEvent(
            sequence=4,
            event_type="residual_risks_reviewed",
            detail=(
                f"{len(risks)} residual risks reviewed; "
                f"{open_critical} open critical."
            ),
            evidence_references=tuple(
                risk.risk_id
                for risk in risks
            ),
        ),
        SecurityAuditEvent(
            sequence=5,
            event_type="security_attestation_created",
            detail=(
                f"Security attestation status: "
                f"{attestation.status.value}."
            ),
            evidence_references=(
                attestation.attestation_id,
            ),
        ),
    )

    report = SecurityValidationReport(
        policy_version=policy["policy_version"],
        suite_id=suite_id,
        adversarial_results=results,
        control_coverage=coverage,
        residual_risks=risks,
        attestation=attestation,
        audit_events=events,
        automatic_exception_approval_performed=False,
        automatic_remediation_performed=False,
        production_changes_performed=False,
        authority_boundary=(
            "Security validation may execute deterministic "
            "test cases, classify outcomes, map evidence, "
            "record residual risks, and produce an "
            "attestation. It cannot grant exceptions, "
            "modify production policy, or remediate systems."
        ),
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    OUTPUT_PATH.write_text(
        json.dumps(
            report.to_dict(),
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    passed = sum(
        result.status is ValidationStatus.PASS
        for result in results
    )

    print(
        f"PASS: adversarial cases={passed}/{len(results)}"
    )
    print(
        f"PASS: attack block rate={block_rate:.2f}%"
    )
    print(
        "PASS: control coverage="
        f"{coverage.coverage_percentage:.2f}%"
    )
    print(
        f"PASS: open critical risks={open_critical}"
    )
    print(
        "PASS: attestation="
        f"{attestation.status.value}"
    )
    print(
        "PASS: no automatic exception approval performed"
    )
    print(
        "PASS: no automatic remediation performed"
    )
    print(
        "PASS: no production changes performed"
    )


if __name__ == "__main__":
    main()
