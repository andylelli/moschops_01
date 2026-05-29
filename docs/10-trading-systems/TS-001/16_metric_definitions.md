# 16 Metric Definitions

System ID: TS-001
Version: 1.0
Last updated: 2026-05-27

## Purpose
Define metric formulas and pass/fail interpretation used by TS-001 validation and promotion gates.

## Trading metrics
| Metric | Formula | Unit | Pass direction | TS-001 note |
|---|---|---|---|---|
| Net Return | (Ending equity - Starting equity) / Starting equity | % | Higher is better | Must be post-cost for gate decisions |
| Expectancy per Trade | Mean(trade return) | % or R | Higher is better | Positive required for promotion |
| Profit Factor | Gross profit / Abs(gross loss) | Ratio | Higher is better | Draft floor 1.20 |
| Max Drawdown | Min((equity/running max)-1) | % | Less negative is better | Draft ceiling -12% |
| Recovery Time | Time to recover prior equity peak | days/bars | Lower is better | Required for live-readiness review |
| Win Rate | Wins / Trades | % | Context metric only | Not a primary gate metric |

## Stability metrics
| Metric | Definition | Unit | Pass direction |
|---|---|---|---|
| Fold Expectancy Median | Median expectancy across walk-forward folds | % or R | Positive |
| Fold Dispersion | Variance of fold expectancy | value | Lower |
| Regime Dispersion | Variation of return across regimes | % | Lower |

## Diagnostic metrics
| Metric | Definition | Unit | Pass direction | Use |
|---|---|---|---|---|
| AUC | ROC area | 0-1 | Higher | Secondary diagnostic |
| Brier | Probability error | 0-1 | Lower | Calibration diagnostic |
| Precision | TP/(TP+FP) | 0-1 | Contextual | Selectivity diagnostic |
| Recall | TP/(TP+FN) | 0-1 | Contextual | Coverage diagnostic |

## Cost model assumptions (current state)
1. Current strategy proxy metrics are simplified and do not fully include spread/slippage/commission in the final gate decision pipeline.
2. Full cost stress integration remains a blocking task for promotion readiness.

## Draft threshold table
| Metric | Minimum | Target | Hard fail threshold |
|---|---:|---:|---:|
| Profit Factor | 1.20 | 1.50 | < 1.00 |
| Max Drawdown % | -12.00 | -8.00 | < -15.00 |
| Net Return % | > 0.00 | > 5.00 | <= 0.00 |
| Minimum trades | 80 | 150 | < 50 |

## Change control
Any formula or threshold change requires:
1. version increment;
2. rationale entry in 12_change_control.md;
3. update in 08_promotion_gates.md.
