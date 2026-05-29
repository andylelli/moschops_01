# 06 Validation Protocol

System ID: TS-002

## Time split policy
1. Train window: rolling development windows ending before holdout boundary.
2. Validation window: walk-forward validation folds with no overlap leakage.
3. Final holdout window: locked acceptance-only window; never used for tuning.
4. Purge/embargo gap: minimum 5 bars, tunable only in development cycle design.

## Mandatory tests
1. Walk-forward out-of-sample test.
2. Cost stress test (spread/slippage/commission).
3. Regime slice test.
4. Parameter perturbation robustness test.
5. Latency/degraded-mode operational test.
6. Feasibility gate test under hard constraints before holdout execution.

## Metrics to report
1. Trading metrics: expectancy, net return, PF, max DD, recovery time.
2. Stability metrics: fold variance, regime variance.
3. Diagnostic metrics: AUC, Brier, calibration bins.
4. Constraint diagnostics: feasibility status, median trades, and selected threshold mode.

## Trial accounting
1. Total runs performed: tracked per batch and cumulative system total.
2. Runs excluded and reason: explicit INVALID_FOR_PROMOTION tagging required.
3. Selected candidate rationale: must reference dev-only evidence and hard gate outcome.

## Invalid run conditions
1. Holdout reuse for tuning.
2. Hidden run cherry-picking.
3. Missing critical lineage.
4. Any fallback-selected run when hard constraints are declared and fail-closed mode is required.

