# 11 Experiment Log

System ID: TS-004
Version: 1.0
Last updated: 2026-05-28

## Experiment entries

| Date | Experiment ID | Hypothesis | Single change made | Result summary | Decision |
|---|---|---|---|---|---|
| — | EXP-001 | XGBoost baseline with default features and edge labels (8 bps, 10-bar) on EURUSD H4 will establish a measurable positive out-of-sample signal | Baseline XGBoost with default feature set, no regime gate, 5-fold CV, base cost model | Not yet run | Pending |
| — | EXP-002 | Adding vol_regime gate [0.80, 2.00] will reduce trade count but improve profit factor and fold consistency | Add volatility regime gate (block-all outside [0.80, 2.00]) | Not yet run | Pending |
| — | EXP-003 | P1 extended feature set (RSI, ADX, efficiency_ratio, MACD) will lift CV AUC vs. baseline | Add P1 extended features to EXP-002 config | Not yet run | Pending |
| — | EXP-004 | Constrained threshold optimisation (min 60 trades, max DD 20%) will produce a stable, low-curve-fit config | Apply constrained optimisation threshold selection to EXP-003 best features | Not yet run | Pending |
| — | EXP-005 | 2× spread / 3× slippage stress cost matrix will confirm the strategy survives adverse execution | Apply stress cost matrix to EXP-004 best config | Not yet run | Pending |
| — | HOLDOUT | EXP-004/EXP-005 best config will meet all Gate B and C thresholds on 2023–2024 holdout | Lock EXP-004/EXP-005 best config; execute single holdout run | Not yet run | Pending |

## Linked evidence

_No run artefacts yet. Links will be added as runs are completed._

## Integrity rules

1. No deletion of failed or invalid runs.
2. Mark any policy-violating run as `INVALID_FOR_PROMOTION`.
3. One change per experiment row. Do not bundle multiple changes.
4. Holdout row may only be added after dev experiments are complete and a single config is locked.
5. Keep trial counts explicit when testing multiple variants (e.g., EXP-003a, EXP-003b).

## Next planned experiments

1. EXP-001: Baseline XGBoost H4, edge labels, 5-fold CV, default features, no regime gate.
2. EXP-002: Add vol_regime gate [0.80, 2.00] — measure trade count and PF change.
3. EXP-003: Add P1 extended features (RSI, ADX, efficiency_ratio, MACD).
4. EXP-004: Constrained threshold optimisation (60 min trades, 20% max DD).
5. EXP-005: Stress cost matrix.
6. HOLDOUT: Final acceptance run (one time only).

## Future experiments (deferred)

| ID | Description | Deferred to |
|---|---|---|
| EXP-006 | Add HTF D1 trend confirmation (training/multiframe.py) | After holdout pass |
| EXP-007 | Add bocpd_cp_prob as event-detection feature | After holdout pass |
| EXP-008 | Add ichimoku cloud_bullish as secondary trend filter | After holdout pass |
| EXP-009 | Variable spread simulation using spread_sim.py | During paper phase |

## Stopping criteria

- **Retire TS-004**: If after EXP-005 the dev-window PF < 1.10 with max DD > 25%.
- **Retire early**: If 3+ consecutive experiments show degradation rather than improvement.
- **Proceed to holdout**: If dev-window config achieves PF ≥ 1.30, max DD ≤ 18%, ≥ 60 trades, ≥ 80% fold consistency.

## Command reference

```bash
# EXP-001 — baseline: XGBoost, edge labels, no regime gate, no trend filter
python training/run_historical_split.py \
  --symbol EURUSD --timeframe H4 \
  --train-start 2012-01-01 --train-end 2021-12-31 \
  --test-start  2022-01-01 --test-end  2022-12-31 \
  --label-mode edge --min-edge-bps 8 --horizon-bars 10 \
  --walk-forward-folds 5 --embargo-bars 5 \
  --spread-bps 2.5 --commission-bps 1.0 --slippage-bps 0.5 \
  --signal-variant baseline \
  --run-label exp-001
# → logs to logs/training/<date>/<time>_EURUSD_H4_exp-001/

# EXP-002 — add volatility regime gate [0.80, 2.00]
#   (add to EXP-001 command):
#   --enable-regime-gate --regime-min-volatility-regime 0.80 --regime-max-volatility-regime 2.00
#   --run-label exp-002

# EXP-003 — switch to trend-follow signal variant
#   (replace --signal-variant baseline with):
#   --signal-variant trend-follow --trend-min-strength 0.30
#   --run-label exp-003

# EXP-004 — constrained threshold optimisation (min 60 trades, max 20% drawdown)
#   (add to EXP-003 command):
#   --threshold-grid 0.52,0.55,0.58,0.60,0.63,0.65,0.68,0.70,0.73,0.75
#   --target-min-median-trades 60 --target-max-drawdown-pct -20.0
#   --run-label exp-004

# EXP-005 — stress cost matrix (2x spread + 3x slippage via multiplier)
#   Note: --stress-cost-multiplier applies uniformly to total cost.
#   Run EXP-004 config once with each stress multiplier below and report all three.
#   --stress-cost-multiplier 2.0   (2x spread scenario)    --run-label exp-005a
#   --stress-cost-multiplier 3.0   (3x slippage scenario)  --run-label exp-005b
#   --stress-cost-multiplier 4.0   (combined worst case)   --run-label exp-005c

# HOLDOUT — single locked run; do NOT run until EXP-001 through EXP-005 are complete
#   (replace test window with holdout window):
#   --test-start 2023-01-01 --test-end 2024-12-31
#   --run-label holdout
```
