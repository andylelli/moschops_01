# 07 Risk and Safety Specification

System ID: TS-003

## Risk budget policy
1. Risk per trade: 0.25% to 0.50% during discovery.
2. Max open risk: 0.75% aggregate.
3. Max open trades: one position per symbol.

## Exposure controls
1. One-position-per-symbol: mandatory.
2. Correlation/directional caps: enforce directional cap across correlated assets.
3. Session/event exposure caps: no new entries during configured event blackout windows.

## Guards
1. Spread guard: block entries when spread exceeds H4 threshold per instrument.
2. Gap guard: block entries on abnormal bar-to-bar discontinuities.
3. Slippage guard: reject entry when expected slippage exceeds tolerance.
4. Cooldown policy: pause entries after consecutive loss events.

## Kill-switch policy
1. Trigger conditions: drawdown breach trajectory, repeated guard failures, infra degradation.
2. Auto-recovery conditions: guards and infra green for defined stabilization period.
3. Manual override process: documented rationale, approver sign-off, expiry required.

## Degraded mode behavior
1. Backend unavailable: fail closed for new entries.
2. Model unavailable: block model-dependent entries.
3. DB unavailable: run invalid for promotion due to missing lineage.

