# Recipe: Event-Aware Trend Continuation

System ID: TS-004
Recipe number: 04
Recipe status: Signed-off
Created: 2026-05-28
Owner: Trading + AI Engineering
Palette version: strategy-design-palette.md v1.0

---

## 1. Strategy Concept

### Thesis

Scheduled macro events (NFP, CPI, FOMC) produce sharp volatility spikes that often resolve in the direction of the prevailing trend once abnormal volatility normalises. A machine-learning classifier can identify high-quality post-event trend continuation setups by distinguishing genuine breakouts from noise-driven fakeouts using volatility regime, momentum, and trend-strength features.

### Market inefficiency targeted

Post-event volatility mean reversion combined with trend momentum persistence. After a news-driven spike, market participants who were stopped out or margin-constrained during the event gradually re-enter in the pre-event trend direction, creating a continuation window of 20–40 hours (5–10 H4 bars).

### Why this is not a duplicate of an existing TS

| Comparison | TS-001 | TS-002 | TS-003 | TS-004 |
|---|---|---|---|---|
| Entry trigger | Breakout + trend filter | Mean-reversion after vol spike | Cross-asset momentum | Post-event trend continuation |
| Timeframe | D1 | H1/H4 | H4 | H4 |
| AI role | Entry quality filter | Entry quality filter | Ranking and allocation | Event-risk gating + sizing |
| Regime handling | None explicit | Vol spike gate | None | Vol normalization window |

TS-004 is differentiated by explicitly targeting the post-event continuation window and using volatility normalisation as the entry qualifier rather than entry suppressor.

### Expected regime profile

| Condition | Expected performance |
|---|---|
| Low vol trending (quiet trends) | Neutral — few triggering events |
| High vol trending (post-event continuation) | Best performance — core thesis |
| Range-bound / choppy | Poor — trend filter blocks entries |
| Crisis / structural break | Poor — sustained elevated vol blocks entries |

---

## 2. Design Palette Selections

### 2.1 Instrument and Timeframe

| Field | Selection |
|---|---|
| Primary instrument | EURUSD |
| Timeframe | H4 |
| Additional instruments | N/A (initial deployment) |

**Rationale:** EURUSD is the only fully proven end-to-end pipeline. H4 is selected over D1 because the post-event continuation window is typically 20–40 hours; D1 bars average over the event noise rather than capturing the normalisation window. H4 provides ~60–80 realistic trades per year versus ~30–40 on D1.

**Data availability confirmed?** Yes — FMP OHLCV endpoint supports H4.

**Expected trade frequency:** ~70 trades / year (higher selectivity due to event-gating)

---

### 2.2 Model Estimator

| Field | Selection |
|---|---|
| Estimator | xgb |
| Calibration method | isotonic |
| Code change required? | No — xgb is wired in train_walk_forward.py (P1) |

**Rationale:** XGBoost handles non-linear interactions between volatility_regime, trend_strength, and momentum features more effectively than logistic regression. Isotonic calibration is preferred for threshold selection quality; it is better calibrated than Platt on skewed classification problems.

---

### 2.3 Feature Set

**Default features:**

| Feature | Include? | Notes |
|---|---|---|
| ret1 to ret5 (lagged log returns) | Yes | Capture short momentum around event |
| ret10 (10-bar log return) | Yes | Capture pre-event trend direction |
| volatility20 | Yes | Current vol level |
| volatility100 | Yes | Background vol baseline |
| volatility_regime (vol20/vol100) | Yes | Core feature — detects vol normalization |
| above_sma (close > SMA200) | Yes | Trend direction gate |
| trend_strength (20-bar return / ATR20) | Yes | Post-event trend quality |
| breakout_distance | Yes | Distance from pre-event levels |
| atr_normalised | Yes | Normalised current vol context |

**Additional features (from current palette):**

| Feature | Type | Code change? | Rationale |
|---|---|---|---|
| rsi14 | Indicator | No — training/features.py (P1) | Overbought/oversold after event spike |
| adx | Indicator | No — training/features.py (P1) | Trend strength confirmation |
| efficiency_ratio | Indicator | No — training/features.py (P1) | Distinguishes trending vs. choppy post-event |
| macd_signal | Indicator | No — training/features.py (P1) | Trend confirmation crossover |

