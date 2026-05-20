# Full Implementation Runbook and Progress Tracker

Version: 1.0
Last updated: 2026-05-20
Owner: Tech Lead
Status: Active

## Purpose
Provide a single execution runbook that tracks implementation progress for every roadmap item, phase task, deliverable, and exit criterion.

## Source Alignment
Primary references:
- ../01-roadmap/coding_plan.md
- ../02-architecture/lld_v1.md
- ../02-architecture/lld_v2.md
- ../05-ui/ui_design.md
- documentation_checklist.md

## How to Use
- Mark each checkbox when complete.
- Do not mark deliverables complete unless all required tasks are complete.
- Do not mark phase exit criteria complete unless all deliverables are complete.
- Update this file in the same change as implementation work.

## Global Phase Dashboard
| Phase | Version target | Status | Owner | Start date | End date | Blockers |
|---|---|---|---|---|---|---|
| 0 Project Bootstrap | v1.0 | Not started |  |  |  |  |
| 1 Base MQL5 EA | v1.0 | Not started |  |  |  |  |
| 2 Backend API and Strategy Contract | v1.0 | Not started |  |  |  |  |
| 3 Database and Audit Logging | v1.0 | Not started |  |  |  |  |
| 4 Risk Engine Hardening | v1.0 | Not started |  |  |  |  |
| 5 Baseline Backtesting and Validation | v1.0 | Not started |  |  |  |  |
| 6 AI Pipeline and Walk-Forward Training | v1.1 | Not started |  |  |  |  |
| 7 ONNX Inference Integration | v1.1 | Not started |  |  |  |  |
| 8 Multi-Symbol Portfolio Runtime | v1.2 | Not started |  |  |  |  |
| 9 Monitoring and Dashboard | v1.3 | Not started |  |  |  |  |
| 10 Demo and Micro-Live Rollout | v1.3 | Not started |  |  |  |  |
| 11 Multi-Strategy Runtime Integration | v2.0 | Not started |  |  |  |  |
| 12 Shared Allocator and Model Promotion Automation | v2.0 | Not started |  |  |  |  |
| 13 Managed Azure Migration and Environment Promotion | v2.1 | Not started |  |  |  |  |

## Phase 0 - Project Bootstrap (Target v1.0)
Objective:
- [ ] Establish repo structure, coding standards, and local dev flow.

Tasks:
- [ ] Create backend folder (Node.js + TypeScript + Fastify + Prisma).
- [ ] Create mql5 folder (EA + includes).
- [ ] Create training folder (Python training pipelines).
- [ ] Create models folder (ONNX artifacts + metadata).
- [ ] Create dashboard folder (Vue 3 + Tailwind CSS).
- [ ] Create docs structure for HLD, runbooks, ADRs.
- [ ] Add TypeScript config.
- [ ] Add linting.
- [ ] Add formatting.
- [ ] Add .env.example.
- [ ] Add Docker compose for PostgreSQL (dev only).
- [ ] Define coding conventions and branching workflow.

Deliverables:
- [ ] Directory skeleton complete.
- [ ] Backend compiles and serves GET /health.
- [ ] Prisma connected to local PostgreSQL.

Exit criteria:
- [ ] npm run build passes in backend.
- [ ] npm run lint passes in backend.
- [ ] PostgreSQL reachable and migrations runnable.

## Phase 1 - Base MQL5 EA (No AI) (Target v1.0)
Objective:
- [ ] Implement deterministic daily breakout strategy with strict completed-candle logic.

Tasks:
- [ ] Implement candle detection for new completed bar only.
- [ ] Implement indicator calculations SMA200, SMA100, ATR20.
- [ ] Implement breakout detection on 55 completed bars.
- [ ] Implement position sizing based on risk percent and stop distance.
- [ ] Implement execution via CTrade.
- [ ] Implement exit rules and stop placement.
- [ ] Add local safety checks for symbol trade mode, spread guard, margin.
- [ ] Enforce one position per symbol.
- [ ] Validate broker lot step/min/max.
- [ ] Log local execution events for diagnostics.

Deliverables:
- [ ] Backtestable EA for D1 timeframe.
- [ ] Configurable params for risk profile and symbol list.

