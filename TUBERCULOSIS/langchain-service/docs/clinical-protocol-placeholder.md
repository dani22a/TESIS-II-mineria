# Institutional screening protocol (PLACEHOLDER)

> PLACEHOLDER. Replace with the institution's approved protocol.

## Workflow

An operator registers a case and uploads a chest X-ray. The system runs a quality check: images that fail quality control are marked not evaluable and never reach the model. Evaluable images receive a screening score and a heatmap for explanation.

## Human review

A reviewer must confirm or correct every screening result. The system supports the decision and never replaces the clinician. Disagreements between reviewer and system are recorded for audit.

## Data protection

Only pseudonymized identifiers are stored. Language models never receive images or patient identifiers; they may only see aggregated statistics.
