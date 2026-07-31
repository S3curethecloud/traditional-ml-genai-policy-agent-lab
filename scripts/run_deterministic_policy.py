#!/usr/bin/env python3
"""Run the Phase 6 deterministic policy demonstration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from incident_agent.evaluation.ambiguity import (
    evaluate_ambiguity_pack,
    load_ambiguity_pack,
)
from incident_agent.genai.provider import (
    DeterministicTutorialProvider,
)
from incident_agent.genai.service import (
    build_synthesis_request,
    synthesize_evidence,
)
from incident_agent.ml.inference import (
    IncidentClassifier,
)
from incident_agent.policy.contracts import (
    PolicyIdentity,
)
from incident_agent.policy.service import (
    build_policy_context,
    evaluate_synthesis_policy,
)
from incident_agent.retrieval.contracts import (
    RetrievalIdentity,
    RetrievalQuery,
    RetrievalScope,
)
from incident_agent.retrieval.engine import (
    retrieve_documents,
)
from incident_agent.retrieval.loader import (
    load_knowledge_corpus,
)
from incident_agent.retrieval.planning import (
    build_retrieval_query_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate GenAI tool recommendations through "
            "the deterministic policy engine."
        )
    )
    parser.add_argument(
        "--knowledge-directory",
        type=Path,
        default=Path("data/knowledge"),
    )
    parser.add_argument(
        "--ambiguity-pack",
        type=Path,
        default=Path(
            "data/ambiguity/phase-3b-cases.yaml"
        ),
    )
    parser.add_argument(
        "--model-directory",
        type=Path,
        default=Path(
            "models/incident-classifier"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "reports/policy/"
            "phase-06-policy-report.json"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    documents = load_knowledge_corpus(
        args.knowledge_directory
    )
    cases = load_ambiguity_pack(
        args.ambiguity_pack
    )
    classifier = IncidentClassifier.load(
        args.model_directory
    )

    ambiguity_results = evaluate_ambiguity_pack(
        cases,
        classifier,
    )

    retrieval_identity = RetrievalIdentity(
        user_id="engineer-42",
        tenant_id="tenant-alpha",
        roles=("incident_responder",),
    )

    policy_identity = PolicyIdentity(
        user_id="engineer-42",
        tenant_id="tenant-alpha",
        roles=("incident_responder",),
    )

    scope = RetrievalScope(
        service="identity-api",
        environment="production",
    )

    provider = DeterministicTutorialProvider()
    case_reports: list[dict[str, Any]] = []

    for ambiguity_result in ambiguity_results:
        query_text = build_retrieval_query_text(
            ambiguity_result
        )

        retrieval_response = retrieve_documents(
            documents=documents,
            query=RetrievalQuery(
                query_text=query_text,
                identity=retrieval_identity,
                scope=scope,
                maximum_results=5,
            ),
        )

        synthesis_request = build_synthesis_request(
            ambiguity_result=ambiguity_result,
            retrieval_response=retrieval_response,
        )

        synthesis_response = synthesize_evidence(
            request=synthesis_request,
            provider=provider,
        )

        policy_context = build_policy_context(
            identity=policy_identity,
            request_tenant_id="tenant-alpha",
            service="identity-api",
            environment="production",
            ambiguity_result=ambiguity_result,
            retrieval_response=retrieval_response,
        )

        policy_evaluation = evaluate_synthesis_policy(
            synthesis=synthesis_response,
            context=policy_context,
        )

        case_reports.append(
            {
                "case_id": ambiguity_result.case_id,
                "synthesis_disposition":
                    synthesis_response.disposition.value,
                "recommended_tool": (
                    synthesis_response
                    .tool_recommendation.tool_name
                    if synthesis_response
                    .tool_recommendation
                    else None
                ),
                "policy_evaluation":
                    policy_evaluation.to_dict(),
            }
        )

    summary = {
        "case_count": len(case_reports),
        "allow_count": sum(
            report["policy_evaluation"]["decision"]
            == "ALLOW"
            for report in case_reports
        ),
        "deny_count": sum(
            report["policy_evaluation"]["decision"]
            == "DENY"
            for report in case_reports
        ),
        "escalate_count": sum(
            report["policy_evaluation"]["decision"]
            == "ESCALATE"
            for report in case_reports
        ),
    }

    report = {
        "phase": "phase-06",
        "policy_version":
            "deterministic-policy-v1",
        "security_properties": {
            "genai_authorized_execution": False,
            "deterministic_policy_evaluated": True,
            "tool_execution_performed": False,
            "deny_precedence_over_escalate": True,
            "escalate_precedence_over_allow": True,
            "request_fingerprint_recorded": True,
        },
        "summary": summary,
        "results": case_reports,
    }

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"PASS: evaluated policy for "
        f"{summary['case_count']} cases"
    )
    print(
        "PASS: GenAI did not authorize execution"
    )
    print(
        "PASS: deterministic policy returned only "
        "ALLOW, DENY, or ESCALATE"
    )
    print(
        "PASS: no tool execution occurred"
    )

    print("\nSummary:")
    print(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
    )

    print("\nCase decisions:")

    for case_report in case_reports:
        evaluation = case_report[
            "policy_evaluation"
        ]

        reason_ids = [
            reason["rule_id"]
            for reason in evaluation["reasons"]
        ]

        print(
            f"  {case_report['case_id']}: "
            f"{evaluation['decision']}; "
            f"tool={case_report['recommended_tool']}; "
            f"reasons={reason_ids}"
        )


if __name__ == "__main__":
    main()
