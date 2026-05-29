# 06 Validation Protocol

System ID: TS-003

## Time split policy
1. Train window: rolling development windows ending before holdout boundary.
2. Validation window: purged walk-forward folds on H4 features.
3. Final holdout window: acceptance only; never used for tuning.
4. Purge/embargo gap: at least 5 bars between fold train and validation partitions.

## Mandatory tests
1. Walk-forward out-of-sample test.
2. Cost stress test (spread/slippage/commission).
3. Regime slice test.
4. Parameter perturbation robustness test.
5. Latency/degraded-mode operational test.

## Metrics to report
1. Trading metrics: expectancy, net return, PF, max DD, recovery time.
2. Stability metrics: fold variance, regime variance.
3. Diagnostic metrics: AUC, Brier, calibration bins.
4. Constraint diagnostics: constraintsSatisfied, selectionMode, and medianTrades.

## Trial accounting
1. Total runs performed:
2. Runs excluded and reason:
3. Selected candidate rationale:

## Invalid run conditions
1. Holdout reuse for tuning.
2. Hidden run cherry-picking.
3. Missing critical lineage.
4. Fallback promotion when fail-closed mode is declared.

