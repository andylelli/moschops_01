# 04 Feature Schema

System ID: TS-004
Version: 1.0
Last updated: 2026-05-28

## Feature schema version

Schema version: `ts004_v1` (based on `features.py` build_feature_set, P1 extended set)

## Feature inventory

### Momentum features

| Feature name | Type | Lookback | Source | Notes |
|---|---|---|---|---|
| ret1 | float | 1 bar | `log(close[t] / close[t-1])` | 1-bar log return |
| ret2 | float | 2 bars | `log(close[t] / close[t-2])` | 2-bar log return |
| ret3 | float | 3 bars | `log(close[t] / close[t-3])` | 3-bar log return |
| ret5 | float | 5 bars | `log(close[t] / close[t-5])` | 5-bar log return |
| ret10 | float | 10 bars | `log(close[t] / close[t-10])` | 10-bar log return (pre-event context) |

### Volatility features

| Feature name | Type | Lookback | Source | Notes |
|---|---|---|---|---|
| volatility20 | float | 20 bars | `std(ret1[-20:]) × sqrt(252×6)` | 20-bar annualised realised vol |
| volatility100 | float | 100 bars | `std(ret1[-100:]) × sqrt(252×6)` | 100-bar baseline vol |
| volatility_regime | float | 100 bars | `vol20 / vol100` | **Key feature** — post-event detection |
| atr_normalised | float | 14 bars | `ATR14 / close` | Normalised average true range |

### Trend features

| Feature name | Type | Lookback | Source | Notes |
|---|---|---|---|---|
| above_sma | int (0/1) | 200 bars | `1 if close > SMA200 else 0` | Trend direction indicator |
| trend_strength | float | 20 bars | `ret20_smooth / ATR20` | Trend quality; > 0.3 = trending |
| breakout_distance | float | 20 bars | `(close - high20) / ATR20` | Distance from 20-bar high |
| efficiency_ratio | float | 20 bars | `abs(ret20) / sum(abs(ret1[-20:]))` | 0 = random; 1 = perfect trend |
| adx | float | 14 bars | Standard ADX formula | Trend strength 0–100 |

### Indicator features

| Feature name | Type | Lookback | Source | Notes |
|---|---|---|---|---|
| rsi14 | float | 14 bars | Standard RSI formula | Overbought/oversold context |
| macd_signal | float | 26+9 bars | `MACD(12,26) signal line (9-EMA)` | Trend confirmation crossover |

## Feature selection rationale for TS-004

| Feature | Why selected for TS-004 |
|---|---|
| volatility_regime | Gate metric and key predictive feature — detects post-event vol normalisation |
| efficiency_ratio | Distinguishes genuine trend continuation from noise after events |
| ret10 | Captures the pre-event trend direction (10 H4 bars = 40 hours pre-event context) |
| trend_strength | Confirms trend quality before entry |
| rsi14 | Identifies overbought/oversold conditions post-event spike |
| adx | Trend strength confirmation; prevents entries into choppy regimes |
| above_sma | Hard trend direction filter |

## Features intentionally excluded in v1

| Feature | Reason for exclusion |
|---|---|
| bocpd_cp_prob | Deferred to EXP-007; computationally expensive |
| ichimoku (cloud_bullish) | Deferred to EXP-008; requires displacement computation |
| multiframe HTF signal | Deferred to EXP-006 |
| COT sentiment | P4 — external data source not yet integrated |

## Scaler specification

| Parameter | Value |
|---|---|
| Scaler type | `StandardScaler` (zero mean, unit variance) |
| Fit window | Training data only (2012-01-01 to 2022-01-01) |
| Apply to holdout | Transform only — never refit on holdout |
| Scaler artifact | Saved alongside model as `scaler.pkl` |

## Feature vector shape

| Property | Value |
|---|---|
| Number of features (v1) | 16 |
| Vector type | Float64 numpy array / pandas DataFrame row |
| Missing value policy | Forward-fill then backfill; fail if > 5% missing |

## Feature schema JSON reference

Schema file: `docs/09-training-runs/feature_schema_ts004_v1.json` (generated at first training run)

Schema format follows the existing `models/feature_schema_v1.json` standard:
```json
{
  "version": "ts004_v1",
  "features": [
    {"name": "ret1", "type": "float", "lookback": 1},
    {"name": "volatility_regime", "type": "float", "lookback": 100},
    ...
  ],
  "generated_at": "<ISO timestamp>",
  "source_script": "training/features.py"
}
```