**Feature schema version that will result:** v2 (using P1 features.py build_feature_set)

---

### 2.4 Label Objective

| Field | Selection |
|---|---|
| Label mode | edge |
| Horizon (bars) | 10 |
| Minimum edge threshold (bps) | 8 |
| Class balance handling | class_weight='balanced' |

**Rationale:** Edge labels at 8 bps (minimum ~0.0008 H4 move) filter out low-conviction setups and focus the classifier on meaningful post-event moves. 10-bar horizon = ~40 hours, matching the expected post-event continuation window. Balanced class weights prevent the classifier from being dominated by the majority (no-edge) class.

**Expected label frequency:** ~25–35% positive bars (8 bps threshold at H4 is achievable but selective)

---

### 2.5 Signal Variant

| Field | Selection |
|---|---|
| Variant | trend-follow |
| Regime gate active? | Yes |
| Regime gate type | volatility_regime threshold |

**Variant-specific knobs:**

| Knob | Value | Notes |
|---|---|---|
| trend_follow_sma_window | 200 | H4 SMA200 ≈ 5.5 months of trend |
| trend_follow_min_strength | 0.3 | Minimum trend_strength to qualify entry |
| regime_gate_min_ratio | 0.80 | Block when vol is unusually compressed |
| regime_gate_max_ratio | 2.00 | Block when vol is still elevated |

**Rationale:** The trend-follow variant ensures entries are aligned with the macro trend direction. The regime gate specifically targets the post-event normalisation window: vol_regime < 0.80 means no event occurred; vol_regime > 2.00 means the event is still ongoing.

---

### 2.6 Regime Gate

| Field | Selection |
|---|---|
| Gate metric | volatility_regime |
| Lower bound | 0.80 |
| Upper bound | 2.00 |
| Gate action | block-all |

**Rationale:** Entries are only taken in the vol_regime band [0.80, 2.00]. Below 0.80 — market is too quiet; no event catalyst to drive continuation. Above 2.00 — event volatility still active; spread widening and false breakout risk is elevated. The gate blocks-all (no log-only mode) because entries outside the window have no edge per the thesis.

---

### 2.7 Probability Threshold Strategy

| Field | Selection |
|---|---|
| Threshold selection method | constrained-optimisation |
| Minimum trade count constraint | 60 |
| Maximum drawdown constraint | 20% |
| Probability floor (hard minimum) | 0.52 |

**Rationale:** H4 with event gating generates fewer signals than baseline; the 60-trade floor prevents over-filtering. The 20% DD ceiling is looser than TS-001 (12%) to account for H4 intraday noise; 0.52 floor prevents degenerate low-confidence entries.

---

### 2.8 Walk-Forward CV Design

| Field | Selection |
|---|---|
| Number of folds | 5 |
| Embargo (bars) | 5 |
| Horizon (bars per test fold) | 8 |
| Window type | expanding |

**Rationale:** 5 folds with 5-bar embargo (20 hours) prevents leakage from H4 serial correlation and overlapping feature windows. Expanding window uses all available history in each training fold. 8-bar test horizon balances fold granularity with sufficient test sample size.

---

### 2.9 Training Window

| Field | Selection |
|---|---|
| Training start date | 2012-01-01 |
| Dev/test split date | 2022-01-01 |
| Holdout start date | 2023-01-01 |
| Holdout end date | 2024-12-31 |
| Minimum training bars | ~17,500 H4 bars (10y) |

**Rationale:** 2012–2021 provides 10 years of diverse macro regimes (Eurozone crisis, post-QE normalisation, COVID disruption, 2021 reflation). Dev/test split at 2022-01-01 captures the rate-hike macro shift as dev/test data. 2023–2024 holdout is 2 full years; acceptance only; never used for tuning. 2024-12-31 end provides a clean holdout boundary.

---

### 2.10 Cost Model

