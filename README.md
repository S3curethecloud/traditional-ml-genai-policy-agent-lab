# Traditional ML, GenAI, and Deterministic Policy Agent Lab

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-273%20passing-brightgreen)](#validation-status)
[![Release](https://img.shields.io/badge/release-v1%20complete-success)](#release-status)
[![Authority](https://img.shields.io/badge/production%20authority-human%20controlled-orange)](#authority-boundary)

A tutorial-driven enterprise AI engineering lab demonstrating how traditional machine learning, permission-aware retrieval, generative AI, deterministic policy, agent orchestration, isolated tools, observability, deployment governance, runtime operations, resilience, and progressive delivery work together in a governed agentic workflow.

> Use probabilistic systems for prediction and synthesis, but deterministic systems for authority, validation, and irreversible decisions.

## Release Status

**Version 1 is complete through Phase 15.**

Current v1 status:

- 273 automated tests passing
- Traditional ML classification and typed inference implemented
- Permission-aware retrieval implemented
- Evidence-grounded GenAI synthesis implemented
- Deterministic policy enforcement implemented
- Typed and isolated tool runtime implemented
- Stateful agent orchestration implemented
- Evaluation and evidence generation implemented
- Production hardening controls implemented
- Supply-chain and release evidence implemented
- Governed deployment simulation implemented
- Runtime SLO and incident response implemented
- Resilience and disaster-recovery simulation implemented
- Progressive delivery and rollback governance implemented
- No uncontrolled production action implemented

Phases 16–20 are reserved for **v2**.

## Tutorial Scenario

The lab implements a governed incident-diagnostic agent for an enterprise identity service.

The workflow:

1. Receives and validates an operational incident.
2. Establishes identity, role, tenant, service, and environment context.
3. Uses traditional ML to classify the incident and estimate severity.
4. Retrieves authorized operational evidence.
5. Uses GenAI to synthesize evidence and produce competing hypotheses.
6. Generates a structured diagnostic or tool proposal.
7. Applies deterministic policy before any tool execution.
8. Executes only authorized, typed, and validated operations.
9. Escalates ambiguous, high-risk, or unauthorized actions.
10. Records the complete evidence and decision trail.

## Architecture

```text
Authenticated User or Support Engineer
                 |
                 v
        Request and Identity Context
                 |
                 v
       Traditional ML Inference
       - Incident classification
       - Severity prediction
       - Confidence evidence
                 |
                 v
      Permission-Aware Retrieval
       - Tenant filtering
       - Role filtering
       - Evidence citations
       - Injection detection
                 |
                 v
          GenAI Synthesis
       - Evidence synthesis
       - Competing hypotheses
       - Explanation
       - Abstention
       - Structured tool proposal
                 |
                 v
      Deterministic Policy Engine
       - Identity and role checks
       - Tenant and service scope
       - Tool allowlist
       - Argument validation
       - Risk evaluation
       - Approval requirements
                 |
          ALLOW | DENY | ESCALATE
                 |
                 v
        Isolated Tool Runtime
       - Typed tool contracts
       - Policy fingerprint
       - Idempotency
       - Dry-run enforcement
       - Timeout and failure handling
                 |
                 v
          Agent Orchestrator
       - Workflow state
       - Step sequencing
       - Checkpoints
       - Retries
       - Stop conditions
       - Replay verification
                 |
                 v
       Evaluation and Evidence
       - Traces and metrics
       - Release gates
       - Audit events
       - Recovery evidence
                 |
                 v
      Governed Release Lifecycle
       - Hardening
       - Supply-chain evidence
       - Deployment authorization
       - Runtime SLOs
       - Incident response
       - Disaster recovery
       - Progressive delivery
       - Rollback governance
```

## Component Responsibilities

### Traditional Machine Learning

Traditional ML provides measurable predictive evidence:

- Incident category
- Predicted severity
- Confidence and class probabilities
- Feature-level explanation
- Deterministic-baseline comparison
- Reproducible inference metadata

Traditional ML does not authorize operational actions.

### Permission-Aware Retrieval

The retrieval layer provides:

- Tenant-aware filtering
- Role-aware filtering
- Document-type restrictions
- Hybrid retrieval
- Evidence citations
- Denied-document protection
- Prompt-injection detection

Unauthorized content is filtered before it can become model evidence.

### Generative AI

GenAI provides:

- Evidence synthesis
- Competing hypotheses
- Explanation
- Retrieval-grounded recommendations
- Structured tool proposals
- Citation-backed claims
- Abstention when evidence is insufficient

GenAI cannot grant permissions, execute tools directly, or override policy.

### Deterministic Policy

The policy engine evaluates:

- Identity and role
- Tenant and service scope
- Environment
- Tool permissions
- Tool arguments
- Action risk
- Evidence integrity
- Approval requirements
- Prompt-injection findings

Policy returns:

- `ALLOW`
- `DENY`
- `ESCALATE`

### Isolated Tool Runtime

The runtime enforces:

- Typed request contracts
- Policy-decision verification
- Policy fingerprint binding
- Tool and argument integrity
- Request expiration
- Idempotency
- Dry-run requirements
- Structured timeout and failure responses
- Audit-event generation

The runtime rejects any request without a valid `ALLOW` decision.

### Agent Orchestrator

The orchestrator manages:

- Workflow state
- Ordered execution
- Checkpoints
- Retry budgets
- Stop conditions
- Human escalation
- Replay verification
- Evidence propagation

The orchestrator coordinates components but cannot bypass their authority boundaries.

## Authority Boundary

The system separates reasoning authority from execution authority.

Probabilistic components may:

- Predict
- Retrieve
- Rank
- Synthesize
- Explain
- Recommend
- Abstain

Deterministic components control:

- Authentication
- Authorization
- Tenant isolation
- Tool access
- Argument validation
- Approval enforcement
- Runtime execution
- Release promotion
- Rollback authorization
- Failover authorization

The tutorial does not perform:

- Real production deployment
- Real production traffic shifting
- Autonomous remediation
- Autonomous rollback
- Autonomous regional failover
- Autonomous disaster declaration
- Self-approved privilege escalation
- Direct GenAI-to-tool execution

## Completed v1 Phases

| Phase | Capability | Status |
|---:|---|:---:|
| 0 | Problem definition, system boundary, authority model, and learning objectives | Complete |
| 1 | Deterministic incident-classification baseline | Complete |
| 2 | Reproducible synthetic incident data and quality validation | Complete |
| 3 | Traditional ML training, selection, explanation, and typed inference | Complete |
| 4 | Ambiguity evaluation and competing-classifier evidence | Complete |
| 5 | Permission-aware retrieval and evidence-grounded GenAI synthesis | Complete |
| 6 | Deterministic policy engine | Complete |
| 7 | Typed and isolated tool runtime | Complete |
| 8 | Stateful agent orchestration, checkpoints, and replay | Complete |
| 9 | Workflow evaluation, observability, and evidence bundles | Complete |
| 10 | Production hardening and release controls | Complete |
| 11 | CI, software supply chain, provenance, and deployment handoff | Complete |
| 12 | Deployment runtime and environment promotion governance | Complete |
| 13 | Runtime operations, SLOs, error budgets, and incident response | Complete |
| 14 | Chaos testing, resilience, backup restoration, RPO, RTO, and disaster recovery | Complete |
| 15 | Staged release, progressive delivery, and rollback governance | Complete |

## v2 Roadmap

| Phase | Planned capability |
|---:|---|
| 16 | Security validation, adversarial testing, and compliance evidence |
| 17 | Domain adaptation packs and reusable platform patterns |
| 18 | Platform integration and end-to-end acceptance |
| 19 | Operational readiness and production handoff |
| 20 | Controlled deployment readiness and release closure |

Version 2 will extend the platform assurance model without weakening the authority boundaries established in v1.

## Quick Start

```bash
git clone https://github.com/S3curethecloud/traditional-ml-genai-policy-agent-lab.git
cd traditional-ml-genai-policy-agent-lab
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
PYTHONPATH=src python -m pytest -v
```

## Run the v1 Operational Demonstrations

```bash
PYTHONPATH=src python scripts/run_deployment_runtime.py
PYTHONPATH=src python scripts/run_runtime_operations.py
PYTHONPATH=src python scripts/run_resilience_dr.py
PYTHONPATH=src python scripts/run_progressive_delivery.py
```

These demonstrations operate only on deterministic tutorial state and generated evidence. They do not modify real infrastructure or production traffic.

## Validation Status

The v1 release has:

```text
273 passed
```

Validated controls include:

- Reproducible data generation
- Schema and leakage detection
- Typed ML inference
- Permission-aware retrieval
- Cross-tenant denial
- Prompt-injection detection
- Citation verification
- Deterministic policy enforcement
- Tool-request integrity
- Policy-fingerprint verification
- Runtime idempotency
- Dry-run enforcement
- Workflow checkpoints
- Replay verification
- Release-gate evaluation
- Secret and configuration validation
- Supply-chain evidence
- Immutable image references
- Deployment authorization
- Runtime SLO evaluation
- Error-budget enforcement
- Incident creation and escalation
- Backup-integrity verification
- RPO and RTO validation
- Human-authorized failover simulation
- Progressive traffic-stage approval
- Rollback governance

### Known Non-Blocking Warning

The test suite currently emits NumPy 2.5 deprecation warnings from `joblib.numpy_pickle`.

These warnings are tracked technical debt and do not represent failing tests or authority-boundary violations.

## Engineering Principles

1. Fail closed when authority is unavailable.
2. Never treat model confidence as authorization.
3. Filter evidence before generation.
4. Require citations for evidence-backed claims.
5. Bind tool requests to deterministic policy decisions.
6. Keep GenAI outside the execution-authority boundary.
7. Use checkpoints and replay for workflow recovery.
8. Make release decisions from verifiable evidence.
9. Require humans for production expansion, rollback, and failover.
10. Preserve an auditable record of every governed decision.

## Intended Audience

This lab is designed for:

- Principal and Staff AI Engineers
- AI Platform Architects
- Agentic AI Engineers
- AI Security Architects
- ML Platform Engineers
- Cloud Security Engineers
- MLOps and DevSecOps engineers
- Technical leaders evaluating governed enterprise AI systems

## License and Usage

This repository is an educational and portfolio lab.

All deployment, failover, remediation, traffic-shifting, and rollback operations are simulations unless explicitly integrated with separately authorized infrastructure.
