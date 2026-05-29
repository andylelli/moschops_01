# 04 Feature Schema

System ID: TS-001
Version: 1.0
Last updated: 2026-05-27

## Feature registry
| Feature | Formula | Inputs | Window | Leakage risk | Runtime parity check |
|---|---|---|---|---|---|
| trend_strength | (SMA50 - SMA200) / close | close | 50, 200 | Low | Verify feature name and ordering |
| volatility20 | std(ret1) | close | 20 | Low | Compare statistical range with training artifact |
| atr14_norm | ATR14 / close | high, low, close | 14 | Low | Confirm non-null and finite values |
| breakout_distance | (close - prior HH55) / close | high, close | 55 | Low | Validate lagged HH55 usage |
| ret10 | pct_change(close, 10) | close | 10 | Low | Confirm lookback-only computation |

## Feature groups
1. Trend context: trend_strength.
2. Volatility normalization: volatility20 and atr14_norm.
3. Breakout context: breakout_distance.
4. Momentum context: ret10.

## Label schema
1. future_ret_h = close(t+h)/close(t) - 1.
2. label = 1 when future_ret_h > 0, else 0.
3. Horizon default in current run: 5 bars.

## Feature computation policy
1. Compute on UTC-ordered bars only.
2. Use shifted rolling windows where needed to avoid look-ahead.
3. Drop rows with null features or label fields.

## Schema lock policy
1. Feature names and order are part of model contract.
2. Training and inference schema mismatch invalidates the run for promotion.
3. Schema changes require version bump and documented rationale.

## Current implementation references
1. [../../../training/run_historical_split.py](../../../training/run_historical_split.py)
2. [../../../mql5/Experts/DailyBreakoutEA.mq5](../../../mql5/Experts/DailyBreakoutEA.mq5)
