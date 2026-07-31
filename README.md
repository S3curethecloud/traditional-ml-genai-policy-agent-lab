# Traditional ML, GenAI, and Deterministic Policy Agent Lab

A tutorial-driven enterprise AI lab demonstrating how traditional machine learning, generative AI, deterministic policy, agent orchestration, tools, and human authority work together in a governed agentic workflow.

## Core Teaching Principle

> Use probabilistic systems for prediction and synthesis, but deterministic systems for authority, validation, and irreversible decisions.

## Tutorial Scenario

The lab implements a governed incident-triage agent for an enterprise identity service.

The workflow will:

1. Receive an operational incident.
2. Validate identity, role, and request context.
3. Collect telemetry and operational evidence.
4. Use traditional ML to classify the incident and predict severity.
5. Use GenAI to synthesize evidence and generate competing hypotheses.
6. Produce a structured diagnostic or action recommendation.
7. Apply deterministic policy before any tool execution.
8. Execute approved diagnostic actions.
9. Escalate high-risk, ambiguous, or unauthorized actions to a human.
10. record the complete evidence and decision trail.

## Technology Responsibilities

### Traditional Machine Learning

Traditional ML provides measurable predictions such as:

- Incident category
- Severity
- Anomaly score
- Failure probability
- Confidence and class probabilities

Traditional ML does not authorize operational actions.

### Generative AI

GenAI provides:

- Evidence synthesis
- Hypothesis generation
- Explanation
- Retrieval-grounded recommendations
- Structured tool requests
- Abstention when evidence is insufficient

GenAI does not grant permissions or override policy.

### Deterministic Policy

Deterministic policy evaluates:

- Identity
- Role
- Tenant and service scope
- Environment
- Tool permissions
- Action risk
- Evidence thresholds
- Approval requirements

Policy produces explicit outcomes:

- `ALLOW`
- `DENY`
- `ESCALATE`

### Agent Orchestrator

The orchestrator manages:

- Workflow state
- Step sequencing
- Retry budgets
- Stop conditions
- Tool execution
- Human escalation
- Checkpoint and recovery behavior

The orchestrator coordinates authority boundaries but does not bypass them.

## Planned Tutorial Phases

| Phase | Topic |
|---|---|
| 0 | Problem, boundaries, authority, and learning objectives |
| 1 | Deterministic incident-handling baseline |
| 2 | Synthetic incident dataset |
| 3 | Traditional ML classifier |
| 4 | Permission-aware retrieval |
| 5 | GenAI evidence synthesis |
| 6 | Deterministic policy engine |
| 7 | Typed tool runtime |
| 8 | Agent state machine |
| 9 | Human approval workflow |
| 10 | Evaluation and adversarial testing |
| 11 | Observability and evidence |
| 12 | End-to-end governed demonstration |

## Repository Status

Phase 0 is in progress.

No runtime capability is authorized until the tutorial boundaries, authority model, and evaluation expectations are documented.
