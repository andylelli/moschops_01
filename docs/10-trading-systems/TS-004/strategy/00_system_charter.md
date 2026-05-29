# 00 System Charter

System ID: TS-004
Version: 1.0
Last updated: 2026-05-28

## Mission

Build and operate a machine-learning trading strategy that captures post-event trend continuation opportunities on EURUSD H4, using volatility regime gating to identify the normalisation window after major macro events.

## Business objective

Generate a net positive return stream on EURUSD H4 with a profit factor ≥ 1.25 and maximum drawdown ≤ 20% after realistic transaction costs, measured over a two-year holdout period (2023–2024).

## Scope

### In scope

- EURUSD H4 signal generation
- XGBoost binary classifier with edge labels (8 bps minimum)
- Volatility regime gate (vol20/vol100 ratio)
- Walk-forward validation, 5 folds, expanding window
- FMP OHLCV data pipeline (existing infrastructure)
- Prometheus/Grafana monitoring (existing backend)
- MQL5 EA deployment via existing template

### Out of scope

- Multi-instrument deployment (initial version)
- Real-time news feed integration
- Options or non-FX instruments
- Automated circuit breaker triggering in EA (monitoring only in v1)
- Intraday (M15, M30) timeframes

## Non-negotiable principles

1. Holdout data (2023-01-01 – 2024-12-31) must not be viewed or used until the single locked holdout run after dev-phase completion.
2. Promotion requires evidence completion on all five gates (A–E) in `08_promotion_gates.md`.
3. All experiment changes must be logged in `11_experiment_log.md` before the next run.
4. One config change per experiment. No bundling of multiple changes into a single run.
5. Fail-closed: if the backend API is unavailable, the EA must not trade.
6. Risk limits in `07_risk_safety.md` are hard limits; no overrides without Change Control process.

## Success criteria

| Criterion | Target | Measured in |
|---|---|---|
| Holdout profit factor | ≥ 1.25 | `08_promotion_gates.md` Gate C |
| Holdout max drawdown | ≤ 20% | `08_promotion_gates.md` Gate C |
| Holdout trade count | ≥ 60 | `08_promotion_gates.md` Gate C |
| Holdout expectancy | > 5 bps after costs | `08_promotion_gates.md` Gate C |
| CV fold consistency | ≥ 60% folds profitable | `06_validation_protocol.md` |
| Full data lineage | No leakage flags | `13_audit_traceability.md` Gate A |
| Operational readiness | All ops checks pass | `09_live_operations.md` Gate D |

## Failure criteria

| Criterion | Failure threshold | Action |
|---|---|---|
| Holdout profit factor | < 1.10 | Retire TS-004; review thesis |
| Holdout max drawdown | > 25% | Reject; tighten stop loss parameters |
| Holdout trades | < 40 | Widen regime gate bounds; re-experiment |
| Any data leakage detected | Any confirmed leak | Invalidate all runs; reprocess data |
| Consecutive unprofitable folds | 4 of 5 folds | Retire thesis; review regime gating |

## Dependencies

| Dependency | Type | Owner | Risk if unavailable |
|---|---|---|---|
| FMP API key | External | Trading team | Training blocked |
| PostgreSQL DB (via Prisma) | Internal | Backend | Signal logging fails |
| ONNX backend inference (port 3000) | Internal | Backend | EA fails closed |
| training/run_historical_split.py | Internal | AI Engineering | Experiments blocked |
| training/features.py (P1) | Internal | AI Engineering | Feature build fails |
| MetaTrader 5 + EA template | Internal | Trading team | Live deployment blocked |
