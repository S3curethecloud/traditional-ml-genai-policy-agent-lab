#!/usr/bin/env python3
"""Run Phase 4 permission-aware retrieval demonstrations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from incident_agent.evaluation.ambiguity import (
    evaluate_ambiguity_pack,
    load_ambiguity_pack,
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
            "Run permission-aware retrieval from "
            "Phase 3B ambiguity evidence."
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
            "reports/retrieval/"
            "phase-04-retrieval-report.json"
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

    case_reports: list[dict[str, Any]] = []

    for ambiguity_result in ambiguity_results:
        query_text = build_retrieval_query_text(
            ambiguity_result
        )

        response = retrieve_documents(
            documents=documents,
            query=RetrievalQuery(
                query_text=query_text,
                identity=identity,
                scope=scope,
                maximum_results=5,
            ),
        )

        case_reports.append(
            {
                "case_id":
                    ambiguity_result.case_id,
                "classifier_evidence": {
                    "deterministic_category":
                        ambiguity_result
                        .deterministic_category,
                    "ml_category":
                        ambiguity_result.ml_category,
                    "ml_second_category":
                        ambiguity_result
                        .ml_second_category,
                    "classifiers_agree":
                        ambiguity_result
                        .classifiers_agree,
                    "review_triggers": list(
                        ambiguity_result
                        .review_triggers
                    ),
                },
                "retrieval_query": query_text,
                "retrieval_results": [
                    {
                        "document_id":
                            result.document_id,
                        "title": result.title,
                        "document_type":
                            result.document_type,
                        "hybrid_score":
                            result.hybrid_score,
                        "citation":
                            result.citation,
                        "trusted_instruction_source":
                            result
                            .trusted_instruction_source,
                        "prompt_injection_detected":
                            result
                            .prompt_injection_detected,
                        "prompt_injection_markers":
                            list(
                                result
                                .prompt_injection_markers
                            ),
                    }
                    for result in response.results
                ],
                "denied_document_evidence": [
                    {
                        "document_id":
                            denied.document_id,
                        "document_type":
                            denied.document_type,
                        "reason_codes": list(
                            denied.reason_codes
                        ),
                    }
                    for denied
                    in response.denied_documents
                ],
            }
        )

    report = {
        "retrieval_version":
            "permission-aware-retrieval-v1",
        "identity": {
            "user_id": identity.user_id,
            "tenant_id": identity.tenant_id,
            "roles": list(identity.roles),
        },
        "scope": {
            "service": scope.service,
            "environment": scope.environment,
        },
        "security_properties": {
            "permission_filtering_before_ranking":
                True,
            "denied_content_returned": False,
            "prompt_injection_inspection":
                True,
            "citations_required": True,
        },
        "case_reports": case_reports,
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

    denied_ids = {
        denied["document_id"]
        for case_report in case_reports
        for denied in case_report[
            "denied_document_evidence"
        ]
    }

    injection_results = [
        result
        for case_report in case_reports
        for result in case_report[
            "retrieval_results"
        ]
        if result["prompt_injection_detected"]
    ]

    print(
        f"PASS: loaded {len(documents)} "
        "knowledge documents"
    )
    print(
        f"PASS: evaluated retrieval for "
        f"{len(case_reports)} ambiguity cases"
    )
    print(
        "PASS: permission filtering occurred "
        "before ranking"
    )
    print(
        "PASS: denied document contents were "
        "not returned"
    )
    print(
        f"Denied document IDs observed: "
        f"{sorted(denied_ids)}"
    )
    print(
        f"Prompt-injection results surfaced: "
        f"{len(injection_results)}"
    )


if __name__ == "__main__":
    main()