| Field | Selection |
|---|---|
| Spread assumption (bps) | 2.5 |
| Commission assumption (bps) | 1.0 |
| Slippage assumption (bps) | 0.5 |
| Overnight swap assumption (bps/night) | 0.5 |
| Stress test multiplier | 2× spread, 3× slippage |

**Rationale:** H4 positions are held ~40 hours on average (~2 overnight rolls). 2.5 bps spread is slightly above the D1 conservative assumption to account for potential news-time spread widening. The 2×/3× stress matrix simulates adverse execution during event windows where spread can triple.

---

### 2.11 Promotion Gate Thresholds

| Gate | Metric | Threshold |
|---|---|---|
| Minimum trades (holdout) | Trade count | 60 |
| Profit factor floor | PF | ≥ 1.25 |
| Maximum drawdown ceiling | Max DD % | ≤ 20% |
| Expectancy floor (per trade) | bps after cost | > 5 bps |
| Fold consistency floor | % folds profitable | ≥ 60% |
| Sortino ratio floor | Sortino | ≥ 0.5 |
| Calmar ratio floor | Calmar | N/A |

**Rationale:** PF ≥ 1.25 is consistent with TS-001 and TS-003 discovery targets. DD ceiling of 20% is higher than TS-001 (12%) because H4 intraday exposure creates larger interim swings. 60% fold consistency is the minimum to avoid regime-dependent overfitting.

---

## 3. Signal Knob Summary

```
python run_historical_split.py \
  --symbol          EURUSD \
  --timeframe       H4 \
  --label-mode      edge \
  --min-edge-bps    8 \
  --horizon         10 \
  --signal-variant  trend-follow \
  --model           xgb \
  --folds           5 \
  --embargo         5 \
  --spread-bps      2.5 \
  --commission-bps  1.0 \
  --slippage-bps    0.5 \
  --min-trades      60 \
  --max-dd          0.20
```

Additional flags for non-default features (when feature pipeline is invoked):
```
--feature-set     p1_extended
--regime-gate-min 0.80
--regime-gate-max 2.00
--trend-sma       200
--min-strength    0.30
```

---

## 4. Experiment Plan

### Primary hypothesis

A trend-following XGBoost model on EURUSD H4 with volatility regime gating (vol_regime in [0.80, 2.00]) and edge labeling (8 bps, 10-bar horizon) will produce a profit factor ≥ 1.25 and a max drawdown ≤ 20% after realistic costs on the 2023–2024 holdout window.

### Success definition

Holdout shows: PF ≥ 1.25, max DD ≤ 20%, ≥ 60 trades, expectancy > 5 bps after costs, and ≥ 60% of CV folds are profitable. Strategy is differentiated from TS-001 by superior H4 performance.

### Failure definition

Any of: PF < 1.10, max DD > 25%, fewer than 40 holdout trades, or ≥ 3 of 5 folds unprofitable. If the regime gate blocks too many entries (< 40 trades), widen the gate bounds and re-evaluate.

### Proposed lab windows

| Phase | Train window | Test window | Purpose |
|---|---|---|---|
| EXP-001 baseline | 2012-01-01 – 2021-12-31 | 2022-01-01 – 2022-12-31 | Establish XGBoost baseline behaviour |
| EXP-002 regime gate | 2012-01-01 – 2021-12-31 | 2022-01-01 – 2022-12-31 | Evaluate vol regime gate impact |
| EXP-003 feature set | 2012-01-01 – 2021-12-31 | 2022-01-01 – 2022-12-31 | Add P1 extended features |
| Holdout (final) | 2012-01-01 – 2022-12-31 | 2023-01-01 – 2024-12-31 | Acceptance only |

### Ordered experiment sequence

1. EXP-001: XGBoost baseline with default features, no regime gate, direction labels, 5 folds.
2. EXP-002: Switch to edge labels (8 bps, 10-bar), same config — measure selectivity impact.
3. EXP-003: Add vol regime gate [0.80, 2.00] — measure trade count and quality change.
4. EXP-004: Add P1 extended features (RSI, ADX, efficiency ratio, MACD) — measure AUC lift.
5. EXP-005: Stress cost matrix (2× spread, 3× slippage) on best dev config.
6. Final holdout run: lock best dev config, execute once on 2023–2024. No re-runs.

