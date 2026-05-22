# Verification Summary - 2026-05-21

## Commands Run

- `cd backend && npm run build`
- `cd backend && npm run verify:provider`
- `cd backend && npm run verify:api`
- `cd backend && npm run verify:idempotency`
- `cd backend && npm run verify:lineage`
- `cd backend && npm run verify:freshness`
- `cd backend && npm run verify:parity`
- `cd backend && npm run prisma:generate`
- `cd backend && npm run prisma:deploy`
- Disabled-mode probe with `NEWS_SYNC_ENABLED=false` for `GET /health` and `GET /news/providers`

## Build Result

- `npm run build`: pass

## Prisma Migration Result

Evidence source: `docs/07-temp/evidence/prisma_migration_check_2026-05-21.txt`

- `npm run prisma:generate`: pass
- `npm run prisma:deploy`: pass
- migration state: no pending migrations

## Provider Probe Result

Evidence source: `docs/07-temp/evidence/provider_probe_2026-05-21.txt`

- stable current day header: `200`, `ok=true`, `count:126`
- stable historical header: `402`, `ok=false`
- stable historical query fallback: `402`, `ok=false`
- v3 current day query: `403`, `ok=false`
- v3 historical query: `403`, `ok=false`

## API Matrix Result

Evidence source: `docs/07-temp/evidence/api_test_report_2026-05-21.json`

- backend endpoints: `14` pass, `0` fail
- `GET /model-version` now returns `200` after model metadata bootstrap seed
- provider probes (from API report): `1` pass, `4` fail (`402` and `403` outcomes)

## Model Metadata Resolution Check

Evidence source: `docs/07-temp/evidence/model_version_probe_2026-05-21.json`

- `GET /model-version` returns:
	- `strategyId = daily-breakout-5-10`
	- `strategyVersion = 1.0.0`
	- `modelVersion = logreg-2026-05-20`
	- `lifecycleState = ACTIVE`

## Idempotency Replay Result

Evidence source: `docs/07-temp/evidence/idempotency_test_report_2026-05-21.json`

- pass count: `4`
- fail count: `0`
- validated replay-stable behavior for:
	- duplicate `POST /signal`
	- duplicate `POST /portfolio/evaluate`

## Lineage Chain Result

Evidence source: `docs/07-temp/evidence/lineage_test_report_2026-05-21.json`

- pass count: `3`
- fail count: `0`
- SQL join proof links signal to trade with traceability fields:
	- `decisionId`
	- `signalId`
	- `strategyId`
	- `strategyVersion`
	- `modelVersion`
	- `tradeId`

## Freshness Transition Result

Evidence source: `docs/07-temp/evidence/freshness_transition_report_2026-05-21.json`

- pass count: `4`
- fail count: `0`
- validated transition states across both `/health` and `/news/providers`:
	- `FRESH`
	- `DEGRADED`
	- `STALE`
	- `DOWN`

## News/Risk Parity Result

Evidence source: `docs/07-temp/evidence/parity_test_report_2026-05-21.json`

- pass count: `4`
- fail count: `0`
- confirmed policy parity for `NEWS_PROVIDER_STALE` across:
	- `POST /signal`
	- `POST /risk-check`
	- `POST /portfolio/evaluate`

## Disabled-Mode Contract Check

Evidence source: `docs/07-temp/evidence/news_disabled_probe_2026-05-21.txt`

- `GET /health` telemetry shows `newsProvider.failureReason = NEWS_SYNC_DISABLED`
- `GET /news/providers` item shows `failureReason = NEWS_SYNC_DISABLED` and `freshnessState = DOWN`
