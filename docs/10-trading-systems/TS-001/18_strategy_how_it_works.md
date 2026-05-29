# 18 Strategy How It Works

System ID: TS-001
Audience: Operator and reviewer

## What TS-001 is trying to do
TS-001 is a trend-following breakout system on D1. It tries to enter only when price breaks out in the same direction as the long-term trend, then exits when that trend-follow condition weakens or risk controls require an exit.

## Exact decision flow per completed bar
1. Wait for a completed bar (no intra-bar decisions).
2. Build the market snapshot and symbol metadata.
3. If metadata is missing or invalid, reject new entry.
4. Check execution guards (spread, trade mode, margin, lot constraints).
5. Check portfolio/risk state (daily loss guard, open-risk/open-trade policy).
6. If all guards pass, evaluate strategy entry rules.
7. If entry qualifies, compute ATR-based stop and risk-based size.
8. Submit through EA/backend decision path.
9. If order submit fails or backend is unavailable, no new entry is allowed.

## Entry rules
1. Long candidate: close breaks above breakout window and is aligned with trend filter.
2. Short candidate: close breaks below breakout window and is aligned with trend filter.
3. All entry checks are evaluated only on completed bars.

## Exit rules
1. Long exit: close falls below fast SMA exit filter.
2. Short exit: close rises above fast SMA exit filter.
3. Protective exits remain enabled even in degraded mode.

## Risk and sizing rules
1. Primary risk per trade default is 0.5% of equity.
2. Daily loss guard default is 2.0% and blocks new entries when breached.
3. Sizing is stop-distance based and normalized to broker min/max/step.
4. One-position-per-symbol behavior is required.

## Hard fail-closed conditions
1. Backend unavailable or invalid response.
2. Symbol trade mode disabled/close-only.
3. Margin check failure.
4. Missing or inconsistent symbol metadata.
5. Active kill-switch condition.

## What TS-001 does not do
1. It does not use incomplete candles for entry confirmation.
2. It does not bypass safety checks to force live entries.
3. It does not allow promotion evidence from test-only timeframe shortcuts.

## Source references
1. 01_strategy_spec.md
2. 02_instruments_execution.md
3. 07_risk_safety.md
