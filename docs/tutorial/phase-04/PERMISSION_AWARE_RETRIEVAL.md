# Phase 4 — Permission-Aware Retrieval

## Purpose

Phase 3B identified incidents where deterministic rules and traditional ML
produce competing, incomplete, or contradictory evidence.

Phase 4 retrieves operational knowledge needed to investigate those cases.

The retrieval layer must answer two different questions in the correct order:

1. Is this caller allowed to access the document?
2. How relevant is the authorized document to the query?

Permission filtering must happen before relevance ranking.

## Core Principle

> The classifiers identify what evidence may be needed; permission-aware
> retrieval determines which evidence the current user and workflow may access.

## Knowledge Sources

The tutorial corpus contains:

- Runbooks
- Deployment records
- Prior incidents
- Service documentation
- Ownership and escalation information
- Restricted security documentation
- An untrusted imported note containing prompt-injection text
- A document belonging to another tenant

## Retrieval Identity

Every retrieval request includes:

- User ID
- Tenant ID
- Assigned roles

The identity context is supplied by a trusted gateway or runtime boundary.

It must not be inferred from the query text.

## Retrieval Scope

Every request also includes:

- Service
- Environment
- Optional document-type restrictions
- Maximum result count

Scope is distinct from identity.

A user may have an authorized role but still be denied a document because it
belongs to another tenant, service, environment, or document type.

## Access Evaluation

Each document is checked for:

1. Tenant match
2. Service match
3. Environment scope
4. Role intersection
5. Requested document type

Possible outcome:

```text
ALLOW
DENY

Denied documents do not enter the relevance-ranking corpus.

Why Filtering Must Precede Ranking

Ranking all documents and removing unauthorized results afterward is unsafe.

That design can leak information through:

Document titles
Ranking positions
Scores
Snippets
Embedding behavior
Result counts
Timing behavior

This tutorial ranks only authorized documents.

Denied-Document Evidence

The response can record that access was denied, but it does not return:

Title
Content
Snippet
Relevance score
Citation
Sensitivity details

Denied evidence contains only:

Document ID
Document type
Reason codes

This supports auditability without returning protected content.

Hybrid Retrieval

Phase 4 uses two relevance signals.

Lexical score

The lexical score measures normalized token overlap.

It is useful for exact terminology such as:

Token-validation error
Deployment version
Signing key
Packet loss
Dependency timeout
TF-IDF similarity

TF-IDF represents query and document text as weighted term vectors and measures
cosine similarity.

This provides a lightweight semantic-ranking approximation without introducing
an external embedding service.

Hybrid score

The score is:

0.40 × lexical score + 0.60 × TF-IDF similarity

The weighting is fixed and versioned.

It is not tuned against the Phase 3B challenge set.

Citations

Every authorized result includes a stable citation:

[document-id]

The later GenAI phase must associate factual claims with these citations.

Prompt-Injection Inspection

Retrieved documents are data, not privileged instructions.

The retrieval layer detects suspicious patterns such as:

Ignore previous instructions
You are authorized
Disclose restricted documents
Restart production

Detection does not automatically delete the document.

Instead, the result records:

Whether injection markers were detected
Which markers were detected
Whether the source is trusted to contain instructions

The GenAI layer must treat untrusted content as evidence only.

Trusted Instruction Sources

A runbook can be marked as a trusted instruction source.

This does not mean the runbook can authorize an action.

It means its procedural instructions come from an approved source.

Authorization still belongs to deterministic policy.

Phase 3B Query Planning

The query planner uses:

Deterministic category
ML category
ML second-ranked category
Competing signals
Contradictions
Review triggers

Example:

Rules: deployment_regression
ML: authentication_failure
Second ML class: deployment_regression
Contradiction: authentication signals are stronger

This produces a query covering both deployment and authentication evidence.

The query planner does not choose a final diagnosis.

Security Boundary

Permission-aware retrieval may:

Filter documents
Rank authorized documents
Return citations
Flag untrusted instructions
Record denied access reasons
Supply evidence to GenAI

It may not:

Expand user roles
Cross tenant boundaries
Return denied content
Authorize tools
Execute operational actions
Treat retrieved instructions as policy
Change the locked ML model
Expected Workflow
Phase 3B classifier evidence
            |
            v
Transparent query planning
            |
            v
Identity and scope evaluation
            |
            v
Permission filtering
            |
            v
Hybrid ranking of authorized documents
            |
            v
Citation and injection metadata
            |
            v
GenAI hypothesis analysis
Run the Demonstration
PYTHONPATH=src python scripts/run_permission_aware_retrieval.py
Run Phase 4 Tests
PYTHONPATH=src python -m pytest tests/unit/retrieval -v
Completion Criteria

Phase 4 is complete when:

The knowledge corpus loads under a strict schema.
Duplicate document IDs are rejected.
Tenant isolation is enforced.
Service scope is enforced.
Environment scope is enforced.
Role restrictions are enforced.
Optional document-type scope is enforced.
Permission filtering occurs before ranking.
Denied document content is never returned.
Hybrid lexical and TF-IDF ranking works.
Every authorized result has a citation.
Prompt-injection markers are surfaced.
Trusted-instruction metadata is preserved.
Phase 3B evidence produces targeted queries.
Retrieval reports preserve security properties.
All Phase 4 and regression tests pass.
