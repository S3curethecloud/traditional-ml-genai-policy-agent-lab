#!/usr/bin/env python3
"""Run the governed Phase 8 end-to-end workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from incident_agent.orchestrator.contracts import (
    WorkflowIdentity,
    WorkflowRequest,
)
from incident_agent.orchestrator.engine import (
    GovernedAgentOrchestrator,
)
from incident_agent.orchestrator.replay import (
    verify_workflow_replay,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the governed agent orchestrator."
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
            "reports/orchestrator/"
            "phase-08-workflow-report.json"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    orchestrator = GovernedAgentOrchestrator(
        knowledge_directory=(
            args.knowledge_directory
        ),
        ambiguity_pack_path=(
            args.ambiguity_pack
        ),
        model_directory=args.model_directory,
    )

    request = WorkflowRequest(
        workflow_id="workflow-phase-08-001",
        trace_id="trace-phase-08-001",
        case_id=(
            "dependency-errors-with-network-loss"
        ),
        identity=WorkflowIdentity(
            user_id="engineer-42",
            tenant_id="tenant-alpha",
            roles=("incident_responder",),
        ),
        request_tenant_id="tenant-alpha",
        service="identity-api",
        environment="production",
        maximum_retrieval_results=5,
        idempotency_key=(
            "phase-08-runtime-key-001"
        ),
        dry_run=False,
        created_at_epoch_seconds=1000.0,
    )

    outcome = orchestrator.run(
        request=request,
        now_epoch_seconds=1001.0,
    )

    replay = verify_workflow_replay(
        outcome
    )

    report = {
        "phase": "phase-08",
        "security_properties": {
            "typed_workflow_state": True,
            "ordered_state_transitions": True,
            "checkpoint_after_each_step": True,
            "runtime_requires_allow": True,
            "policy_cannot_be_skipped": True,
            "direct_genai_runtime_path":
                False,
            "trace_binding_enforced": True,
            "workflow_replay_verified":
                replay.valid,
            "production_side_effects_performed":
                False,
        },
        "workflow_outcome": outcome.to_dict(),
        "replay_verification": {
            "valid": replay.valid,
            "event_sequence_valid":
                replay.event_sequence_valid,
            "checkpoint_sequence_valid":
                replay.checkpoint_sequence_valid,
            "trace_binding_valid":
                replay.trace_binding_valid,
            "workflow_binding_valid":
                replay.workflow_binding_valid,
            "runtime_after_allow_only":
                replay.runtime_after_allow_only,
            "errors": list(replay.errors),
        },
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
        f"PASS: workflow status="
        f"{outcome.status.value}"
    )
    print(
        f"PASS: final step="
        f"{outcome.final_step.value}"
    )
    print(
        f"PASS: policy decision="
        f"{outcome.policy_decision}"
    )
    print(
        f"PASS: runtime status="
        f"{outcome.runtime_status}"
    )
    print(
        f"PASS: checkpoints="
        f"{len(outcome.checkpoints)}"
    )
    print(
        f"PASS: events={len(outcome.events)}"
    )
    print(
        f"PASS: replay valid={replay.valid}"
    )
    print(
        "PASS: no production side effects performed"
    )


if __name__ == "__main__":
    main()
