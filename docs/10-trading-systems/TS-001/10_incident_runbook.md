# 10 Incident Runbook

System ID: TS-001
Version: 1.0
Last updated: 2026-05-27

## Incident classes
1. Execution failure or repeated order rejection.
2. Backend connectivity failure from EA.
3. Data freshness or historical data integrity failure.
4. Model artifact or inference mismatch.
5. Risk-control malfunction.

## Severity matrix
| Severity | Description | Response target | Escalation |
|---|---|---|---|
| Sev1 | Capital protection or safety-critical failure | Immediate | Tech lead + operator |
| Sev2 | Material degradation with elevated risk | < 1 hour | Engineering owner |
| Sev3 | Non-critical defect with workaround | < 1 business day | Backlog triage |

## Triage flow
1. Confirm blast radius and affected symbols/sessions.
2. Freeze new entries if safety impact exists.
3. Capture decisionId, signalId, tradeId, and relevant logs.
4. Apply mitigation and verify recovery.
5. Record remediation task and owner.

## Standard mitigations
1. Backend unreachable: block entries, keep protective exits, restore connectivity.
2. Spread anomaly: maintain spread guard block until normalization.
3. Model mismatch: disable AI-gated path and revert to approved safe mode per policy.
4. Risk control anomaly: activate kill-switch and investigate before restart.

## Post-incident review
1. Root cause.
2. Detection gap.
3. Preventive control change.
4. Documentation updates required.
5. Owner and due date.
