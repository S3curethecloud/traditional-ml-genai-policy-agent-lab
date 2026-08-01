# Phase 10 — Production Hardening and Release Controls

## Purpose

Phases 1–9 created and evaluated a governed AI workflow.

Phase 10 prepares the architecture for controlled deployment.

It does not add new model intelligence or execution authority.

## Core Principle

> Production hardening constrains how the system operates. It must not weaken
> policy, bypass release evidence, or expand tool authority.

## Production Configuration

The production configuration pins:

- Model provider
- Model name
- Model version
- Prompt version
- Policy version
- Runtime version
- Orchestrator version
- Evaluation version
- Request timeout
- Provider timeout
- Rate limit
- Concurrency limit
- Circuit-breaker thresholds
- Release-evidence requirements
- Promotion paths
- Secret references
- Rollback requirements

Configuration drift must produce a different SHA-256 digest.

## Secret Handling

Secrets must not appear inline in configuration.

The tutorial supports external references such as:

```text
env://RELEASE_ATTESTATION_KEY

Production implementations should use a managed secret system such as:

AWS Secrets Manager
Azure Key Vault
Google Secret Manager
HashiCorp Vault

The tutorial validates the reference but never writes the secret into reports.

Structured Logging

Operational events retain:

Event type
Trace ID
Workflow ID
Severity
Structured attributes

Sensitive fields are recursively redacted.

Examples include:

Authorization headers
API keys
Passwords
Tokens
Cookies
Private keys
Credentials
Rate Limiting

Rate limiting protects:

Model capacity
Retrieval infrastructure
Runtime tools
Tenant fairness
Cost budgets
Abuse boundaries

The tutorial uses a per-subject sliding window.

A production implementation would use a distributed atomic store.

Concurrency Limiting

Concurrency limits protect the system from:

Resource exhaustion
Provider saturation
Tool-runtime saturation
Queue collapse
Cascading failure

Concurrency is distinct from request rate.

A tenant can remain below its rate limit while still attempting too many
simultaneous workflows.

Circuit Breaker

The circuit breaker transitions through:

CLOSED
  |
  v
OPEN
  |
  v
HALF_OPEN
  |
  +---- success ----> CLOSED
  |
  +---- failure ----> OPEN

It prevents repeated calls to an unhealthy dependency.

The circuit breaker does not authorize fallback execution.

Any fallback must remain within the original policy and data-governance
boundary.

Signed Release Attestation

The release attestation binds:

Release ID
Source environment
Target environment
Evidence digest
Configuration digest
Rollback plan
Signer identity
Signature algorithm

The tutorial uses HMAC-SHA256.

A production implementation should use asymmetric signing through a protected
CI identity or key-management service.

Promotion Controls

Promotion is approved only when:

The Phase 9 release gate passed.
The evidence bundle has enough artifacts.
Evidence digest matches the attestation.
Attestation signature is valid.
Release ID matches.
Promotion source is allowed.
Promotion target is allowed.
A rollback plan exists.
Critical component versions are pinned.
Production configuration is valid.
Promotion Is Not Deployment

The promotion evaluator returns:

APPROVE
REJECT

It does not deploy anything.

A deployment system must separately consume an approved, signed promotion
record.

Rollback Evidence

A release must identify a rollback plan before promotion.

A production rollback plan should specify:

Previous known-good version
Database compatibility
Model and prompt rollback
Policy rollback restrictions
Runtime rollback
Feature-flag state
Data migration reversibility
Rollback owner
Rollback verification
Maximum rollback time
Failure Injection

Phase 10 exercises controlled failures:

Provider timeout
Provider failure
Retrieval unavailable
Runtime timeout

Each injected failure must prove:

Failure was observed
Sensitive details were not exposed
Authority was not expanded
Production side effects did not occur
Deployment Readiness

The readiness report contains:

Release ID
READY or BLOCKED status
Individual checks
Passed-check count
Failed-check count
Hardening version
Authority boundary

A failed check blocks promotion.

CI Release Gate

The Phase 10 validation script is suitable for a CI release gate.

A CI pipeline should run:

Unit tests
Regression tests
Evaluation report validation
Evidence-bundle verification
Configuration validation
Secret scanning
Dependency scanning
Container scanning
Signed attestation generation
Deployment-readiness evaluation
Promotion decision
Authority Boundary

Production hardening may:

Validate configuration
Reject inline secrets
Redact logs
Limit request rates
Limit concurrency
Open dependency circuits
Verify evidence
Verify signatures
Block promotion
Require rollback plans

It may not:

Grant tool authority
Change a policy decision
Override a failed release metric
Execute a production deployment
Create a human approval
Reveal secrets
Skip runtime controls
Run the Demonstration
PYTHONPATH=src python scripts/run_production_hardening.py
Run Phase 10 Tests
PYTHONPATH=src python -m pytest tests/unit/hardening -v
Completion Criteria

Phase 10 is complete when:

Production configuration is validated.
Critical versions are pinned.
Configuration digest is reproducible.
Inline secrets are rejected.
External secret references are validated.
Structured logs redact sensitive fields.
Trace and workflow binding remain in logs.
Rate limiting rejects excess requests.
Rate windows expire correctly.
Concurrency limiting rejects excess work.
Circuit breaker opens at its threshold.
Circuit breaker supports half-open recovery.
Successful recovery closes the circuit.
Release attestations are signed.
Tampered attestations are rejected.
Evidence digest is bound to promotion.
Failed release gates block promotion.
Missing rollback plans block promotion.
Insufficient evidence blocks promotion.
Invalid promotion paths block promotion.
Failure injection exposes no secrets.
Failure injection expands no authority.
Readiness evaluation cannot deploy.
Promotion is explicitly APPROVE or REJECT.
All Phase 10 and regression tests pass.
