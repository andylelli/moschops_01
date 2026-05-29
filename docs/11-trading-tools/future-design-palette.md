# Future Design Palette

Version: 1.1  
Last updated: 2026-05-28  
Audience: Strategy developer, researcher

---

## Progress Tracker

| Priority tier | Description | Total items | Implemented | Remaining | Status |
|---|---|---|---|---|---|
| P1 | Low effort, high confidence — quick wins | 22 | 22 | 0 | Complete |
| P2 | Medium effort, high confidence | 17 | 17 | 0 | Complete |
| P3 | Medium effort, medium confidence | 10 | 10 | 0 | Complete |
| P4 | High effort or speculative | 4 | 0 | 4 | Not started |
| **Total** | | **53** | **49** | **4** | |

**P1 new files created:**
- `training/features.py` — RSI, MACD, Bollinger, ADX, Squeeze, Supertrend, KAMA, LR slope/R², Volume, Calendar, Hurst, CUSUM, Efficiency Ratio + `build_feature_set()` + `P1_FEATURE_NAMES`
- `training/quality.py` — bar quality validation, ADF stationarity check, winsorisation
- `training/metrics.py` — Sortino, Calmar, MAE/MFE/G-ratio, Deflated Sharpe Ratio, Monte Carlo permutation test, swap cost model, `evaluate_advanced_gates()`
- `training/monitoring.py` — `check_performance_drift()`, `write_monitoring_alert()`
- `backend/src/utils/indicators.ts` — TypeScript port of all 23 indicator functions + `computeP1Features()` + `P1_FEATURE_NAMES`
- `models/feature_schema_v2.json` — canonical 23-feature schema document

**P1 changes to existing files:**
- `training/train_walk_forward.py` — XGBoost/LightGBM in `build_model()` and `--model` CLI; SHAP lazy-import block in `build_diagnostics()`

**P2 new files created:**
- `training/labeling.py` — triple barrier labeling, CUSUM-filtered event sampling
- `training/frac_diff.py` — FFD fractional differencing, `find_min_ffd()`, `add_frac_diff_features()`
- `training/regimes.py` — HMM regime labeling (`hmm_regime_labels`, `hmm_regime_feature`), GARCH/EGARCH conditional vol (`garch_conditional_vol`, `garch_vol_feature`)
- `training/cv.py` — `ExpandingWindowCV` sklearn-compatible expanding-window splitter
- `training/meta_label.py` — `MetaLabeler` class (primary + secondary two-stage filter)
- `training/ensemble.py` — `build_soft_voting_ensemble()` (LogReg + XGBoost + RF)
- `training/sizing.py` — `vol_scaled_lot()`, `equity_curve_scalar()`, `apply_sizing()`
- `training/external_features.py` — `add_dxy_feature()`, `add_vix_feature()` (yfinance, lazy)
- `training/multiframe.py` — `resample_ohlcv()`, `add_htf_trend()`, `mtf_confirmed_signal()`
- `training/attribution.py` — `regime_pnl_attribution()`, `chow_test()`, `rolling_structural_breaks()`
- `training/audit.py` — `feature_correlation_matrix()`, `psi()`, `concept_drift_report()`
- `training/feature_store.py` — `FeatureStore` class (SQLAlchemy, PostgreSQL/SQLite, save/load/exists/delete)

**P3 new files created:**
- `training/bocpd.py` — Bayesian Online Changepoint Detection (Adams & MacKay 2007); `bocpd_changepoint_probs()`, `bocpd_changepoint_feature()`
- `training/cpcv.py` — Combinatorial Purged Cross-Validation + PBO; `CombPurgedCV`, `probability_of_backtest_overfitting()`
- `training/kmeans_regimes.py` — K-means clustering regime detection; `fit_kmeans_regimes()`, `kmeans_regime_feature()`, `predict_regime()`
- `training/ichimoku.py` — Ichimoku Cloud features; `add_ichimoku()` with tenkan/kijun/senkou/chikou + cloud_bullish / price_above_cloud / tk_cross_bull
- `training/spread_sim.py` — Variable spread simulation; `simulate_spread()`, `apply_spread_costs()`, `spread_cost_report()`
- `training/mc_simulation.py` — Monte Carlo equity curve simulation; `bootstrap_equity_curves()`, `mc_drawdown_stats()`, `mc_sharpe_distribution()`, `mc_var_cvar()`
- `training/shadow_trader.py` — `ShadowTrader` class; log/mark/report/save/load pattern for paper-trading signal quality tracking
- `training/portfolio_sizing.py` — Correlation-aware sizing; `correlation_adjusted_lots()`, `kelly_fraction()`, `half_kelly()`, `diversification_ratio()`, `equal_risk_contribution_weights()`
- `training/circuit_breaker.py` — `CircuitBreaker` class; daily-loss / drawdown / consecutive-loss thresholds with configurable cooldown
- `training/retrain_pipeline.py` — `RetrainConfig`, `should_retrain()`, `run_retrain()`, `load_current_metrics()`; full fetch→feature→QC→train→gate→promote cycle

