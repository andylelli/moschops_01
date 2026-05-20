# API Contract Specification

Version: 1.0  
Last updated: 2026-05-20

## Purpose
Define the backend HTTP contract used by the EA, backend services, and dashboard.

## Common Rules
- All endpoints use JSON request and response bodies unless noted otherwise.
- Correlation fields are immutable for a given decision request.
- Endpoints must fail closed on invalid payloads.

## Common Error Format
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Human-readable summary",
    "details": "Optional technical detail",
    "requestId": "uuid"
  }
}
```

## Endpoints
### POST /signal
Request fields:
- decisionId
- strategyId
- symbol
- timeframe
- barCloseTimeUtc
- marketSnapshot
- accountSnapshot
- optional feature payload

Response fields:
- decisionId
- signalId
- action
- riskDecision
- reasonCodes
- evaluatedAtUtc

### POST /risk-check
Request fields:
- decisionId
- strategyId
- symbol
- proposed size and stop details
- account and exposure snapshot

Response fields:
- approved
- vetoReasonCodes
- adjustedSize
- evaluatedAtUtc

### POST /log-signal
Persists accepted or rejected signal records.

### POST /log-rejected-signal
Persists rejected signal records with structured reason codes.

### POST /log-trade
Persists trade lifecycle and execution quality data.

### POST /trades/open
Persists the EA open-trade snapshot.

### GET /trades/open
Returns the current open-trade snapshot for dashboard use.

### GET /model-version
Returns the active model metadata for a strategy/environment.

### GET /performance
Returns performance snapshots, risk events, and summary metrics.

### GET /health
Returns backend dependency status.

## Idempotency
- decisionKey = strategyId + symbol + timeframe + barCloseTimeUtc
- Replays with the same decisionId must not create duplicate business records.

## Status Codes
- 200: successful read or accepted write
- 400: invalid request payload
- 401: unauthorized
- 409: duplicate or conflicting decision key
- 422: semantically invalid request
- 500: unexpected server failure
