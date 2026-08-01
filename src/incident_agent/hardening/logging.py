"""Structured operational logging with deterministic redaction."""

from __future__ import annotations

from typing import Any

from incident_agent.hardening.contracts import (
    StructuredLogEvent,
)


DEFAULT_SENSITIVE_FIELDS = {
    "access_token",
    "api_key",
    "authorization",
    "cookie",
    "credential",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "token",
}


def redact_value(
    value: Any,
    sensitive_fields: set[str] | None = None,
) -> Any:
    """Recursively redact sensitive structured values."""

    fields = (
        DEFAULT_SENSITIVE_FIELDS
        if sensitive_fields is None
        else {
            field.lower()
            for field in sensitive_fields
        }
    )

    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED]"
                if str(key).lower() in fields
                else redact_value(
                    nested,
                    sensitive_fields=fields,
                )
            )
            for key, nested in value.items()
        }

    if isinstance(value, list):
        return [
            redact_value(
                nested,
                sensitive_fields=fields,
            )
            for nested in value
        ]

    if isinstance(value, tuple):
        return tuple(
            redact_value(
                nested,
                sensitive_fields=fields,
            )
            for nested in value
        )

    return value


def create_structured_log_event(
    event_type: str,
    trace_id: str,
    workflow_id: str,
    severity: str,
    attributes: dict[str, Any],
) -> StructuredLogEvent:
    """Create a redacted operational event."""

    return StructuredLogEvent(
        event_type=event_type,
        trace_id=trace_id,
        workflow_id=workflow_id,
        severity=severity,
        attributes=redact_value(attributes),
    )
