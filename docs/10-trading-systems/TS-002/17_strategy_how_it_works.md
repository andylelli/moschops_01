# 17 Strategy How It Works

System ID: TS-002
Audience: Operator and reviewer

## What TS-002 is trying to do
TS-002 is an H1 mean-reversion design. It looks for short-term overextension (volatility expansion) and enters only when that expansion shows signs of compression, aiming for partial reversion back toward a mid-band state.

## Exact decision flow per evaluation cycle
1. Read H1 features for expansion/compression context.
2. Compute overextension score (normalized ATR and return z-score context).
3. Check whether compression confirmation appears within allowed lookahead bars.
4. Apply execution and risk guards before allowing any entry.
5. If guards pass and setup is valid, size position using discovery risk budget and volatility scaling.
6. Submit entry; if submission path is degraded, fail closed for new entries.

## Entry rules
1. Long setup: downside overextension exceeds threshold, then compression confirmation arrives in configured window.
2. Short setup: upside overextension exceeds threshold, then compression confirmation arrives in configured window.
3. Entry is rejected if spread/slippage/cooldown or event blackout guards are violated.

## Exit rules
1. Target exit: price reverts toward configured mean-reversion target.
2. Time-stop exit: trade is closed when reversion does not progress within max hold bars.
3. Abort exit: close early when volatility re-expands against the position.

## Risk and sizing rules
1. Discovery risk per trade is low (0.25% to 0.50%).
2. Aggregate open risk is constrained during discovery.
3. No pyramiding during discovery.
4. One open position per symbol is mandatory.

## Hard fail-closed conditions
1. Backend unavailable.
2. Model unavailable for inference-dependent entries.
3. DB unavailable for promotion-eligible run lineage.
4. Spread/gap/slippage guard breaches.
5. Active kill-switch state.

## Current documentation boundary
1. TS-002 execution profile document is still partly templated.
2. This description reflects the currently approved logic in 01_strategy_spec and 07_risk_safety.

## Source references
1. 01_strategy_spec.md
2. 02_instruments_execution.md
3. 07_risk_safety.md
