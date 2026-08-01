"""SLI, SLO, and error-budget evaluation."""

from __future__ import annotations

from incident_agent.operations.contracts import (
    ComparisonOperator,
    ErrorBudgetStatus,
    MetricSample,
    SLODefinition,
    SLOResult,
)


def sample_is_compliant(
    definition: SLODefinition,
    sample: MetricSample,
) -> bool:
    """Evaluate one metric sample against an SLO."""

    if sample.metric_name != definition.metric_name:
        raise ValueError(
            "Metric sample does not match SLO definition"
        )

    if definition.comparison is ComparisonOperator.GTE:
        return sample.value >= definition.threshold

    if definition.comparison is ComparisonOperator.LTE:
        return sample.value <= definition.threshold

    if definition.comparison is ComparisonOperator.EQ:
        return sample.value == definition.threshold

    raise ValueError(
        f"Unsupported comparison: {definition.comparison}"
    )


def evaluate_slo(
    definition: SLODefinition,
    samples: tuple[MetricSample, ...],
    minimum_samples: int,
    warning_threshold: float,
    exhausted_threshold: float,
) -> SLOResult:
    """Evaluate one SLO and calculate error-budget use."""

    matching = tuple(
        sample
        for sample in samples
        if sample.metric_name == definition.metric_name
    )

    if len(matching) < minimum_samples:
        raise ValueError(
            f"Insufficient samples for {definition.slo_id}"
        )

    compliant = sum(
        sample_is_compliant(definition, sample)
        for sample in matching
    )

    compliance = (
        compliant / len(matching)
    ) * 100.0

    allowed_failure_ratio = (
        100.0 - definition.target_percentage
    ) / 100.0

    observed_failure_ratio = (
        len(matching) - compliant
    ) / len(matching)

    if allowed_failure_ratio == 0.0:
        budget_consumed = (
            0.0
            if observed_failure_ratio == 0.0
            else 1.0
        )
    else:
        budget_consumed = (
            observed_failure_ratio
            / allowed_failure_ratio
        )

    budget_remaining = max(
        0.0,
        1.0 - budget_consumed,
    )

    if budget_consumed >= exhausted_threshold:
        budget_status = ErrorBudgetStatus.EXHAUSTED
    elif budget_consumed >= warning_threshold:
        budget_status = ErrorBudgetStatus.WARNING
    else:
        budget_status = ErrorBudgetStatus.HEALTHY

    return SLOResult(
        slo_id=definition.slo_id,
        metric_name=definition.metric_name,
        sample_count=len(matching),
        compliant_samples=compliant,
        compliance_percentage=round(
            compliance,
            4,
        ),
        target_percentage=(
            definition.target_percentage
        ),
        passed=(
            compliance
            >= definition.target_percentage
        ),
        error_budget_consumed=round(
            budget_consumed,
            4,
        ),
        error_budget_remaining=round(
            budget_remaining,
            4,
        ),
        error_budget_status=budget_status,
    )


def evaluate_all_slos(
    definitions: tuple[SLODefinition, ...],
    samples: tuple[MetricSample, ...],
    minimum_samples: int,
    warning_threshold: float,
    exhausted_threshold: float,
) -> tuple[SLOResult, ...]:
    """Evaluate all configured service objectives."""

    return tuple(
        evaluate_slo(
            definition=definition,
            samples=samples,
            minimum_samples=minimum_samples,
            warning_threshold=warning_threshold,
            exhausted_threshold=exhausted_threshold,
        )
        for definition in definitions
    )
