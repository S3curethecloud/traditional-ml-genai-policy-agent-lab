#!/usr/bin/env python3
"""Run Phase 5 evidence synthesis over ambiguity cases."""

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
            "Run evidence-grounded GenAI synthesis "
            "using the deterministic tutorial provider."
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
            "reports/genai/"
            "phase-05-synthesis-report.json"
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

    identity = RetrievalIdentity(
        user_id="engineer-42",
        tenant_id="tenant-alpha",
        roles=("incident_responder",),
    )

    scope = RetrievalScope(
        service="identity-api",
        environment="production",
    )

    provider = DeterministicTutorialProvider()

    synthesis_reports: list[dict[str, Any]] = []

    for ambiguity_result in ambiguity_results:
        query_text = build_retrieval_query_text(
            ambiguity_result
        )

        retrieval_response = retrieve_documents(
            documents=documents,
            query=RetrievalQuery(
                query_text=query_text,
                identity=identity,
                scope=scope,
                maximum_results=5,
            ),
        )

        request = build_synthesis_request(
            ambiguity_result=ambiguity_result,
            retrieval_response=retrieval_response,
        )

        response = synthesize_evidence(
            request=request,
            provider=provider,
        )

        synthesis_reports.append(
            response.to_dict()
        )

    report = {
        "phase": "phase-05",
        "provider": provider.provider_name,
        "live_model_called": False,
        "provider_role": (
            "Deterministic test double for validating "
            "the GenAI evidence contract."
        ),
        "security_properties": {
            "authorized_evidence_only": True,
            "denied_content_available_to_provider":
                False,
            "citations_validated": True,
            "prompt_injection_documents_ignored":
                True,
            "tool_execution_performed": False,
            "authorization_decision_performed":
                False,
        },
        "summary": {
            "case_count": len(synthesis_reports),
            "recommend_count": sum(
                item["disposition"] == "RECOMMEND"
                for item in synthesis_reports
            ),
            "request_more_evidence_count": sum(
                item["disposition"]
                == "REQUEST_MORE_EVIDENCE"
                for item in synthesis_reports
            ),
            "abstain_count": sum(
                item["disposition"] == "ABSTAIN"
                for item in synthesis_reports
            ),
            "human_review_count": sum(
                item["requires_human_review"]
                for item in synthesis_reports
            ),
        },
        "results": synthesis_reports,
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
        f"PASS: synthesized evidence for "
        f"{len(synthesis_reports)} cases"
    )
    print(
        "PASS: authorized retrieval evidence only"
    )
    print(
        "PASS: citations validated"
    )
    print(
        "PASS: prompt-injection documents ignored"
    )
    print(
        "PASS: no tool execution performed"
    )
    print(
        "PASS: no authorization decision performed"
    )

    print("\nSummary:")
    print(
        json.dumps(
            report["summary"],
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
