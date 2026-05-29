# Outstanding Tasks for Dev Against a Demo MT5 Account

Date: 2026-05-27

## Scope

This document captures the remaining work to run the platform in development against a demo MT5 account. It focuses on the end-to-end path:

- MT5 demo terminal
- EA deployment and compile/attach
- Backend and dashboard connectivity
- News/risk gating
- Model/runtime readiness
- Demonstrable EA-backend roundtrip evidence

## Current State

Already in place:

- Backend dev stack starts locally and can auto-select a free PostgreSQL host port if 5432 is busy.
- Dashboard builds successfully after Plotly bundle splitting.
- Backend health endpoint is live and reports model/news telemetry.
- EA source exists in [mql5/Experts/DailyBreakoutEA.mq5](../../mql5/Experts/DailyBreakoutEA.mq5).
- EA deployment helper exists in [scripts/deploy-ea-to-mt5.bat](../../scripts/deploy-ea-to-mt5.bat).
- Backend exposes `/signal`, `/risk-check`, `/portfolio/evaluate`, `/trades/open`, `/health`, and supporting persistence routes.

Important limitation:

- The system does not yet have a fully automated AI-to-EA live trade request workflow. The current AI path scores signals and the EA still executes from its own deterministic logic.

## Outstanding Tasks

### 1. Confirm the exact demo MT5 terminal data path

What remains:

- Identify the target MT5 demo terminal instance path under the Windows `MetaQuotes\Terminal\<INSTANCE_ID>` directory.
- Verify the terminal is logged into the intended demo account.
- Confirm the terminal is the one that will be used for the development/test cycle.

Why it matters:

- The EA deployment script needs the correct MT5 data path.
- Wrong terminal selection causes the EA to compile/attach against the wrong account.

Suggested completion evidence:

- Screenshot or note of the MT5 terminal path and demo account login.

### 2. Deploy and compile the EA in MetaEditor

What remains:

- Copy [mql5/Experts/DailyBreakoutEA.mq5](../../mql5/Experts/DailyBreakoutEA.mq5) into the MT5 data directory with [scripts/deploy-ea-to-mt5.bat](../../scripts/deploy-ea-to-mt5.bat).
- Open MetaEditor and compile the EA without errors.
- Attach the EA to the intended chart/timeframe.

Why it matters:

- The platform cannot operate against a demo account until the EA is compiled and attached.

Suggested completion evidence:

- Compile log and successful attach confirmation.

### 3. Enable MT5 WebRequest access to the backend

What remains:

- Add the backend base URL to MT5 WebRequest allowed list.
- Confirm the EA can reach `http://127.0.0.1:3000` or the selected backend host.
- Verify both signal and open-trade snapshot endpoints are reachable.

Why it matters:

- Without WebRequest permission, the EA cannot talk to the backend.

Suggested completion evidence:

- MT5 Journal entry showing allowed WebRequest and successful backend requests.

### 4. Align backend environment for demo operation

What remains:

- Confirm `backend/.env` values are appropriate for the demo run.
- Keep `NEWS_SYNC_ENABLED=true` if the demo needs live news control.
- Ensure `NEWS_PROVIDER_TIER` matches the intended entitlement (`FREE` for v1.x demo behavior, `BASIC` for v2+ behavior).
- Confirm `DATABASE_URL` points to the local/target PostgreSQL instance used by the demo run.
- Confirm `FMP_API_KEY` is present and valid if news sync is expected.

Why it matters:

- Demo runs need stable telemetry and deterministic news gating.
- Misconfigured news settings can cause stale-provider vetoes or disabled freshness indicators.

Suggested completion evidence:

- `/health` showing the expected news freshness state and database state.

### 5. Validate EA-backend decision roundtrip

What remains:

- Prove the EA can send a decision/request to the backend and receive a deterministic response.
- Confirm the backend persists signal/rejected-signal records with decision IDs, model version, and reason codes.
- Confirm the backend and EA logs agree on the same request IDs.

Why it matters:

- This is the core integration proof that the dev environment can support demo trading safely.

Suggested completion evidence:

- Paired MT5 Journal logs, backend request logs, and persisted DB rows.

### 6. Validate trade and open-trade snapshot posting

What remains:

- Exercise the EA open-trade snapshot path.
- Confirm backend `/trades/open` receives and stores the snapshot.
- Verify dashboard/operations views can reflect the snapshot data.

Why it matters:

- Demo oversight depends on the backend seeing EA-side state in near real time.

Suggested completion evidence:

- Backend `trades/open` rows linked to the EA action that created them.

### 7. Decide whether the demo needs AI-created trade requests or only AI scoring

What remains:

- Confirm the intended demo operating model.
- If the goal is autonomous AI-originated requests, add the missing request-generation workflow.
- If the goal is risk-gated deterministic execution with AI scoring support, keep the EA as the execution authority and use the model only for scoring/size gating.

Why it matters:

- The current system can score signals and execute locally, but it does not yet produce a dedicated live trade-request ticket for the EA to consume.

Suggested completion evidence:

- Architecture decision recorded in the runbook or demo dossier.

### 8. Validate demo safety gates and degraded-state messaging

What remains:

- Confirm the dashboard clearly shows news freshness, risk vetoes, and kill-switch state.
- Confirm `NEWS_PROVIDER_STALE` vetoes are understood and expected when news is stale.
- Confirm the EA respects local safety checks for spread, margin, and daily loss.

Why it matters:

- Demo runs must fail closed and remain operator-readable.

Suggested completion evidence:

- UI screenshots or operator notes showing degraded and warning states.

### 9. Collect demo evidence package

What remains:

- Capture startup logs.
- Capture MT5 compile/attach evidence.
- Capture roundtrip logs and `/health` output.
- Capture a short controlled demo run showing the full path.
- Store the evidence in the temp docs folder until it is promoted into the formal runbook or demo gate dossier.

Why it matters:

- The rollout phases and demo gate require proof, not just working code.

Suggested completion evidence:

- A single demo evidence bundle with links to logs, screenshots, and API payloads.

## Recommended Order

1. Confirm the correct MT5 demo terminal path and account.
2. Deploy, compile, and attach the EA.
3. Allow backend WebRequest access from MT5.
4. Verify backend `.env` is set for demo news operation.
5. Run the EA-backend roundtrip and open-trade snapshot checks.
6. Decide whether a trade-request generation workflow is required beyond current AI scoring.
7. Capture demo evidence and update the formal runbook/gate docs.

## Practical Status Summary

- Backend/runtime: mostly ready.
- Dashboard/runtime: mostly ready.
- MT5/EA integration: still needs compile, attach, WebRequest permission, and roundtrip proof.
- AI: trained model exists for scoring, but not yet a live trade-request generator.
- Demo-readiness: blocked on MT5 demo wiring and evidence capture.
