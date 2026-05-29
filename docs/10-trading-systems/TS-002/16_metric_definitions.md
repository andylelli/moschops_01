# 16 Metric Definitions (Template)

System ID: TS-002
Last updated: YYYY-MM-DD

## Purpose
Define a single source of truth for metric formulas, units, and pass/fail interpretation.

## Trading Metrics
| Metric | Formula | Unit | Pass Direction | Notes |
|---|---|---|---|---|
| Net Return | (Ending equity - Starting equity) / Starting equity | % | Higher is better | Must be after costs |
| Expectancy per Trade | Mean(trade return) | % or R | Higher is better | Use consistent return basis |
| Profit Factor | Gross profit / Abs(gross loss) | Ratio | Higher is better | Undefined if no losses |
| Max Drawdown | Min((equity/running max)-1) | % | Lower magnitude is better | Report as negative percent |
| Recovery Time | Time to exceed prior equity peak after drawdown | Bars/days | Lower is better | Include median and max |
| Win Rate | Wins / Total trades | % | Contextual | Not primary alone |

## Stability Metrics
| Metric | Definition | Unit | Pass Direction | Notes |
|---|---|---|---|---|
| Fold Expectancy Median | Median expectancy across WF folds | % or R | Higher is better | Must be positive |
| Fold Expectancy Variance | Variance of fold expectancy | Value | Lower is better | Indicates robustness |
| Regime Dispersion | Std dev of regime returns | % | Lower is better | Avoid regime dependence |

## Diagnostic Metrics
| Metric | Definition | Unit | Pass Direction | Notes |
|---|---|---|---|---|
| AUC | ROC area under curve | 0-1 | Higher is better | Secondary only |
| Brier | Mean squared prob error | 0-1 | Lower is better | Calibration quality |
| Precision | TP/(TP+FP) | 0-1 | Contextual | Trade selectivity |
| Recall | TP/(TP+FN) | 0-1 | Contextual | Capture rate |

## Cost Model Assumptions
1. Spread model:
2. Slippage model:
3. Commission model:
4. Swap/financing model:
5. Reject/partial fill handling:

## Threshold Table
| Metric | Minimum | Target | Hard fail threshold |
|---|---:|---:|---:|
| Profit Factor |  |  |  |
| Max Drawdown % |  |  |  |
| Net Return % |  |  |  |
| Minimum trades |  |  |  |

## Change Control
- Any formula change requires a version increment and rationale.

