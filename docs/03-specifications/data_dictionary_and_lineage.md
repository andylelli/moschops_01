# Data Dictionary and Lineage

Version: 1.0  
Last updated: 2026-05-23

## Purpose
Define the primary persisted entities and the lineage required for auditability and model training.

## Core Entities
| Entity | Purpose | Primary source | Key lineage fields |
|---|---|---|---|
| strategy_configs | Strategy runtime + training-default parameter snapshots | Backend config API | strategy_id, strategy_version, config_json.aiThresholds, config_json.aiMandatory |
| model_versions | Model registry metadata | Training pipeline | model_version, feature_schema_hash |
| signals | Candidate trade decisions | `/signal` flow | decision_id, signal_id, strategy_id, model_version |
| rejected_signals | Signals vetoed by rules or risk | `/risk-check` flow | decision_id, rejection_reason, strategy_id |
| features | Decision-time feature vectors | Feature engine | decision_id, feature_hash, dataset_version |
| model_predictions | Inference outputs and confidence | Model runtime | decision_id, model_version, prediction_score |
| trades | Executed trade lifecycle | EA and backend logs | trade_id, decision_id, strategy_id |
| positions | Open portfolio state | EA snapshot and backend state | position_id, symbol, strategy_id |
| risk_events | Risk vetoes and safety events | Risk engine | event_id, decision_id, risk_rule |
| account_snapshots | Account and exposure snapshots | EA snapshot | snapshot_id, account_id, captured_at |
| training_runs | Training session records with achieved metrics, diagnostics artifacts, and execution telemetry | Training pipeline and training API | training_run_id, status (RUNNING/COMPLETED/FAILED), dataset_version, model_version, metrics_json.outcome, metrics_json.diagnostics, metrics_json.execution |
| outcome_labels | Supervised labels for learning | Post-trade labeling job | signal_id, label_version |
| performance_snapshots | Aggregated performance metrics | Reporting pipeline | snapshot_id, strategy_id, model_version |
| market_bars_raw | Historical OHLCV source bars | MT5 export / broker history | symbol, timeframe, bar_close_time_utc, source_batch_id |
| training_datasets | Materialized supervised datasets | Training extraction pipeline | dataset_version, feature_schema_hash, source_batch_id |
| news_events | Normalized scheduled and incident event records | Financial Modeling Prep (FMP) ingestion | news_event_id, provider, provider_event_id, scheduled_at_utc |
| news_provider_status | Provider freshness and sync state | FMP sync monitor | provider, provider_tier, freshness_state, last_successful_sync_utc |
| news_guard_windows | Materialized policy windows for risk checks | News policy resolver | guard_window_id, news_event_id, policy_action, starts_at_utc, ends_at_utc |
| news_incidents | Breaking-news incident lifecycle (v2+) | FMP + operator workflow | news_incident_id, source, status, started_at_utc |
| historical_download_jobs | Historical data ingestion job audit records | Dashboard-triggered provider download flow | job_id, source, symbol, timeframe, from_date, to_date, status |
| historical_bars | Persisted OHLCV bars for training/exploration | Provider historical API ingestion | source, symbol, timeframe, bar_close_time_utc |

## Lineage Rules
- Every decision record must link to one strategy and one decision time.
- Every model prediction must link to the model version and feature hash used at inference time.
- Every trade outcome must link back to the originating signal or risk veto.
- Retention policy must be defined alongside the implementation schema before live data goes into production.
- Every training dataset row must trace back to raw market bars and execution outcomes.
- Feature parity fields (including volatility) must be consistent between runtime payload and training dataset definitions.
- News-driven decisions must include provider lineage (`provider=FMP`) and active pricing tier (`FREE` in `v1.x`, `BASIC` in `v2+`).
- Historical data ingestion must record request scope (symbol/timeframe/date window), ingestion outcome counts, and persisted bar lineage for reproducibility.
- Strategy runtime settings used by `/signal` must be traceable to the latest persisted `strategy_configs` snapshot for `(strategy_id, strategy_version)`.
- Training session outcomes shown in UI must come from persisted `training_runs.metrics_json` so operators can audit what was achieved per run.
- Training diagnostics views (confusion matrix, ROC/PR curves, calibration bins, and feature importance) must be sourced from `training_runs.metrics_json.diagnostics` with run-level provenance.
