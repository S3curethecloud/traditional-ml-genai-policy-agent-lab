# Phase 8 — Agent Orchestrator and End-to-End Workflow

## Purpose

The previous phases created isolated components:

1. Deterministic classification
2. Traditional ML
3. Ambiguity evaluation
4. Permission-aware retrieval
5. GenAI evidence synthesis
6. Deterministic policy
7. Isolated tool runtime

Phase 8 connects them through a governed workflow.

## Core Principle

> The orchestrator sequences work. It does not classify, retrieve, reason,
> authorize, or execute on its own.

## Why an Orchestrator Is Required

An enterprise agent workflow needs more than function calls.

It needs:

- Ordered state transitions
- Correlation IDs
- Trace IDs
- Checkpoints
- Stop conditions
- Failure isolation
- Replay verification
- Human escalation
- Audit timelines
- Evidence references
- Retry ownership

Without an orchestrator, components can be called in the wrong order or bypassed.

## Workflow State Machine

```text
RECEIVED
   |
   v
AMBIGUITY_EVALUATED
   |
   v
RETRIEVAL_COMPLETED
   |
   v
SYNTHESIS_COMPLETED
   |
   v
POLICY_EVALUATED
   |
   +-------------------+-------------------+
   |                   |                   |
 DENY               ESCALATE             ALLOW
   |                   |                   |
   v                   v                   v
DENIED       HUMAN_ESCALATION_REQUIRED  RUNTIME_COMPLETED
                                               |
                                               v
                                           COMPLETED
Typed Workflow Request

The request contains:

Workflow ID
Trace ID
Case ID
Identity
Request tenant
Service
Environment
Retrieval-result limit
Runtime idempotency key
Dry-run flag
Creation timestamp

These values are propagated through the governed components.

Component Authority Boundaries
Ambiguity Evaluation

Produces classifier comparison evidence.

It cannot retrieve documents or execute tools.

Permission-Aware Retrieval

Filters evidence before relevance ranking.

It cannot authorize a tool.

GenAI Synthesis

Produces hypotheses and a typed recommendation.

It cannot grant permission.

Deterministic Policy

Returns ALLOW, DENY, or ESCALATE.

It cannot execute the tool.

Isolated Runtime

Executes only a policy-bound ALLOW.

It cannot create authority.

Orchestrator

Sequences all steps and records state.

It cannot bypass any component.

Checkpoints

The orchestrator records a checkpoint after every completed step.

Each checkpoint includes:

Workflow ID
Trace ID
Step
Sequence
State digest
Evidence references

The digest creates a stable record of the state observed at that boundary.

Evidence References

Each event and checkpoint records relevant evidence:

Classifier categories
Case ID
Retrieval citations
GenAI citations
Policy reason IDs
Policy fingerprint
Runtime audit event types

This creates an explainable path from incident evidence to execution outcome.

Stop Conditions
Policy DENY

The workflow stops immediately.

The runtime is not called.

Policy ESCALATE

The workflow enters:

HUMAN_ESCALATION_REQUIRED

The runtime is not called.

GenAI ABSTAIN

The workflow stops without tool execution.

Runtime REJECTED

The workflow fails safely.

Runtime FAILED or TIMED_OUT

The workflow records a controlled failure.

Step Exception

The orchestrator sanitizes the failure and enters FAILED.

Retry Ownership

Retries belong to the component that owns the failure mode.

Examples:

Retrieval retry belongs to retrieval infrastructure.
Model retry belongs to the provider adapter.
Runtime retry belongs to the runtime tool definition.
Workflow restart belongs to the orchestrator.

The orchestrator must not blindly retry every step.

Replay

Phase 8 replay verifies:

Event ordering
Checkpoint ordering
Trace binding
Workflow binding
Runtime occurred only after ALLOW

Replay verification does not re-execute the tool.

Tool replay protection remains the responsibility of the runtime idempotency key.

Human Escalation

ESCALATE is a terminal outcome for the automated workflow.

A future human-approval phase may produce a new governed request.

The orchestrator must not silently convert escalation into approval.

Failure Isolation

Each component exposes structured outputs.

The orchestrator records:

Last completed step
Stop reason
Policy decision
Runtime status
Checkpoints
Events

A failure in one component does not erase evidence from earlier completed steps.

Audit Timeline

The final outcome includes an ordered event timeline.

Example:

1 workflow_received
2 ambiguity_evaluated
3 retrieval_completed
4 synthesis_completed
5 policy_evaluated
6 runtime_completed
7 workflow_completed
No Direct GenAI-to-Tool Path

The orchestrator enforces:

SYNTHESIS_COMPLETED
        |
        v
POLICY_EVALUATED
        |
        v
RUNTIME_COMPLETED

There is no supported transition from synthesis directly to runtime.

Run the Demonstration
PYTHONPATH=src python scripts/run_agent_orchestrator.py
Run Phase 8 Tests
PYTHONPATH=src python -m pytest tests/unit/orchestrator -v
Completion Criteria

Phase 8 is complete when:

Workflow inputs are typed.
State transitions are ordered.
Every major step creates an event.
Every completed step creates a checkpoint.
Checkpoint digests are stable.
Trace IDs propagate across the workflow.
Workflow IDs propagate across the workflow.
Retrieval occurs before synthesis.
Synthesis occurs before policy.
Policy occurs before runtime.
No direct GenAI-to-runtime path exists.
DENY prevents runtime execution.
ESCALATE prevents runtime execution.
ALLOW is required for runtime.
Runtime rejection fails safely.
Runtime timeout fails safely.
Unknown cases fail safely.
Evidence references are retained.
Policy fingerprints are retained.
Runtime replay does not execute twice.
Workflow replay validates ordering.
Failure states retain prior checkpoints.
The orchestrator cannot expand authority.
All Phase 8 and regression tests pass.
