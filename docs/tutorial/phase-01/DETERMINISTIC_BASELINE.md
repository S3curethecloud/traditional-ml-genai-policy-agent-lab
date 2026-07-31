# Phase 1 — Deterministic Incident Baseline

## Purpose

Before introducing traditional machine learning or generative AI, this phase builds a transparent rule-based incident classifier.

The baseline provides a control implementation that learners can inspect, test, and compare against later probabilistic models.

## Why Begin with Deterministic Rules?

A tutorial should not introduce machine learning before establishing what the system can accomplish with explicit logic.

The baseline helps answer:

- Which decisions can be expressed as fixed thresholds?
- Which rules are easy to explain?
- Where do manually selected thresholds become brittle?
- When does traditional ML provide meaningful additional value?
- Which decisions must remain deterministic even after ML is introduced?

## Input Features

The classifier receives normalized incident features:

| Feature | Meaning |
|---|---|
| `login_failure_rate` | Fraction of login attempts that fail |
| `token_validation_error_rate` | Fraction of requests with token-validation errors |
| `http_5xx_rate` | Fraction of requests returning server errors |
| `latency_p95_ms` | 95th percentile response latency |
| `cpu_utilization_percent` | Current CPU utilization |
| `memory_utilization_percent` | Current memory utilization |
| `dependency_error_rate` | Failure rate from downstream dependencies |
| `network_packet_loss_percent` | Observed network packet loss |
| `deployment_age_minutes` | Minutes since the latest deployment |
| `affected_user_count` | Estimated number of affected users |
| `regions_affected` | Number of affected regions |

## Classification Rules

### Deployment Regression

The baseline classifies an incident as a deployment regression when:

- A deployment occurred within the previous 30 minutes, and
- Login failures or HTTP 5xx errors exceed configured thresholds.

### Authentication Failure

The baseline classifies an incident as an authentication failure when:

- Login failures exceed 10 percent, and
- Token-validation errors exceed 5 percent.

### Infrastructure Saturation

The baseline classifies an incident as infrastructure saturation when:

- CPU utilization exceeds 90 percent, or
- Memory utilization exceeds 90 percent.

### Network Degradation

The baseline classifies an incident as network degradation when:

- Packet loss exceeds 3 percent.

### Dependency Failure

The baseline classifies an incident as a dependency failure when:

- Dependency errors exceed 8 percent.

### Unknown

The classifier returns `unknown` when no rule matches.

## Rule Priority

More than one rule can match the same incident.

The baseline uses this fixed priority order:

1. Deployment regression
2. Authentication failure
3. Infrastructure saturation
4. Network degradation
5. Dependency failure
6. Unknown

This priority is intentionally explicit and deterministic.

It also exposes a limitation: a manually selected priority may hide another valid diagnosis.

## Severity Rules

Severity is calculated separately from incident category.

### SEV-1

Assigned when any of the following are true:

- At least 10,000 users are affected
- At least three regions are affected
- HTTP 5xx errors reach 50 percent

### SEV-2

Assigned when any of the following are true:

- At least 1,000 users are affected
- At least two regions are affected
- HTTP 5xx errors reach 20 percent

### SEV-3

Assigned when any of the following are true:

- At least 100 users are affected
- Login failures reach 10 percent
- P95 latency reaches 2,000 milliseconds

### SEV-4

Assigned when no higher severity threshold is met.

## Confidence Semantics

The deterministic baseline uses a simple confidence convention:

- No matched rule: `0.00`
- One matched rule: `0.70`
- Two matched rules: `0.85`
- Three or more matched rules: `0.95`

This value is not a calibrated statistical probability.

It represents the strength of deterministic rule agreement.

Later phases will contrast this with:

- ML class probabilities
- Retrieval relevance scores
- GenAI-generated confidence
- Deterministic policy thresholds

These values must not be treated as interchangeable.

## What the Baseline Does Well

The baseline is:

- Transparent
- Easy to test
- Fast
- Reproducible
- Explainable
- Independent of external models
- Suitable for fixed operational controls

## What the Baseline Does Poorly

The baseline is limited because:

- Thresholds are manually chosen
- Rules do not learn from historical incidents
- Feature interactions are simplistic
- Fixed priority can suppress competing diagnoses
- Confidence is not statistically calibrated
- Rules may become difficult to maintain as scenarios grow
- Small input changes can cause abrupt category changes

These limitations justify introducing traditional ML later.

## Important Architectural Boundary

The deterministic classifier is not the deterministic policy engine.

They solve different problems:

| Component | Question answered |
|---|---|
| Deterministic classifier | What type of incident appears to be happening? |
| Deterministic policy engine | Is the requested action permitted? |

The classifier may be replaced or supplemented by ML.

The authorization policy must remain independently enforceable.

## Test Coverage

Phase 1 tests verify:

- Deployment regression classification
- Authentication failure classification
- Infrastructure saturation classification
- Network degradation classification
- Dependency failure classification
- Unknown classification
- Deterministic rule priority
- SEV-1 severity assignment

## Completion Evidence

The Phase 1 test command is:

```bash
PYTHONPATH=src python -m pytest tests/unit/baseline -v

Expected result:

8 passed