Exit criteria:
- [ ] Signals use only bar index 1 and prior complete bars.
- [ ] Single-symbol backtest runs end-to-end.
- [ ] No unsafe order attempts for invalid lot or stop values.

## Phase 2 - Backend API and Strategy Contract (Target v1.0)
Objective:
- [ ] Build strategy orchestration service that evaluates plug-ins and returns decisions.

Tasks:
- [ ] Implement POST /signal.
- [ ] Implement POST /risk-check.
- [ ] Implement POST /log-signal.
- [ ] Implement POST /log-trade.
- [ ] Implement POST /log-rejected-signal.
- [ ] Implement GET /model-version.
- [ ] Implement GET /performance.
- [ ] Implement GET /health.
- [ ] Define StrategyPlugin TypeScript interface.
- [ ] Define MarketSnapshot interface.
- [ ] Define StrategyFeatures interface.
- [ ] Define SetupCandidate interface.
- [ ] Define SetupScore interface.
- [ ] Define TradePlan interface.
- [ ] Implement daily-breakout-5-10 plugin in rule-only mode.

Deliverables:
- [ ] Deterministic BUY/SELL/HOLD responses for fixtures.
- [ ] Strategy plugin loaded by registry/config.

Exit criteria:
- [ ] API contract tests pass.
- [ ] Plugin swap works without shared-module edits.

## Phase 3 - Database and Full Audit Logging (Target v1.0)
Objective:
- [ ] Capture all decisions and outcomes for audit and training.

Tasks:
- [ ] Add Prisma schema and migrations for signals.
- [ ] Add Prisma schema and migrations for rejected_signals.
- [ ] Add Prisma schema and migrations for trades.
- [ ] Add Prisma schema and migrations for positions.
- [ ] Add Prisma schema and migrations for features.
- [ ] Add Prisma schema and migrations for model_predictions.
- [ ] Add Prisma schema and migrations for risk_events.
- [ ] Add Prisma schema and migrations for strategy_configs.
- [ ] Add Prisma schema and migrations for model_versions.
- [ ] Add Prisma schema and migrations for training_runs.
- [ ] Add Prisma schema and migrations for account_snapshots.
- [ ] Add Prisma schema and migrations for performance_snapshots.
- [ ] Add required fields strategy_id, strategy_version, model_version.
- [ ] Add required fields symbol, timeframe, decision_id, signal_id, risk_profile, created_at.
- [ ] Implement idempotent logging writes via unique decision keys.

Deliverables:
- [ ] Migration scripts created.
- [ ] DB-backed logging service supports retry-safe inserts.

Exit criteria:
- [ ] Accepted, rejected, and errored decision paths are persisted.
- [ ] Traceability signal -> trade -> outcome is queryable.

## Phase 4 - Risk Engine Hardening (Target v1.0)
Objective:
- [ ] Enforce portfolio-level and trade-level controls independent of strategy and AI.

Tasks:
- [ ] Implement risk per trade default 0.50%.
- [ ] Implement max total open risk default 4%.
- [ ] Implement max open trades default 6.
- [ ] Implement daily loss limits.
- [ ] Implement weekly loss limits.
- [ ] Implement spread guards.
- [ ] Implement slippage guards.
- [ ] Implement correlation concentration checks.
- [ ] Implement kill-switch state machine with reasons and reset policy.
- [ ] Add EA-side final risk validation before order send.

Deliverables:
- [ ] Shared risk-engine module in backend.
- [ ] Risk events persisted and visible in performance endpoints.

Exit criteria:
- [ ] Risk engine can veto any signal regardless of AI score.
- [ ] Kill-switch conditions tested via simulation fixtures.

## Phase 5 - Baseline Backtesting and Validation (Target v1.0)
Objective:
- [ ] Validate non-AI strategy robustness before ML integration.

Tasks:
- [ ] Build multi-symbol backtest scenarios.
- [ ] Use realistic spread, slippage, commission assumptions.
- [ ] Cover trend, range, and high-volatility regimes.
- [ ] Produce expectancy metric.
- [ ] Produce profit factor metric.
- [ ] Produce max drawdown metric.
- [ ] Produce trade count metric.
- [ ] Produce Sharpe metric.
- [ ] Identify stable parameter zones.

