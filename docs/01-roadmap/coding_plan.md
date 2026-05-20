# AI Trading System Coding Plan

Version: 1.1  
Last updated: 2026-05-20

## Contents
- [1. Goal](#1-goal)
- [2. Delivery Strategy](#2-delivery-strategy)
- [2.1 Original HLD Content Baseline (Consolidated)](#21-original-hld-content-baseline-consolidated)
- [2.2 Document Authority and Reading Order](#22-document-authority-and-reading-order)
- [3. Versioned Integration Plan (Full Build)](#3-versioned-integration-plan-full-build)
  - [v1.0 - Core Deterministic Trading Platform](#v10---core-deterministic-trading-platform)
  - [v1.1 - AI-Enabled Daily Breakout](#v11---ai-enabled-daily-breakout)
  - [v1.2 - Portfolio and Market Guard Expansion](#v12---portfolio-and-market-guard-expansion)
  - [v1.3 - Operations and Controlled Production Readiness](#v13---operations-and-controlled-production-readiness)
  - [v2.0 - Full Strategy Platform Integration](#v20---full-strategy-platform-integration)
  - [v2.1 - Managed Cloud Integration](#v21---managed-cloud-integration)
- [4. Phase Plan (Mapped to Versions)](#4-phase-plan-mapped-to-versions)
  - [Phase 0 - Project Bootstrap](#phase-0---project-bootstrap-2-3-days-target-v10)
  - [Phase 1 - Base MQL5 EA (No AI)](#phase-1---base-mql5-ea-no-ai-1-2-weeks-target-v10)
  - [Phase 2 - Backend API and Strategy Contract](#phase-2---backend-api-and-strategy-contract-1-week-target-v10)
  - [Phase 3 - Database and Full Audit Logging](#phase-3---database-and-full-audit-logging-1-week-target-v10)
  - [Phase 4 - Risk Engine Hardening](#phase-4---risk-engine-hardening-1-week-target-v10)
  - [Phase 5 - Baseline Backtesting and Validation](#phase-5---baseline-backtesting-and-validation-1-week-target-v10)
  - [Phase 6 - AI Pipeline and Walk-Forward Training](#phase-6---ai-pipeline-and-walk-forward-training-1-2-weeks-target-v11)
  - [Phase 7 - ONNX Inference Integration](#phase-7---onnx-inference-integration-3-5-days-target-v11)
  - [Phase 8 - Multi-Symbol Portfolio Runtime](#phase-8---multi-symbol-portfolio-runtime-1-week-target-v12)
  - [Phase 9 - Monitoring and Dashboard](#phase-9---monitoring-and-dashboard-1-2-weeks-target-v13)
  - [Phase 10 - Demo and Micro-Live Rollout](#phase-10---demo-and-micro-live-rollout-target-v13)
  - [Phase 11 - Multi-Strategy Runtime Integration](#phase-11---multi-strategy-runtime-integration-2-3-weeks-target-v20)
  - [Phase 12 - Shared Portfolio Allocator and Model Promotion Automation](#phase-12---shared-portfolio-allocator-and-model-promotion-automation-2-weeks-target-v20)
  - [Phase 13 - Managed Azure Migration and Environment Promotion](#phase-13---managed-azure-migration-and-environment-promotion-2-4-weeks-target-v21)
- [5. Version-to-Phase Traceability](#5-version-to-phase-traceability)
- [6. Priority Backlog (First 6 Sprints)](#6-priority-backlog-first-6-sprints)
- [7. Testing Plan](#7-testing-plan)
- [8. Definition of Done (Per Feature)](#8-definition-of-done-per-feature)
- [9. Technical Standards](#9-technical-standards)
- [10. Immediate Next Actions (This Week)](#10-immediate-next-actions-this-week)
- [11. Risks to Track Continuously](#11-risks-to-track-continuously)
- [12. Suggested Repository Tasks Board](#12-suggested-repository-tasks-board)

### Logging Requirements

All logs must:
1. Include `decisionId`, `signalId`, and `tradeId` for traceability.
2. Capture feature vectors and model predictions for retraining lineage.

Missing logs must trigger an alert and block promotion to the next environment.

## 1. Goal
Build a modular MT5 trading platform where shared services (execution, risk, logging, AI inference, retraining) support one or more strategy plug-ins.

First production candidate strategy:
- AI-filtered daily trend-following breakout
- Trend filter: SMA 200
- Entry breakout: 55 bars
- Stop: ATR(20) * 2.5
- Exit filter: SMA 100
- AI role: setup quality scoring and optional position scaling

## 2. Delivery Strategy
Use incremental delivery with hard quality gates. Do not enable AI in live/demo execution until base strategy, risk controls, and logging are validated.

Release tracks:
1. Core platform track: MQL5 EA, backend API, database, risk, logging
2. Strategy track: daily breakout plug-in + config + model integration
3. Model track: training, validation, ONNX export, deployment
4. Operations track: monitoring, safety controls, deployment workflow
5. UI track: operator dashboard built in Vue 3 with Tailwind CSS and light/dark theming

## 2.2 Document Authority and Reading Order
This repository treats the documents as a layered specification, not as interchangeable notes.

Authority order:
1. `../02-architecture/lld_v1.md` and `../02-architecture/lld_v2.md` define implementation behavior.
2. `../05-ui/ui_design.md` defines operator-facing UX and presentation rules.
3. `coding_plan.md` defines the delivery roadmap and phased implementation intent.
4. `../00-governance/documentation_checklist.md` defines documentation completion status and governance tracking.

Reading rules:
- Section 2.1 is preserved as historical baseline material.
- Sections 3-12 are the active planning roadmap and should be read as normative delivery guidance.
- If any planning note conflicts with the LLDs, the LLDs win.
- If any UI note conflicts with the LLDs, the UI spec must be updated to match the LLDs rather than inventing new payload shapes.

## 2.1 Original HLD Content Baseline (Consolidated)
This section preserves the substantive content of the original implementation document in planning form.
If any detail conflicts with newer LLD decisions, LLD is authoritative for implementation behavior.

Business objective baseline:
- Support configurable growth/risk profiles (5-10%, 10-15%, higher-risk profiles gated behind stronger evidence).
- Prioritize survivability, risk control, auditability, and validation over aggressive returns.
- Use AI as setup-quality probability filter and position-sizing enhancer, not as black-box price predictor.
- Keep platform modular so new strategies are plug-ins, not platform rewrites.

Design principle baseline:
- Rules identify candidate trades.
- AI filters setup quality.
- Volatility controls stops and sizing.
- Risk engine protects capital.
- MQL5 executes defensively.
- Historical data improves future models.

Target strategy profiles baseline:

| Profile | Indicative target | Style | Risk posture |
|---|---:|---|---|
| Conservative | ~5% p.a. | Low-frequency trend following | Low risk, capital preservation |
| Balanced | ~10% p.a. | AI-filtered trend + momentum | Moderate risk |
| Active | ~15% p.a. | Adaptive breakout + momentum | Higher activity/drawdown tolerance |
| Aggressive | ~20-25% p.a. | Tactical momentum / higher beta | High risk, not initial focus |
| Speculative | ~50% p.a. | High leverage / concentrated | Very high risk, not standard-client target |

Initial implementation focus:
- Primary focus remains Conservative/Balanced/Active ranges up to approximately 15% target profile.

Prototype infrastructure baseline:
- Single Azure Windows VM initially (intentional simplicity before managed-cloud migration).
- Co-locate MT5, MQL5 EA, backend, PostgreSQL, Python training, ONNX models, and the Vue 3 dashboard.

Recommended prototype VM baseline:

| Item | Recommendation |
|---|---|
| VM type | Azure Windows VM |
| Size | B2ms or equivalent |
| CPU/RAM | 2 vCPU / 8 GB |
| Disk | 128 GB Standard SSD |
| Region | UK South or West Europe |
| Security | RDP restricted by IP; strong credentials; VPN/Bastion later |
| Backup | Manual snapshots initially; automated backup later |

Technology stack baseline:

| Layer | Technology |
|---|---|
| Trading platform | MetaTrader 5 |
| Execution code | MQL5 Expert Advisor |
| Backend runtime | Node.js |
| Backend language | TypeScript |
| API framework | Fastify |
| Database | PostgreSQL |
| ORM | Prisma |
| AI training | Python |
| Candidate models | Logistic Regression, Random Forest, XGBoost, LightGBM |
| Model format | ONNX |
| Inference | ONNX Runtime in backend (MQL5 ONNX optional later) |
| Dashboard frontend | Vue 3 |
| CSS framework | Tailwind CSS |
| UI state/routing | Pinia + Vue Router |
| Charting | ECharts (via Vue integration) |
| Theme support | Mandatory light/dark mode with persisted user preference |

Architecture baseline flow:
- MT5 market data -> EA snapshot/build decision input.
- Backend feature engine + strategy plug-in + AI score + risk engine.
- Decision returned: BUY/SELL/HOLD/CLOSE/REDUCE.
- EA enforces local final safety checks before execution.
- Accepted and rejected decisions logged to PostgreSQL.
- Training/retraining pipeline learns from historical outcomes.
- Open trade info bridge: EA collects open trades, sends JSON snapshot to backend API (`POST /trades/open`), backend persists and serves via `GET /trades/open` for dashboard.

Strategy plug-in baseline intent:
- Shared reusable components: execution layer, backend API surface, DB schema conventions, risk engine, logging/audit, retraining pipeline.
- Strategy-specific modules: entry/exit logic, symbol universe, timeframe, AI model, thresholds, and risk-profile parameters.

Initial strategy baseline (daily breakout):
- Timeframe: D1.
- Trend filter: SMA200.
- Breakout lookback: 55 completed bars.
- Exit filter: SMA100.
- Volatility stop: ATR20 with 2.5x multiplier.
- Risk per trade baseline: 0.25%-0.75% (default 0.50%).
- AI thresholds baseline: full >= 0.65, half 0.55-0.65, skip < 0.55.
- Max total open risk baseline: 4%.
- Max open trades baseline: 6.
- Mandatory anti-look-ahead rule: use completed bars only (no current unfinished bar confirmation).

AI/ML baseline intent:
- AI target question: whether a valid setup is likely to hit +2R before -1R in horizon.
- Label baseline: Y=1 if +2R before -1R within 20 bars, else 0.
- Model governance: walk-forward validation, calibration checks, and out-of-sample superiority required for promotion.

Risk engine baseline controls:
- Risk engine can override strategy and AI decisions.
- Fixed-fractional sizing + ATR-based stops.
- Portfolio risk caps, open-trade caps, and one-position-per-symbol baseline start point.
- Daily/weekly loss limits, drawdown kill switch, spread/slippage/correlation controls.
- No martingale, no averaging down, no uncontrolled leverage.

Database/content baseline requirements:
- Persist all candidate signals including rejects.
- Persist feature vectors used at decision time.
- Persist execution quality data (spread, slippage, fill details, stop details, close reason).
- Persist strategy/model version lineage on predictions and trades.
- Persist outcome labels for training and calibration.

Validation baseline requirements:
- Validate base strategy first without AI.
- Use realistic spread/commission/slippage assumptions.
- Multi-symbol, multi-regime testing; avoid cherry-picked backtests.
- Favor stable parameter zones rather than single optimal points.
- AI must improve robust out-of-sample quality (drawdown/Sharpe/profit factor/expectancy).

Monitoring baseline requirements:
- Equity/drawdown/PnL views.
- Open/closed trades and rejected-signal analysis (open trades live from backend API).
- AI score distribution and drift/degradation indicators.
- Risk events and kill-switch history.
- Execution quality metrics (spread/slippage/rejections/errors).

Safety/failure baseline requirements:
- Kill switches for daily/weekly loss, drawdown, risk-cap breaches, abnormal spread, backend/model failures.
- EA must not trust backend blindly; must revalidate symbol, margin, lot, stops, and order results locally.

Original build checklist coverage baseline:
- Infrastructure provisioning, base EA, DB schema, backend endpoints, backtesting, dataset export, model training, ONNX deployment, AI thresholding, demo validation, and micro-live pilot are all represented in the phased/versioned roadmap.

## 3. Versioned Integration Plan (Full Build)

This section defines which platform capabilities ship in each version so the roadmap is not limited to v1.

## v1.0 - Core Deterministic Trading Platform
Contains:
- Repo and environment bootstrap (`backend`, `mql5`, `training`, `models`, `docs`)
- MQL5 daily-breakout EA (rule-based only, no AI gating)
- Backend strategy API (`/signal`, `/risk-check`, `/health`)
- PostgreSQL schema and full signal/trade/risk logging
- Core risk controls (risk per trade, open-risk cap, open-trade cap, kill-switch)
- Baseline backtesting and validation reports

Does not contain:
- ONNX AI inference in production decision path
- Multi-strategy runtime
- Operator dashboard as required component

## v1.1 - AI-Enabled Daily Breakout
Contains:
- Training pipeline with walk-forward validation and calibration checks
- Outcome labeling pipeline and model metadata governance
- ONNX model export + backend ONNX inference runtime
- AI score thresholds (full/half/skip) integrated into `/signal`
- Feature schema parity checks between training and inference

## v1.2 - Portfolio and Market Guard Expansion
Contains:
- Multi-symbol portfolio runtime for first strategy
- Correlation and directional exposure controls
- Gap, spread/slippage, and optional high-impact news guards
- Symbol contract-spec aware sizing across FX, metals, and indices

## v1.3 - Operations and Controlled Production Readiness
Contains:
- Dashboard/monitoring views (PnL, drawdown, risk events, AI score distribution)
- Degraded-mode runbooks and health telemetry hardening
- Demo validation cycle (8-12 weeks) and promotion checklist
- Micro-live pilot controls and incident workflow
- Production dashboard UI in Vue 3 + Tailwind CSS with full light/dark mode support

## v2.0 - Full Strategy Platform Integration
Contains:
- Multi-strategy plugin runtime (not only daily-breakout)
- Strategy-level model registry and version pinning
- Shared cross-strategy portfolio risk allocator
- Automated retraining orchestration and model promotion workflow
- Strategy comparison and attribution reporting (per strategy/model/version)

## v2.1 - Managed Cloud Integration
Contains:
- Migration path from single VM to managed services (Azure DB/containers/ML)
- Deployment automation and environment promotion (dev -> demo -> pilot)
- Backup/restore automation and operational SLO monitoring

Design-spec alignment:
- Detailed LLD for `v1.0` to `v1.3`: `../02-architecture/lld_v1.md`
- Detailed LLD for `v2.0` to `v2.1`: `../02-architecture/lld_v2.md`

## 4. Phase Plan (Mapped to Versions)

## Phase 0 - Project Bootstrap (2-3 days) [Target: v1.0]
Objective:
- Establish repo structure, coding standards, and local dev flow.

Tasks:
- Create monorepo structure:
  - `backend/` (Node.js + TypeScript + Fastify + Prisma)
  - `mql5/` (EA + includes)
  - `training/` (Python training pipelines)
  - `models/` (ONNX artifacts + metadata)
  - `dashboard/` (Vue 3 + Tailwind CSS)
  - `../` (HLD, runbooks, ADRs)
- Add initial tooling:
  - TypeScript config, linting, formatting
  - `.env.example`
  - Docker compose for PostgreSQL (dev only)
- Define coding conventions and branching workflow.

Deliverables:
- Directory skeleton
- Backend compiles and serves `GET /health`
- Prisma connected to local PostgreSQL

Exit criteria:
- `npm run build` and `npm run lint` pass in `backend/`
- PostgreSQL reachable and migrations runnable

## Phase 1 - Base MQL5 EA (No AI) (1-2 weeks) [Target: v1.0]
Objective:
- Implement deterministic daily breakout strategy with strict completed-candle logic.

Tasks:
- Build EA modules:
  - Candle detection (new completed bar only)
  - Indicator calculations: SMA200, SMA100, ATR20
  - Breakout detection (55 completed bars)
  - Position sizing (risk % + stop distance)
  - Execution via `CTrade`
  - Exit rules and stop placement
- Add local safety checks:
  - Symbol trade mode, spread guard, margin checks
  - One position per symbol
  - Broker lot step/min/max validation
- Log local execution events to file for early diagnostics.

Deliverables:
- Backtestable EA for D1 timeframe
- Configurable params for risk profile and symbol list

Exit criteria:
- Signals only use bar `[1]` and prior complete bars
- EA can complete single-symbol backtest end-to-end
- No unsafe order attempts on invalid lot/stop values

## Phase 2 - Backend API and Strategy Contract (1 week) [Target: v1.0]
Objective:
- Build strategy orchestration service that can evaluate plug-ins and return trade decisions.

Tasks:
- Implement Fastify modules:
  - `POST /signal`
  - `POST /risk-check`
  - `POST /log-signal`
  - `POST /log-trade`
  - `POST /log-rejected-signal`
  - `GET /model-version`
  - `GET /performance`
  - `GET /health`
- Define plugin interfaces in TypeScript:
  - `StrategyPlugin`
  - `MarketSnapshot`, `StrategyFeatures`, `SetupCandidate`, `SetupScore`, `TradePlan`
- Implement `daily-breakout-5-10` plugin (rule-based first, AI disabled).

Deliverables:
- API returns deterministic BUY/SELL/HOLD decisions for test fixtures
- Strategy plug-in loaded by registry/config

Exit criteria:
- API contract tests pass
- Plugin can be swapped without changes to shared modules

## Phase 3 - Database and Full Audit Logging (1 week) [Target: v1.0]
Objective:
- Capture all decisions and outcomes for auditability and future model training.

Tasks:
- Create Prisma schema and migrations for core tables:
  - `signals`, `rejected_signals`, `trades`, `positions`
  - `features`, `model_predictions`, `risk_events`
  - `strategy_configs`, `model_versions`, `training_runs`
  - `account_snapshots`, `performance_snapshots`
- Add required fields:
  - `strategy_id`, `strategy_version`, `model_version`
  - `symbol`, `timeframe`, `decision_id`, `signal_id`, `risk_profile`, `created_at`
- Implement idempotent logging writes using unique decision keys.

Deliverables:
- Migration scripts
- DB-backed logging service with retry-safe inserts

Exit criteria:
- Every decision path is persisted (accepted, rejected, errored)
- Traceability from signal to trade to outcome is queryable

## Phase 4 - Risk Engine Hardening (1 week) [Target: v1.0]
Objective:
- Enforce portfolio-level and trade-level controls independent of strategy and AI.

Tasks:
- Implement risk rules:
  - Risk per trade (default 0.50%)
  - Max total open risk (default 4%)
  - Max open trades (default 6)
  - Daily/weekly loss limits
  - Spread and slippage guards
  - Correlation concentration checks
- Add kill-switch state machine with reasons and reset policy.
- Add EA-side final risk validation before order send.

Deliverables:
- Shared `risk-engine` module in backend
- Risk events persisted and visible in performance endpoints

Exit criteria:
- Risk engine can veto any signal regardless of AI score
- Kill-switch conditions tested by simulation fixtures

## Phase 5 - Baseline Backtesting and Validation (1 week) [Target: v1.0]
Objective:
- Validate non-AI strategy robustness before ML integration.

Tasks:
- Build repeatable backtest scenarios:
  - Multi-symbol tests
  - Realistic spread/slippage/commission assumptions
  - Regime coverage (trend, range, high-volatility periods)
- Produce baseline metrics:
  - Expectancy, profit factor, max drawdown, trade count, Sharpe
- Identify stable parameter zones, not single-point optimizations.

Deliverables:
- Baseline validation report in `../validation/baseline.md`
- Exported signal/outcome dataset for ML

Exit criteria:
- Base strategy meets minimum threshold across multiple symbols
- No look-ahead bias detected

## Phase 6 - AI Pipeline and Walk-Forward Training (1-2 weeks) [Target: v1.1]
Objective:
- Train setup-quality classifier and validate out-of-sample behavior.

Tasks:
- Implement training pipeline in `training/`:
  - Data extraction from PostgreSQL
  - Label generation: +2R before -1R within 20 bars
  - Time-based splits and walk-forward windows
  - Model training: Logistic Regression, Random Forest, XGBoost/LightGBM
  - Calibration checks (Brier score, reliability bins)
- Store model metadata, feature schema, and validation artifacts.

Deliverables:
- Training scripts and reproducible run config
- Best candidate model with validation report

Exit criteria:
- Out-of-sample results beat baseline on selected criteria
- Calibration and trade-count adequacy checks pass

## Phase 7 - ONNX Inference Integration (3-5 days) [Target: v1.1]
Objective:
- Integrate validated model into runtime decision path safely.

Tasks:
- Export selected model to ONNX with versioning.
- Add backend ONNX Runtime inference service.
- Implement threshold logic:
  - `score >= 0.65`: full size
  - `0.55 <= score < 0.65`: half size
  - `< 0.55`: skip
- Log all inference outputs with model version and feature hash.

Deliverables:
- AI-enabled `/signal` responses
- Model version endpoint wired to active artifacts

Exit criteria:
- Inference latency acceptable for D1 strategy
- Feature schema parity checks pass between training and runtime

## Phase 8 - Multi-Symbol Portfolio Runtime (1 week) [Target: v1.2]
Objective:
- Expand from single-symbol to portfolio execution with controlled risk aggregation.

Tasks:
- Add symbol universe config and scheduling cadence.
- Enforce portfolio-wide risk across all open and pending exposures.
- Add symbol-specific contract metadata handling (tick size/value, volume steps).

Deliverables:
- Portfolio-ready configuration profiles (5-10 and 10-15)

Exit criteria:
- Multi-symbol simulation runs without exposure-limit violations

## Phase 9 - Monitoring and Dashboard (1-2 weeks) [Target: v1.3]
Objective:
- Provide operations visibility and safety observability.

Tasks:
- Build dashboard app using Vue 3 + Tailwind CSS.
- Implement global theming system with mandatory light and dark mode.
- Persist user theme preference and support system theme fallback.
- Build dashboard views:
  - Equity, drawdown, PnL (daily/weekly)
  - Trade ledger and rejected signals (live open trades from backend API)
  - AI score distribution and drift proxies
  - Risk events and kill-switch history
- Add service-health monitors for backend, DB, and EA connectivity.

Deliverables:
- Operator dashboard (Vue 3 web UI with light/dark mode)

Exit criteria:
- Operator can diagnose strategy, risk, model, and system status in one place

## Phase 10 - Demo and Micro-Live Rollout [Target: v1.3]
Objective:
- Controlled operational validation before scaling risk.

Tasks:
- Demo run: 8-12 weeks with weekly review cadence.
- Micro-live run: 3-6 months with minimal capital.
- Promotion criteria include:
  - Drawdown boundaries respected
  - Stable execution quality
  - No unresolved safety incidents

Deliverables:
- Deployment readiness report and go/no-go decision log

Exit criteria:
- Meets predefined risk and operational reliability thresholds

## Phase 11 - Multi-Strategy Runtime Integration (2-3 weeks) [Target: v2.0]
Objective:
- Evolve from a single-strategy deployment to a true strategy platform runtime.

Tasks:
- Add at least one additional plugin (for example `adaptive-momentum-10-15`).
- Implement strategy registry with per-strategy enable/disable, symbol scopes, and profile overrides.
- Add strategy isolation controls so one strategy can fail without stopping others.
- Add strategy-level attribution (`strategy_id`, `strategy_version`, `model_version`) across all reports.

Deliverables:
- Multi-strategy execution build with strategy-level observability

Exit criteria:
- Multiple strategies can run concurrently under shared risk controls without record collisions

## Phase 12 - Shared Portfolio Allocator and Model Promotion Automation (2 weeks) [Target: v2.0]
Objective:
- Centralize cross-strategy capital allocation and automate model promotion safely.

Tasks:
- Build portfolio allocator that enforces total risk budget across strategies.
- Add capital/risk budget assignment by strategy profile and recent performance.
- Implement model promotion workflow (candidate -> validation -> staged -> active).
- Add rollback mechanism to prior model version with one-step revert.

Deliverables:
- Cross-strategy risk allocator and model promotion pipeline

Exit criteria:
- Strategy additions or model upgrades do not require manual code edits in execution paths

## Phase 13 - Managed Azure Migration and Environment Promotion (2-4 weeks) [Target: v2.1]
Objective:
- Migrate from single-VM prototype operations to managed-cloud deployment patterns.

Tasks:
- Move PostgreSQL to managed service and validate migration/backups.
- Containerize backend/training services and define environment configs.
- Implement CI/CD environment promotion gates (dev -> demo -> pilot).
- Add SLO dashboards and automated backup/restore drills.

Deliverables:
- Managed-cloud deployment baseline with promotion controls

Exit criteria:
- Managed deployment can be recovered from backup and promoted between environments without manual reconfiguration

## 5. Version-to-Phase Traceability
Version mapping:
- `v1.0`: Phases 0, 1, 2, 3, 4, 5
- `v1.1`: Phases 6, 7
- `v1.2`: Phase 8
- `v1.3`: Phases 9, 10
- `v2.0`: Phases 11, 12
- `v2.1`: Phase 13

Planned extension mapping:
- `v2.0`: Multi-strategy runtime + shared allocator + retrain/promotion automation
- `v2.1`: Managed Azure migration + deployment automation + operational SLO controls

## 6. Priority Backlog (First 6 Sprints)
Sprint 1:
- Repo scaffolding
- Backend skeleton + health endpoint
- Prisma init + first migration

Sprint 2:
- EA base indicators + completed-candle engine
- Rule-based entry/exit implementation
- Unit tests for breakout and MA logic (backend fixtures)

Sprint 3:
- `/signal` + strategy plugin registry
- Logging endpoints + decision IDs
- DB writes for signals/trades/rejections

Sprint 4:
- Risk engine rules + kill-switches
- EA local safety validations
- Integration tests for veto paths

Sprint 5:
- Baseline multi-symbol backtest
- Validation report generation
- Training dataset export pipeline

Sprint 6:
- First ML training run + walk-forward report
- ONNX export and backend inference wiring
- AI threshold decisions in `/signal`

## 7. Testing Plan
Test layers:
- Unit tests:
  - Feature calculations
  - Risk formulas
  - Strategy rule logic
- Integration tests:
  - API decision flow
  - DB persistence and idempotency
  - ONNX inference path
- System tests:
  - EA-backend round trip
  - Kill-switch behavior
  - Degraded backend behavior
- Backtest validation:
  - Multi-symbol, multi-regime, realistic costs

Minimum CI gates:
- Lint and type-check pass
- Unit and integration tests pass
- Prisma migration check pass
- API contract tests pass

## 8. Definition of Done (Per Feature)
A feature is done only when:
- Code implemented and reviewed
- Tests added and passing
- Structured logs emitted
- Metrics/events observable
- Documentation updated
- Safety/risk impact assessed

## 9. Technical Standards
Backend:
- TypeScript strict mode
- Fastify for APIs
- Prisma migrations versioned in git
- Structured JSON logging

MQL5:
- Defensive order execution
- Strict completed-bar signal checks
- Parameterized symbol/profile config
- Explicit error handling and retry boundaries

AI/Training:
- Time-series safe splitting only
- Reproducible training configs
- Versioned model artifacts and feature schema
- Calibration report required for promotion

## 10. Immediate Next Actions (This Week)
1. Scaffold repo folders and baseline configs.
2. Implement backend `GET /health` and Prisma bootstrap.
3. Build EA completed-candle detector + SMA/ATR/breakout logic.
4. Define strategy plugin interfaces and first plugin stub.
5. Create initial DB schema with core audit tables.
6. Add smoke tests for API and strategy rule fixtures.

## 11. Risks to Track Continuously
- Look-ahead bias from candle indexing mistakes
- Feature mismatch between Python and runtime services
- Underestimated spread/slippage assumptions
- Overfitting due to weak walk-forward controls
- Broker symbol spec differences causing invalid sizing

## 12. Suggested Repository Tasks Board
Columns:
- Backlog
- In Progress
- In Review
- Done
- Blocked

Labels:
- `area:ea`
- `area:backend`
- `area:data`
- `area:ai`
- `area:risk`
- `area:ops`
- `priority:p0|p1|p2`
- `risk:high`

Milestones:
- `M1 (v1.0) Base Non-AI EA`
- `M2 (v1.0) API + Audit Logging`
- `M3 (v1.0) Risk Hardened`
- `M4 (v1.1) AI Candidate Ready`
- `M5 (v1.2) Portfolio Runtime`
- `M6 (v1.3) Demo Validation Complete`
- `M7 (v1.3) Micro-Live Pilot Complete`
- `M8 (v2.0) Multi-Strategy Integration`
- `M9 (v2.1) Managed Cloud Migration`
