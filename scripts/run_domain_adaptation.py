#!/usr/bin/env python3
"""Run Phase 17 domain adaptation validation."""

from __future__ import annotations

import json
from pathlib import Path

from incident_agent.domain_adaptation.comparison import (
    compare_domain_packs,
    determine_adaptation_decision,
)
from incident_agent.domain_adaptation.contracts import (
    AdaptationReport,
    PackValidationStatus,
)
from incident_agent.domain_adaptation.loading import (
    load_adaptation_policy,
    load_domain_pack,
)
from incident_agent.domain_adaptation.validation import (
    validate_domain_pack,
)


ROOT = Path(".")
POLICY_PATH = (
    ROOT
    / "config/domain-adaptation/"
    "domain-adaptation-policy.json"
)
REFERENCE_PATH = (
    ROOT
    / "domains/identity-operations/"
    "domain-pack.json"
)
CANDIDATE_PATH = (
    ROOT
    / "domains/payments-operations/"
    "domain-pack.json"
)
OUTPUT_PATH = (
    ROOT
    / "reports/domain-adaptation/"
    "phase-17-domain-adaptation-report.json"
)


def main() -> None:
    policy = load_adaptation_policy(POLICY_PATH)
    reference = load_domain_pack(REFERENCE_PATH)
    candidate = load_domain_pack(CANDIDATE_PATH)

    results = (
        validate_domain_pack(reference, policy),
        validate_domain_pack(candidate, policy),
    )

    comparison = compare_domain_packs(
        reference,
        candidate,
    )

    decision, reasons = determine_adaptation_decision(
        results,
        comparison,
    )

    report = AdaptationReport(
        policy_version=policy["policy_version"],
        platform_contract_version=policy[
            "platform_contract_version"
        ],
        packs=(reference, candidate),
        validation_results=results,
        comparison=comparison,
        decision=decision,
        reasons=reasons,
        automatic_pack_activation_performed=False,
        automatic_policy_mutation_performed=False,
        automatic_tool_registration_performed=False,
        production_changes_performed=False,
        authority_boundary=(
            "Domain packs may provide taxonomy, evidence, "
            "tool metadata, evaluation cases, and policy "
            "restrictions. They cannot execute tools, "
            "expand platform authority, approve exceptions, "
            "register themselves, or activate production."
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

    valid_count = sum(
        result.status is PackValidationStatus.VALID
        for result in results
    )

    print(
        f"PASS: valid domain packs={valid_count}/{len(results)}"
    )
    print(
        "PASS: candidate decision="
        f"{decision.value}"
    )
    print(
        "PASS: shared capabilities="
        f"{len(comparison.shared_capabilities)}"
    )
    print(
        "PASS: candidate-only capabilities="
        f"{len(comparison.candidate_only_capabilities)}"
    )
    print(
        "PASS: domain taxonomies isolated="
        f"{comparison.isolated_taxonomies}"
    )
    print(
        "PASS: evidence sources isolated="
        f"{comparison.isolated_evidence_sources}"
    )
    print("PASS: no automatic pack activation")
    print("PASS: no automatic policy mutation")
    print("PASS: no automatic tool registration")
    print("PASS: no production changes")


if __name__ == "__main__":
    main()
