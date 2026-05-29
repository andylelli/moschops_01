# Implementation Roadmap — Trading Tools Future Design Palette

**Document:** `docs/11-trading-tools/implementation-roadmap.md`  
**Version:** 1.0  
**Status:** Draft  
**Source palette:** `docs/11-trading-tools/future-design-palette.md` v1.1  
**Last updated:** 2025-01

---

## Progress Tracker

| Phase | Name | Status | Items done / total | Notes |
|---|---|---|---|---|
| 0 | Foundation Hardening | Not started | 0 / 12 | — |
| 1 | Feature Library Expansion | Not started | 0 / 12 | — |
| 2 | Label and CV Improvements | Not started | 0 / 7 | — |
| 3 | Regime Intelligence | Not started | 0 / 8 | — |
| 4 | Advanced ML Stack and Pipeline Automation | Not started | 0 / 13 | — |
| 5 | Research Frontier | Not started | 0 / 8 | — |

**How to use.** Update `Status` to `In progress` when work begins and `Complete` when all test criteria pass. Increment `Items done` as individual deliverables are checked off. Add brief notes for blockers, partial completions, or deferred items.

---

## Purpose

This roadmap translates the Future Design Palette into a phased, prioritised build plan. Each phase has a clear objective, a deliverables table, and test criteria. Dependencies flow from earlier to later phases — do not start a phase until its upstream dependencies are in place.

The roadmap covers 6 phases spanning the full palette. Each phase assumes one developer with access to the current stack (Fastify/Node.js backend, Python venv, Prisma/PostgreSQL, ONNX, MT5 EA).

---

## Phase 0 — Foundation Hardening (Weeks 0–4)

### Objective

Make the existing pipeline production-safe before adding any new features. All items in this phase are low-effort, high-confidence improvements that remove the most dangerous gaps in the current stack.

### Deliverables

| Item | Section | Effort | Expected impact | Dependency |
|---|---|---|---|---|
| Bar quality validation pipeline | 14 | Low | Eliminates stale/inconsistent bars from training | None |
| Feature stationarity reporting (ADF / KPSS) | 14 | Low | Detects non-stationary features before training | None |
| Winsorisation of feature outliers (1st/99th pct) | 14 | Low | Removes extreme values that destabilise models | None |
| Feature correlation audit (flag \|r\| > 0.85) | 14 | Low | Detects near-duplicate features | None |
| Missing data policy enforcement | 14 | Low | Prevents silent NaN propagation | None |
| Monte Carlo permutation test | 8 | Low | Minimum significance check on holdout | None |
| Deflated Sharpe Ratio (DSR) gate | 8 / 12 | Low | Corrects for multiple-testing in strategy selection | None |
| MAE / MFE / G-ratio in gate evaluation | 12 | Low | Rich exit quality measurement | None |
| Calmar + Sortino in gate evaluation | 12 | Low | Drawdown-adjusted return metrics | None |
| Overnight swap cost model | 10 | Low | Correct cost modelling for positions held overnight | None |
| Wire XGBoost and LightGBM to CLI | 2 | Low | Unlocks two well-supported boosting estimators | None |
| Model performance monitoring alerts | 17 | Low | Early warning for live model degradation | Backend running |

### Test criteria

- Training run produces a gate evaluation JSON containing `dsr`, `mae`, `mfe`, `g_ratio`, `calmar`, `sortino` fields.
- A run on shuffled labels fails the Monte Carlo permutation test (p > 0.05) while a real run passes.
- A training run on a dataset containing a 0-volume bar, stale bar, and a NaN feature raises `DATA_QUALITY_FAILURE` before fitting.
- XGBoost and LightGBM estimators produce ONNX artefacts that load and infer without error.
- Live monitoring fires an alert (log-level WARN) when simulated win-rate deviation exceeds threshold.

---

## Phase 1 — Feature Library Expansion (Weeks 4–10)

### Objective

Build a comprehensive feature library covering the most reliable technical and structural signals. All items are well-understood, low-implementation-risk improvements.

### Deliverables

| Item | Section | Effort | Expected impact | Dependency |
|---|---|---|---|---|
| RSI, MACD, Bollinger Band width | 3.1 / 3.2 | Low | Core momentum + trend strength | Phase 0 data quality |
| ADX strength feature / filter | 3.1 / 5 | Low | Trend quality signal | — |
| Squeeze Momentum (KB squeeze) | 3.1 | Low | Consolidation-to-expansion signal | — |
| KAMA and KAMA slope | 3.1 | Low | Adaptive noise-filtering MA | — |
| Linear regression slope + R-squared | 3.1 | Low | Directional strength + fit quality | — |
| Supertrend direction flag | 3.1 | Low | Binary trend filter | — |
| Volume ratio + volume momentum | 3.3 | Low | Confirms breakout strength | — |
| Day of week + session calendar | 3.5 | Low | Captures intraday/weekly seasonality | — |
| Hurst exponent | 3.7 | Low | Trending vs. mean-reverting regime signal | — |
| CUSUM filter statistic | 3.7 | Low | Detects structural mean shifts as feature | — |
| Efficiency ratio | 6 | Low | Directional efficiency of recent price path | — |
| Ichimoku Cloud features | 3.1 | Low | TK cross, cloud position, chikou confirmation | Phase 0 data quality |

