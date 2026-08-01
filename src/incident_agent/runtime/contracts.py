"""Typed contracts for the isolated tool runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from incident_agent.genai.contracts import ToolRisk


class ExecutionStatus(StrEnum):
    """Final runtime execution status."""

    SUCCEEDED = "SUCCEEDED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    REPLAYED = "REPLAYED"


class RuntimeErrorCode(StrEnum):
    """Stable isolated-runtime error codes."""

    POLICY_NOT_ALLOWED = "POLICY_NOT_ALLOWED"
    POLICY_FINGERPRINT_MISMATCH = (
        "POLICY_FINGERPRINT_MISMATCH"
    )
    TOOL_NOT_REGISTERED = "TOOL_NOT_REGISTERED"
    TOOL_NAME_MISMATCH = "TOOL_NAME_MISMATCH"
    ARGUMENT_SCHEMA_INVALID = "ARGUMENT_SCHEMA_INVALID"
    IDEMPOTENCY_KEY_REUSED = "IDEMPOTENCY_KEY_REUSED"
    REQUEST_EXPIRED = "REQUEST_EXPIRED"
    EXECUTION_TIMEOUT = "EXECUTION_TIMEOUT"
    HANDLER_FAILURE = "HANDLER_FAILURE"
    RISK_MISMATCH = "RISK_MISMATCH"
    DRY_RUN_REQUIRED = "DRY_RUN_REQUIRED"


@dataclass(frozen=True)
class RuntimeIdentity:
    """Identity propagated from the trusted gateway."""

    user_id: str
    tenant_id: str
    roles: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeToolRequest:
    """Typed request submitted to the isolated tool runtime."""

    request_id: str
    idempotency_key: str
    tool_name: str
    arguments: dict[str, str]
    declared_risk: ToolRisk
    identity: RuntimeIdentity
    service: str
    environment: str
    policy_fingerprint: str
    created_at_epoch_seconds: float
    expires_at_epoch_seconds: float
    dry_run: bool


@dataclass(frozen=True)
class RuntimeToolResult:
    """Structured output returned by a tool handler."""

    tool_name: str
    data: dict[str, Any]
    side_effects_performed: bool
    handler_version: str


@dataclass(frozen=True)
class RuntimeError:
    """Structured runtime rejection or failure."""

    code: RuntimeErrorCode
    message: str
    retryable: bool


@dataclass(frozen=True)
class AuditEvent:
    """One immutable runtime audit event."""

    event_type: str
    request_id: str
    idempotency_key: str
    tool_name: str
    policy_fingerprint: str
    status: ExecutionStatus
    detail: str


@dataclass(frozen=True)
class ExecutionRecord:
    """Complete isolated-runtime execution record."""

    request_id: str
    idempotency_key: str
    tool_name: str
    status: ExecutionStatus
    result: RuntimeToolResult | None
    error: RuntimeError | None
    audit_events: tuple[AuditEvent, ...]
    execution_attempted: bool
    policy_fingerprint: str
    runtime_version: str
    authority_boundary: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)
