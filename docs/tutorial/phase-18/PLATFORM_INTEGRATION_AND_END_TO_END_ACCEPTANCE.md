# Phase 18 — Platform Integration and End-to-End Acceptance

## Purpose

Phase 18 validates the governed AI platform as an integrated system.

Earlier phases proved individual components and controls. This phase verifies
that those components preserve ordering, authority, evidence continuity, and
safe stopping behavior across complete workflow paths.

## Acceptance Domains

The suite exercises:

- Identity operations
- Payments operations

Both domains use the same platform authority model while preserving independent
taxonomies, evidence sources, roles, and tools.

## Acceptance Scenario Types

The suite includes:

- Authorized read-only success
- Cross-tenant denial
- Prompt-injection escalation
- Insufficient-evidence abstention
- Policy-fingerprint rejection
- Mutating-action escalation

Every scenario is executed for both supported domains.

## Integrated Stage Order

```text
request_validation
        |
domain_resolution
        |
ml_inference
        |
retrieval
        |
genai_synthesis
        |
policy_evaluation
        |
runtime_evaluation
        |
orchestration
        |
observability
        |
security_validation
        |
release_evidence

A negative outcome may stop execution before runtime, but orchestration,
observability, security validation, and evidence recording must still complete.

Acceptance Requirements

The platform is accepted for operational-readiness evaluation only when:

Every required domain is represented.
Every required scenario type is represented.
Every scenario produces its expected result.
Stage coverage is 100 percent.
Evidence continuity is 100 percent.
Unauthorized scenarios never execute runtime.
No scenario performs a real side effect.
No acceptance exception is automatically approved.
No remediation is automatically performed.
No production execution occurs.
Authority Boundary

The acceptance harness may:

Simulate integrated workflows
Evaluate deterministic outcomes
Record stage evidence
Verify stop conditions
Verify runtime non-execution
Calculate acceptance metrics
Produce an acceptance decision

It may not:

Deploy the system
Shift production traffic
Mutate production data
Approve exceptions
Remediate failures
Trigger rollback or failover
Expand platform capabilities
Override deterministic policy
Run Phase 18
PYTHONPATH=src python scripts/run_integration_acceptance.py
Run Phase 18 Tests
PYTHONPATH=src python -m pytest tests/unit/integration_acceptance -v
Completion Criteria

Phase 18 is complete when:

The acceptance policy validates.
Automatic acceptance approval remains disabled.
Automatic exception approval remains disabled.
Automatic remediation remains disabled.
Production execution remains disabled.
Scenario IDs are unique.
Required domains are represented.
Required scenario types are represented.
Authorized read-only scenarios complete.
Cross-tenant attempts are denied.
Prompt injection is escalated.
Insufficient evidence causes abstention.
Policy forgery is rejected.
Mutating actions without approval escalate.
Unauthorized scenarios do not execute runtime.
Stage order remains deterministic.
Evidence continuity is complete.
Scenario pass rate is 100 percent.
No real side effects occur.
The platform is accepted for operational readiness.
Phase and regression tests pass.
