"""Deterministic document-access evaluation."""

from __future__ import annotations

from incident_agent.retrieval.contracts import (
    AccessDecision,
    AccessEvaluation,
    KnowledgeDocument,
    RetrievalIdentity,
    RetrievalScope,
)


def evaluate_document_access(
    document: KnowledgeDocument,
    identity: RetrievalIdentity,
    scope: RetrievalScope,
) -> AccessEvaluation:
    """Evaluate access before relevance scoring."""

    reasons: list[str] = []

    if document.tenant_id != identity.tenant_id:
        reasons.append("tenant_mismatch")

    if document.service != scope.service:
        reasons.append("service_scope_mismatch")

    if scope.environment not in document.environment_scope:
        reasons.append("environment_scope_mismatch")

    if not set(identity.roles).intersection(
        document.allowed_roles
    ):
        reasons.append("role_not_allowed")

    if (
        scope.document_types
        and document.document_type
        not in scope.document_types
    ):
        reasons.append("document_type_not_requested")

    return AccessEvaluation(
        document_id=document.document_id,
        decision=(
            AccessDecision.DENY
            if reasons
            else AccessDecision.ALLOW
        ),
        reason_codes=tuple(reasons),
    )