*Update "Implemented" and "Remaining" counts as items are built. Full item list in the [Priority Matrix](#priority-matrix) at the end of this document.*

---

## Purpose

This document catalogues everything that could be added to each dimension of the strategy design palette — features, model architectures, label methods, regime detectors, signal variants, CV techniques, and more. Items are drawn from academic literature, industry practice, and open-source quant toolkits.

Each item is tagged with an **effort estimate** and a **confidence rating** for how likely it is to improve performance on an OHLCV-only FX/metal strategy:

- **Effort**: Low (single function / few lines) | Medium (new module or CLI flag) | High (architectural change)
- **Confidence**: High (well-evidenced for FX/daily timeframes) | Medium (mixed evidence) | Low (speculative / asset-class dependent)

Items marked **[QUICK WIN]** are low effort and high confidence — the most actionable candidates.

---

## Contents

1. [Instruments and Timeframes](#1-instruments-and-timeframes)
2. [Model Estimators](#2-model-estimators)
3. [Feature Set Additions](#3-feature-set-additions)
   - 3.1 Momentum and Trend Oscillators
   - 3.2 Volatility and Range Features
   - 3.3 Volume and Order Flow Proxies
   - 3.4 Market Structure Features
   - 3.5 Calendar and Seasonality Features
   - 3.6 Cross-Asset and Macro Features
   - 3.7 Higher-Order Statistical Features
   - 3.8 Alternative Data Features
4. [Label Objectives](#4-label-objectives)
5. [Signal Variants](#5-signal-variants)
6. [Regime Detection Methods](#6-regime-detection-methods)
7. [Probability Threshold Strategy](#7-probability-threshold-strategy)
8. [Walk-Forward CV Improvements](#8-walk-forward-cv-improvements)
9. [Training Window Design](#9-training-window-design)
10. [Cost Model Enhancements](#10-cost-model-enhancements)
11. [Position Sizing Models](#11-position-sizing-models)
12. [Promotion Gate Enhancements](#12-promotion-gate-enhancements)
13. [Pipeline and Architecture Additions](#13-pipeline-and-architecture-additions)
14. [Data Quality and Preprocessing Tools](#14-data-quality-and-preprocessing-tools)
15. [Backtesting Engine Improvements](#15-backtesting-engine-improvements)
16. [Portfolio and Multi-System Risk](#16-portfolio-and-multi-system-risk)
17. [Live Trading Infrastructure](#17-live-trading-infrastructure)

---

## 1. Instruments and Timeframes

### Additional instruments

| Instrument | Type | Rationale | Confidence |
|---|---|---|---|
| XAUUSD (Gold) | Metal | Classic safe-haven; strong trend periods; good ATR | High |
| GBPUSD | FX Major | Higher volatility than EURUSD; different momentum dynamics | High |
| USDJPY | FX Major | Carry-trade driven; different regime character | High |
| AUDUSD | FX Major | Commodity-linked; risk-on/off sensitivity | Medium |
| US30 / SPX500 | Index CFD | Strong trending behaviour; requires wider spread model | Medium |
| USOIL (WTI) | Commodity | Strong momentum cycles; high ATR | Medium |
| BTCUSD | Crypto | Extreme momentum; different vol regime; 24/7 | Low |

**Implementation note.** No code changes needed — only bar data downloads. Symbol classification in the portfolio service needs extension for non-FX symbols (`evaluateSymbolClass()`).

### Additional timeframes

| Timeframe | Notes | Effort |
|---|---|---|
| W1 (weekly) | Fewer bars but very clean signal; long training window required | Low |
| MN1 (monthly) | Macro-scale regime identification only; not practical for execution | Low |
| Tick / volume bars | Replace time-based bars with event-based bars (fixed-volume or fixed-tick) — removes artificial discretisation | High |
| Dollar bars | Each bar closes after a fixed notional value traded — more uniform information content | High |

---

## 2. Model Estimators

### Gradient-boosted trees (near-term, low effort)

| Estimator | Library | Status | Notes |
|---|---|---|---|
| XGBoost | `xgboost` | Ready — requires ~20-line code change | Strong on tabular data; add `--model xgb` to CLI |
| LightGBM | `lightgbm` | Ready — requires ~20-line code change | Faster than XGBoost; good for wide feature sets |
| CatBoost | `catboost` | Needs install | Handles categorical features natively; good for calendar features |
| HistGradientBoosting | `sklearn` | Already installed | Fast sklearn implementation; useful baseline |

**[QUICK WIN]** Wire XGBoost and LightGBM into the model factory in `run_historical_split.py` with `--model xgb|lgbm`. Literature consistently shows gradient boosting outperforms logistic regression on tabular financial data.

### Ensemble and stacking

| Method | Approach | Effort | Confidence |
|---|---|---|---|
| Soft voting ensemble | Average probabilities from logreg + XGBoost + RF | Medium | High |
| Stacking (meta-learner) | Train a meta-estimator on CV fold out-of-sample predictions | Medium | High |
| Bagging over walk-forward folds | Train multiple models on bootstrap samples of training folds | Medium | Medium |
| Feature-subsample ensemble | Multiple models on random feature subsets; average outputs | Medium | Medium |

### Sequence and deep learning (medium-term)

| Architecture | Library | Characteristic | Confidence |
|---|---|---|---|
| LSTM | `pytorch` / `keras` | Captures temporal dependencies; requires longer sequences (50-200 bars) | Medium |
| Temporal Convolutional Network (TCN) | `pytorch` | Faster than LSTM; dilated convolutions capture multi-scale patterns | Medium |
| Temporal Fusion Transformer (TFT) | `pytorch-forecasting` | State-of-the-art for multi-horizon tabular time-series; includes attention interpretability | Medium |
| 1D-CNN | `keras` | Fast; good at detecting local bar patterns (candlestick-like) | Medium |
| Transformer encoder | `pytorch` | Self-attention across bar sequence; good for 30-100 bar windows | Low |

**Caveat.** Deep learning models typically require more data (5+ years daily minimum), careful hyperparameter tuning, and ONNX export compatibility testing. Results on short H4/D1 FX windows are mixed. Priority is lower than gradient boosting.

### Probabilistic and uncertainty-aware models

| Method | What it adds | Effort | Confidence |
|---|---|---|---|
| Calibrated probability outputs (already active) | Well-behaved threshold selection | — | — |
| Conformal prediction | Prediction sets with coverage guarantees; quantify uncertainty per bar | Medium | Medium |
| Bayesian logistic regression | Posterior probability distributions; natural uncertainty quantification | High | Medium |
| Monte Carlo dropout | Approximate Bayesian inference in neural nets; uncertainty at inference time | High | Low |

---

## 3. Feature Set Additions

> All features below are computable from OHLCV bars alone unless marked `[EXTERNAL DATA]`. All are implementable as additions to `compute_features()` in `run_historical_split.py`.

### 3.1 Momentum and Trend Oscillators

**[QUICK WIN]** These are well-established, low-correlation additions to the current feature set.

| Feature | Description | Period(s) to try | Confidence |
|---|---|---|---|
| RSI (Relative Strength Index) | 0-100 oscillator measuring speed of price changes | 7, 14, 21 | High |
| RSI divergence | Binary: price makes new high/low but RSI does not | 14 | High |
| MACD line | EMA(12) - EMA(26); normalised by ATR | 12/26/9 | High |
| MACD histogram | MACD minus signal line; rate of change of momentum | 12/26/9 | High |
| Stochastic %K | Close position within N-bar range; 0-100 | 14 | High |
| Stochastic %D | 3-bar SMA of %K | 14/3 | Medium |
| ADX (Average Directional Index) | Trend strength 0-100; direction-agnostic | 14 | High |
| +DI / -DI | Directional components of ADX | 14 | Medium |
| CCI (Commodity Channel Index) | Price deviation from moving average; normalised | 14, 20 | Medium |
| Williams %R | Inverse of Stochastic; -100 to 0 | 14 | Medium |
| Aroon Up/Down | Time since recent high/low as % of lookback | 25 | Medium |
| Rate of Change (ROC) | Percentage price change over N bars | 5, 10, 20 | High |
| Detrended Price Oscillator (DPO) | Price minus displaced SMA; removes long-term trend | 20 | Low |
| Ultimate Oscillator | Weighted average of 3 time-frame momentum | 7/14/28 | Low |

### Ichimoku Cloud features

The Ichimoku system produces five components, each a stand-alone feature.

| Feature | Description | Confidence |
|---|---|---|
| Price vs. Kumo cloud | Binary: close above / below the cloud (Senkou A and B) | High |
| Tenkan-Kijun cross | Bullish when Tenkan-sen crosses above Kijun-sen | High |
| Tenkan-sen slope | Rate of change of the 9-period conversion line | Medium |
| Chikou span vs. price | Close 26 bars ago vs. current price; lagged confirmation | Medium |
| Cloud thickness | Absolute(Senkou A - Senkou B) / ATR; structural volatility proxy | Medium |
| Price vs. Kijun-sen | Distance from the base line normalised by ATR | High |

**Implementation.** Pure OHLCV calculation. Add 6 Ichimoku features to `compute_features()`. Especially strong on D1 and H4 FX timeframes.

### Adaptive moving averages

| Feature | Description | Confidence |
|---|---|---|
| KAMA (Kaufman Adaptive MA) | Adapts speed via efficiency ratio; fast in trends, slow in noise | High |
| KAMA slope (N bars) | Rate of change of KAMA; trend direction and acceleration | High |
| Price deviation from KAMA | Normalised by ATR; momentum and mean-reversion indicator | High |
| TEMA (Triple EMA) | Triple-smoothed EMA; significantly reduces lag vs. standard EMA | Medium |

### Linear regression channel features

| Feature | Description | Confidence |
|---|---|---|
| Linear regression slope (N bars) | Best-fit slope normalised by ATR; rate of trend | High |
| R-squared of N-bar trend | How well price fits a straight line; 0 = noise, 1 = perfect trend | High |
| Forecast deviation | Close vs. linear regression forecast; mean-reversion signal | Medium |
| Standard error of regression | Deviation around the trend line; volatility of trend quality | Medium |

### Squeeze Momentum

Combines Bollinger Bands inside Keltner Channels to detect volatility compression before a breakout:
- **Squeeze on**: Bollinger Bands narrower than Keltner Channels (compression state)
- **Squeeze fire**: Bollinger Bands expand outside Keltner Channels (expansion trigger)
- **Momentum direction**: Linear regression of delta-momentum; positive = bullish, negative = bearish

**[QUICK WIN]** Implementable in ~35 lines. Strong empirical evidence on D1 and H4 timeframes. Pairs naturally with the existing Bollinger Band width feature.

### Supertrend

Dynamic trailing stop / trend direction indicator based on ATR:
- `Upper band = midpoint + multiplier * ATR`; `Lower band = midpoint - multiplier * ATR`
- Direction flips when close crosses the active band

Produces a binary trend-direction flag and a normalised distance-from-band feature. Lightweight complement to the existing regime gate.

### 3.2 Volatility and Range Features

| Feature | Description | Confidence |
|---|---|---|
| Bollinger Band width | (Upper - Lower) / Middle; measures volatility compression and expansion | High |
| Bollinger Band %B | Position of close within band (0 = lower, 1 = upper) | High |
| Bollinger Band squeeze | Band width at multi-month minimum; precedes explosive move | High |
| Keltner Channel position | Close position relative to ATR-based channel | Medium |
| Historical volatility ratio (multiple windows) | HV5 / HV20 and HV20 / HV60; multi-scale vol regime | High |
| Realised vol vs implied vol proxy | ATR20 / (52-week ATR); over/under-volatility regime | Medium |
| True Range normalised | Daily true range / N-day average true range | High |
| Parkinson volatility | Uses high/low of bar; more efficient than close-to-close | Medium |
| Garman-Klass volatility | Uses open, high, low, close; most efficient single-bar volatility estimate | Medium |

### 3.3 Volume and Order Flow Proxies

> FMP API includes volume in OHLCV bars. For FX, volume is tick volume (proxy for activity).

| Feature | Description | Confidence |
|---|---|---|
| Volume ratio | Bar volume / N-bar average volume | High |
| Volume momentum | 5-bar sum of signed volume (+ on up bars, - on down bars) | High |
| On-Balance Volume (OBV) normalised | Cumulative signed volume; normalised over rolling window | High |
| OBV momentum | Rate of change of OBV | Medium |
| Volume-price divergence | Price makes new high/low but volume is declining | Medium |
| Chaikin Money Flow (CMF) | Volume-weighted measure of buying/selling pressure over 20 bars | Medium |
| Volume-weighted spread | Bar range weighted by volume; identifies high-conviction bars | Medium |
| Relative volume spike | Binary: volume > 2x rolling average | High |

### 3.4 Market Structure Features

| Feature | Description | Confidence |
|---|---|---|
| N-bar high/low distance (multiple periods) | Current breakout distances at 20, 34, 89, 200 bars | High |
| Pivot points (daily/weekly) | Classic PP, R1/R2/R3, S1/S2/S3; distance from current price | Medium |
| Support/resistance proximity | Distance to nearest significant swing high/low in N bars | Medium |
| Higher high / lower low sequence | Binary flags for N consecutive HH or LL; trend structure | High |
| Inside bar flag | Binary: current bar fully within previous bar range; compression signal | High |
| Outside bar flag | Binary: current bar engulfs previous bar range; expansion signal | Medium |
| Doji / hammer / engulfing pattern | Candlestick pattern classification flags | Low |
| Gap (open vs. previous close) | Open gap size normalised by ATR; strong regime signal on D1 | Medium |
| Bar body ratio | (Close - Open) / True Range; measure of bar conviction | High |
| Upper/lower wick ratio | Upper wick / True Range; lower wick / True Range | Medium |
| 200-SMA slope | Rate of change of SMA200; trending vs. flat macro environment | High |
| Multi-timeframe SMA alignment | Whether price is above SMA on H4, D1, and W1 simultaneously | Medium |

### 3.5 Calendar and Seasonality Features

**[QUICK WIN]** These are zero-cost features (no new data needed) with documented seasonality effects in FX markets.

| Feature | Description | Confidence |
|---|---|---|
| Day of week | Monday=0 to Friday=4; one-hot or ordinal | High |
| Hour of day (for H1/M15) | Session time; captures Asian/European/US open dynamics | High |
| Month of year | January effect, year-end flows | Medium |
| Quarter end flag | Last 5 trading days of each quarter; rebalancing flows | Medium |
| Monday / Friday binary | Specific day flags; FX Monday gap risk, Friday position-squaring | High |
| US/UK/EU bank holiday proximity | Binary: next 1-3 days include major holiday | Medium |
| NFP / FOMC proximity | Binary: within N bars of scheduled high-impact event | Medium |
| Year-end flag | Dec 15 - Jan 15; reduced liquidity / positioning | Low |
| Daylight saving time transition | Binary: week of DST change; affects session timing | Low |

### 3.6 Cross-Asset and Macro Features

> Requires additional data sources or derived calculations. Mark as `[EXTERNAL DATA]` where a new feed is needed.

| Feature | Description | Data source | Confidence |
|---|---|---|---|
| DXY level and rate of change | US Dollar Index; key driver of all USD pairs | `[EXTERNAL DATA]` FMP | High |
| DXY vs EURUSD divergence | Binary: EURUSD moving opposite to DXY expectation | Computed | Medium |
| Gold / USD negative correlation flag | Divergence between XAUUSD and DXY | Computed | Medium |
| VIX level and rate of change `[EXTERNAL DATA]` | Equity volatility index; risk-off regime indicator for all assets | FMP US indices | High |
| US 10Y yield rate of change `[EXTERNAL DATA]` | Drives USD carry; key macro factor | FMP bonds | Medium |
| US-EU rate differential `[EXTERNAL DATA]` | Key fundamental driver for EURUSD | FMP bonds | Medium |
| Equity index trend `[EXTERNAL DATA]` | SPX500 above/below SMA200; risk-on/risk-off proxy | FMP indices | Medium |
| Oil price rate of change `[EXTERNAL DATA]` | Affects CAD, NOK, and risk appetite globally | FMP commodities | Low |

### 3.7 Higher-Order Statistical Features

| Feature | Description | Confidence |
|---|---|---|
| Rolling skewness of returns | 20-bar and 60-bar skewness; identifies asymmetric return distribution periods | Medium |
| Rolling kurtosis of returns | Fat-tail regime indicator | Medium |
| Autocorrelation lag-1 | Serial correlation of returns; elevated = momentum, negative = mean-reversion | High |
| Hurst exponent (rolling) | H > 0.5 = trending; H < 0.5 = mean-reverting; H = 0.5 = random walk | High |
| Variance ratio test statistic | Lo-MacKinlay variance ratio; another trend/MR discriminant | Medium |
| Z-score of price deviation | Distance from rolling mean in standard deviation units | High |
| Percentile rank of close | Close's percentile within rolling N-bar window | High |
| CUSUM filter statistic | Running cumulative sum; detects when price deviates significantly from equilibrium | High |
| Fractionally differentiated price series | Apply d < 1 differencing to preserve long memory while achieving stationarity | High |
| Sample entropy | Sequence irregularity; low = structured / high = random; regime complexity measure | Medium |
| ADF t-statistic (rolling window) | Rolling unit-root test statistic; stationarity level as a feature | Medium |
| Half-life of mean reversion | Estimated via OU process; shorter = stronger MR signal | Medium |

### 3.8 Alternative Data Features

> Requires external data pipelines. Highest potential but highest implementation cost.

| Feature | Description | Effort | Confidence |
|---|---|---|---|
| FX positioning (COT report) | CFTC Commitments of Traders; net speculative positioning for major FX | High | High |
| Retail sentiment index | % of retail traders long vs. short (IG, OANDA sentiment APIs) | High | Medium |
| News sentiment score | NLP-derived sentiment from financial news headlines (per symbol) | High | Medium |
| Economic surprise index | Citi ESI; measures whether data beats/misses consensus | High | Medium |
| Google Trends / search volume | Search interest proxy for retail participation | High | Low |
| Options implied volatility | Put/call ratio, vol surface skew for FX options | High | Medium |

---

## 4. Label Objectives

### Triple barrier method (Marcos Lopez de Prado)

The current `direction` and `edge` labels set a fixed horizon. The triple barrier method uses dynamic barriers:
- **Upper barrier**: fixed profit target (e.g., +2 ATR) — labels as +1
- **Lower barrier**: fixed stop loss (e.g., -1 ATR) — labels as -1
- **Vertical barrier**: time limit (horizon bars) — neutral or directional label

**Benefit.** More realistic — aligns labels with how actual trades close. Removes the noise from near-zero moves and losses that would have been stopped out.

**[QUICK WIN]** Effort: Medium. Add `--label-mode triple-barrier --barrier-profit-multiplier 2.0 --barrier-stop-multiplier 1.0` to `run_historical_split.py`.

### Risk-adjusted return label

`Y = 1` when `future_return / rolling_vol > threshold_in_sharpe_units`

- Normalises the target by contemporaneous volatility
- Makes the label comparable across different vol regimes
- Effective on instruments with time-varying volatility (gold, oil)

### Meta-labeling (Lopez de Prado)

A two-stage approach:
1. **Primary model**: existing rule-based strategy generates a buy/sell signal
2. **Meta-model**: ML model predicts whether the primary signal will be *profitable* (binary: 1 = take the trade, 0 = skip)

**Benefit.** Dramatically reduces noise trades — the model learns to filter the strategy's own false positives rather than predicting raw direction. Well-evidenced in academic literature.

**Effort:** Medium. The primary signal comes from `evaluateDailyBreakout()` in the backend. The meta-label is computed against the primary signal's P&L outcome.

### Return-to-risk ratio label

`Y = 1` when `future_return / ATR20 > threshold`

- Scales the target by current volatility level
- Produces more stable label frequency across low and high vol periods
- Natural complement to ATR-based position sizing

### Multi-class label

| Class | Condition | Use |
|---|---|---|
| +1 (Strong up) | Return > edge_high_bps | Full-size entry |
| 0 (Neutral) | \|Return\| <= edge_low_bps | Skip |
| -1 (Strong down) | Return < -edge_high_bps | Short entry (if shorts enabled) |
| +0.5 (Weak up) | edge_low_bps < return <= edge_high_bps | Half-size entry |

**Benefit.** Natural mapping to the three-bucket sizing system (FULL / HALF / SKIP). Replace binary classification with 4-class or ordinal regression.

### Quantile regression label

Predict the entire conditional distribution of future returns, not just direction. The model outputs confidence intervals; entry only when the lower confidence bound exceeds the cost model threshold.

### CUSUM-filtered sampling (Lopez de Prado)

Before labeling, apply a symmetric CUSUM filter to sample only statistically significant price events:

- `S_up(t) = max(0, S_up(t-1) + return(t) - E[return])`
- `S_down(t) = min(0, S_down(t-1) + return(t) - E[return])`

Sample a bar only when `|S(t)| > threshold`. The filter removes the majority of low-information observations, dramatically reducing label noise and serial correlation in the training set.

**Effort:** Medium. Implement as a sampling step before `compute_features()`. Pairs naturally with triple barrier labeling. **Confidence:** High — well-evidenced in Lopez de Prado's Advances in Financial Machine Learning.

### Fractionally differentiated features (Lopez de Prado)

Log returns (d=1 differencing) are stationary but lose all memory. Raw prices (d=0) are non-stationary. Fractional differentiation finds the minimum d that achieves stationarity while preserving maximum historical memory:

`w_k = product_{j=0}^{k-1} (d - j) / (j + 1)` applied as a weighted moving average with weights decaying to zero.

Use an ADF test to confirm stationarity at the chosen d. Features derived from fractionally differentiated price series carry both stationarity and historical memory — especially important for SMA deviation, breakout distance, and other trend features.

**Effort:** Medium (~60 lines). **Confidence:** High for features with long mean-reversion half-lives.

---

## 5. Signal Variants

### Volume-confirmation variant

Enter only when the bar's tick volume is above the N-bar rolling average.

**Rationale.** Strong directional bars on high volume have higher follow-through probability than low-volume bars. Reduces noise trades by ~20-30% with modest impact on quality.

**Knobs:** `--volume-min-ratio` (e.g., 1.2 = 20% above average)

### RSI filter variant

Apply an RSI condition before entry:
- Trend-following entries: only when RSI > 50 (momentum confirmed)
- Mean-reversion entries: only when RSI < 30 or RSI > 70 (extreme reading)

**Knobs:** `--rsi-trend-floor`, `--rsi-mr-ceiling`, `--rsi-mr-floor`

### Multi-timeframe confirmation variant

Require alignment across two timeframes before entry:
- H4 primary signal + D1 trend confirmation (above D1 SMA200, D1 RSI > 50)
- H1 signal + H4 regime filter

**Implementation note.** Requires fetching a second timeframe's bar data and computing features independently, then merging on timestamp.

### Bollinger Band squeeze variant

Enter only after a defined compression period:
- Measure band width relative to its 6-month percentile
- When width crosses below the 20th percentile (squeeze), flag the next breakout entry
- Exits when band width returns to normal

### ADX strength filter

Enter only when ADX > threshold (e.g., 20-25):
- Avoids choppy, range-bound markets
- Strong complement to trend-follow variant
- Orthogonal to the current regime gate (which uses vol-regime ratio)

**[QUICK WIN]** Effort: Low. Add `--adx-min-strength` parameter to the regime gate.

### Seasonality filter variant

Enter only on statistically favourable calendar conditions:
- Day of week: avoid Mondays (gap risk), reduce Friday exposure
- Month: avoid August/December (low liquidity)
- Session: restrict H1/M15 entries to high-liquidity windows (London/NY overlap)

### Short-side variant

All current variants are long-only. Adding symmetric short entries:
- Mirror the trend-follow conditions for downside breakouts
- Requires short-side backtesting (currently `backtest_engine.py` is long-only)
- EA already supports SELL actions via `CTrade`

**Effort:** Medium. `backtest_engine.py` needs short-trade simulation; label generation needs to include downward moves.

### Carry-aware variant (FX-specific)

For FX pairs where the interest rate differential is favourable, apply a lower probability threshold (carry adds edge). For unfavourable carry, raise the threshold.

---

## 6. Regime Detection Methods

### Hidden Markov Model (HMM)

Fits a 2-state or 3-state Gaussian HMM to return sequences. States typically correspond to:
- State 0: Low-volatility trending regime
- State 1: High-volatility mean-reverting or crisis regime

**Implementation.** `hmmlearn` is installable via pip. Produces a per-bar state probability that can be used as a filter or feature.

**[QUICK WIN]** Effort: Medium. Evidence is strong for regime-switching in FX. The HMM state probability is a powerful input feature even without using it as a hard gate.

### Gaussian Mixture Model (GMM) regime clustering

Cluster trailing 60-bar return/vol windows into K regimes using GMM. Assign current bar a soft regime membership probability vector.

**Advantage over HMM.** No temporal constraints — can detect regimes based on feature clustering rather than sequential dependencies.

### Change-point detection (PELT / BOCPD)

Detect structural breaks in the returns/volatility process using:
- PELT (Pruned Exact Linear Time): fast, offline changepoint detection
- BOCPD (Bayesian Online Changepoint Detection): real-time; produces a posterior over changepoint recency

**Use case.** Detect when the underlying market behaviour has shifted. Suppress entries immediately after a changepoint until the new regime stabilises.

**Library.** `ruptures` (PELT), `bayesian_changepoint_detection`.

### Kalman filter trend extraction

Apply a Kalman filter to the price series to extract the "true" trend component, removing observation noise. The Kalman gain dynamically adjusts the filter's sensitivity to new observations.

**Feature output.** `kalman_trend` (filtered price trend), `kalman_velocity` (rate of change of trend), `kalman_uncertainty` (observation noise estimate).

### Hurst exponent regime gate

Compute the rolling Hurst exponent (e.g., 100-bar window):
- H > 0.55: enter trend-following trades
- H < 0.45: enter mean-reversion trades
- 0.45 < H < 0.55: skip (indeterminate regime)

**Library.** Computable from scratch in ~20 lines; or `hurst` pip package.

### Fractal dimension / efficiency ratio

The Efficiency Ratio (Perry Kaufman) measures `|net price change| / sum(|bar changes|)` over N bars.
- High ER (>0.6): directed movement — trend-follow
- Low ER (<0.3): noisy movement — mean-revert or skip

Computationally cheap; strong complement to the existing `trend_strength` feature.

**[QUICK WIN]** Effort: Low. Add `efficiency_ratio` as a feature and/or regime gate knob.

### Volatility regime via VIX proxy

Instead of the current `vol20/vol100` ratio, use a 3-state volatility regime:
- Low vol: trailing 20-bar HV in bottom 30th percentile of 2-year history
- Medium vol: 30th-70th percentile
- High vol (crisis): top 30th percentile

Block entries in high-vol regime; apply different thresholds in low vs. medium.

### GARCH / EGARCH volatility regime

Fit a GARCH(1,1) or EGARCH model to extract the conditional variance as a dynamic volatility signal. Unlike simple rolling vol ratios, GARCH captures volatility clustering: today's volatility is a function of yesterday's volatility and yesterday's shock magnitude.

| Feature | Description |
|---|---|
| GARCH conditional variance | Point estimate of current volatility from the fitted model |
| GARCH variance ratio | Conditional variance / long-run (unconditional) variance |
| GARCH vol state | Binary: current conditional variance above or below long-run variance |
| EGARCH asymmetry | Leverage effect: negative return shocks produce more volatility than positive shocks |

**Library.** `arch` package (`pip install arch`). Fit once per training fold; apply fitted parameters to the test fold for zero-lookahead features.

### K-means clustering regime

Cluster trailing feature windows into K market states:
1. For each bar, compute a rolling feature window (last 60-bar return / vol statistics)
2. Fit K-means (K = 3 or K = 4) on the training data
3. Assign each bar a cluster label; post-hoc label clusters by return and volatility profile
4. Use cluster membership probability as a soft feature or hard entry gate

**Advantage.** Unsupervised — discovers regime structure from data without hand-coded thresholds.

### Structural break tests

Validate that training windows do not straddle a major structural break before committing to window dates.

| Test | What it detects | Library |
|---|---|---|
| Zivot-Andrews | Single structural break at unknown date | `statsmodels` |
| CUSUM of squares | Recursive parameter instability in linear models | `statsmodels` |
| Bai-Perron | Multiple structural breaks | `ruptures` |
| ICSS | Multiple volatility breaks | Custom ~50 lines |

**Use case.** Run before setting training window dates. If a break is detected inside the window, adjust the start date or split at the break.

---

## 7. Probability Threshold Strategy

### Dynamic threshold scheduling

Instead of a static threshold selected at training time, adjust the threshold at inference time based on current market conditions:

| Condition | Threshold adjustment |
|---|---|
| Current vol-regime > 1.5 | Raise threshold by +0.05 (more selective in high vol) |
| Model prediction uncertainty high (conformal interval wide) | Raise threshold |
| Recent signal history: 3+ consecutive losses | Raise threshold temporarily |
| Recent signal history: high win-rate streak | Revert to baseline |

### Asymmetric long/short thresholds

Set different probability thresholds for long and short entries. Long entries may warrant a lower threshold if carry is positive; short entries may require a higher threshold.

### Kelly-optimal threshold selection

Instead of selecting the threshold that satisfies DD and trades constraints, select the threshold that maximises the Kelly criterion:

`f* = (edge / odds) = (p * W - (1-p) * L) / (W/L)`

where `p` = win rate, `W` = average win, `L` = average loss at each threshold candidate.

**Caveat.** Kelly is theoretically optimal but produces aggressive sizing in practice. Use fractional Kelly (0.25-0.5 Kelly) as a sizing knob.

### Threshold per regime

Store separate thresholds for each detected regime. During low-vol trending regimes, a lower threshold may be appropriate. During high-vol regimes, raise the threshold to compensate for wider stops.

**Implementation.** The `historical_split_report.json` could include per-regime threshold selections alongside the overall constrained selection.

---

## 8. Walk-Forward CV Improvements

### Combinatorial Purged Cross-Validation (CPCV)

Lopez de Prado's CPCV generates multiple train/test splits from K groups, exhaustively combining them to maximise the number of distinct test paths. Unlike standard WF-CV:
- No single "future" test path — multiple paths covering the full sample
- Dramatically more efficient use of data
- Produces a distribution of performance metrics, not just one estimate

**Library.** Implementable with `mlfinlab` or custom code (~100 lines).

**Effort:** Medium. **Confidence:** High for reducing selection bias.

### Purged and embargoed CV (improvements to current embargo)

The current embargo is a fixed bar gap. Improvements:
- **Purging**: remove all training observations whose labels overlap with the test window's label horizon (not just a fixed gap)
- **Rolling embargo**: scale embargo bars with the horizon length (`embargo = 0.01 * N_training`)

### Expanding window vs. rolling window

The current approach uses a rolling training window. An **expanding window** keeps all historical data in each fold's training set:

| Method | Trade-off |
|---|---|
| Rolling (current) | Responsive to regime changes; discards old data |
| Expanding | More training data per fold; slower to adapt to regime shifts |
| Hybrid | Expanding until a minimum sample size, then rolling |

**[QUICK WIN]** Effort: Low. Add `--cv-window-type rolling|expanding|hybrid` flag.

### Anchored walk-forward

Fix the training start date but advance the test window incrementally. Mimics the "all historical knowledge" available at each live deployment point. Particularly relevant for regime-sensitive models where very old data still provides useful distributional coverage.

### Block bootstrap CV

Resample contiguous blocks of training data (respecting serial correlation) to generate multiple training samples. Produces more robust out-of-sample estimates when the training window is short.

### Deflated Sharpe Ratio (DSR) test

The DSR adjusts the observed Sharpe Ratio for three back-test biases: non-normality of returns, serial correlation, and multiple testing. A strategy with DSR below a benchmark level should be rejected regardless of its nominal Sharpe.

The core insight: with enough configuration trials, any search process will eventually find a strategy that passes a Sharpe threshold by luck. DSR quantifies whether the observed Sharpe is statistically meaningful given the number of configurations tested.

**Effort:** Low (~30 lines using `scipy.stats`). Compute on every holdout evaluation alongside Sharpe Ratio. Reference: Bailey and Lopez de Prado (2014).

### Probability of Backtest Overfitting (PBO)

Uses CPCV-generated splits to estimate whether the selected configuration was chosen by multiple-testing luck:

1. For each CPCV split, rank all tested configurations by in-sample Sharpe
2. For each split, record the out-of-sample performance rank of the in-sample winner
3. PBO = fraction of splits where the in-sample winner ranks below the median OOS performance

PBO = 0%: selection is valid. PBO > 50%: the search process is effectively random. Report alongside every multi-experiment gate evaluation.

**Effort:** High (requires CPCV). **Confidence:** High for quantifying selection bias.

### Monte Carlo permutation test

A minimum statistical significance check: verify the strategy's performance is not simply explained by the random ordering of the same returns.

1. Record the observed Sharpe / profit factor on actual data
2. Randomly shuffle the order of trade returns (or bar returns) N = 1000 times
3. Recompute the metric on each permuted series
4. p-value = fraction of permuted runs that exceed the observed metric

Require p < 0.05 for promotion. Computationally cheap: ~30 lines. Run after every holdout evaluation as a minimum significance check.

---

## 9. Training Window Design

### Regime-conditional windows

Train separate models for each detected regime. The inference pipeline applies whichever model's regime condition is currently active.

| Regime model | Trained on | Applied when |
|---|---|---|
| Trending model | Only bars where HMM state = trend | Current HMM state = trend |
| MR model | Only bars where HMM state = mean-revert | Current HMM state = MR |
| Crisis model | High-vol bars only | Vol-regime > threshold |

### Adaptive lookback

Instead of a fixed training window, use a variable lookback that adapts to regime stability:
- If a structural break was detected recently (BOCPD changepoint): shorten the lookback
- If the regime has been stable for 2+ years: extend the lookback (more data = better)

### Ensemble over multiple training windows

Train 3-5 models on different window lengths (e.g., 2yr, 4yr, 6yr, 8yr). Ensemble their outputs. Reduces sensitivity to any single window choice.

### Out-of-distribution detection on holdout

Before running holdout, compute the feature distribution distance (KL divergence or maximum mean discrepancy) between the dev training set and holdout test set. If the distance exceeds a threshold, flag a potential regime shift and adjust gate expectations.

---

## 10. Cost Model Enhancements

### Overnight swap / financing cost

For instruments held overnight (FX, CFDs), funding costs accumulate daily. For EURUSD long:
- Swap rate = EURIBOR - Fed Funds Rate (sign determines whether positive or negative carry)
- On a 1-lot position: approximately -$0.50 to +$2.00 per night depending on rate differential

**[QUICK WIN]** Effort: Low. Add `--overnight-swap-bps` parameter; deduct from each trade held >1 session.

### Market impact (permanent and temporary)

For larger positions, execution moves the market:
- **Temporary impact**: bid-ask spread widens when crossing a large order
- **Permanent impact**: price adjusts to reflect information content of large trade

Modelled as: `impact = lambda * sigma * sqrt(Q / ADV)` where Q is order size and ADV is average daily volume.

### Execution fill rate model

Not every limit or stop order fills at the expected price. Model as:
- `fill_price = signal_price + Normal(0, slippage_std)`
- Alternatively, model partial fills: `fill_quantity = min(order_size, available_liquidity)`

### Realistic stop-loss execution

Current model assumes stop-losses execute exactly at the stop price. In reality:
- Gaps (especially on D1 open) can cause significant slippage beyond the stop
- Add `--gap-slippage-multiplier` (e.g., 1.5x stop slippage on D1)
- Model D1 gap distribution from historical open-vs-close data

---

## 11. Position Sizing Models

### Fractional Kelly criterion

Sizes each trade based on the estimated edge and win/loss ratio from recent history:

`position_size = f * Kelly_fraction`  
`Kelly = (p * W - (1-p) * L) / (W/L)`

`f = 0.25` (quarter Kelly) is a common production choice — reduces drawdown while preserving most of the Kelly growth rate.

**[QUICK WIN]** Effort: Medium. Requires the backend to calculate Kelly based on recent strategy statistics and pass sizing guidance back to the EA.

### Volatility-scaled position sizing

Size each trade such that the expected dollar risk is constant regardless of ATR:

`position_size = (account_risk_pct * account_balance) / (N * ATR)`

where N is the ATR multiplier for the stop distance.

Current platform uses a fixed lot size. Volatility-scaling improves risk consistency dramatically across instruments and time periods.

### Optimal-f (Ralph Vince)

Maximise the Terminal Wealth Relative (TWR) over historical trades by finding the fixed fraction `f` that produces the highest geometric growth:

`TWR = product((1 + f * HPR_i)^(1/N))`

More aggressive than fractional Kelly but provides a data-driven size anchor.

### Fixed-ratio position sizing

Increase position size only after accumulating a fixed delta in profits:
- Start at 1 lot; increase to 2 lots after `delta` profit
- Conservative compounding approach; prevents early over-sizing

### Regime-conditional sizing

- Low-vol trending regime: full position size
- High-vol or ambiguous regime: half position size
- Crisis / structural break: minimum size or skip

---

## 12. Promotion Gate Enhancements

### Additional risk-adjusted metrics

| Metric | Formula | Threshold target | Confidence |
|---|---|---|---|
| Calmar ratio | Annualised return / max drawdown % | > 0.5 | High |
| MAR ratio | Same as Calmar but over full period | > 0.3 | High |
| Sortino ratio | Return / downside deviation (not total vol) | > 1.0 | High |
| Omega ratio | Probability-weighted ratio of gains to losses | > 1.0 | Medium |
| Ulcer Index | RMS of drawdown depth; penalises prolonged drawdowns | Lower is better | Medium |
| Pain Index | Area under the drawdown curve / observation count | Lower is better | Medium |

**[QUICK WIN]** Add Calmar ratio and Sortino ratio to `ts003_gate_evaluation.json` output and Gate 3 check.

### Regime-conditional gate evaluation

Evaluate Gates separately for:
- Trending-regime bars only
- Mean-reverting-regime bars only

A strategy that passes overall gates but fails in one specific regime has concentrated risk. Detecting this requires per-regime P&L attribution.

### Tail risk gates

| Metric | Description | Gate action |
|---|---|---|
| CVaR (Conditional Value-at-Risk) | Expected loss in the worst 5% of outcomes | REJECT if CVaR > 2x average drawdown |
| Maximum consecutive losses | Longest losing streak | PAPER_ONLY if > 8 consecutive losses |
| Recovery factor | Net profit / max drawdown | Require > 2.0 for PROMOTE |

### Stress scenario gates

Beyond the current 2x cost multiplier:

| Scenario | How to implement |
|---|---|
| Wide spread regime | 5x cost multiplier; simulates high-vol market making conditions |
| Execution gap scenario | Add random gaps (sampled from historical distribution) to entry prices |
| Regime shift scenario | Evaluate holdout restricted to 2020 (COVID), 2022 (Ukraine/Fed pivot) periods only |
| Drawdown from peak | Evaluate whether strategy recovers within 90 calendar days of maximum drawdown |

### Consistency gate

Require the strategy to be profitable in at least 60% of individual calendar months in the holdout window. Guards against a single outlier month driving the overall result.

### Out-of-sample Sharpe comparison

Compare holdout Sharpe to dev Sharpe. If `holdout_Sharpe < 0.5 * dev_Sharpe`, flag potential overfitting regardless of whether absolute gate thresholds pass.

### Maximum Adverse Excursion (MAE) analysis

For every closed trade, record the maximum unfavourable move before exit:
- Plot the MAE distribution for winners vs. losers separately
- Target: winner MAE should be concentrated well below the stop distance
- If winners frequently approach the stop before recovering: entry timing may be imprecise or stop too tight

**Effort:** Low. Add `mae_bps` and `mfe_bps` columns to the trade record in `backtest_engine.py`. Compute and report after every backtest run.

### Maximum Favourable Excursion (MFE) analysis

For every closed trade, record the maximum favourable move before exit:
- Compare MFE distribution to actual exit P&L
- If median MFE significantly exceeds median exit profit: exits are leaving edge on the table
- MFE vs. actual P&L scatter plot identifies systematic exit leakage

### G-ratio

`G-ratio = mean MFE / mean |MAE|`

| G-ratio | Interpretation |
|---|---|
| > 2.0 | Strong asymmetric payoff; entries and stops are well-designed |
| 1.0 to 2.0 | Acceptable; room for exit optimisation |
| < 1.0 | Entry or stop design needs review |

Report G-ratio in every gate evaluation alongside profit factor and Calmar ratio.

### Deflated Sharpe Ratio gate

Require DSR > 0.5 on the holdout window. A strategy with positive nominal Sharpe but DSR < 0.5 has likely been selected by multiple-testing luck and must not be promoted regardless of other gate outcomes.

---

## 13. Pipeline and Architecture Additions

### Online learning / incremental retraining

Instead of periodic full retrains, update the model incrementally as new bars arrive:
- **Sliding window refit**: retrain on the most recent N bars on a scheduled basis (e.g., weekly)
- **Warm start**: initialise new training from the previous model's weights
- **Concept drift detection**: alert when feature distribution or model calibration shifts beyond a threshold (Population Stability Index > 0.2)

### Feature selection and importance

| Method | Use |
|---|---|
| SHAP values | Per-prediction feature importance; identify which features drive each signal | 
| Permutation importance (rolling) | Track feature importance stability across training folds |
| Recursive Feature Elimination (RFE) | Automatically prune low-importance features |
| Maximum relevance / minimum redundancy (mRMR) | Select the most informative and least correlated feature subset |

**[QUICK WIN]** Add SHAP output to `historical_split_report.json`. Already supported by `shap` library (pip-installable).

### Multi-instrument portfolio training

Train a single model across multiple instruments simultaneously (EURUSD + XAUUSD + GBPUSD). Use instrument identity as a categorical feature. Benefit: cross-asset patterns, more training samples.

### Adversarial validation

Train a binary classifier to distinguish training bars from test bars. If it achieves high accuracy, the train/test sets are too different — a warning sign of non-stationarity or look-ahead.

### Walk-forward performance decomposition

Decompose P&L into components for each gate evaluation:
- Alpha from threshold selection
- Alpha from signal variant filter
- Alpha from regime gate
- Cost drag

Reveals which components are genuinely contributing vs. which are over-tuned.

### Explainable AI (XAI) report

For every promoted model, produce:
- SHAP summary plot (feature importance)
- SHAP dependence plots for top 3 features
- Calibration plot (predicted probability vs. actual win rate)
- Feature drift report comparing train vs. test feature distributions

### Model versioning and lineage registry

Extend the current `model_version` table to include:
- Full training configuration hash
- Feature schema version
- CV fold performance distribution (mean ± std for each metric)
- Parent model version (if warm-started)
- Environment hash (library versions)

This enables full reproducibility and automated regression detection when a new model underperforms its parent.

### Shadow trading

Deploy a candidate model alongside the live model. The shadow model generates signals and logs hypothetical P&L against live prices without executing real trades. Compare shadow vs. live for N bars before any model switch.

**Implementation.** Add a `shadow_mode` flag to the signal endpoint. Backend generates both live and shadow signals on each bar; EA ignores shadow signals. A reporting endpoint computes shadow P&L.

### A/B testing framework

Allocate a fraction of trading sessions to a challenger model while the champion handles the rest. Use a Sequential Probability Ratio Test (SPRT) to determine when the challenger has demonstrated superiority with statistical confidence.

**Gate for champion replacement:** SPRT p < 0.05 with minimum N = 20 challenger trades before any switch is proposed. Human approval always required.

### Feature store

A centralised, versioned registry of computed feature vectors in the database:
- Features computed once per bar and written to a `feature_cache` table (`symbol`, `timeframe`, `bar_date`, `schema_version`, `features JSONB`)
- Training scripts query the cache; downstream reuse eliminates redundant computation across training runs
- Feature values are immutable once written — full audit trail

**Implementation.** Add `feature_cache` table to Prisma schema. Populate via a post-download compute job.

### Concept drift detection

Monitor Population Stability Index (PSI) per feature between the training distribution and the most recent N live bars:

| PSI | Interpretation | Action |
|---|---|---|
| < 0.10 | No meaningful change | Continue |
| 0.10 to 0.20 | Moderate distribution shift | Monitor and log |
| > 0.20 | Significant drift | Trigger model review |

Alert via the `/health` backend endpoint. PSI computed nightly by a scheduled job.

### Automated retraining pipeline

A scheduled job (weekly or monthly) that:
1. Downloads new bar data since the last training run
2. Recomputes features via the feature store
3. Runs walk-forward CV on the extended window using the existing recipe configuration
4. Compares new model metrics to the current live model (Sharpe, PF, DD, DSR)
5. If new model passes all gates AND beats the current on 3 / 4 key metrics: set status `pending_approval`
6. Human reviews and approves before any live model swap

Automated promotion is never allowed — human approval is always the final gate.

---

## 14. Data Quality and Preprocessing Tools

### Bar quality validation

Every downloaded bar must pass quality checks before entering the feature pipeline:

| Check | Description | Action on fail |
|---|---|---|
| Stale bar | Current OHLCV identical to previous bar | Flag and exclude from training |
| OHLCV consistency | High >= max(Open, Close), Low <= min(Open, Close), High >= Low | Reject bar entirely |
| Extreme gap | Open deviates > 5 * ATR from previous close | Flag; include in gap-slippage model |
| Zero volume | Volume = 0 (weekend or holiday artifact) | Exclude |
| Timestamp gap | Missing bars in expected sequence | Interpolate up to N gaps; otherwise flag |
| NaN / inf in features | Any feature computes to NaN or infinity | Block training run with DATA_QUALITY_FAILURE |

### Feature stationarity testing

Before training, verify each feature is stationary in the training window:

| Test | Null hypothesis | Action if not rejected |
|---|---|---|
| Augmented Dickey-Fuller (ADF) | Series has a unit root (non-stationary) | Apply differencing or fractional differencing |
| KPSS test | Series is trend-stationary | Apply detrending |
| Phillips-Perron | Series has a unit root | Corroborating check for ADF |

Report ADF p-values for all continuous features in the gate evaluation JSON. Flag any feature with p > 0.05 as potentially non-stationary. **Library:** `statsmodels` (already available in the venv).

### Outlier detection and treatment

| Method | Description | Application |
|---|---|---|
| Winsorisation at 1st/99th percentile | Cap extreme values at training distribution boundaries | Apply to all continuous features before training |
| IQR fence (3x) | Remove / cap values beyond 3x IQR from median | Alternative for skewed distributions |
| Return spike filter | Single-bar return > 5 sigma from rolling mean | Flag as extreme event; test performance with and without |
| Mahalanobis distance | Multi-dimensional outlier on full feature vector | Flag rows with distance > chi-squared 99% threshold |

### Feature correlation audit

Before each training run, compute and report the feature correlation matrix:
- Flag feature pairs with Pearson |r| > 0.85 as near-duplicates
- Track correlation stability across folds (high variance in correlation = unstable relationship)
- Report VIF (Variance Inflation Factor) for each feature; VIF > 10 suggests multicollinearity

### Missing data policy

| Scenario | Policy |
|---|---|
| Feature computable but data missing for bar | Forward-fill up to 3 bars; otherwise exclude the bar |
| External data feed unavailable | Use last valid value if within 2 trading days; otherwise block entries |
| Training window has more than 5% missing bars | Reject run with DATA_QUALITY_FAILURE |

---

## 15. Backtesting Engine Improvements

### Variable spread simulation

Current engine uses a fixed spread assumption. Improvements:
- Sample spread from the empirical distribution of historical bid-ask spreads
- Widen spread during high-vol periods: `spread = base_spread * (1 + k * volatility_ratio)`
- Model liquidity crisis spread spikes (spread > 5x normal on extreme bars)

**Implementation.** Add `--spread-model fixed|variable|volatility-scaled` flag to `backtest_engine.py`.

### Realistic order execution model

| Execution assumption | Current | Improved |
|---|---|---|
| Entry price | Bar close | Bar close + slippage drawn from Normal(0, slippage_std) |
| Stop-loss fill | Exact stop price | Stop price + gap (D1 open gaps sampled from historical gap distribution) |
| Limit order fill rate | 100% | Stochastic probability function of distance from market |

### Monte Carlo simulation of equity curve

After backtest, run N = 1000 Monte Carlo simulations:
- Resample trades with replacement (bootstrap)
- Compute distribution of Sharpe, Max DD, and profit factor
- Report 5th, 50th, and 95th percentile for each metric

**Use.** Understand the realistic range of outcomes, not just the point estimate from the observed sequence of trades.

### Regime-conditional P&L attribution

After every backtest, decompose total P&L by:
- Regime label (trending / ranging / high-vol)
- Calendar period (year, quarter, month)
- Trade duration bucket (short-held vs. long-held)
- Signal probability bucket (0.50-0.55, 0.55-0.65, 0.65+)

Report this breakdown in every gate evaluation JSON to identify whether edge is broad or concentrated in specific regimes or periods.

### Synthetic data augmentation

Generate additional training data to supplement limited historical windows:
- **GBM paths**: synthetic price paths calibrated to observed drift and volatility
- **VAR model paths**: multi-asset synthetic paths preserving cross-correlations
- **Block bootstrap**: resample contiguous historical blocks to create alternative history paths

**Caveat.** Synthetic data must only be used for training augmentation. Never use synthetic data for holdout validation.

---

## 16. Portfolio and Multi-System Risk

### Correlation-aware position sizing

When multiple systems (TS-001, TS-003, etc.) are simultaneously active:
- Compute rolling 60-bar correlation between system returns
- Apply a correlation discount to each system's position size: `size = base_size / (1 + sum(|rho_ij|))`
- Prevents over-concentration when multiple systems are in correlated trades

### Equity-curve-based risk scaling

Adjust position size dynamically based on the strategy's drawdown state:

| Equity curve state | Position size |
|---|---|
| Above rolling 100-trade SMA | Full size |
| Below SMA but within 10% of peak | 75% of full size |
| Drawdown 10-20% from peak | 50% of full size |
| Drawdown greater than 20% from peak | 25% or pause |

### Portfolio-level circuit breaker

Define a portfolio-level maximum drawdown (e.g., 15% of total capital across all active systems). If breached:
1. All systems reduce to minimum position size
2. Human review required before restoring to normal
3. Event logged in the incident runbook

### Kelly-optimal portfolio weights

Apply portfolio-level Kelly criterion to allocate capital across multiple active strategies:
- Estimate the covariance matrix of strategy returns from the experiment history
- Compute Kelly-optimal weights using the mean-variance framework
- Apply half-Kelly (50%) for production safety

### Intra-day correlation limit

Hard rule: at any point in time, total notional exposure to strategies with pairwise return correlation > 0.7 must not exceed a defined percentage of total capital.

---

## 17. Live Trading Infrastructure

### Model performance monitoring

Track live model performance against backtest expectations continuously:

| Metric | Alert condition |
|---|---|
| Live win rate vs. backtest win rate | Alert if deviation exceeds 15% over 20+ live trades |
| Live profit factor vs. backtest PF | Alert if live PF less than 0.8 * backtest PF over 20+ trades |
| Live vs. backtest average trade return | Alert if live mean is less than 0.6 * backtest mean |
| Signal frequency vs. expected | Alert if live signal count is less than 50% of expected rate |

### Signal confidence reporting

Alongside each trade signal, log:
- Raw model probability score
- Calibration bin (expected win rate for this probability range from training calibration plot)
- Top-3 feature contributions (from SHAP values if enabled)
- Regime state at signal time

### Live vs. training feature parity check

After each live bar, compare the feature vector computed by the backend against the feature vector computed in the training pipeline using the same raw data. Flag any discrepancy > 0.1% as a potential data or computation drift.

### EA health monitoring extensions

Extend the current EA heartbeat to include:

| Check | Frequency | Action on fail |
|---|---|---|
| Backend API latency | Every bar | Log warning if > 200ms |
| Model version match (live vs. expected) | Every bar | Alert if mismatch |
| Feature schema version match | On EA startup | Block trading if mismatch |
| Position size vs. risk model ceiling | On every entry signal | Block if lot size exceeds risk ceiling |

### Trade journal and post-trade analysis

After each trade closes, record and analyse:
- MAE, MFE, duration, entry reason (signal probability, regime state)
- Flag trades that significantly deviate from expected MAE / MFE profile
- Weekly summary: win rate, average R, G-ratio, DSR for the live period
- KS test comparing live trade return distribution to backtest distribution

---

## Priority Matrix

A consolidated view of the highest-impact, lowest-effort additions across all sections, including all items added in v1.1.

| Item | Section | Effort | Confidence | Priority | Status |
|---|---|---|---|---|---|
| Wire XGBoost / LightGBM to CLI | 2 | Low | High | P1 | ✅ |
| RSI, MACD, Bollinger Band width features | 3.1 / 3.2 | Low | High | P1 | ✅ |
| ADX strength filter / feature | 3.1 / 5 | Low | High | P1 | ✅ |
| Squeeze Momentum indicator | 3.1 | Low | High | P1 | ✅ |
| Supertrend direction flag | 3.1 | Low | High | P1 | ✅ |
| KAMA and KAMA slope features | 3.1 | Low | High | P1 | ✅ |
| Linear regression slope + R-squared | 3.1 | Low | High | P1 | ✅ |
| Volume ratio and volume momentum | 3.3 | Low | High | P1 | ✅ |
| Bar quality validation pipeline | 14 | Low | High | P1 | ✅ |
| Feature stationarity reporting (ADF) | 14 | Low | High | P1 | ✅ |
| Winsorisation of feature outliers | 14 | Low | High | P1 | ✅ |
| Day of week, session calendar features | 3.5 | Low | High | P1 | ✅ |
| Hurst exponent feature | 3.7 | Low | High | P1 | ✅ |
| CUSUM filter statistic as feature | 3.7 | Low | High | P1 | ✅ |
| Efficiency ratio feature | 6 | Low | High | P1 | ✅ |
| Calmar + Sortino in gate evaluation | 12 | Low | High | P1 | ✅ |
| MAE / MFE / G-ratio in gate evaluation | 12 | Low | High | P1 | ✅ |
| Monte Carlo permutation test | 8 | Low | High | P1 | ✅ |
| SHAP feature importance in report | 13 | Low | High | P1 | ✅ |
| Overnight swap cost model | 10 | Low | High | P1 | ✅ |
| Deflated Sharpe Ratio gate | 8 / 12 | Low | High | P1 | ✅ |
| Model performance monitoring alerts | 17 | Low | High | P1 | ✅ |
| Triple barrier labeling | 4 | Medium | High | P2 | ✅ |
| CUSUM-filtered sampling | 4 | Medium | High | P2 | ✅ |
| Fractionally differentiated features | 3.7 / 4 | Medium | High | P2 | ✅ |
| HMM regime detection as feature | 6 | Medium | High | P2 | ✅ |
| GARCH / EGARCH vol regime | 6 | Medium | High | P2 | ✅ |
| Expanding window CV option | 8 | Low | Medium | P2 | ✅ |
| Meta-labeling | 4 | Medium | High | P2 | ✅ |
| Soft voting ensemble (logreg + XGB + RF) | 2 | Medium | High | P2 | ✅ |
| Volatility-scaled position sizing | 11 | Medium | High | P2 | ✅ |
| Equity-curve risk scaling | 16 | Medium | High | P2 | ✅ |
| DXY and VIX as external features | 3.6 | Medium | High | P2 | ✅ |
| Multi-timeframe confirmation variant | 5 | Medium | Medium | P2 | ✅ |
| Regime-conditional P&L attribution | 15 | Medium | High | P2 | ✅ |
| Feature correlation audit | 14 | Low | Medium | P2 | ✅ |
| Feature store (database cache) | 13 | Medium | High | P2 | ✅ |
| Concept drift detection (PSI) | 13 | Medium | High | P2 | ✅ |
| Structural break tests on windows | 6 | Medium | High | P2 | ✅ |
| BOCPD changepoint detection | 6 | Medium | Medium | P3 | ✅ |
| CPCV walk-forward + PBO | 8 | Medium | High | P3 | ✅ |
| K-means clustering regime | 6 | Medium | Medium | P3 | ✅ |
| Ichimoku Cloud features | 3.1 | Low | High | P3 | ✅ |
| Variable spread simulation | 15 | Medium | Medium | P3 | ✅ |
| Monte Carlo equity curve simulation | 15 | Medium | High | P3 | ✅ |
| Shadow trading framework | 13 | Medium | High | P3 | ✅ |
| Correlation-aware portfolio sizing | 16 | Medium | High | P3 | ✅ |
| Portfolio-level circuit breaker | 16 | Low | High | P3 | ✅ |
| Automated retraining pipeline | 13 | High | High | P3 | ✅ |
| Deep learning (LSTM / TCN) | 2 | High | Medium | P4 | ⬜ |
| COT / retail sentiment data | 3.8 | High | High | P4 | ⬜ |
| Synthetic data augmentation | 15 | High | Medium | P4 | ⬜ |
| Kelly-optimal portfolio weights | 16 | High | Medium | P4 | ⬜ |