### Stopping criteria

Stop experimenting and retire if: after 6 experiments the dev-window PF does not exceed 1.15 with max DD ≤ 25%. Stop experimenting and proceed to holdout if: a dev-window config achieves PF ≥ 1.30, max DD ≤ 18%, ≥ 60 trades, 80% fold consistency.

---

## 5. Risk and Safety Constraints

### Hard position limits

| Parameter | Limit |
|---|---|
| Max risk per trade (% of account) | 0.5% |
| Max open trades simultaneously | 1 |
| Max correlated exposure | N/A — single instrument |

### Stop loss policy

| Field | Value |
|---|---|
| Stop type | ATR multiple |
| Stop distance | 1.5 × ATR20 from entry |
| Trailing stop? | No |

### Capital constraints

| Field | Value |
|---|---|
| Minimum account size for this strategy | $5,000 |
| Target lot size | Micro (0.01–0.10) |
| Max drawdown tolerance before system pause | 15% from peak |

### Operational dependencies

| Dependency | Required? | Fallback if unavailable |
|---|---|---|
| Backend API (localhost:3000) | Yes | Fail-closed — EA does not trade |
| FMP historical data feed | Yes (training only) | Re-run blocked until restored |
| MT5 terminal | Yes (live) | N/A |
| H4 bar provider | Yes | Fail-closed if H4 bars unavailable |

---

## 6. What This Recipe Drives

| Recipe section | Drives TS document(s) |
|---|---|
| 1. Strategy concept | 00_system_charter, 01_strategy_spec, 17_strategy_how_it_works |
| 2.1 Instrument / timeframe | 00_system_charter, 02_instruments_execution, 03_data_contract |
| 2.2 Model estimator | 05_model_training |
| 2.3 Feature set | 03_data_contract, 04_feature_schema |
| 2.4 Label objective | 01_strategy_spec, 05_model_training |
| 2.5 Signal variant | 01_strategy_spec |
| 2.6 Regime gate | 01_strategy_spec |
| 2.7 Threshold strategy | 01_strategy_spec, 08_promotion_gates |
| 2.8 CV design | 05_model_training, 06_validation_protocol |
| 2.9 Training window | 05_model_training, 06_validation_protocol |
| 2.10 Cost model | 06_validation_protocol, 08_promotion_gates |
| 2.11 Gate thresholds | 08_promotion_gates |
| 3. Signal knob summary | 05_model_training, 06_validation_protocol, 11_experiment_log |
| 4. Experiment plan | 11_experiment_log, 06_validation_protocol |
| 5. Risk and safety | 07_risk_safety, 02_instruments_execution |

---

## 7. Open Questions / Future Extensions

1. **Multi-timeframe confirmation** (P2 — implemented): Add H4 + D1 HTF trend confirmation using `training/multiframe.py`. Deferred to EXP-006.
2. **BOCPD changepoint feature** (P3 — implemented): Include `bocpd_cp_prob` as an event-detection feature. High cp_prob near entry confirms a structural shift. Deferred to EXP-007.
3. **Ichimoku cloud filter** (P3 — implemented): Add cloud_bullish as an additional trend confirmation layer. Deferred to EXP-008.
4. **Shadow trading** (P3 — implemented): Run ShadowTrader in parallel from EXP-001 to track live signal quality without capital risk.
5. **Circuit breaker** (P3 — implemented): Wire CircuitBreaker with max_daily_loss_pct=0.015, max_consecutive_losses=4 into EA parameter set before any micro-live deployment.
6. **Variable spread simulation** (P3 — implemented): Apply spread_sim.py in EXP-005 stress testing with news_multiplier=4.0 at event bar indices.
7. **COT / retail sentiment data** (P4 — not yet implemented): Adding commitment-of-traders positioning would directly inform the post-event thesis.

---

## Sign-off

| Field | Value |
|---|---|
| Signed off by | Trading + AI Engineering |
| Sign-off date | 2026-05-28 |
| Recipe status | Signed-off |
| Next step | Phase 2 — generate TS-004 folder |
