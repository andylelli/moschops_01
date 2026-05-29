# 15 System Folder Index

System ID: TS-004
Version: 1.0
Last updated: 2026-05-28

## All files in TS-004 folder

| File | Created | Version | Description |
|---|---|---|---|
| README.md | 2026-05-28 | 1.0 | System overview and quick navigation |
| _INDEX.md | 2026-05-28 | 1.0 | Folder index (this file via _INDEX) |
| 00_system_charter.md | 2026-05-28 | 1.0 | Mission, scope, success and failure criteria |
| 01_strategy_spec.md | 2026-05-28 | 1.0 | Signal logic, entry conditions, regime gate, threshold |
| 02_instruments_execution.md | 2026-05-28 | 1.0 | EURUSD H4 spec, execution policy, cost model |
| 03_data_contract.md | 2026-05-28 | 1.0 | Data sources, OHLCV fields, holdout protocol |
| 04_feature_schema.md | 2026-05-28 | 1.0 | All 16 features with lookbacks and sources |
| 05_model_training.md | 2026-05-28 | 1.0 | Training config, CV design, artefact requirements |
| 06_validation_protocol.md | 2026-05-28 | 1.0 | Walk-forward stages, cost model, statistical checks |
| 07_risk_safety.md | 2026-05-28 | 1.0 | Position limits, stops, circuit breaker specification |
| 08_promotion_gates.md | 2026-05-28 | 1.0 | Numeric gate thresholds, current posture (REJECT) |
| 09_live_operations.md | 2026-05-28 | 1.0 | Deployment stages, SLO, monitoring rules |
| 10_incident_runbook.md | 2026-05-28 | 1.0 | P1–P4 runbooks for common incidents |
| 11_experiment_log.md | 2026-05-28 | 1.0 | 5 planned experiments (all Pending) |
| 12_change_control.md | 2026-05-28 | 1.0 | Change policy and version history |
| 13_audit_traceability.md | 2026-05-28 | 1.0 | Lineage chain, leakage checklist, run registry |
| 14_document_completion_checklist.md | 2026-05-28 | 1.0 | Phase completion gates |
| 15_system_folder_index.md | 2026-05-28 | 1.0 | This file |
| 17_strategy_how_it_works.md | 2026-05-28 | 1.0 | Non-technical strategy explainer |

## Related files (outside this folder)

| File | Location | Description |
|---|---|---|
| Implementation config | `docs/10-trading-systems/TS-004/implementation/config.yaml` | Machine-readable config for runner, gate evaluator and deployment |
| Recipe | `docs/10-trading-systems/recipes/04-recipe-ts-004.md` | Source design recipe |
| Training script | `training/run_historical_split.py` | Primary training runner |
| Feature builder | `training/features.py` | Feature computation |
| Walk-forward CV | `training/cpcv.py` | CPCV splitter and PBO |
| Circuit breaker | `training/circuit_breaker.py` | Risk circuit breaker |
| Shadow trader | `training/shadow_trader.py` | Paper signal tracking |
| MC simulation | `training/mc_simulation.py` | Bootstrap/MC analysis |
| Portfolio sizing | `training/portfolio_sizing.py` | Kelly and ERC weights |
| Run artefacts | `docs/09-training-runs/runs/` | Per-run reports and models |
| Production model | `models/ts004_v1.onnx` (after holdout run) | Deployed inference model |
