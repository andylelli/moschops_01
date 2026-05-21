# Model Governance Standard

Version: 1.0  
Last updated: 2026-05-20

## Purpose
Define the validation, promotion, rollback, and retraining rules for AI models.

## Required Controls
- Walk-forward validation on time-ordered data only.
- Leakage controls with purge and embargo between train and validation slices.
- Calibration review using Brier score and reliability bins.
- Minimum trade-count sufficiency before promotion.
- Promotion requires out-of-sample improvement over the active model.
- Training dataset must be sourced from real historical market and execution data before promotion beyond development.

## Data Source Requirements

- Synthetic datasets are allowed only for pipeline bootstrap and local engineering validation.
- Demo, pilot, and live promotion decisions must use real historical data with auditable provenance.
- Required provenance fields:
  - symbol
  - timeframe
  - barCloseTimeUtc
  - strategyVersion
  - modelVersion
  - featureSchemaHash

Minimum dataset standards for candidate model promotion:

- At least 3 years of history for each active symbol.
- Coverage across trend, range, and high-volatility regimes.
- Label generation based on documented horizon and +2R/-1R rules.
- When news-aware controls are part of evaluation scope, include Financial Modeling Prep (FMP) lineage fields and provider tier evidence (`FREE` for `v1.x`, `BASIC` for `v2+`).

## Lifecycle
1. candidate
2. validation
3. staged
4. active
5. rollback

## Promotion Criteria
- OOS performance must be better than the active model on the selected metric set.
- No regression in drawdown, risk behavior, or calibration.
- Feature schema must match runtime inference exactly.

## Numeric Promotion Thresholds

- **Out-of-Sample Improvement**:
  - Minimum 5% improvement in selected performance metrics (e.g., Sharpe ratio, Brier score).
- **Drawdown Regression**:
  - Maximum allowable increase: 2% relative to the active model.
- **Minimum Trade Count**:
  - At least 500 trades in validation data.
- **Calibration Targets**:
  - Brier score ≤ 0.2.
  - Reliability bins within ±5% of ideal calibration.

## Rollback Criteria
- Any material regression in live behavior.
- Model-serving failure that affects decision flow.
- Operator-triggered rollback after incident review.

## Retraining Cadence
- Baseline cadence: every 4 weeks.
- Earlier retrain if drift, calibration degradation, or operational feedback indicates it.
