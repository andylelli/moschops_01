# Logging and Observability Guide

Version: 1.0
Last updated: 2026-05-27

## Purpose
Define the local filesystem logging layout and the categories that should be available for fast operator diagnosis.

## Logging Model

- Fastify request and response lifecycle events are written to file logs under `backend/logs/http/`.
- Backend startup, shutdown, and bootstrap events are written under `backend/logs/startup/`.
- Runtime failures are written under `backend/logs/error/`.
- Model loading, preflight, and inference events are written under `backend/logs/model/`.
- News synchronization events are written under `backend/logs/news/`.
- Training runtime events are written under `backend/logs/training/`.
- Audit persistence writes are mirrored under `backend/logs/audit/`.
- Administrative and access-sensitive actions are mirrored under `backend/logs/security/`.
- Database bootstrap and persistence warnings are written under `backend/logs/db/`.

## Directory Layout

Recommended structure:

```text
backend/logs/
  app/
  audit/
  db/
  error/
  http/
  model/
  news/
  security/
  startup/
  system/
  training/
```

Each category writes one UTC-dated JSONL file per day, for example `2026-05-27.log`.

## Operational Rules

- Do not store secrets, tokens, cookies, or authorization headers in file logs.
- Prefer correlation identifiers such as `requestId`, `decisionId`, `incidentId`, `tradeId`, `trainingRunId`, and `modelVersion`.
- Preserve structured JSON lines so logs remain searchable and easy to ingest later.
- Keep database-backed audit records as the canonical source of truth; file logs are an operational mirror.
- Use the `error/` category for unrecoverable failures and the `startup/` category for boot/shutdown flow visibility.

## Operator Usage

1. Check `backend/logs/error/` first when a service fails to start.
2. Check `backend/logs/http/` for request/response flow and status codes.
3. Check `backend/logs/model/` for ONNX load, preflight, and inference failures.
4. Check `backend/logs/news/` for provider sync state and budget gating.
5. Check `backend/logs/training/` for runtime selection, Python discovery, and subprocess failures.
6. Check `backend/logs/audit/` and `backend/logs/security/` for operator-impacting actions.
