# Phase 17 — Domain Adaptation Packs and Reusable Platform Patterns

## Purpose

Phase 17 separates the reusable governed-agent platform from domain-specific
configuration.

The platform kernel retains authority for identity, tenant isolation, policy
evaluation, tool execution, orchestration, evidence, security validation,
release governance, and production authorization.

Domain adaptation packs provide bounded configuration for:

- Domain vocabulary
- Incident taxonomy
- Evidence-source metadata
- Tool metadata
- Policy restrictions
- Evaluation requirements
- Deployment constraints

## Reference and Candidate Domains

The phase includes two packs:

1. `identity-operations-v1`
   The reference implementation represented by the existing tutorial.

2. `payments-operations-v1`
   A reusable candidate adaptation for payment-processing incident diagnosis.

The payments pack does not process or mutate real transactions.

## Reusable Pattern

```text
Platform Kernel
    |
    +-- Stable contracts
    +-- Authority boundaries
    +-- Policy enforcement
    +-- Runtime controls
    +-- Evidence model
    +-- Release governance
            |
            v
Domain Adaptation Pack
    |
    +-- Taxonomy
    +-- Evidence sources
    +-- Tool metadata
    +-- Evaluation cases
    +-- Deployment profile
            |
            v
Deterministic Pack Validation
            |
      VALID | INVALID
            |
            v
READY FOR INTEGRATION | BLOCKED
Validation Rules

A valid domain pack must:

Target the current platform contract
Use only platform-approved capabilities
Define unique incident categories
Define tenant-scoped evidence sources
Use recognized tool-risk levels
Require approval for mutating tools
Deny cross-tenant access
Deny unapproved production mutation
Deny direct GenAI-to-tool execution
Require a complete evaluation profile
Require human approval for production activation
Preserve all platform authority boundaries
Authority Boundary

A domain adaptation pack may:

Define domain terminology
Define incident categories
Identify evidence-source types
Declare tool metadata
Narrow policy behavior
Add evaluation cases
Restrict deployment environments

A domain adaptation pack may not:

Execute tools
Register tools automatically
Expand platform capabilities
Weaken tenant isolation
Modify platform policy
Approve exceptions
Activate itself
Deploy itself
Change production infrastructure
Compliance and Security Continuity

Every domain pack inherits the security requirements validated in Phase 16.

Adapting the platform to another domain does not bypass:

Prompt-injection defenses
Cross-tenant denial
Policy-fingerprint validation
Tool-argument integrity
Approval binding
Release-evidence integrity
Supply-chain integrity
Recovery controls
Progressive-delivery governance
Run Phase 17
PYTHONPATH=src python scripts/run_domain_adaptation.py
Run Phase 17 Tests
PYTHONPATH=src python -m pytest tests/unit/domain_adaptation -v
Completion Criteria

Phase 17 is complete when:

The adaptation policy validates.
Automatic activation is disabled.
Automatic policy mutation is disabled.
Automatic tool registration is disabled.
The reusable template exists.
The identity reference pack validates.
The payments candidate pack validates.
Both pack digests are reproducible.
Unsupported capabilities are rejected.
Policy expansion is rejected.
Cross-tenant weakening is rejected.
Unapproved mutating tools are rejected.
Pack-level tool execution is rejected.
Pack-level policy mutation is rejected.
Pack-level exception approval is rejected.
Self-activation is rejected.
Domain taxonomies remain isolated.
Evidence sources remain isolated.
The candidate adds no unauthorized capability.
Adaptation is ready only after deterministic validation.
Phase and regression tests pass.
