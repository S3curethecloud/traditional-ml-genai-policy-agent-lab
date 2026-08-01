"""Construction and execution services for the isolated runtime."""

from __future__ import annotations

import time
import uuid

from incident_agent.genai.contracts import (
    SynthesisResponse,
)
from incident_agent.policy.contracts import (
    PolicyContext,
    PolicyEvaluation,
    PolicyIdentity,
)
from incident_agent.runtime.contracts import (
    ExecutionRecord,
    RuntimeIdentity,
    RuntimeToolRequest,
)
from incident_agent.runtime.engine import (
    IsolatedToolRuntime,
)


def build_runtime_request(
    synthesis: SynthesisResponse,
    policy_evaluation: PolicyEvaluation,
    policy_identity: PolicyIdentity,
    service: str,
    environment: str,
    idempotency_key: str,
    now_epoch_seconds: float | None = None,
    lifetime_seconds: float = 60.0,
    dry_run: bool = False,
) -> RuntimeToolRequest:
    """Build a typed runtime request from governed outputs."""

    recommendation = synthesis.tool_recommendation

    if recommendation is None:
        raise ValueError(
            "Cannot build runtime request without a "
            "tool recommendation"
        )

    current_time = (
        time.time()
        if now_epoch_seconds is None
        else now_epoch_seconds
    )

    return RuntimeToolRequest(
        request_id=str(uuid.uuid4()),
        idempotency_key=idempotency_key,
        tool_name=recommendation.tool_name,
        arguments=dict(recommendation.arguments),
        declared_risk=recommendation.risk,
        identity=RuntimeIdentity(
            user_id=policy_identity.user_id,
            tenant_id=policy_identity.tenant_id,
            roles=policy_identity.roles,
        ),
        service=service,
        environment=environment,
        policy_fingerprint=(
            policy_evaluation.request_fingerprint
        ),
        created_at_epoch_seconds=current_time,
        expires_at_epoch_seconds=(
            current_time + lifetime_seconds
        ),
        dry_run=dry_run,
    )


def execute_authorized_request(
    runtime: IsolatedToolRuntime,
    request: RuntimeToolRequest,
    synthesis: SynthesisResponse,
    policy_evaluation: PolicyEvaluation,
    policy_context: PolicyContext,
    now_epoch_seconds: float | None = None,
) -> ExecutionRecord:
    """Execute through the isolated runtime boundary."""

    return runtime.execute(
        request=request,
        synthesis=synthesis,
        policy_evaluation=policy_evaluation,
        policy_context=policy_context,
        now_epoch_seconds=now_epoch_seconds,
    )
