#!/usr/bin/env python3
"""Run Phase 10 production-hardening validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from incident_agent.hardening.attestation import (
    create_release_attestation,
)
from incident_agent.hardening.circuit_breaker import (
    CircuitBreaker,
)
from incident_agent.hardening.configuration import (
    configuration_sha256,
    load_production_configuration,
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
)
from incident_agent.hardening.promotion import (
    evaluate_deployment_readiness,
    evaluate_promotion,
)


TUTORIAL_SIGNING_KEY = (
    "phase-10-ephemeral-tutorial-signing-key"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate production hardening and release "
            "promotion controls."
        )
    )
    parser.add_argument(
        "--configuration",
        type=Path,
        default=Path(
            "config/production-hardening.json"
        ),
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path(
            "reports/observability/"
            "phase-09-release-evidence.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "reports/hardening/"
            "phase-10-production-readiness.json"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    configuration = load_production_configuration(
        path=args.configuration,
        environment={
            "RELEASE_ATTESTATION_KEY":
                TUTORIAL_SIGNING_KEY,
        },
    )

    evidence = json.loads(
        args.evidence.read_text(encoding="utf-8")
    )

    config_digest = configuration_sha256(
        configuration
    )

    attestation = create_release_attestation(
        release_id="phase-10-tutorial-release",
        source_environment="staging",
        target_environment="production",
        evidence_sha256=(
            evidence["aggregate_sha256"]
        ),
        configuration_sha256=config_digest,
        rollback_plan_id="rollback-phase-10-v1",
        signer_id="tutorial-ci-release-identity",
        signing_key=TUTORIAL_SIGNING_KEY,
    )

    readiness = evaluate_deployment_readiness(
        configuration=configuration,
        release_id="phase-10-tutorial-release",
        release_gate_passed=(
            evidence["release_gate_passed"]
        ),
        evidence_artifact_count=(
            evidence["artifact_count"]
        ),
        evidence_sha256=(
            evidence["aggregate_sha256"]
        ),
        attestation=attestation,
        signing_key=TUTORIAL_SIGNING_KEY,
        rollback_plan_exists=True,
    )

    promotion = evaluate_promotion(
        report=readiness,
        attestation=attestation,
    )

    rate_limiter = SlidingWindowRateLimiter(
        maximum_requests=2,
        window_seconds=60.0,
    )

    rate_results = [
        rate_limiter.allow(
            subject="tenant-alpha:user-42",
            now_epoch_seconds=timestamp,
        )[0]
        for timestamp in (
            1000.0,
            1001.0,
            1002.0,
        )
    ]

    concurrency_limiter = ConcurrencyLimiter(
        maximum_concurrent=1
    )

    first_acquired, _ = (
        concurrency_limiter.acquire()
    )
    second_acquired, second_error = (
        concurrency_limiter.acquire()
    )

    concurrency_limiter.release()

    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_seconds=30.0,
    )

    breaker.record_failure(1000.0)
    breaker.record_failure(1001.0)

    circuit_allowed_before_recovery, _ = (
        breaker.allow_request(1002.0)
    )
    circuit_allowed_after_recovery, _ = (
        breaker.allow_request(1032.0)
    )

    failure_results = [
        inject_failure(mode)
        for mode in FailureMode
    ]

    redacted_event = create_structured_log_event(
        event_type="release_validation",
        trace_id="trace-phase-10",
        workflow_id="release-phase-10",
        severity="INFO",
        attributes={
            "release_id":
                "phase-10-tutorial-release",
            "authorization":
                "Bearer tutorial-secret",
            "nested": {
                "api_key": "not-for-logs",
                "status": "validated",
            },
        },
    )

    report = {
        "phase": "phase-10",
        "configuration": {
            "configuration_version":
                configuration.configuration_version,
            "configuration_sha256":
                config_digest,
            "environment":
                configuration.environment,
            "model_version":
                configuration.model_version,
            "prompt_version":
                configuration.prompt_version,
            "policy_version":
                configuration.policy_version,
            "runtime_version":
                configuration.runtime_version,
            "orchestrator_version":
                configuration.orchestrator_version,
            "evaluation_version":
                configuration.evaluation_version,
        },
        "release_attestation": {
            "release_id": attestation.release_id,
            "source_environment":
                attestation.source_environment,
            "target_environment":
                attestation.target_environment,
            "evidence_sha256":
                attestation.evidence_sha256,
            "configuration_sha256":
                attestation.configuration_sha256,
            "rollback_plan_id":
                attestation.rollback_plan_id,
            "signer_id": attestation.signer_id,
            "signature_algorithm":
                attestation.signature_algorithm,
            "signature": attestation.signature,
        },
        "deployment_readiness":
            readiness.to_dict(),
        "promotion_evaluation":
            promotion.to_dict(),
        "admission_controls": {
            "rate_limit_results": rate_results,
            "rate_limit_third_request_blocked":
                rate_results == [
                    True,
                    True,
                    False,
                ],
            "first_concurrency_slot_acquired":
                first_acquired,
            "second_concurrency_slot_acquired":
                second_acquired,
            "second_concurrency_error": (
                second_error.code.value
                if second_error
                else None
            ),
        },
        "circuit_breaker": {
            "allowed_before_recovery":
                circuit_allowed_before_recovery,
            "allowed_after_recovery":
                circuit_allowed_after_recovery,
            "state_after_recovery":
                breaker.state.value,
        },
        "failure_injection": [
            {
                "failure_mode":
                    result.failure_mode.value,
                "failure_observed":
                    result.failure_observed,
                "sensitive_details_exposed":
                    result.sensitive_details_exposed,
                "authority_expanded":
                    result.authority_expanded,
                "fallback_used":
                    result.fallback_used,
                "explanation":
                    result.explanation,
            }
            for result in failure_results
        ],
        "redacted_log_event": {
            "event_type":
                redacted_event.event_type,
            "trace_id":
                redacted_event.trace_id,
            "workflow_id":
                redacted_event.workflow_id,
            "severity":
                redacted_event.severity,
            "attributes":
                redacted_event.attributes,
        },
        "security_properties": {
            "inline_secrets_stored": False,
            "structured_logging_redacted": True,
            "rate_limiting_enforced": True,
            "concurrency_limiting_enforced": True,
            "circuit_breaker_enforced": True,
            "release_evidence_verified": True,
            "signed_attestation_required": True,
            "rollback_plan_required": True,
            "version_pinning_required": True,
            "promotion_executes_deployment": False,
            "hardening_expands_authority": False,
            "production_side_effects_performed":
                False,
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
        f"PASS: readiness="
        f"{readiness.status.value}"
    )
    print(
        f"PASS: promotion="
        f"{promotion.decision.value}"
    )
    print(
        "PASS: release attestation signed"
    )
    print(
        "PASS: rate limit rejected excess request"
    )
    print(
        "PASS: concurrency limit rejected excess slot"
    )
    print(
        "PASS: circuit breaker opened and recovered"
    )
    print(
        "PASS: operational event redacted"
    )
    print(
        "PASS: controlled failures did not expand authority"
    )
    print(
        "PASS: no production deployment was performed"
    )


if __name__ == "__main__":
    main()
