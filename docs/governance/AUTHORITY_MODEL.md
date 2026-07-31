
Authority Model
1. Governing Principle

The system separates recommendation authority from execution authority.

The model may recommend an action, but only deterministic policy may authorize it, and only the tool runtime may execute it.

2. Authority Participants
User

The user supplies the incident request and authenticated identity context.

The user may have roles such as:

support_engineer
incident_responder
production_operator
incident_commander
security_reviewer
Traditional ML Model

The ML model may:

Classify an incident
Predict severity
Produce anomaly scores
Return probabilities

The ML model may not:

Select its own permissions
Execute tools
Authorize changes
Approve production actions
Generative AI Model

The GenAI model may:

Summarize evidence
Generate hypotheses
Recommend a diagnostic step
Request a typed tool operation
Explain uncertainty
Abstain

The GenAI model may not:

Modify its own policy
Grant itself roles
Override deterministic controls
Execute unrestricted code
Approve high-risk actions
Deterministic Policy Engine

The policy engine may:

Validate identity and roles
Evaluate action scope
Enforce environment restrictions
Apply evidence thresholds
Require human approval
Allow, deny, or escalate

The policy engine may not:

Invent missing evidence
Generate probabilistic diagnoses
Change policies at runtime
Execute tools directly
Tool Runtime

The tool runtime may:

Execute registered tools
Validate typed arguments
Enforce timeouts
Enforce idempotency
Return typed results
Produce audit events

The tool runtime may not:

Execute unregistered tools
Bypass policy decisions
Expand permissions
Accept arbitrary model-generated code
Human Approver

A human approver may:

Approve
Reject
Modify
Expire
Request additional evidence

The human approver remains accountable for high-impact operational actions.

3. Decision Outcomes
ALLOW

The action satisfies all deterministic requirements and may proceed.

DENY

The action violates a non-negotiable constraint and must not proceed.

ESCALATE

The action requires human judgment, additional evidence, or elevated authority.

4. Initial Action Classes
Action	Risk	Initial behavior
Read incident metadata	Low	Allow
Inspect logs	Low	Allow
Inspect deployment history	Low	Allow
Inspect configuration	Medium	Allow with role and scope checks
Restart service	High	Escalate
Roll back deployment	Critical	Escalate
Change identity configuration	Critical	Deny in tutorial runtime
5. Non-Negotiable Rules
GenAI output is never an authorization decision.
Policy must be evaluated before every tool execution.
Tool arguments must pass schema validation.
Production-changing actions require human approval.
Unknown tools are denied.
Out-of-scope services are denied.
Expired approvals cannot be reused.
Duplicate high-impact actions must be blocked.
Every decision must record the policy version.
Every model-derived recommendation must retain its supporting evidence.
