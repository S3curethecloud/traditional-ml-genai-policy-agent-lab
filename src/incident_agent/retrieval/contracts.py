"""Typed contracts for permission-aware retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Sensitivity(StrEnum):
    """Supported document-sensitivity levels."""

    INTERNAL = "internal"
    RESTRICTED = "restricted"
    HIGHLY_RESTRICTED = "highly_restricted"


class AccessDecision(StrEnum):
    """Document-access outcomes."""

    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass(frozen=True)
class RetrievalIdentity:
    """Caller identity and authorization context."""

    user_id: str
    tenant_id: str
    roles: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalScope:
    """Requested operational evidence scope."""

    service: str
    environment: str
    document_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class KnowledgeDocument:
    """Normalized knowledge-base document."""

    document_id: str
    title: str
    document_type: str
    tenant_id: str
    service: str
    environment_scope: tuple[str, ...]
    allowed_roles: tuple[str, ...]
    sensitivity: Sensitivity
    created_at: str
    updated_at: str
    trusted_instruction_source: bool
    content: str
    source_path: str


@dataclass(frozen=True)
class AccessEvaluation:
    """Permission evaluation for one document."""

    document_id: str
    decision: AccessDecision
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalQuery:
    """One retrieval request."""

    query_text: str
    identity: RetrievalIdentity
    scope: RetrievalScope
    maximum_results: int = 5


@dataclass(frozen=True)
class RetrievalResult:
    """One authorized ranked document result."""

    document_id: str
    title: str
    document_type: str
    sensitivity: str
    lexical_score: float
    semantic_score: float
    hybrid_score: float
    citation: str
    content: str
    trusted_instruction_source: bool
    prompt_injection_detected: bool
    prompt_injection_markers: tuple[str, ...]


@dataclass(frozen=True)
class DeniedDocumentEvidence:
    """Non-content evidence for a denied document."""

    document_id: str
    document_type: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalResponse:
    """Complete permission-aware retrieval response."""

    query_text: str
    results: tuple[RetrievalResult, ...]
    denied_documents: tuple[DeniedDocumentEvidence, ...]
    corpus_documents_considered: int
    authorized_documents_ranked: int
    retrieval_version: str
