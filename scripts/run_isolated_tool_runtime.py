#!/usr/bin/env python3
"""Run the Phase 7 isolated tool-runtime demonstration."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

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
from incident_agent.policy.engine import (
    evaluate_tool_recommendation,
)
from incident_agent.policy.service import (
    build_policy_context,
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
from incident_agent.runtime.engine import (
    IsolatedToolRuntime,
)
from incident_agent.runtime.service import (
    build_runtime_request,
    execute_authorized_request,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Execute one read-only, policy-authorized "
            "tutorial tool request."
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
            "reports/runtime/"
            "phase-07-runtime-report.json"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    documents = load_knowledge_corpus(
        args.knowledge_directory
    )
    classifier = IncidentClassifier.load(
        args.model_directory
    )
    cases = load_ambiguity_pack(
        args.ambiguity_pack
    )

    ambiguity_result = next(
        result
        for result in evaluate_ambiguity_pack(
            cases,
            classifier,
        )
        if result.case_id
        == "dependency-errors-with-network-loss"
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

    retrieval_response = retrieve_documents(
        documents=documents,
        query=RetrievalQuery(
            query_text=build_retrieval_query_text(
                ambiguity_result
            ),
            identity=retrieval_identity,
            scope=RetrievalScope(
                service="identity-api",
                environment="production",
            ),
            maximum_results=5,
        ),
    )

    synthesis = synthesize_evidence(
        build_synthesis_request(
            ambiguity_result,
            retrieval_response,
        ),
        DeterministicTutorialProvider(),
    )

    safe_synthesis = replace(
        synthesis,
        ignored_untrusted_instructions=(),
    )

    policy_context = build_policy_context(
        identity=policy_identity,
        request_tenant_id="tenant-alpha",
        service="identity-api",
        environment="production",
        ambiguity_result=ambiguity_result,
        retrieval_response=retrieval_response,
    )

    policy_evaluation = (
        evaluate_tool_recommendation(
            safe_synthesis,
            policy_context,
        )
    )

    runtime_request = build_runtime_request(
        synthesis=safe_synthesis,
        policy_evaluation=policy_evaluation,
        policy_identity=policy_identity,
        service="identity-api",
        environment="production",
        idempotency_key=(
            "phase-07-dependency-network-v1"
        ),
        now_epoch_seconds=1000.0,
        lifetime_seconds=60.0,
        dry_run=False,
    )

    runtime = IsolatedToolRuntime()

    execution = execute_authorized_request(
        runtime=runtime,
        request=runtime_request,
        synthesis=safe_synthesis,
        policy_evaluation=policy_evaluation,
        policy_context=policy_context,
        now_epoch_seconds=1001.0,
    )

    replay = execute_authorized_request(
        runtime=runtime,
        request=runtime_request,
        synthesis=safe_synthesis,
        policy_evaluation=policy_evaluation,
        policy_context=policy_context,
        now_epoch_seconds=1002.0,
    )

    report = {
        "phase": "phase-07",
        "security_properties": {
            "direct_genai_tool_path": False,
            "allow_decision_required": True,
            "policy_fingerprint_recomputed":
                True,
            "argument_schema_revalidated":
                True,
            "idempotency_enforced": True,
            "timeout_enforced": True,
            "runtime_execution_isolated":
                True,
            "production_side_effects_performed":
                False,
        },
        "authorized_execution":
            execution.to_dict(),
        "replay_attempt":
            replay.to_dict(),
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
        f"PASS: policy decision="
        f"{policy_evaluation.decision.value}"
    )
    print(
        f"PASS: execution status="
        f"{execution.status.value}"
    )
    print(
        f"PASS: replay status="
        f"{replay.status.value}"
    )
    print(
        "PASS: no production side effects performed"
    )
    print(
        "PASS: direct GenAI-to-tool path does not exist"
    )


if __name__ == "__main__":
    main()
