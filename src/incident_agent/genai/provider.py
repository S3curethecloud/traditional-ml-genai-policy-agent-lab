"""Provider abstraction for GenAI evidence synthesis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from incident_agent.genai.contracts import (
    EvidenceReference,
    Hypothesis,
    SynthesisDisposition,
    SynthesisRequest,
    SynthesisResponse,
    ToolRecommendation,
    ToolRisk,
)
from incident_agent.genai.prompts import PROMPT_VERSION


class SynthesisProvider(Protocol):
    """Interface implemented by GenAI provider adapters."""

    @property
    def provider_name(self) -> str:
        """Return the provider identifier."""

    def synthesize(
        self,
        request: SynthesisRequest,
        prompt: str,
    ) -> SynthesisResponse:
        """Produce structured evidence synthesis."""


@dataclass(frozen=True)
class DeterministicTutorialProvider:
    """Repeatable provider used for tests and local tutorial execution."""

    provider_name: str = "deterministic-tutorial-provider-v1"

    def synthesize(
        self,
        request: SynthesisRequest,
        prompt: str,
    ) -> SynthesisResponse:
        del prompt

        usable_evidence = tuple(
            item
            for item in request.authorized_evidence
            if not item.prompt_injection_detected
        )

        ignored = tuple(
            item.document_id
            for item in request.authorized_evidence
            if item.prompt_injection_detected
        )

        hypotheses = _build_hypotheses(
            request,
            usable_evidence,
        )

        has_evidence = bool(usable_evidence)
        has_contradiction = bool(
            request.classifier_evidence.contradictions
        )
        low_margin = (
            request.classifier_evidence
            .ml_probability_margin
            < 0.20
        )
        classifier_disagreement = not (
            request.classifier_evidence
            .classifiers_agree
        )

        if not has_evidence:
            disposition = SynthesisDisposition.ABSTAIN
            next_step = (
                "Escalate because no authorized evidence "
                "is available."
            )
            tool_recommendation = None
        elif (
            classifier_disagreement
            or low_margin
            or has_contradiction
        ):
            disposition = (
                SynthesisDisposition
                .REQUEST_MORE_EVIDENCE
            )
            next_step = (
                "Collect additional read-only diagnostic "
                "evidence before selecting a root cause."
            )
            tool_recommendation = ToolRecommendation(
                tool_name="inspect_incident_telemetry",
                arguments={
                    "service": "identity-api",
                    "environment": "production",
                },
                rationale=(
                    "Classifier disagreement or contradictory "
                    "evidence requires additional telemetry."
                ),
                risk=ToolRisk.READ_ONLY,
            )
        else:
            disposition = SynthesisDisposition.RECOMMEND
            next_step = (
                "Validate the highest-ranked hypothesis "
                "using the cited runbook."
            )
            tool_recommendation = ToolRecommendation(
                tool_name="inspect_service_health",
                arguments={
                    "service": "identity-api",
                    "environment": "production",
                },
                rationale=(
                    "Authorized evidence supports a focused "
                    "read-only health inspection."
                ),
                risk=ToolRisk.READ_ONLY,
            )

        citations = tuple(
            dict.fromkeys(
                reference.citation
                for hypothesis in hypotheses
                for reference in (
                    *hypothesis.supporting_evidence,
                    *hypothesis.contradicting_evidence,
                )
            )
        )

        return SynthesisResponse(
            case_id=request.case_id,
            summary=(
                "Classifier evidence and authorized operational "
                "documents indicate multiple plausible causes. "
                "The result remains diagnostic evidence."
            ),
            hypotheses=hypotheses,
            recommended_next_step=next_step,
            tool_recommendation=tool_recommendation,
            disposition=disposition,
            requires_human_review=(
                classifier_disagreement
                or has_contradiction
                or disposition
                is SynthesisDisposition.ABSTAIN
            ),
            citations=citations,
            ignored_untrusted_instructions=ignored,
            provider_name=self.provider_name,
            prompt_version=PROMPT_VERSION,
            authority_boundary=(
                "GenAI output is evidence and recommendation "
                "only. Deterministic policy must independently "
                "authorize any tool execution."
            ),
        )


def _build_hypotheses(
    request: SynthesisRequest,
    usable_evidence: tuple,
) -> tuple[Hypothesis, ...]:
    categories = tuple(
        dict.fromkeys(
            (
                request.classifier_evidence.ml_category,
                request.classifier_evidence
                .deterministic_category,
                request.classifier_evidence
                .ml_second_category,
                *request.classifier_evidence
                .competing_signals,
            )
        )
    )

    selected_categories = categories[:3]
    hypotheses: list[Hypothesis] = []

    for index, category in enumerate(
        selected_categories
    ):
        matching_evidence = tuple(
            item
            for item in usable_evidence
            if _document_matches_category(
                item.title,
                item.content,
                category,
            )
        )

        if not matching_evidence:
            matching_evidence = usable_evidence[:1]

        supporting = tuple(
            EvidenceReference(
                claim=(
                    f"Authorized evidence is relevant to "
                    f"{category.replace('_', ' ')}."
                ),
                citation=item.citation,
            )
            for item in matching_evidence[:2]
        )

        contradicting = tuple(
            EvidenceReference(
                claim=contradiction,
                citation=usable_evidence[0].citation,
            )
            for contradiction
            in request.classifier_evidence
            .contradictions[:1]
            if usable_evidence
        )

        confidence = max(
            0.10,
            min(
                0.90,
                request.classifier_evidence.ml_confidence
                - index * 0.15,
            ),
        )

        hypotheses.append(
            Hypothesis(
                name=category,
                confidence=round(confidence, 6),
                supporting_evidence=supporting,
                contradicting_evidence=contradicting,
                missing_evidence=(
                    "Current telemetry time series",
                    "Independent confirmation of causal order",
                ),
            )
        )

    return tuple(hypotheses)


def _document_matches_category(
    title: str,
    content: str,
    category: str,
) -> bool:
    haystack = f"{title} {content}".lower()

    category_terms = {
        "authentication_failure": (
            "authentication",
            "token",
            "signing-key",
            "login",
        ),
        "deployment_regression": (
            "deployment",
            "version",
            "regression",
            "rollback",
        ),
        "infrastructure_saturation": (
            "cpu",
            "memory",
            "saturation",
            "queue",
        ),
        "network_degradation": (
            "network",
            "packet loss",
            "latency",
            "retransmission",
        ),
        "dependency_failure": (
            "dependency",
            "downstream",
            "timeout",
            "retry",
        ),
        "unknown": (
            "ownership",
            "escalation",
            "missing evidence",
        ),
    }

    return any(
        term in haystack
        for term in category_terms.get(
            category,
            (category.replace("_", " "),),
        )
    )
