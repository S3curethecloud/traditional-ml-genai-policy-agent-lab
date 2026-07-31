"""Deterministic policy evaluation for GenAI tool proposals."""

from __future__ import annotations

from incident_agent.genai.contracts import (
    SynthesisDisposition,
    SynthesisResponse,
    ToolRisk,
)
from incident_agent.policy.contracts import (
    HumanApproval,
    PolicyContext,
    PolicyDecision,
    PolicyEvaluation,
    PolicyReason,
    ToolPolicy,
)
from incident_agent.policy.fingerprint import (
    build_request_fingerprint,
)
from incident_agent.policy.registry import (
    POLICY_VERSION,
    TOOL_POLICIES,
)


LOW_ML_MARGIN_THRESHOLD = 0.20


def evaluate_tool_recommendation(
    synthesis: SynthesisResponse,
    context: PolicyContext,
) -> PolicyEvaluation:
    """Evaluate a GenAI tool proposal without executing it."""

    deny_reasons: list[PolicyReason] = []
    escalate_reasons: list[PolicyReason] = []

    recommendation = synthesis.tool_recommendation
    tool_name = (
        recommendation.tool_name
        if recommendation is not None
        else None
    )

    fingerprint = build_request_fingerprint(
        synthesis=synthesis,
        context=context,
    )

    if context.identity.tenant_id != context.request_tenant_id:
        deny_reasons.append(
            PolicyReason(
                rule_id="POL-TENANT-001",
                message=(
                    "Authenticated identity tenant does not "
                    "match the request tenant."
                ),
            )
        )

    if not context.identity.roles:
        deny_reasons.append(
            PolicyReason(
                rule_id="POL-IDENTITY-001",
                message=(
                    "Authenticated identity has no assigned roles."
                ),
            )
        )

    if synthesis.disposition is SynthesisDisposition.ABSTAIN:
        deny_reasons.append(
            PolicyReason(
                rule_id="POL-SYNTHESIS-001",
                message=(
                    "GenAI abstained and therefore supplied no "
                    "actionable recommendation."
                ),
            )
        )

    if recommendation is None:
        deny_reasons.append(
            PolicyReason(
                rule_id="POL-TOOL-001",
                message="No tool recommendation was provided.",
            )
        )

        return _finalize(
            tool_name=None,
            deny_reasons=deny_reasons,
            escalate_reasons=escalate_reasons,
            fingerprint=fingerprint,
        )

    tool_policy = TOOL_POLICIES.get(
        recommendation.tool_name
    )

    if tool_policy is None:
        deny_reasons.append(
            PolicyReason(
                rule_id="POL-TOOL-002",
                message=(
                    "Recommended tool is not registered in "
                    "the deterministic policy registry."
                ),
            )
        )

        return _finalize(
            tool_name=recommendation.tool_name,
            deny_reasons=deny_reasons,
            escalate_reasons=escalate_reasons,
            fingerprint=fingerprint,
        )

    _evaluate_tool_contract(
        recommendation_risk=recommendation.risk,
        recommendation_arguments=recommendation.arguments,
        policy=tool_policy,
        context=context,
        deny_reasons=deny_reasons,
    )

    _evaluate_evidence(
        synthesis=synthesis,
        context=context,
        policy=tool_policy,
        deny_reasons=deny_reasons,
        escalate_reasons=escalate_reasons,
    )

    _evaluate_risk_and_ambiguity(
        synthesis=synthesis,
        context=context,
        policy=tool_policy,
        escalate_reasons=escalate_reasons,
    )

    _evaluate_approvals(
        context=context,
        policy=tool_policy,
        escalate_reasons=escalate_reasons,
    )

    return _finalize(
        tool_name=recommendation.tool_name,
        deny_reasons=deny_reasons,
        escalate_reasons=escalate_reasons,
        fingerprint=fingerprint,
    )


