# 03 Data Contract

System ID: TS-001
Version: 1.0
Last updated: 2026-05-27

## Data sources
| Source | Endpoint/File | Granularity | Ownership | Notes |
|---|---|---|---|---|
| Market bars | /historical-data/download and /historical-data/bars | D1 primary | Backend | Used for training and validation windows |
| Live snapshot | EA payload to /signal | decision event | EA + backend | Includes OHLC-derived context and account snapshot |
| Open trades snapshot | /trades/open | runtime snapshot | EA + backend | Used for operator visibility |
| Training artifact | training/run_historical_split.py output JSON | run-level | Training pipeline | Includes metrics, bars, model path |

## Required market snapshot fields
| Field | Type | Description |
|---|---|---|
| symbol | string | Instrument identifier |
| timeframe | string | Decision timeframe |
| barCloseTimeUtc | string | Completed bar timestamp |
| close1 | number | Latest completed close |
| sma100_1 | number | Fast trend filter |
| sma200_1 | number | Long trend filter |
| highestHigh55 | number | Breakout high reference |
| lowestLow55 | number | Breakout low reference |
| atr20_1 | number | Volatility and stop reference |
| volatility | number | Normalized volatility field |
| spreadPrice | number | Raw spread at decision time |

## Point-in-time rules
1. Decisions must use completed-bar data only.
2. All timestamps use UTC normalization.
3. No future bars allowed in training feature generation.

## Data quality checks
1. Drop or repair non-numeric OHLCV rows before feature build.
2. Drop duplicates on barCloseTimeUtc prior to feature computation.
3. Reject runs with insufficient bars for train or test thresholds.

## Data lineage requirements
1. Capture run windows (train and test) in output artifact.
2. Capture model path and generation timestamp in run artifact.
3. Maintain decision and execution IDs for runtime traceability.

## Governance reference
1. [../robust_trading_no_curve_fit_plan.md](../robust_trading_no_curve_fit_plan.md)
