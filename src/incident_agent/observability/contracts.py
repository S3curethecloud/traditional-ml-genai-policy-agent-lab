"""Typed contracts for evaluation, observability, and evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from incident_agent.orchestrator.contracts import (
    WorkflowOutcome,
)


class ExpectedOutcome(StrEnum):
    """Expected result category for an evaluation case."""

    NORMAL_SUCCESS = "NORMAL_SUCCESS"
    EXPECTED_DENIAL = "EXPECTED_DENIAL"
    EXPECTED_ESCALATION = "EXPECTED_ESCALATION"
    EXPECTED_FAILURE = "EXPECTED_FAILURE"


class MetricStatus(StrEnum):
    """Evaluation status for a metric or SLO."""

    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class StepLatency:
    """Observed latency for one workflow step."""

    step_name: str
    latency_ms: float


@dataclass(frozen=True)
class UsageObservation:
    """Model and infrastructure usage associated with a workflow."""

    input_tokens: int
    output_tokens: int
    estimated_model_cost_usd: float
    retrieval_queries: int
    tool_execution_attempts: int


@dataclass(frozen=True)
class WorkflowObservation:
    """One evaluated workflow with operational metadata."""

    evaluation_case_id: str
    expected_outcome: ExpectedOutcome
    outcome: WorkflowOutcome
    total_latency_ms: float
    step_latencies: tuple[StepLatency, ...]
    usage: UsageObservation
    prompt_injection_detected: bool
    cross_tenant_attempt: bool
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class MetricResult:
    """One named metric with a threshold evaluation."""

    metric_name: str
    value: float
    unit: str
    target: str
    status: MetricStatus
    explanation: str


@dataclass(frozen=True)
class DistributionEntry:
    """Count and ratio for one categorical value."""

    name: str
    count: int
    ratio: float


@dataclass(frozen=True)
class EvaluationSummary:
    """Aggregated workflow evaluation results."""

    evaluation_version: str
    workflow_count: int
    normal_workflow_count: int
    negative_test_count: int
    workflow_status_distribution: tuple[
        DistributionEntry,
        ...,
    ]
    policy_decision_distribution: tuple[
        DistributionEntry,
        ...,
    ]
    runtime_status_distribution: tuple[
        DistributionEntry,
        ...,
    ]
    metrics: tuple[MetricResult, ...]
    authority_boundary: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)


@dataclass(frozen=True)
class EvidenceArtifact:
    """One artifact included in a release evidence bundle."""

    artifact_name: str
    artifact_type: str
    sha256: str
    description: str


@dataclass(frozen=True)
class ReleaseEvidenceBundle:
    """Tamper-evident release evidence manifest."""

    bundle_version: str
    release_id: str
    evaluation_version: str
    artifact_count: int
    artifacts: tuple[EvidenceArtifact, ...]
    aggregate_sha256: str
    release_gate_passed: bool
    failed_metric_names: tuple[str, ...]
    authority_boundary: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)
