# API Contract Specification

Version: 1.0  
Last updated: 2026-05-23

## Purpose
Define the backend HTTP contract used by the EA, backend services, and dashboard.

News provider baseline:
- Selected provider: Financial Modeling Prep (FMP).
- Pricing reference: https://site.financialmodelingprep.com/developer/docs/pricing
- `v1.x` tier: `FREE`.
- `v2+` tier: `BASIC`.
- Backend owns news state and provider integration (EA does not supply provider payloads).

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
- `AI_MANDATORY_BLOCK` when strategy profile requires AI and no valid score is available.

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

### GET /score-distribution
Returns score histogram bins derived from persisted model predictions for AI monitoring.

Query fields:
- strategyId (optional)
- bins (default 10, range 5-20)
- lookback (default 1000, range 50-5000)

Response fields:
- count
- bins[]: `label`, `lower`, `upper`, `count`

### GET /health
Returns backend dependency status.

Health telemetry requirements:
- `telemetry.modelLoader` returns `available` or `degraded`.
- `telemetry.modelReason` provides degradation reason when applicable.
- `telemetry.newsProvider` returns `FMP` when news integration is enabled.
- `telemetry.newsProviderTier` returns `FREE` for `v1.x` and `BASIC` for `v2+`.
- `telemetry.newsFreshness` returns `FRESH|DEGRADED|STALE|DOWN`.

### GET /news/upcoming
Returns upcoming normalized calendar events from FMP-backed ingestion.

### GET /news/active
Returns currently active guard windows derived from normalized FMP events.

### GET /news/providers
Returns provider status and freshness, including provider name (`FMP`) and active tier.

### POST /historical-data/download
Triggers provider-backed historical bar download and persists bars in PostgreSQL.

Request fields:
- source (`FMP`)
- symbol (for example `EURUSD`)
- timeframe (`M15|H1|H4|D1`)
- fromDate (`YYYY-MM-DD`)
- toDate (`YYYY-MM-DD`)
- replaceExisting (boolean)
- requestedBy (optional operator identifier)

Response fields:
- job.id
- job.status (`COMPLETED|FAILED`)
- job.symbol
- job.timeframe
- job.fromDate
- job.toDate
- job.barsFetched
- job.barsInserted
- job.barsSkipped
- job.requestedAtUtc
- job.completedAtUtc

### GET /historical-data/jobs
Returns recent historical download jobs for UI status/audit visibility.

Query fields:
- limit (default 50, max 200)

### GET /historical-data/bars
Returns persisted bars from PostgreSQL for a selected symbol/timeframe/date range.

Query fields:
- source (`FMP`)
- symbol
- timeframe (`M15|H1|H4|D1`)
- fromDate (optional)
- toDate (optional)
- limit (default 500, max 2000)

### GET /strategy-config/current
Returns the active strategy runtime and training-default configuration profile for a strategy/version.

Query fields:
- strategyId (default `daily-breakout-5-10`)
- strategyVersion (default `1.0.0`)

Response fields:
- strategyId
- strategyVersion
- riskProfile
- source (`default|database`)
- createdAt
- config.aiThresholds (`full`, `half`)
- config.aiMandatory
- config.trainingDefaults (dataset profile, horizon, CV, calibration, threshold, feature toggles)

### PUT /strategy-config/current
Persists a new strategy runtime configuration snapshot.

Request fields:
- strategyId
- strategyVersion
- riskProfile
- config.aiThresholds (`full`, `half`, with `half < full`)
- config.aiMandatory
- config.trainingDefaults (dataset profile, horizon, CV, calibration, threshold, feature toggles)

Response fields:
- same as `GET /strategy-config/current`

### POST /strategy-config/reset
Persists a fresh default strategy configuration snapshot for the specified strategy/version.

Request fields:
- strategyId (optional; defaults to `daily-breakout-5-10`)
- strategyVersion (optional; defaults to `1.0.0`)

Response fields:
- ok
- profile (same shape as `GET /strategy-config/current`)

### GET /training/runtime/health
Returns Python runtime preflight status used by Training Studio before launch.

Response fields:
- runtime.ok
- runtime.configuredExecutable
- runtime.command
- runtime.executable
- runtime.pythonVersion
- runtime.moduleStatus (required Python package import checks)
- runtime.missingPackages
- runtime.errors

### GET /training/runs
Returns recent persisted training sessions for timeline and achieved-metrics views.

Query fields:
- limit (default 20, max 100)

Response fields:
- count
- items[]: `trainingRunId`, `strategyId`, `modelVersion`, `datasetVersion`, `status`, `metricsJson`, `createdAt`

Training metrics payload (`metricsJson`) includes:
- `outcome`: `aucMean`, `aucMin`, `brierMean`, `brierMax`, `calibrationDrift`
- `diagnostics.confusionMatrix`: `labels`, `matrix`, `threshold`
- `diagnostics.rocCurve[]`: `threshold`, `fpr`, `tpr`
- `diagnostics.prCurve[]`: `threshold`, `recall`, `precision`
- `diagnostics.calibrationBins[]`: `bucketStart`, `bucketEnd`, `predictedMean`, `observedRate`, `count`
- `diagnostics.featureImportance[]`: `feature`, `importance`

### GET /training/runs/:trainingRunId
Returns one persisted training session by ID.

### POST /training/runs
Executes a training run from operator-supplied wizard settings, then persists run state and achieved metrics for operator review.

Request fields:
- strategyId
- strategyVersion
- mode (`easy|advanced`)
- presetName
- datasetProfile
- horizonBars
- cvFolds
- calibration (`isotonic|platt|none`)
- threshold
- includeMacro
- includeNewsWindows
- includeSessionFeatures
- enableClassWeights

Response fields:
- run object with persisted training run metadata and `metricsJson`

Execution behavior:
- Backend creates a `RUNNING` training run record, executes `training/train_walk_forward.py`, then updates status to `COMPLETED` on success.
- If script execution fails, backend updates status to `FAILED` and returns `500` with `TRAINING_RUN_FAILED`.
- `metricsJson.execution` persists execution telemetry (`command`, `model`, and stdout/stderr tails) for operator diagnostics.

Diagnostics behavior:
- If `models/training_report.json` includes diagnostics artifacts, they are persisted into `metricsJson.diagnostics`.
- If diagnostics are missing in artifact input, backend persists deterministic fallback diagnostics derived from achieved AUC/Brier/calibration values so UI diagnostics remain available.

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
- 500: unexpected server failure or training execution failure (`TRAINING_RUN_FAILED`)

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
