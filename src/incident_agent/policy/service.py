"""Policy-context construction from governed upstream evidence."""

from __future__ import annotations

from incident_agent.evaluation.ambiguity import (
    AmbiguityResult,
)
from incident_agent.genai.contracts import (
    SynthesisResponse,
)
from incident_agent.policy.contracts import (
    HumanApproval,
    PolicyContext,
    PolicyEvaluation,
    PolicyIdentity,
)
from incident_agent.policy.engine import (
    evaluate_tool_recommendation,
)
from incident_agent.retrieval.contracts import (
    RetrievalResponse,
)


def build_policy_context(
    identity: PolicyIdentity,
    request_tenant_id: str,
    service: str,
    environment: str,
    ambiguity_result: AmbiguityResult,
    retrieval_response: RetrievalResponse,
    approvals: tuple[HumanApproval, ...] = (),
) -> PolicyContext:
    """Build policy context from trusted system boundaries."""

    return PolicyContext(
        identity=identity,
        request_tenant_id=request_tenant_id,
        service=service,
        environment=environment,
        authorized_citations=tuple(
            result.citation
            for result in retrieval_response.results
        ),
        denied_document_ids=tuple(
            denied.document_id
            for denied
            in retrieval_response.denied_documents
        ),
        classifiers_agree=(
            ambiguity_result.classifiers_agree
        ),
        ml_probability_margin=(
            ambiguity_result.ml_probability_margin
        ),
        approvals=approvals,
    )


def evaluate_synthesis_policy(
    synthesis: SynthesisResponse,
    context: PolicyContext,
) -> PolicyEvaluation:
    """Evaluate synthesis output through deterministic policy."""

    return evaluate_tool_recommendation(
        synthesis=synthesis,
        context=context,
    )
