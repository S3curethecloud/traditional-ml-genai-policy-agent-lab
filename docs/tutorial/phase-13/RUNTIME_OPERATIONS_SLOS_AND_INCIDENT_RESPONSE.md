# Phase 13 — Runtime Operations, SLOs, and Incident Response

## Purpose

Phase 13 introduces a governed operational control plane for the deployed
incident-agent platform.

It evaluates runtime evidence, detects SLO failures, creates alerts and
incidents, recommends runbooks and mitigations, and verifies recovery.

It does not execute production remediation.

## Operational Flow

```text
Runtime telemetry
       |
       v
SLI calculation
       |
       v
SLO evaluation
       |
       v
Error-budget evaluation
       |
       v
Alert classification
       |
       v
Incident creation
       |
       v
Runbook recommendation
       |
       v
Rollback or escalation recommendation
       |
       v
Human-authorized mitigation
       |
       v
Recovery verification
       |
       v
Post-incident evidence
Service-Level Indicators

The tutorial evaluates:

Request success
Request latency
Unauthorized runtime execution
Recovery time

Each metric sample contains:

Metric name
Numeric value
Timestamp
Trace identifier
Service-Level Objectives

Configured objectives include:

99 percent request success
95 percent of requests at or below 200 milliseconds
Zero unauthorized runtime executions
95 percent of recoveries within 300 seconds
Error Budgets

For each objective, the evaluator calculates:

Sample count
Compliant sample count
Compliance percentage
Error budget consumed
Error budget remaining
Budget status

Budget states are:

HEALTHY
WARNING
EXHAUSTED
Alert Classification

Failed objectives can produce:

AVAILABILITY_DEGRADATION
LATENCY_DEGRADATION
AUTHORIZATION_VIOLATION
RECOVERY_OBJECTIVE_BREACH
DEPLOYMENT_REGRESSION
UNKNOWN

Authorization violations are classified as SEV_1.

Incident Creation

An incident binds:

Release ID
Environment
Alert IDs
Severity
Deployment correlation
Human-escalation requirement

Production incidents always require human escalation.

Deployment Correlation

The operations layer consumes the Phase 12 deployment report.

It correlates the incident with the current release when:

Release IDs match.
Production deployment status is healthy.
The degraded telemetry is associated with that environment.

Correlation supports a rollback recommendation but does not execute rollback.

Runbook Selection

Runbook selection is evidence-based.

Authorization violations take precedence over availability and latency
degradation because they may indicate an authority-boundary failure.

A runbook recommendation never grants execution authority.

Mitigation Recommendations

The operations layer may recommend:

Human escalation
Runtime isolation
Continued investigation
Deployment rollback

It may not directly perform any of these production actions.

Recovery Verification

Recovery is complete only when all evaluated service objectives pass.

A partially recovered service remains escalated.

Authority Boundary

Runtime operations may:

Consume runtime telemetry
Calculate SLIs
Evaluate SLOs
Calculate error budgets
Create alerts
Classify severity
Create incidents
Correlate deployment evidence
Recommend runbooks
Recommend rollback
Require human escalation
Verify recovery
Create post-incident evidence

Runtime operations may not:

Grant production roles
Approve deployment
Execute rollback
Modify infrastructure
Change deterministic policy
Suppress alerts
Rewrite deployment evidence
Claim recovery without passing evidence
Run Phase 13
PYTHONPATH=src python scripts/run_runtime_operations.py
Run Phase 13 Tests
PYTHONPATH=src python -m pytest tests/unit/operations -v
Completion Criteria

Phase 13 is complete when:

Operations policy validates.
Automatic remediation remains disabled.
SLO definitions are unique.
SLI comparisons are deterministic.
Minimum sample counts are enforced.
Compliance percentages are calculated.
Error budgets are calculated.
Error-budget exhaustion is detected.
Failed SLOs create alerts.
Passing SLOs do not create alerts.
Authorization violations become SEV-1.
Alerts create an incident.
Production incidents require escalation.
Incidents correlate to deployment evidence.
Runbooks are evidence-selected.
Runbooks cannot execute automatically.
Rollback may be recommended.
Rollback requires human approval.
Recovery requires every SLO to pass.
Audit events remain ordered.
No automatic remediation occurs.
No production side effects occur.
Phase 13 and regression tests pass.
