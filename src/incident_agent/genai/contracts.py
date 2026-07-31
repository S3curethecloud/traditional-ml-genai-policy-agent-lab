"""Typed contracts for GenAI evidence synthesis."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class SynthesisDisposition(StrEnum):
    """Final evidence-synthesis disposition."""

    RECOMMEND = "RECOMMEND"
    ABSTAIN = "ABSTAIN"
    REQUEST_MORE_EVIDENCE = "REQUEST_MORE_EVIDENCE"


class ToolRisk(StrEnum):
    """Risk level attached to a proposed tool request."""

    READ_ONLY = "read_only"
    MUTATING = "mutating"
    HIGH_IMPACT = "high_impact"


@dataclass(frozen=True)
class EvidenceItem:
    """Authorized evidence available to the GenAI provider."""

    document_id: str
    citation: str
    title: str
    document_type: str
    content: str
    trusted_instruction_source: bool
    prompt_injection_detected: bool
    prompt_injection_markers: tuple[str, ...]


@dataclass(frozen=True)
class ClassifierEvidence:
    """Combined deterministic and ML classifier evidence."""

    deterministic_category: str
    deterministic_confidence: float
    deterministic_matched_rules: tuple[str, ...]
    ml_category: str
    ml_confidence: float
    ml_second_category: str
    ml_second_probability: float
    ml_probability_margin: float
    classifiers_agree: bool
    competing_signals: tuple[str, ...]
    contradictions: tuple[str, ...]
    review_triggers: tuple[str, ...]


@dataclass(frozen=True)
class SynthesisRequest:
    """Complete input to a GenAI evidence-synthesis provider."""

    case_id: str
    incident_summary: str
    classifier_evidence: ClassifierEvidence
    authorized_evidence: tuple[EvidenceItem, ...]
    denied_document_ids: tuple[str, ...]
    permitted_tool_names: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceReference:
    """One evidence claim tied to a retrieved citation."""

    claim: str
    citation: str


@dataclass(frozen=True)
class Hypothesis:
    """One ranked incident hypothesis."""

    name: str
    confidence: float
    supporting_evidence: tuple[EvidenceReference, ...]
    contradicting_evidence: tuple[EvidenceReference, ...]
    missing_evidence: tuple[str, ...]


@dataclass(frozen=True)
class ToolRecommendation:
    """Structured request for a later policy-controlled tool evaluation."""

    tool_name: str
    arguments: dict[str, str]
    rationale: str
    risk: ToolRisk


@dataclass(frozen=True)
class SynthesisResponse:
    """Validated GenAI evidence-synthesis output."""

    case_id: str
    summary: str
    hypotheses: tuple[Hypothesis, ...]
    recommended_next_step: str
    tool_recommendation: ToolRecommendation | None
    disposition: SynthesisDisposition
    requires_human_review: bool
    citations: tuple[str, ...]
    ignored_untrusted_instructions: tuple[str, ...]
    provider_name: str
    prompt_version: str
    authority_boundary: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)
