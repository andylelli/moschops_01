# 13 Audit Traceability

System ID: TS-004
Version: 1.0
Last updated: 2026-05-28

## Purpose

This document provides the audit trail linking each training run to its inputs, configuration, outputs, and any downstream decisions. Every experiment must produce a complete audit record before results are used.

## Lineage requirements

For each experiment run (EXP-001 onwards), the following must be present in the run directory before results are considered valid.

Run directories are auto-generated under: `logs/training/<YYYY-MM-DD>/<HHmmss>_<symbol>_<timeframe>_<label>/`

| Artefact | Required | Filename |
|---|---|---|
| Run config | Yes | `run_config.json` |
| Training report | Yes | `report.json` |
| Feature schema | Yes | `feature_schema.json` |
| Run log (human) | Yes | `run.log` |
| Structured events | Yes | `run.jsonl` |
| ONNX model | Yes (holdout only) | `model.onnx` |
| Monte Carlo report | Yes (EXP-004+) | `mc_report.json` |
| PBO calculation | Yes (EXP-004+) | `pbo.json` |

## Data lineage chain

```
FMP API → raw_ohlcv.csv → features.py (build_feature_set) → feature_matrix.csv
→ label computation (edge, 8 bps, 10-bar) → labelled_dataset.csv
→ train/test split (2012-2021 / 2022) → StandardScaler fit
→ XGBoost training (5-fold CV) → calibrated model
→ ONNX export (skl2onnx) → model.onnx
→ Backend inference endpoint → EA signal
```

Each arrow represents a deterministic transformation. The run artefacts must make every step reproducible.

## Leakage prevention checklist

For each run, confirm:

| Check | Confirmed in | Action if fails |
|---|---|---|
| Scaler fit only on training data | `run_config.json` | Invalidate run; fix scaler; rerun |
| No future bar data in features | Feature lookbacks in `04_feature_schema.md` | Invalidate; fix feature pipeline |
| Holdout not used for threshold selection | `run_config.json` | Invalidate; threshold must come from dev CV only |
| Label computed using only forward bars (no leakage) | `label_distribution.json` label offset | Invalidate; fix labelling |
| Embargo correctly applied (5 bars) | CV config in `run_config.json` | Invalidate; rerun with correct embargo |

## Run registry

| Run ID | Experiment | Date | Status | Artefact path |
|---|---|---|---|---|
| — | EXP-001 | Not yet run | Pending | `logs/training/<date>/<time>_EURUSD_H4_exp-001/` |
| — | EXP-002 | Not yet run | Pending | `logs/training/<date>/<time>_EURUSD_H4_exp-002/` |
| — | EXP-003 | Not yet run | Pending | `logs/training/<date>/<time>_EURUSD_H4_exp-003/` |
| — | EXP-004 | Not yet run | Pending | `logs/training/<date>/<time>_EURUSD_H4_exp-004/` |
| — | EXP-005 | Not yet run | Pending | `logs/training/<date>/<time>_EURUSD_H4_exp-005a/` … |
| — | HOLDOUT | Not yet run | Pending | `logs/training/<date>/<time>_EURUSD_H4_holdout/` |

_Status values: Pending / Valid / INVALID_FOR_PROMOTION / Archived_

## Promotion artefact set

Before promotion is considered, the following must be confirmed valid:

| Item | Required document |
|---|---|
| Holdout run artefacts complete (all 9 required artefacts present) | This document |
| No leakage flags in any holdout artefact | This document |
| Gate C thresholds met (signed off in `08_promotion_gates.md`) | `08_promotion_gates.md` |
| Holdout run_config matches the locked dev config | `run_config.json` comparison |
| ONNX model hash matches deployed model | `model.onnx` SHA-256 |
