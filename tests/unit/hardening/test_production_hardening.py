"""Tests for Phase 10 production hardening."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from incident_agent.hardening.attestation import (
    create_release_attestation,
    verify_release_attestation,
)
from incident_agent.hardening.circuit_breaker import (
    CircuitBreaker,
)
from incident_agent.hardening.configuration import (
    configuration_sha256,
    load_production_configuration,
    validate_configuration_payload,
)
from incident_agent.hardening.contracts import (
    CircuitState,
    HardeningErrorCode,
    PromotionDecision,
    ReadinessStatus,
)
from incident_agent.hardening.failure_injection import (
    FailureMode,
    inject_failure,
)
from incident_agent.hardening.limits import (
    ConcurrencyLimiter,
    SlidingWindowRateLimiter,
)
from incident_agent.hardening.logging import (
    create_structured_log_event,
    redact_value,
)
from incident_agent.hardening.promotion import (
    evaluate_deployment_readiness,
    evaluate_promotion,
)


CONFIGURATION_PATH = Path(
    "config/production-hardening.json"
)

SIGNING_KEY = "unit-test-signing-key"


def load_configuration():
    return load_production_configuration(
        path=CONFIGURATION_PATH,
        environment={
            "RELEASE_ATTESTATION_KEY":
                SIGNING_KEY,
        },
    )


def build_attestation(
    evidence_sha256: str = "a" * 64,
):
    configuration = load_configuration()

    return create_release_attestation(
        release_id="release-test",
        source_environment="staging",
        target_environment="production",
        evidence_sha256=evidence_sha256,
        configuration_sha256=(
            configuration_sha256(
                configuration
            )
        ),
        rollback_plan_id="rollback-test-v1",
        signer_id="ci-test-identity",
        signing_key=SIGNING_KEY,
    )


def build_readiness(
    release_gate_passed: bool = True,
    evidence_artifact_count: int = 3,
    evidence_sha256: str = "a" * 64,
    rollback_plan_exists: bool = True,
):
    configuration = load_configuration()
    attestation = build_attestation(
        evidence_sha256=evidence_sha256
    )

    return evaluate_deployment_readiness(
        configuration=configuration,
        release_id="release-test",
        release_gate_passed=(
            release_gate_passed
        ),
        evidence_artifact_count=(
            evidence_artifact_count
        ),
        evidence_sha256=evidence_sha256,
        attestation=attestation,
        signing_key=SIGNING_KEY,
        rollback_plan_exists=(
            rollback_plan_exists
        ),
    )


def test_production_configuration_loads() -> None:
    configuration = load_configuration()

    assert configuration.environment == "production"
    assert (
        configuration.policy_version
        == "deterministic-policy-v1"
    )
    assert (
        configuration.runtime_version
        == "isolated-tool-runtime-v1"
    )


def test_missing_secret_reference_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="SECRET_REFERENCE_MISSING",
    ):
        load_production_configuration(
            path=CONFIGURATION_PATH,
            environment={},
        )


def test_inline_secret_is_detected() -> None:
    payload = json.loads(
        CONFIGURATION_PATH.read_text(
            encoding="utf-8"
        )
    )
    payload["api_key"] = "inline-secret"

    errors = validate_configuration_payload(
        payload=payload,
        environment={
            "RELEASE_ATTESTATION_KEY":
                SIGNING_KEY,
        },
    )

    assert any(
        error.code
        is HardeningErrorCode.INLINE_SECRET_DETECTED
        for error in errors
    )


def test_provider_timeout_must_be_lower_than_request_timeout() -> None:
    payload = json.loads(
        CONFIGURATION_PATH.read_text(
            encoding="utf-8"
        )
    )
    payload["provider_timeout_seconds"] = 30.0
    payload["request_timeout_seconds"] = 30.0

    errors = validate_configuration_payload(
        payload=payload,
        environment={
            "RELEASE_ATTESTATION_KEY":
                SIGNING_KEY,
        },
    )

    assert any(
        "Provider timeout" in error.message
        for error in errors
    )


def test_configuration_digest_is_reproducible() -> None:
    configuration = load_configuration()

    first = configuration_sha256(configuration)
    second = configuration_sha256(configuration)

    assert first == second
    assert len(first) == 64


def test_recursive_log_redaction() -> None:
    value = {
        "authorization": "Bearer secret",
        "nested": {
            "api_key": "secret-key",
            "status": "ok",
        },
        "items": [
            {
                "password": "secret-password",
            }
        ],
    }

    redacted = redact_value(value)

    assert (
        redacted["authorization"]
        == "[REDACTED]"
    )
    assert (
        redacted["nested"]["api_key"]
        == "[REDACTED]"
    )
    assert redacted["nested"]["status"] == "ok"
    assert (
        redacted["items"][0]["password"]
        == "[REDACTED]"
    )


def test_structured_log_preserves_trace_binding() -> None:
    event = create_structured_log_event(
        event_type="workflow_started",
        trace_id="trace-123",
        workflow_id="workflow-123",
        severity="INFO",
        attributes={
            "token": "secret",
            "service": "identity-api",
        },
    )

    assert event.trace_id == "trace-123"
    assert event.workflow_id == "workflow-123"
    assert (
        event.attributes["token"]
        == "[REDACTED]"
    )


def test_rate_limiter_rejects_excess_request() -> None:
    limiter = SlidingWindowRateLimiter(
        maximum_requests=2,
        window_seconds=60.0,
    )

    assert limiter.allow("user-1", 1000.0)[0]
    assert limiter.allow("user-1", 1001.0)[0]

    allowed, error = limiter.allow(
        "user-1",
        1002.0,
    )

    assert not allowed
    assert error is not None
    assert (
        error.code
        is HardeningErrorCode.RATE_LIMIT_EXCEEDED
    )


def test_rate_limiter_window_expires() -> None:
    limiter = SlidingWindowRateLimiter(
        maximum_requests=1,
        window_seconds=60.0,
    )

    assert limiter.allow("user-1", 1000.0)[0]
    assert not limiter.allow("user-1", 1059.0)[0]
    assert limiter.allow("user-1", 1060.0)[0]


def test_concurrency_limiter_rejects_excess_slot() -> None:
    limiter = ConcurrencyLimiter(
        maximum_concurrent=1
    )

    assert limiter.acquire()[0]

    allowed, error = limiter.acquire()

    assert not allowed
    assert error is not None
    assert (
        error.code
        is HardeningErrorCode
        .CONCURRENCY_LIMIT_EXCEEDED
    )

    limiter.release()

    assert limiter.active == 0


def test_circuit_breaker_opens_at_threshold() -> None:
    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_seconds=30.0,
    )

    breaker.record_failure(1000.0)

    assert breaker.state is CircuitState.CLOSED

    breaker.record_failure(1001.0)

    assert breaker.state is CircuitState.OPEN
    assert not breaker.allow_request(1002.0)[0]


def test_circuit_breaker_enters_half_open_after_recovery() -> None:
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_seconds=30.0,
    )

    breaker.record_failure(1000.0)

    allowed, error = breaker.allow_request(
        1030.0
    )

    assert allowed
    assert error is None
    assert (
        breaker.state
        is CircuitState.HALF_OPEN
    )


def test_circuit_breaker_success_closes_circuit() -> None:
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_seconds=30.0,
    )

    breaker.record_failure(1000.0)
    assert breaker.allow_request(1030.0)[0]

    breaker.record_success()

    assert breaker.state is CircuitState.CLOSED
    assert breaker.consecutive_failures == 0


def test_release_attestation_verifies() -> None:
    attestation = build_attestation()

    assert verify_release_attestation(
        attestation=attestation,
        signing_key=SIGNING_KEY,
    )


def test_tampered_attestation_is_rejected() -> None:
    attestation = build_attestation()

    tampered = replace(
        attestation,
        evidence_sha256="b" * 64,
    )

    assert not verify_release_attestation(
        attestation=tampered,
        signing_key=SIGNING_KEY,
    )


def test_ready_release_is_approved() -> None:
    report = build_readiness()
    attestation = build_attestation()

    promotion = evaluate_promotion(
        report=report,
        attestation=attestation,
    )

    assert (
        report.status
        is ReadinessStatus.READY
    )
    assert (
        promotion.decision
        is PromotionDecision.APPROVE
    )


def test_failed_release_gate_blocks_promotion() -> None:
    report = build_readiness(
        release_gate_passed=False
    )
    attestation = build_attestation()

    promotion = evaluate_promotion(
        report=report,
        attestation=attestation,
    )

    assert (
        report.status
        is ReadinessStatus.BLOCKED
    )
    assert (
        promotion.decision
        is PromotionDecision.REJECT
    )
    assert any(
        "release_gate" in reason
        for reason in promotion.reasons
    )


def test_missing_rollback_plan_blocks_promotion() -> None:
    report = build_readiness(
        rollback_plan_exists=False
    )

    assert (
        report.status
        is ReadinessStatus.BLOCKED
    )

    failed = {
        check.check_name
        for check in report.checks
        if not check.passed
    }

    assert "rollback_plan" in failed


def test_insufficient_evidence_blocks_promotion() -> None:
    report = build_readiness(
        evidence_artifact_count=2
    )

    assert (
        report.status
        is ReadinessStatus.BLOCKED
    )

    failed = {
        check.check_name
        for check in report.checks
        if not check.passed
    }

    assert (
        "minimum_evidence_artifacts"
        in failed
    )


@pytest.mark.parametrize(
    "failure_mode",
    tuple(FailureMode),
)
def test_failure_injection_does_not_expand_authority(
    failure_mode,
) -> None:
    result = inject_failure(failure_mode)

    assert result.failure_observed
    assert not result.sensitive_details_exposed
    assert not result.authority_expanded


def test_readiness_report_cannot_deploy() -> None:
    report = build_readiness()

    assert "cannot deploy" in (
        report.authority_boundary
    )
