# Phase 9 — Evaluation, Observability, and Evidence

## Purpose

The first eight phases created a governed agentic workflow.

Phase 9 answers a different question:

> How do we prove that the workflow is useful, reliable, secure, traceable, and
> economically operable?

This phase measures the workflow. It does not add execution capability.

## Core Principle

> A production AI workflow is not complete when it runs. It is complete when
> its quality, security, reliability, cost, and authority boundaries can be
> measured and proven.

## Evaluation Dimensions

Phase 9 measures:

- Workflow outcomes
- Expected negative outcomes
- Trace completeness
- Checkpoint integrity
- Policy sequencing
- Runtime authorization
- Citation integrity
- Cross-tenant denial
- Prompt-injection handling
- Runtime success
- Workflow latency
- Token usage
- Estimated model cost
- Production side effects
- Release-gate status

## Normal Cases and Negative Controls

A security test that is expected to be denied is not an operational failure.

Phase 9 separates:

```text
NORMAL_SUCCESS
EXPECTED_DENIAL
EXPECTED_ESCALATION
EXPECTED_FAILURE

Examples:

A normal diagnostic workflow should complete.
A cross-tenant request should be denied.
A prompt-injection finding should escalate.
An expired runtime request should fail safely.

This separation prevents misleading success-rate calculations.

Quality Metrics
Normal Workflow Success Rate

Measures whether ordinary, authorized workflows complete successfully.

Expected Negative Outcome Rate

Measures whether deliberate security and failure tests produce their expected
safe results.

Citation Manifest Integrity

Checks that synthesis citations originate from evidence returned by
permission-aware retrieval.

This proves citation provenance. It does not prove that every diagnosis is
correct.

Security Metrics
Runtime After ALLOW Rate

Every runtime event must be associated with:

policy_decision = ALLOW

Target:

100%
Unauthorized Runtime Attempt Rate

Measures runtime activity where policy was not ALLOW.

Target:

0%
Cross-Tenant Denial Rate

Measures whether cross-tenant attempts are denied before runtime.

Target:

100%
Prompt-Injection Runtime Rate

Measures whether workflows containing prompt-injection findings reached the
runtime.

Target:

0%
Reliability Metrics
Trace Completeness

Every event and checkpoint must retain:

Workflow ID
Trace ID
Sequence
Evidence references
Checkpoint Integrity

Checks:

Ordered event sequence
Unique event sequence
Ordered checkpoint sequence
Unique checkpoint sequence
Trace binding
Workflow binding
Successful Step Completeness

A completed workflow must include:

Request received
Ambiguity evaluated
Retrieval completed
Synthesis completed
Policy evaluated
Runtime completed
Workflow completed
Latency Metrics

Phase 9 records:

Total workflow latency
Per-step latency
p95 workflow latency

The tutorial SLO is:

workflow p95 <= 5000 ms

Production thresholds would be based on user experience, operational urgency,
provider latency, and cost.

Token and Cost Metrics

Each observation records:

Input tokens
Output tokens
Estimated model cost
Retrieval-query count
Tool-execution attempts

The tutorial budgets are:

average input tokens <= 4000
average output tokens <= 1500
average model cost <= $0.05 per normal workflow

The Phase 5 deterministic tutorial provider does not call a live model.
The usage values are explicit evaluation observations used to demonstrate the
accounting model.

They are not claimed to be live provider billing records.

Distributions

The scorecard records distributions for:

Workflow status
Policy decision
Runtime status

These reveal changes such as:

Increased abstention
Increased policy denial
Increased escalation
Runtime timeout growth
Unexpected replay rates
Release Gate

Each applicable metric returns:

PASS
FAIL
NOT_APPLICABLE

The release gate passes only when all applicable metrics pass.

Evaluation cannot waive a failed control.

Tamper-Evident Evidence Bundle

The release evidence bundle includes:

Evaluation summary
Workflow outcomes
Evaluation report
SHA-256 digest for every artifact
Aggregate bundle digest
Release-gate result
Failed metric names
Evaluation and bundle versions

The bundle supports:

Audit review
Release review
Security review
Regression comparison
Evidence retention
Incident reconstruction
Evidence Limitations

A SHA-256 digest proves that an artifact changed after the digest was produced.

It does not independently prove:

Who created the artifact
Whether the source data was truthful
Whether the release was approved
Whether the deployment occurred
Whether the model diagnosis was correct

Production evidence would additionally use:

Signed attestations
Immutable object storage
CI identity
Build provenance
Deployment records
Retention controls
Authority Boundary

The evaluation layer may:

Measure workflow outcomes
Aggregate metrics
Evaluate SLOs
Generate scorecards
Generate evidence manifests
Block a release gate
Report failed controls

It may not:

Change a policy decision
Execute a tool
Create an approval
Grant a role
Rewrite a workflow result
Hide a failed metric
Convert a failed release gate into a pass
End-to-End Architecture
Incident request
      |
      v
Deterministic classifier + ML
      |
      v
Permission-aware retrieval
      |
      v
GenAI evidence synthesis
      |
      v
Deterministic policy
      |
      v
Isolated runtime
      |
      v
Orchestrator outcome
      |
      v
Evaluation and observability
      |
      v
Release evidence bundle
Run the Demonstration
PYTHONPATH=src python scripts/run_workflow_evaluation.py
Run Phase 9 Tests
PYTHONPATH=src python -m pytest tests/unit/observability -v
Completion Criteria

Phase 9 is complete when:

Normal and negative cases are separated.
Normal workflow success is measured.
Expected denials are measured as successful controls.
Expected failures are measured as successful controls.
Workflow status distribution is recorded.
Policy decision distribution is recorded.
Runtime status distribution is recorded.
Trace completeness is measured.
Checkpoint integrity is measured.
Policy-before-runtime sequencing is measured.
Runtime-after-ALLOW is measured.
Unauthorized runtime attempts are measured.
Cross-tenant denial is measured.
Prompt-injection runtime access is measurable.
Citation-manifest integrity is measured.
Workflow p95 latency is evaluated.
Token usage is recorded.
Estimated model cost is recorded.
Production-side-effect rate is evaluated.
Failed metrics block the release gate.
Evidence artifacts have SHA-256 digests.
The aggregate bundle digest is reproducible.
Evaluation versions are recorded.
Evaluation cannot expand authority.
All Phase 9 and regression tests pass.
