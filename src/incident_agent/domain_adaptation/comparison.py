"""Compare domain packs and determine adaptation readiness."""

from __future__ import annotations

from incident_agent.domain_adaptation.contracts import (
    AdaptationDecision,
    DomainComparison,
    DomainPack,
    PackValidationResult,
    PackValidationStatus,
)


def compare_domain_packs(
    reference: DomainPack,
    candidate: DomainPack,
) -> DomainComparison:
    reference_capabilities = set(
        reference.supported_capabilities
    )
    candidate_capabilities = set(
        candidate.supported_capabilities
    )

    reference_tools = {
        tool.tool_name
        for tool in reference.tools
    }
    candidate_tools = {
        tool.tool_name
        for tool in candidate.tools
    }

    reference_categories = {
        item.category_id
        for item in reference.incident_categories
    }
    candidate_categories = {
        item.category_id
        for item in candidate.incident_categories
    }

    reference_sources = {
        item.source_id
        for item in reference.evidence_sources
    }
    candidate_sources = {
        item.source_id
        for item in candidate.evidence_sources
    }

    return DomainComparison(
        reference_pack_id=reference.pack_id,
        candidate_pack_id=candidate.pack_id,
        shared_capabilities=tuple(
            sorted(
                reference_capabilities
                & candidate_capabilities
            )
        ),
        reference_only_capabilities=tuple(
            sorted(
                reference_capabilities
                - candidate_capabilities
            )
        ),
        candidate_only_capabilities=tuple(
            sorted(
                candidate_capabilities
                - reference_capabilities
            )
        ),
        shared_tool_names=tuple(
            sorted(reference_tools & candidate_tools)
        ),
        isolated_taxonomies=not bool(
            reference_categories & candidate_categories
        ),
        isolated_evidence_sources=not bool(
            reference_sources & candidate_sources
        ),
    )


def determine_adaptation_decision(
    results: tuple[PackValidationResult, ...],
    comparison: DomainComparison,
) -> tuple[AdaptationDecision, tuple[str, ...]]:
    reasons: list[str] = []

    invalid = tuple(
        result.pack_id
        for result in results
        if result.status is PackValidationStatus.INVALID
    )

    if invalid:
        reasons.append(
            "Invalid domain packs: " + ", ".join(invalid)
        )

    if comparison.candidate_only_capabilities:
        reasons.append(
            "Candidate requests capabilities not present "
            "in the reference pack."
        )

    if not comparison.isolated_taxonomies:
        reasons.append(
            "Domain taxonomies are not isolated."
        )

    if not comparison.isolated_evidence_sources:
        reasons.append(
            "Domain evidence sources are not isolated."
        )

    decision = (
        AdaptationDecision.READY_FOR_INTEGRATION
        if not reasons
        else AdaptationDecision.BLOCKED
    )

    return decision, tuple(reasons)
