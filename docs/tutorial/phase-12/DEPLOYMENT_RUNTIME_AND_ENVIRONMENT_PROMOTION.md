# Phase 12 — Deployment Runtime and Environment Promotion

## Purpose

Phase 12 introduces a controlled deployment-runtime simulation.

It consumes the Phase 11 deployment handoff and demonstrates how an approved
release moves from staging to production without allowing CI to deploy directly.

## Core Principle

> Promotion approval and deployment execution are separate authorities.

## Deployment Flow

```text
Phase 11 deployment handoff
            |
            v
Deployment identity validation
            |
            v
Immutable manifest validation
            |
            v
Environment preflight
            |
       +----+----+
       |         |
       v         v
    STAGING   PRODUCTION
       |         |
       |      approval required
       |         |
       +----+----+
            |
            v
Simulated deployment runtime
            |
            v
Health + readiness checks
            |
            v
Drift detection
            |
       +----+----+
       |         |
       v         v
    HEALTHY   ROLLBACK
Immutable Image Reference

The deployment manifest must use:

sha256:<64 hexadecimal characters>

Mutable tags such as latest are rejected.

Deployment Identity

A deployment identity must contain:

Subject ID
Deployment roles
Explicit environment scope

The required execution role is:

deployment_operator

Production approval additionally requires:

production_approver
Environment Overlays

Staging and production use distinct overlays.

Each overlay defines:

Replica count
Maximum concurrency
Request timeout
Provider timeout
Health-failure threshold
Human-approval requirement
Simulation permission
Production-side-effect prohibition
Staging Promotion

Staging requires:

Deployment operator role
Staging scope
Valid Phase 11 handoff
Matching source revision
Rollback plan
Immutable image
Valid environment configuration

Staging does not require human approval in this tutorial.

Production Promotion

Production requires every staging control plus:

Production environment scope
Production approver role
Explicit approval record
Matching release ID
Matching environment
Approval decision set to true
Evidence digest matching the Phase 11 handoff
Supply-Chain Binding

The deployment runtime verifies:

Deployment handoff exists
Handoff decision is ready
Handoff says deployment has not occurred
Manifest revision matches handoff revision
Rollback evidence exists
Health and Readiness

After applying simulated state, the runtime evaluates:

Health result
Readiness result

A failure causes simulated rollback.

Drift Detection

Desired state is compared with observed state for:

Environment
Release ID
Image digest
Source revision
Replica count
Environment-configuration digest

Any mismatch produces DRIFTED.

Rollback

Rollback removes simulated runtime state.

The tutorial does not execute:

Kubernetes changes
Cloud API calls
Terraform
Container publication
Production traffic changes
Audit Events

Deployment audit events record:

Sequence
Event type
Release ID
Environment
Actor
Detail
Evidence references

Events remain ordered and bound to the release.

Separation from CI

The Phase 11 GitHub Actions workflow may prepare:

READY_FOR_DEPLOYMENT_HANDOFF

It may not call the deployment runtime for production.

A separate deployment identity must consume the handoff.

Authority Boundary

The deployment runtime may:

Validate a deployment identity
Validate immutable manifests
Verify a supply-chain handoff
Require production approval
Apply simulated runtime state
Run health and readiness checks
Detect drift
Remove simulated state
Record audit evidence

It may not:

Change deterministic policy
Grant deployment roles
Create production approval
Rewrite supply-chain evidence
Deploy real infrastructure
Bypass health checks
Suppress drift
Hide rollback evidence
Run the Demonstration
PYTHONPATH=src python scripts/run_deployment_runtime.py
Run Phase 12 Tests
PYTHONPATH=src python -m pytest tests/unit/deployment -v
Completion Criteria

Phase 12 is complete when:

Deployment manifest requires an immutable digest.
Manifest versions are pinned.
Staging overlay validates.
Production overlay validates.
Environment digests are reproducible.
Deployment identity is required.
Deployment role is required.
Environment scope is enforced.
Phase 11 handoff is required.
Source revision is bound to the handoff.
Rollback evidence is required.
Staging deployment is allowed.
Production without approval is blocked.
Production approval is evidence-bound.
Approved production deployment is allowed.
Health failure triggers rollback.
Readiness failure triggers rollback.
Desired runtime state is drift-free.
Modified runtime state is detected.
Manual rollback removes runtime state.
Audit events are ordered.
Audit events bind release and environment.
No real infrastructure side effects occur.
CI has no direct production deployment path.
All Phase 12 and regression tests pass.
