# 05 Model and Training Specification

System ID: TS-001
Version: 1.0
Last updated: 2026-05-27

## AI role
AI acts as a setup-quality classifier and trade-activation filter; deterministic rules still define market structure and baseline trade logic.

## Labeling policy
1. Binary directional label over horizon bars.
2. Positive class when future return over horizon is greater than zero.
3. Horizon default currently 5 bars.

## Current model baseline
1. Model family: logistic regression.
2. Pipeline: StandardScaler + LogisticRegression.
3. Class weighting: balanced.
4. Probability threshold baseline: 0.5.

## Training protocol
1. Fetch bars from backend historical endpoints.
2. Build feature matrix and labels on train window.
3. Run walk-forward folds on training data with embargo for threshold selection.
4. Fit final model on full train set with selected threshold policy.
5. Evaluate on strict out-of-sample test window.
6. Export ONNX artifact and JSON metrics artifact.

## Current split used in baseline run
1. Train: 2014-05-27 to 2024-05-27.
2. Test: 2024-05-28 to 2026-05-27.
3. Source: FMP.
4. Timeframe: D1.

## Reproducibility controls
1. Persist run windows and source in artifact JSON.
2. Persist model artifact path and generation timestamp.
3. Capture total bars and feature-row counts for train/test.
4. Persist walk-forward fold summaries and selected threshold.
5. Persist cost assumptions used for base and stress scenarios.

## Gaps to close
1. Threshold selection objective currently optimizes median fold net return and should be upgraded to risk-adjusted objective.
2. Cost model remains simplified and should be expanded toward execution-realistic assumptions.
3. Hyperparameter search policy should be explicitly codified per run with trial-budget limits.

## References
1. [../../../training/run_historical_split.py](../../../training/run_historical_split.py)
2. [../../09-training-runs/runs/2026-05-27_19-43-historical-10y-2y/RUN_REPORT.md](../../09-training-runs/runs/2026-05-27_19-43-historical-10y-2y/RUN_REPORT.md)
