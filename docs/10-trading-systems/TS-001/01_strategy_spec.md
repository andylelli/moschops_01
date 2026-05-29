# 01 Strategy Specification

System ID: TS-001
Version: 1.0
Last updated: 2026-05-27

## Strategy thesis
TS-001 assumes breakouts aligned with higher-timeframe trend have better follow-through than random entries, and AI can improve trade selection quality by suppressing weak setups.

## Entry logic
1. Long candidate: completed-bar close above trend filter and breakout high window.
2. Short candidate: completed-bar close below trend filter and breakout low window.
3. Only completed bars are valid for decisioning.

## Exit logic
1. Exit long when completed-bar close falls below fast SMA filter.
2. Exit short when completed-bar close rises above fast SMA filter.
3. Protective exits must remain available in degraded conditions.

## Stop logic
1. Initial stop uses ATR multiple from entry context.
2. Test mode supports fixed-stop override for integration and plumbing checks.

## Position sizing logic
1. Primary sizing is risk-based and depends on stop distance and symbol metadata.
2. Min-lot normalization and margin safety checks are mandatory.
3. If metadata or safety checks fail, no new trade is allowed.

## Parameter table
| Parameter | Type | Current default | Range | Effect |
|---|---|---|---|---|
| InpRiskPerTrade | number | 0.005 | >0 to policy cap | Risk budget per trade |
| InpBreakoutLookback | integer | 55 | >= 20 | Breakout sensitivity |
| InpAtrPeriod | integer | 20 | >= 5 | Stop distance behavior |
| InpFastSma | integer | 100 | >= 20 | Exit responsiveness |
| InpTrendSma | integer | 200 | >= 50 | Trend regime filter |
| InpMaxSpreadPips | integer | 50 | broker-dependent | Execution quality guard |
| InpMaxDailyLossPct | number | 0.02 | 0 to policy cap | Daily capital protection |

## Regime assumptions
1. Performs best in directional, persistent-trend conditions.
2. Performs worst in choppy, mean-reverting low-range environments.

## Known invalid market states
1. Abnormal spread and execution dislocation.
2. Missing symbol metadata or malformed market snapshot state.
