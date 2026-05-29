# 03 Data Contract

System ID: TS-004
Version: 1.0
Last updated: 2026-05-28

## Data sources

| Source | Type | Used for | Endpoint / access |
|---|---|---|---|
| FMP (Financial Modelling Prep) | OHLCV H4 bars | Training and inference features | `/v3/historical-chart/4hour/EURUSD` |
| PostgreSQL (via Prisma) | Signal logs, outcomes | Monitoring, retrain trigger | Backend ORM |
| ONNX model file | Inference | Live signal generation | Loaded by backend on startup |

## Required OHLCV fields

| Field | Type | Required | Notes |
|---|---|---|---|
| datetime | ISO 8601 string / Unix timestamp | Yes | Bar open time UTC |
| open | float | Yes | Bar open price |
| high | float | Yes | Bar high price |
| low | float | Yes | Bar low price |
| close | float | Yes | Bar close price |
| volume | float | Yes | Tick volume (FX proxy) |

## Training data window

| Parameter | Value |
|---|---|
| Training start | 2012-01-01 |
| Training end (dev/test split) | 2022-01-01 |
| Holdout start | 2023-01-01 |
| Holdout end | 2024-12-31 |
| Data refresh cadence | Per-experiment run |
| Minimum bar count for training | ~17,500 H4 bars (2012–2021) |
| Minimum bar count for holdout | ~4,000 H4 bars (2023–2024) |

## Data quality rules

| Rule | Action on violation |
|---|---|
| No OHLC relationship (high < low, close outside high/low) | Drop bar and log warning |
| Zero volume bar | Drop bar and log warning |
| Gap > 5× ATR between consecutive close prices | Flag as abnormal; log; do not drop |
| Duplicate datetime | Drop duplicate; keep first occurrence |
| More than 0.5% of bars missing | Fail training run with lineage error |
| Any bar before 2012-01-01 | Drop; outside approved training window |

## Feature computation dependencies

All features are computed from the raw OHLCV fields above using `training/features.py`. No external data sources are required for feature computation. The following features have lookback requirements that must be satisfied before the first usable bar:

| Feature | Lookback (bars) | Minimum bars to first usable bar |
|---|---|---|
| SMA200 | 200 | 200 |
| vol100 | 100 | 100 |
| vol20 | 20 | 20 |
| volatility_regime | 100 (via vol100) | 100 |
| rsi14 | 14 | 14 |
| efficiency_ratio (20-bar) | 20 | 20 |
| adx (14-bar) | 14 | 28 (includes internal smoothing) |

The training dataset must have at least 200 bars before the first labelled bar to accommodate SMA200 initialisation.

## Label computation

| Field | Value |
|---|---|
| Label source | Computed from forward OHLCV bars |
| Label mode | edge |
| Edge threshold | 8 bps (0.0008) |
| Horizon | 10 bars |
| Positive label | 1 if abs(close[+10] - close[0]) / close[0] > 0.0008 |
| Label leakage policy | Features computed at bar close using only [0..−N] data |

## Holdout data protocol

1. Holdout bars must not be used for any feature scaling, threshold selection, or model training.
2. The scaler fit on the training window must be applied (transform only) to holdout bars.
3. Any exploratory viewing of holdout distributions (EDA) before the locked run is a protocol violation.
4. The locked holdout run must be logged in `11_experiment_log.md` as the final experiment.

## Data lineage artefacts

For each training run, the following artefacts must be present in the run directory:

| Artefact | Description |
|---|---|
| `data_summary.json` | Row count, date range, null counts, feature distributions |
| `label_distribution.json` | Positive/negative count, class ratio |
| `feature_schema.json` | Feature names, types, computed from |
| `run_config.json` | All training parameters used |

See [13_audit_traceability.md](13_audit_traceability.md) for full lineage requirements.
