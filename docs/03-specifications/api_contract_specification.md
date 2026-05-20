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
- strategyVersion
- symbol
- timeframe
- barCloseTimeUtc
- marketSnapshot
- accountSnapshot
- optional feature payload

Signal feature requirements:
- `marketSnapshot.volatility` is required and must represent rolling return volatility from completed bars.
- Runtime feature vector must match training schema exactly:
  - `trend_strength`
  - `volatility`
  - `spread_atr`
  - `breakout_distance`
  - `momentum`

Response fields:
- decisionId
- signalId
- action
- riskDecision
- reasonCodes
- evaluatedAtUtc

AI reason code behavior:
- `AI_SCORE_APPLIED` when score thresholds were applied.
- `AI_HALF_SIZE` and `AI_SKIP` for score-band decisions.
- `AI_MODEL_UNAVAILABLE` when model is unavailable/degraded.
- `AI_INFERENCE_ERROR` when runtime inference fails.
- `AI_INVALID_FEATURES` when feature payload is invalid.

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

### POST /portfolio/evaluate
Request fields:
- accountSnapshot
- plans[]
- maxOpenRisk
- maxOpenTrades
- optional `portfolioDecisionId`

Response fields:
- portfolioDecisionId
- approvedPlans
- rejectedPlans
- remainingRiskBudget
- remainingTradeSlots
- evaluatedAtUtc

Persistence and idempotency semantics:
- Evaluation results are persisted atomically (decision + decision items).
- Replays with matching request payload return the existing `portfolioDecisionId` and cached result.
- If `portfolioDecisionId` is supplied and already exists, cached result is returned.

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

Health telemetry requirements:
- `telemetry.modelLoader` returns `available` or `degraded`.
- `telemetry.modelReason` provides degradation reason when applicable.

## Idempotency
- decisionKey = strategyId + symbol + timeframe + barCloseTimeUtc
- Replays with the same decisionId must not create duplicate business records.
- Portfolio evaluations are idempotent by explicit `portfolioDecisionId` or stable request hash.

## Status Codes
- 200: successful read or accepted write
- 400: invalid request payload
- 401: unauthorized
- 409: duplicate or conflicting decision key
- 422: semantically invalid request
- 500: unexpected server failure

### Risk Decision Flow

The `/signal` endpoint includes preliminary risk checks for immediate vetoes (e.g., capital limits, kill-switch triggers). The `/risk-check` endpoint provides a secondary, detailed evaluation for proposed trades.

#### Flow Order:
1. `/signal` evaluates:
   - Strategy-level constraints.
   - Immediate veto conditions.
2. `/risk-check` evaluates:
   - Account-level exposure.
   - Adjusted trade sizes.

Both endpoints must log their decisions for auditability.
