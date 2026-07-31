"""Tests for permission-aware hybrid retrieval."""

from __future__ import annotations

from pathlib import Path

from incident_agent.evaluation.ambiguity import (
    evaluate_ambiguity_pack,
    load_ambiguity_pack,
)
from incident_agent.ml.inference import (
    IncidentClassifier,
)
from incident_agent.retrieval.access import (
    evaluate_document_access,
)
from incident_agent.retrieval.contracts import (
    AccessDecision,
    RetrievalIdentity,
    RetrievalQuery,
    RetrievalScope,
)
from incident_agent.retrieval.engine import (
    RETRIEVAL_VERSION,
    retrieve_documents,
)
from incident_agent.retrieval.injection import (
    detect_prompt_injection,
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


def incident_responder_identity() -> RetrievalIdentity:
    return RetrievalIdentity(
        user_id="engineer-42",
        tenant_id="tenant-alpha",
        roles=("incident_responder",),
    )


def production_identity_scope() -> RetrievalScope:
    return RetrievalScope(
        service="identity-api",
        environment="production",
    )


def test_corpus_loads_unique_documents() -> None:
    documents = load_knowledge_corpus(
        KNOWLEDGE_DIRECTORY
    )

    identifiers = [
        document.document_id
        for document in documents
    ]

    assert len(documents) == 12
    assert len(identifiers) == len(
        set(identifiers)
    )


def test_same_tenant_authorized_runbook_is_allowed() -> None:
    documents = load_knowledge_corpus(
        KNOWLEDGE_DIRECTORY
    )

    document = next(
        document
        for document in documents
        if document.document_id
        == "runbook-deployment-regression"
    )

    result = evaluate_document_access(
        document=document,
        identity=incident_responder_identity(),
        scope=production_identity_scope(),
    )

    assert result.decision is AccessDecision.ALLOW
    assert result.reason_codes == ()


def test_other_tenant_document_is_denied() -> None:
    documents = load_knowledge_corpus(
        KNOWLEDGE_DIRECTORY
    )

    document = next(
        document
        for document in documents
        if document.document_id
        == "service-payments-api-other-tenant"
    )

    result = evaluate_document_access(
        document=document,
        identity=incident_responder_identity(),
        scope=production_identity_scope(),
    )

    assert result.decision is AccessDecision.DENY
    assert "tenant_mismatch" in result.reason_codes
    assert (
        "service_scope_mismatch"
        in result.reason_codes
    )


def test_role_restricted_document_is_denied() -> None:
    documents = load_knowledge_corpus(
        KNOWLEDGE_DIRECTORY
    )

    document = next(
        document
        for document in documents
        if document.document_id
        == "service-identity-api-security-restricted"
    )

    result = evaluate_document_access(
        document=document,
        identity=incident_responder_identity(),
        scope=production_identity_scope(),
    )

    assert result.decision is AccessDecision.DENY
    assert "role_not_allowed" in result.reason_codes


def test_security_reviewer_can_access_restricted_document() -> None:
    documents = load_knowledge_corpus(
        KNOWLEDGE_DIRECTORY
    )

    document = next(
        document
        for document in documents
        if document.document_id
        == "service-identity-api-security-restricted"
    )

    result = evaluate_document_access(
        document=document,
        identity=RetrievalIdentity(
            user_id="reviewer-7",
            tenant_id="tenant-alpha",
            roles=("security_reviewer",),
        ),
        scope=production_identity_scope(),
    )

    assert result.decision is AccessDecision.ALLOW


def test_permission_filtering_prevents_denied_content_return() -> None:
    documents = load_knowledge_corpus(
        KNOWLEDGE_DIRECTORY
    )

    response = retrieve_documents(
        documents=documents,
        query=RetrievalQuery(
            query_text=(
                "restricted signing key architecture "
                "payments production procedures"
            ),
            identity=incident_responder_identity(),
            scope=production_identity_scope(),
            maximum_results=10,
        ),
    )

    result_ids = {
        result.document_id
        for result in response.results
    }

    denied_ids = {
        denied.document_id
        for denied in response.denied_documents
    }

    assert (
        "service-identity-api-security-restricted"
        not in result_ids
    )
    assert (
        "service-payments-api-other-tenant"
        not in result_ids
    )
    assert (
        "service-identity-api-security-restricted"
        in denied_ids
    )
    assert (
        "service-payments-api-other-tenant"
        in denied_ids
    )

    returned_content = " ".join(
        result.content
        for result in response.results
    )

    assert (
        "key-custody implementation details"
        not in returned_content
    )
    assert (
        "Payments API operational procedures"
        not in returned_content
    )


def test_denied_evidence_contains_no_content_field() -> None:
    documents = load_knowledge_corpus(
        KNOWLEDGE_DIRECTORY
    )

    response = retrieve_documents(
        documents=documents,
        query=RetrievalQuery(
            query_text="restricted security architecture",
            identity=incident_responder_identity(),
            scope=production_identity_scope(),
            maximum_results=5,
        ),
    )

    denied = next(
        item
        for item in response.denied_documents
        if item.document_id
        == "service-identity-api-security-restricted"
    )

    assert not hasattr(denied, "content")
    assert denied.reason_codes == (
        "role_not_allowed",
    )


def test_hybrid_retrieval_returns_relevant_auth_documents() -> None:
    documents = load_knowledge_corpus(
        KNOWLEDGE_DIRECTORY
    )

    response = retrieve_documents(
        documents=documents,
        query=RetrievalQuery(
            query_text=(
                "login failures token validation "
                "signing key mismatch after deployment"
            ),
            identity=incident_responder_identity(),
            scope=production_identity_scope(),
            maximum_results=5,
        ),
    )

    result_ids = [
        result.document_id
        for result in response.results
    ]

    assert (
        "runbook-identity-token-validation"
        in result_ids
    )
    assert (
        "incident-auth-key-mismatch-2026-06"
        in result_ids
    )

    assert all(
        response.results[index].hybrid_score
        >= response.results[index + 1].hybrid_score
        for index in range(
            len(response.results) - 1
        )
    )


def test_each_result_has_citation() -> None:
    documents = load_knowledge_corpus(
        KNOWLEDGE_DIRECTORY
    )

    response = retrieve_documents(
        documents=documents,
        query=RetrievalQuery(
            query_text="deployment regression identity api",
            identity=incident_responder_identity(),
            scope=production_identity_scope(),
        ),
    )

    assert response.results

    for result in response.results:
        assert result.citation == (
            f"[{result.document_id}]"
        )


def test_prompt_injection_is_detected_and_not_trusted() -> None:
    documents = load_knowledge_corpus(
        KNOWLEDGE_DIRECTORY
    )

    injected = next(
        document
        for document in documents
        if document.document_id
        == "untrusted-injected-operational-note"
    )

    markers = detect_prompt_injection(
        injected.content
    )

    assert markers
    assert (
        "ignore_previous_instructions"
        in markers
    )
    assert injected.trusted_instruction_source is False


def test_injected_document_is_flagged_in_results() -> None:
    documents = load_knowledge_corpus(
        KNOWLEDGE_DIRECTORY
    )

    response = retrieve_documents(
        documents=documents,
        query=RetrievalQuery(
            query_text=(
                "restart production login failures "
                "authorized instructions"
            ),
            identity=incident_responder_identity(),
            scope=production_identity_scope(),
            maximum_results=10,
        ),
    )

    result = next(
        result
        for result in response.results
        if result.document_id
        == "untrusted-injected-operational-note"
    )

    assert result.prompt_injection_detected
    assert not result.trusted_instruction_source
    assert result.prompt_injection_markers


def test_phase_3b_evidence_builds_targeted_query() -> None:
    classifier = IncidentClassifier.load(
        MODEL_DIRECTORY
    )
    cases = load_ambiguity_pack(
        AMBIGUITY_PACK
    )
    results = evaluate_ambiguity_pack(
        cases,
        classifier,
    )

    authentication_case = next(
        result
        for result in results
        if result.case_id
        == "recent-deployment-with-authentication-signals"
    )

    query_text = build_retrieval_query_text(
        authentication_case
    )

    assert "token validation" in query_text
    assert "deployment" in query_text
    assert "contradictory evidence present" in query_text


def test_retrieval_version_and_counts_are_recorded() -> None:
    documents = load_knowledge_corpus(
        KNOWLEDGE_DIRECTORY
    )

    response = retrieve_documents(
        documents=documents,
        query=RetrievalQuery(
            query_text="identity api incident evidence",
            identity=incident_responder_identity(),
            scope=production_identity_scope(),
        ),
    )

    assert (
        response.retrieval_version
        == RETRIEVAL_VERSION
    )
    assert (
        response.corpus_documents_considered
        == len(documents)
    )
    assert response.authorized_documents_ranked > 0
    assert response.denied_documents


def test_document_type_scope_is_enforced() -> None:
    documents = load_knowledge_corpus(
        KNOWLEDGE_DIRECTORY
    )

    response = retrieve_documents(
        documents=documents,
        query=RetrievalQuery(
            query_text="deployment regression evidence",
            identity=incident_responder_identity(),
            scope=RetrievalScope(
                service="identity-api",
                environment="production",
                document_types=("runbook",),
            ),
            maximum_results=10,
        ),
    )

    assert response.results
    assert all(
        result.document_type == "runbook"
        for result in response.results
    )

    denied_reason_sets = [
        denied.reason_codes
        for denied in response.denied_documents
    ]

    assert any(
        "document_type_not_requested"
        in reasons
        for reasons in denied_reason_sets
    )
