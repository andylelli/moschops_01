# 07 Risk and Safety Specification

System ID: TS-002

## Risk budget policy
1. Risk per trade: discovery default 0.25% to 0.50% of equity.
2. Max open risk: 0.50% aggregate in discovery.
3. Max open trades: one open position per symbol.

## Exposure controls
1. One-position-per-symbol: mandatory.
2. Correlation/directional caps: no net directional stacking across highly correlated majors.
3. Session/event exposure caps: no new entries during configured high-impact news blackout windows.

## Guards
1. Spread guard: block entries when spread exceeds pair/timeframe cap.
2. Gap guard: block entries when current bar gap exceeds configured ATR fraction.
3. Slippage guard: reject fill intent when estimated slippage breaches tolerance.
4. Cooldown policy: enforce cooldown after stop-out cluster or risk kill event.

## Kill-switch policy
1. Trigger conditions: DD breach trajectory, repeated safety-guard violations, or infra degradation.
2. Auto-recovery conditions: all hard guards green for minimum stabilization window.
3. Manual override process: documented rationale, approver sign-off, and explicit expiry.

## Degraded mode behavior
1. Backend unavailable: no new entries, protective exits still permitted.
2. Model unavailable: no inference-dependent entries; fail closed.
3. DB unavailable: no promotion-eligible run may proceed without lineage persistence.

