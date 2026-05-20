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

## Rollback Criteria
- Any material regression in live behavior.
- Model-serving failure that affects decision flow.
- Operator-triggered rollback after incident review.

## Retraining Cadence
- Baseline cadence: every 4 weeks.
- Earlier retrain if drift, calibration degradation, or operational feedback indicates it.
