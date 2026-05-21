# AI Trading System Low-Level Design (LLD) - v1

Version: 1.0
Last updated: 2026-05-21
Coverage: `v1.0` to `v1.3` from `../01-roadmap/coding_plan.md`

## News Provider Decision (Normative)
- Selected provider: Financial Modeling Prep (FMP).
- Pricing reference: https://site.financialmodelingprep.com/developer/docs/pricing
- `v1.x` tier: `FREE`.
- `v2+` tier: `BASIC`.
- LLD integration: `v1.1` scheduled-news execution is defined in `lld_v1_1_news.md` and must persist provider lineage as `FMP`.

## Contents
- [1. Scope](#1-scope)
- [2. Runtime Architecture](#2-runtime-architecture)
- [3. Strategy Logic (Daily Breakout)](#3-strategy-logic-daily-breakout)
- [4. API Contracts](#4-api-contracts)
- [5. Risk Engine](#5-risk-engine)
- [6. Data Model (v1)](#6-data-model-v1)
- [7. AI and Relearning (v1)](#7-ai-and-relearning-v1)
- [8. Safety and Failure Handling](#8-safety-and-failure-handling)
- [9. Testing and Acceptance](#9-testing-and-acceptance)
- [10. UI Design (v1.3)](#10-ui-design-v13)

## Progress Table
| Step | Version target | Related tech | Implementation language/runtime | Component placement | Status | Notes |
|---|---|---|---|---|---|---|
| 1. Bootstrap repository and tooling | v1.0 | Node.js, TypeScript, Prisma, PostgreSQL, MQL5 | TypeScript/Node.js + SQL + MQL5 | Repository root, backend bootstrap, MQL5 project skeleton | Planned | Workspace, build, lint, and migration tooling ready |
| 2. Build deterministic EA execution | v1.0 | MQL5, MT5, CTrade | MQL5 in MT5 terminal | EA execution module and indicator/risk includes | Planned | Completed-candle rule and base order lifecycle |
| 3. Implement strategy API contracts | v1.0 | Fastify, TypeScript | TypeScript on Node.js | Backend API layer (`/signal`, `/risk-check`, logging endpoints) | Planned | Signal and risk endpoints with strict schemas |
| 4. Add audit-grade persistence | v1.0 | PostgreSQL, Prisma | TypeScript/Node.js + SQL | Backend DB repository and migration layer | Planned | Signals, rejections, trades, risk events, snapshots |
| 5. Enforce core risk controls | v1.0 | Risk engine, MQL5 safety checks | TypeScript on Node.js + MQL5 guards | Backend risk engine plus EA local validation path | Planned | Caps, kill-switches, and fail-closed behavior |
| 6. Baseline non-AI validation | v1.0 | MT5 Strategy Tester, reporting | MT5 tester + analysis scripts | Backtest harness and validation report outputs | Planned | Multi-symbol backtest with realistic costs |
| 7. Implement model training pipeline | v1.1 | Python, pandas/sklearn/xgboost/lightgbm | Python training jobs | `training/` pipelines and model artifact generation | Planned | Walk-forward, calibration, and label generation |
| 8. Integrate ONNX inference runtime | v1.1 | ONNX Runtime, Node.js | TypeScript on Node.js | Backend model-inference service in decision flow | Planned | Full/half/skip thresholds in decision flow |
| 9. Expand to portfolio runtime | v1.2 | Backend scheduler, risk allocator logic | TypeScript on Node.js | Backend orchestration and portfolio-risk modules | Planned | Correlation, gap, slippage, and news guards |
| 10. Add operations monitoring views | v1.3 | Vue 3, Tailwind CSS, Pinia, Vue Router, ECharts, metrics/logging | Vue 3 SPA + TypeScript | Dashboard/reporting layer and health endpoints | Planned | Equity, drawdown, AI scores, risk-event history with light/dark mode |
| 11. Run demo validation cycle | v1.3 | MT5 demo account, operational runbooks | MQL5 runtime + backend ops workflows | Demo deployment environment and runbook process | Planned | 8-12 week evidence and incident tracking |
| 12. Execute micro-live pilot | v1.3 | Live broker integration, safeguards | MQL5 runtime + backend ops workflows | Pilot deployment environment with strict guardrails | Planned | Controlled capital rollout with promotion criteria |

## 1. Scope
In scope:
- `v1.0`: Core deterministic daily-breakout platform
- `v1.1`: AI-enabled decision filtering via ONNX
- `v1.2`: Multi-symbol portfolio controls and market guards
- `v1.3`: Monitoring, demo validation, and micro-live controls

Out of scope:
- Cross-strategy shared allocator and strategy registry orchestration (`v2.0`)
- Managed-cloud migration and environment promotion (`v2.1`)

## 2. Runtime Architecture
Processes:
- MT5 + MQL5 EA
- Node.js/Fastify backend
- PostgreSQL
- Python training jobs

Open trade info bridge:
- MQL5 EA collects open trade/order/account info using MQL5 functions (e.g., `PositionsTotal()`, `PositionGetTicket()`, etc.).
- EA serializes open trade data as JSON and sends it via HTTP POST (`WebRequest`) to backend endpoint (`/api/trades/open`).
- Backend authenticates, parses, and persists open trade info (PostgreSQL or cache).
- Backend exposes `GET /api/trades/open` for frontend consumption.
- Frontend (Vue 3) fetches and displays open trades in the "Trades and Signals" view.

Flow:
1. EA detects new completed D1 candle.
2. EA sends market/account snapshot to `POST /signal`.
3. Backend applies strategy rule logic, optional AI score, and risk veto.
4. Backend returns action (`BUY|SELL|HOLD|CLOSE|REDUCE`) with trace keys.
5. EA performs local safety checks and executes via `CTrade`.
6. Backend persists signal/trade/risk/model logs for audit and retraining.

Startup model contract check:
- Backend startup includes model inference preflight to validate ONNX output compatibility.
- `GET /health` must expose model loader state as `available` or `degraded`.

## 3. Strategy Logic (Daily Breakout)
Signal rules (completed bars only):
- Long: `Close[1] > SMA200[1]` and `Close[1] > HighestHigh(55, bars 2..56)`.
- Short: `Close[1] < SMA200[1]` and `Close[1] < LowestLow(55, bars 2..56)`.
- Exit long: `Close[1] < SMA100[1]`.
- Exit short: `Close[1] > SMA100[1]`.
- Stop: `2.5 * ATR20[1]` from entry.

Feature parity requirements:
- Runtime inference feature schema must match training schema exactly.
- `volatility` is required in signal payload and must be rolling return volatility from completed bars.
- ATR is not a substitute for volatility in model input.

Execution guards:
- Gap guard: reject if `abs(open[0]-close[1]) / ATR20[1] > maxGapAtr`.
- Spread guard: reject if `spreadPrice / atr20_1 > spreadAtrMax`.
- Slippage guard with optional size reduction.
- Optional cooldown after stop-out.

## 4. API Contracts
Mandatory endpoints:
- `POST /signal`
- `POST /risk-check`
- `POST /log-signal`
- `POST /log-rejected-signal`
- `POST /log-trade`
- `GET /model-version`
- `GET /performance`
- `GET /health`
- `POST /trades/open` (from EA, open trade snapshot)
- `GET /trades/open` (for dashboard, current open trades)

Idempotency and traceability:
- `decisionKey = strategyId + symbol + timeframe + barCloseTimeUtc`
- `decisionId` immutable client UUID for request correlation
- Response must include `decisionId`, `signalId`, `barCloseTimeUtc`, `evaluatedAtUtc`
- Duplicate signal writes must return the previously persisted response (idempotent replay behavior).
- Portfolio evaluations must persist atomically and support replay-safe idempotency via decision ID or request hash.

## 5. Risk Engine
Core controls:
- `riskPerTrade` default `0.005`
- `maxOpenRisk` default `0.04`
- `maxOpenTrades` default `6`
- One position per symbol
- Daily/weekly loss limits + drawdown/system pause states
- Correlation and directional exposure controls
- Optional high-impact news block/reduce policy

Sizing model:
- Uses symbol metadata (`tickSize`, `tickValueAccountCcy`, `contractSize`)
- Cross-currency conversion supported via `c_fx`
- Reject trade when metadata is missing/inconsistent

### Metadata Validation Policy

If symbol metadata (`tickSize`, `tickValueAccountCcy`, `contractSize`) is missing or inconsistent:
1. Reject the trade with a `MISSING_METADATA` error.
2. Log the rejection in the `rejected_signals` table with the reason code.
3. Notify the operator via the dashboard with actionable details.

## 6. Data Model (v1)
Core tables:
- `strategy_configs`
- `model_versions`
- `signals`
- `rejected_signals`
- `features`
- `model_predictions`
- `trades`
- `positions`
- `risk_events`
- `account_snapshots`
- `training_runs`
- `outcome_labels`
- `performance_snapshots`

Data guarantees:
- Persist all candidate signals, including rejections
- Persist feature vectors and model version lineage
- Persist execution quality (`spread`, `slippage`, `commission`, `swap`)
- Persist labels (`+2R` before `-1R` within `20` bars)

## 7. AI and Relearning (v1)
Training and validation:
- Walk-forward windows only (time-series safe)
- Purge/embargo between train and validation slices
- Calibration checks (Brier + reliability bins)

Periodic relearning policy:
- Recalibration review every 4 weeks or earlier on drift trigger
- Retrain when OOS calibration or expectancy breaches threshold
- Model promotion: `candidate -> validation -> staged -> active`

## 8. Safety and Failure Handling
EA-safe behavior:
- If backend unavailable: no new entries; protective exits still allowed
- If response invalid: treat as `HOLD` and log risk event
- If DB critical write unavailable: block new entries

Degraded modes:
- AI unavailable and optional profile: fallback to rule-only
- AI unavailable and mandatory profile: pause strategy/system

v1.3 operations hardening requirements:
- Maintain degraded-mode runbooks for backend unavailable, model unavailable, and DB-write-failure scenarios.
- Emit health telemetry for EA connectivity, backend health, DB health, and model loader status.
- Record kill-switch activation reasons and operator actions in incident logs for demo/micro-live audit.
- Provide operator monitoring views for equity/drawdown, PnL, AI-score distribution, and risk-event history.

## 9. Testing and Acceptance
Minimum gates:
- Unit: strategy rules, sizing math, unit normalization
- Integration: API flow, DB persistence, idempotency by `decisionKey`
- System: EA-backend roundtrip, kill-switch behavior, degraded mode behavior
- Validation: multi-symbol, multi-regime, realistic costs, gap stress tests

Quality notes:
- This v1 LLD is aligned to `../01-roadmap/coding_plan.md` phases 0 through 10.
- Relearning cadence and drift-trigger retraining are intentionally explicit for live operations.
- Safety controls are fail-closed for new entries when critical dependencies are unavailable.

Version exit mapping:
- `v1.0`: deterministic base + risk + logging + baseline backtest
- `v1.1`: AI inference and promotion controls active
- `v1.2`: portfolio controls and market guards active
- `v1.3`: monitoring + demo and micro-live operational evidence

## 10. UI Design (v1.3)
Frontend stack:
- Framework: Vue 3
- CSS framework: Tailwind CSS
- State management: Pinia
- Routing: Vue Router
- Visualization: ECharts (Vue integration)

UI requirements:
- Light and dark mode are mandatory.
- Theme switch must be available in the global shell/header.
- Theme preference must persist per user/browser session (local storage) with system theme fallback.
- All monitoring views must be readable and contrast-safe in both modes.

Core views:
- Portfolio overview (equity, drawdown, PnL).
- Trade and signal ledger (accepted + rejected with reasons, live open trades from backend API).
- AI monitoring (score distribution, drift proxy indicators).
- Risk and safety panel (kill-switch status/events, connectivity health).

### Risk Decision Flow

The risk engine evaluates trades in two stages:
1. **Signal-level vetoes**: Applied during `/signal` processing.
2. **Account-level checks**: Applied during `/risk-check` processing.

This ensures that immediate strategy constraints are enforced early, while detailed account-level evaluations occur before execution.
