"""Checkpoint storage for orchestrated workflows."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

from incident_agent.orchestrator.contracts import (
    WorkflowCheckpoint,
    WorkflowStep,
)


def build_state_digest(
    state_payload: dict[str, Any],
) -> str:
    """Create a stable digest for checkpoint evidence."""

    canonical = json.dumps(
        state_payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()


@dataclass
class InMemoryCheckpointStore:
    """Tutorial checkpoint store."""

    _checkpoints: dict[
        str,
        list[WorkflowCheckpoint],
    ] = field(default_factory=dict)

    def append(
        self,
        checkpoint: WorkflowCheckpoint,
    ) -> None:
        """Append a checkpoint in sequence order."""

        checkpoints = self._checkpoints.setdefault(
            checkpoint.workflow_id,
            [],
        )

        if checkpoints:
            previous = checkpoints[-1]

            if checkpoint.sequence <= previous.sequence:
                raise ValueError(
                    "Checkpoint sequence must increase"
                )

        checkpoints.append(checkpoint)

    def list_for_workflow(
        self,
        workflow_id: str,
    ) -> tuple[WorkflowCheckpoint, ...]:
        """Return all checkpoints for a workflow."""

        return tuple(
            self._checkpoints.get(
                workflow_id,
                (),
            )
        )

    def latest(
        self,
        workflow_id: str,
    ) -> WorkflowCheckpoint | None:
        """Return the most recent checkpoint."""

        checkpoints = self._checkpoints.get(
            workflow_id
        )

        if not checkpoints:
            return None

        return checkpoints[-1]


def create_checkpoint(
    workflow_id: str,
    trace_id: str,
    step: WorkflowStep,
    sequence: int,
    state_payload: dict[str, Any],
    evidence_references: tuple[str, ...],
) -> WorkflowCheckpoint:
    """Create one immutable workflow checkpoint."""

    return WorkflowCheckpoint(
        workflow_id=workflow_id,
        trace_id=trace_id,
        step=step,
        sequence=sequence,
        state_digest=build_state_digest(
            state_payload
        ),
        evidence_references=evidence_references,
    )