Deliverables:
- [ ] Baseline validation report at ../validation/baseline.md.
- [ ] Exported signal/outcome dataset for ML.

Exit criteria:
- [ ] Base strategy passes threshold across multiple symbols.
- [ ] No look-ahead bias detected.

## Phase 6 - AI Pipeline and Walk-Forward Training (Target v1.1)
Objective:
- [ ] Train setup-quality classifier and validate out-of-sample behavior.

Tasks:
- [ ] Implement data extraction from PostgreSQL.
- [ ] Implement label generation (+2R before -1R within 20 bars).
- [ ] Implement time-based splits and walk-forward windows.
- [ ] Train Logistic Regression model.
- [ ] Train Random Forest model.
- [ ] Train XGBoost or LightGBM model.
- [ ] Implement calibration checks (Brier score, reliability bins).
- [ ] Store model metadata.
- [ ] Store feature schema.
- [ ] Store validation artifacts.

Deliverables:
- [ ] Training scripts and reproducible run configuration.
- [ ] Best candidate model with validation report.

Exit criteria:
- [ ] Out-of-sample results beat baseline for selected criteria.
- [ ] Calibration and trade-count adequacy checks pass.

## Phase 7 - ONNX Inference Integration (Target v1.1)
Objective:
- [ ] Integrate validated model into runtime decision path safely.

Tasks:
- [ ] Export selected model to ONNX with versioning.
- [ ] Add backend ONNX Runtime inference service.
- [ ] Implement threshold score >= 0.65 full size.
- [ ] Implement threshold 0.55 <= score < 0.65 half size.
- [ ] Implement threshold score < 0.55 skip.
- [ ] Log inference outputs with model version and feature hash.

Deliverables:
- [ ] AI-enabled /signal responses.
- [ ] Model version endpoint wired to active artifacts.

Exit criteria:
- [ ] Inference latency acceptable for D1 strategy.
- [ ] Feature schema parity checks pass between training and runtime.

## Phase 8 - Multi-Symbol Portfolio Runtime (Target v1.2)
Objective:
- [ ] Expand from single-symbol to portfolio execution with controlled risk aggregation.

Tasks:
- [ ] Add symbol universe config and scheduling cadence.
- [ ] Enforce portfolio-wide risk across open and pending exposures.
- [ ] Add symbol-specific contract metadata handling (tick size/value, volume steps).

Deliverables:
- [ ] Portfolio-ready config profiles for 5-10 and 10-15.

Exit criteria:
- [ ] Multi-symbol simulation runs without exposure-limit violations.

## Phase 9 - Monitoring and Dashboard (Target v1.3)
Objective:
- [ ] Provide operations visibility and safety observability.

Tasks:
- [ ] Build dashboard app using Vue 3 and Tailwind CSS.
- [ ] Implement global theming with light and dark modes.
- [ ] Persist user theme preference with system fallback.
- [ ] Build equity, drawdown, PnL views.
- [ ] Build trade ledger and rejected signal views.
- [ ] Build AI score distribution and drift proxy views.
- [ ] Build risk events and kill-switch history views.
- [ ] Add backend, DB, and EA connectivity health monitors.

Deliverables:
- [ ] Operator dashboard with light and dark mode.

Exit criteria:
- [ ] Operator can diagnose strategy, risk, model, and system status in one place.

## Phase 10 - Demo and Micro-Live Rollout (Target v1.3)
Objective:
- [ ] Perform controlled operational validation before scaling risk.

Tasks:
- [ ] Run demo for 8-12 weeks with weekly review cadence.
- [ ] Run micro-live for 3-6 months with minimal capital.
- [ ] Validate drawdown boundaries are respected.
- [ ] Validate execution quality remains stable.
- [ ] Verify no unresolved safety incidents.

Deliverables:
- [ ] Deployment readiness report.
- [ ] Go or no-go decision log.

Exit criteria:
- [ ] Meets predefined risk and operational reliability thresholds.

## Phase 11 - Multi-Strategy Runtime Integration (Target v2.0)
Objective:
- [ ] Evolve from single-strategy deployment to multi-strategy platform runtime.

