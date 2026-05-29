# Dev Stack Error Capture - 2026-05-27

## Run Summary

Executed `scripts/start-dev-stack.bat` from the repository root.

Observed outcome:

- PostgreSQL host port `5432` was already in use.
- The launcher auto-selected host port `5435` and started the container successfully.
- Backend and dashboard windows were launched.
- `scripts/check-local-health.bat` returned `OK` for `GET /health`.
- Backend runtime logs show successful startup and ONNX model preflight.

## Error and Warning Inventory

### 1. Historical backend entrypoint error in `backend/stderr.log`

Observed message:

```text
Error: Cannot find module 'C:\moschops_01\backend\dist\index.js'
```

Where it came from:

- `backend/run_tests.ps1` starts Node with `dist/index.js`.
- `backend/verify_backend.ps1` also starts Node with `dist/index.js`.

Analysis:

- These helper scripts point at an outdated compiled entrypoint path.
- The backend package currently declares `node dist/src/index.js` as the start target in `backend/package.json`.
- The mismatch means the scripts can fail even when the backend build itself is correct.

Suggested fix:

- Update the helper scripts to launch `dist/src/index.js`.
- Prefer reusing `npm run start` so the scripts stay aligned with `backend/package.json`.
- If these scripts are still part of automation, add a quick preflight that checks the compiled output path before launching Node.

### 2. Port `5432` already in use during DB startup

Observed message:

```text
[start-db] WARNING: Port 5432 is already in use. Using 5435 for PostgreSQL instead.
```

Analysis:

- This is no longer a failure because the launcher now falls back to a free port.
- It is still useful operational visibility because it tells you the stack is not using the default port.

Suggested fix:

- No code fix required for startup reliability.
- If operators want a fixed port, stop the process occupying `5432` or set a preferred `POSTGRES_HOST_PORT`.

### 3. News sync disabled in runtime health

Observed state:

- `GET /health` reports `newsProvider.failureReason = NEWS_SYNC_DISABLED`.
- `backend/logs/news/2026-05-27.log` contains `news_sync_disabled` entries.

Analysis:

- This is configuration-driven, not a crash.
- The backend is healthy, but the news provider freshness telemetry stays `DOWN` while sync is disabled.

Suggested fix:

- If live news freshness is required, set `NEWS_SYNC_ENABLED=true` and provide a valid `FMP_API_KEY`.
- If offline operation is intended, keep it disabled and treat this as an expected degraded state.

## Log Directory Findings

- `backend/logs/error/` was empty during this run.
- `backend/logs/model/2026-05-27.log` shows successful model load and preflight.
- `backend/logs/startup/2026-05-27.log` shows clean startup events.
- `backend/logs/http/` was created for request/response capture.

## Bottom Line

The current dev stack launch is healthy.

The only concrete error artifact found was the stale `dist/index.js` reference in older backend helper scripts. That issue does not block the dev stack now, but it should be corrected so the helper scripts stay reliable.