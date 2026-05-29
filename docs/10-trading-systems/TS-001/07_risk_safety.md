# 07 Risk and Safety Specification

System ID: TS-001
Version: 1.0
Last updated: 2026-05-27

## Risk budget policy
1. Baseline risk per trade configured at 0.5%.
2. Daily loss guard configured at 2.0% in EA inputs.
3. Open-risk and open-trade limits are enforced through backend policy path.

## Exposure controls
1. One-position-per-symbol behavior required.
2. Risk engine veto path blocks unsafe entries.
3. Trade blocked when symbol trade mode is disabled or close-only.

## Execution guards
1. Spread guard using pip-aware conversion.
2. Margin checks prior to order placement.
3. Lot-step, min-lot, and max-lot normalization.
4. Test-mode force-trade is restricted to test workflows only.

## Kill-switch policy
1. Trigger on hard risk-limit breaches or operator command.
2. New entries blocked when kill-switch active.
3. Protective exits must remain permitted.

## Degraded mode behavior
1. Backend unavailable: block new entries, log failure.
2. Invalid response: treat as non-tradable state.
3. Data integrity failure: block promotion and require remediation.

## Missing metadata behavior
1. Missing or inconsistent metadata must fail closed for new entries.
2. Reject event should be captured for operator audit.

## Required evidence
1. Safety precondition checks present in EA flow.
2. Risk gate decision recorded in run and system logs.
3. Incident runbook prepared before live promotion.

## References
1. [../../../mql5/Experts/DailyBreakoutEA.mq5](../../../mql5/Experts/DailyBreakoutEA.mq5)
2. [../../04-operations/incident_and_operations_runbooks.md](../../04-operations/incident_and_operations_runbooks.md)