def _evaluate_tool_contract(
    recommendation_risk: ToolRisk,
    recommendation_arguments: dict[str, str],
    policy: ToolPolicy,
    context: PolicyContext,
    deny_reasons: list[PolicyReason],
) -> None:
    if recommendation_risk is not policy.risk:
        deny_reasons.append(
            PolicyReason(
                rule_id="POL-TOOL-003",
                message=(
                    "Recommended risk does not match the "
                    "registered tool risk."
                ),
            )
        )

    supplied_arguments = set(
        recommendation_arguments
    )
    required_arguments = set(
        policy.required_arguments
    )

    missing_arguments = (
        required_arguments - supplied_arguments
    )
    unexpected_arguments = (
        supplied_arguments - required_arguments
    )

    if missing_arguments:
        deny_reasons.append(
            PolicyReason(
                rule_id="POL-ARG-001",
                message=(
                    "Required tool arguments are missing: "
                    f"{sorted(missing_arguments)}."
                ),
            )
        )

    if unexpected_arguments:
        deny_reasons.append(
            PolicyReason(
                rule_id="POL-ARG-002",
                message=(
                    "Unexpected tool arguments were supplied: "
                    f"{sorted(unexpected_arguments)}."
                ),
            )
        )

    if (
        "service" in recommendation_arguments
        and recommendation_arguments["service"]
        != context.service
    ):
        deny_reasons.append(
            PolicyReason(
                rule_id="POL-SCOPE-001",
                message=(
                    "Recommended service does not match the "
                    "authorized service scope."
                ),
            )
        )

    if (
        "environment" in recommendation_arguments
        and recommendation_arguments["environment"]
        != context.environment
    ):
        deny_reasons.append(
            PolicyReason(
                rule_id="POL-SCOPE-002",
                message=(
                    "Recommended environment does not match "
                    "the authorized environment scope."
                ),
            )
        )

    if context.environment not in policy.allowed_environments:
        deny_reasons.append(
            PolicyReason(
                rule_id="POL-ENV-001",
                message=(
                    "Tool is not allowed in the requested "
                    "environment."
                ),
            )
        )

    if not set(context.identity.roles).intersection(
        policy.allowed_roles
    ):
        deny_reasons.append(
            PolicyReason(
                rule_id="POL-ROLE-001",
                message=(
                    "Authenticated identity has no role "
                    "authorized for the recommended tool."
                ),
            )
        )


def _evaluate_evidence(
    synthesis: SynthesisResponse,
    context: PolicyContext,
    policy: ToolPolicy,
    deny_reasons: list[PolicyReason],
    escalate_reasons: list[PolicyReason],
) -> None:
    authorized_citations = set(
        context.authorized_citations
    )
    response_citations = set(
        synthesis.citations
    )

    denied_citations = {
        f"[{document_id}]"
        for document_id
        in context.denied_document_ids
    }

    unauthorized_citations = (
        response_citations - authorized_citations
    )

    if unauthorized_citations:
        deny_reasons.append(
            PolicyReason(
                rule_id="POL-EVIDENCE-001",
                message=(
                    "Synthesis contains citations outside "
                    "the authorized evidence set."
                ),
            )
        )

    if response_citations.intersection(
        denied_citations
    ):
        deny_reasons.append(
            PolicyReason(
                rule_id="POL-EVIDENCE-002",
                message=(
                    "Synthesis references denied-document "
                    "citations."
                ),
            )
        )

    if len(response_citations) < policy.minimum_citations:
        escalate_reasons.append(
            PolicyReason(
                rule_id="POL-EVIDENCE-003",
                message=(
                    "The recommendation does not meet the "
                    "minimum citation threshold for this tool."
                ),
            )
        )

    hypothesis_citations = {
        reference.citation
        for hypothesis in synthesis.hypotheses
        for reference in (
            *hypothesis.supporting_evidence,
            *hypothesis.contradicting_evidence,
        )
    }

    citations_missing_from_summary = (
        hypothesis_citations - response_citations
    )

    if citations_missing_from_summary:
        deny_reasons.append(
            PolicyReason(
                rule_id="POL-EVIDENCE-004",
                message=(
                    "Hypothesis evidence citations are missing "
                    "from the synthesis citation manifest."
                ),
            )
        )

    if not synthesis.hypotheses:
        escalate_reasons.append(
            PolicyReason(
                rule_id="POL-EVIDENCE-005",
                message=(
                    "No diagnostic hypotheses were provided."
                ),
            )
        )


