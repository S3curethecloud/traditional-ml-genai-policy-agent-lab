"""Backup, restore, RPO, RTO, and consistency verification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from incident_agent.resilience.contracts import (
    BackupRecord,
    CheckpointRecord,
    RecoveryStatus,
    RecoveryVerification,
    RPOResult,
    RTOResult,
)


def canonical_sha256(
    payload: dict[str, Any],
) -> str:
    """Return deterministic state digest."""

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()


def create_checkpoint(
    workflow_id: str,
    sequence: int,
    payload: dict[str, Any],
) -> CheckpointRecord:
    """Create a deterministic workflow checkpoint."""

    state_sha256 = canonical_sha256(payload)

    checkpoint_id = (
        "checkpoint-"
        + hashlib.sha256(
            (
                f"{workflow_id}|{sequence}|"
                f"{state_sha256}"
            ).encode("utf-8")
        ).hexdigest()[:12]
    )

    return CheckpointRecord(
        checkpoint_id=checkpoint_id,
        workflow_id=workflow_id,
        sequence=sequence,
        state_sha256=state_sha256,
        payload=payload,
    )


def create_backup(
    checkpoint: CheckpointRecord,
    release_id: str,
    created_epoch_seconds: int,
    output_path: Path,
) -> BackupRecord:
    """Persist a deterministic tutorial backup."""

    payload = {
        "checkpoint_id": checkpoint.checkpoint_id,
        "workflow_id": checkpoint.workflow_id,
        "sequence": checkpoint.sequence,
        "state_sha256": checkpoint.state_sha256,
        "payload": checkpoint.payload,
        "release_id": release_id,
        "created_epoch_seconds": created_epoch_seconds,
    }

    backup_sha256 = canonical_sha256(payload)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return BackupRecord(
        backup_id=f"backup-{backup_sha256[:12]}",
        release_id=release_id,
        created_epoch_seconds=created_epoch_seconds,
        source_state_sha256=checkpoint.state_sha256,
        backup_sha256=backup_sha256,
        path=str(output_path),
    )


def restore_backup(
    backup: BackupRecord,
) -> dict[str, Any]:
    """Load and validate a persisted backup."""

    path = Path(backup.path)

    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    if canonical_sha256(payload) != backup.backup_sha256:
        raise ValueError(
            "Backup integrity verification failed"
        )

    return payload


def evaluate_rpo(
    failure_epoch_seconds: int,
    backup_epoch_seconds: int,
    objective_seconds: int,
) -> RPOResult:
    """Evaluate recovery-point objective."""

    observed = max(
        0,
        failure_epoch_seconds - backup_epoch_seconds,
    )

    return RPOResult(
        observed_seconds=observed,
        objective_seconds=objective_seconds,
        passed=observed <= objective_seconds,
    )


def evaluate_rto(
    recovery_started_epoch_seconds: int,
    recovery_completed_epoch_seconds: int,
    objective_seconds: int,
) -> RTOResult:
    """Evaluate recovery-time objective."""

    observed = max(
        0,
        recovery_completed_epoch_seconds
        - recovery_started_epoch_seconds,
    )

    return RTOResult(
        observed_seconds=observed,
        objective_seconds=objective_seconds,
        passed=observed <= objective_seconds,
    )


def verify_recovery(
    checkpoint: CheckpointRecord,
    restored_payload: dict[str, Any],
    replay_verified: bool,
) -> RecoveryVerification:
    """Verify restored state and replay integrity."""

    restored_state = restored_payload["payload"]
    restored_sha256 = canonical_sha256(
        restored_state
    )

    consistent = (
        restored_sha256 == checkpoint.state_sha256
        and restored_payload["state_sha256"]
        == checkpoint.state_sha256
    )

    authority_preserved = (
        restored_state.get("policy_decision")
        in {"ALLOW", "DENY", "ESCALATE"}
        and restored_state.get(
            "authority_expanded",
            False,
        )
        is False
    )

    recovered = (
        consistent
        and replay_verified
        and authority_preserved
    )

    return RecoveryVerification(
        status=(
            RecoveryStatus.RECOVERED
            if recovered
            else RecoveryStatus.FAILED
        ),
        source_state_sha256=checkpoint.state_sha256,
        restored_state_sha256=restored_sha256,
        state_consistent=consistent,
        replay_verified=replay_verified,
        authority_boundary_preserved=authority_preserved,
    )
