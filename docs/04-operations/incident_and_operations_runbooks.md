# Incident and Operations Runbooks

Version: 1.0  
Last updated: 2026-05-20

## Purpose
Define the first-response playbooks for backend, database, model, and kill-switch incidents.

## Required Runbooks
### Backend unavailable
- Confirm EA degraded mode.
- Block new entries.
- Preserve protective exits.
- Restore backend service and verify health.

### Database unavailable
- Stop new persistence writes.
- Switch to fail-closed trade handling.
- Recover the database and revalidate write paths.

### Model-serving unavailable
- If AI is optional, fall back to rule-only behavior.
- If AI is mandatory, pause strategy execution.
- Revalidate the active model endpoint before resuming.

### Kill-switch activation
- Record trigger source and reason code.
- Confirm no new entries are allowed.
- Verify operator acknowledgement before reset.

### News provider stale or down (FMP)
- Confirm provider freshness state from `/health` and `/news/providers`.
- Enforce fail-closed behavior for impacted new entries (`NEWS_PROVIDER_STALE`).
- Preserve protective exits.
- Verify configured tier for running version (`FREE` in `v1.x`, `BASIC` in `v2+`).
- Record outage window and remediation actions.

## Required Fields in Every Incident Log
- incidentId
- start time
- detection source
- root cause summary
- actions taken
- recovery time
- follow-up tasks
