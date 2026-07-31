"""Permission-aware hybrid retrieval engine."""

from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import (
    TfidfVectorizer,
)

from incident_agent.retrieval.access import (
    evaluate_document_access,
)
from incident_agent.retrieval.contracts import (
    AccessDecision,
    DeniedDocumentEvidence,
    KnowledgeDocument,
    RetrievalQuery,
    RetrievalResponse,
    RetrievalResult,
)
from incident_agent.retrieval.injection import (
    detect_prompt_injection,
)


RETRIEVAL_VERSION = "permission-aware-retrieval-v1"

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_-]+")


def retrieve_documents(
    documents: list[KnowledgeDocument],
    query: RetrievalQuery,
) -> RetrievalResponse:
    """Filter by permission, then rank only authorized documents."""

    if query.maximum_results < 1:
        raise ValueError(
            "maximum_results must be at least 1"
        )

    authorized: list[KnowledgeDocument] = []
    denied: list[DeniedDocumentEvidence] = []

    for document in documents:
        access = evaluate_document_access(
            document=document,
            identity=query.identity,
            scope=query.scope,
        )

        if access.decision is AccessDecision.ALLOW:
            authorized.append(document)
        else:
            denied.append(
                DeniedDocumentEvidence(
                    document_id=document.document_id,
                    document_type=document.document_type,
                    reason_codes=access.reason_codes,
                )
            )

    if not authorized:
        return RetrievalResponse(
            query_text=query.query_text,
            results=(),
            denied_documents=tuple(denied),
            corpus_documents_considered=len(documents),
            authorized_documents_ranked=0,
            retrieval_version=RETRIEVAL_VERSION,
        )

    lexical_scores = _lexical_scores(
        query.query_text,
        authorized,
    )
    semantic_scores = _semantic_scores(
        query.query_text,
        authorized,
    )

    ranked: list[RetrievalResult] = []

    for index, document in enumerate(authorized):
        lexical_score = lexical_scores[index]
        semantic_score = semantic_scores[index]

        hybrid_score = (
            0.40 * lexical_score
            + 0.60 * semantic_score
        )

        injection_markers = detect_prompt_injection(
            document.content
        )

        ranked.append(
            RetrievalResult(
                document_id=document.document_id,
                title=document.title,
                document_type=document.document_type,
                sensitivity=document.sensitivity.value,
                lexical_score=round(
                    lexical_score,
                    8,
                ),
                semantic_score=round(
                    semantic_score,
                    8,
                ),
                hybrid_score=round(
                    hybrid_score,
                    8,
                ),
                citation=(
                    f"[{document.document_id}]"
                ),
                content=document.content,
                trusted_instruction_source=(
                    document.trusted_instruction_source
                ),
                prompt_injection_detected=bool(
                    injection_markers
                ),
                prompt_injection_markers=(
                    injection_markers
                ),
            )
        )

    ranked.sort(
        key=lambda result: (
            -result.hybrid_score,
            result.document_id,
        )
    )

    return RetrievalResponse(
        query_text=query.query_text,
        results=tuple(
            ranked[:query.maximum_results]
        ),
        denied_documents=tuple(
            sorted(
                denied,
                key=lambda item: item.document_id,
            )
        ),
        corpus_documents_considered=len(documents),
        authorized_documents_ranked=len(authorized),
        retrieval_version=RETRIEVAL_VERSION,
    )


def _lexical_scores(
    query_text: str,
    documents: list[KnowledgeDocument],
) -> list[float]:
    query_tokens = _tokenize(query_text)

    if not query_tokens:
        return [0.0 for _ in documents]

    query_counts = Counter(query_tokens)
    scores: list[float] = []

    for document in documents:
        document_tokens = _tokenize(
            _document_search_text(document)
        )
        document_counts = Counter(document_tokens)

        overlap = sum(
            min(
                query_counts[token],
                document_counts[token],
            )
            for token in query_counts
        )

        denominator = math.sqrt(
            sum(query_counts.values())
            * max(1, sum(document_counts.values()))
        )

        scores.append(
            overlap / denominator
        )

    return scores


def _semantic_scores(
    query_text: str,
    documents: list[KnowledgeDocument],
) -> list[float]:
    corpus = [
        _document_search_text(document)
        for document in documents
    ]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        stop_words="english",
        sublinear_tf=True,
    )

    matrix = vectorizer.fit_transform(
        [query_text, *corpus]
    )

    query_vector = matrix[0]
    document_vectors = matrix[1:]

    scores = document_vectors @ query_vector.T

    return [
        float(value)
        for value in np.asarray(
            scores.toarray()
        ).reshape(-1)
    ]


def _document_search_text(
    document: KnowledgeDocument,
) -> str:
    return " ".join(
        (
            document.title,
            document.document_type,
            document.service,
            document.content,
        )
    )


def _tokenize(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_PATTERN.findall(text)
    ]
