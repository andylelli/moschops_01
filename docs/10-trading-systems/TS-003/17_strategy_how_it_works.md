# 17 Strategy How It Works

System ID: TS-003
Audience: Operator and reviewer

## What TS-003 is trying to do
TS-003 is an H4 momentum system. It prefers instruments/states with persistent momentum and trend strength, while blocking low-quality conditions where spread, volatility regime, or execution friction are likely to destroy edge.

## Exact decision flow per evaluation cycle
1. Read H4 feature set (momentum, trend strength, volatility regime, breakout distance, returns).
2. Score setup quality from trained model probability output.
3. Apply configured signal variant logic (baseline, trend-follow, or regime-split).
4. Apply regime gate and execution/risk guards.
5. If all checks pass, open position with ATR-normalized stop and discovery risk sizing.
6. If any hard guard fails, reject new entry and keep protective behavior active.

## Entry rules
1. Core requirement: positive momentum state with quality threshold pass.
2. Variant-specific filtering may require stronger trend confirmation or regime split behavior.
3. Entry is blocked in low-liquidity/high-friction windows and guard-failure states.

## Exit rules
1. Momentum decay exit when signal quality drops below threshold.
2. Protective stop exit (ATR-normalized).
3. Time-stop exit at max holding horizon.
4. Additional risk veto if post-entry volatility expands beyond tolerance.

## Risk and sizing rules
1. Discovery risk per trade is constrained (0.25% to 0.50%).
2. Aggregate open risk cap applies.
3. One position per symbol is mandatory.
4. Correlation and event blackout caps can block new entries.

## Hard fail-closed conditions
1. Backend unavailable.
2. Model unavailable for model-dependent entries.
3. DB unavailable for promotion-grade lineage.
4. Spread/gap/slippage guard breaches.
5. Active kill-switch state.

## Current validation reality
1. Current TS-003 experiments remain blocked for promotion under hard constraints.
2. This description defines operating logic, not proof of promotion readiness.

## Source references
1. 01_strategy_spec.md
2. 02_instruments_execution.md
3. 07_risk_safety.md