### Test criteria

- Each new feature computes without NaN for a full 4-year EURUSD D1 bar dataset.
- ADF test on every new feature passes stationarity gate (p ≤ 0.05) or transformation is applied and documented.
- Walk-forward backtest shows no drop in Sharpe compared to baseline when adding Phase 1 features (model should absorb or discard uninformative features).
- Feature correlation audit does not flag more than 3 new pairs as near-duplicates (\|r\| > 0.85).

---

## Phase 2 — Label and CV Improvements (Weeks 10–16)

### Objective

Improve the quality of the learning signal and the rigour of out-of-sample evaluation. These changes directly reduce backtest overfitting and improve the validity of gate decisions.

### Deliverables

| Item | Section | Effort | Expected impact | Dependency |
|---|---|---|---|---|
| Triple barrier labeling | 4 | Medium | More realistic trade outcome labels than fixed-horizon | Phase 0 |
| CUSUM-filtered sampling | 4 | Medium | Removes non-informative flat-market samples from training | Phase 0 bar quality |
| Fractionally differentiated features | 3.7 / 4 | Medium | Stationarity with memory preservation | Phase 0 stationarity gate |
| Expanding window CV option | 8 | Low | Reduces look-ahead bias in early folds | Phase 1 features |
| Structural break tests before windows | 6 | Medium | Validates window homogeneity before training | Phase 1 |
| Probability of Backtest Overfitting (PBO) | 8 | Medium | Requires CPCV; quantifies probability result is overfit | CPCV below |
| Combinatorial Purged CV (CPCV) | 8 | High | Gold-standard out-of-sample CV | Phase 1 complete |

### Test criteria

- Triple barrier labeling applied to EURUSD D1 produces labels where at least 15% of bars are labelled as stop-loss outcomes (non-trivial classification).
- CUSUM-filtered training set is smaller than the full training set by at least 20% (flat-market samples are removed).
- Fractional differentiation pipeline preserves at least 80% autocorrelation memory while passing the ADF stationarity test.
- PBO score < 0.5 on a genuine strategy; PBO > 0.5 on a deliberately overfit (look-ahead) strategy.
- CPCV produces a larger number of test folds than standard WF for the same dataset.

---

## Phase 3 — Regime Intelligence (Weeks 16–24)

### Objective

Add dynamic regime awareness to features, threshold selection, and training. This allows the pipeline to adapt to changing market states rather than fitting a single global model.

### Deliverables

| Item | Section | Effort | Expected impact | Dependency |
|---|---|---|---|---|
| HMM regime detection as feature | 6 | Medium | Principled latent-state market classification | Phase 1 features |
| GARCH / EGARCH volatility regime | 6 | Medium | Forward-looking vol forecasting for sizing | Phase 1 |
| K-means clustering regime | 6 | Medium | Unsupervised regime labelling for experiments | Phase 1 |
| Adaptive thresholds (by regime) | 7 | Medium | Higher threshold in choppy regime | Phase 3 regime features |
| Meta-labeling | 4 | Medium | Secondary classifier confirms primary signal | Phase 2 labels |
| BOCPD changepoint detection | 6 | Medium | Online regime change detection | Phase 2 |
| Regime-conditional training windows | 9 | Medium | Train separate models per regime | Phase 3 regime features |
| Regime-conditional gate evaluation | 12 | Low | Split gate metrics by detected regime | Phase 3 regime features |

### Test criteria

- HMM trained on D1 EURUSD assigns at least 2 distinct persistent regime states across a 4-year window.
- Adaptive threshold produces a different threshold for a low-ADX period vs. a high-ADX period in a holdout evaluation.
- Meta-labeled model produces lower false-positive rate than primary model alone on holdout data.
- BOCPD changepoint events correlate with known macro events (COVID March 2020, Fed rate hike periods) at rate > 60%.

---

## Phase 4 — Advanced ML Stack and Pipeline Automation (Weeks 24–36)

### Objective

Introduce ensemble models, portfolio-level risk management, automated retraining, and live infrastructure upgrades. These changes require a solid foundation from Phases 0–3.

### Deliverables