Tasks:
- [ ] Add at least one additional plugin (example adaptive-momentum-10-15).
- [ ] Implement strategy registry with per-strategy enable or disable.
- [ ] Implement strategy symbol scopes and profile overrides.
- [ ] Add strategy isolation controls.
- [ ] Add strategy-level attribution across all reports.

Deliverables:
- [ ] Multi-strategy execution build with strategy-level observability.

Exit criteria:
- [ ] Multiple strategies run concurrently under shared risk controls without collisions.

## Phase 12 - Shared Portfolio Allocator and Model Promotion Automation (Target v2.0)
Objective:
- [ ] Centralize cross-strategy capital allocation and automate model promotion.

Tasks:
- [ ] Build allocator enforcing total risk budget across strategies.
- [ ] Add budget assignment by strategy profile and recent performance.
- [ ] Implement model promotion workflow candidate -> validation -> staged -> active.
- [ ] Add one-step rollback to prior model version.

Deliverables:
- [ ] Cross-strategy risk allocator.
- [ ] Model promotion pipeline.

Exit criteria:
- [ ] Strategy additions and model upgrades require no manual execution-path code edits.

## Phase 13 - Managed Azure Migration and Environment Promotion (Target v2.1)
Objective:
- [ ] Migrate from single VM prototype to managed-cloud deployment patterns.

Tasks:
- [ ] Migrate PostgreSQL to managed service and validate migration.
- [ ] Validate backups for managed PostgreSQL.
- [ ] Containerize backend services.
- [ ] Containerize training services.
- [ ] Define environment configurations.
- [ ] Implement CI/CD promotion gates dev -> demo -> pilot.
- [ ] Add SLO dashboards.
- [ ] Automate backup and restore drills.

Deliverables:
- [ ] Managed-cloud deployment baseline with promotion controls.

Exit criteria:
- [ ] Deployment recoverable from backup.
- [ ] Promotion between environments works without manual reconfiguration.

## Sprint Tracker (First 6 Sprints)
Sprint 1:
- [ ] Repo scaffolding.
- [ ] Backend skeleton and health endpoint.
- [ ] Prisma init and first migration.

Sprint 2:
- [ ] EA base indicators and completed-candle engine.
- [ ] Rule-based entry and exit implementation.
- [ ] Unit tests for breakout and MA logic.

Sprint 3:
- [ ] /signal and strategy plugin registry.
- [ ] Logging endpoints and decision IDs.
- [ ] DB writes for signals, trades, rejections.

Sprint 4:
- [ ] Risk engine rules and kill-switches.
- [ ] EA local safety validations.
- [ ] Integration tests for veto paths.

Sprint 5:
- [ ] Baseline multi-symbol backtest.
- [ ] Validation report generation.
- [ ] Training dataset export pipeline.

Sprint 6:
- [ ] First ML training run and walk-forward report.
- [ ] ONNX export and backend inference wiring.
- [ ] AI threshold decisions in /signal.

## Documentation Workstream Tracker
Based on documentation_checklist.md:
- [ ] DOC-01 Requirements Traceability Matrix complete and verified.
- [ ] DOC-02 API Contract Specification complete and verified.
- [ ] DOC-03 Data Dictionary and Lineage complete and verified.
- [ ] DOC-04 Model Governance Standard complete and verified.
- [ ] DOC-05 Backtest and Validation Methodology complete and verified.
- [ ] DOC-06 Security and Access Control complete and verified.
- [ ] DOC-07 Incident and Operations Runbooks complete and verified.
- [ ] DOC-08 SLO, SLI, and Alerting Matrix complete and verified.
- [ ] DOC-09 Release and Change Management Guide complete and verified.
- [ ] DOC-10 Frontend Implementation Addendum complete and verified.
- [ ] DOC-11 Environment and Deployment Topology complete and verified.
- [ ] DOC-12 Documentation Governance Standard complete and verified.

## Risks to Track Continuously
- [ ] Look-ahead bias from candle indexing mistakes monitored.
- [ ] Feature mismatch between Python and runtime monitored.
- [ ] Spread and slippage assumptions validated periodically.
- [ ] Overfitting controls monitored continuously.
- [ ] Broker symbol specification sizing risks monitored.

## Change Log
- 2026-05-20: Initial runbook created with full phase and documentation trackers.
