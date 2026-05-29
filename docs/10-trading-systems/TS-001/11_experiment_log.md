# 11 Experiment Log

System ID: TS-001
Version: 1.0
Last updated: 2026-05-27

## Experiment entries
| Date | Experiment ID | Hypothesis | Single change made | Result summary | Decision |
|---|---|---|---|---|---|
| 2026-05-27 | EXP-001 | 10y train + 2y test split can deliver robust directional filtering on EURUSD D1 | Introduced historical split runner and fixed strategy metric computation | OOS classifier moderate; strategy-proxy metrics positive but gate set incomplete | Continue research |
| 2026-05-27 | EXP-005 | Purged walk-forward threshold selection plus explicit cost assumptions should improve robustness and reduce curve-fit risk | Added walk-forward threshold selection with embargo and cost-aware plus stress-cost forward metrics in runner | Forward test remained profitable after costs, but risk profile worsened (higher drawdown) versus prior thresholding | Keep framework; refine selection objective |
| 2026-05-27 | EXP-010 | Multi-run parameter exploration can improve TS-001 while preserving no-curve-fit protocol | Ran 9 development runs on pre-holdout split and selected config by dev-only score, then executed 1 locked final holdout run | Best dev config (R06) produced strong holdout return and PF, but drawdown remained above strict promotion limits | Continue research; tighten risk-adjusted selection objective |

## Linked evidence
1. [../../09-training-runs/runs/2026-05-27_19-43-historical-10y-2y/RUN_REPORT.md](../../09-training-runs/runs/2026-05-27_19-43-historical-10y-2y/RUN_REPORT.md)
2. [../../../training/run_historical_split.py](../../../training/run_historical_split.py)
3. [../../09-training-runs/runs/2026-05-27_20-53-historical-10y-2y-improved/artifacts/historical_split_report.json](../../09-training-runs/runs/2026-05-27_20-53-historical-10y-2y-improved/artifacts/historical_split_report.json)
4. [../../09-training-runs/runs/2026-05-27_20-53-historical-10y-2y-improved/run_output.log](../../09-training-runs/runs/2026-05-27_20-53-historical-10y-2y-improved/run_output.log)
5. [../../09-training-runs/runs/2026-05-27_21-00-ts001-10run-lab/summary.csv](../../09-training-runs/runs/2026-05-27_21-00-ts001-10run-lab/summary.csv)
6. [../../09-training-runs/runs/2026-05-27_21-00-ts001-10run-lab/summary.json](../../09-training-runs/runs/2026-05-27_21-00-ts001-10run-lab/summary.json)
7. [../../09-training-runs/runs/2026-05-27_21-00-ts001-10run-lab/R10-holdout-final/artifacts/historical_split_report.json](../../09-training-runs/runs/2026-05-27_21-00-ts001-10run-lab/R10-holdout-final/artifacts/historical_split_report.json)

## Integrity rules
1. No deletion of failed or invalid runs.
2. Mark any policy-violating run as INVALID_FOR_PROMOTION.
3. Keep trial counts explicit when testing multiple variants.

## Next planned experiments
1. EXP-002: Purged walk-forward protocol with fold-level reporting.
2. EXP-003: Stress-cost matrix with spread/slippage shocks.
3. EXP-004: Threshold stability sweep with fixed holdout untouched.
4. EXP-006: Risk-adjusted threshold objective to optimize return-drawdown balance instead of raw median net return.
5. EXP-011: Introduce hard drawdown and minimum-trades constraints during dev-run config selection.