| Item | Section | Effort | Expected impact | Dependency |
|---|---|---|---|---|
| Soft-voting ensemble (logreg + XGB + RF) | 2 | Medium | Reduces variance; often +5–10% Sharpe improvement | Phase 0 XGB/LGBM |
| Volatility-scaled position sizing | 11 | Medium | Dynamic risk per trade | Phase 3 GARCH regime |
| Equity-curve risk scaling | 16 | Medium | Drawdown-responsive bet sizing | Phase 3 complete |
| Portfolio-level drawdown circuit breaker | 16 | Low | Hard stop on total capital loss | Phase 3 complete |
| Feature store (Postgres cache) | 13 | Medium | Single source of truth for features; parity assurance | Phase 2 features stable |
| Concept drift detection (PSI) | 13 | Medium | Alerts when live feature distribution shifts | Feature store |
| Shadow trading framework | 13 | Medium | Paper-trade new model before promotion | Backend infra |
| Variable spread simulation | 15 | Medium | Realistic transaction cost modelling | Phase 0 cost model |
| Regime-conditional P&L attribution | 15 | Medium | Understand which regimes drive P&L | Phase 3 regimes |
| Live feature parity check | 17 | Medium | Detect backend vs. training pipeline drift | Feature store |
| EA health monitoring extensions | 17 | Low | Broader production health coverage | Live MT5 connection |
| Trade journal and post-trade analysis | 17 | Medium | Systematic learning from live trade outcomes | Phase 0 MAE/MFE |
| Automated retraining pipeline | 13 | High | Reduces human effort for scheduled retraining | Feature store + shadow trading |

### Test criteria

- Ensemble model produces calibrated probabilities with lower Brier score than any individual constituent on holdout data.
- PSI > 0.2 alert fires correctly when feature distribution is deliberately shifted in a test.
- Shadow trade runs for a minimum of 20 signals before any promotion is allowed.
- Variable spread simulation produces 5–15% higher transaction cost estimate than fixed spread on D1 EURUSD across 4 years.
- Automated retraining runs end-to-end without human intervention and sets model to `pending_approval` on success.

---

## Phase 5 — Research Frontier (Weeks 36+)

### Objective

Explore the highest-complexity, highest-risk items. These have large potential upside but require careful experimentation, and their production use must be gated by Phase 0–4 infrastructure.

### Deliverables

| Item | Section | Effort | Expected impact | Dependency |
|---|---|---|---|---|
| Deep learning — LSTM sequence model | 2 | High | Learns temporal dependencies natively | Phase 4 feature store |
| Deep learning — TCN (Temporal CNN) | 2 | High | Faster training than LSTM for long sequences | Phase 4 feature store |
| Temporal Fusion Transformer (TFT) | 2 | High | State-of-the-art multi-horizon time-series | Phase 5 LSTM baseline |
| COT / retail sentiment data | 3.8 | High | Macro positioning data as features | Phase 4 feature store |
| Kelly-optimal portfolio weights | 16 | High | Theoretically optimal capital allocation | Phase 4 ensemble models |
| Synthetic data augmentation (GBM/VAR) | 15 | High | Supplement scarce historical data | Phase 4 complete |
| Online learning / incremental retraining | 13 | High | Real-time model updates without full retraining | Phase 4 automated retraining |
| Bayesian model (GP / Bayesian regression) | 2 | High | Native uncertainty quantification | Phase 3 complete |

### Test criteria

- LSTM / TCN model must beat the Phase 2 ensemble baseline on the same holdout period before being considered for production.
- COT features must pass ADF stationarity test and show non-trivial correlation (> 0.05) with D1 trade labels.
- Kelly-optimal allocation must not exceed 2x the position size of the current fixed sizing in any single strategy.
- Online learning update must not degrade model calibration (Brier score must remain within 10% of the full-retrain baseline).

---

## Cross-Phase Risk Controls

The following constraints apply across all phases:

| Control | Rule |
|---|---|
| Holdout integrity | The final 20% of each dataset is a holdout. No feature engineering decisions are made on holdout data. |
| Gate requirements | Every model must pass: Sharpe > 0.8, Profit Factor > 1.3, Max DD < 20%, DSR > 0.5, PF p-value < 0.05, Win Rate > 50%. |
| Human approval gate | No live model swap occurs without human sign-off regardless of automated test outcomes. |
| Recipe traceability | Every experiment must reference a signed-off recipe in `docs/10-trading-systems/recipes/`. |
| Reversibility | Every deployed model is versioned. Rollback to previous model must be achievable in under 5 minutes. |
| Documentation sync | When a palette item is implemented, mark it as `Implemented` in the Priority Matrix of `future-design-palette.md`. |

---

## Milestone Summary

| Phase | Scope | Weeks | Key outputs |
|---|---|---|---|
| 0 | Foundation hardening | 0–4 | Data quality pipeline, expanded gate metrics, XGB/LGBM wiring |
| 1 | Feature library | 4–10 | 12 new features (momentum, volume, adaptive MA, structural) |
| 2 | Label + CV | 10–16 | Triple barrier, CUSUM sampling, CPCV, PBO |
| 3 | Regime intelligence | 16–24 | HMM, GARCH, K-means, adaptive thresholds, meta-labeling |
| 4 | Advanced ML + automation | 24–36 | Ensemble, feature store, shadow trading, automated retraining |
| 5 | Research frontier | 36+ | Deep learning, COT data, Kelly sizing, online learning |
