
Tutorial Phase Gates
Governing Rule

A later phase must not compensate for an incomplete earlier phase.

Each phase must have:

A learning objective
An implementation artifact
A demonstration
Automated tests
A completion checklist
Phase 0 — Foundation

Required artifacts:

Problem and system boundary
Learning objectives
Authority model
Initial scenarios
Repository roadmap

Exit criteria:

System responsibilities are separated.
In-scope and out-of-scope behavior is explicit.
Human authority is defined.
No real infrastructure action is permitted.
Tutorial phases are documented.
Phase 1 — Deterministic Baseline

Exit criteria:

A non-AI baseline can classify simple incidents using explicit rules.
Baseline limitations are documented.
Tests cover expected rule outcomes.
Phase 2 — Dataset

Exit criteria:

Synthetic incidents are reproducible.
Features and labels are documented.
Data quality checks pass.
No sensitive data is present.
Phase 3 — Traditional ML

Exit criteria:

The model trains reproducibly.
Metrics are reported.
Confidence behavior is evaluated.
The model artifact is versioned.
Inference uses typed contracts.
Phase 4 — Retrieval

Exit criteria:

Runbooks and operational evidence are retrievable.
Metadata filtering is enforced.
Retrieved evidence includes source identifiers.
Adversarial documents are represented.
Phase 5 — GenAI

Exit criteria:

Responses follow a schema.
Hypotheses contain supporting and contradicting evidence.
Citation validation exists.
Abstention is tested.
Prompt injection is tested.
Phase 6 — Policy

Exit criteria:

Tool authorization is deterministic.
Allow, deny, and escalate are tested.
Policies are versioned.
Models cannot override decisions.
Phase 7 — Tools

Exit criteria:

Tools use typed contracts.
Risk classifications exist.
Timeouts and idempotency are defined.
No real production action occurs.
Phase 8 — Orchestration

Exit criteria:

Workflow states are explicit.
Invalid transitions are rejected.
Retries and stop conditions are bounded.
Checkpoint recovery is demonstrated.
Phase 9 — Human Approval

Exit criteria:

High-risk actions pause.
Approval, rejection, expiration, and resume are tested.
Approval identity is recorded.
Phase 10 — Evaluation

Exit criteria:

ML, GenAI, policy, and end-to-end metrics are separated.
Failure and adversarial cases run automatically.
Expected outcomes are declared.
Phase 11 — Evidence and Observability

Exit criteria:

Every workflow produces a trace.
Model, prompt, policy, and tool versions are recorded.
Sensitive content is excluded from logs.
Phase 12 — End-to-End Demonstration

Exit criteria:

Happy path passes.
Denied-action path passes.
Escalation path passes.
Incorrect-ML-prediction path passes.
Prompt-injection path passes.
