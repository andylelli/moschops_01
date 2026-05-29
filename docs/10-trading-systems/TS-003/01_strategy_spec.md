# 01 Strategy Specification

System ID: TS-003

## Strategy thesis
Momentum persistence across related instruments can be harvested by favoring stronger relative performers and avoiding weak/mean-reverting tails. H4 cadence balances signal stability with sufficient trade opportunities.

## Entry logic
1. Compute momentum and trend-strength features over H4 bars.
2. Enter long when momentum state is positive and passes volatility/spread quality gates.
3. Block entries in low-liquidity or high-friction windows.

## Exit logic
1. Exit on momentum decay below threshold.
2. Exit on risk stop or time stop.

## Stop logic
1. ATR-normalized protective stop.
2. Hard risk veto if post-entry volatility expands beyond tolerance.

## Position sizing logic
1. Fixed discovery risk-per-trade with volatility adjustment.
2. Instrument eligibility score can reduce exposure, never increase beyond hard cap.

## Parameter table
| Parameter | Type | Default | Range | Effect |
|---|---|---|---|---|
| momentumLookbackBars | int | 30 | 12-80 | Defines momentum horizon on H4 |
| trendFilterBars | int | 120 | 40-240 | Directional regime filter |
| entryThreshold | float | 0.55 | 0.45-0.75 | Selectivity of long entry |
| stopAtr | float | 1.2 | 0.8-2.0 | Protective stop distance |
| maxHoldBars | int | 36 | 12-96 | Time-based exit |

## Regime assumptions
1. Performs best when medium-term trends persist with manageable volatility.
2. Performs worst when frequent trend reversals and gap-driven noise dominate.

## Known invalid market states
1. Severe event-driven discontinuities with unreliable execution quality.
2. Structural spread blowouts where costs consume edge.

