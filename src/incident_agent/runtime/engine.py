"""Isolated execution boundary for policy-authorized tools."""

from __future__ import annotations

import concurrent.futures
import time

from incident_agent.genai.contracts import (
    SynthesisResponse,
)
from incident_agent.policy.contracts import (
    PolicyContext,
    PolicyDecision,
    PolicyEvaluation,
)
from incident_agent.policy.fingerprint import (
    build_request_fingerprint,
)
from incident_agent.runtime.contracts import (
    AuditEvent,
    ExecutionRecord,
    ExecutionStatus,
    RuntimeError,
    RuntimeErrorCode,
    RuntimeToolRequest,
)
from incident_agent.runtime.idempotency import (
    InMemoryIdempotencyStore,
)
from incident_agent.runtime.registry import (
    RUNTIME_TOOLS,
    RUNTIME_VERSION,
)


class IsolatedToolRuntime:
    """Policy-bound and replay-protected tool runtime."""

    def __init__(
        self,
        idempotency_store: (
            InMemoryIdempotencyStore | None
        ) = None,
    ) -> None:
        self._idempotency_store = (
            idempotency_store
            or InMemoryIdempotencyStore()
        )

    def execute(
        self,
        request: RuntimeToolRequest,
        synthesis: SynthesisResponse,
        policy_evaluation: PolicyEvaluation,
        policy_context: PolicyContext,
        now_epoch_seconds: float | None = None,
    ) -> ExecutionRecord:
        """Validate and execute one authorized request."""

        now = (
            time.time()
            if now_epoch_seconds is None
            else now_epoch_seconds
        )

        initial_event = _audit_event(
            request=request,
            status=ExecutionStatus.REJECTED,
            event_type="runtime_request_received",
            detail="Runtime request received.",
        )

        existing = self._idempotency_store.get(
            request.idempotency_key
        )

        if existing is not None:
            replay_record = ExecutionRecord(
                request_id=request.request_id,
                idempotency_key=request.idempotency_key,
                tool_name=request.tool_name,
                status=ExecutionStatus.REPLAYED,
                result=existing.result,
                error=RuntimeError(
                    code=(
                        RuntimeErrorCode
                        .IDEMPOTENCY_KEY_REUSED
                    ),
                    message=(
                        "Idempotency key was previously used. "
                        "The handler was not executed again."
                    ),
                    retryable=False,
                ),
                audit_events=(
                    initial_event,
                    _audit_event(
                        request=request,
                        status=ExecutionStatus.REPLAYED,
                        event_type="runtime_replay_blocked",
                        detail=(
                            "Replay blocked by idempotency "
                            "protection."
                        ),
                    ),
                ),
                execution_attempted=False,
                policy_fingerprint=(
                    request.policy_fingerprint
                ),
                runtime_version=RUNTIME_VERSION,
                authority_boundary=(
                    "The runtime executes only policy-bound "
                    "requests and does not grant authority."
                ),
            )

            return replay_record

        rejection = self._validate_request(
            request=request,
            synthesis=synthesis,
            policy_evaluation=policy_evaluation,
            policy_context=policy_context,
            now=now,
        )

        if rejection is not None:
            record = _rejected_record(
                request=request,
                error=rejection,
                initial_event=initial_event,
            )

            self._idempotency_store.save(
                request.idempotency_key,
                record,
            )

            return record

        tool_definition = RUNTIME_TOOLS[
            request.tool_name
        ]

        attempt_events: list[AuditEvent] = [
            initial_event,
            _audit_event(
                request=request,
                status=ExecutionStatus.SUCCEEDED,
                event_type="runtime_policy_binding_validated",
                detail=(
                    "ALLOW decision, fingerprint, tool, "
                    "risk, and arguments validated."
                ),
            ),
        ]

        last_error: RuntimeError | None = None

        for attempt_number in range(
            1,
            tool_definition.maximum_attempts + 1,
        ):
            attempt_events.append(
                _audit_event(
                    request=request,
                    status=ExecutionStatus.SUCCEEDED,
                    event_type="runtime_execution_attempt",
                    detail=(
                        f"Execution attempt "
                        f"{attempt_number} started."
                    ),
                )
            )

            try:
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=1
                ) as executor:
                    future = executor.submit(
                        tool_definition.handler,
                        request.arguments,
                        request.dry_run,
                    )

                    result = future.result(
                        timeout=(
                            tool_definition
                            .timeout_seconds
                        )
                    )

                record = ExecutionRecord(
                    request_id=request.request_id,
                    idempotency_key=(
                        request.idempotency_key
                    ),
                    tool_name=request.tool_name,
                    status=ExecutionStatus.SUCCEEDED,
                    result=result,
                    error=None,
                    audit_events=(
                        *attempt_events,
                        _audit_event(
                            request=request,
                            status=(
                                ExecutionStatus
                                .SUCCEEDED
                            ),
                            event_type=(
                                "runtime_execution_succeeded"
                            ),
                            detail=(
                                "Tool handler completed "
                                "successfully."
                            ),
                        ),
                    ),
                    execution_attempted=True,
                    policy_fingerprint=(
                        request.policy_fingerprint
                    ),
                    runtime_version=RUNTIME_VERSION,
                    authority_boundary=(
                        "The runtime executed a request "
                        "authorized by deterministic policy. "
                        "It did not create or expand authority."
                    ),
                )

                self._idempotency_store.save(
                    request.idempotency_key,
                    record,
                )

                return record

            except concurrent.futures.TimeoutError:
                last_error = RuntimeError(
                    code=(
                        RuntimeErrorCode
                        .EXECUTION_TIMEOUT
                    ),
                    message=(
                        "Tool handler exceeded its runtime "
                        "timeout."
                    ),
                    retryable=(
                        attempt_number
                        < tool_definition.maximum_attempts
                    ),
                )

            except Exception as exc:
                last_error = RuntimeError(
                    code=RuntimeErrorCode.HANDLER_FAILURE,
                    message=(
                        "Tool handler failed without exposing "
                        f"sensitive internals: "
                        f"{type(exc).__name__}"
                    ),
                    retryable=(
                        attempt_number
                        < tool_definition.maximum_attempts
                    ),
                )

            attempt_events.append(
                _audit_event(
                    request=request,
                    status=ExecutionStatus.FAILED,
                    event_type="runtime_execution_failed",
                    detail=last_error.message,
                )
            )

        final_status = (
            ExecutionStatus.TIMED_OUT
            if last_error is not None
            and last_error.code
            is RuntimeErrorCode.EXECUTION_TIMEOUT
            else ExecutionStatus.FAILED
        )

        record = ExecutionRecord(
            request_id=request.request_id,
            idempotency_key=request.idempotency_key,
            tool_name=request.tool_name,
            status=final_status,
            result=None,
            error=last_error,
            audit_events=tuple(attempt_events),
            execution_attempted=True,
            policy_fingerprint=(
                request.policy_fingerprint
            ),
            runtime_version=RUNTIME_VERSION,
            authority_boundary=(
                "The runtime attempted only a request "
                "authorized by deterministic policy."
            ),
        )

        self._idempotency_store.save(
            request.idempotency_key,
            record,
        )

        return record

    def _validate_request(
        self,
        request: RuntimeToolRequest,
        synthesis: SynthesisResponse,
        policy_evaluation: PolicyEvaluation,
        policy_context: PolicyContext,
        now: float,
    ) -> RuntimeError | None:
        if (
            policy_evaluation.decision
            is not PolicyDecision.ALLOW
        ):
            return RuntimeError(
                code=(
                    RuntimeErrorCode.POLICY_NOT_ALLOWED
                ),
                message=(
                    "Runtime requires a deterministic "
                    "ALLOW decision."
                ),
                retryable=False,
            )

        if (
            request.policy_fingerprint
            != policy_evaluation.request_fingerprint
        ):
            return RuntimeError(
                code=(
                    RuntimeErrorCode
                    .POLICY_FINGERPRINT_MISMATCH
                ),
                message=(
                    "Runtime request is not bound to the "
                    "supplied policy decision."
                ),
                retryable=False,
            )

        recomputed_fingerprint = (
            build_request_fingerprint(
                synthesis=synthesis,
                context=policy_context,
            )
        )

        if (
            recomputed_fingerprint
            != policy_evaluation.request_fingerprint
        ):
            return RuntimeError(
                code=(
                    RuntimeErrorCode
                    .POLICY_FINGERPRINT_MISMATCH
                ),
                message=(
                    "Synthesis or policy context changed "
                    "after policy evaluation."
                ),
                retryable=False,
            )

        recommendation = synthesis.tool_recommendation

        if recommendation is None:
            return RuntimeError(
                code=RuntimeErrorCode.TOOL_NAME_MISMATCH,
                message=(
                    "Synthesis contains no tool "
                    "recommendation."
                ),
                retryable=False,
            )

        if (
            policy_evaluation.tool_name
            != request.tool_name
            or recommendation.tool_name
            != request.tool_name
        ):
            return RuntimeError(
                code=RuntimeErrorCode.TOOL_NAME_MISMATCH,
                message=(
                    "Runtime, policy, and synthesis tool "
                    "names do not match."
                ),
                retryable=False,
            )

        tool_definition = RUNTIME_TOOLS.get(
            request.tool_name
        )

        if tool_definition is None:
            return RuntimeError(
                code=(
                    RuntimeErrorCode.TOOL_NOT_REGISTERED
                ),
                message=(
                    "Tool is not registered in the isolated "
                    "runtime."
                ),
                retryable=False,
            )

        if (
            request.declared_risk
            is not tool_definition.risk
            or recommendation.risk
            is not tool_definition.risk
        ):
            return RuntimeError(
                code=RuntimeErrorCode.RISK_MISMATCH,
                message=(
                    "Runtime request risk does not match "
                    "the registered tool risk."
                ),
                retryable=False,
            )

        required_arguments = set(
            tool_definition.required_arguments
        )
        supplied_arguments = set(
            request.arguments
        )

        if supplied_arguments != required_arguments:
            return RuntimeError(
                code=(
                    RuntimeErrorCode
                    .ARGUMENT_SCHEMA_INVALID
                ),
                message=(
                    "Runtime arguments do not exactly match "
                    "the registered schema."
                ),
                retryable=False,
            )

        if request.arguments != recommendation.arguments:
            return RuntimeError(
                code=(
                    RuntimeErrorCode
                    .ARGUMENT_SCHEMA_INVALID
                ),
                message=(
                    "Runtime arguments differ from the "
                    "policy-evaluated recommendation."
                ),
                retryable=False,
            )

        if (
            request.arguments.get("service")
            != request.service
            or request.arguments.get("environment")
            != request.environment
        ):
            return RuntimeError(
                code=(
                    RuntimeErrorCode
                    .ARGUMENT_SCHEMA_INVALID
                ),
                message=(
                    "Runtime argument scope does not match "
                    "the request scope."
                ),
                retryable=False,
            )

        if (
            tool_definition.dry_run_required
            and not request.dry_run
        ):
            return RuntimeError(
                code=RuntimeErrorCode.DRY_RUN_REQUIRED,
                message=(
                    "This tutorial runtime permits the tool "
                    "only in dry-run mode."
                ),
                retryable=False,
            )

        if now > request.expires_at_epoch_seconds:
            return RuntimeError(
                code=RuntimeErrorCode.REQUEST_EXPIRED,
                message=(
                    "Runtime request has passed its expiry."
                ),
                retryable=False,
            )

        if (
            request.created_at_epoch_seconds
            > request.expires_at_epoch_seconds
        ):
            return RuntimeError(
                code=RuntimeErrorCode.REQUEST_EXPIRED,
                message=(
                    "Runtime request timestamps are invalid."
                ),
                retryable=False,
            )

        return None


def _rejected_record(
    request: RuntimeToolRequest,
    error: RuntimeError,
    initial_event: AuditEvent,
) -> ExecutionRecord:
    return ExecutionRecord(
        request_id=request.request_id,
        idempotency_key=request.idempotency_key,
        tool_name=request.tool_name,
        status=ExecutionStatus.REJECTED,
        result=None,
        error=error,
        audit_events=(
            initial_event,
            _audit_event(
                request=request,
                status=ExecutionStatus.REJECTED,
                event_type="runtime_request_rejected",
                detail=error.message,
            ),
        ),
        execution_attempted=False,
        policy_fingerprint=request.policy_fingerprint,
        runtime_version=RUNTIME_VERSION,
        authority_boundary=(
            "The runtime rejected the request before "
            "handler execution."
        ),
    )


def _audit_event(
    request: RuntimeToolRequest,
    status: ExecutionStatus,
    event_type: str,
    detail: str,
) -> AuditEvent:
    return AuditEvent(
        event_type=event_type,
        request_id=request.request_id,
        idempotency_key=request.idempotency_key,
        tool_name=request.tool_name,
        policy_fingerprint=request.policy_fingerprint,
        status=status,
        detail=detail,
    )
