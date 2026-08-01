# Phase 7 — Isolated Tool Runtime

## Purpose

Phase 6 returned a deterministic policy decision:

```text
ALLOW
DENY
ESCALATE

Phase 7 introduces the first execution boundary.

The runtime executes a tool only when the request is cryptographically bound to
the exact synthesis and policy context that produced an ALLOW decision.

Core Principle

No GenAI-to-tool path exists. The tool runtime executes only a request bound
to a valid deterministic ALLOW decision.

Runtime Inputs

The runtime receives:

Typed runtime request
Structured GenAI synthesis
Deterministic policy evaluation
Policy context
Policy fingerprint
Identity context
Tool name
Exact arguments
Declared risk
Service and environment
Idempotency key
Request creation and expiration times
Dry-run flag
Required ALLOW Decision

The runtime rejects both:

DENY
ESCALATE

A valid-looking tool request cannot bypass the policy result.

Fingerprint Binding

The runtime checks three conditions:

The request fingerprint equals the policy decision fingerprint.
The policy fingerprint is recomputed from the supplied synthesis and policy
context.
The recomputed fingerprint equals the stored policy decision fingerprint.

This detects changes made after policy evaluation, including:

Tool replacement
Argument changes
Citation changes
Identity changes
Tenant changes
Environment changes
Approval changes
Classifier evidence changes
Synthesis changes
Tool Registry

Only registered runtime tools can execute.

Each runtime definition includes:

Tool name
Risk
Required arguments
Timeout
Maximum attempts
Dry-run requirement
Handler

The runtime registry is separate from the GenAI tool-name list.

Argument Revalidation

The runtime revalidates the arguments even though policy already validated them.

This is intentional defense in depth.

The runtime requires:

Exact argument names
Exact agreement with the synthesis recommendation
Service agreement
Environment agreement

Argument drift is rejected before handler execution.

Risk Revalidation

The runtime compares:

GenAI recommendation risk
Runtime request risk
Registered runtime risk

All three must match.

A mutating tool cannot be relabeled as read-only.

Idempotency

Every request includes an idempotency key.

Once the runtime records a result for that key, another request using the same
key does not execute the handler again.

The replay result is:

REPLAYED

This prevents accidental duplicate operations caused by:

Network retries
Client retries
Orchestrator retries
Duplicate messages
Replayed requests

The tutorial uses an in-memory store. A production runtime would use a durable,
transactional store.

Expiration

Each request has:

Creation time
Expiration time

Expired requests are rejected.

This prevents a previously authorized action from being executed indefinitely
after its operational context has changed.

Timeouts and Retries

Each registered tool defines:

Execution timeout
Maximum attempts

Read-only tools may permit a limited retry.

Mutating and high-impact tools use one attempt in this tutorial.

Failures are returned through structured error contracts rather than raw stack
traces.

Dry-Run Isolation

The tutorial runtime does not perform production mutations.

Registered mutating and high-impact tools require:

dry_run=true

Their handlers return an execution plan without changing infrastructure.

This preserves the architecture and authority model without introducing unsafe
side effects.

Structured Status

The runtime returns one status:

SUCCEEDED
REJECTED
FAILED
TIMED_OUT
REPLAYED

These are runtime outcomes, not policy decisions.

Structured Errors

Runtime errors include:

Stable error code
Safe message
Retryable flag

Raw sensitive exception messages are not exposed.

Audit Events

Each execution record includes audit events for:

Request received
Policy binding validated
Execution attempt
Success
Failure
Rejection
Replay prevention

Each event is bound to:

Request ID
Idempotency key
Tool name
Policy fingerprint
Runtime status
Authority Boundary

The runtime may:

Validate policy binding
Revalidate tool schema
Execute a registered handler
Enforce timeout
Enforce idempotency
Apply dry-run restrictions
Record structured audit events

It may not:

Grant authority
Convert DENY to ALLOW
Convert ESCALATE to ALLOW
Create human approval
Change identity
Expand scope
Select an unregistered tool
Accept direct GenAI commands
Perform production mutations in this tutorial
Workflow
GenAI typed recommendation
             |
             v
Deterministic policy
ALLOW | DENY | ESCALATE
             |
             v
Typed runtime request
             |
             v
Fingerprint and schema validation
             |
             v
Idempotency and expiry checks
             |
             v
Isolated registered handler
             |
             v
Structured result + audit events
Run the Demonstration
PYTHONPATH=src python scripts/run_isolated_tool_runtime.py
Run Phase 7 Tests
PYTHONPATH=src python -m pytest tests/unit/runtime -v
Completion Criteria

Phase 7 is complete when:

Only ALLOW decisions can reach a handler.
DENY is rejected before execution.
ESCALATE is rejected before execution.
The policy fingerprint is validated.
The fingerprint is recomputed from synthesis and policy context.
Tool names must agree across synthesis, policy, and runtime.
Only registered runtime tools execute.
Tool risk is revalidated.
Argument schema is revalidated.
Argument tampering is rejected.
Request scope is revalidated.
Expired requests are rejected.
Idempotency prevents duplicate execution.
Timeouts return structured errors.
Handler failures return sanitized errors.
Mutating tools require dry-run mode.
Tutorial handlers perform no production side effects.
Audit events bind execution to the policy fingerprint.
Runtime and handler versions are recorded.
No direct GenAI-to-tool path exists.
All Phase 7 and regression tests pass.
