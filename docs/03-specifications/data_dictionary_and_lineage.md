# Data Dictionary and Lineage

Version: 1.0  
Last updated: 2026-05-20

## Purpose
Define the primary persisted entities and the lineage required for auditability and model training.

## Core Entities
| Entity | Purpose | Primary source | Key lineage fields |
|---|---|---|---|
| strategy_configs | Strategy parameters by environment | Backend config | strategy_id, strategy_version |
| model_versions | Model registry metadata | Training pipeline | model_version, feature_schema_hash |
| signals | Candidate trade decisions | `/signal` flow | decision_id, signal_id, strategy_id, model_version |
| rejected_signals | Signals vetoed by rules or risk | `/risk-check` flow | decision_id, rejection_reason, strategy_id |
| features | Decision-time feature vectors | Feature engine | decision_id, feature_hash, dataset_version |
| model_predictions | Inference outputs and confidence | Model runtime | decision_id, model_version, prediction_score |
| trades | Executed trade lifecycle | EA and backend logs | trade_id, decision_id, strategy_id |
| positions | Open portfolio state | EA snapshot and backend state | position_id, symbol, strategy_id |
| risk_events | Risk vetoes and safety events | Risk engine | event_id, decision_id, risk_rule |
| account_snapshots | Account and exposure snapshots | EA snapshot | snapshot_id, account_id, captured_at |
| training_runs | Training job metadata | Training pipeline | training_run_id, dataset_version |
| outcome_labels | Supervised labels for learning | Post-trade labeling job | signal_id, label_version |
| performance_snapshots | Aggregated performance metrics | Reporting pipeline | snapshot_id, strategy_id, model_version |

## Lineage Rules
- Every decision record must link to one strategy and one decision time.
- Every model prediction must link to the model version and feature hash used at inference time.
- Every trade outcome must link back to the originating signal or risk veto.
- Retention policy must be defined alongside the implementation schema before live data goes into production.
