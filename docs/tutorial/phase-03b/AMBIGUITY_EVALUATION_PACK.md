# Phase 3B — Ambiguity and Classifier-Disagreement Evaluation

## Purpose

Phase 3 produced perfect classification results on a controlled synthetic test set.

That result is valid, but it also demonstrates that the original feature distributions are highly separable.

Phase 3B introduces a sealed challenge set containing:

- Overlapping incident signals
- Contradictory telemetry
- Missing deployment context
- Near-threshold measurements
- Multiple matching deterministic rules
- High-impact incidents without a dominant root-cause pattern
- Isolated noisy features

The pack evaluates limitations without retraining or selecting a new model.

## Governing Boundary

The ambiguity pack must never be used for:

- Model training
- Hyperparameter tuning
- Candidate-model selection
- Decision-threshold optimization
- Synthetic training-data generation

Using the challenge pack to improve the model and repeatedly reevaluating it would convert the challenge set into another validation set.

## Evaluated Classifiers

### Phase 1 deterministic classifier

The rule-based classifier produces:

- Incident category
- Rule-agreement confidence
- Matched rule identifiers

Its confidence is not a statistical probability.

### Phase 3 traditional ML classifier

The locked ML model produces:

- Predicted category
- Complete class-probability distribution
- Top-class confidence
- Second-ranked category
- Probability margin

Its output is probabilistic evidence.

## Why Agreement Is Not Sufficient

The two classifiers can agree and still be wrong.

Agreement may occur because:

- Both were influenced by the same synthetic distributions
- Both depend on the same telemetry features
- The dominant signal hides a secondary cause
- Missing operational context is not represented
- A correlated symptom is mistaken for the root cause

Therefore, agreement is recorded as evidence—not proof.

## Why Disagreement Is Useful

Classifier disagreement tells the orchestrator that deterministic thresholds and learned feature relationships reached different conclusions.

This should trigger additional evidence gathering.

Examples include:

- Retrieve deployment history
- Retrieve authentication logs
- Inspect dependency health
- Compare regional telemetry
- Validate whether a measurement is noisy
- Ask a human for missing operational context

## Probability Margin

The ML probability margin is:

```text
highest class probability - second-highest class probability

A small margin indicates that the model sees competing categories.

A large margin indicates stronger statistical separation, but does not prove the prediction is correct.

GenAI Review Triggers

Phase 3B requests downstream GenAI review when one or more conditions are present:

The classifiers disagree.
ML confidence is below 0.70.
The top-two ML probability margin is below 0.20.
More than one deterministic rule matches.
Contradictory evidence is declared in the case.

The GenAI layer will later use these signals to generate competing hypotheses and identify missing evidence.

GenAI Responsibility

The future GenAI component may:

Explain why classifiers disagree
Compare competing hypotheses
Identify supporting evidence
Identify contradicting evidence
Request additional retrieval
Recommend the next diagnostic step
Abstain when evidence remains insufficient

It may not:

Decide that an action is authorized
Override deterministic policy
Execute a tool
Convert classifier confidence into permission
Hide disagreement from the final evidence record
Evaluation Output

The report records:

Challenge-pack digest
Locked-model digest
Locked-metadata digest
Whether training occurred
Whether model selection occurred
Whether threshold tuning occurred
Classifier agreement
Deterministic matched rules
ML confidence
ML probability margin
Competing signals
Contradictions
Review triggers
Authority boundary
Expected Architecture Transition
Traditional ML prediction
             +
Deterministic classifier result
             +
Classifier agreement or disagreement
             +
Competing signals and contradictions
             |
             v
Permission-Aware Retrieval
             |
             v
GenAI Competing-Hypothesis Analysis
             |
             v
Deterministic Policy

Phase 3B does not yet retrieve documents or call a language model.

It creates the evidence contract those later phases require.

Run the Evaluation
PYTHONPATH=src python scripts/evaluate_ambiguity_pack.py
Run the Tests
PYTHONPATH=src python -m pytest tests/unit/evaluation -v
Completion Criteria

Phase 3B is complete when:

The challenge set is versioned and sealed.
Prohibited uses are declared.
No training labels are included.
The selected model remains unchanged.
Model metadata remains unchanged.
Both classifiers evaluate every case.
Agreement and disagreement are recorded.
ML confidence and probability margin are recorded.
Multiple deterministic rule matches are recorded.
Every ambiguity case produces a GenAI review decision.
The report explicitly states that no training, model selection, or threshold tuning occurred.
All Phase 3B and regression tests pass.
