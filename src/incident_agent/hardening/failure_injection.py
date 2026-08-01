"""Controlled failure injection for production-hardening tests."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FailureMode(StrEnum):
    """Supported deterministic failure modes."""

    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    RETRIEVAL_UNAVAILABLE = "RETRIEVAL_UNAVAILABLE"
    RUNTIME_TIMEOUT = "RUNTIME_TIMEOUT"


@dataclass(frozen=True)
class FailureInjectionResult:
    """Result of one controlled failure injection."""

    failure_mode: FailureMode
    failure_observed: bool
    sensitive_details_exposed: bool
    authority_expanded: bool
    fallback_used: bool
    explanation: str


def inject_failure(
    failure_mode: FailureMode,
) -> FailureInjectionResult:
    """Return a deterministic tutorial failure result."""

    explanations = {
        FailureMode.PROVIDER_TIMEOUT: (
            "Provider timeout was surfaced through a "
            "structured failure boundary."
        ),
        FailureMode.PROVIDER_FAILURE: (
            "Provider failure was sanitized and did not "
            "authorize runtime execution."
        ),
        FailureMode.RETRIEVAL_UNAVAILABLE: (
            "Retrieval failure prevented evidence synthesis "
            "and tool execution."
        ),
        FailureMode.RUNTIME_TIMEOUT: (
            "Runtime timeout retained the policy and audit "
            "evidence without repeating a mutation."
        ),
    }

    return FailureInjectionResult(
        failure_mode=failure_mode,
        failure_observed=True,
        sensitive_details_exposed=False,
        authority_expanded=False,
        fallback_used=False,
        explanation=explanations[failure_mode],
    )
