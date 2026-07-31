"""Tests for the Phase 6 deterministic policy engine."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from incident_agent.evaluation.ambiguity import (
    evaluate_ambiguity_pack,
    load_ambiguity_pack,
)
from incident_agent.genai.contracts import (
    SynthesisDisposition,
    ToolRecommendation,
    ToolRisk,
)
from incident_agent.genai.provider import (
    DeterministicTutorialProvider,
)
from incident_agent.genai.service import (
    build_synthesis_request,
    synthesize_evidence,
)
from incident_agent.ml.inference import (
    IncidentClassifier,
)
from incident_agent.policy.contracts import (
    HumanApproval,
    PolicyDecision,
    PolicyIdentity,
)
from incident_agent.policy.engine import (
    evaluate_tool_recommendation,
)
from incident_agent.policy.registry import (
    POLICY_VERSION,
)
from incident_agent.policy.service import (
    build_policy_context,
)
from incident_agent.retrieval.contracts import (
    RetrievalIdentity,
    RetrievalQuery,
    RetrievalScope,
)
from incident_agent.retrieval.engine import (
    retrieve_documents,
)
from incident_agent.retrieval.loader import (
    load_knowledge_corpus,
)
from incident_agent.retrieval.planning import (
    build_retrieval_query_text,
)


KNOWLEDGE_DIRECTORY = Path("data/knowledge")
AMBIGUITY_PACK = Path(
    "data/ambiguity/phase-3b-cases.yaml"
)
MODEL_DIRECTORY = Path(
    "models/incident-classifier"
)


def build_policy_inputs(
    case_id: str = (
        "recent-deployment-with-authentication-signals"
    ),
):
    documents = load_knowledge_corpus(
        KNOWLEDGE_DIRECTORY
    )
    classifier = IncidentClassifier.load(
        MODEL_DIRECTORY
    )
    cases = load_ambiguity_pack(
        AMBIGUITY_PACK
    )

    ambiguity_results = evaluate_ambiguity_pack(
        cases,
        classifier,
    )

    ambiguity_result = next(
        result
        for result in ambiguity_results
        if result.case_id == case_id
    )

    retrieval_identity = RetrievalIdentity(
        user_id="engineer-42",
        tenant_id="tenant-alpha",
        roles=("incident_responder",),
    )

    retrieval_response = retrieve_documents(
        documents=documents,
        query=RetrievalQuery(
            query_text=build_retrieval_query_text(
                ambiguity_result
            ),
            identity=retrieval_identity,
            scope=RetrievalScope(
                service="identity-api",
                environment="production",
            ),
            maximum_results=5,
        ),
    )

    synthesis_request = build_synthesis_request(
        ambiguity_result,
        retrieval_response,
    )

    synthesis_response = synthesize_evidence(
        synthesis_request,
        DeterministicTutorialProvider(),
    )

    context = build_policy_context(
        identity=PolicyIdentity(
            user_id="engineer-42",
            tenant_id="tenant-alpha",
            roles=("incident_responder",),
        ),
        request_tenant_id="tenant-alpha",
        service="identity-api",
        environment="production",
        ambiguity_result=ambiguity_result,
        retrieval_response=retrieval_response,
    )

    return (
        ambiguity_result,
        retrieval_response,
        synthesis_response,
        context,
    )


def reason_ids(evaluation) -> set[str]:
    return {
        reason.rule_id
        for reason in evaluation.reasons
    }


def test_read_only_tool_can_be_allowed() -> None:
    (
        _,
        _,
        synthesis,
        context,
    ) = build_policy_inputs(
        "dependency-errors-with-network-loss"
    )

    safe_synthesis = replace(
        synthesis,
        ignored_untrusted_instructions=(),
    )

    evaluation = evaluate_tool_recommendation(
        safe_synthesis,
        context,
    )

    assert evaluation.decision is PolicyDecision.ALLOW
    assert "POL-ALLOW-001" in reason_ids(
        evaluation
    )


def test_policy_never_executes_tool() -> None:
    _, _, synthesis, context = build_policy_inputs()

    evaluation = evaluate_tool_recommendation(
        synthesis,
        context,
    )

    assert evaluation.execution_performed is False
    assert "does not execute" in (
        evaluation.authority_boundary
    )


def test_cross_tenant_identity_is_denied() -> None:
    _, _, synthesis, context = build_policy_inputs()

    invalid_context = replace(
        context,
        identity=replace(
            context.identity,
            tenant_id="tenant-beta",
        ),
    )

    evaluation = evaluate_tool_recommendation(
        synthesis,
        invalid_context,
    )

    assert evaluation.decision is PolicyDecision.DENY
    assert "POL-TENANT-001" in reason_ids(
        evaluation
    )


def test_unknown_tool_is_denied() -> None:
    _, _, synthesis, context = build_policy_inputs()

    assert synthesis.tool_recommendation is not None

    invalid_synthesis = replace(
        synthesis,
        tool_recommendation=replace(
            synthesis.tool_recommendation,
            tool_name="delete_production_database",
        ),
    )

    evaluation = evaluate_tool_recommendation(
        invalid_synthesis,
        context,
    )

    assert evaluation.decision is PolicyDecision.DENY
    assert "POL-TOOL-002" in reason_ids(
        evaluation
    )


def test_risk_mismatch_is_denied() -> None:
    _, _, synthesis, context = build_policy_inputs()

    assert synthesis.tool_recommendation is not None

    invalid_synthesis = replace(
        synthesis,
        tool_recommendation=replace(
            synthesis.tool_recommendation,
            risk=ToolRisk.HIGH_IMPACT,
        ),
    )

    evaluation = evaluate_tool_recommendation(
        invalid_synthesis,
        context,
    )

    assert evaluation.decision is PolicyDecision.DENY
    assert "POL-TOOL-003" in reason_ids(
        evaluation
    )


def test_missing_argument_is_denied() -> None:
    _, _, synthesis, context = build_policy_inputs()

    assert synthesis.tool_recommendation is not None

    invalid_synthesis = replace(
        synthesis,
        tool_recommendation=replace(
            synthesis.tool_recommendation,
            arguments={
                "service": "identity-api",
            },
        ),
    )

    evaluation = evaluate_tool_recommendation(
        invalid_synthesis,
        context,
    )

    assert evaluation.decision is PolicyDecision.DENY
    assert "POL-ARG-001" in reason_ids(
        evaluation
    )


def test_unexpected_argument_is_denied() -> None:
    _, _, synthesis, context = build_policy_inputs()

    assert synthesis.tool_recommendation is not None

    invalid_synthesis = replace(
        synthesis,
        tool_recommendation=replace(
            synthesis.tool_recommendation,
            arguments={
                "service": "identity-api",
                "environment": "production",
                "force": "true",
            },
        ),
    )

    evaluation = evaluate_tool_recommendation(
        invalid_synthesis,
        context,
    )

    assert evaluation.decision is PolicyDecision.DENY
    assert "POL-ARG-002" in reason_ids(
        evaluation
    )


def test_service_scope_mismatch_is_denied() -> None:
    _, _, synthesis, context = build_policy_inputs()

    assert synthesis.tool_recommendation is not None

    invalid_synthesis = replace(
        synthesis,
        tool_recommendation=replace(
            synthesis.tool_recommendation,
            arguments={
                "service": "payments-api",
                "environment": "production",
            },
        ),
    )

    evaluation = evaluate_tool_recommendation(
        invalid_synthesis,
        context,
    )

    assert evaluation.decision is PolicyDecision.DENY
    assert "POL-SCOPE-001" in reason_ids(
        evaluation
    )


def test_unauthorized_role_is_denied() -> None:
    _, _, synthesis, context = build_policy_inputs()

    invalid_context = replace(
        context,
        identity=replace(
            context.identity,
            roles=("auditor",),
        ),
    )

    evaluation = evaluate_tool_recommendation(
        synthesis,
        invalid_context,
    )

    assert evaluation.decision is PolicyDecision.DENY
    assert "POL-ROLE-001" in reason_ids(
        evaluation
    )


def test_prompt_injection_finding_escalates() -> None:
    _, _, synthesis, context = build_policy_inputs()

    synthesis_with_injection = replace(
        synthesis,
        ignored_untrusted_instructions=(
            "untrusted-injected-operational-note",
        ),
    )

    evaluation = evaluate_tool_recommendation(
        synthesis_with_injection,
        context,
    )

    assert (
        evaluation.decision
        is PolicyDecision.ESCALATE
    )
    assert "POL-INJECTION-001" in reason_ids(
        evaluation
    )


def test_unauthorized_citation_is_denied() -> None:
    _, _, synthesis, context = build_policy_inputs()

    invalid_synthesis = replace(
        synthesis,
        citations=(
            *synthesis.citations,
            "[not-authorized]",
        ),
    )

    evaluation = evaluate_tool_recommendation(
        invalid_synthesis,
        context,
    )

    assert evaluation.decision is PolicyDecision.DENY
    assert "POL-EVIDENCE-001" in reason_ids(
        evaluation
    )


def test_abstention_is_denied() -> None:
    _, _, synthesis, context = build_policy_inputs()

    abstained = replace(
        synthesis,
        disposition=SynthesisDisposition.ABSTAIN,
        tool_recommendation=None,
    )

    evaluation = evaluate_tool_recommendation(
        abstained,
        context,
    )

    assert evaluation.decision is PolicyDecision.DENY
    assert "POL-SYNTHESIS-001" in reason_ids(
        evaluation
    )
    assert "POL-TOOL-001" in reason_ids(
        evaluation
    )


def test_mutating_tool_without_approval_escalates() -> None:
    _, _, synthesis, context = build_policy_inputs()

    mutating = replace(
        synthesis,
        ignored_untrusted_instructions=(),
        tool_recommendation=ToolRecommendation(
            tool_name="restart_service",
            arguments={
                "service": "identity-api",
                "environment": "production",
            },
            rationale=(
                "Restart proposed for deterministic "
                "policy review."
            ),
            risk=ToolRisk.MUTATING,
        ),
    )

    operator_context = replace(
        context,
        identity=replace(
            context.identity,
            roles=("production_operator",),
        ),
        classifiers_agree=True,
        ml_probability_margin=0.50,
    )

    evaluation = evaluate_tool_recommendation(
        mutating,
        operator_context,
    )

    assert (
        evaluation.decision
        is PolicyDecision.ESCALATE
    )
    assert "POL-APPROVAL-001" in reason_ids(
        evaluation
    )


def test_matching_approval_can_allow_mutating_tool() -> None:
    _, _, synthesis, context = build_policy_inputs()

    mutating = replace(
        synthesis,
        ignored_untrusted_instructions=(),
        requires_human_review=False,
        tool_recommendation=ToolRecommendation(
            tool_name="restart_service",
            arguments={
                "service": "identity-api",
                "environment": "production",
            },
            rationale=(
                "Restart proposed for deterministic "
                "policy review."
            ),
            risk=ToolRisk.MUTATING,
        ),
    )

    approval = HumanApproval(
        approval_id="approval-123",
        approver_id="commander-9",
        approver_role="incident_commander",
        tenant_id="tenant-alpha",
        service="identity-api",
        environment="production",
        tool_name="restart_service",
    )

    operator_context = replace(
        context,
        identity=replace(
            context.identity,
            roles=("production_operator",),
        ),
        classifiers_agree=True,
        ml_probability_margin=0.50,
        approvals=(approval,),
    )

    evaluation = evaluate_tool_recommendation(
        mutating,
        operator_context,
    )

    assert evaluation.decision is PolicyDecision.ALLOW


def test_wrong_scope_approval_does_not_satisfy_policy() -> None:
    _, _, synthesis, context = build_policy_inputs()

    mutating = replace(
        synthesis,
        ignored_untrusted_instructions=(),
        requires_human_review=False,
        tool_recommendation=ToolRecommendation(
            tool_name="restart_service",
            arguments={
                "service": "identity-api",
                "environment": "production",
            },
            rationale="Controlled restart proposal.",
            risk=ToolRisk.MUTATING,
        ),
    )

    wrong_approval = HumanApproval(
        approval_id="approval-wrong",
        approver_id="commander-9",
        approver_role="incident_commander",
        tenant_id="tenant-beta",
        service="identity-api",
        environment="production",
        tool_name="restart_service",
    )

    operator_context = replace(
        context,
        identity=replace(
            context.identity,
            roles=("production_operator",),
        ),
        classifiers_agree=True,
        ml_probability_margin=0.50,
        approvals=(wrong_approval,),
    )

    evaluation = evaluate_tool_recommendation(
        mutating,
        operator_context,
    )

    assert (
        evaluation.decision
        is PolicyDecision.ESCALATE
    )
    assert "POL-APPROVAL-001" in reason_ids(
        evaluation
    )


def test_high_impact_production_action_escalates() -> None:
    _, _, synthesis, context = build_policy_inputs()

    high_impact = replace(
        synthesis,
        ignored_untrusted_instructions=(),
        requires_human_review=False,
        tool_recommendation=ToolRecommendation(
            tool_name="rollback_deployment",
            arguments={
                "service": "identity-api",
                "environment": "production",
                "target_version": "4.3.1",
            },
            rationale="Rollback proposed for policy review.",
            risk=ToolRisk.HIGH_IMPACT,
        ),
    )

    approvals = (
        HumanApproval(
            approval_id="approval-commander",
            approver_id="commander-9",
            approver_role="incident_commander",
            tenant_id="tenant-alpha",
            service="identity-api",
            environment="production",
            tool_name="rollback_deployment",
        ),
        HumanApproval(
            approval_id="approval-operator",
            approver_id="operator-8",
            approver_role="production_operator",
            tenant_id="tenant-alpha",
            service="identity-api",
            environment="production",
            tool_name="rollback_deployment",
        ),
    )

    privileged_context = replace(
        context,
        identity=replace(
            context.identity,
            roles=(
                "production_operator",
                "incident_commander",
            ),
        ),
        classifiers_agree=True,
        ml_probability_margin=0.50,
        approvals=approvals,
    )

    evaluation = evaluate_tool_recommendation(
        high_impact,
        privileged_context,
    )

    assert (
        evaluation.decision
        is PolicyDecision.ESCALATE
    )
    assert "POL-PROD-001" in reason_ids(
        evaluation
    )


def test_deny_takes_precedence_over_escalate() -> None:
    _, _, synthesis, context = build_policy_inputs()

    assert synthesis.tool_recommendation is not None

    invalid_synthesis = replace(
        synthesis,
        ignored_untrusted_instructions=(
            "untrusted-injected-operational-note",
        ),
        tool_recommendation=replace(
            synthesis.tool_recommendation,
            tool_name="unknown_tool",
        ),
    )

    evaluation = evaluate_tool_recommendation(
        invalid_synthesis,
        context,
    )

    assert evaluation.decision is PolicyDecision.DENY
    assert "POL-TOOL-002" in reason_ids(
        evaluation
    )


def test_fingerprint_is_reproducible() -> None:
    _, _, synthesis, context = build_policy_inputs()

    first = evaluate_tool_recommendation(
        synthesis,
        context,
    )
    second = evaluate_tool_recommendation(
        synthesis,
        context,
    )

    assert (
        first.request_fingerprint
        == second.request_fingerprint
    )
    assert len(first.request_fingerprint) == 64


def test_policy_version_is_recorded() -> None:
    _, _, synthesis, context = build_policy_inputs()

    evaluation = evaluate_tool_recommendation(
        synthesis,
        context,
    )

    assert evaluation.policy_version == POLICY_VERSION
