"""Strict knowledge-document loading and schema validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from incident_agent.retrieval.contracts import (
    KnowledgeDocument,
    Sensitivity,
)


REQUIRED_DOCUMENT_FIELDS = frozenset(
    {
        "document_id",
        "title",
        "document_type",
        "tenant_id",
        "service",
        "environment_scope",
        "allowed_roles",
        "sensitivity",
        "created_at",
        "updated_at",
        "trusted_instruction_source",
        "content",
    }
)


class KnowledgeDocumentError(ValueError):
    """Raised when a knowledge document is invalid."""


def load_knowledge_corpus(
    root_directory: Path,
) -> list[KnowledgeDocument]:
    """Load all YAML knowledge documents recursively."""

    paths = sorted(root_directory.rglob("*.yaml"))

    if not paths:
        raise KnowledgeDocumentError(
            f"No knowledge documents found in {root_directory}"
        )

    documents = [
        load_knowledge_document(path)
        for path in paths
    ]

    identifiers = [
        document.document_id
        for document in documents
    ]

    if len(identifiers) != len(set(identifiers)):
        raise KnowledgeDocumentError(
            "Knowledge document IDs must be unique"
        )

    return documents


def load_knowledge_document(
    path: Path,
) -> KnowledgeDocument:
    """Load one strict YAML knowledge document."""

    with path.open("r", encoding="utf-8") as handle:
        parsed = yaml.safe_load(handle)

    if not isinstance(parsed, dict):
        raise KnowledgeDocumentError(
            f"{path}: root must be a mapping"
        )

    document = parsed.get("document")

    if not isinstance(document, dict):
        raise KnowledgeDocumentError(
            f"{path}: document must be a mapping"
        )

    observed_fields = set(document)
    missing = REQUIRED_DOCUMENT_FIELDS - observed_fields
    unexpected = observed_fields - REQUIRED_DOCUMENT_FIELDS

    if missing or unexpected:
        raise KnowledgeDocumentError(
            f"{path}: schema mismatch; "
            f"missing={sorted(missing)}, "
            f"unexpected={sorted(unexpected)}"
        )

    environment_scope = _string_tuple(
        document["environment_scope"],
        path,
        "environment_scope",
    )
    allowed_roles = _string_tuple(
        document["allowed_roles"],
        path,
        "allowed_roles",
    )

    content = str(document["content"]).strip()

    if not content:
        raise KnowledgeDocumentError(
            f"{path}: content must not be empty"
        )

    return KnowledgeDocument(
        document_id=_required_string(
            document["document_id"],
            path,
            "document_id",
        ),
        title=_required_string(
            document["title"],
            path,
            "title",
        ),
        document_type=_required_string(
            document["document_type"],
            path,
            "document_type",
        ),
        tenant_id=_required_string(
            document["tenant_id"],
            path,
            "tenant_id",
        ),
        service=_required_string(
            document["service"],
            path,
            "service",
        ),
        environment_scope=environment_scope,
        allowed_roles=allowed_roles,
        sensitivity=Sensitivity(
            str(document["sensitivity"])
        ),
        created_at=_required_string(
            document["created_at"],
            path,
            "created_at",
        ),
        updated_at=_required_string(
            document["updated_at"],
            path,
            "updated_at",
        ),
        trusted_instruction_source=bool(
            document["trusted_instruction_source"]
        ),
        content=content,
        source_path=str(path),
    )


def _required_string(
    value: Any,
    path: Path,
    field_name: str,
) -> str:
    text = str(value).strip()

    if not text:
        raise KnowledgeDocumentError(
            f"{path}: {field_name} must not be empty"
        )

    return text


def _string_tuple(
    value: Any,
    path: Path,
    field_name: str,
) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise KnowledgeDocumentError(
            f"{path}: {field_name} must be a non-empty list"
        )

    values = tuple(
        str(item).strip()
        for item in value
    )

    if any(not item for item in values):
        raise KnowledgeDocumentError(
            f"{path}: {field_name} contains an empty value"
        )

    return values
