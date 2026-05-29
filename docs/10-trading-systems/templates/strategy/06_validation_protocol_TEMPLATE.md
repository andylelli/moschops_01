# 06 Validation Protocol (Template)

System ID: TS-XXX

## Time split policy
1. Train window:
2. Validation window:
3. Final holdout window:
4. Purge/embargo gap:

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

## Trial accounting
1. Total runs performed:
2. Runs excluded and reason:
3. Selected candidate rationale:

## Invalid run conditions
1. Holdout reuse for tuning.
2. Hidden run cherry-picking.
3. Missing critical lineage.
