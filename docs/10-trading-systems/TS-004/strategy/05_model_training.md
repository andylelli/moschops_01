# 05 Model Training

System ID: TS-004
Version: 1.0
Last updated: 2026-05-28

## Training framework

| Field | Value |
|---|---|
| Training script | `training/run_historical_split.py` |
| Walk-forward script | `training/train_walk_forward.py` |
| Feature builder | `training/features.py` |
| Quality gates | `training/quality.py` |
| Metrics | `training/metrics.py` |

## Model configuration

| Parameter | Value | Notes |
|---|---|---|
| Estimator | XGBoost (`xgb`) | |
| Task | Binary classification | P(edge) |
| Label mode | edge | 8 bps, 10-bar horizon |
| Class balance | `class_weight='balanced'` | Handles ~70/30 class imbalance |
| Calibration | Isotonic regression | Applied post-training using held-out fold |
| ONNX export | Yes | Via `skl2onnx` after final training |
| ONNX opset | 15 | Default in export pipeline |

## XGBoost hyperparameter defaults (discovery phase)

| Parameter | Value | Rationale |
|---|---|---|
| `n_estimators` | 200 | Starting point; sweep in EXP-004 |
| `max_depth` | 4 | Limits overfitting on 16-feature set |
| `learning_rate` | 0.05 | Conservative; prevents aggressive early splits |
| `subsample` | 0.8 | Introduces bagging variance |
| `colsample_bytree` | 0.8 | Feature subsampling per tree |
| `reg_alpha` | 0.1 | L1 regularisation |
| `reg_lambda` | 1.0 | L2 regularisation |
| `random_state` | 42 | Reproducibility |

## Walk-forward cross-validation design

| Parameter | Value | Notes |
|---|---|---|
| Number of folds | 5 | |
| Window type | Expanding | All prior data in each train fold |
| Embargo (bars) | 5 | = 20 hours gap between train end and test start |
| Test fold size | Variable (equal time slices) | Approx. 10 months per fold |
| Purge policy | Embargo-only | No per-sample purging (no overlapping labels) |
| CV implementation | `training/cpcv.py` `CombPurgedCV` (P3) | For PBO calculation |
| Probability of backtest overfitting | Computed after EXP-004 | Target PBO < 0.40 |

## Training window specification

| Split point | Date | Purpose |
|---|---|---|
| Train start | 2012-01-01 | 10 years of diverse macro regimes |
| Dev/test split | 2022-01-01 | Rate-hike macro shift in dev window |
| Holdout start | 2023-01-01 | Never used until acceptance run |
| Holdout end | 2024-12-31 | 2 full years of holdout |

**Approximate bar counts:**
- Train window: ~17,500 H4 bars
- Dev/test window: ~1,500 H4 bars (2022)
- Holdout window: ~4,400 H4 bars (2023–2024)

## Threshold selection protocol

| Step | Action |
|---|---|
| 1 | Run 5-fold CV on dev window; collect per-fold calibrated probabilities |
| 2 | For each candidate threshold in [0.52, 0.75] (step 0.01), compute constrained objective |
| 3 | Objective: maximise median net return subject to: trades ≥ 60 AND max_dd ≤ 20% |
| 4 | Select threshold with best dev-window objective score |
| 5 | Lock threshold — do not adjust on holdout data |

## Feature pipeline invocation

```bash
python training/run_historical_split.py \
  --symbol          EURUSD \
  --timeframe       H4 \
  --label-mode      edge \
  --min-edge-bps    8 \
  --horizon-bars    10 \
  --walk-forward-folds 5 \
  --embargo-bars    5 \
  --spread-bps      2.5 \
  --commission-bps  1.0 \
  --slippage-bps    0.5 \
  --min-trades      60 \
  --max-dd          0.20 \
  --run-label       exp-001
```

> Output is written to `logs/training/<date>/<time>_EURUSD_H4_exp-001/`. No `--output-dir` required.

## Model artefacts (per run)

All artefacts are written to the auto-generated run directory:
`logs/training/<YYYY-MM-DD>/<HHmmss>_<symbol>_<timeframe>[_<label>]/`

Use `--run-label exp-001` (etc.) to embed the experiment ID in the directory name.

| Artefact | Filename | Description |
|---|---|---|
| Run log | `run.log` | Timestamped human-readable progress log (INFO+) |
| Structured events | `run.jsonl` | One JSON line per event (DEBUG+); machine-readable |
| Training report | `report.json` | Full metric report (AUC, PF, drawdown, fold summaries, cost assumptions) |
| Feature schema | `feature_schema.json` | Feature names and types written at run time |
| Run config | `run_config.json` | All CLI parameters used for reproducibility |
| ONNX model | `model.onnx` | Inference model |

## Model governance

| Rule | Detail |
|---|---|
| One config per run | No parameter bundling across experiments |
| Holdout locked | Holdout run is the final experiment only |
| Retraining trigger | Monitoring AUC < 0.52 for 7+ consecutive days, or `retrain_pipeline.py` trigger |
| Retraining gate | New model AUC > current − 0.01 AND current gates still pass |
| Model version | Semantic version in ONNX model metadata (e.g., `ts004_v1.0.0`) |

## Shadow trading integration

From EXP-001 onwards, `training/shadow_trader.py` (P3) will run in parallel to track signal quality without capital risk. Shadow trader log is stored in `docs/09-training-runs/runs/<run_dir>/shadow_trades.json`.
