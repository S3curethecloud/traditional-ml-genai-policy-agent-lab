"""Validation for structured GenAI evidence-synthesis output."""

from __future__ import annotations

from incident_agent.genai.contracts import (
    SynthesisDisposition,
    SynthesisRequest,
    SynthesisResponse,
)


class SynthesisValidationError(ValueError):
    """Raised when GenAI output violates the evidence contract."""


def validate_synthesis_response(
    request: SynthesisRequest,
    response: SynthesisResponse,
) -> None:
    """Validate citations, tools, confidence, and authority boundaries."""

    errors: list[str] = []

    authorized_citations = {
        item.citation
        for item in request.authorized_evidence
    }

    denied_citations = {
        f"[{document_id}]"
        for document_id in request.denied_document_ids
    }

    used_citations = set(response.citations)

    for hypothesis in response.hypotheses:
        if not 0.0 <= hypothesis.confidence <= 1.0:
            errors.append(
                f"invalid confidence for {hypothesis.name}"
            )

        for reference in (
            *hypothesis.supporting_evidence,
            *hypothesis.contradicting_evidence,
        ):
            used_citations.add(reference.citation)

    fabricated = used_citations - authorized_citations

    if fabricated:
        errors.append(
            f"unauthorized or fabricated citations: "
            f"{sorted(fabricated)}"
        )

    denied_used = used_citations & denied_citations

    if denied_used:
        errors.append(
            f"denied document citations used: "
            f"{sorted(denied_used)}"
        )

    if (
        response.tool_recommendation is not None
        and response.tool_recommendation.tool_name
        not in request.permitted_tool_names
    ):
        errors.append(
            "tool recommendation is not in the permitted "
            "tool-name contract"
        )

    injection_document_ids = {
        item.document_id
        for item in request.authorized_evidence
        if item.prompt_injection_detected
    }

    ignored_ids = set(
        response.ignored_untrusted_instructions
    )

    missing_ignored = (
        injection_document_ids - ignored_ids
    )

    if missing_ignored:
        errors.append(
            "prompt-injection documents were not explicitly "
            f"ignored: {sorted(missing_ignored)}"
        )

    if (
        not request.authorized_evidence
        and response.disposition
        is not SynthesisDisposition.ABSTAIN
    ):
        errors.append(
            "response must abstain when no authorized "
            "evidence is available"
        )

    if not response.authority_boundary:
        errors.append(
            "authority boundary is missing"
        )

    if errors:
        raise SynthesisValidationError(
            "; ".join(errors)
        )
