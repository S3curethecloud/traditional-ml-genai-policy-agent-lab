# Phase 3 — Traditional ML Incident Classifier

## Purpose

This phase demonstrates how traditional machine learning learns classification patterns from labeled incident data.

The ML output is evidence.

It is not:

- An authorization decision
- A tool-execution command
- A policy result
- A substitute for human authority

## Learning Principle

> Traditional ML learns relationships from labeled historical features, but its prediction remains evidence—not authorization and not execution authority.

## Dataset Usage

The phase uses the Phase 2 artifacts:

- `train.csv`
- `validation.csv`
- `test.csv`

The splits have separate responsibilities:

| Split | Purpose |
|---|---|
| Train | Fit candidate model parameters |
| Validation | Compare candidates and select one |
| Test | Evaluate the locked selected model once |

The test set must not participate in model selection.

## Feature Allowlist

The model may use only the canonical operational features:

- Login failure rate
- Token-validation error rate
- HTTP 5xx rate
- P95 latency
- CPU utilization
- Memory utilization
- Dependency error rate
- Network packet loss
- Deployment age
- Affected-user count
- Number of affected regions

The following fields are explicitly excluded:

- `incident_id`
- `category`
- `severity`

`incident_id` is traceability metadata.

`category` is the target label.

`severity` is a separate derived label and could leak incident-impact information into category training.

## Missing-Value Handling

`deployment_age_minutes` may be absent when no deployment exists in the observation window.

The preprocessing pipeline:

1. Converts the empty CSV value to `NaN`.
2. Calculates the training-set median.
3. Replaces missing values with the training median.
4. Adds a missing-value indicator.

The imputer is fitted only on training data.

Validation and test data do not determine imputation values.

## Candidate Models

### Logistic Regression

Logistic regression is the primary interpretable candidate.

It provides:

- Class probabilities
- Per-class coefficients
- Reproducible training
- A linear decision boundary
- A useful educational baseline

Numeric features are:

1. Median-imputed
2. Given missingness indicators
3. Standardized
4. Passed to multinomial classification

### Random Forest

Random forest is the secondary candidate.

It provides:

- Nonlinear decision boundaries
- Feature interaction learning
- Feature-importance estimates
- A comparison with the linear model

Numeric features are median-imputed before tree training.

## Validation-Based Selection

Both candidates are fitted on the training split.

Both are evaluated on the validation split.

The selected model is the candidate with:

1. Highest validation macro F1
2. Lower validation log loss when macro F1 is tied

The model name is locked before the test split is evaluated.

## Evaluation Metrics

### Accuracy

The percentage of all classifications that are correct.

Accuracy can hide weak performance on individual classes, so it is not sufficient alone.

### Macro Precision

Precision is calculated independently for each class and averaged equally.

This asks:

> When the classifier predicts a category, how often is it correct?

### Macro Recall

Recall is calculated independently for each class and averaged equally.

This asks:

> Of the incidents belonging to each category, how many did the model find?

### Macro F1

Macro F1 balances precision and recall while giving every class equal importance.

It is the Phase 3 model-selection metric.

### Confusion Matrix

The confusion matrix shows which categories are mistaken for one another.

This is especially useful for examining:

- Deployment regression versus authentication failure
- Dependency failure versus generic server failure
- Unknown incidents incorrectly assigned to a known class

### Log Loss

Log loss evaluates the complete probability distribution.

A confidently incorrect prediction is penalized more than an uncertain incorrect prediction.

### Expected Calibration Error

Calibration compares predicted confidence with observed correctness.

A well-calibrated model should be correct approximately:

- 60 percent of the time when reporting 60 percent confidence
- 80 percent of the time when reporting 80 percent confidence
- 95 percent of the time when reporting 95 percent confidence

Low expected calibration error is better.

Calibration does not mean the model is accurate. A model can be calibrated but insufficiently discriminative.

## Interpretability

If logistic regression is selected, the metadata records the strongest absolute coefficients per class.

A positive coefficient increases support for a class.

A negative coefficient decreases support for a class.

If random forest is selected, the metadata records the strongest feature-importance values.

Neither explanation proves causality.

The explanation describes learned statistical behavior.

## Deterministic Baseline Comparison

The Phase 1 rule-based classifier is evaluated on the same test split.

This comparison teaches that:

- Rules can be transparent and operationally stable.
- ML can learn more complex feature interactions.
- Rules may outperform ML on strongly encoded thresholds.
- ML may generalize better where rules become brittle.
- Neither classifier authorizes an operational action.

The deterministic baseline and ML classifier both answer:

> What type of incident may be occurring?

The policy engine will later answer:

> Is the recommended action permitted?

## Serialized Artifacts

Training produces:

```text
models/incident-classifier/
├── model.joblib
└── metadata.json

The metadata contains:

Model version
Feature schema version
Selected model
Selection rule
Random seed
Allowed feature columns
Excluded columns
Class names
Split sizes
Class distributions
Validation metrics
Test metrics
Deterministic baseline metrics
Coefficients or feature importances
Model artifact SHA-256
Authority-boundary statement
Typed Inference Contract

Inference returns:

{
  "predicted_category": "authentication_failure",
  "confidence": 0.91,
  "class_probabilities": {
    "authentication_failure": 0.91,
    "dependency_failure": 0.02,
    "deployment_regression": 0.04,
    "infrastructure_saturation": 0.01,
    "network_degradation": 0.01,
    "unknown": 0.01
  },
  "model_version": "incident-classifier-v1",
  "feature_schema_version": "incident-features-v1"
}

The downstream agent must preserve:

Model version
Feature schema version
Predicted category
Complete probability distribution
Incident trace identifier
Known Limitations

The model is trained on synthetic data.

High metrics may reflect simplified feature distributions rather than real-world readiness.

The model has not yet been tested against:

Production telemetry
Long-term drift
New incident categories
Missing values beyond deployment age
Delayed labels
Ambiguous multi-cause incidents
Adversarial feature manipulation
Cross-tenant distribution differences
Authority Boundary

The ML classifier may:

Predict a category
Return probabilities
Contribute evidence
Support hypothesis ranking

The ML classifier may not:

Grant access
Select its own permissions
Authorize tools
Execute operational changes
Override policy
Approve a production action
Commands

Install dependencies:

python -m pip install numpy scikit-learn joblib

Train and evaluate:

PYTHONPATH=src python scripts/train_incident_classifier.py

Run Phase 3 tests:

PYTHONPATH=src python -m pytest tests/unit/ml -v

Run the complete suite:

PYTHONPATH=src python -m pytest -v
Completion Criteria

Phase 3 is complete when:

CSV schema drift is rejected.
Identifier and label leakage are rejected.
Missing deployment age is imputed in the pipeline.
Logistic regression and random forest are compared.
Validation data selects the model.
Test data is evaluated after selection.
Required classification metrics are recorded.
Calibration error is recorded.
Model explanation is generated.
Model and metadata artifacts are serialized.
Typed inference returns valid probabilities.
Deterministic baseline comparison is recorded.
The authority boundary appears in model metadata.
All tests pass.
