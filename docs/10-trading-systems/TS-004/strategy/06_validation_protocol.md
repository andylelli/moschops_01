# 06 Validation Protocol

System ID: TS-004
Version: 1.0
Last updated: 2026-05-28

## Validation philosophy

TS-004 follows the lab operating model: dev-window experiments, one locked holdout run, promotion only through gate evidence. The holdout is a single unrepeatable acceptance test, not a tuning signal.

## Validation stages

| Stage | Window | Purpose | Run count policy |
|---|---|---|---|
| Development | 2012-01-01 – 2021-12-31 train / 2022-01-01 – 2022-12-31 test | Hypothesis testing, config selection | Unlimited |
| Walk-forward | Dev window, 5 folds | CV robustness and fold consistency | Per dev experiment |
| Stress testing | Dev window, best config | Cost shock and drawdown sensitivity | EXP-005 onwards |
| Holdout acceptance | 2023-01-01 – 2024-12-31 | Final gate evidence | 1 only |

## Walk-forward protocol

| Parameter | Value |
|---|---|
| Folds | 5 |
| Window | Expanding |
| Embargo | 5 bars (20 hours) |
| Horizon per fold test | Variable (equal time slices) |
| Threshold | Selected using constrained optimisation on dev CV results |
| Fold reporting | Per-fold: AUC, PF, max DD, trade count, expectancy |
| Consistency metric | % folds with PF > 1.00 |

## Cost model used in validation

| Component | Base | Stress (2× spread, 3× slippage) |
|---|---|---|
| Spread | 2.5 bps | 5.0 bps |
| Commission | 1.0 bps | 1.0 bps (not stressed) |
| Slippage | 0.5 bps | 1.5 bps |
| Overnight swap | 0.5 bps/night × 2 nights | 1.5 bps/hold |
| Total per trade | ~4.5 bps | ~9.0 bps |

**All strategy metrics (PF, expectancy, return) are reported on a net-after-cost basis using the base cost model. Stress metrics are reported separately.**

## Statistical robustness checks

| Check | Method | Minimum standard |
|---|---|---|
| Out-of-sample AUC | 5-fold CV median | ≥ 0.53 |
| Calibration error | Brier score | ≤ 0.25 |
| Probability of Backtest Overfitting | `cpcv.py probability_of_backtest_overfitting` | < 0.40 |
| Monte Carlo drawdown distribution | `mc_simulation.py mc_drawdown_stats` | P95 max DD ≤ 25% |
| Bootstrap Sharpe distribution | `mc_simulation.py mc_sharpe_distribution` | P5 Sharpe ≥ 0.0 |
| Fold consistency | % folds with PF > 1.00 | ≥ 60% (3 of 5) |

## Holdout acceptance criteria

The following must all be true for the holdout run to pass:

| Criterion | Threshold | Gate |
|---|---|---|
| Trade count | ≥ 60 | C |
| Profit factor | ≥ 1.25 | C |
| Maximum drawdown | ≤ 20% | C |
| Expectancy (bps after cost) | > 5 bps | C |
| Median fold PF (from dev CV) | ≥ 1.10 | B |
| CV fold consistency | ≥ 60% folds profitable | B |
| MC P95 drawdown | ≤ 25% | C |

Failure of any single criterion is sufficient to reject promotion.

## Stress test protocol (EXP-005)

Apply the following shocks to the best dev config:

| Shock | Config |
|---|---|
| 2× spread | Replace 2.5 bps with 5.0 bps |
| 3× slippage | Replace 0.5 bps with 1.5 bps |
| Full combined stress | Apply both simultaneously |
| Regime gate shock | Widen gate to [0.60, 2.50]; measure trade count and PF sensitivity |

Report: PF under each shock, max DD under each shock, and % config still meets PF ≥ 1.00.

## Spread simulation (optional, EXP-005+)

Use `training/spread_sim.py` (P3) to simulate variable spreads at event bar indices:
- Base spread: 2.5 bps
- News multiplier: 4.0× at identified event bars
- Overnight multiplier: 2.0× at overnight bars

This provides a more realistic cost model than constant spread assumptions.

## Run report — required after every experiment

After each training and test run, a `run_report.md` **must** be written to the run directory before the experiment is logged in `11_experiment_log.md`.

**Steps:**
1. Copy the template from `logs/training/run_report_template.md` into the run directory as `run_report.md`.
2. Fill all `{{PLACEHOLDER}}` fields from `report.json`, `run_config.json`, and the terminal output.
3. Complete the Scorecard (each aspect scored 1–10 with a one-line rationale).
4. Complete the Gate Assessment table.
5. Write a Root Cause Analysis (minimum 2 bullet points for failing runs).
6. Commit `run_report.md` alongside the other run artefacts.

The run report is the human-readable companion to `report.json`. It is the primary document reviewed when deciding whether to proceed to the next experiment.

**Reference example:** `logs/training/2026-05-29/164822_EURUSD_H4_exp-001/run_report.md`

## Validation artefacts required per run

| Artefact | Required for holdout? | Notes |
|---|---|---|
| `run_report.md` | Yes | Scored human-readable report (see template above) |
| `report.json` | Yes | Full metric table (machine-readable source of truth) |
| `feature_schema.json` | Yes | Confirm no feature leakage |
| Per-fold metric table | Yes | Embedded in `report.json` `walkForwardSelection.foldSummaries` |
| Cost model section | Yes | Must show base, no-cost, and stress cost rows |
| PBO calculation | Yes (EXP-004+) | From `cpcv.py` |
| Monte Carlo summary | Yes (EXP-004+) | From `mc_simulation.py` |
| Shadow trader report | No | Nice-to-have from EXP-001+ |

See [13_audit_traceability.md](13_audit_traceability.md) for complete lineage requirements.
