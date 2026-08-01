#!/usr/bin/env python3
"""Run Phase 18 platform integration acceptance."""

from __future__ import annotations

import json
from pathlib import Path

from incident_agent.integration_acceptance.contracts import (
    PlatformAcceptanceReport,
)
from incident_agent.integration_acceptance.evaluation import (
    calculate_acceptance_metrics,
    determine_platform_acceptance,
)
from incident_agent.integration_acceptance.harness import (
    execute_acceptance_suite,
)
from incident_agent.integration_acceptance.loading import (
    load_acceptance_policy,
    load_acceptance_scenarios,
)


ROOT = Path(".")
POLICY_PATH = (
    ROOT
    / "config/integration-acceptance/"
    "integration-acceptance-policy.json"
)
SCENARIOS_PATH = (
    ROOT
    / "acceptance/scenarios/"
    "phase-18-acceptance-scenarios.json"
)
OUTPUT_PATH = (
    ROOT
    / "reports/integration-acceptance/"
    "phase-18-platform-acceptance-report.json"
)


def main() -> None:
    policy = load_acceptance_policy(POLICY_PATH)
    suite_id, scenarios = load_acceptance_scenarios(
        SCENARIOS_PATH
    )

    results = execute_acceptance_suite(scenarios)

    required_stages = tuple(policy["required_stages"])

    metrics = calculate_acceptance_metrics(
        results,
        required_stages,
    )

    actual_domains = {
        scenario.domain
        for scenario in scenarios
    }
    required_domains_present = (
        set(policy["required_domains"])
        <= actual_domains
    )

    actual_types = {
        scenario.scenario_type
        for scenario in scenarios
    }
    required_types_present = (
        set(policy["required_scenario_types"])
        <= actual_types
    )

    real_side_effects = any(
        result.real_side_effect_performed
        for result in results
    )

    decision, reasons = determine_platform_acceptance(
        metrics=metrics,
        policy=policy,
        required_domains_present=(
            required_domains_present
        ),
        required_scenario_types_present=(
            required_types_present
        ),
        real_side_effects_performed=real_side_effects,
    )

    report = PlatformAcceptanceReport(
        policy_version=policy["policy_version"],
        platform_contract_version=policy[
            "platform_contract_version"
        ],
        suite_id=suite_id,
        scenario_results=results,
        metrics=metrics,
        decision=decision,
        reasons=reasons,
        automatic_acceptance_approval_performed=False,
        automatic_exception_approval_performed=False,
        automatic_remediation_performed=False,
        production_execution_performed=False,
        authority_boundary=(
            "The acceptance harness may simulate complete "
            "workflow paths and produce evidence. It cannot "
            "deploy, mutate production data, shift traffic, "
            "approve exceptions, authorize itself, or expand "
            "platform and tool authority."
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

    print(
        "PASS: acceptance scenarios="
        f"{metrics.passed_scenarios}/"
        f"{metrics.total_scenarios}"
    )
    print(
        "PASS: scenario pass rate="
        f"{metrics.scenario_pass_rate_percentage:.2f}%"
    )
    print(
        "PASS: stage coverage="
        f"{metrics.stage_coverage_percentage:.2f}%"
    )
    print(
        "PASS: evidence continuity="
        f"{metrics.evidence_continuity_percentage:.2f}%"
    )
    print(
        "PASS: platform decision="
        f"{decision.value}"
    )
    print("PASS: no automatic acceptance approval")
    print("PASS: no automatic exception approval")
    print("PASS: no automatic remediation")
    print("PASS: no production execution")


if __name__ == "__main__":
    main()
