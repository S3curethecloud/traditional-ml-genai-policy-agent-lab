# Phase 11 — CI/CD, Supply Chain Security, and Deployment Evidence

## Purpose

Phase 11 converts the prior release controls into an automated delivery gate.

The pipeline can:

- Compile source
- Run tests
- Regenerate evaluation evidence
- Regenerate hardening evidence
- Scan repository content
- Generate an SBOM
- Generate artifact checksums
- Generate build provenance
- Build a non-root container
- Produce a deployment handoff

It does not deploy to production.

## Core Principle

> The delivery pipeline may build, inspect, attest, and approve a release
> artifact. It must not silently weaken controls or deploy without a separate
> authorized deployment action.

## CI Pipeline

The GitHub Actions workflow runs on:

- Pull requests
- Pushes to `main`
- Manual workflow dispatch

The workflow uses:

- Read-only repository permissions
- Credential persistence disabled
- Python 3.12
- A bounded job timeout
- Concurrency cancellation
- Complete regression testing
- Evidence artifact retention

## Test Gate

The pipeline runs:

```text
PYTHONPATH=src python -m pytest -v

All tests must pass before the release evidence is accepted.

Secret and Source Scan

The repository scanner checks:

Prohibited file patterns
Private-key markers
Inline credential markers
Password-style assignments
Secret-style assignments

The tutorial scanner is deterministic and dependency-free.

A production pipeline should additionally use a specialized scanner such as:

Gitleaks
TruffleHog
GitHub secret scanning
Software Bill of Materials

Phase 11 generates a CycloneDX-compatible dependency inventory.

Each component includes:

Package name
Package version
Component type
Package URL

The SBOM digest is bound into build provenance and the deployment handoff.

Checksum Manifest

The checksum manifest records:

Artifact path
SHA-256 digest
Artifact size
Aggregate manifest digest

Tampering with a protected artifact causes verification to fail.

Build Provenance

Build provenance records:

Release ID
Source repository
Source revision
Source branch
Builder identity
Build command
Test command
Policy digest
Checksum-manifest digest
SBOM digest
Deployment-performed flag

The tutorial provenance is deterministic release metadata.

A production implementation should use signed SLSA-compatible provenance.

Container Controls

The tutorial container:

Uses Python 3.12 slim
Runs as user 10001
Compiles source during build
Excludes tests and local environments
Does not embed secrets
Is built but not pushed by the CI workflow
Release Evidence Chain
Source revision
      |
      v
Regression tests
      |
      v
Phase 9 evaluation evidence
      |
      v
Phase 10 readiness evidence
      |
      v
Repository scan
      |
      v
SBOM + checksums + provenance
      |
      v
Container build validation
      |
      v
Deployment handoff
Deployment Handoff

The deployment handoff contains:

Release ID
Source revision
Source environment
Target environment
Release-evidence digest
Checksum-manifest digest
SBOM digest
Provenance digest
Rollback-plan path
READY or BLOCKED decision
Deployment-performed flag

The expected decision is:

READY_FOR_DEPLOYMENT_HANDOFF

This does not mean deployment occurred.

Separation of Duties

The CI pipeline prepares evidence.

A separate deployment system must:

Authenticate the deployment identity.
Verify the deployment handoff.
Verify artifact digests.
Verify environment authorization.
Apply deployment policy.
Record the deployment result.
Rollback Artifact

The rollback plan defines:

Trigger conditions
Previous approved versions
Evidence preservation
Artifact restoration
Configuration restoration
Security-control verification
Post-rollback evidence

The document does not execute a rollback.

Authority Boundary

Phase 11 may:

Run tests
Scan source
Generate an SBOM
Generate checksums
Generate provenance
Build a container
Validate release evidence
Prepare a deployment handoff
Block a release

It may not:

Change deterministic policy
Expand runtime authority
Hide a failed gate
Push an unverified container
Deploy to production
Execute a rollback
Create human approval
Run the Phase 11 Generator
PYTHONPATH=src python scripts/run_supply_chain_evidence.py
Run Phase 11 Tests
PYTHONPATH=src python -m pytest tests/unit/supply_chain -v
Completion Criteria

Phase 11 is complete when:

Supply-chain policy loads successfully.
Policy hashing is reproducible.
Repository scanning detects prohibited files.
Repository scanning detects secret markers.
The clean repository passes scanning.
An SBOM is generated.
The SBOM is reproducible.
SBOM hashing is reproducible.
Artifact checksums verify.
Artifact tampering is detected.
Prior release evidence is verified.
Phase 9 release status is verified.
Phase 10 readiness is verified.
Phase 10 promotion path is verified.
Build provenance is generated.
Provenance records no deployment.
Provenance hashing is reproducible.
A rollback artifact exists.
The container uses a non-root user.
Failed gates block deployment handoff.
Missing rollback evidence blocks handoff.
Passing gates create a deployment handoff.
GitHub Actions runs the complete regression suite.
GitHub Actions builds but does not push the container.
CI uploads release evidence.
No production deployment occurs.
All Phase 11 and regression tests pass.
