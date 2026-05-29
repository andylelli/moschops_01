# 06 Validation Protocol

System ID: TS-001
Version: 1.0
Last updated: 2026-05-27

## Time-split policy
1. Train zone: historical past only.
2. Validation zone: reserved for model and threshold selection.
3. Final holdout zone: one-time acceptance evaluation.
4. Purge/embargo gap: mandatory when walk-forward folds are enabled.

## Current baseline evidence
1. Historical split run executed with 10-year train and 2-year test windows.
2. Output includes classifier metrics and strategy proxy backtest metrics.
3. Evidence stored in training run folder and artifact JSON.

## Mandatory tests for promotion
1. Purged walk-forward out-of-sample tests across folds.
2. Stress-cost scenarios with wider spread and slippage assumptions.
3. Regime-slice tests (trend/range/high-vol/low-vol).
4. Parameter-perturbation stability tests around chosen settings.
5. Degraded-mode operational safety tests.

## Metrics to report
1. Trading-first metrics: net return after costs, profit factor, max drawdown, expectancy.
2. Stability metrics: fold dispersion and regime consistency.
3. Diagnostics only: AUC, Brier, precision/recall, calibration behavior.

## Invalid run criteria
1. Any holdout reuse for tuning.
2. Hidden experimental cherry-picking.
3. Missing critical lineage artifacts.
4. Cost-free promotion decisioning.

## Trial accounting requirements
1. Record total experiments attempted for each hypothesis.
2. Keep failed runs in the log.
3. Report rationale for selected candidate model.

## Decision outcomes
1. REJECT
2. PAPER_ONLY
3. MICRO_LIVE
4. PROMOTE

## Governance reference
1. [../robust_trading_no_curve_fit_plan.md](../robust_trading_no_curve_fit_plan.md)
