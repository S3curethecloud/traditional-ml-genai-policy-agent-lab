# Problem and System Boundary

## 1. Business Problem

Enterprise incident responders frequently receive incomplete operational reports such as:

> Customers in the western region are experiencing intermittent login failures after a recent deployment.

The responder must determine:

- What is failing?
- How severe is the incident?
- What evidence supports the diagnosis?
- Which diagnostic action should happen next?
- Is an operational change permitted?
- Does the action require human approval?

A large language model alone is insufficient because incident response requires prediction, evidence, permissions, operational safeguards, and accountability.

## 2. Tutorial Goal

The goal is to teach how multiple decision mechanisms cooperate inside one agentic workflow.

The lab must demonstrate that:

- Traditional ML detects patterns and produces measurable predictions.
- GenAI interprets evidence and produces structured recommendations.
- Deterministic policy enforces authority and safety constraints.
- The orchestrator manages workflow state and execution.
- Humans retain authority over high-impact actions.

## 3. Primary User

The primary user is an authenticated enterprise incident responder.

Example roles include:

- Support engineer
- Site reliability engineer
- Production operator
- Incident commander
- Security reviewer

## 4. Supported Initial Scenario

The first supported scenario is an incident involving an enterprise identity API.

Example symptoms:

- Increased login failures
- Token-validation errors
- Elevated latency
- Regional service degradation
- Failure following a deployment

## 5. In-Scope Capabilities

The initial lab includes:

- Incident intake
- Input validation
- Identity and role context
- Synthetic operational telemetry
- Incident classification
- Severity prediction
- Anomaly scoring
- Retrieval of runbooks and deployment evidence
- Competing-hypothesis generation
- Structured action recommendations
- Policy evaluation
- Simulated diagnostic tools
- Simulated production actions
- Human approval
- Evidence and audit records
- Evaluation scenarios

## 6. Out-of-Scope Capabilities

The initial lab does not include:

- Real production infrastructure changes
- Autonomous unrestricted remediation
- Direct access to live cloud accounts
- Real customer data
- Unbounded web access
- Self-modifying policies
- Model-controlled authorization
- Multi-agent delegation
- Continuous online model retraining

These may be introduced only as clearly separated advanced extensions.

## 7. Safety Boundary

All operational actions are simulated.

The initial implementation must never:

- Restart a real service
- Roll back a real deployment
- Change production configuration
- Access real credentials
- Send external notifications
- Modify cloud resources

## 8. System Boundary

```text
Authenticated User
       |
       v
Request Gateway
       |
       v
Agent Orchestrator
       |
       +-------------------+
       |                   |
       v                   v
Traditional ML       Evidence Retrieval
       |                   |
       +---------+---------+
                 |
                 v
           GenAI Analysis
                 |
                 v
       Deterministic Policy
                 |
       ALLOW / DENY / ESCALATE
                 |
                 v
          Simulated Tools
                 |
                 v
       Evidence and Audit Record
9. Success Condition

The lab succeeds when a learner can explain and demonstrate:

Why one model should not own prediction, explanation, authorization, and execution.
How ML predictions become evidence rather than unquestioned truth.
How GenAI generates grounded and structured recommendations.
How deterministic policy constrains tools and actions.
How the orchestrator handles state, failure, and escalation.
How humans remain accountable for high-risk decisions.
