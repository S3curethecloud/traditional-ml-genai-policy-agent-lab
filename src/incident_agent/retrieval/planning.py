"""Targeted retrieval-query planning from classifier evidence."""

from __future__ import annotations

from incident_agent.evaluation.ambiguity import (
    AmbiguityResult,
)


CATEGORY_QUERY_TERMS = {
    "authentication_failure": (
        "login failures token validation signing key "
        "issuer audience authentication configuration"
    ),
    "deployment_regression": (
        "recent deployment version configuration change "
        "regression rollback verification"
    ),
    "infrastructure_saturation": (
        "cpu memory saturation latency queue workload"
    ),
    "network_degradation": (
        "packet loss latency retransmission regional network"
    ),
    "dependency_failure": (
        "dependency errors timeout retry downstream failure"
    ),
    "unknown": (
        "incident diagnosis missing evidence prior incident "
        "service ownership escalation"
    ),
}


def build_retrieval_query_text(
    result: AmbiguityResult,
) -> str:
    """Build a transparent evidence query from ambiguity results."""

    categories: list[str] = [
        result.deterministic_category,
        result.ml_category,
        result.ml_second_category,
        *result.competing_signals,
    ]

    unique_categories = tuple(
        dict.fromkeys(categories)
    )

    category_terms = " ".join(
        CATEGORY_QUERY_TERMS.get(
            category,
            category.replace("_", " "),
        )
        for category in unique_categories
    )

    contradiction_terms = " ".join(
        result.contradictions
    )

    trigger_terms = " ".join(
        trigger.replace("_", " ")
        for trigger in result.review_triggers
    )

    return " ".join(
        part
        for part in (
            category_terms,
            contradiction_terms,
            trigger_terms,
        )
        if part
    )
