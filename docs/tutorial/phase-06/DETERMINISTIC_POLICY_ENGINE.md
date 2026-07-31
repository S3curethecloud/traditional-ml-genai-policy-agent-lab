# Phase 6 — Deterministic Policy Engine

## Purpose

Phase 5 produced a structured diagnostic synthesis and an optional typed tool
recommendation.

Phase 6 determines whether that recommendation is acceptable under explicit,
versioned policy.

The policy engine returns:

```text
ALLOW
DENY
ESCALATE

It does not execute the tool.

Core Principle

GenAI proposes. Deterministic policy decides. A separate runtime executes only
an authorized request.

Why GenAI Cannot Authorize Tools

A language model is probabilistic and can be influenced by:

Ambiguous evidence
Prompt injection
Incorrect retrieval results
Fabricated reasoning
Missing operational context
Model-version changes
Prompt-version changes
Temperature and provider behavior

Authorization must therefore remain outside the model.

Policy Inputs

The deterministic policy engine evaluates:

Authenticated user ID
Authenticated tenant ID
User roles
Request tenant
Service scope
Environment scope
Recommended tool
Tool arguments
Declared tool risk
Registered tool risk
Authorized citations
Denied document identifiers
Classifier agreement
ML probability margin
Prompt-injection findings
Human-review flag
Approval evidence
Tool Registry

Every callable tool must have a registered policy.

The registry defines:

Tool name
Risk level
Required argument names
Allowed roles
Allowed environments
Minimum citation count
Whether approval is required
Which approval roles are required

An unregistered tool is denied.

Argument Validation

The policy engine validates exact argument names.

It denies:

Missing required arguments
Unexpected arguments
Service mismatches
Environment mismatches

This prevents the model from adding parameters such as:

force=true
skip_approval=true
tenant=other-tenant
Risk Validation

The model cannot assign a lower risk to a tool.

The recommendation risk must match the registered risk.

Example:

restart_service

cannot be declared read_only when its registered policy says mutating.

A mismatch produces DENY.

Evidence Controls

The policy engine validates:

Every synthesis citation is authorized
No denied-document citation is used
Hypothesis citations appear in the citation manifest
The minimum citation threshold is satisfied
At least one hypothesis exists

Citation validation provides provenance. It does not prove the diagnosis is
correct.

Prompt-Injection Findings

If Phase 5 reports ignored untrusted instructions, Phase 6 returns ESCALATE.

The injection text was not followed, but its presence is still material security
evidence that should be reviewed.

Classifier Ambiguity

Classifier disagreement and low ML margin do not automatically block a
read-only evidence-gathering tool.

They do block automatic approval of mutating and high-impact tools.

This permits safe diagnostic progress while restricting operational changes.

Human Approvals

Approval evidence contains:

Approval ID
Approver ID
Approver role
Tenant
Service
Environment
Tool name

An approval is valid only when its scope exactly matches the request.

An approval for another:

Tenant
Service
Environment
Tool

does not satisfy policy.

Decision Semantics
ALLOW

All deterministic checks passed.

ALLOW means the typed request may proceed to a separate tool runtime.

It does not mean the policy engine executed the tool.

DENY

A hard security or contract violation occurred.

Examples:

Tenant mismatch
Unknown tool
Risk mismatch
Invalid arguments
Unauthorized role
Denied citation use
GenAI abstention
ESCALATE

The request is structurally valid but requires additional human judgment or
approval.

Examples:

Prompt-injection evidence
Missing approval
Insufficient citations
Mutating action during classifier disagreement
Low ML margin for a mutating action
High-impact production action
Decision Precedence

The engine uses this precedence:

DENY > ESCALATE > ALLOW

A request containing both a hard denial and an escalation condition is denied.

Production High-Impact Rule

High-impact production actions always escalate.

Even complete approval evidence does not automatically convert a production
rollback into ALLOW in this tutorial policy.

This creates a deliberate final human-control boundary.

Request Fingerprint

Every policy evaluation records a SHA-256 fingerprint derived from:

Synthesis response
Identity
Tenant
Service
Environment
Authorized citations
Denied document IDs
Classifier ambiguity
Approval evidence

The fingerprint supports:

Audit correlation
Replay detection
Decision comparison
Evidence immutability
Incident review
Authority Boundary

The policy engine may:

Validate the request
Apply deterministic rules
Return ALLOW, DENY, or ESCALATE
Record reason codes
Record a request fingerprint
Verify approval scope

It may not:

Execute a tool
Change identity
Grant a role
Create an approval
Rewrite GenAI evidence
Retrieve additional documents
Override tenant isolation
Hide a denial reason
End-to-End Flow
Traditional ML and deterministic classifier
                    |
                    v
Permission-aware retrieval
                    |
                    v
GenAI evidence synthesis
                    |
                    v
Typed tool recommendation
                    |
                    v
Deterministic policy engine
       ALLOW | DENY | ESCALATE
                    |
                    v
Future isolated tool runtime
Run the Demonstration
PYTHONPATH=src python scripts/run_deterministic_policy.py
Run Phase 6 Tests
PYTHONPATH=src python -m pytest tests/unit/policy -v
Completion Criteria

Phase 6 is complete when:

Only registered tools can be evaluated.
Risk must match the tool registry.
Argument names are strictly validated.
Service scope is enforced.
Environment scope is enforced.
Tenant isolation is enforced.
Role authorization is enforced.
Authorized citations are validated.
Denied citations are rejected.
Prompt-injection findings escalate.
GenAI abstention is denied.
Read-only evidence collection can be allowed.
Mutating tools require approval.
Approval scope is validated.
Classifier ambiguity restricts mutating actions.
High-impact production actions escalate.
DENY takes precedence over ESCALATE.
Request fingerprints are reproducible.
Policy and reason versions are recorded.
The policy engine never executes a tool.
All Phase 6 and regression tests pass.
