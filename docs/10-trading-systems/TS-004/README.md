# TS-004 Event-Aware Trend Continuation

## System overview

| Field | Value |
|---|---|
| System ID | TS-004 |
| System name | Event-Aware Trend Continuation |
| Version | 1.0 |
| Status | Discovery |
| Instrument | EURUSD |
| Timeframe | H4 |
| Strategy class | Trend-follow with event gating |
| AI model | XGBoost (calibrated) |
| Created | 2026-05-28 |
| Recipe | [04-recipe-ts-004.md](../recipes/04-recipe-ts-004.md) |

## One-line thesis

After major macro events, the pre-event trend tends to resume once abnormal volatility normalises; a classifier gated on volatility regime captures these high-quality continuation windows.

## Current status

TS-004 is in the **Discovery** phase. No training runs or holdout evaluation have been performed. Proceed with experiments in the order defined in [11_experiment_log.md](strategy/11_experiment_log.md).

## Quick links

| # | Document | Description |
|---|---|---|
| 00 | [00_system_charter.md](strategy/00_system_charter.md) | Mission, scope, success criteria |
| 01 | [01_strategy_spec.md](strategy/01_strategy_spec.md) | Signal logic, regime gate, thresholds |
| 02 | [02_instruments_execution.md](strategy/02_instruments_execution.md) | Instrument, execution parameters |
| 03 | [03_data_contract.md](strategy/03_data_contract.md) | Data sources and field contract |
| 04 | [04_feature_schema.md](strategy/04_feature_schema.md) | Full feature list and schema |
| 05 | [05_model_training.md](strategy/05_model_training.md) | Training config and CV design |
| 06 | [06_validation_protocol.md](strategy/06_validation_protocol.md) | Walk-forward and cost assumptions |
| 07 | [07_risk_safety.md](strategy/07_risk_safety.md) | Position limits, stops, circuit breakers |
| 08 | [08_promotion_gates.md](strategy/08_promotion_gates.md) | Gate thresholds and promotion status |
| 09 | [09_live_operations.md](strategy/09_live_operations.md) | Live deployment and monitoring |
| 10 | [10_incident_runbook.md](strategy/10_incident_runbook.md) | Incident response procedures |
| 11 | [11_experiment_log.md](strategy/11_experiment_log.md) | Ordered experiment log |
| 12 | [12_change_control.md](strategy/12_change_control.md) | Change log and version history |
| 13 | [13_audit_traceability.md](strategy/13_audit_traceability.md) | Artifact lineage and audit trail |
| 14 | [14_document_completion_checklist.md](strategy/14_document_completion_checklist.md) | Document completion status |
| 15 | [15_system_folder_index.md](strategy/15_system_folder_index.md) | Full file index |
| 17 | [17_strategy_how_it_works.md](strategy/17_strategy_how_it_works.md) | Non-technical strategy explainer |
| — | [implementation/config.yaml](implementation/config.yaml) | Machine-readable implementation config |

## Do not do list

- Do not view holdout data before the single locked holdout run.
- Do not re-tune using holdout results.
- Do not run more than one config against holdout.
- Do not promote without completing all 5 promotion gates.
