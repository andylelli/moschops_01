# 09 Live Operations Profile

System ID: TS-001
Version: 1.0
Last updated: 2026-05-27

## Deployment ladder
1. Research: backtests and validation-only, no live capital.
2. Paper: real-time signal generation with simulated execution costs.
3. Micro-live: strict capital cap and daily oversight.
4. Controlled scale: pre-defined scale steps with revalidation at each step.

## Monitoring objectives
1. System health: backend, database, model availability.
2. Risk posture: daily loss, open-risk, open trades, kill-switch state.
3. Data freshness: historical/news provider status as required by policy.
4. Decision quality: trade outcomes and drift indicators.

## Daily operator checklist
1. Confirm health endpoint status and telemetry state.
2. Verify kill-switch and risk limits configuration.
3. Check unresolved incidents and audit-log continuity.
4. Review spread and execution anomalies from previous session.

## Weekly operator checklist
1. Review strategy performance vs expected envelope.
2. Review drift, calibration, and regime-behavior diagnostics.
3. Confirm no missing artifacts in experiment and run logs.
4. Revalidate gate status and unresolved blockers.

## Rollback triggers
1. Drawdown breach beyond configured hard limit.
2. Missing critical logging or broken lineage.
3. Repeated operational failures in signal or execution path.
4. Verified model behavior drift outside accepted band.

## References
1. [08_promotion_gates.md](08_promotion_gates.md)
2. [10_incident_runbook.md](10_incident_runbook.md)
3. [../../04-operations/incident_and_operations_runbooks.md](../../04-operations/incident_and_operations_runbooks.md)