def _evaluate_risk_and_ambiguity(
    synthesis: SynthesisResponse,
    context: PolicyContext,
    policy: ToolPolicy,
    escalate_reasons: list[PolicyReason],
) -> None:
    if synthesis.ignored_untrusted_instructions:
        escalate_reasons.append(
            PolicyReason(
                rule_id="POL-INJECTION-001",
                message=(
                    "Retrieved evidence contained prompt-"
                    "injection indicators and requires review."
                ),
            )
        )

    if (
        not context.classifiers_agree
        and policy.risk is not ToolRisk.READ_ONLY
    ):
        escalate_reasons.append(
            PolicyReason(
                rule_id="POL-AMBIGUITY-001",
                message=(
                    "Classifier disagreement blocks automatic "
                    "approval of a mutating or high-impact tool."
                ),
            )
        )

    if (
        context.ml_probability_margin
        < LOW_ML_MARGIN_THRESHOLD
        and policy.risk is not ToolRisk.READ_ONLY
    ):
        escalate_reasons.append(
            PolicyReason(
                rule_id="POL-AMBIGUITY-002",
                message=(
                    "Low ML probability margin blocks automatic "
                    "approval of a mutating or high-impact tool."
                ),
            )
        )

    if (
        synthesis.requires_human_review
        and policy.risk is not ToolRisk.READ_ONLY
    ):
        escalate_reasons.append(
            PolicyReason(
                rule_id="POL-HUMAN-001",
                message=(
                    "The synthesis explicitly requires human "
                    "review before a mutating action."
                ),
            )
        )

    if (
        context.environment == "production"
        and policy.risk is ToolRisk.HIGH_IMPACT
    ):
        escalate_reasons.append(
            PolicyReason(
                rule_id="POL-PROD-001",
                message=(
                    "High-impact production actions always "
                    "require explicit escalation."
                ),
            )
        )


def _evaluate_approvals(
    context: PolicyContext,
    policy: ToolPolicy,
    escalate_reasons: list[PolicyReason],
) -> None:
    if not policy.requires_human_approval:
        return

    valid_approval_roles = {
        approval.approver_role
        for approval in context.approvals
        if _approval_matches_context(
            approval=approval,
            context=context,
            tool_name=policy.tool_name,
        )
    }

    missing_roles = (
        set(policy.required_approval_roles)
        - valid_approval_roles
    )

    if missing_roles:
        escalate_reasons.append(
            PolicyReason(
                rule_id="POL-APPROVAL-001",
                message=(
                    "Required human approvals are missing for "
                    f"roles: {sorted(missing_roles)}."
                ),
            )
        )


def _approval_matches_context(
    approval: HumanApproval,
    context: PolicyContext,
    tool_name: str,
) -> bool:
    return (
        approval.tenant_id
        == context.request_tenant_id
        and approval.service == context.service
        and approval.environment
        == context.environment
        and approval.tool_name == tool_name
    )


def _finalize(
    tool_name: str | None,
    deny_reasons: list[PolicyReason],
    escalate_reasons: list[PolicyReason],
    fingerprint: str,
) -> PolicyEvaluation:
    if deny_reasons:
        decision = PolicyDecision.DENY
        reasons = tuple(deny_reasons)
    elif escalate_reasons:
        decision = PolicyDecision.ESCALATE
        reasons = tuple(escalate_reasons)
    else:
        decision = PolicyDecision.ALLOW
        reasons = (
            PolicyReason(
                rule_id="POL-ALLOW-001",
                message=(
                    "All deterministic policy checks passed."
                ),
            ),
        )

    return PolicyEvaluation(
        decision=decision,
        tool_name=tool_name,
        reasons=reasons,
        policy_version=POLICY_VERSION,
        request_fingerprint=fingerprint,
        execution_performed=False,
        authority_boundary=(
            "Policy evaluation authorizes or rejects a typed "
            "request. It does not execute the tool."
        ),
    )
