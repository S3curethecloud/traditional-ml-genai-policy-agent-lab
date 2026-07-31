"""GenAI evidence-synthesis service boundary."""

from __future__ import annotations

from incident_agent.genai.contracts import (
    ClassifierEvidence,
    EvidenceItem,
    SynthesisRequest,
    SynthesisResponse,
)
from incident_agent.genai.prompts import (
    build_synthesis_prompt,
)
from incident_agent.genai.provider import (
    SynthesisProvider,
)
from incident_agent.genai.validation import (
    validate_synthesis_response,
)
from incident_agent.retrieval.contracts import (
    RetrievalResponse,
)
from incident_agent.evaluation.ambiguity import (
    AmbiguityResult,
)


DEFAULT_PERMITTED_TOOLS = (
    "inspect_incident_telemetry",
    "inspect_service_health",
    "inspect_deployment_history",
    "inspect_identity_configuration",
)


def build_synthesis_request(
    ambiguity_result: AmbiguityResult,
    retrieval_response: RetrievalResponse,
) -> SynthesisRequest:
    """Build the provider request from governed upstream evidence."""

    return SynthesisRequest(
        case_id=ambiguity_result.case_id,
        incident_summary=ambiguity_result.title,
        classifier_evidence=ClassifierEvidence(
            deterministic_category=(
                ambiguity_result
                .deterministic_category
            ),
            deterministic_confidence=(
                ambiguity_result
                .deterministic_confidence
            ),
            deterministic_matched_rules=(
                ambiguity_result
                .deterministic_matched_rules
            ),
            ml_category=ambiguity_result.ml_category,
            ml_confidence=(
                ambiguity_result.ml_confidence
            ),
            ml_second_category=(
                ambiguity_result.ml_second_category
            ),
            ml_second_probability=(
                ambiguity_result
                .ml_second_probability
            ),
            ml_probability_margin=(
                ambiguity_result
                .ml_probability_margin
            ),
            classifiers_agree=(
                ambiguity_result.classifiers_agree
            ),
            competing_signals=(
                ambiguity_result.competing_signals
            ),
            contradictions=(
                ambiguity_result.contradictions
            ),
            review_triggers=(
                ambiguity_result.review_triggers
            ),
        ),
        authorized_evidence=tuple(
            EvidenceItem(
                document_id=result.document_id,
                citation=result.citation,
                title=result.title,
                document_type=result.document_type,
                content=result.content,
                trusted_instruction_source=(
                    result.trusted_instruction_source
                ),
                prompt_injection_detected=(
                    result.prompt_injection_detected
                ),
                prompt_injection_markers=(
                    result.prompt_injection_markers
                ),
            )
            for result in retrieval_response.results
        ),
        denied_document_ids=tuple(
            denied.document_id
            for denied
            in retrieval_response.denied_documents
        ),
        permitted_tool_names=DEFAULT_PERMITTED_TOOLS,
    )


def synthesize_evidence(
    request: SynthesisRequest,
    provider: SynthesisProvider,
) -> SynthesisResponse:
    """Build prompt, invoke provider, and validate output."""

    prompt = build_synthesis_prompt(request)

    response = provider.synthesize(
        request=request,
        prompt=prompt,
    )

    validate_synthesis_response(
        request=request,
        response=response,
    )

    return response
